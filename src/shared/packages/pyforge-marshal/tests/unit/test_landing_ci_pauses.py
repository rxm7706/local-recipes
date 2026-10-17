"""Story 100.1 (CAP-292): CI pause surfaces recorded at dispatch landing merge time.

Story 101.1 (a fix under CAP-292): under the CI master switch, steward 103.1's
``paused_by_master`` row property adds every surface the master stopped.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest
from pyforge.core.process import ProcessError, ProcessResult
from pyforge.testing_kit.flags import flag_states

from pyforge.marshal.adapters.steward_cli import StewardCiStatusOutcome, StewardCli
from pyforge.marshal.core import policy
from pyforge.marshal.core.dispatch_landing import DispatchLandingVerdict
from pyforge.marshal.core.dispatch_verification import DispatchVerificationVerdict
from pyforge.marshal.core.identity import normalize
from pyforge.marshal.core.journal import CI_PAUSES_AT_MERGE_FIELD
from pyforge.marshal.core.landing_checks import CheckRun
from pyforge.marshal.core.landing_ci_pauses import (
    LANDING_CI_PAUSES_FLAG_KEY,
    append_ci_pauses_line_to_pr_body,
    envelope_is_valid,
    record_from_envelope,
    render_ci_pauses_pr_line,
    row_counts_as_paused_at_merge,
    surfaces_from_envelope,
    unknown_record,
)
from pyforge.marshal.core.model import Severity
from pyforge.marshal.dispatch_land import _dispatch_pr_body, execute_dispatch_land
from pyforge.marshal.ports.forge import ForgeCommandError


def _load_dispatch_landing_harness():
    path = Path(__file__).with_name("test_dispatch_landing.py")
    spec = importlib.util.spec_from_file_location("_dispatch_landing_harness", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_lh = _load_dispatch_landing_harness()
FakeProcess = _lh.FakeProcess
FakeVcs = _lh.FakeVcs
_FakeClock = _lh._FakeClock
_ChecksForge = _lh._ChecksForge
_GREEN = _lh._GREEN
_install_fake_spec_surface = _lh._install_fake_spec_surface


def _install_flag_tree(repo_root: Path, *, enabled: bool) -> None:
    config_dir = repo_root / "src/platform/config"
    config_dir.mkdir(parents=True, exist_ok=True)
    variant = "on" if enabled else "off"
    (config_dir / "flags.json").write_text(
        json.dumps(
            {
                "flags": {
                    LANDING_CI_PAUSES_FLAG_KEY: {
                        "state": "ENABLED",
                        "variants": {"on": True, "off": False},
                        "defaultVariant": variant,
                    }
                }
            }
        ),
        encoding="utf-8",
    )


def _land_with_ci_pauses(
    tmp_path: Path,
    forge: _ChecksForge,
    clock: _FakeClock,
    monkeypatch,
    *,
    process: FakeProcess | None = None,
):
    proc = process if process is not None else FakeProcess()
    _install_fake_spec_surface(monkeypatch, (), process=proc)
    worktree = tmp_path / "wt"
    worktree.mkdir(exist_ok=True)
    effective, findings = policy.compose(project_slug="pyforge-marshal", project={}, flags={})
    assert findings == ()
    return execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="80-1-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        effective=effective,
        vcs=FakeVcs(merged=False),
        forge=forge,
        process=proc,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )


def _sample_envelope() -> dict[str, Any]:
    return {
        "fetched_at": "2026-10-14T12:00:00Z",
        "repo": "rxm7706/local-recipes",
        "rate_limit": {"core_limit": 5000, "core_remaining": 4999},
        "rows": [
            {
                "id": "platform-ci.container",
                "declared_state": "paused",
                "live_switch_value": "true",
                "verdict": "paused",
            },
            {
                "id": "platform-ci.container-dbgpt",
                "declared_state": "paused",
                "live_switch_value": "true",
                "verdict": "overdue",
            },
            {
                "id": "station-tests.guild-container",
                "declared_state": "paused",
                "live_switch_value": "true",
                "verdict": "paused",
            },
            {
                "id": "wf.manual",
                "declared_state": "paused-manually",
                "live_switch_value": None,
                "verdict": "paused-manually",
            },
            {"id": "opt.in", "declared_state": "opt-in-off", "live_switch_value": "true", "verdict": "opt-in-off"},
            {
                "id": "platform-ci.registry",
                "declared_state": "live",
                "live_switch_value": "https://example",
                "verdict": "live",
            },
            {"id": "lint", "declared_state": "live", "live_switch_value": "false", "verdict": "live"},
            {
                "id": "unregistered:PAUSE_FOO",
                "declared_state": "drift",
                "live_switch_value": "true",
                "verdict": "drift",
            },
        ],
    }


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"id": "a", "declared_state": "paused", "live_switch_value": "true"}, True),
        ({"id": "b", "declared_state": "paused", "live_switch_value": "true", "verdict": "overdue"}, True),
        ({"id": "c", "declared_state": "paused-manually", "live_switch_value": None}, True),
        ({"id": "d", "declared_state": "opt-in-off", "live_switch_value": "true"}, False),
        ({"id": "e", "declared_state": "live", "live_switch_value": "https://x"}, False),
        ({"id": "f", "declared_state": "retired", "live_switch_value": "true"}, False),
        ({"id": "unregistered:X", "declared_state": "drift", "live_switch_value": "true"}, False),
        ({"id": "g", "declared_state": "live", "live_switch_value": "TRUE "}, True),
    ],
)
def test_row_listing_rule(row: dict[str, Any], expected: bool) -> None:
    assert row_counts_as_paused_at_merge(row) is expected


def test_ac1_envelope_produces_sorted_four_paused_surfaces() -> None:
    record = record_from_envelope(_sample_envelope())
    assert record == {
        "state": "read",
        "surfaces": [
            "platform-ci.container",
            "platform-ci.container-dbgpt",
            "station-tests.guild-container",
            "wf.manual",
        ],
        "fetched_at": "2026-10-14T12:00:00Z",
    }


def test_ac2_empty_surfaces_and_pr_line() -> None:
    env = {
        "fetched_at": "t",
        "repo": "r",
        "rate_limit": {"core_limit": 1, "core_remaining": 1},
        "rows": [{"id": "lint", "declared_state": "live", "live_switch_value": "false", "verdict": "live"}],
    }
    record = record_from_envelope(env)
    assert record["surfaces"] == []
    assert render_ci_pauses_pr_line(record) == "CI paused at merge: none"


class _StewardProcess:
    def __init__(self, *, stdout: str = "", stderr: str = "", returncode: int = 0, raise_timeout: bool = False):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.raise_timeout = raise_timeout

    def run(self, argv, *, cwd: Path, timeout_s: float | None = None):
        if self.raise_timeout:
            raise ProcessError("timed out")
        return ProcessResult(returncode=self.returncode, stdout=self.stdout, stderr=self.stderr)


class _BodyRecordingForge(_ChecksForge):
    def __init__(self, *steps: object) -> None:
        super().__init__(*steps)
        self.bodies: list[str] = []

    def update_pr(self, repo, number, title, body):
        self.bodies.append(body.text if hasattr(body, "text") else str(body))
        return super().update_pr(repo, number, title, body)


@flag_states("pyforge.marshal.landing_ci_pauses")
def test_ac7_flag_on_records_and_updates_pr_body(tmp_path: Path, monkeypatch, flag_provider: dict[str, bool]) -> None:
    enabled = flag_provider["pyforge.marshal.landing_ci_pauses"]
    _install_flag_tree(tmp_path, enabled=enabled)
    sample = _sample_envelope()

    def _fake_record(self, **kwargs):
        if not enabled:
            raise AssertionError("steward must not run when flag off")
        return record_from_envelope(sample)

    monkeypatch.setattr("pyforge.marshal.dispatch_land.StewardCli.ci_status_record", _fake_record)
    forge = _BodyRecordingForge(_GREEN)
    clock = _FakeClock()
    result, envelope = _land_with_ci_pauses(tmp_path, forge, clock, monkeypatch)
    assert result.verdict == DispatchLandingVerdict.LANDED
    base_text = _dispatch_pr_body(normalize("80-1-example")).text
    if enabled:
        assert envelope.data[CI_PAUSES_AT_MERGE_FIELD]["state"] == "read"
        assert len(envelope.data[CI_PAUSES_AT_MERGE_FIELD]["surfaces"]) == 4
        assert forge.bodies[-1] == append_ci_pauses_line_to_pr_body(base_text, envelope.data[CI_PAUSES_AT_MERGE_FIELD])
    else:
        assert CI_PAUSES_AT_MERGE_FIELD not in envelope.data
        assert all("CI paused at merge" not in b for b in forge.bodies)


def test_ac3_unknown_on_steward_refusal_still_lands(tmp_path: Path, monkeypatch) -> None:
    _install_flag_tree(tmp_path, enabled=True)
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land.StewardCli.ci_status_record",
        lambda self, **kwargs: {"state": "unknown", "reason": "steward ci status refused (exit 3): flag off"},
    )
    forge = _BodyRecordingForge(_GREEN)
    clock = _FakeClock()
    result, envelope = _land_with_ci_pauses(tmp_path, forge, clock, monkeypatch)
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert envelope.data[CI_PAUSES_AT_MERGE_FIELD]["state"] == "unknown"
    assert "CI paused at merge: unknown" in forge.bodies[-1]


def test_ac4_update_pr_failure_warns_and_lands(tmp_path: Path, monkeypatch) -> None:
    _install_flag_tree(tmp_path, enabled=True)

    class _FailUpdateForge(_BodyRecordingForge):
        def update_pr(self, repo, number, title, body):
            text = body.value if hasattr(body, "value") else str(body)
            if "CI paused at merge" in text:
                raise ForgeCommandError("rate limited")
            return super().update_pr(repo, number, title, body)

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land.StewardCli.ci_status_record",
        lambda self, **kwargs: record_from_envelope(_sample_envelope()),
    )
    forge = _FailUpdateForge(_GREEN)
    clock = _FakeClock()
    result, envelope = _land_with_ci_pauses(tmp_path, forge, clock, monkeypatch)
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert any(f.code == "MRS-DISP-066" and f.severity is Severity.WARN for f in envelope.findings)


def test_ac5_check_refusal_skips_steward(tmp_path: Path, monkeypatch) -> None:
    _install_flag_tree(tmp_path, enabled=True)
    calls: list[str] = []

    def _record(self, **kwargs):
        calls.append("steward")
        return record_from_envelope(_sample_envelope())

    monkeypatch.setattr("pyforge.marshal.dispatch_land.StewardCli.ci_status_record", _record)
    forge = _ChecksForge((CheckRun(name="Lint / ruff", status="completed", conclusion="failure"),))
    clock = _FakeClock()
    result, envelope = _land_with_ci_pauses(tmp_path, forge, clock, monkeypatch)
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert calls == []
    assert CI_PAUSES_AT_MERGE_FIELD not in envelope.data


def test_steward_cli_unknown_paths() -> None:
    assert StewardCli(_StewardProcess()).ci_status_record(repo_root=Path("/tmp")).get("state") == "unknown"
    assert (
        StewardCli(_StewardProcess(returncode=1, stderr="partial\n")).ci_status_record(repo_root=Path("/tmp"))["state"]
        == "unknown"
    )
    assert StewardCli(_StewardProcess(stdout="not json")).ci_status_record(repo_root=Path("/tmp"))["state"] == "unknown"
    assert StewardCli(_StewardProcess(stdout="{}")).ci_status_record(repo_root=Path("/tmp"))["state"] == "unknown"


def test_steward_cli_success_and_resolve_binary(tmp_path: Path, monkeypatch) -> None:
    envelope_json = json.dumps(_sample_envelope())
    cli = StewardCli(_StewardProcess(stdout=envelope_json))
    outcome = cli.ci_status(repo_root=tmp_path, binary_path="/bin/false")
    assert outcome.ok is True
    assert outcome.envelope is not None
    assert cli.ci_status_record(repo_root=tmp_path, binary_path="/bin/false")["state"] == "read"

    monkeypatch.setattr("shutil.which", lambda _: None)
    bin_dir = tmp_path / ".pixi/envs/pyforge-steward/bin"
    bin_dir.mkdir(parents=True)
    pyforge = bin_dir / "pyforge"
    pyforge.write_text("#!/bin/sh\n", encoding="utf-8")
    pyforge.chmod(0o755)
    assert cli.resolve_binary(tmp_path) == str(pyforge)
    assert cli.resolve_binary(None) is None


def test_steward_cli_timeout_and_refusal(tmp_path: Path, monkeypatch) -> None:
    cli = StewardCli(_StewardProcess(raise_timeout=True))
    outcome = cli.ci_status(repo_root=Path("/tmp"), binary_path="/bin/true")
    assert outcome.ok is False
    assert outcome.reason and "timed out" in outcome.reason

    cli2 = StewardCli(_StewardProcess(returncode=3, stderr="flag off\n"))
    outcome = cli2.ci_status(repo_root=Path("/tmp"), binary_path="/bin/true")
    assert outcome.ok is False
    assert "exit 3" in (outcome.reason or "")

    cli3 = StewardCli(_StewardProcess())
    monkeypatch.setattr(cli3, "resolve_binary", lambda *args, **kwargs: None)
    outcome = cli3.ci_status(repo_root=tmp_path, binary_path=None)
    assert outcome.ok is False
    assert outcome.reason and "no pyforge binary" in outcome.reason


def test_envelope_is_valid_and_pr_render_helpers() -> None:
    assert envelope_is_valid(_sample_envelope()) is True
    assert envelope_is_valid({"rows": []}) is False
    assert unknown_record("x")["reason"] == "x"
    record = record_from_envelope(_sample_envelope())
    line = render_ci_pauses_pr_line(record)
    assert line.startswith("CI paused at merge:")
    assert append_ci_pauses_line_to_pr_body("body", record).startswith("body\n")
    assert render_ci_pauses_pr_line({"state": "unknown", "reason": "r"}) == "CI paused at merge: unknown (r)"
    assert render_ci_pauses_pr_line({"state": "bad"}) == "CI paused at merge: unknown (invalid record)"


def test_finalize_ac6_invalid_json_becomes_unknown() -> None:
    from pyforge.marshal.dispatch_land_finalize.__main__ import _parse_ci_pauses_at_merge_arg

    parsed = _parse_ci_pauses_at_merge_arg("{not-json")
    assert parsed == {"state": "unknown", "reason": "finalize could not parse the landing's record"}


def test_surfaces_from_envelope_never_uses_verdict_alone() -> None:
    env = {
        "fetched_at": "t",
        "repo": "r",
        "rate_limit": {"core_limit": 1, "core_remaining": 1},
        "rows": [{"id": "x", "declared_state": "opt-in-off", "live_switch_value": "false", "verdict": "paused"}],
    }
    assert surfaces_from_envelope(env) == []


def test_steward_cli_partial_envelope_on_stdout_is_a_read_carrying_partial() -> None:
    """Steward Story 103.7 AC5: exit 1 with a valid envelope on stdout is a partial read, not unknown."""
    complete = _sample_envelope()
    partial = {**complete, "partial": True, "run_list_errors": [".github/workflows/x.yml: HTTP 404"]}

    read = StewardCli(_StewardProcess(stdout=json.dumps(complete))).ci_status_record(
        repo_root=Path("/tmp"), binary_path="/bin/true"
    )
    assert read["state"] == "read"
    assert "partial" not in read

    partial_read = StewardCli(_StewardProcess(returncode=1, stdout=json.dumps(partial))).ci_status_record(
        repo_root=Path("/tmp"), binary_path="/bin/true"
    )
    assert partial_read["state"] == "read"
    assert partial_read["partial"] is True
    assert partial_read["surfaces"] == read["surfaces"]
    assert render_ci_pauses_pr_line(partial_read) == render_ci_pauses_pr_line(read)

    on_stderr_only = StewardCli(_StewardProcess(returncode=1, stderr=json.dumps(partial))).ci_status_record(
        repo_root=Path("/tmp"), binary_path="/bin/true"
    )
    assert on_stderr_only["state"] == "unknown"
    assert "partial read (exit 1)" in on_stderr_only["reason"]
    not_envelope = StewardCli(_StewardProcess(returncode=1, stdout="{}")).ci_status_record(
        repo_root=Path("/tmp"), binary_path="/bin/true"
    )
    assert not_envelope["state"] == "unknown"


# ---------------------------------------------------------------------------
# Story 101.1: the master switch's surfaces, read from steward's ``paused_by_master``
# ---------------------------------------------------------------------------

# tests/unit -> tests -> pyforge-marshal -> packages: steward 103.1's AC6 fixture, read as a file, never imported.
_STEWARD_MASTER_ON_FIXTURE = (
    Path(__file__).resolve().parents[3] / "pyforge-steward" / "tests" / "fixtures" / "ci_status_master_on.json"
)

_MASTER_ROW: dict[str, Any] = {
    "id": "master:PAUSE_ALL_CI",
    "declared_state": "live",
    "live_switch_value": "true",
    "verdict": "drift",
    "paused_by_master": False,
}

# AC1: each of these is listed while the master is on.
_MASTER_LISTED_ROWS: tuple[dict[str, Any], ...] = (
    _MASTER_ROW,
    {
        "id": "gated.live-paused",
        "declared_state": "live",
        "live_switch_value": None,
        "verdict": "paused",
        "paused_by_master": True,
    },
    {
        "id": "gated.live-stuck",
        "declared_state": "live",
        "live_switch_value": "false",
        "verdict": "stuck",
        "paused_by_master": True,
    },
    {
        "id": "gated.paused-overdue",
        "declared_state": "paused",
        "live_switch_value": "true",
        "verdict": "overdue",
        "paused_by_master": True,
    },
    {
        "id": "gated.live-drift",
        "declared_state": "live",
        "live_switch_value": "true",
        "verdict": "drift",
        "paused_by_master": True,
    },
    {
        "id": "gated.opt-in-on",
        "declared_state": "opt-in-off",
        "live_switch_value": "true",
        "verdict": "drift",
        "paused_by_master": True,
    },
    {
        # Review nit 2: the opt-in clause strips and lower-cases the switch, as Story 100.1's own-switch path does.
        "id": "gated.opt-in-on-padded",
        "declared_state": "opt-in-off",
        "live_switch_value": " TRUE ",
        "verdict": "drift",
        "paused_by_master": True,
    },
)

# AC2: none of these is listed, in the same envelope.
_MASTER_UNLISTED_ROWS: tuple[dict[str, Any], ...] = (
    {
        # Review nit 1: an opt-in that is off is left out by its declared state and switch, never by its verdict
        # (the spec's rejected design, `verdict != "opt-in-off"`, would list this stuck one).
        "id": "gated.opt-in-off-stuck",
        "declared_state": "opt-in-off",
        "live_switch_value": "false",
        "verdict": "stuck",
        "paused_by_master": True,
    },
    {
        "id": "gated.opt-in-off-false",
        "declared_state": "opt-in-off",
        "live_switch_value": "false",
        "verdict": "opt-in-off",
        "paused_by_master": True,
    },
    {
        "id": "gated.opt-in-off-null",
        "declared_state": "opt-in-off",
        "live_switch_value": None,
        "verdict": "opt-in-off",
        "paused_by_master": True,
    },
    {
        "id": "ungated.live",
        "declared_state": "live",
        "live_switch_value": "false",
        "verdict": "live",
        "paused_by_master": False,
    },
    {
        "id": "gated.retired",
        "declared_state": "retired",
        "live_switch_value": "true",
        "verdict": "retired",
        "paused_by_master": True,
    },
    {
        "id": "unregistered:PAUSE_FOO",
        "declared_state": "drift",
        "live_switch_value": "true",
        "verdict": "drift",
        "paused_by_master": True,
    },
    {
        "id": "field.string-true",
        "declared_state": "live",
        "live_switch_value": "false",
        "verdict": "live",
        "paused_by_master": "true",
    },
    {
        "id": "field.int-one",
        "declared_state": "live",
        "live_switch_value": "false",
        "verdict": "live",
        "paused_by_master": 1,
    },
    {
        "id": "field.null",
        "declared_state": "live",
        "live_switch_value": None,
        "verdict": "live",
        "paused_by_master": None,
    },
)

_MASTER_LISTED_IDS: list[str] = sorted(str(row["id"]) for row in _MASTER_LISTED_ROWS)


def _master_on_envelope() -> dict[str, Any]:
    """AC1's envelope: the listed rows and AC2's unlisted rows, interleaved, the master ``true``."""
    rows: list[dict[str, Any]] = []
    for listed, unlisted in zip(_MASTER_LISTED_ROWS, _MASTER_UNLISTED_ROWS, strict=False):
        rows += [dict(unlisted), dict(listed)]
    rows += [dict(row) for row in _MASTER_UNLISTED_ROWS[len(_MASTER_LISTED_ROWS) :]]
    return {
        "fetched_at": "2026-10-17T09:00:00Z",
        "repo": "rxm7706/local-recipes",
        "rate_limit": {"core_limit": 5000, "core_remaining": 4998},
        "rows": rows,
    }


def _listed_by_story_100_1(row: dict[str, Any]) -> bool:
    """Story 100.1's rule alone: the row as a steward before 103.1 would send it."""
    return row_counts_as_paused_at_merge({k: v for k, v in row.items() if k != "paused_by_master"})


