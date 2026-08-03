"""Unit tests for ``pyforge.marshal.supervisor.__main__`` (Story 3.4,
AD-9/AD-20/AD-25/AD-28/AD-30) -- ``run_supervisor``'s full I/O & Edge-Case
Matrix, driven entirely through FAKE ``FsPort``/``ProcessPort``/
``ClockPort``/``SessionObserverPort`` implementations (no real filesystem/
subprocess/clock -- AD-20's own "every supervisor behaviour has a test that
runs in milliseconds"). ``sleep`` is injected as a no-op, and
``FakeProcess.is_alive`` bounds every loop deterministically -- neither
mechanism ever needs a real 60s tick.

This module cannot import ``cli/spin.py``'s own ``FakeFs``/journal-line
helpers (the AD-9 contract this story adds forbids ``supervisor`` from
importing ``pyforge.marshal.cli``, and the fakes below stand in for
``run_supervisor``'s OWN collaborators, not ``run_spin``'s) -- defined here
independently, mirroring ``test_spin.py``'s own per-story-scoped fake
convention.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pyforge.marshal.adapters.fs_local import FsError
from pyforge.marshal.core.journal import (
    JournalEntryId,
    Phase,
    build_entry,
    prepare_for_write,
)
from pyforge.marshal.supervisor import __main__ as supervisor_main
from pyforge.marshal.supervisor.__main__ import main, run_supervisor


class FakeFs:
    """Fakes just the ``FsPort`` surface ``run_supervisor`` reaches:
    ``read_text`` (the one-time journal read), ``append_line`` (every
    ``observation`` entry), and ``write_text_atomic`` (the sidecar branch,
    unreachable by this story's own small payloads but implemented for
    completeness, mirroring ``test_spin.py``'s own ``FakeFs``)."""

    def __init__(
        self,
        *,
        journal_text: str | None = None,
        blobs: dict[Path, str] | None = None,
    ) -> None:
        self.journal_text = journal_text
        # Sidecar blobs, keyed by their FULL path under the run directory.
        # Any path NOT in this map reads back as the journal text, matching
        # this fake's original single-file behaviour.
        self.blobs = dict(blobs or {})
        self.read_text_calls: list[Path] = []
        self.appended_lines: list[tuple[Path, str, bool]] = []
        self.written_texts: dict[Path, str] = {}
        self.fail_read_text: Exception | None = None
        # 1-indexed across every append_line call this fake sees (mirrors
        # test_spin.py's own FakeFs.fail_append_line_on_call convention).
        self.fail_append_line_on_call: int | None = None
        self._append_line_call_count = 0

    def read_text(self, path: Path) -> str | None:
        self.read_text_calls.append(path)
        if self.fail_read_text:
            raise self.fail_read_text
        if self.blobs:
            # FsPort.read_text's own "absent" contract for a blob this test
            # deliberately did not provide.
            return self.blobs.get(path, self.journal_text if path.suffix != ".json" else None)
        return self.journal_text

    def append_line(self, path: Path, line: str, *, fsync: bool) -> None:
        self._append_line_call_count += 1
        if self.fail_append_line_on_call == self._append_line_call_count:
            raise FsError(
                f"simulated failure on append_line call #{self._append_line_call_count}"
            )
        self.appended_lines.append((path, line, fsync))

    def write_text_atomic(self, path: Path, content: str) -> None:
        self.written_texts[path] = content


class FakeProcess:
    """``is_alive`` reports ``True`` for the first ``alive_for`` calls, then
    ``False`` -- the mechanism this story's own tests use to bound
    ``run_supervisor``'s loop deterministically instead of an unbounded
    ``while True`` (see that function's own docstring)."""

    def __init__(self, *, alive_for: int) -> None:
        self.alive_for = alive_for
        self.calls = 0

    def is_alive(self, pid: int) -> bool:
        self.calls += 1
        return self.calls <= self.alive_for


class FakeClock:
    def __init__(self) -> None:
        self.calls = 0

    def now(self) -> datetime:
        self.calls += 1
        return datetime(2026, 8, 3, 5, 45, 12, tzinfo=timezone.utc)


class FakeObserver:
    def __init__(self, *, pane: str | None = None) -> None:
        self.pane = pane
        self.pane_content_calls: list[str] = []
        self.mtime_calls: list[Path] = []

    def pane_content(self, session: str) -> str | None:
        self.pane_content_calls.append(session)
        return self.pane

    def mtime(self, path: Path) -> float | None:
        self.mtime_calls.append(path)
        return None


def _no_sleep(seconds: float) -> None:
    pass


def _launch_outcome_line(run_id: str, *, watched_pid: int = 4242) -> str:
    """A minimal, valid ``phase: outcome, kind: "run-launch"`` journal
    line -- the ONE entry ``run_supervisor``'s own inert-check looks for,
    matching ``cli/spin.py``'s own real payload shape (``{pid,
    harness_run_id}``)."""
    entry = build_entry(
        id=JournalEntryId("spin-1", 1),
        ts="2026-08-03T05:45:00.000Z",
        run_id=run_id,
        kind="run-launch",
        phase=Phase.OUTCOME,
        intent_id=JournalEntryId("spin-1", 0),
        payload={"pid": watched_pid, "harness_run_id": None},
    )
    return prepare_for_write(entry).line


_HOME = Path("/home/acme-loop")
_LOG_PATH = Path("/home/acme-loop/supervisor.log")


# --- normal attach: attach, heartbeat until the harness exits, then detach ----


def test_normal_attach_journals_attach_then_heartbeats_then_detach():
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    process = FakeProcess(alive_for=3)
    clock = FakeClock()
    observer = FakeObserver()

    rc = run_supervisor(
        _HOME,
        "acme",
        "acme-run-1",
        4242,
        _LOG_PATH,
        fs=fs,
        process=process,
        clock=clock,
        observer=observer,
        sleep=_no_sleep,
    )

    assert rc == 0
    # The journal is read exactly ONCE -- no second read anywhere.
    assert len(fs.read_text_calls) == 1

    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    assert [entry["kind"] for entry in entries] == [
        "supervisor-attach",
        "supervisor-heartbeat",
        "supervisor-heartbeat",
        "supervisor-heartbeat",
        "supervisor-detach",
    ]
    # Every write is Phase.OBSERVATION -- fsync=False, no write-before-act.
    assert all(fsync is False for _, _, fsync in fs.appended_lines)
    assert all(entry["phase"] == "observation" for entry in entries)
    assert all(entry["run_id"] == "acme-run-1" for entry in entries)

    supervisor_pid = entries[0]["payload"]["pid"]
    assert entries[0]["payload"] == {"pid": supervisor_pid, "watched_pid": 4242}
    for heartbeat in entries[1:4]:
        assert heartbeat["payload"]["pid"] == supervisor_pid
        assert "sampled_at" in heartbeat["payload"]
    # The first two heartbeats sample a still-alive process; the THIRD is
    # the fresh, contemporaneous reading that discovers the watched process
    # has just exited -- `watched_alive` is a genuine per-tick observation
    # (review finding), never a hardcoded `True` that only a separate
    # `supervisor-detach` entry could ever contradict.
    assert [heartbeat["payload"]["watched_alive"] for heartbeat in entries[1:4]] == [
        True,
        True,
        False,
    ]
    assert entries[-1]["payload"] == {
        "pid": supervisor_pid,
        "reason": "watched-process-exited",
    }

    # The injection seam is proven: clock/observer were actually sampled
    # each tick -- none of these samples drive a decision in this story.
    assert observer.pane_content_calls == ["acme-run-1"] * 3
    assert observer.mtime_calls == [_LOG_PATH] * 3
    assert clock.calls >= 4  # 1 attach ts + 3 heartbeat samples


# --- inert on a run it did not start -------------------------------------------


def test_inert_when_the_journal_does_not_exist_at_all():
    fs = FakeFs(journal_text=None)  # FsPort.read_text's own "absent" contract
    process = FakeProcess(alive_for=5)

    rc = run_supervisor(
        _HOME, "acme", "bogus-run", 1, _LOG_PATH,
        fs=fs, process=process, clock=FakeClock(), observer=FakeObserver(),
        sleep=_no_sleep,
    )

    assert rc == 0
    assert fs.appended_lines == []
    assert process.calls == 0  # is_alive is never even reached


def test_attaches_when_the_journal_has_only_an_intent_entry_and_no_outcome_yet():
    """Review finding: checking ONLY the outcome entry meant that when
    ``cli/spin.py``'s own outcome-journal append itself fails
    (``MRS-SPIN-006`` -- a live harness process already exists, but its
    outcome never made it to disk), this run's own journal carries an
    ``intent`` for ``run-launch`` but no matching ``outcome`` -- and the
    OLD inert-check read that as "not started by Marshal", silently
    abandoning a live, genuinely Marshal-started run with zero supervision.
    AD-6's write-before-act guarantees the intent entry lands BEFORE any
    spawn is even attempted, so it alone is sufficient proof this run is
    Marshal's own; the supervisor must attach normally, not go inert."""
    intent_entry = build_entry(
        id=JournalEntryId("spin-1", 0),
        ts="2026-08-03T05:45:00.000Z",
        run_id="acme-run-1",
        kind="run-launch",
        phase=Phase.INTENT,
        payload={"epic": None, "story": None, "max_count": None, "preview": []},
    )
    fs = FakeFs(journal_text=prepare_for_write(intent_entry).line + "\n")

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        fs=fs, process=FakeProcess(alive_for=0), clock=FakeClock(), observer=FakeObserver(),
        sleep=_no_sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    assert [entry["kind"] for entry in entries] == [
        "supervisor-attach",
        "supervisor-detach",
    ]


def _big_intent_prepared(run_id: str, *, stories: int = 200):
    """A ``phase: intent, kind: "run-launch"`` entry whose payload is big
    enough to be SIDECAR-REFERENCED -- ``cli/spin.py`` puts one rendered
    feed key per RESOLVED story into ``preview``, so the payload grows with
    the project and crosses ``core.journal.SIDECAR_THRESHOLD_BYTES`` at
    roughly 150 stories."""
    entry = build_entry(
        id=JournalEntryId("spin-1", 0),
        ts="2026-08-03T05:45:00.000Z",
        run_id=run_id,
        kind="run-launch",
        phase=Phase.INTENT,
        payload={
            "epic": None,
            "story": None,
            "max_count": None,
            "preview": [
                f"{i // 10 + 1}.{i % 10 + 1}-some-representative-story-slug"
                for i in range(stories)
            ],
        },
    )
    prepared = prepare_for_write(entry)
    assert prepared.sidecar_relative_path is not None, (
        "this fixture is only meaningful if the payload actually crosses "
        "the inline threshold"
    )
    return prepared


def test_attaches_when_the_only_run_launch_entry_is_sidecar_referenced():
    """Follow-up review finding, reproduced live. ``run_supervisor`` used to
    call ``fold(lines)`` with NO ``sidecars`` mapping, on the module
    docstring's stated ground that both ``cli/spin.py`` payloads are
    "always small enough to inline". False for the INTENT payload: its
    ``preview`` list is unbounded (one key per resolved story), so a
    large-enough project writes it as a ``{"sidecar_ref": ...}``
    placeholder, ``fold`` quarantines the line as unresolvable
    (``MRS-JOURNAL-002``), ``by_kind("run-launch")`` comes back EMPTY, and
    the sidecar exits inert.

    That is exactly the ``MRS-SPIN-006`` state the phase-widening exists to
    serve -- the outcome append failed, so the sidecar-referenced intent is
    the ONLY ownership proof on disk -- meaning the largest projects lost
    supervision precisely when their outcome could not be journaled. No
    corruption is involved: it is deterministic on story count."""
    prepared = _big_intent_prepared("acme-run-1")
    run_dir = supervisor_main._run_dir(_HOME, "acme", "acme-run-1")
    fs = FakeFs(
        journal_text=prepared.line + "\n",
        blobs={run_dir / prepared.sidecar_relative_path: prepared.sidecar_content},
    )

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        fs=fs, process=FakeProcess(alive_for=0), clock=FakeClock(),
        observer=FakeObserver(), sleep=_no_sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    assert [entry["kind"] for entry in entries] == [
        "supervisor-attach",
        "supervisor-detach",
    ]
    # The blob is read from the run directory, exactly once, alongside the
    # journal -- never re-read, and never from anywhere else.
    assert fs.read_text_calls == [
        run_dir / supervisor_main._JOURNAL_FILENAME,
        run_dir / prepared.sidecar_relative_path,
    ]


def test_inert_when_a_sidecar_referenced_entry_names_a_different_run():
    """The sidecar resolution must not weaken the ownership check itself --
    a resolvable blob for some OTHER run is still not this run's launch."""
    prepared = _big_intent_prepared("some-other-run")
    run_dir = supervisor_main._run_dir(_HOME, "acme", "acme-run-1")
    fs = FakeFs(
        journal_text=prepared.line + "\n",
        blobs={run_dir / prepared.sidecar_relative_path: prepared.sidecar_content},
    )

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        fs=fs, process=FakeProcess(alive_for=5), clock=FakeClock(),
        observer=FakeObserver(), sleep=_no_sleep,
    )

    assert rc == 0
    assert fs.appended_lines == []


