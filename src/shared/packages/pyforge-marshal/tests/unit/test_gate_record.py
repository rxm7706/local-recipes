"""``marshal gate evaluate --story`` writes a redacted gate record (Story 82.9, FR-25, AD-34 / AD-25 F-25,
DW-FU-2-6-2).

``build_gate_record`` had no caller: the gate printed its envelope and left no durable evidence. These tests
drive ``cli/gate.py::evaluate_gate`` with a real ``LocalFs`` as the ``RecordPort`` over a provisioned loop home in
``tmp_path`` and read the record back from disk: where it lands (the run's directory, else the AD-25 ``sessions/``
namespace), what it holds, that it validates against ``schemas/gate-record.json``, that a credential never reaches
it, and -- the load-bearing half -- that a record which cannot be written is ONE ``MRS-GATE-017`` WARN under a
verdict and exit code that did not move.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import pytest
from pyforge.core.process import ProcessResult

from pyforge.marshal.adapters.fs_local import FsError, LocalFs
from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.cli import config as config_module
from pyforge.marshal.cli import gate as gate_module
from pyforge.marshal.core.egress import GATE_RECORD_FILENAME
from pyforge.marshal.core.verdict import exit_code_for

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "marshal" / "schemas" / "gate-record.json"
_SLUG = "acme"
_NOW = datetime(2026, 10, 2, 12, 34, 56, 789000, tzinfo=timezone.utc)
_HEAD = "0123456789abcdef0123456789abcdef01234567"
_SECRET = "ghp_" + "a" * 36


def _schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


class _Clock:
    def now(self) -> datetime:
        return _NOW

    def monotonic(self) -> float:
        return 0.0


class _Process:
    def __init__(self, *, returncode: int = 0, stdout: str = "ok", stderr: str = "") -> None:
        self._result = ProcessResult(returncode=returncode, stdout=stdout, stderr=stderr)
        self.calls: list[list[str]] = []

    def run(self, argv, *, cwd, timeout_s=None):
        self.calls.append(list(argv))
        return self._result


class _Vcs:
    """The reads ``evaluate_gate`` makes for ``--story``/``--scope-check``, plus the tree revision."""

    def __init__(self, *, head: str | None = _HEAD, changed: tuple[str, ...] = ()) -> None:
        self._head = head
        self._changed = changed
        self.head_calls: list[Path] = []

    def repo_common_root(self, start):
        return start

    def changed_files(self, repo_root, worktree_path, *, base):
        return self._changed

    def worktree_head_sha(self, worktree_path):
        self.head_calls.append(worktree_path)
        if self._head is None:
            raise VcsCommandError("git rev-parse HEAD failed: not a git repository")
        return self._head


class _RaisingRecord:
    def __init__(self, exc: BaseException) -> None:
        self._exc = exc
        self.calls = 0

    def write_redacted_atomic(self, path, payload):
        self.calls += 1
        raise self._exc


class _RecordingRecord:
    def __init__(self) -> None:
        self.writes: list[tuple[Path, object]] = []

    def write_redacted_atomic(self, path, payload):
        self.writes.append((path, payload))


@pytest.fixture
def world(tmp_path, monkeypatch):
    """A repo root, the project's conventional policy declaring one verify command, and a loop-home root."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    monkeypatch.setattr(config_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "repo_root", lambda: tmp_path)
    policy_dir = tmp_path / "_bmad-output" / "projects" / _SLUG / "planning-artifacts"
    policy_dir.mkdir(parents=True)
    (policy_dir / "marshal-policy.toml").write_text('verify_commands = ["true"]\n', encoding="utf-8")
    return tmp_path


def _tier3(world: Path) -> Path:
    return world / "loop-homes" / _SLUG / "_bmad-output" / "projects" / _SLUG / "implementation-artifacts"


def _provision_home(world: Path) -> Path:
    tier3 = _tier3(world)
    tier3.mkdir(parents=True)
    return tier3


def _provision_run(world: Path, run_id: str) -> Path:
    run_dir = _provision_home(world) / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "journal.jsonl").write_text("", encoding="utf-8")
    return run_dir


def _args(*, story: str | None = "2.3", run_id: str | None = None, scope_check: bool = False):
    return argparse.Namespace(project=_SLUG, run_id=run_id, scope_check=scope_check, story=story, format="json")


def _evaluate(args, *, record=None, clock=None, process=None, vcs=None):
    return gate_module.evaluate_gate(
        args,
        process=process if process is not None else _Process(),
        vcs=vcs if vcs is not None else _Vcs(),
        fs=LocalFs(),
        record=record,
        clock=clock,
    )