@pytest.mark.parametrize(
    ("row", "expected"),
    [pytest.param(row, True, id=str(row["id"])) for row in _MASTER_LISTED_ROWS]
    + [pytest.param(row, False, id=str(row["id"])) for row in _MASTER_UNLISTED_ROWS]
    + [
        pytest.param(
            {
                "id": "row.manual",
                "declared_state": "paused-manually",
                "live_switch_value": None,
                "paused_by_master": False,
            },
            True,
            id="paused-manually",
        ),
        pytest.param(
            {"id": "row.retired", "declared_state": "retired", "live_switch_value": None, "paused_by_master": False},
            False,
            id="retired-ungated",
        ),
        pytest.param(
            {"id": "row.value", "declared_state": "live", "live_switch_value": "https://x", "paused_by_master": False},
            False,
            id="value-row",
        ),
        pytest.param(
            {"id": "unregistered-workflow:x.yml", "declared_state": "drift", "paused_by_master": True},
            False,
            id="unregistered-workflow",
        ),
    ],
)
def test_101_1_row_rule_under_the_master_switch(row: dict[str, Any], expected: bool) -> None:
    """AC1/AC2: each row kind of the I/O matrix, alone."""
    assert row_counts_as_paused_at_merge(row) is expected


def test_101_1_ac1_master_surfaces_are_listed_sorted_once() -> None:
    surfaces = surfaces_from_envelope(_master_on_envelope())
    assert surfaces == _MASTER_LISTED_IDS
    assert len(surfaces) == len(set(surfaces))
    assert "master:PAUSE_ALL_CI" in surfaces