def test_sidecar_refs_rejects_any_ref_that_walks_out_of_the_run_directory():
    """No blob content can redirect this sidecar's control flow (the
    inert-check reads only ``kind``/``phase``/``run_id``, all of which live
    in the journal LINE) -- but the REF itself becomes a path handed to
    ``FsPort.read_text``, so a corrupt or forged one must never point the
    read outside the run directory. ``fold`` independently re-validates
    every ref against its owning entry's id; this is the first gate."""
    def _line(ref: str) -> str:
        return json.dumps({"payload": {"sidecar_ref": ref}})

    hostile = [
        "../../../../etc/passwd",
        "blobs/../../../etc/passwd",
        "/etc/passwd",
        "blobs/",
        "blobs/..",
        "blobs/sub/dir.json",
        "blobs\\evil.json",
    ]
    assert supervisor_main._sidecar_refs([_line(ref) for ref in hostile]) == ()
    # ...while the one real shape prepare_for_write emits is accepted.
    assert supervisor_main._sidecar_refs([_line("blobs/spin-1-0.json")]) == (
        "blobs/spin-1-0.json",
    )


def test_sidecar_refs_skips_unparseable_and_non_placeholder_lines():
    """``fold`` is the one place a malformed line is judged -- this scan
    must never raise on one, and must never mistake a real inline payload
    that merely CARRIES a ``sidecar_ref`` key for a placeholder."""
    lines = [
        "{not valid json at all",
        "",
        json.dumps({"payload": {"sidecar_ref": "blobs/a-0.json", "extra": 1}}),
        json.dumps({"payload": {"sidecar_ref": 42}}),
        json.dumps({"payload": "sidecar_ref not even a mapping"}),
        json.dumps(["sidecar_ref"]),
    ]
    assert supervisor_main._sidecar_refs(lines) == ()


