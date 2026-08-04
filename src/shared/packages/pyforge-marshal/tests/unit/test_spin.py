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
import builtins
import errno
import json
import sys
from pathlib import Path

import jsonschema
import pytest
from pyforge.marshal.adapters.fs_local import FsError
from pyforge.marshal.adapters.harness_bmadloop import HarnessError
from pyforge.marshal.adapters.process_posix import ProcessError
from pyforge.marshal.cli import spin as spin_module
from pyforge.marshal.cli.main import main
from pyforge.marshal.cli.spin import _non_negative_int, run_attach, run_resume, run_spin
from pyforge.marshal.core.journal import JournalEntryId, Phase, build_entry, prepare_for_write
from pyforge.marshal.core.verdict import EXIT_OK, EXIT_SIGINT, Verdict, exit_code_for
from pyforge.marshal.ports.harness import RunStatusSnapshot, SpinResult

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
    ``read_symlink_target`` (the Tier-3 backlink gate),
    ``ensure_dir``/``create_dir_exclusive`` (the run directory), and
    ``append_line``/``write_text_atomic`` (the journal + any sidecar
    blob).

    ``tier3_backlink`` defaults to ``True`` -- a provisioned home HAS a
    backlink, so every pre-existing scenario keeps describing the same
    world it always did. Setting it ``False`` models the home this fake
    could not previously express AT ALL, which is exactly why the missing
    gate survived the first review pass: a fake with no
    ``read_symlink_target`` can only ever model a well-formed home."""

    def __init__(
        self,
        *,
        dirs: set[Path] | None = None,
        events: list[str] | None = None,
        tier3_backlink: bool = True,
    ) -> None:
        self.dirs: set[Path] = set(dirs or set())
        self.tier3_backlink = tier3_backlink
        # `LocalFs.read_symlink_target` RAISES `FsError` on any `OSError`
        # (its own implementation comment names the trigger: a
        # `PermissionError` from an unsearchable ancestor). Only a fake that
        # can raise can model that, which is why the unguarded call survived
        # the review pass that ADDED the backlink gate.
        self.fail_read_symlink_target: Exception | None = None
        # A backlink that EXISTS but whose target was removed (a repo
        # re-clone, a moved checkout). `read_symlink_target` still returns
        # the target -- the link is there -- but `is_dir` FOLLOWS the link,
        # so it is False. Only a fake that can express that gap between the
        # two probes can model the case where the presence check passes and
        # the very next write then fails.
        self.tier3_dangling = False
        self.read_symlink_target_calls: list[Path] = []
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
        # Story 3.7's own `run_resume` read seam -- see `read_text` below.
        self.read_text_contents: dict[Path, str] = {}
        self.fail_read_text: Exception | None = None

    def is_dir(self, path: Path) -> bool:
        self.calls.append("is_dir")
        if path in self.dirs:
            return True
        # A path this fake has already reported as a healthy backlink also
        # resolves as a directory -- that is what "points at the canonical
        # store" MEANS -- unless the test declared it dangling. Without this
        # the fake would describe an impossible world (a symlink to a real
        # store that is somehow not a directory) for every scenario.
        return (
            path in self.read_symlink_target_calls
            and self.tier3_backlink
            and not self.tier3_dangling
        )

    def read_symlink_target(self, path: Path) -> Path | None:
        self.calls.append("read_symlink_target")
        self.read_symlink_target_calls.append(path)
        if self.fail_read_symlink_target:
            raise self.fail_read_symlink_target
        if not self.tier3_backlink:
            return None
        return Path("/canonical/store") / path.name

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

    def read_text(self, path: Path) -> str | None:
        """Story 3.7's own ``run_resume`` needs this to resolve a prior
        run's ``harness_run_id`` -- keyed by full path (mirrors
        ``test_supervisor.py::FakeFs``'s own ``journal_text`` convention,
        extended to per-path content since ``run_resume`` reads a DIFFERENT
        run's journal than the one it is about to write)."""
        self.calls.append("read_text")
        if self.fail_read_text:
            raise self.fail_read_text
        return self.read_text_contents.get(path)


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
        # `story_feed_error`'s port docstring promises "never raises", so
        # this fake could only ever model a method that honors it -- which
        # is precisely why `run_spin`'s unguarded call to it survived three
        # review passes. bmad_loop's own parsing can raise `RecursionError`
        # (deeply-nested YAML: a RuntimeError, so `yaml.YAMLError` misses
        # it) or a plain `ValueError` (`int()` on an over-long digit run)
        # past the adapter's catch tuples.
        self.fail_feed_error: Exception | None = None
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
        # Story 3.7's own `run_resume` seam -- `run_status_snapshot`
        # defaults to `None` (inert -- resume proceeds), and `resume`
        # defaults to succeeding with a fixed pid, mirroring `spin_result`'s
        # own "succeeds by default" convention.
        self.run_status_snapshot_result: object | None = None
        self.run_status_snapshot_calls: list[tuple[Path, str]] = []
        self.resolution_reference_result: str | None = None
        self.resolution_reference_calls: list[tuple[Path, str, str]] = []
        self.resume_result: int = 636363
        self.fail_resume: Exception | None = None
        self.resume_calls: list[dict[str, object]] = []

    def story_feed_error(self, project: Path) -> str | None:
        self.calls.append("story_feed_error")
        if self.fail_feed_error:
            raise self.fail_feed_error
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

    def run_status_snapshot(self, project: Path, run_id: str) -> object | None:
        self.calls.append("run_status_snapshot")
        self.run_status_snapshot_calls.append((project, run_id))
        return self.run_status_snapshot_result

    def resolution_reference(self, project: Path, run_id: str, story_key: str) -> str | None:
        self.calls.append("resolution_reference")
        self.resolution_reference_calls.append((project, run_id, story_key))
        return self.resolution_reference_result

    def resume(self, project: Path, run_id: str, *, log_path: Path) -> int:
        self.calls.append("resume")
        self._events.append("resume")
        self.resume_calls.append({"project": project, "run_id": run_id, "log_path": log_path})
        if self.fail_resume:
            raise self.fail_resume
        return self.resume_result


class FakeProcess:
    """Fakes ``ProcessPort``'s ONE method ``run_spin`` calls (Story 3.4):
    ``spawn_detached``, the supervisor sidecar's own launch. Mirrors
    ``FakeHarness``/``FakeFs``'s identical per-story-scoped fake
    convention -- ``run_spin`` never calls ``ProcessPort.run``, so this
    fake implements only what it needs."""

    def __init__(self, *, events: list[str] | None = None) -> None:
        self._events = events if events is not None else []
        self.calls: list[str] = []
        self.spawn_result: int = 424242
        self.fail_spawn: Exception | None = None
        self.spawn_calls: list[dict[str, object]] = []

    def spawn_detached(self, argv: list[str], *, cwd: Path, log_path: Path) -> int:
        self.calls.append("spawn_detached")
        self._events.append("spawn_detached")
        self.spawn_calls.append({"argv": list(argv), "cwd": cwd, "log_path": log_path})
        if self.fail_spawn:
            raise self.fail_spawn
        return self.spawn_result


class _StubProcess:
    """The default supervisor-spawn stand-in for every test in this file
    that PRE-DATES Story 3.4 and does not itself exercise supervisor-spawn
    behavior (the overwhelming majority) -- returns a fixed pid without
    touching the real filesystem/subprocess machinery, so ``run_spin``'s
    own NEW last step (spawning the supervisor sidecar) cannot fail these
    tests over a real I/O concern that has nothing to do with what they
    actually test (``FakeFs``'s own ``home``/``run_dir`` never exist on the
    real disk -- a REAL ``PosixProcess.spawn_detached`` would raise
    ``ProcessError`` trying to open a log file under a directory that was
    only ever recorded in a fake, registering a spurious ``MRS-SPIN-007``
    in every one of them)."""

    def spawn_detached(self, argv: list[str], *, cwd: Path, log_path: Path) -> int:
        return 999999


@pytest.fixture(autouse=True)
def _default_supervisor_spawn_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pins ``run_spin``'s own DI default (``process: ProcessPort | None =
    None`` -> ``PosixProcess()``) to ``_StubProcess`` for every test that
    does not pass its own ``process=`` fake explicitly -- an explicit
    keyword argument always wins over this module-level patch, since
    ``run_spin`` only ever constructs ``PosixProcess()`` when ``process``
    is ``None``."""
    monkeypatch.setattr(spin_module, "PosixProcess", lambda: _StubProcess())


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


def _resume_namespace(slug: str, *, fmt: str = "text") -> argparse.Namespace:
    return argparse.Namespace(slug=slug, format=fmt, factory_command="resume")


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
    assert "harness_run_id: 'acme-20260803T054512123Z-ab12cd'" in out

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
    # `1` is a genuine passthrough code; this test previously used `3`, which
    # the follow-up review pass established must NOT pass through (it is the
    # GATE_FAILED rung -- a judgment marshal never made). The projection of
    # 2/3/4 has its own parametrized coverage below.
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.foreground_result = 1

    exit_code = run_spin(_spin_namespace("acme", foreground=True), fs=fs, harness=harness)

    assert exit_code == 1
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


def test_attach_no_runs_found_relays_its_nonzero_exit_code(home):
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


# --- relayed exit codes are PROJECTED into the frozen domain, not verbatim ----
#
# Review finding (Blind Hunter + Edge Case Hunter, both verified live): the
# two no-envelope paths returned their child's RAW exit code, but `main()`
# admits only `GUARDED_EXIT_CODES` from a handler and clamps the rest to
# `EXIT_USAGE` -- so a harness exiting 5/7/137/143 reported as a marshal
# USAGE error, and `BmadLoopHarness._normalize_returncode`'s own 128+N
# signal convention (added by the PREVIOUS review pass) was voided outright.
# The `main()`-level tests below are the coverage class whose absence let
# that through: every pre-existing test called `run_spin`/`run_attach`
# directly, where the clamp is not in the picture at all.


@pytest.mark.parametrize("passthrough", [0, 1, EXIT_SIGINT])
def test_spin_foreground_passes_in_domain_exit_codes_through_untouched(home, passthrough):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.foreground_result = passthrough

    exit_code = run_spin(_spin_namespace("acme", foreground=True), fs=fs, harness=harness)

    assert exit_code == passthrough


@pytest.mark.parametrize("child_code", [2, 3, 4, 5, 7, 128, 137, 143, 255])
def test_spin_foreground_projects_out_of_domain_exit_codes_to_the_error_rung(home, child_code):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.foreground_result = child_code

    exit_code = run_spin(_spin_namespace("acme", foreground=True), fs=fs, harness=harness)

    assert exit_code == exit_code_for(Verdict.ERROR)


@pytest.mark.parametrize("child_code", [2, 3, 4, 5, 137, 143])
def test_attach_projects_out_of_domain_exit_codes_to_the_error_rung(home, child_code):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.attach_result = child_code

    exit_code = run_attach(_attach_namespace("acme"), fs=fs, harness=harness)

    assert exit_code == exit_code_for(Verdict.ERROR)


@pytest.mark.parametrize(
    ("child_code", "expected"),
    [
        (0, EXIT_OK),
        (1, 1),
        (EXIT_SIGINT, EXIT_SIGINT),
        (2, exit_code_for(Verdict.ERROR)),  # was EXIT_USAGE -- see the class below
        (3, exit_code_for(Verdict.ERROR)),  # was the GATE_FAILED rung
        (4, exit_code_for(Verdict.ERROR)),
        (5, exit_code_for(Verdict.ERROR)),
        (137, exit_code_for(Verdict.ERROR)),  # SIGKILL, via _normalize_returncode's 128+N
        (143, exit_code_for(Verdict.ERROR)),  # SIGTERM, likewise
    ],
)
def test_foreground_relay_survives_mains_handler_clamp(
    home, monkeypatch, child_code, expected
):
    """End-to-end through ``main()`` -- the ONLY level at which the original
    defect was observable. Before the fix every out-of-domain row here
    returned ``EXIT_USAGE`` (2)."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.foreground_result = child_code

    def _fake_run_spin(args):
        return run_spin(args, fs=fs, harness=harness)

    monkeypatch.setattr(spin_module, "run_spin", _fake_run_spin)

    assert main(["factory", "spin", "acme", "--foreground"]) == expected