def test_101_1_ac2_unlisted_rows_stay_out_of_the_same_envelope() -> None:
    surfaces = set(surfaces_from_envelope(_master_on_envelope()))
    for row in _MASTER_UNLISTED_ROWS:
        assert row["id"] not in surfaces, row


def test_101_1_ac3_no_field_or_false_field_keeps_story_100_1_record() -> None:
    """AC3: no existing envelope carries the field, and the master off (``false`` on every row) changes nothing."""
    sample = _sample_envelope()
    assert all("paused_by_master" not in row for row in sample["rows"])
    master_off = {**sample, "rows": [{**row, "paused_by_master": False} for row in sample["rows"]]}
    assert record_from_envelope(master_off) == record_from_envelope(sample)


def test_101_1_ac4_journal_record_and_pr_line_agree(tmp_path: Path, monkeypatch) -> None:
    _install_flag_tree(tmp_path, enabled=True)
    master_on = _master_on_envelope()
    calls: list[Path] = []

    def _fake_ci_status(self, *, repo_root: Path, binary_path: str | None = None) -> StewardCiStatusOutcome:
        calls.append(repo_root)
        return StewardCiStatusOutcome(ok=True, envelope=master_on, argv=("pyforge", "steward", "ci", "status"))

    monkeypatch.setattr("pyforge.marshal.dispatch_land.StewardCli.ci_status", _fake_ci_status)
    forge = _BodyRecordingForge(_GREEN)
    clock = _FakeClock()
    result, envelope = _land_with_ci_pauses(tmp_path, forge, clock, monkeypatch)
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert len(calls) == 1
    record = envelope.data[CI_PAUSES_AT_MERGE_FIELD]
    assert record == {"state": "read", "surfaces": _MASTER_LISTED_IDS, "fetched_at": "2026-10-17T09:00:00Z"}
    body = forge.bodies[-1]
    assert body.count("CI paused at merge:") == 1
    assert body.endswith("\nCI paused at merge: " + ", ".join(_MASTER_LISTED_IDS))