def test_a_missing_sidecar_blob_still_leaves_the_supervisor_inert():
    """An unreadable/absent blob maps to ``None``, which ``fold`` treats
    exactly as it already treats an absent one -- the line quarantines and
    the sidecar stays inert (and now SAYS so), rather than crashing."""
    prepared = _big_intent_prepared("acme-run-1")
    fs = FakeFs(journal_text=prepared.line + "\n", blobs={})
    fs.blobs = {Path("/nowhere.json"): "{}"}  # non-empty, but not the real ref

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        fs=fs, process=FakeProcess(alive_for=5), clock=FakeClock(),
        observer=FakeObserver(), sleep=_no_sleep,
    )

    assert rc == 0
    assert fs.appended_lines == []


def test_inert_when_the_journal_read_raises_a_plain_value_error():
    """Follow-up review finding: ``LocalFs.read_text`` translates only
    ``(OSError, UnicodeDecodeError)`` into ``FsError``, but an embedded NUL
    byte in a path makes ``Path.read_text`` raise a PLAIN ``ValueError`` --
    the same CPython split this story already guards at ``spawn_detached``'s
    ``open()`` and in both ``observer_mux`` methods. Unreachable through
    ``main()`` (``execve`` argv cannot carry a NUL) but this is the FIRST
    call ``run_supervisor`` makes, and it is a public function."""
    fs = FakeFs()
    fs.fail_read_text = ValueError("embedded null byte")

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 1, _LOG_PATH,
        fs=fs, process=FakeProcess(alive_for=5), clock=FakeClock(),
        observer=FakeObserver(), sleep=_no_sleep,
    )

    assert rc == 0
    assert fs.appended_lines == []