def _evaluate_recording(args, **kwargs):
    return _evaluate(args, record=LocalFs(), clock=_Clock(), **kwargs)


def _read(envelope) -> dict:
    path = Path(envelope.data["gate_record"]["path"])
    assert path.name == GATE_RECORD_FILENAME
    return json.loads(path.read_text(encoding="utf-8"))


def _codes(envelope) -> list[str]:
    return [finding.code for finding in envelope.findings]


# --- where the record lands ---------------------------------------------------------------------------------------


def test_a_resolvable_run_gets_its_record_in_that_runs_directory(world):
    run_dir = _provision_run(world, "run-1")

    envelope = _evaluate_recording(_args(run_id="run-1"))

    info = envelope.data["gate_record"]
    expected = run_dir / "gate-records" / "2-3" / GATE_RECORD_FILENAME
    assert info == {"written": True, "path": str(expected), "namespace": "run", "run_id": "run-1"}
    record = _read(envelope)
    jsonschema.validate(instance=record, schema=_schema())
    assert record["story"] == "2.3"
    assert record["run_id"] == "run-1"
    assert record["tree_revision"] == _HEAD
    assert record["timestamp"] == "2026-10-02T12:34:56Z"
    assert record["scope_check_verdict"] is None
    assert record["commands"] == []  # the --run branch folds a journal and runs nothing
    assert "MRS-GATE-017" not in _codes(envelope)


def test_with_no_run_the_record_lands_in_the_sessions_namespace_and_names_the_commands(world):
    tier3 = _provision_home(world)
    process = _Process(returncode=0, stdout="all green")

    envelope = _evaluate_recording(_args(), process=process)

    info = envelope.data["gate_record"]
    assert info["written"] is True
    assert info["namespace"] == "session"
    assert info["run_id"] is None
    path = Path(info["path"])
    sessions = tier3 / "sessions"
    assert path.is_relative_to(sessions)
    session_id, gate_records, story, filename = path.relative_to(sessions).parts
    assert session_id.startswith(f"{_SLUG}-20261002T123456789Z-")  # mint_run_id: <slug>-<utc compact>-<random>
    assert (gate_records, story, filename) == ("gate-records", "2-3", GATE_RECORD_FILENAME)
    record = _read(envelope)
    jsonschema.validate(instance=record, schema=_schema())
    assert "run_id" not in record  # a genuinely run-less evaluation carries none
    assert record["commands"] == [
        {"command": "true", "returncode": 0, "resolvable": True, "stdout": "all green", "stderr": ""}
    ]
    assert process.calls == [["true"]]


def test_a_run_that_does_not_resolve_lands_in_sessions_with_run_id_set(world):
    tier3 = _provision_home(world)

    envelope = _evaluate_recording(_args(run_id="run-missing"))

    info = envelope.data["gate_record"]
    assert info["written"] is True
    assert info["namespace"] == "session"
    assert info["run_id"] == "run-missing"
    assert Path(info["path"]).is_relative_to(tier3 / "sessions")
    record = _read(envelope)
    jsonschema.validate(instance=record, schema=_schema())
    assert record["run_id"] == "run-missing"
    assert "MRS-GATE-005" in _codes(envelope)  # the unresolved run is still the gate's own finding


def test_one_directory_per_story_so_two_stories_in_one_run_never_overwrite(world):
    run_dir = _provision_run(world, "run-1")

    first = _evaluate_recording(_args(story="2.3", run_id="run-1"))
    second = _evaluate_recording(_args(story="2.4", run_id="run-1"))

    assert Path(first.data["gate_record"]["path"]) == run_dir / "gate-records" / "2-3" / GATE_RECORD_FILENAME
    assert Path(second.data["gate_record"]["path"]) == run_dir / "gate-records" / "2-4" / GATE_RECORD_FILENAME
    assert _read(first)["story"] == "2.3"
    assert _read(second)["story"] == "2.4"


def test_the_scope_check_verdict_is_recorded_when_the_check_ran(world):
    _provision_home(world)

    envelope = _evaluate_recording(_args(scope_check=True), vcs=_Vcs(changed=()))

    assert envelope.data["scope_check"]["checked"] is True
    assert _read(envelope)["scope_check_verdict"] in {"clean", "warn"}


# --- what the record holds ----------------------------------------------------------------------------------------