def test_101_1_ac5_steward_master_on_fixture() -> None:
    """AC5: steward 103.1's checked-in payload, read as a file; a missing file fails, never skips."""
    assert _STEWARD_MASTER_ON_FIXTURE.is_file(), f"steward 103.1's fixture is missing: {_STEWARD_MASTER_ON_FIXTURE}"
    payload = json.loads(_STEWARD_MASTER_ON_FIXTURE.read_text(encoding="utf-8"))
    assert envelope_is_valid(payload) is True
    rows = [row for row in payload["rows"] if isinstance(row, dict)]
    surfaces = surfaces_from_envelope(payload)
    assert surfaces == sorted(set(surfaces))
    assert "master:PAUSE_ALL_CI" in surfaces
    gated_paused = [row["id"] for row in rows if row.get("verdict") == "paused" and row.get("paused_by_master") is True]
    assert gated_paused, "the fixture holds no gated paused row; the check below would be vacuous"
    for row_id in gated_paused:
        assert row_id in surfaces, row_id
    ungated = [row for row in rows if row.get("paused_by_master") is False]
    assert ungated, "the fixture holds no ungated row; the check below would be vacuous"
    for row in ungated:
        assert (row["id"] in surfaces) is _listed_by_story_100_1(row), row


# Review nit 4: a row with no usable id names no surface; it is skipped, never a KeyError out of the landing.
_ROWS_WITHOUT_AN_ID: tuple[dict[str, Any], ...] = (
    {"declared_state": "paused-manually", "live_switch_value": None, "verdict": "paused-manually"},
    {"declared_state": "live", "live_switch_value": None, "verdict": "paused", "paused_by_master": True},
    {"id": "", "declared_state": "live", "live_switch_value": None, "verdict": "paused", "paused_by_master": True},
    {"id": None, "declared_state": "paused", "live_switch_value": "true", "verdict": "paused"},
    {"id": 7, "declared_state": "live", "live_switch_value": None, "verdict": "paused", "paused_by_master": True},
)