def test_inert_when_the_outcome_entry_belongs_to_a_different_run_id():
    """Defense in depth: the outcome entry's own ``run_id`` must match the
    run this supervisor was told to watch, not merely exist somewhere in the
    file."""
    fs = FakeFs(journal_text=_launch_outcome_line("some-other-run") + "\n")

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 1, _LOG_PATH,
        fs=fs, process=FakeProcess(alive_for=5), clock=FakeClock(), observer=FakeObserver(),
        sleep=_no_sleep,
    )

    assert rc == 0
    assert fs.appended_lines == []


def test_inert_when_the_journal_read_itself_fails():
    """Cannot even determine whether this run is Marshal's own -- the safe
    reading is to stay inert rather than assume ownership this read cannot
    prove."""
    fs = FakeFs()
    fs.fail_read_text = FsError("Permission denied")

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 1, _LOG_PATH,
        fs=fs, process=FakeProcess(alive_for=5), clock=FakeClock(), observer=FakeObserver(),
        sleep=_no_sleep,
    )

    assert rc == 0
    assert fs.appended_lines == []


# --- watched process already dead at the first check --------------------------


def test_watched_process_already_dead_journals_attach_then_immediately_detach():
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    process = FakeProcess(alive_for=0)  # is_alive() is False on the FIRST call

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        fs=fs, process=process, clock=FakeClock(), observer=FakeObserver(),
        sleep=_no_sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    assert [entry["kind"] for entry in entries] == [
        "supervisor-attach",
        "supervisor-detach",
    ]
    assert process.calls == 1