@pytest.mark.parametrize(
    ("child_code", "expected"),
    [(0, EXIT_OK), (1, 1), (5, exit_code_for(Verdict.ERROR)), (137, exit_code_for(Verdict.ERROR))],
)
def test_attach_relay_survives_mains_handler_clamp(home, monkeypatch, child_code, expected):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.attach_result = child_code

    def _fake_run_attach(args):
        return run_attach(args, fs=fs, harness=harness)

    monkeypatch.setattr(spin_module, "run_attach", _fake_run_attach)

    assert main(["factory", "attach", "acme"]) == expected


# --- the Tier-3 backlink is a real precondition of the WRITE path -------------


def test_spin_missing_tier3_backlink_refuses_before_any_write(home, capsys):
    """Review finding (both reviewers, verified live): ``fs.is_dir(home)``
    was the only home gate, so a home with no Tier-3 backlink reached
    ``ensure_dir(parents=True)``, which FABRICATED the whole
    ``_bmad-output/projects/<slug>/implementation-artifacts/runs/`` tree as
    real local directories and wrote the journal into them -- at exit 0,
    silently violating NFR-8 and poisoning any later ``marshal init`` with
    its own MRS-INIT-005."""
    fs = FakeFs(dirs={home}, tier3_backlink=False)
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness)

    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-SPIN-002" in out
    assert "Tier-3 backlink" in out
    # Nothing minted, nothing created, nothing journaled, nothing spawned.
    assert fs.created_dirs == []
    assert fs.ensure_dir_calls == []
    assert fs.appended_lines == []
    assert harness.spin_calls == []


def test_spin_checks_the_backlink_at_the_local_tier3_path(home):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    run_spin(_spin_namespace("acme"), fs=fs, harness=harness)

    assert fs.read_symlink_target_calls == [
        home / "_bmad-output" / "projects" / "acme" / "implementation-artifacts"
    ]


def test_spin_foreground_needs_no_tier3_backlink(home):
    """``--foreground`` writes nothing at all, so the backlink is not one of
    its preconditions -- it must still launch against a home the detached
    path would (correctly) refuse."""
    fs = FakeFs(dirs={home}, tier3_backlink=False)
    harness = FakeHarness()
    harness.foreground_result = 0

    assert run_spin(_spin_namespace("acme", foreground=True), fs=fs, harness=harness) == EXIT_OK
    assert harness.calls == ["run_foreground"]
    assert fs.read_symlink_target_calls == []


# --- run_attach's own no-envelope error path ---------------------------------


def test_attach_error_path_prints_the_finding_code(capsys):
    """Review finding: the message printed without its CODE, so the operator
    (and any log scraper) could not correlate an attach refusal with the
    IDENTICAL run_spin refusal, which prints the code in its envelope."""
    fs = FakeFs()
    harness = FakeHarness()

    run_attach(_attach_namespace("../escaped-dir"), fs=fs, harness=harness)

    err = capsys.readouterr().err
    assert "MRS-SPIN-001" in err
    assert "malformed project slug" in err


def test_attach_error_path_survives_an_unwritable_stderr(capsys, monkeypatch):
    """Review finding (Edge Case Hunter, verified live): the print was
    unguarded, unlike its sibling ``_emit`` -- an unwritable stderr raised
    ``OSError`` straight out of ``run_attach``, breaking ``main()``'s own
    documented "never raises" contract with a raw traceback."""
    fs = FakeFs()
    harness = FakeHarness()

    real_print = builtins.print

    def _exploding_print(*args, **kwargs):
        if kwargs.get("file") is sys.stderr:
            raise OSError(errno.ENOSPC, "No space left on device")
        return real_print(*args, **kwargs)

    monkeypatch.setattr(builtins, "print", _exploding_print)

    exit_code = run_attach(_attach_namespace("../escaped-dir"), fs=fs, harness=harness)

    assert exit_code != EXIT_OK


# --- follow-up review pass: the last unguarded FsPort call --------------------


def test_spin_unreadable_tier3_backlink_exits_cleanly_as_mrs_spin_002(home, capsys):
    """Review finding (Blind Hunter + Edge Case Hunter, both verified live):
    ``fs.read_symlink_target`` was the ONLY unguarded ``FsPort`` call left in
    ``run_spin`` -- added by the PREVIOUS pass's own backlink-gate fix. It
    raises ``FsError`` on any ``OSError``, and ``main()`` catches only
    ``SystemExit``/``KeyboardInterrupt``, so an unsearchable ancestor
    surfaced as a raw traceback instead of the clean refusal every other
    precondition in this function produces."""
    fs = FakeFs(dirs={home})
    fs.fail_read_symlink_target = FsError("cannot read symlink: Permission denied")
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness)

    assert exit_code == exit_code_for(Verdict.ERROR)
    assert "MRS-SPIN-002" in capsys.readouterr().out
    # Refused BEFORE the first write, exactly as an absent backlink is.
    assert "create_dir_exclusive" not in fs.calls
    assert "append_line" not in fs.calls
    assert harness.spin_calls == []


def test_spin_unreadable_tier3_backlink_never_escapes_through_main(home, monkeypatch):
    """The same defect at the level it was actually observable: ``main()``'s
    own documented "never raises" contract."""
    fs = FakeFs(dirs={home})
    fs.fail_read_symlink_target = FsError("cannot read symlink: Permission denied")
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    monkeypatch.setattr(
        spin_module, "run_spin", lambda args: run_spin(args, fs=fs, harness=harness)
    )

    assert main(["factory", "spin", "acme"]) == exit_code_for(Verdict.ERROR)


# --- follow-up review pass: the harness log path is reported -------------------


def test_spin_reports_the_harness_log_path(home, capsys):
    """Review finding (Blind Hunter): the log path was computed, handed to
    ``spin``, and then dropped -- absent from ``data``, from both journal
    entries, and from the text render. For a DETACHED child whose stdout the
    operator no longer has, that file is their only diagnostic."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    run_spin(_spin_namespace("acme", fmt="json"), fs=fs, harness=harness)

    envelope = json.loads(capsys.readouterr().out)
    log_path = envelope["data"]["log"]
    assert log_path.endswith("harness.log")
    # The same path `spin` was actually told to redirect into.
    assert str(harness.spin_calls[0]["log_path"]) == log_path


def test_spin_unconfirmed_run_id_warning_names_the_log_path(home, capsys):
    """``MRS-SPIN-004`` said the run id "could not be confirmed" without
    saying where to look -- unactionable for a detached process."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)
    harness.spin_result = SpinResult(pid=4242, harness_run_id=None)

    assert run_spin(_spin_namespace("acme"), fs=fs, harness=harness) == EXIT_OK

    out = capsys.readouterr().out
    assert "MRS-SPIN-004" in out
    assert str(harness.spin_calls[0]["log_path"]) in out


# --- Story 3.6 FR-14: the preflight advisory (MRS-SPIN-009) --------------------
#
# Both signals read the REAL filesystem directly (``Path.stat()``/
# ``Path.glob()``/``Path.read_text()``), never through the injected
# ``FsPort``. ``FsPort`` has no stat-like or glob-like method, which is what
# this story's own Code Map anticipates ("use fs if this module already has
# one available for stat-like checks, else Path.stat()") -- but it DOES
# expose ``read_text``/``exists`` (review finding: the earlier wording here
# claimed otherwise), so the prior-attempt scan's own file reads could be
# routed through the port even though the glob and the size check cannot.
# Routing them is deferred, not decided against: it needs a port-surface
# decision, and until then a caller injecting a fake fs still gets an
# advisory that reads the real filesystem. See ``deferred-work.md``.
# ``home`` is a genuine path under pytest's own ``tmp_path`` sandbox (see
# the ``home`` fixture above), so these tests write real files there rather
# than configuring ``FakeFs``.


