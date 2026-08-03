"""Unit tests for ``pyforge.marshal.cli.spin`` (Story 3.3, FR-9/FR-17,
AD-3/AD-6/AD-22/AD-25/AD-38) -- ``run_spin``/``run_attach``'s orchestration
against the I/O & Edge-Case Matrix, driven entirely through FAKE
``FsPort``/``HarnessPort`` implementations (no real filesystem/subprocess
I/O -- that lives in ``test_harness_bmadloop_spin.py`` and the spec's own
manual check). Every fake call is recorded in ``.calls`` so "no I/O
attempted" scenarios (a malformed slug, an unprovisioned home) can be
asserted exactly, mirroring ``test_init.py``'s own ``FakeVcs``/``FakeFs``
convention.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import jsonschema
import pytest
from pyforge.marshal.adapters.fs_local import FsError
from pyforge.marshal.adapters.harness_bmadloop import HarnessError
from pyforge.marshal.cli.spin import _non_negative_int, run_attach, run_spin
from pyforge.marshal.core.verdict import EXIT_OK
from pyforge.marshal.ports.harness import SpinResult

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "pyforge"
    / "marshal"
    / "schemas"
    / "envelope.v1.json"
)


class FakeFs:
    """Fakes just enough of ``FsPort`` for ``run_spin``/``run_attach`` to
    reach every write path: ``is_dir`` (the loop-home-provisioned gate),
    ``ensure_dir``/``create_dir_exclusive`` (the run directory), and
    ``append_line``/``write_text_atomic`` (the journal + any sidecar
    blob)."""

    def __init__(self, *, dirs: set[Path] | None = None, events: list[str] | None = None) -> None:
        self.dirs: set[Path] = set(dirs or set())
        self.calls: list[str] = []
        self._events = events if events is not None else []
        self.created_dirs: list[Path] = []
        self.ensure_dir_calls: list[Path] = []
        self.appended_lines: list[tuple[Path, str, bool]] = []
        self.written_texts: dict[Path, str] = {}
        self.fail_create_dir_exclusive: Exception | None = None
        self.fail_append_line: Exception | None = None
        # 1-indexed: e.g. 2 fails only the SECOND append_line call (the
        # outcome entry), letting the first (the intent entry) succeed --
        # needed to test the "spawn succeeded, only the outcome write
        # failed" MRS-SPIN-006 path distinctly from "nothing was ever
        # written" (fail_append_line above, unconditional).
        self.fail_append_line_on_call: int | None = None
        self._append_line_call_count = 0

    def is_dir(self, path: Path) -> bool:
        self.calls.append("is_dir")
        return path in self.dirs

    def ensure_dir(self, path: Path) -> None:
        self.calls.append("ensure_dir")
        self.ensure_dir_calls.append(path)
        self.dirs.add(path)

    def create_dir_exclusive(self, path: Path) -> None:
        self.calls.append("create_dir_exclusive")
        self._events.append("create_dir_exclusive")
        if self.fail_create_dir_exclusive:
            raise self.fail_create_dir_exclusive
        self.created_dirs.append(path)
        self.dirs.add(path)

    def append_line(self, path: Path, line: str, *, fsync: bool) -> None:
        self.calls.append("append_line")
        self._events.append("append_line")
        self._append_line_call_count += 1
        if self.fail_append_line:
            raise self.fail_append_line
        if self.fail_append_line_on_call == self._append_line_call_count:
            raise FsError(f"simulated failure on append_line call #{self._append_line_call_count}")
        self.appended_lines.append((path, line, fsync))

    def write_text_atomic(self, path: Path, content: str) -> None:
        self.calls.append("write_text_atomic")
        self.written_texts[path] = content


class FakeHarness:
    """Fakes ``HarnessPort``'s Story 3.3 methods (``story_feed_error``,
    ``story_feed_keys``, ``spin``, ``attach``, ``run_foreground``) --
    ``run_spin``/``run_attach`` never call any of the other seven methods
    on the Protocol, so this fake implements only what it needs, mirroring
    ``test_init.py``'s own ``FakeHarness`` convention of a per-story-scoped
    fake."""

    def __init__(self, *, events: list[str] | None = None) -> None:
        self._events = events if events is not None else []
        self.calls: list[str] = []
        self.feed_error: str | None = None
        self.feed_keys: tuple[str, ...] = ()
        self.spin_result: SpinResult = SpinResult(
            pid=4242, harness_run_id="acme-20260803T054512123Z-ab12cd"
        )
        self.fail_spin: Exception | None = None
        self.spin_calls: list[dict[str, object]] = []
        self.attach_result: int = 0
        self.fail_attach: Exception | None = None
        self.attach_calls: list[Path] = []
        self.foreground_result: int = 0
        self.fail_run_foreground: Exception | None = None
        self.foreground_calls: list[dict[str, object]] = []

    def story_feed_error(self, project: Path) -> str | None:
        self.calls.append("story_feed_error")
        return self.feed_error

    def story_feed_keys(self, project: Path) -> tuple[str, ...]:
        self.calls.append("story_feed_keys")
        return self.feed_keys

    def spin(
        self,
        project: Path,
        *,
        epic: int | None,
        story: str | None,
        max_count: int | None,
        log_path: Path,
    ) -> SpinResult:
        self.calls.append("spin")
        self._events.append("spin")
        self.spin_calls.append(
            {
                "project": project,
                "epic": epic,
                "story": story,
                "max_count": max_count,
                "log_path": log_path,
            }
        )
        if self.fail_spin:
            raise self.fail_spin
        return self.spin_result

    def attach(self, project: Path) -> int:
        self.calls.append("attach")
        self.attach_calls.append(project)
        if self.fail_attach:
            raise self.fail_attach
        return self.attach_result

    def run_foreground(
        self,
        project: Path,
        *,
        epic: int | None,
        story: str | None,
        max_count: int | None,
    ) -> int:
        self.calls.append("run_foreground")
        self.foreground_calls.append(
            {"project": project, "epic": epic, "story": story, "max_count": max_count}
        )
        if self.fail_run_foreground:
            raise self.fail_run_foreground
        return self.foreground_result


@pytest.fixture(autouse=True)
def _sandbox_loop_home_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test drives ``cli/init.py``'s pure home-path arithmetic (reused
    by ``cli/spin.py`` via ``_home_path``) through the real
    ``BMAD_LOOP_HOME_ROOT`` env-var read -- pinned under ``tmp_path``,
    mirroring ``test_init.py``'s own identical fixture."""
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))