# --- journal append fails mid-loop ---------------------------------------------


def test_journal_append_failure_mid_loop_exits_nonzero_and_stops_looping():
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    # append #1 (attach) succeeds; append #2 (the first heartbeat) fails.
    fs.fail_append_line_on_call = 2
    process = FakeProcess(alive_for=10)

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        fs=fs, process=process, clock=FakeClock(), observer=FakeObserver(),
        sleep=_no_sleep,
    )

    assert rc != 0
    # Only the attach entry actually landed durably.
    assert len(fs.appended_lines) == 1
    assert json.loads(fs.appended_lines[0][1])["kind"] == "supervisor-attach"
    # The loop stopped at the FIRST failure -- it never looped forever
    # against a broken journal. Two is_alive calls total: the pre-loop
    # check that admits the first tick, then the one fresh reading taken
    # inside that tick (now doubling as both the heartbeat's own
    # `watched_alive` value and the loop's continuation decision) whose
    # resulting heartbeat append is the one that fails.
    assert process.calls == 2


def test_journal_append_failure_prints_a_diagnostic_to_stderr(capsys):
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    fs.fail_append_line_on_call = 1  # even the attach entry itself fails

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        fs=fs, process=FakeProcess(alive_for=5), clock=FakeClock(), observer=FakeObserver(),
        sleep=_no_sleep,
    )

    assert rc != 0
    err = capsys.readouterr().err
    assert "cannot append" in err.lower()


# --- multiplexer pane unavailable ----------------------------------------------


def test_pane_unavailable_the_tick_proceeds_without_it():
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    process = FakeProcess(alive_for=1)
    observer = FakeObserver(pane=None)  # "no session by that name"

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        fs=fs, process=process, clock=FakeClock(), observer=observer,
        sleep=_no_sleep,
    )

    assert rc == 0
    assert observer.pane_content_calls == ["acme-run-1"]
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    assert [entry["kind"] for entry in entries] == [
        "supervisor-attach",
        "supervisor-heartbeat",
        "supervisor-detach",
    ]


# --- main(): argv parsing + dispatch --------------------------------------------


def test_main_parses_argv_and_dispatches_to_run_supervisor(monkeypatch):
    calls: list[tuple[Path, str, str, int, Path]] = []

    def _fake_run_supervisor(home, slug, run_id, watched_pid, log_path):
        calls.append((home, slug, run_id, watched_pid, log_path))
        return 0

    monkeypatch.setattr(supervisor_main, "run_supervisor", _fake_run_supervisor)

    rc = main(["/home/acme-loop", "acme", "acme-run-1", "4242", "/home/acme-loop/supervisor.log"])

    assert rc == 0
    assert calls == [
        (Path("/home/acme-loop"), "acme", "acme-run-1", 4242, Path("/home/acme-loop/supervisor.log"))
    ]


def test_main_rejects_the_wrong_argument_count(capsys):
    rc = main(["only", "two"])
    assert rc != 0
    assert "usage" in capsys.readouterr().err.lower()


def test_main_rejects_a_non_integer_watched_pid(capsys):
    rc = main(["/home", "acme", "acme-run-1", "not-a-pid", "/home/supervisor.log"])
    assert rc != 0
    assert "invalid watched pid" in capsys.readouterr().err.lower()


def test_main_rejects_a_zero_or_negative_watched_pid(capsys):
    """Review finding: ``os.kill(pid, 0)`` gives ``0``/negative pids
    special "signal a process GROUP" semantics rather than "no such
    process" -- a malformed invocation naming one of them must be refused
    cleanly rather than let ``is_alive`` silently probe an unintended
    target."""
    for bad_pid in ("0", "-1"):
        rc = main(["/home", "acme", "acme-run-1", bad_pid, "/home/supervisor.log"])
        assert rc != 0
        assert "must be positive" in capsys.readouterr().err.lower()