def test_preflight_advisory_warns_on_a_real_titled_spec_filename(home, capsys):
    """REGRESSION (review finding -- this half of the advisory was dead code
    in production, and the whole suite stayed green).

    The first implementation probed one exact path,
    ``spec-{render_filename_slug(key)}.md`` (``spec-1-1.md``) -- the literal
    formula the story's own intent contract names. But every spec
    ``bmad-dev-auto`` actually writes carries a descriptive title after the
    key: its step-01 derives ``spec-{slug}.md`` from a slug that LEADS with
    the story number and continues with the intent text, so real files are
    ``spec-1-1-package-spine-verdict-lattice-....md``. ``stat()`` therefore
    always raised, ``spec_size`` was pinned at 0, and the size signal could
    never fire on real data. Verified against this project's own Tier-3
    store: 21 of 21 specs carry a title; 7 would have crossed the threshold.

    The pre-existing test above passes only because it fabricates the
    untitled name -- which is why this one uses the shape bmad-loop and
    bmad-dev-auto really produce."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    spec_dir = home / "_bmad-output" / "projects" / "acme" / "implementation-artifacts"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec-1-1-package-spine-and-the-verdict-lattice.md").write_bytes(
        b"x" * (spin_module._LARGE_SPEC_BYTES + 1)
    )

    exit_code = run_spin(_spin_namespace("acme", fmt="json"), fs=fs, harness=harness)

    envelope = json.loads(capsys.readouterr().out)
    findings_by_code = {finding["code"]: finding for finding in envelope["findings"]}
    assert "MRS-SPIN-009" in findings_by_code
    assert "spec size" in findings_by_code["MRS-SPIN-009"]["message"]
    assert exit_code == EXIT_OK


def test_preflight_advisory_does_not_confuse_story_3_6_with_story_3_60(home, capsys):
    """The titled-filename glob is anchored on a trailing hyphen, so story
    ``1.1`` cannot be advised on the strength of story ``1.10``'s spec."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    spec_dir = home / "_bmad-output" / "projects" / "acme" / "implementation-artifacts"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec-1-10-a-completely-different-story.md").write_bytes(
        b"x" * (spin_module._LARGE_SPEC_BYTES + 1)
    )

    exit_code = run_spin(_spin_namespace("acme", fmt="json"), fs=fs, harness=harness)

    envelope = json.loads(capsys.readouterr().out)
    codes = {finding["code"] for finding in envelope["findings"]}
    assert "MRS-SPIN-009" not in codes
    assert exit_code == EXIT_OK


def test_preflight_advisory_warns_on_a_real_bmad_loop_state_json_shape(home, capsys):
    """REGRESSION (review finding -- the OTHER half of the dead advisory).

    bmad-loop keys ``state.json``'s ``tasks`` map by its OWN key spelling,
    the full sprint-status slug -- verified against 5 live runs on this
    machine, e.g. ``"3-6-budget-ceilings-and-the-heaviest-story-advisory"``.
    The first implementation looked the task up by ``render_feed_key(key)``,
    the dot form ``"3.6"``, so it could never hit on real data; the
    pre-existing tests pass only because they fabricate
    ``{"tasks": {"1.1": ...}}``, a shape bmad-loop never writes.

    Matching now normalizes both sides through ``core.identity`` (AD-23's
    sole parser), so today's slug keys AND the fabricated dot keys both
    resolve to the same ``StoryKey``."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    prior_run_dir = home / ".bmad-loop" / "runs" / "acme-20260803-023308-65b7"
    prior_run_dir.mkdir(parents=True)
    (prior_run_dir / "state.json").write_text(
        json.dumps(
            {
                "run_id": "acme-20260803-023308-65b7",
                "project": str(home),
                "tasks": {
                    "1-1-first-story": {
                        "story_key": "1-1-first-story",
                        "epic": 1,
                        "phase": "dev-running",
                        "attempt": 3,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    exit_code = run_spin(_spin_namespace("acme", fmt="json"), fs=fs, harness=harness)

    envelope = json.loads(capsys.readouterr().out)
    findings_by_code = {finding["code"]: finding for finding in envelope["findings"]}
    assert "MRS-SPIN-009" in findings_by_code
    assert "attempt" in findings_by_code["MRS-SPIN-009"]["message"]
    assert exit_code == EXIT_OK


def test_preflight_advisory_only_covers_the_selected_stories(home, capsys):
    """REGRESSION (review finding): the advisory ran BEFORE
    ``_filter_preview``, so it iterated the whole resolved feed and warned
    about stories ``--epic``/``--story``/``--max-count`` had already
    excluded from this launch -- up to N-1 WARN findings, and a WARN verdict
    on the exit envelope, about work that will not run. The acceptance
    criterion is "preflight warns when a SELECTED story is likely to exceed
    the session budget"."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story", "9-9-the-heavy-one")

    spec_dir = home / "_bmad-output" / "projects" / "acme" / "implementation-artifacts"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec-9-9-the-heavy-one.md").write_bytes(
        b"x" * (spin_module._LARGE_SPEC_BYTES + 1)
    )

    exit_code = run_spin(
        _spin_namespace("acme", story="1-1-first-story", fmt="json"), fs=fs, harness=harness
    )

    envelope = json.loads(capsys.readouterr().out)
    codes = {finding["code"] for finding in envelope["findings"]}
    assert envelope["data"]["preview"] == ["1.1"]
    assert "MRS-SPIN-009" not in codes, (
        "warned about story 9.9, which this launch's own --story selector excludes"
    )
    assert exit_code == EXIT_OK


def test_preflight_advisory_survives_a_deeply_nested_prior_state_json(home, capsys):
    """``json.loads`` raises ``RecursionError`` -- NOT a ``ValueError`` -- on
    a deeply nested document, and the scan's own docstring promises one
    malformed prior run never aborts the scan, still less the whole command
    (review finding: it escaped ``run_spin`` and ``main()``, crashing
    ``marshal factory spin`` with a traceback before any launch)."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    prior_run_dir = home / ".bmad-loop" / "runs" / "acme-prior-run"
    prior_run_dir.mkdir(parents=True)
    (prior_run_dir / "state.json").write_text(
        "[" * 200_000 + "]" * 200_000, encoding="utf-8"
    )

    exit_code = run_spin(_spin_namespace("acme", fmt="json"), fs=fs, harness=harness)

    envelope = json.loads(capsys.readouterr().out)
    codes = {finding["code"] for finding in envelope["findings"]}
    assert "MRS-SPIN-009" not in codes
    assert exit_code == EXIT_OK
    assert harness.spin_calls


def test_preflight_advisory_warns_on_an_oversized_spec(home, capsys):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    spec_dir = home / "_bmad-output" / "projects" / "acme" / "implementation-artifacts"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec-1-1.md").write_bytes(b"x" * (spin_module._LARGE_SPEC_BYTES + 1))

    exit_code = run_spin(_spin_namespace("acme", fmt="json"), fs=fs, harness=harness)

    envelope = json.loads(capsys.readouterr().out)
    findings_by_code = {finding["code"]: finding for finding in envelope["findings"]}
    assert "MRS-SPIN-009" in findings_by_code
    assert findings_by_code["MRS-SPIN-009"]["severity"] == "warn"
    assert "1.1" in findings_by_code["MRS-SPIN-009"]["message"]
    assert "spec size" in findings_by_code["MRS-SPIN-009"]["message"]
    # Never blocks: the launch itself still succeeds.
    assert exit_code == EXIT_OK
    assert harness.spin_calls


def test_preflight_advisory_warns_on_prior_attempt_history(home, capsys):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    prior_run_dir = home / ".bmad-loop" / "runs" / "acme-prior-run"
    prior_run_dir.mkdir(parents=True)
    (prior_run_dir / "state.json").write_text(
        json.dumps({"tasks": {"1.1": {"story_key": "1.1", "attempt": 2}}}),
        encoding="utf-8",
    )

    exit_code = run_spin(_spin_namespace("acme", fmt="json"), fs=fs, harness=harness)

    envelope = json.loads(capsys.readouterr().out)
    findings_by_code = {finding["code"]: finding for finding in envelope["findings"]}
    assert "MRS-SPIN-009" in findings_by_code
    assert findings_by_code["MRS-SPIN-009"]["severity"] == "warn"
    assert "attempt" in findings_by_code["MRS-SPIN-009"]["message"]
    assert exit_code == EXIT_OK


def test_preflight_advisory_warns_on_a_deferred_prior_outcome(home, capsys):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    prior_run_dir = home / ".bmad-loop" / "runs" / "acme-prior-run"
    prior_run_dir.mkdir(parents=True)
    (prior_run_dir / "state.json").write_text(
        json.dumps({"tasks": {"1.1": {"story_key": "1.1", "phase": "deferred"}}}),
        encoding="utf-8",
    )

    exit_code = run_spin(_spin_namespace("acme", fmt="json"), fs=fs, harness=harness)

    envelope = json.loads(capsys.readouterr().out)
    findings_by_code = {finding["code"]: finding for finding in envelope["findings"]}
    assert "MRS-SPIN-009" in findings_by_code
    assert exit_code == EXIT_OK


def test_preflight_advisory_silent_when_neither_signal_trips(home, capsys):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    exit_code = run_spin(_spin_namespace("acme", fmt="json"), fs=fs, harness=harness)

    envelope = json.loads(capsys.readouterr().out)
    codes = {finding["code"] for finding in envelope["findings"]}
    assert "MRS-SPIN-009" not in codes
    assert exit_code == EXIT_OK


def test_preflight_advisory_ignores_prior_runs_for_a_different_story(home, capsys):
    """A prior attempt recorded for a DIFFERENT story key must never warn
    about this one."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    prior_run_dir = home / ".bmad-loop" / "runs" / "acme-prior-run"
    prior_run_dir.mkdir(parents=True)
    (prior_run_dir / "state.json").write_text(
        json.dumps({"tasks": {"9.9": {"story_key": "9.9", "attempt": 5}}}),
        encoding="utf-8",
    )

    exit_code = run_spin(_spin_namespace("acme", fmt="json"), fs=fs, harness=harness)

    envelope = json.loads(capsys.readouterr().out)
    codes = {finding["code"] for finding in envelope["findings"]}
    assert "MRS-SPIN-009" not in codes
    assert exit_code == EXIT_OK