@pytest.fixture
def home(tmp_path: Path) -> Path:
    return tmp_path / "loop-homes" / "acme"


def _spin_namespace(
    slug: str,
    *,
    epic: int | None = None,
    story: str | None = None,
    max_count: int | None = None,
    foreground: bool = False,
    fmt: str = "text",
) -> argparse.Namespace:
    return argparse.Namespace(
        slug=slug,
        epic=epic,
        story=story,
        max_count=max_count,
        foreground=foreground,
        format=fmt,
    )


def _attach_namespace(slug: str) -> argparse.Namespace:
    return argparse.Namespace(slug=slug)


# --- happy path, whole feed ----------------------------------------------------


def test_spin_happy_path_mints_run_id_journals_and_spawns(home, capsys):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story", "1-2-second-story")

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness)

    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "feed: resolved 2 of 2" in out
    assert "1.1" in out and "1.2" in out
    assert "pid: 4242" in out
    assert "harness_run_id: acme-20260803T054512123Z-ab12cd" in out

    # Exactly one spin() call, against the resolved home.
    [spin_call] = harness.spin_calls
    assert spin_call["project"] == home
    assert spin_call["epic"] is None
    assert spin_call["story"] is None
    assert spin_call["max_count"] is None

    # Exactly two journal appends: intent (fsync=True) then outcome (fsync=False).
    assert len(fs.appended_lines) == 2
    (intent_path, intent_line, intent_fsync), (outcome_path, outcome_line, outcome_fsync) = (
        fs.appended_lines
    )
    assert intent_path == outcome_path
    assert intent_fsync is True
    assert outcome_fsync is False

    intent = json.loads(intent_line)
    outcome = json.loads(outcome_line)
    assert intent["kind"] == "run-launch"
    assert intent["phase"] == "intent"
    assert intent["payload"]["preview"] == ["1.1", "1.2"]
    assert intent["payload"]["epic"] is None
    assert intent["id"]["writer_id"].startswith("spin-")
    assert intent["id"]["counter"] == 0

    assert outcome["kind"] == "run-launch"
    assert outcome["phase"] == "outcome"
    assert outcome["intent_id"] == intent["id"]
    assert outcome["id"]["counter"] == 1
    assert outcome["payload"] == {"pid": 4242, "harness_run_id": "acme-20260803T054512123Z-ab12cd"}
    assert outcome["run_id"] == intent["run_id"]
    assert intent["run_id"].startswith("acme-")