def test_main_rejects_a_slug_that_escapes_the_run_directory(capsys):
    """Follow-up review finding (both reviewers): ``main()`` guarded
    ``watched_pid`` for the "malformed direct invocation" reachability class
    while leaving the two arguments that actually become PATH SEGMENTS of
    the journal (``slug``, ``run_id``) entirely unvalidated. ``_run_dir``
    composes them straight into a path, and ``FsPort.append_line`` opens
    ``O_CREAT`` -- so a traversing slug pointed this sidecar's reads and
    appends outside the run directory. ``cli/spin.py`` refuses a malformed
    slug via this same ``core.policy._is_valid_project_slug`` before ANY
    filesystem touch; this second entry point re-derives the identical paths
    and now applies the identical gate."""
    for bad_slug in ("../../../../tmp/evil", "..", "acme/../..", ""):
        rc = main(["/home/acme-loop", bad_slug, "acme-run-1", "4242", "/home/s.log"])
        assert rc != 0, f"slug {bad_slug!r} was accepted"
        assert "invalid project slug" in capsys.readouterr().err.lower()


def test_main_rejects_a_run_id_that_escapes_the_run_directory(capsys):
    """The ``run_id`` half of the same finding: it is the LAST path segment
    of the run directory, so a separator or a dot-segment in it relocates
    the journal just as effectively as a traversing slug does."""
    for bad_run_id in ("../../evil", "..", ".", "acme/run", "", "a\\b"):
        rc = main(["/home/acme-loop", "acme", bad_run_id, "4242", "/home/s.log"])
        assert rc != 0, f"run_id {bad_run_id!r} was accepted"
        assert "invalid run id" in capsys.readouterr().err.lower()


def test_main_accepts_a_real_spin_minted_run_id(monkeypatch):
    """Negative control for the two guards above -- the real ``run_id``
    shape ``cli/spin.py`` mints (``<slug>-<timestamp>-<suffix>``) must still
    pass, or the guards would have broken every genuine invocation."""
    calls: list[str] = []

    def _fake_run_supervisor(home, slug, run_id, watched_pid, log_path):
        calls.append(run_id)
        return 0

    monkeypatch.setattr(supervisor_main, "run_supervisor", _fake_run_supervisor)
    rc = main(
        ["/home/acme-loop", "acme", "acme-20260803T101112000Z-abcd1234", "4242", "/home/s.log"]
    )
    assert rc == 0
    assert calls == ["acme-20260803T101112000Z-abcd1234"]


def test_inert_exit_prints_a_diagnostic_naming_the_run(capsys):
    """Follow-up review finding: the inert exit was COMPLETELY silent -- no
    journal write (correct, per the AC) but also nothing on this process's
    own stderr, which is redirected to ``supervisor.log`` and is the only
    diagnostic channel a detached sidecar has. An operator holding that log
    saw an empty file and could not tell the run had been examined at all."""
    fs = FakeFs(journal_text=_launch_outcome_line("some-other-run") + "\n")

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242,
        _LOG_PATH,
        fs=fs, process=FakeProcess(alive_for=1), clock=FakeClock(),
        observer=FakeObserver(), sleep=_no_sleep,
    )

    assert rc == 0
    assert fs.appended_lines == []
    err = capsys.readouterr().err
    assert "acme-run-1" in err
    assert "not a run marshal started" in err.lower()


def test_inert_exit_on_a_quarantined_journal_says_so_distinctly(capsys):
    """The half of the already-deferred quarantine finding that IS this
    story's to fix: when ``fold`` cannot evaluate the run-launch line (a
    torn append, a stray non-JSON byte), ``by_kind`` comes back empty and
    this sidecar stays inert on a run Marshal genuinely DID start. Making
    such a line recoverable is the separately-logged deferred item; making
    the two causes distinguishable in the log is not, and used to be
    impossible -- both exits printed nothing at all."""
    fs = FakeFs(journal_text="{not valid json at all\n")

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242,
        _LOG_PATH,
        fs=fs, process=FakeProcess(alive_for=1), clock=FakeClock(),
        observer=FakeObserver(), sleep=_no_sleep,
    )

    assert rc == 0
    assert fs.appended_lines == []
    err = capsys.readouterr().err
    assert "unevaluable" in err.lower()
    assert "1 journal line" in err.lower()