def test_preflight_advisory_skips_an_unreadable_prior_run_file_silently(home, capsys):
    """The scan must never abort, still less fail the whole command, over
    ONE malformed prior-run file -- a genuinely warning-worthy prior run
    elsewhere must still be found."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    bad_run_dir = home / ".bmad-loop" / "runs" / "acme-bad-run"
    bad_run_dir.mkdir(parents=True)
    (bad_run_dir / "state.json").write_text("{not valid json at all", encoding="utf-8")

    good_run_dir = home / ".bmad-loop" / "runs" / "acme-good-run"
    good_run_dir.mkdir(parents=True)
    (good_run_dir / "state.json").write_text(
        json.dumps({"tasks": {"1.1": {"story_key": "1.1", "attempt": 3}}}),
        encoding="utf-8",
    )

    exit_code = run_spin(_spin_namespace("acme", fmt="json"), fs=fs, harness=harness)

    envelope = json.loads(capsys.readouterr().out)
    findings_by_code = {finding["code"]: finding for finding in envelope["findings"]}
    assert "MRS-SPIN-009" in findings_by_code
    assert exit_code == EXIT_OK


# --- Story 3.4: the supervisor sidecar spawn -----------------------------------


def test_spin_spawns_the_supervisor_with_the_expected_argv(home):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)
    process = FakeProcess()

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness, process=process)

    assert exit_code == EXIT_OK
    [call] = process.spawn_calls
    run_id = json.loads(fs.appended_lines[0][1])["run_id"]
    assert call["argv"] == [
        sys.executable,
        "-m",
        "pyforge.marshal.supervisor",
        str(home),
        "acme",
        run_id,
        "4242",  # harness.spin_result's own pid
        str(call["log_path"]),
        # Story 3.5's 6th positional: the effective idle_threshold_minutes
        # (core.policy.DEFAULT_POLICY's own value -- no project-policy file
        # exists for the "acme" slug this test fixture uses).
        "25",
        # Story 3.6's 7th-10th positionals: the 4 budget ceilings, likewise
        # DEFAULT_POLICY's own values.
        "50000000",
        "500000000",
        "1440",
        "2880",
    ]
    assert call["cwd"] == home
    assert call["log_path"].name == "supervisor.log"
    # A SEPARATE file from the harness's own redirected log.
    assert call["log_path"] != harness.spin_calls[0]["log_path"]


def test_spin_surfaces_a_malformed_idle_threshold_minutes_project_policy_finding(
    home, tmp_path, monkeypatch, capsys
):
    """Review finding: ``policy.compose()``'s own ``Finding`` list for the
    ``idle_threshold_minutes`` lookup used to be captured into a variable
    that was never looked at again -- a malformed override in the
    project's own ``marshal-policy.toml`` produced a real
    ``MRS-POLICY-003`` finding that never reached the operator, and the
    effective value silently fell back to the code default with zero
    diagnostic. It must now be surfaced into this command's own findings.

    But NOT by splicing them in verbatim (second review finding): every
    ``MRS-POLICY-00{1,2,3,4,6}`` classifies ``Verdict.UNEVALUABLE`` -> exit
    1, which is right for ``marshal config`` (whose whole job IS the policy)
    and wrong here, where the policy is a supplementary input read AFTER a
    real harness process is already live. Any unknown key or malformed value
    ANYWHERE in a project's policy file would have made ``marshal factory
    spin`` exit 1 over a successfully launched, supervised run -- and a
    caller that retries on non-zero would then double-dispatch the same
    story, the exact hazard this story's own Design Notes give as the reason
    ``stop``+``resume`` is the retry primitive. One WARN-tier
    ``MRS-SPIN-008`` carries every underlying message instead."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    policy_path = tmp_path / "marshal-policy.toml"
    policy_path.write_text('idle_threshold_minutes = "not-a-number"\n', encoding="utf-8")
    monkeypatch.setattr(
        spin_module, "conventional_project_policy_path", lambda slug: policy_path
    )

    exit_code = run_spin(_spin_namespace("acme", fmt="json"), fs=fs, harness=harness)

    envelope = json.loads(capsys.readouterr().out)
    findings_by_code = {finding["code"]: finding for finding in envelope["findings"]}
    assert "MRS-SPIN-008" in findings_by_code
    assert findings_by_code["MRS-SPIN-008"]["severity"] == "warn"
    # The underlying policy finding's own code and message survive into the
    # re-tiered one -- the diagnostic is preserved, only its verdict tier is
    # not inherited.
    assert "MRS-POLICY-003" in findings_by_code["MRS-SPIN-008"]["message"]
    assert "MRS-POLICY-003" not in findings_by_code, "verbatim splice inverts the verdict"
    # The launch itself succeeded, so the command succeeds: a malformed
    # supplementary value must never re-classify a live, already-launched,
    # supervised run as a failure.
    assert exit_code == EXIT_OK
    assert "supervisor_pid" in envelope["data"]
    assert harness.spin_calls  # the harness launch was actually attempted


def test_spin_never_aborts_a_live_launch_over_an_unreadable_project_policy(
    home, tmp_path, monkeypatch, capsys
):
    """Review finding: this read is the LAST step on the post-launch path.
    By the time it runs a real bmad-loop process is already live and
    journalled, and the detached supervisor has not been spawned yet -- so
    anything escaping here leaves the worst state this command can produce
    (a running, UNSUPERVISED harness) and exits non-zero, which invites the
    caller to retry and double-dispatch the very story the live run is
    already working.

    Catching only ``PolicyIOError`` was under-inclusive against this
    module's own stated rule that the read "must never abort an otherwise-
    successful harness launch": ``tomllib.load`` raises a bare
    ``RecursionError`` on a deeply nested document, which is neither an
    ``OSError`` nor a ``ValueError`` and passed straight through."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    policy_path = tmp_path / "marshal-policy.toml"
    policy_path.write_text("idle_threshold_minutes = 30\n", encoding="utf-8")
    monkeypatch.setattr(
        spin_module, "conventional_project_policy_path", lambda slug: policy_path
    )

    def _explode(path):
        raise RecursionError("maximum recursion depth exceeded")

    monkeypatch.setattr(spin_module, "_read_project_policy", _explode)

    exit_code = run_spin(_spin_namespace("acme", fmt="json"), fs=fs, harness=harness)

    envelope = json.loads(capsys.readouterr().out)
    # The launch stands, the supervisor is still spawned, and the threshold
    # simply falls back to its composed default.
    assert exit_code == EXIT_OK
    assert "supervisor_pid" in envelope["data"]
    assert harness.spin_calls


def test_the_supervisor_accepts_the_argv_spin_actually_builds(home, monkeypatch, capsys):
    """Review finding: the two halves of this story's deliberately-
    unimportable boundary were pinned only by matching LITERALS -- this
    module restates the argv it expects, and ``test_supervisor.py``
    restates the argv its own parser accepts, with nothing driving one
    against the other. A later story adding a sixth required argument, or
    tightening ``run_id`` validation, updates the supervisor's own tests,
    leaves this module's literal untouched, and both suites stay green
    while every real sidecar exits 1 with ``usage:`` into ``supervisor.log``
    and every run silently goes unsupervised.

    Worse, misordering is absorbed silently rather than loudly: a
    slug/run_id SWAP passes BOTH of ``main()``'s own gates (a minted run id
    is a valid slug, and a slug is a valid run id), so it degrades to an
    inert exit 0 rather than an error.

    This drives the argv ``run_spin`` genuinely produced through the
    supervisor's OWN ``main()`` and asserts the ten values it recovers
    compose the SAME run directory ``run_spin`` wrote its journal into.
    ``run_supervisor`` is stubbed out, so this stays pure parsing --
    ``test_supervisor_run_path_agreement.py`` pins the path helpers
    themselves; this pins the interface that feeds them.

    A test module is not part of the ``pyforge.marshal`` package, so
    importing both sides here does not touch the AD-9 contract."""
    from pyforge.marshal.supervisor import __main__ as supervisor_main

    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)
    process = FakeProcess()

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness, process=process)
    assert exit_code == EXIT_OK
    [call] = process.spawn_calls
    argv = call["argv"]

    # The journal `run_spin` itself appended to -- the file the sidecar this
    # argv launches must find its own run-launch entry in.
    journal_path = fs.appended_lines[0][0]

    recovered: list[tuple[Path, str, str, int, Path, float, float, float, float, float]] = []

    def _fake_run_supervisor(
        home,
        slug,
        run_id,
        watched_pid,
        log_path,
        idle_threshold_minutes,
        max_tokens_per_story,
        max_tokens_per_run,
        max_wall_clock_minutes_per_story,
        max_wall_clock_minutes_per_run,
    ):
        recovered.append(
            (
                home,
                slug,
                run_id,
                watched_pid,
                log_path,
                idle_threshold_minutes,
                max_tokens_per_story,
                max_tokens_per_run,
                max_wall_clock_minutes_per_story,
                max_wall_clock_minutes_per_run,
            )
        )
        return 0

    monkeypatch.setattr(supervisor_main, "run_supervisor", _fake_run_supervisor)

    # `[:3]` is the interpreter invocation; the supervisor's own `main()`
    # parses exactly the tail.
    assert argv[:3] == [sys.executable, "-m", "pyforge.marshal.supervisor"]
    assert supervisor_main.main(argv[3:]) == 0, capsys.readouterr().err

    [
        (
            got_home,
            got_slug,
            got_run_id,
            got_pid,
            got_log,
            got_threshold,
            got_max_tokens_per_story,
            got_max_tokens_per_run,
            got_max_wall_clock_minutes_per_story,
            got_max_wall_clock_minutes_per_run,
        )
    ] = recovered
    assert (
        supervisor_main._run_dir(got_home, got_slug, got_run_id)
        / supervisor_main._JOURNAL_FILENAME
        == journal_path
    )
    assert got_pid == harness.spin_result.pid
    assert got_log == call["log_path"]
    assert got_threshold == 25.0
    assert got_max_tokens_per_story == 50_000_000.0
    assert got_max_tokens_per_run == 500_000_000.0
    assert got_max_wall_clock_minutes_per_story == 1_440.0
    assert got_max_wall_clock_minutes_per_run == 2_880.0


def test_spin_spawns_the_supervisor_after_the_outcome_append_not_right_after_spin(home):
    """The spec's own ordering requirement: the spawn is the LAST step.

    Follow-up review finding: this docstring used to justify the ordering by
    a race the code no longer has -- the supervisor's inert-check was
    widened (by the first review pass) to accept the INTENT run-launch entry
    too, and that entry is written ``fsync=True`` BEFORE ``harness.spin()``,
    so ownership is already provable at any point after it. The ordering is
    still required, for the reason ``cli/spin.py``'s own comment now gives:
    it keeps this command's intent/outcome pair closed before a SECOND
    writer (the sidecar) ever opens the same journal."""
    events: list[str] = []
    fs = FakeFs(dirs={home}, events=events)
    harness = FakeHarness(events=events)
    harness.feed_keys = ("1-1-first-story",)
    process = FakeProcess(events=events)

    run_spin(_spin_namespace("acme"), fs=fs, harness=harness, process=process)

    spin_index = events.index("spin")
    spawn_index = events.index("spawn_detached")
    append_indices = [i for i, event in enumerate(events) if event == "append_line"]
    assert len(append_indices) == 2  # intent, then outcome
    outcome_append_index = append_indices[1]
    assert spin_index < outcome_append_index < spawn_index


def test_spin_reports_the_supervisor_pid_in_json_and_text(home, capsys):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)
    process = FakeProcess()
    process.spawn_result = 555555

    run_spin(_spin_namespace("acme"), fs=fs, harness=harness, process=process)
    out = capsys.readouterr().out
    assert "supervisor_pid: 555555" in out

    fs2 = FakeFs(dirs={home})
    harness2 = FakeHarness()
    harness2.feed_keys = ("1-1-first-story",)
    process2 = FakeProcess()
    process2.spawn_result = 555555
    run_spin(_spin_namespace("acme", fmt="json"), fs=fs2, harness=harness2, process=process2)
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["data"]["supervisor_pid"] == 555555


def test_spin_supervisor_spawn_failure_registers_mrs_spin_007_but_still_exits_ok(home, capsys):
    """The harness launch already succeeded (a live process exists) --
    losing supervision degrades the run to unsupervised, never invalidates
    the launch: WARN, not error, matching MRS-SPIN-006's own precedent."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)
    process = FakeProcess()
    process.fail_spawn = ProcessError("cannot launch: python not found")

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness, process=process)

    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-SPIN-007" in out
    assert "warn" in out.lower()
    # The harness run itself is entirely unaffected: both journal entries
    # landed, and the harness was launched exactly once.
    assert len(fs.appended_lines) == 2
    assert len(harness.spin_calls) == 1
    assert "pid: 4242" in out