def test_the_record_is_redacted_a_credential_in_captured_output_never_reaches_disk(world):
    _provision_home(world)

    envelope = _evaluate_recording(_args(), process=_Process(returncode=0, stdout=f"token {_SECRET} printed"))

    text = Path(envelope.data["gate_record"]["path"]).read_text(encoding="utf-8")
    assert _SECRET not in text
    assert "ghp_" not in text
    assert "***REDACTED***" in text
    # the live envelope is NOT the durable record: only the record is redacted (AD-34: egress, not stdout)
    assert _SECRET in envelope.data["commands"][0]["stdout"]


def test_the_tree_revision_is_read_from_the_evaluated_root(world):
    _provision_home(world)
    vcs = _Vcs()

    _evaluate_recording(_args(), vcs=vcs)

    assert vcs.head_calls == [world]


# --- a record that cannot be written never moves the verdict -------------------------------------------------------


def _verdict_and_exit(envelope) -> tuple[str, int]:
    return envelope.verdict.value, exit_code_for(envelope.verdict)


def test_no_loop_home_is_one_warn_and_the_verdict_and_exit_code_do_not_move(world):
    without = _evaluate(_args())  # the record port absent: the pre-82.9 gate
    with_ports = _evaluate_recording(_args())  # no loop home provisioned

    assert "gate_record" not in without.data
    assert _codes(with_ports).count("MRS-GATE-017") == 1
    assert [f.code for f in with_ports.findings if f.code != "MRS-GATE-017"] == [f.code for f in without.findings]
    assert _verdict_and_exit(with_ports) == _verdict_and_exit(without)
    info = with_ports.data["gate_record"]
    assert info["written"] is False
    assert "no loop home" in info["reason"]
    finding = next(f for f in with_ports.findings if f.code == "MRS-GATE-017")
    assert finding.severity.value == "warn"
    assert "2.3" in finding.message
    assert not (world / "loop-homes").exists()  # nothing was created on the way to failing


def _write_binding_spec(world: Path, key: str = "2-3") -> None:
    """A tracked spec whose Success signal declares exactly the policy's one verify command, so
    `--story` finds nothing wrong with the gate itself."""
    specs = world / "_bmad-output" / "projects" / _SLUG / "planning-artifacts" / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    (specs / f"spec-{key}.md").write_text(
        "---\ntitle: 'x'\n---\n\n<intent-contract>\n\n## Verification\n\n**Commands:**\n- `true` -- expected: ok.\n",
        encoding="utf-8",
    )


def test_a_clean_gate_with_an_unwritable_record_stays_clean_and_exits_zero(world):
    """The verdict is computed over the gate's own findings and NEVER recomputed to include MRS-GATE-017:
    a gate that passed stays `clean` (exit 0) however the record write went."""
    _write_binding_spec(world)
    portless = _evaluate(_args())
    assert portless.verdict.value == "clean", [f.code for f in portless.findings]

    envelope = _evaluate_recording(_args())  # no loop home provisioned -> MRS-GATE-017

    assert _codes(envelope) == ["MRS-GATE-017"]
    assert envelope.verdict.value == "clean"
    assert exit_code_for(envelope.verdict) == 0
    assert envelope.status == portless.status


@pytest.mark.parametrize(
    "exc",
    [FsError("cannot write /x: disk full"), TypeError("payload must be a Redacted instance, got str"), OSError("EIO")],
)
def test_a_failed_write_is_one_warn_the_verdict_unchanged(world, exc):
    _provision_home(world)
    baseline = _evaluate(_args())
    failing = _RaisingRecord(exc)

    envelope = _evaluate(_args(), record=failing, clock=_Clock())

    assert failing.calls == 1
    assert _codes(envelope).count("MRS-GATE-017") == 1
    assert envelope.data["gate_record"]["written"] is False
    assert _verdict_and_exit(envelope) == _verdict_and_exit(baseline)


def test_an_unreadable_tree_revision_writes_nothing_and_warns(world):
    tier3 = _provision_home(world)
    baseline = _evaluate(_args())
    recording = _RecordingRecord()

    envelope = _evaluate(_args(), record=recording, clock=_Clock(), vcs=_Vcs(head=None))

    assert recording.writes == []
    assert not (tier3 / "sessions").exists()
    assert _codes(envelope).count("MRS-GATE-017") == 1
    assert "tree revision" in envelope.data["gate_record"]["reason"]
    assert _verdict_and_exit(envelope) == _verdict_and_exit(baseline)


def test_a_tier3_path_that_is_not_a_directory_is_no_loop_home(world):
    tier3 = _tier3(world)
    tier3.parent.mkdir(parents=True)
    tier3.write_text("not a directory", encoding="utf-8")

    envelope = _evaluate_recording(_args())

    assert _codes(envelope).count("MRS-GATE-017") == 1
    assert envelope.data["gate_record"]["written"] is False