def test_spin_writes_the_run_directory_under_the_local_tier3_store(home):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-a",)

    run_spin(_spin_namespace("acme"), fs=fs, harness=harness)

    [run_dir] = fs.created_dirs
    tier3_runs = home / "_bmad-output" / "projects" / "acme" / "implementation-artifacts" / "runs"
    assert run_dir.parent == tier3_runs
    assert fs.ensure_dir_calls == [tier3_runs]


def test_spin_journals_the_intent_before_calling_harness_spin(home):
    events: list[str] = []
    fs = FakeFs(dirs={home}, events=events)
    harness = FakeHarness(events=events)
    harness.feed_keys = ("1-1-a",)

    run_spin(_spin_namespace("acme"), fs=fs, harness=harness)

    spin_index = events.index("spin")
    first_append_index = events.index("append_line")
    assert first_append_index < spin_index


# --- --epic/--story/--max-count composed ---------------------------------------


def test_spin_composed_selectors_filter_the_preview_and_pass_through(home):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-a", "1-2-b", "2-1-c")

    exit_code = run_spin(
        _spin_namespace("acme", epic=1, story="1-2", max_count=5), fs=fs, harness=harness
    )

    assert exit_code == EXIT_OK
    [spin_call] = harness.spin_calls
    assert spin_call["epic"] == 1
    assert spin_call["story"] == "1-2"
    assert spin_call["max_count"] == 5

    intent = json.loads(fs.appended_lines[0][1])
    # epic=1 narrows to {1-1-a, 1-2-b}; story="1-2" normalizes to StoryKey(1,2)
    # and matches only 1-2-b; max_count=5 is a no-op on a 1-element list.
    assert intent["payload"]["preview"] == ["1.2"]
    assert intent["payload"]["epic"] == 1
    assert intent["payload"]["story"] == "1-2"
    assert intent["payload"]["max_count"] == 5


def test_spin_unparseable_story_selector_previews_empty_without_raising(home):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-a",)

    exit_code = run_spin(
        _spin_namespace("acme", story="some-slug-fragment"), fs=fs, harness=harness
    )

    # Never pre-refuses on a zero-count preview (the spec's own Never
    # clause) -- the launch still proceeds.
    assert exit_code == EXIT_OK
    intent = json.loads(fs.appended_lines[0][1])
    assert intent["payload"]["preview"] == []
    assert harness.spin_calls  # the launch still happened


# --- one raw feed key fails normalize() -----------------------------------------


def test_spin_unresolved_feed_key_refuses_the_launch_with_no_journal_entries(home, capsys):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-good", "not-a-valid-key-at-all")

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness)

    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-IDENT-001" in out
    assert fs.created_dirs == []
    assert fs.appended_lines == []
    assert harness.spin_calls == []


# --- loop home not provisioned ---------------------------------------------------


def test_spin_loop_home_not_provisioned(capsys):
    fs = FakeFs()  # home is NOT registered as a dir
    harness = FakeHarness()

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness)

    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-SPIN-002" in out
    assert harness.calls == []


# --- malformed slug: rejected before any I/O -------------------------------------


@pytest.mark.parametrize("slug", ["../escaped-dir", "/etc", "a/b", "..", "."])
def test_spin_malformed_slug_rejected_before_any_io(slug, capsys):
    fs = FakeFs()
    harness = FakeHarness()

    exit_code = run_spin(_spin_namespace(slug), fs=fs, harness=harness)

    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-SPIN-001" in out
    assert fs.calls == []
    assert harness.calls == []


# --- story feed missing/unparseable -----------------------------------------------


def test_spin_story_feed_error_refuses_the_launch(home, capsys):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_error = "sprint status file not found: sprint-status.yaml"

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness)

    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-SPIN-005" in out
    assert harness.calls == ["story_feed_error"]
    assert fs.created_dirs == []


# --- detached spawn cannot launch -------------------------------------------------