def test_spin_supervisor_spawn_failure_omits_supervisor_pid_from_data(home, capsys):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)
    process = FakeProcess()
    process.fail_spawn = ProcessError("cannot launch: python not found")

    run_spin(_spin_namespace("acme", fmt="json"), fs=fs, harness=harness, process=process)

    envelope = json.loads(capsys.readouterr().out)
    assert "supervisor_pid" not in envelope["data"]


def test_spin_no_supervisor_spawn_attempted_when_the_harness_launch_itself_fails(home, capsys):
    """A harness launch failure returns BEFORE the new spawn step is ever
    reached -- there is no live process to supervise."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)
    harness.fail_spin = HarnessError("bmad-loop binary not found")
    process = FakeProcess()

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness, process=process)

    assert exit_code != EXIT_OK
    assert process.spawn_calls == []
    assert "MRS-SPIN-007" not in capsys.readouterr().out


def test_spin_foreground_never_spawns_a_supervisor(home):
    """``--foreground`` writes nothing and mints no run id -- there is
    nothing this story's own sidecar could meaningfully watch."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    process = FakeProcess()

    run_spin(_spin_namespace("acme", foreground=True), fs=fs, harness=harness, process=process)

    assert process.spawn_calls == []


# --- follow-up review pass: the sidecar branch of _append_entry ----------------


def test_spin_oversized_preview_writes_the_sidecar_blob_before_its_line(home):
    """Review finding (Blind Hunter): ``_append_entry``'s sidecar branch was
    reachable from ``run_spin`` (a preview list long enough to push the
    payload past ``SIDECAR_THRESHOLD_BYTES``) but entirely unexercised --
    no test built a payload that large. The ordering is the invariant that
    matters: the blob must land BEFORE the line referencing it, or a reader
    can observe a ``sidecar_ref`` that does not yet resolve."""
    events: list[str] = []
    fs = FakeFs(dirs={home}, events=events)
    harness = FakeHarness(events=events)
    # ~700 keys of ~8 JSON bytes each clears the 4096-byte threshold.
    harness.feed_keys = tuple(f"1-{n}-story" for n in range(1, 701))

    assert run_spin(_spin_namespace("acme"), fs=fs, harness=harness) == EXIT_OK

    assert len(fs.written_texts) == 1
    blob_path, blob_content = next(iter(fs.written_texts.items()))
    assert blob_path.parent.name == "blobs"
    assert "1.700" in blob_content
    # The intent line embeds the placeholder, not the payload...
    intent_line = json.loads(fs.appended_lines[0][1])
    assert intent_line["payload"] == {"sidecar_ref": f"blobs/{blob_path.name}"}
    # ...and the blob was written before it.
    assert fs.calls.index("write_text_atomic") < fs.calls.index("append_line")


# --- review pass 4: the text projection is not a shell for forged output ------


def test_render_text_quotes_a_newline_injected_selector(home, capsys):
    """Review finding (Edge Case Hunter, reproduced live): ``_render_text``
    interpolated every field RAW, so a newline inside one forged whole lines
    of the report. ``--story $'9.9\\nfindings:\\n  MRS-SPIN-001 [error] ...'``
    printed a ``findings:`` block that no ``Finding`` produced, on a run that
    had genuinely LAUNCHED and exited 0. ``cli/gate.py``'s own
    ``_render_text`` already carries exactly this ``!r`` hardening across two
    of its own review passes; this module shipped without it."""
    forged = "9.9\nfindings:\n  MRS-SPIN-001 [error] FORGED: launch refused"
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    assert run_spin(_spin_namespace("acme", story=forged), fs=fs, harness=harness) == EXIT_OK

    out = capsys.readouterr().out
    # The run really did launch, so a `findings:` header is a pure forgery.
    assert harness.spin_calls != []
    # The forgery is STRUCTURAL: no line of the report may begin with the
    # injected header (the substring survives, escaped, inside the quoted
    # value -- that is the whole point of quoting it).
    assert not any(line.startswith("findings:") for line in out.splitlines())
    assert not any("FORGED" in line for line in out.splitlines() if "story=" not in line)
    # The value is still REPORTED -- quoted, so the newline is visible as an
    # escape rather than structural, on one line.
    assert repr(forged) in out


def test_render_text_quotes_newline_injected_feed_keys(home, capsys):
    """The same forgery from the OTHER untrusted direction: a raw feed key.
    Reproduced live -- a key carrying ``\\nrun_id: ...\\npid: 1`` printed a
    run id and a pid for a launch that was REFUSED (nothing minted, nothing
    spawned), which is strictly worse than the selector case."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("zz\nrun_id: acme-FORGED-000\npid: 1",)

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness)

    out = capsys.readouterr().out
    assert exit_code != EXIT_OK
    assert harness.spin_calls == []
    # No LINE of the report may be forged -- the key survives escaped, on
    # one line, in both the `unresolved:` list and the MRS-IDENT-001 message
    # (quoted at construction, per `cli/gate.py`'s documented split).
    assert not any(line.startswith("run_id:") for line in out.splitlines())
    assert not any(line.startswith("pid:") for line in out.splitlines())
    assert repr(harness.feed_keys[0]) in out


def test_render_text_renders_none_as_the_json_spelling(home, capsys):
    """``_render_text`` is documented as a pure projection of the SAME
    envelope the ``--format json`` path prints (AD-14), but it leaked the
    Python ``repr`` ``None`` where JSON renders ``null`` -- which a shell
    consumer could read as a literal harness run id named ``None``."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)
    harness.spin_result = SpinResult(pid=4242, harness_run_id=None)

    run_spin(_spin_namespace("acme"), fs=fs, harness=harness)

    out = capsys.readouterr().out
    assert "harness_run_id: null" in out
    assert "epic=null story=null max_count=null" in out
    assert "None" not in out


def test_spin_non_utf8_story_selector_does_not_crash_after_the_spawn(home, monkeypatch):
    """Review finding (Edge Case Hunter, reproduced live end-to-end): Python
    decodes ``argv`` with ``surrogateescape``, so a non-UTF-8 byte in
    ``--story`` reached a strict UTF-8 stdout and raised
    ``UnicodeEncodeError`` -- a ``ValueError`` subclass the ``except OSError``
    guard never saw. It fired AFTER the detached child was live and both
    journal entries were fsynced: a traceback instead of the run id the
    operator needs to attach. Two independent fixes are asserted here --
    ``repr`` keeps the surrogate out of the encoder, and ``_emit``'s guard
    now catches it anyway."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    real_print = builtins.print

    def _strict_utf8_print(*args, **kwargs):
        # Model a strict UTF-8 stdout: encoding the payload is what raises.
        for arg in args:
            if isinstance(arg, str):
                arg.encode("utf-8")
        return real_print(*args, **kwargs)

    monkeypatch.setattr(builtins, "print", _strict_utf8_print)

    exit_code = run_spin(_spin_namespace("acme", story="\udcff"), fs=fs, harness=harness)

    assert exit_code == EXIT_OK
    assert harness.spin_calls != []


# --- review pass 4: guards on the two remaining raising call sites ------------


@pytest.mark.parametrize(
    "exc",
    [
        RecursionError("maximum recursion depth exceeded"),
        ValueError("Exceeds the limit (4300 digits) for integer string conversion"),
    ],
    ids=["recursion", "value"],
)
def test_spin_story_feed_error_that_raises_exits_cleanly_as_mrs_spin_005(home, capsys, exc):
    """Review finding (Blind Hunter + Edge Case Hunter, each reproduced
    independently against a real feed): ``story_feed_error``'s own port
    docstring promises "never raises", but its adapter's catch tuples are
    not exhaustive over what bmad_loop's parsing throws. This call site was
    unguarded while its SIBLING 17 lines below had been wrapped for exactly
    this shape by an earlier pass -- the asymmetry between two adjacent
    calls was the defect."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.fail_feed_error = exc

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness)

    assert exit_code == exit_code_for(Verdict.ERROR)
    assert "MRS-SPIN-005" in capsys.readouterr().out
    assert harness.spin_calls == []
    assert "create_dir_exclusive" not in fs.calls


def test_spin_story_feed_error_that_raises_never_escapes_through_main(home, monkeypatch):
    """The same defect at the level it was observable: ``main()``'s own
    documented "never raises" contract (it catches only
    ``SystemExit``/``KeyboardInterrupt``)."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.fail_feed_error = RecursionError("maximum recursion depth exceeded")

    monkeypatch.setattr(
        spin_module, "run_spin", lambda args: run_spin(args, fs=fs, harness=harness)
    )

    assert main(["factory", "spin", "acme"]) == exit_code_for(Verdict.ERROR)


def test_spin_feed_key_past_the_int_conversion_limit_is_mrs_spin_005(home, capsys):
    """``core.identity.resolve_feed`` catches only ``MalformedStoryKeyError``
    around its own ``normalize`` calls, so a raw feed key whose epic position
    exceeds CPython's 4300-digit int-conversion limit raises a PLAIN
    ``ValueError`` through it (reproduced live against a real
    ``sprint-status.yaml`` using YAML explicit-key syntax). ``cli/spin.py`` is
    that function's only caller in the tree, so the crash is newly reachable
    with this story."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1" * 4301 + "-1-story",)

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness)

    assert exit_code == exit_code_for(Verdict.ERROR)
    assert "MRS-SPIN-005" in capsys.readouterr().out
    assert harness.spin_calls == []