def test_the_failure_reason_never_carries_the_record_content(world):
    _provision_home(world)
    failing = _RaisingRecord(ValueError(f"bad payload {_SECRET}"))

    envelope = _evaluate(_args(), record=failing, clock=_Clock(), process=_Process(stdout=_SECRET))

    finding = next(f for f in envelope.findings if f.code == "MRS-GATE-017")
    # the failure's own text is the TYPE only -- never the exception message (or the content it was built from)
    assert _SECRET not in json.dumps(envelope.data["gate_record"])
    assert _SECRET not in finding.message
    assert "ValueError" in envelope.data["gate_record"]["reason"]


# --- when no record is asked for, none is written -----------------------------------------------------------------


def test_without_story_no_record_is_written_and_data_carries_no_gate_record(world):
    _provision_home(world)
    recording = _RecordingRecord()

    envelope = _evaluate(_args(story=None), record=recording, clock=_Clock())

    assert recording.writes == []
    assert "gate_record" not in envelope.data
    assert "MRS-GATE-017" not in _codes(envelope)


def test_an_unresolvable_story_writes_no_record(world):
    _provision_home(world)
    recording = _RecordingRecord()

    envelope = _evaluate(_args(story="not-a-story"), record=recording, clock=_Clock())

    assert recording.writes == []
    assert "gate_record" not in envelope.data


@pytest.mark.parametrize("ports", [{"record": None, "clock": _Clock()}, {"record": _RecordingRecord(), "clock": None}])
def test_both_ports_are_required_so_land_story_s_portless_rerun_writes_nothing(world, ports):
    _provision_home(world)

    envelope = _evaluate(_args(), **ports)

    assert "gate_record" not in envelope.data
    if ports["record"] is not None:
        assert ports["record"].writes == []


# --- run_evaluate: the real filesystem only ------------------------------------------------------------------------


class _Spy:
    """Captures what ``run_evaluate`` hands ``evaluate_gate`` and returns its real envelope-shaped result."""

    def __init__(self, monkeypatch) -> None:
        self.kwargs: dict = {}
        real = gate_module.evaluate_gate

        def spy(args, **kwargs):
            self.kwargs = kwargs
            return real(args, **kwargs)

        monkeypatch.setattr(gate_module, "evaluate_gate", spy)


class _FakeFs:
    """Not a ``LocalFs`` (so ``run_evaluate`` hands it no record port), yet it reads and writes like one."""

    def __init__(self) -> None:
        self.real = LocalFs()

    def __getattr__(self, name):
        return getattr(self.real, name)


def test_run_evaluate_wires_the_record_only_when_fs_is_a_local_fs(world, monkeypatch, capsys):
    _provision_home(world)
    spy = _Spy(monkeypatch)
    real_fs = LocalFs()

    gate_module.run_evaluate(_args(), process=_Process(), vcs=_Vcs(), fs=real_fs)

    assert spy.kwargs["record"] is real_fs
    assert spy.kwargs["clock"] is not None
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["gate_record"]["written"] is True

    gate_module.run_evaluate(_args(), process=_Process(), vcs=_Vcs(), fs=_FakeFs())

    assert spy.kwargs["record"] is None  # an injected fake fs writes nothing
    payload = json.loads(capsys.readouterr().out)
    assert "gate_record" not in payload["data"]


def test_run_evaluate_exit_code_is_the_gates_even_when_the_record_cannot_be_written(world, capsys):
    # no loop home: MRS-GATE-017 rides along; the exit code is what the portless gate returns
    portless = gate_module.run_evaluate(_args(), process=_Process(), vcs=_Vcs(), fs=_FakeFs())
    capsys.readouterr()
    text_args = _args()
    text_args.format = "text"
    recording = gate_module.run_evaluate(text_args, process=_Process(), vcs=_Vcs(), fs=LocalFs())
    out = capsys.readouterr().out

    assert recording == portless
    assert "MRS-GATE-017" in out  # the text projection names the finding...
    assert "gate record: not written" in out  # ...and the record's own line


def test_the_text_projection_names_the_written_record(world, capsys):
    _provision_home(world)
    args = _args()
    args.format = "text"

    gate_module.run_evaluate(args, process=_Process(), vcs=_Vcs(), fs=LocalFs())

    out = capsys.readouterr().out
    assert "gate record: " in out
    assert "(session namespace)" in out
    assert GATE_RECORD_FILENAME in out