def test_spin_detached_launch_failure_journals_a_failed_outcome(home, capsys):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-a",)
    harness.fail_spin = HarnessError("bmad-loop binary not found")

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness)

    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-SPIN-003" in out
    # run id already minted and directory already created.
    assert len(fs.created_dirs) == 1
    # journaled as a FAILED outcome, never as a successful launch.
    assert len(fs.appended_lines) == 2
    outcome = json.loads(fs.appended_lines[1][1])
    assert outcome["phase"] == "outcome"
    assert outcome["payload"]["pid"] is None
    assert outcome["payload"]["harness_run_id"] is None


def test_spin_uncaught_story_feed_keys_error_exits_cleanly_as_mrs_spin_005(home, capsys):
    """Review finding (Edge Case Hunter, verified live): ``story_feed_keys``
    documents it can still raise ``HarnessError`` despite the
    ``story_feed_error`` gate having already passed (a TOCTOU window, or a
    caller reaching it via a path that skipped that gate) -- this call was
    originally unguarded, crashing ``run_spin`` with a raw traceback instead
    of the clean exit every OTHER harness call in this function already
    produces."""

    class _RaisingFeedKeysHarness(FakeHarness):
        def story_feed_keys(self, project: Path) -> tuple[str, ...]:
            self.calls.append("story_feed_keys")
            raise HarnessError("cannot read story feed: disk error")

    fs = FakeFs(dirs={home})
    harness = _RaisingFeedKeysHarness()

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness)

    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-SPIN-005" in out
    assert "disk error" in out
    assert fs.created_dirs == []
    assert harness.spin_calls == []


def test_spin_outcome_journal_write_failure_after_successful_spawn_is_mrs_spin_006(
    home, capsys
):
    """Distinct from ``test_spin_detached_launch_failure_journals_a_failed_outcome``
    above: here the spawn itself SUCCEEDS (``harness.spin`` returns a real
    ``SpinResult``) and only the OUTCOME journal write fails -- review
    finding (Blind Hunter): this originally reused ``MRS-SPIN-003``
    (``Verdict.ERROR``, "never launched, safe to retry"), which a caller
    could not distinguish from a genuine launch failure and could act on by
    double-spawning a second concurrent run against a process that is, in
    fact, already live."""
    fs = FakeFs(dirs={home})
    fs.fail_append_line_on_call = 2  # the intent (#1) succeeds; the outcome (#2) fails
    harness = FakeHarness()
    harness.feed_keys = ("1-1-a",)

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness)

    # WARN tier -- matching MRS-SPIN-004's own precedent: the spawn already
    # succeeded, so this is a paper-trail gap, never a failure (AD-21's F-17
    # amendment for a lone unclosed intent: "classifies WARN, not error").
    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-SPIN-006" in out
    assert "MRS-SPIN-003" not in out
    assert "warn" in out.lower()
    # The spawn itself really happened -- distinct from the launch-failure
    # test above, where appended_lines still records the (failed) outcome.
    assert len(fs.appended_lines) == 1  # only the intent actually landed
    [spin_call] = harness.spin_calls
    assert spin_call["project"] == home


# --- CLI argument validation: negative --epic/--max-count ----------------------


@pytest.mark.parametrize("text", ["-1", "-100"])
def test_non_negative_int_rejects_negative_values(text):
    with pytest.raises(argparse.ArgumentTypeError, match="must be >= 0"):
        _non_negative_int(text)


def test_non_negative_int_rejects_unparseable_values():
    with pytest.raises(argparse.ArgumentTypeError, match="invalid int value"):
        _non_negative_int("not-a-number")


@pytest.mark.parametrize("text,expected", [("0", 0), ("3", 3), ("42", 42)])
def test_non_negative_int_accepts_zero_and_positive_values(text, expected):
    assert _non_negative_int(text) == expected


def test_spin_parser_rejects_negative_epic_and_max_count():
    """Full argparse-level regression (not just the validator function in
    isolation): ``marshal factory spin`` must reject ``--epic -1``/
    ``--max-count -1`` as a usage error rather than accepting a value that
    ``_filter_preview``'s slice semantics or ``bmad-loop run`` itself would
    silently misinterpret."""
    from pyforge.marshal.cli.main import _build_parser

    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["factory", "spin", "acme", "--epic", "-1"])
    with pytest.raises(SystemExit):
        parser.parse_args(["factory", "spin", "acme", "--max-count", "-1"])