def test_spin_story_selector_past_the_int_conversion_limit_previews_empty(home):
    """The same CPython limit reached from ``argv`` instead of the feed:
    ``_filter_preview`` caught only ``MalformedStoryKeyError``, so
    ``--story <4301-digit epic>.1`` escaped as a raw ``ValueError`` from any
    shell with one long argument. Widened to ``ValueError`` (a strict
    superset -- ``MalformedStoryKeyError`` IS one), so it previews empty
    exactly as any other unparseable selector does, and still launches (the
    spec's Never clause forbids pre-refusing on a zero-count preview)."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    exit_code = run_spin(
        _spin_namespace("acme", story="1" * 4301 + ".1"), fs=fs, harness=harness
    )

    assert exit_code == EXIT_OK
    # The 4301-digit selector pushes the intent payload past
    # SIDECAR_THRESHOLD_BYTES, so the preview lands in the sidecar blob.
    assert json.loads(next(iter(fs.written_texts.values())))["preview"] == []
    assert harness.spin_calls != []


# --- review pass 4: a dangling backlink is a provisioning gap, not a launch one


def test_spin_dangling_tier3_backlink_refuses_as_mrs_spin_002(home, capsys):
    """Review finding (Blind Hunter, reproduced): a backlink that EXISTS but
    whose target was removed (a repo re-clone, a moved checkout) passed the
    presence check the previous pass added, then made
    ``ensure_dir(run_dir.parent)`` raise ``FileExistsError`` -- surfacing as
    ``MRS-SPIN-003`` ("cannot create run directory ...: File exists:
    <implementation-artifacts>"), a LAUNCH-failure code naming a path that is
    not the run directory, for the same provisioning gap that gate exists to
    catch."""
    fs = FakeFs(dirs={home})
    fs.tier3_dangling = True
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness)

    out = capsys.readouterr().out
    assert exit_code == exit_code_for(Verdict.ERROR)
    assert "MRS-SPIN-002" in out
    assert "MRS-SPIN-003" not in out
    assert "dangling" in out
    # Refused before the first write, exactly as an absent backlink is.
    assert "ensure_dir" not in fs.calls
    assert "create_dir_exclusive" not in fs.calls
    assert harness.spin_calls == []


# --- review pass 4: the two MRS-SPIN-003 branches nothing exercised -----------


def test_spin_run_directory_creation_failure_is_mrs_spin_003(home, capsys):
    """Review finding (Blind Hunter, grep-verified): ``FakeFs`` has shipped a
    ``fail_create_dir_exclusive`` hook since this module's first pass and NO
    test ever assigned it, leaving this branch entirely unpinned."""
    fs = FakeFs(dirs={home})
    fs.fail_create_dir_exclusive = FsError("cannot create run directory: Read-only file system")
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness)

    assert exit_code == exit_code_for(Verdict.ERROR)
    assert "MRS-SPIN-003" in capsys.readouterr().out
    # Nothing was launched -- MRS-SPIN-003's own "safe to retry" meaning.
    assert harness.spin_calls == []
    assert "append_line" not in fs.calls


def test_spin_intent_journal_write_failure_never_spawns(home, capsys):
    """The single most important NEGATIVE invariant in this module, and it
    was unpinned (review finding, Blind Hunter): AD-6's write-before-act says
    if the ``intent`` cannot be DURABLY recorded, do not act. The behaviour
    was already correct; nothing protected it from regression."""
    fs = FakeFs(dirs={home})
    fs.fail_append_line = FsError("cannot append to journal: No space left on device")
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness)

    assert exit_code == exit_code_for(Verdict.ERROR)
    assert "MRS-SPIN-003" in capsys.readouterr().out
    # The whole point: no process was started.
    assert harness.spin_calls == []


@pytest.mark.parametrize("command", ["spin", "attach"], ids=["spin", "attach"])
def test_loop_home_root_resolution_failure_is_mrs_spin_002(monkeypatch, capsys, command):
    """The ``except (RuntimeError, OSError)`` arm around ``_home_path`` exists
    in BOTH ``run_spin`` and ``run_attach`` and neither was covered (review
    finding, Blind Hunter, grep-verified)."""
    fs = FakeFs()
    harness = FakeHarness()

    def _boom(_slug):
        raise RuntimeError("Could not determine home directory")

    monkeypatch.setattr(spin_module, "_home_path", _boom)

    if command == "spin":
        exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness)
        stream = capsys.readouterr().out
    else:
        exit_code = run_attach(_attach_namespace("acme"), fs=fs, harness=harness)
        stream = capsys.readouterr().err

    assert exit_code == exit_code_for(Verdict.ERROR)
    assert "MRS-SPIN-002" in stream
    assert harness.spin_calls == []
    assert harness.attach_calls == []


def test_spin_still_spawns_the_supervisor_when_the_outcome_append_fails(home, capsys):
    """Follow-up review finding: the whole reason the supervisor's own
    inert-check was widened to accept the INTENT run-launch entry is THIS
    branch -- ``MRS-SPIN-006``, where a live harness process exists but its
    outcome entry never reached disk. ``cli/spin.py``'s comment says the
    spawn happens "whether or not the outcome append itself succeeded", yet
    nothing asserted the two coexist: no Story 3.4 test set
    ``fail_append_line_on_call = 2``, and the ``MRS-SPIN-006`` test passed
    no ``process=`` at all. Someone moving the spawn inside the outcome
    ``try`` (or into its ``else``) would keep every test green while
    silently making the widened inert-check dead code and leaving exactly
    the runs that most need supervision unsupervised."""
    fs = FakeFs(dirs={home})
    fs.fail_append_line_on_call = 2  # intent (#1) lands; outcome (#2) fails
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)
    process = FakeProcess()

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness, process=process)

    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-SPIN-006" in out
    # The spawn was still attempted, and succeeded -- an unsupervised run is
    # never the price of a paper-trail gap.
    assert process.calls == ["spawn_detached"]
    assert f"supervisor_pid: {process.spawn_result}" in out
    # Only the intent actually landed, so the ONLY journal proof of Marshal
    # ownership the sidecar will find is the intent entry -- the exact state
    # the widened inert-check exists to handle.
    assert len(fs.appended_lines) == 1


def test_spin_reports_both_mrs_spin_006_and_mrs_spin_007_together(home, capsys):
    """The compound failure: the outcome append fails AND the supervisor
    cannot be spawned. Both are WARN-tier paper-trail/supervision gaps over
    an already-successful launch, so both must surface -- neither may mask
    the other, and the launch itself must still report success."""
    fs = FakeFs(dirs={home})
    fs.fail_append_line_on_call = 2
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)
    process = FakeProcess()
    process.fail_spawn = ProcessError("cannot launch: python not found")

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness, process=process)

    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-SPIN-006" in out
    assert "MRS-SPIN-007" in out
    assert len(harness.spin_calls) == 1


def test_spin_reports_the_supervisor_log_path_even_when_the_spawn_fails(home, capsys):
    """Follow-up review finding: ``supervisor.log`` is the detached
    sidecar's ONLY diagnostic channel -- its stderr goes nowhere else -- but
    it appeared in neither ``data`` nor the ``MRS-SPIN-007`` message, so an
    operator whose supervisor died later held a pid and no path to any
    output. ``data["log"]`` carries the harness's own log for exactly this
    reason, added there as a prior review finding."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)
    process = FakeProcess()
    process.fail_spawn = ProcessError("cannot launch: python not found")

    run_spin(_spin_namespace("acme", fmt="json"), fs=fs, harness=harness, process=process)

    envelope = json.loads(capsys.readouterr().out)
    supervisor_log = envelope["data"]["supervisor_log"]
    assert supervisor_log.endswith("supervisor.log")
    # Named in the finding message too -- a warning that supervision was
    # lost is unactionable without saying where the output would have gone.
    [finding] = [f for f in envelope["findings"] if f["code"] == "MRS-SPIN-007"]
    assert supervisor_log in finding["message"]


def test_spin_reports_the_supervisor_log_path_on_success_too(home, capsys):
    """Reported unconditionally, not only on failure: a supervisor that
    spawns fine and dies 60s later on an unwritable journal is precisely the
    case where the operator needs this path, and that run's ``spin`` output
    is all they have."""
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)
    process = FakeProcess()

    run_spin(_spin_namespace("acme", fmt="json"), fs=fs, harness=harness, process=process)

    envelope = json.loads(capsys.readouterr().out)
    assert envelope["data"]["supervisor_log"].endswith("supervisor.log")
    assert envelope["data"]["supervisor_log"] == str(process.spawn_calls[0]["log_path"])


def test_mrs_spin_007_quotes_the_supervisor_log_path(home, capsys, monkeypatch):
    """Review finding: ``_render_text``'s own comment states that finding
    MESSAGES are deliberately NOT quoted and requires "every message that
    interpolates an untrusted value quotes it at construction instead" --
    which ``MRS-SPIN-001``/``002`` do. ``MRS-SPIN-007`` shipped with a RAW
    path built from ``BMAD_LOOP_HOME_ROOT``, which ``cli/init.py`` reads
    unvalidated, so a newline in it forged whole lines of the DEFAULT text
    report on a run that genuinely launched -- reintroducing on this
    story's own new finding exactly the defect a prior pass fixed for
    ``--story`` and raw feed keys."""
    poisoned_root = (
        str(home.parent) + "\nfindings:\n  MRS-SPIN-001 [error] FORGED: launch refused"
    )
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", poisoned_root)
    poisoned_home = Path(poisoned_root) / "acme"

    fs = FakeFs(dirs={poisoned_home})
    harness = FakeHarness()
    harness.feed_keys = ("1-1-first-story",)
    process = FakeProcess()
    process.fail_spawn = ProcessError("cannot launch: python not found")

    exit_code = run_spin(_spin_namespace("acme"), fs=fs, harness=harness, process=process)

    # The launch genuinely SUCCEEDED -- MRS-SPIN-007 is a WARN.
    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-SPIN-007" in out
    # The forged text still APPEARS -- it is part of the path -- but only
    # ever escaped inside a quoted scalar, never as a line of its own. That
    # distinction is the whole defect: forgery is about line STRUCTURE.
    assert "FORGED" in out
    # Exactly one `findings:` header -- the report's own.
    assert [line for line in out.splitlines() if line.startswith("findings:")] == [
        "findings:"
    ]
    # ...and no forged FINDING line: every rendered finding is one of the
    # report's own, at the `_render_text` indent.
    forged = [
        line
        for line in out.splitlines()
        if line.startswith("  MRS-") and "MRS-SPIN-007" not in line
    ]
    assert forged == [], forged


# =============================================================================
# Story 3.7: `marshal factory resume` (AD-3/AD-25/AD-45, FR-15/16/17)
# =============================================================================