@pytest.mark.parametrize("row", [pytest.param(row, id=f"row-{n}") for n, row in enumerate(_ROWS_WITHOUT_AN_ID)])
def test_101_1_a_row_without_a_string_id_is_skipped(row: dict[str, Any]) -> None:
    assert row_counts_as_paused_at_merge(row) is False


def test_101_1_rows_without_an_id_never_raise_out_of_the_record() -> None:
    envelope = _master_on_envelope()
    envelope["rows"] = [dict(row) for row in _ROWS_WITHOUT_AN_ID] + envelope["rows"]
    assert surfaces_from_envelope(envelope) == _MASTER_LISTED_IDS
    record = StewardCli(_StewardProcess(stdout=json.dumps(envelope))).ci_status_record(
        repo_root=Path("/tmp"), binary_path="/bin/true"
    )
    assert record == {"state": "read", "surfaces": _MASTER_LISTED_IDS, "fetched_at": "2026-10-17T09:00:00Z"}


# Review nit 3, AC6's second half as a standing test: marshal's own src/ names neither the master switch nor the
# registry (steward is the one reader of the pause state). tests/unit -> tests -> pyforge-marshal.
_MARSHAL_SRC = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "marshal"


def test_101_1_ac6_no_marshal_src_module_names_the_master_switch_or_the_registry() -> None:
    modules = sorted(_MARSHAL_SRC.rglob("*.py"))
    assert _MARSHAL_SRC / "core" / "landing_ci_pauses.py" in modules, "the scan found no marshal src; it is vacuous"
    offenders = [
        f"{path.relative_to(_MARSHAL_SRC).as_posix()}: {name}"
        for path in modules
        for name in ("PAUSE_ALL_CI", "ci-surfaces.yaml")
        if name in path.read_text(encoding="utf-8")
    ]
    assert offenders == []