# --- harness_run_id unconfirmed ---------------------------------------------------


def test_spin_unconfirmed_harness_run_id_warns_but_still_exits_0(home, capsys):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-a",)
    harness.spin_result = SpinResult(pid=777, harness_run_id=None)

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness)

    assert exit_code == EXIT_OK  # WARN tier -> exit 0, CLI returns promptly regardless
    out = capsys.readouterr().out
    assert "MRS-SPIN-004" in out
    outcome = json.loads(fs.appended_lines[1][1])
    assert outcome["payload"] == {"pid": 777, "harness_run_id": None}


# --- --foreground ------------------------------------------------------------------


def test_spin_foreground_relays_the_exit_code_and_skips_the_journal(home):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.foreground_result = 3

    exit_code = run_spin(_spin_namespace("acme", foreground=True), fs=fs, harness=harness)

    assert exit_code == 3
    assert harness.calls == ["run_foreground"]
    assert fs.created_dirs == []
    assert fs.appended_lines == []


def test_spin_foreground_passes_through_the_same_selectors(home):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()

    run_spin(
        _spin_namespace("acme", epic=2, story="2-1", max_count=1, foreground=True),
        fs=fs,
        harness=harness,
    )

    [call] = harness.foreground_calls
    assert call["project"] == home
    assert call["epic"] == 2
    assert call["story"] == "2-1"
    assert call["max_count"] == 1


def test_spin_foreground_launch_failure_still_uses_the_envelope(home, capsys):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.fail_run_foreground = HarnessError("bmad-loop binary not found")

    exit_code = run_spin(_spin_namespace("acme", foreground=True), fs=fs, harness=harness)

    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-SPIN-003" in out


def test_spin_foreground_still_checked_the_shared_preconditions(capsys):
    """A malformed slug or an unprovisioned home are real preconditions
    independent of foreground-vs-detached -- --foreground does not bypass
    them."""
    fs = FakeFs()  # home NOT provisioned
    harness = FakeHarness()

    exit_code = run_spin(_spin_namespace("acme", foreground=True), fs=fs, harness=harness)

    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-SPIN-002" in out
    assert harness.calls == []


# --- --format json validates against the envelope schema -----------------------


def test_spin_json_output_validates_against_the_envelope_schema(home, capsys):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-a",)

    exit_code = run_spin(_spin_namespace("acme", fmt="json"), fs=fs, harness=harness)

    assert exit_code == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=payload, schema=schema)
    assert payload["command"] == "factory spin"
    assert payload["status"] == "ok"


# --- marshal factory attach -----------------------------------------------------


def test_attach_relays_the_exit_code_and_builds_no_envelope(home, capsys):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.attach_result = 0

    exit_code = run_attach(_attach_namespace("acme"), fs=fs, harness=harness)

    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert harness.attach_calls == [home]


def test_attach_no_runs_found_relays_a_nonzero_exit_code_verbatim(home):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.attach_result = 1  # bmad-loop attach's own "no runs found" exit

    exit_code = run_attach(_attach_namespace("acme"), fs=fs, harness=harness)

    assert exit_code == 1


def test_attach_malformed_slug_rejected_before_any_io(capsys):
    fs = FakeFs()
    harness = FakeHarness()

    exit_code = run_attach(_attach_namespace("../escaped-dir"), fs=fs, harness=harness)

    assert exit_code != EXIT_OK
    assert "error:" in capsys.readouterr().err
    assert fs.calls == []
    assert harness.calls == []


def test_attach_loop_home_not_provisioned(capsys):
    fs = FakeFs()  # home NOT registered as a dir
    harness = FakeHarness()

    exit_code = run_attach(_attach_namespace("acme"), fs=fs, harness=harness)

    assert exit_code != EXIT_OK
    assert "error:" in capsys.readouterr().err
    assert harness.calls == []


def test_attach_launch_failure(home, capsys):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.fail_attach = HarnessError("bmad-loop binary not found")

    exit_code = run_attach(_attach_namespace("acme"), fs=fs, harness=harness)

    assert exit_code != EXIT_OK
    assert "cannot launch bmad-loop attach" in capsys.readouterr().err