def _outcome_line(
    run_id: str, *, kind: str = "run-launch", harness_run_id: str | None, watched_pid: int = 4242
) -> str:
    """A minimal, valid ``phase: outcome`` journal line for a PRIOR run --
    the one entry ``_resolve_harness_run_id_for_resume`` looks for. Mirrors
    ``test_supervisor.py::_launch_outcome_line``'s identical shape,
    parameterized by ``kind`` so a test can model either an ordinary
    ``run-launch`` origin or a CHAINED prior ``run-resume``."""
    entry = build_entry(
        id=JournalEntryId("spin-1", 1),
        ts="2026-08-01T00:00:00.000Z",
        run_id=run_id,
        kind=kind,
        phase=Phase.OUTCOME,
        intent_id=JournalEntryId("spin-1", 0),
        payload={"pid": watched_pid, "harness_run_id": harness_run_id},
    )
    return prepare_for_write(entry).line


def _seed_prior_run(home: Path, slug: str, run_id: str) -> Path:
    """Creates a REAL directory on disk at the prior run's own Tier-3 path
    -- ``_latest_run_dir`` globs the real filesystem directly (no
    directory-listing primitive exists on ``FsPort``; mirrors this
    module's own ``_prior_attempt_keys``/``_large_spec_bytes`` precedent,
    Story 3.6). The caller still configures ``FakeFs.read_text_contents``
    for the journal ``run_resume`` reads back through the injected
    ``fs``."""
    run_dir = (
        home / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "runs" / run_id
    )
    run_dir.mkdir(parents=True)
    return run_dir


def _seed_resolvable_prior_run(
    home: Path, slug: str, fs: FakeFs, *, run_id: str, harness_run_id: str, kind: str = "run-launch"
) -> Path:
    prior_dir = _seed_prior_run(home, slug, run_id)
    fs.read_text_contents[prior_dir / spin_module._JOURNAL_FILENAME] = (
        _outcome_line(run_id, kind=kind, harness_run_id=harness_run_id) + "\n"
    )
    return prior_dir


# --- happy path --------------------------------------------------------------------


def test_resume_happy_path_journals_ad45_fields_and_spawns(home):
    slug = "acme"
    fs = FakeFs(dirs={home})
    _seed_resolvable_prior_run(
        home, slug, fs, run_id="acme-20260801T000000000Z-aaaa", harness_run_id="acme-hh01"
    )
    harness = FakeHarness()
    harness.run_status_snapshot_result = RunStatusSnapshot(
        paused_stage="escalation",
        paused_story_key="3-7-escalation-deferral-and-resume",
        paused_reason="the frozen spec contradicts itself",
        escalated_spec_file="spec-3-7.md",
        # Already re-armed by a human -- EscalationStatus.RESOLVED.
        escalated_task_phase="pending",
        deferred=(),
    )
    harness.resolution_reference_result = "/home/acme-loop/.bmad-loop/runs/acme-hh01/resolve/3-7-escalation-deferral-and-resume/resolution.json"
    process = FakeProcess()

    exit_code = run_resume(_resume_namespace(slug), fs=fs, harness=harness, process=process)

    assert exit_code == EXIT_OK
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    assert [e["kind"] for e in entries] == ["run-resume", "run-resume"]
    intent, outcome = entries
    assert intent["phase"] == "intent"
    assert outcome["phase"] == "outcome"
    assert outcome["intent_id"] == intent["id"]
    assert intent["payload"]["resumed_from_run"] == "acme-20260801T000000000Z-aaaa"
    assert intent["payload"]["harness_run_id"] == "acme-hh01"
    assert intent["payload"]["story_key"] == "3.7"
    assert intent["payload"]["reason"] == "the frozen spec contradicts itself"
    assert intent["payload"]["spec_file"] == "spec-3-7.md"
    assert intent["payload"]["resolution_reference"] == harness.resolution_reference_result
    assert intent["payload"]["resolver"]
    assert outcome["payload"]["pid"] == harness.resume_result
    assert outcome["payload"]["harness_run_id"] == "acme-hh01"
    new_run_dir = spin_module._run_dir(home, slug, intent["run_id"])
    assert harness.resume_calls == [
        {
            "project": home,
            "run_id": "acme-hh01",
            "log_path": new_run_dir / spin_module._LOG_FILENAME,
        }
    ]
    assert harness.resolution_reference_calls == [
        (home, "acme-hh01", "3-7-escalation-deferral-and-resume")
    ]
    assert process.spawn_calls, "a fresh supervisor sidecar is spawned"
    argv = process.spawn_calls[0]["argv"]
    assert argv[:3] == [sys.executable, "-m", "pyforge.marshal.supervisor"]
    assert argv[3] == str(home)
    assert argv[4] == slug
    assert argv[5] == intent["run_id"]
    assert argv[6] == str(harness.resume_result)


def test_resume_proceeds_with_a_null_resolution_reference_when_no_marker_exists(home):
    """I/O matrix: "Resolution marker absent" -- ``resolution_reference:
    null`` in the ``run-resume`` payload; resume still proceeds."""
    slug = "acme"
    fs = FakeFs(dirs={home})
    _seed_resolvable_prior_run(
        home, slug, fs, run_id="acme-20260801T000000000Z-aaaa", harness_run_id="acme-hh01"
    )
    harness = FakeHarness()
    harness.resolution_reference_result = None
    process = FakeProcess()

    exit_code = run_resume(_resume_namespace(slug), fs=fs, harness=harness, process=process)

    assert exit_code == EXIT_OK
    intent = json.loads(fs.appended_lines[0][1])
    assert intent["payload"]["resolution_reference"] is None


def test_resume_picks_the_most_recent_prior_run_when_several_exist(home):
    slug = "acme"
    fs = FakeFs(dirs={home})
    _seed_prior_run(home, slug, "acme-20260801T000000000Z-aaaa")
    _seed_resolvable_prior_run(
        home, slug, fs, run_id="acme-20260802T000000000Z-bbbb", harness_run_id="acme-hh-newer"
    )
    harness = FakeHarness()
    process = FakeProcess()

    exit_code = run_resume(_resume_namespace(slug), fs=fs, harness=harness, process=process)

    assert exit_code == EXIT_OK
    intent = json.loads(fs.appended_lines[0][1])
    assert intent["payload"]["resumed_from_run"] == "acme-20260802T000000000Z-bbbb"
    assert intent["payload"]["harness_run_id"] == "acme-hh-newer"


def test_resume_resolves_harness_run_id_from_a_chained_prior_resume(home):
    """The immediately prior run may itself have been minted by an earlier
    ``marshal factory resume`` -- its own outcome entry carries
    ``harness_run_id`` under ``kind: "run-resume"``, not ``"run-launch"``."""
    slug = "acme"
    fs = FakeFs(dirs={home})
    _seed_resolvable_prior_run(
        home,
        slug,
        fs,
        run_id="acme-20260801T000000000Z-aaaa",
        harness_run_id="acme-hh02",
        kind="run-resume",
    )
    harness = FakeHarness()
    process = FakeProcess()

    exit_code = run_resume(_resume_namespace(slug), fs=fs, harness=harness, process=process)

    assert exit_code == EXIT_OK
    assert harness.resume_calls[0]["run_id"] == "acme-hh02"


def test_resume_resolver_attribution_uses_getpass_getuser(home, monkeypatch):
    monkeypatch.setattr(spin_module.getpass, "getuser", lambda: "operator-42")
    slug = "acme"
    fs = FakeFs(dirs={home})
    _seed_resolvable_prior_run(
        home, slug, fs, run_id="acme-20260801T000000000Z-aaaa", harness_run_id="acme-hh01"
    )
    harness = FakeHarness()
    process = FakeProcess()

    run_resume(_resume_namespace(slug), fs=fs, harness=harness, process=process)

    intent = json.loads(fs.appended_lines[0][1])
    assert intent["payload"]["resolver"] == "operator-42"


def test_resume_resolver_falls_back_to_none_when_getpass_fails(home, monkeypatch):
    """Review finding (Story 3.7 pass 1): ``getpass.getuser()`` can raise
    ``OSError``/``KeyError`` when no pwd entry exists and none of
    LOGNAME/USER/LNAME/USERNAME is set -- a realistic condition in a
    detached/headless automation context, exactly where ``marshal factory
    resume`` is meant to run (AD-22). Must degrade to ``resolver: None``,
    never crash the command with a raw traceback."""

    def _raise():
        raise OSError("no such user")

    monkeypatch.setattr(spin_module.getpass, "getuser", _raise)
    slug = "acme"
    fs = FakeFs(dirs={home})
    _seed_resolvable_prior_run(
        home, slug, fs, run_id="acme-20260801T000000000Z-aaaa", harness_run_id="acme-hh01"
    )
    harness = FakeHarness()
    process = FakeProcess()

    exit_code = run_resume(_resume_namespace(slug), fs=fs, harness=harness, process=process)

    assert exit_code == EXIT_OK
    intent = json.loads(fs.appended_lines[0][1])
    assert intent["payload"]["resolver"] is None


def test_resume_does_not_populate_ad45_fields_for_a_non_escalation_pause(home):
    """Review finding (Story 3.7 pass 1): ``paused_story_key`` is a GENERIC
    field shared by every bmad-loop pause reason (spec-approval,
    epic-boundary, a stories-mode checkpoint...), not just escalation.
    Before this fix, ``run_resume`` populated AD-45's back-reference fields
    for ANY paused_story_key regardless of pause type, producing a
    ``run-resume`` journal entry that looked exactly like an escalation was
    resolved when nothing of the sort happened."""
    slug = "acme"
    fs = FakeFs(dirs={home})
    _seed_resolvable_prior_run(
        home, slug, fs, run_id="acme-20260801T000000000Z-aaaa", harness_run_id="acme-hh01"
    )
    harness = FakeHarness()
    harness.run_status_snapshot_result = RunStatusSnapshot(
        paused_stage="spec-approval",
        paused_story_key="3.9",
        paused_reason="awaiting human plan review",
        escalated_spec_file="spec-3-9.md",
        escalated_task_phase=None,
        deferred=(),
    )
    harness.resolution_reference_result = "should-never-be-read"
    process = FakeProcess()

    exit_code = run_resume(_resume_namespace(slug), fs=fs, harness=harness, process=process)

    assert exit_code == EXIT_OK
    intent = json.loads(fs.appended_lines[0][1])
    assert intent["payload"]["story_key"] is None
    assert intent["payload"]["reason"] is None
    assert intent["payload"]["spec_file"] is None
    assert intent["payload"]["resolution_reference"] is None
    assert harness.resolution_reference_calls == []


def test_resume_warns_and_proceeds_when_live_status_read_fails(home, capsys):
    """Review finding (Story 3.7 pass 1): a live ``run_status_snapshot``
    read failure at exactly this gate must never be SILENT -- the gate's
    whole purpose is to positively confirm the escalation is resolved
    before letting resume proceed. Mirrors AD-32's own "a stale/unreadable
    sample degrades to a registered WARN, never a silent pass" precedent."""
    slug = "acme"
    fs = FakeFs(dirs={home})
    _seed_resolvable_prior_run(
        home, slug, fs, run_id="acme-20260801T000000000Z-aaaa", harness_run_id="acme-hh01"
    )
    harness = FakeHarness()
    harness.run_status_snapshot_result = None
    process = FakeProcess()

    exit_code = run_resume(_resume_namespace(slug), fs=fs, harness=harness, process=process)

    assert exit_code == EXIT_OK
    assert "MRS-SPIN-012" in capsys.readouterr().out
    assert process.spawn_calls, "an unconfirmed (not positively-refused) status must not block resume"


def test_resume_text_output_labels_itself_factory_resume(home, capsys):
    slug = "acme"
    fs = FakeFs(dirs={home})
    _seed_resolvable_prior_run(
        home, slug, fs, run_id="acme-20260801T000000000Z-aaaa", harness_run_id="acme-hh01"
    )
    harness = FakeHarness()
    process = FakeProcess()

    run_resume(_resume_namespace(slug), fs=fs, harness=harness, process=process)

    out = capsys.readouterr().out
    assert out.startswith("factory resume:")
    assert "'acme'" in out


def test_resume_json_envelope_command_is_factory_resume(home, capsys):
    slug = "acme"
    fs = FakeFs(dirs={home})
    _seed_resolvable_prior_run(
        home, slug, fs, run_id="acme-20260801T000000000Z-aaaa", harness_run_id="acme-hh01"
    )
    harness = FakeHarness()
    process = FakeProcess()

    run_resume(_resume_namespace(slug, fmt="json"), fs=fs, harness=harness, process=process)

    envelope = json.loads(capsys.readouterr().out)
    assert envelope["command"] == "factory resume"


# --- refusal: unresolved escalation (MRS-SPIN-010) ----------------------------------


def test_resume_refuses_when_escalation_is_unresolved(home, capsys):
    slug = "acme"
    fs = FakeFs(dirs={home})
    _seed_resolvable_prior_run(
        home, slug, fs, run_id="acme-20260801T000000000Z-aaaa", harness_run_id="acme-hh01"
    )
    harness = FakeHarness()
    harness.run_status_snapshot_result = RunStatusSnapshot(
        paused_stage="escalation",
        paused_story_key="3.7",
        paused_reason="ambiguous",
        escalated_spec_file="spec-3-7.md",
        escalated_task_phase="escalated",
        deferred=(),
    )
    process = FakeProcess()

    exit_code = run_resume(_resume_namespace(slug), fs=fs, harness=harness, process=process)

    assert exit_code == exit_code_for(Verdict.ERROR)
    out = capsys.readouterr().out
    assert "MRS-SPIN-010" in out
    assert fs.appended_lines == []
    assert process.spawn_calls == []
    assert "resume" not in harness.calls
    assert "resolution_reference" not in harness.calls


def test_resume_refusal_never_raises(home):
    """Refusal itself never raises (the I/O matrix's own Error Handling
    column)."""
    slug = "acme"
    fs = FakeFs(dirs={home})
    _seed_resolvable_prior_run(
        home, slug, fs, run_id="acme-20260801T000000000Z-aaaa", harness_run_id="acme-hh01"
    )
    harness = FakeHarness()
    harness.run_status_snapshot_result = RunStatusSnapshot(
        paused_stage="escalation",
        paused_story_key="3.7",
        paused_reason=None,
        escalated_spec_file=None,
        escalated_task_phase="escalated",
        deferred=(),
    )
    process = FakeProcess()
    run_resume(_resume_namespace(slug), fs=fs, harness=harness, process=process)


# --- refusal: no resumable run (MRS-SPIN-011) ----------------------------------------


def test_resume_refuses_when_no_prior_run_exists(home, capsys):
    fs = FakeFs(dirs={home})
    harness = FakeHarness()
    process = FakeProcess()

    exit_code = run_resume(_resume_namespace("acme"), fs=fs, harness=harness, process=process)

    assert exit_code == exit_code_for(Verdict.ERROR)
    out = capsys.readouterr().out
    assert "MRS-SPIN-011" in out
    assert fs.appended_lines == []
    assert process.spawn_calls == []


def test_resume_refuses_when_harness_run_id_cannot_be_resolved(home, capsys):
    slug = "acme"
    fs = FakeFs(dirs={home})
    # A prior run directory exists, but its journal carries no matching
    # outcome entry -- fs.read_text returns None (unconfigured).
    _seed_prior_run(home, slug, "acme-20260801T000000000Z-aaaa")
    harness = FakeHarness()
    process = FakeProcess()

    exit_code = run_resume(_resume_namespace(slug), fs=fs, harness=harness, process=process)

    assert exit_code == exit_code_for(Verdict.ERROR)
    out = capsys.readouterr().out
    assert "MRS-SPIN-011" in out
    assert process.spawn_calls == []


def test_resume_refuses_when_the_prior_journal_read_fails(home, capsys):
    slug = "acme"
    fs = FakeFs(dirs={home})
    _seed_prior_run(home, slug, "acme-20260801T000000000Z-aaaa")
    fs.fail_read_text = FsError("permission denied")
    harness = FakeHarness()
    process = FakeProcess()

    exit_code = run_resume(_resume_namespace(slug), fs=fs, harness=harness, process=process)

    assert exit_code == exit_code_for(Verdict.ERROR)
    assert "MRS-SPIN-011" in capsys.readouterr().out


# --- shared pre-I/O gates (reused codes) ---------------------------------------------


def test_resume_rejects_a_malformed_slug(capsys):
    fs = FakeFs()
    harness = FakeHarness()
    process = FakeProcess()

    exit_code = run_resume(
        _resume_namespace("../escaped"), fs=fs, harness=harness, process=process
    )

    assert exit_code == exit_code_for(Verdict.UNEVALUABLE)
    assert "MRS-SPIN-001" in capsys.readouterr().out
    assert fs.calls == []


def test_resume_rejects_an_unprovisioned_loop_home(capsys):
    fs = FakeFs()  # no dirs at all
    harness = FakeHarness()
    process = FakeProcess()

    exit_code = run_resume(_resume_namespace("acme"), fs=fs, harness=harness, process=process)

    assert exit_code == exit_code_for(Verdict.ERROR)
    assert "MRS-SPIN-002" in capsys.readouterr().out


def test_resume_rejects_a_dangling_tier3_backlink(home, capsys):
    fs = FakeFs(dirs={home})
    fs.tier3_dangling = True

    exit_code = run_resume(
        _resume_namespace("acme"), fs=fs, harness=FakeHarness(), process=FakeProcess()
    )

    assert exit_code == exit_code_for(Verdict.ERROR)
    assert "MRS-SPIN-002" in capsys.readouterr().out


# --- launch/journal failure paths ------------------------------------------------------


def test_resume_launch_failure_journals_a_failed_outcome(home, capsys):
    slug = "acme"
    fs = FakeFs(dirs={home})
    _seed_resolvable_prior_run(
        home, slug, fs, run_id="acme-20260801T000000000Z-aaaa", harness_run_id="acme-hh01"
    )
    harness = FakeHarness()
    harness.fail_resume = HarnessError("cannot launch: bmad-loop not found")
    process = FakeProcess()

    exit_code = run_resume(_resume_namespace(slug), fs=fs, harness=harness, process=process)

    assert exit_code == exit_code_for(Verdict.ERROR)
    assert "MRS-SPIN-003" in capsys.readouterr().out
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    assert [e["kind"] for e in entries] == ["run-resume", "run-resume"]
    assert entries[1]["phase"] == "outcome"
    assert entries[1]["payload"]["pid"] is None
    assert "cannot launch" in entries[1]["payload"]["error"]
    assert process.spawn_calls == []


def test_resume_outcome_write_failure_registers_a_warn_but_still_spawns(home, capsys):
    slug = "acme"
    fs = FakeFs(dirs={home})
    _seed_resolvable_prior_run(
        home, slug, fs, run_id="acme-20260801T000000000Z-aaaa", harness_run_id="acme-hh01"
    )
    # Call #1 is the intent append; call #2 is the outcome append.
    fs.fail_append_line_on_call = 2
    harness = FakeHarness()
    process = FakeProcess()

    exit_code = run_resume(_resume_namespace(slug), fs=fs, harness=harness, process=process)

    assert exit_code == EXIT_OK
    assert "MRS-SPIN-006" in capsys.readouterr().out
    assert process.spawn_calls, "supervisor still spawned despite the journal gap"


def test_resume_supervisor_spawn_failure_registers_a_warn(home, capsys):
    slug = "acme"
    fs = FakeFs(dirs={home})
    _seed_resolvable_prior_run(
        home, slug, fs, run_id="acme-20260801T000000000Z-aaaa", harness_run_id="acme-hh01"
    )
    harness = FakeHarness()
    process = FakeProcess()
    process.fail_spawn = ProcessError("cannot launch: python not found")

    exit_code = run_resume(_resume_namespace(slug), fs=fs, harness=harness, process=process)

    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-SPIN-007" in out
    # Review finding (Story 3.7 pass 1): `_spawn_supervisor_sidecar` is
    # shared with `run_spin`, and its MRS-SPIN-007 message used to hardcode
    # "bmad-loop run launched..." even when reached via `run_resume` -- a
    # misleading diagnostic, since the process actually launched was
    # `bmad-loop resume`.
    assert "bmad-loop resume launched" in out
    assert "bmad-loop run launched" not in out


# --- no --epic/--story/--max-count, no --foreground -----------------------------------


@pytest.mark.parametrize("flag", ["--epic", "--story", "--max-count", "--foreground"])
def test_resume_cli_rejects_spin_only_flags(flag):
    """bmad-loop resume itself ignores scope selectors, rebuilding the
    engine from state-pinned scope only (the spec's own Never clause); no
    synchronous HarnessPort counterpart to resume exists, unlike spin's own
    --foreground."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    spin_module.add_factory_subparser(subparsers)

    argv = ["factory", "resume", "acme", flag]
    if flag in ("--epic", "--max-count"):
        argv.append("1")
    elif flag == "--story":
        argv.append("1.1")

    with pytest.raises(SystemExit):
        parser.parse_args(argv)


def test_resume_cli_accepts_slug_and_format():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    spin_module.add_factory_subparser(subparsers)

    args = parser.parse_args(["factory", "resume", "acme", "--format", "json"])

    assert args.slug == "acme"
    assert args.format == "json"
    assert args.handler is run_resume
