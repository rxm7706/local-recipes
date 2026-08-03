"""Unit tests for ``pyforge.marshal.supervisor.__main__`` (Story 3.4/3.5,
AD-9/AD-20/AD-25/AD-28/AD-30) -- ``run_supervisor``'s full I/O & Edge-Case
Matrix, driven entirely through FAKE ``FsPort``/``ProcessPort``/
``ClockPort``/``SessionObserverPort``/``HarnessPort`` implementations (no
real filesystem/subprocess/clock -- AD-20's own "every supervisor behaviour
has a test that runs in milliseconds"). ``sleep`` is injected as a no-op
(or, for the idle-ladder tests, paired with an ``AdvancingClock`` that
treats one ``sleep`` call as one tick's worth of elapsed wall-clock time),
and ``FakeProcess.is_alive`` bounds every loop deterministically -- neither
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
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jsonschema
from pyforge.marshal.adapters.fs_local import FsError
from pyforge.marshal.adapters.harness_bmadloop import HarnessError
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
    ``observation``/``intent``/``outcome`` entry), and
    ``write_text_atomic`` (the sidecar branch, unreachable by this story's
    own small payloads but implemented for completeness, mirroring
    ``test_spin.py``'s own ``FakeFs``)."""

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


class AdvancingClock:
    """A clock paired with a ``sleep`` callable (``.sleep``) that advances
    it by exactly the amount ``sleep`` was asked to wait for -- so one
    ``sleep(_TICK_SECONDS)`` call equals one tick's worth of elapsed
    wall-clock time, decoupled from how many OTHER ``.now()`` calls happen
    inside that same tick for journal-entry timestamping. This is what lets
    the idle-ladder tests below control elapsed time precisely: every
    ``.now()`` call within one tick (the sample, any ladder intent/outcome,
    the heartbeat) returns the SAME value, exactly mirroring a real
    supervisor where ``time.sleep(60)`` genuinely advances the wall clock
    once per tick and every read within that tick happens back-to-back."""

    def __init__(self, *, start: datetime | None = None) -> None:
        self._now = start if start is not None else datetime(2026, 8, 3, 5, 45, 12, tzinfo=timezone.utc)
        self.calls = 0

    def now(self) -> datetime:
        self.calls += 1
        return self._now

    def sleep(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)


class FakeObserver:
    def __init__(
        self,
        *,
        pane: str | None = None,
        pane_sequence: list[str | None] | None = None,
        send_text_result: bool = True,
    ) -> None:
        self.pane = pane
        self.pane_sequence = pane_sequence
        self.pane_content_calls: list[str] = []
        self.mtime_calls: list[Path] = []
        self.send_text_calls: list[tuple[str, str]] = []
        self.send_text_result = send_text_result

    def pane_content(self, session: str) -> str | None:
        self.pane_content_calls.append(session)
        if self.pane_sequence is not None:
            index = len(self.pane_content_calls) - 1
            return self.pane_sequence[min(index, len(self.pane_sequence) - 1)]
        return self.pane

    def mtime(self, path: Path) -> float | None:
        self.mtime_calls.append(path)
        return None

    def send_text(self, session: str, text: str) -> bool:
        self.send_text_calls.append((session, text))
        return self.send_text_result


class FakeHarness:
    """Fakes ``HarnessPort``'s ``stop``/``resume`` -- the idle ladder's
    ``stop-and-retry`` rung. Defaults to succeeding (``stop`` returns
    ``True``, ``resume`` returns ``resume_result``); a test injects
    ``fail_stop``/``fail_resume`` to exercise the ``HarnessError`` path, or
    sets ``stop_result = False`` to model ``stop()``'s own documented "the
    run had already finished" outcome (not an exception -- see that port
    method's own docstring)."""

    def __init__(self) -> None:
        self.stop_calls: list[tuple[Path, str]] = []
        self.resume_calls: list[dict[str, object]] = []
        self.fail_stop: Exception | None = None
        self.fail_resume: Exception | None = None
        self.stop_result: bool = True
        self.resume_result: int = 555555

    def stop(self, project: Path, run_id: str) -> bool:
        self.stop_calls.append((project, run_id))
        if self.fail_stop:
            raise self.fail_stop
        return self.stop_result

    def resume(self, project: Path, run_id: str, *, log_path: Path) -> int:
        self.resume_calls.append({"project": project, "run_id": run_id, "log_path": log_path})
        if self.fail_resume:
            raise self.fail_resume
        return self.resume_result


def _no_sleep(seconds: float) -> None:
    pass


class RecordingSleep:
    """A no-op ``sleep`` that RECORDS what it was asked to wait for.

    Review finding: ``_no_sleep`` discards its argument and no test read it
    back, so ``sleep(_TICK_SECONDS)`` could be deleted from the loop
    outright -- or handed ``0`` -- with all of this module green (every
    loop here is bounded by ``FakeProcess.is_alive``, never by sleeping).
    A real supervisor would then busy-spin: a ``tmux`` fork/exec, an
    ``os.kill``, a ``Path.stat`` and one journal append per iteration at
    disk speed, for the whole life of the run. ``_TICK_SECONDS`` was read
    by exactly one other test, which only compares it to another constant
    -- the "two constants, one of which nothing reads" shape that test's
    own docstring levels at ITS predecessor."""

    def __init__(self) -> None:
        self.seconds: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.seconds.append(seconds)


# A realistic harness-minted run id shape (the harness's OWN self-minted id
# -- confirmed live as `f"{project}-{utc_compact}-{token}"` -- distinct from
# Marshal's own journal run_id). Used as the DEFAULT harness_run_id for
# `_launch_outcome_line` below, since Story 3.5's ladder is the interesting
# behaviour most tests in this file now exercise (harmlessly inert, given
# every pre-existing test's own FakeClock never advances -- see that class).
_HARNESS_RUN_ID = "acme-20260803T054512123Z-ab12cd"
_SESSION_NAME = f"bmad-loop-{_HARNESS_RUN_ID}"


def _launch_outcome_line(
    run_id: str, *, watched_pid: int = 4242, harness_run_id: str | None = _HARNESS_RUN_ID
) -> str:
    """A minimal, valid ``phase: outcome, kind: "run-launch"`` journal
    line -- the ONE entry ``run_supervisor``'s own inert-check looks for,
    matching ``cli/spin.py``'s own real payload shape (``{pid,
    harness_run_id}``). Defaults to a REAL ``harness_run_id`` so the idle
    ladder is active by default (Story 3.5) -- pass ``harness_run_id=None``
    to exercise the "unavailable" scenario instead."""
    entry = build_entry(
        id=JournalEntryId("spin-1", 1),
        ts="2026-08-03T05:45:00.000Z",
        run_id=run_id,
        kind="run-launch",
        phase=Phase.OUTCOME,
        intent_id=JournalEntryId("spin-1", 0),
        payload={"pid": watched_pid, "harness_run_id": harness_run_id},
    )
    return prepare_for_write(entry).line


_HOME = Path("/home/acme-loop")
_LOG_PATH = Path("/home/acme-loop/supervisor.log")
# A large, inert-by-default idle threshold (25 minutes, matching
# core.policy's own default) -- with the non-advancing `FakeClock`, elapsed
# is always 0 regardless of this value, so every pre-existing (non-ladder)
# test in this file stays behaviourally unaffected by the ladder's addition.
_IDLE_THRESHOLD_MINUTES = 25.0

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "pyforge"
    / "marshal"
    / "schemas"
    / "journal.json"
)


def _journal_schema() -> dict[str, object]:
    """The packaged, frozen journal-entry contract -- ``test_journal.py``'s
    own helper, reused here because the supervisor is the FIRST writer of
    ``Phase.OBSERVATION`` entries into a real journal and no test on this
    side ever validated one against it (review finding). ``test_journal.py``
    validates its own SYNTHETIC entries; this validates the ones production
    code actually builds."""
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _run_dir() -> Path:
    return supervisor_main._run_dir(_HOME, "acme", "acme-run-1")


def _harness_log_path() -> Path:
    return _run_dir() / supervisor_main._HARNESS_LOG_FILENAME


# --- normal attach: attach, heartbeat until the harness exits, then detach ----


def test_normal_attach_journals_attach_then_heartbeats_then_detach():
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    process = FakeProcess(alive_for=3)
    clock = FakeClock()
    observer = FakeObserver()
    sleep = RecordingSleep()

    rc = run_supervisor(
        _HOME,
        "acme",
        "acme-run-1",
        4242,
        _LOG_PATH,
        _IDLE_THRESHOLD_MINUTES,
        fs=fs,
        process=process,
        clock=clock,
        observer=observer,
        sleep=sleep,
    )

    assert rc == 0
    # The journal is read exactly ONCE -- no second read anywhere -- and
    # from the ONE path this run's own `_run_dir`/`_JOURNAL_FILENAME`
    # compose (review finding: this asserted only the COUNT, so a
    # regression that read some other path entirely -- a dropped `runs/`
    # segment, `run_dir` itself -- still received this fake's journal text
    # and passed every assertion below).
    _journal_path = (
        supervisor_main._run_dir(_HOME, "acme", "acme-run-1")
        / supervisor_main._JOURNAL_FILENAME
    )
    assert fs.read_text_calls == [_journal_path]
    # Every append lands in that same journal -- the WRITE half of the same
    # pin (review finding: every assertion here unpacked `_, line, _`, so
    # `_append` could have written to `observations.jsonl`, to `log_path`,
    # or to a bare relative path with the whole suite green, and AD-25's
    # single source of run truth would silently carry no supervision
    # record at all).
    assert {path for path, _, _ in fs.appended_lines} == {_journal_path}
    # One real 60s tick per heartbeat -- not zero, and not some other
    # interval (review finding: nothing read this back, so deleting the
    # sleep entirely left a busy-spinning supervisor and a green suite).
    assert sleep.seconds == [supervisor_main._TICK_SECONDS] * 3

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
    # each tick the ladder actually ran, against the REAL session/log target
    # (Story 3.5, closing Story 3.4's own placeholder gaps) -- only TWO of
    # the three ticks, not three (review finding): the ladder block is now
    # gated on that SAME tick's own fresh `watched_alive` (patch: it must
    # never fire against a process that has already exited), so the third
    # tick -- the one whose heartbeat above reports `watched_alive: False`
    # -- skips sampling entirely rather than needlessly probing a session
    # for a process already known to be gone. The non-advancing FakeClock
    # means no ladder ACTION would have fired regardless (elapsed is always
    # 0); this is purely about how many ticks even attempt the sample.
    assert observer.pane_content_calls == [_SESSION_NAME] * 2
    assert observer.mtime_calls == [_harness_log_path()] * 2
    assert clock.calls >= 4  # 1 attach ts + 3 heartbeat samples

    # Every line this sidecar writes conforms to the packaged, frozen
    # journal contract (review finding: nothing on this side validated a
    # supervisor-written line against `schemas/journal.json`, although the
    # supervisor is the first producer of `Phase.OBSERVATION` entries and
    # the schema is `additionalProperties: false` with an `allOf` rule
    # forbidding `intent_id` on a non-outcome entry -- a break would have
    # surfaced only in whichever later story first read the file back).
    schema = _journal_schema()
    for entry in entries:
        jsonschema.validate(instance=entry, schema=schema)


# --- inert on a run it did not start -------------------------------------------


def test_inert_when_the_journal_does_not_exist_at_all():
    fs = FakeFs(journal_text=None)  # FsPort.read_text's own "absent" contract
    process = FakeProcess(alive_for=5)

    rc = run_supervisor(
        _HOME, "acme", "bogus-run", 1, _LOG_PATH, _IDLE_THRESHOLD_MINUTES,
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
    Marshal's own; the supervisor must attach normally, not go inert. Since
    the intent entry carries no ``harness_run_id`` field at all, the ladder
    is ALSO unavailable here (Story 3.5's own MRS-SUPV-003 scenario)."""
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, _IDLE_THRESHOLD_MINUTES,
        fs=fs, process=FakeProcess(alive_for=0), clock=FakeClock(), observer=FakeObserver(),
        sleep=_no_sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    assert [entry["kind"] for entry in entries] == [
        "supervisor-attach",
        "idle-harness-run-id-unavailable",
        "supervisor-detach",
    ]
    assert entries[1]["payload"]["finding"]["code"] == "MRS-SUPV-003"


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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, _IDLE_THRESHOLD_MINUTES,
        fs=fs, process=FakeProcess(alive_for=0), clock=FakeClock(),
        observer=FakeObserver(), sleep=_no_sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    assert [entry["kind"] for entry in entries] == [
        "supervisor-attach",
        "idle-harness-run-id-unavailable",
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, _IDLE_THRESHOLD_MINUTES,
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, _IDLE_THRESHOLD_MINUTES,
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
        _HOME, "acme", "acme-run-1", 1, _LOG_PATH, _IDLE_THRESHOLD_MINUTES,
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
        _HOME, "acme", "acme-run-1", 1, _LOG_PATH, _IDLE_THRESHOLD_MINUTES,
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
        _HOME, "acme", "acme-run-1", 1, _LOG_PATH, _IDLE_THRESHOLD_MINUTES,
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, _IDLE_THRESHOLD_MINUTES,
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, _IDLE_THRESHOLD_MINUTES,
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, _IDLE_THRESHOLD_MINUTES,
        fs=fs, process=FakeProcess(alive_for=5), clock=FakeClock(), observer=FakeObserver(),
        sleep=_no_sleep,
    )

    assert rc != 0
    err = capsys.readouterr().err
    assert "cannot append" in err.lower()


# --- multiplexer pane unavailable ----------------------------------------------


def test_pane_unavailable_the_tick_proceeds_without_it():
    # alive_for=2, not 1 (review finding): the ladder block is now gated on
    # THIS tick's own fresh `watched_alive` -- with alive_for=1 the single
    # tick would ALSO be the one that discovers the process just exited, so
    # the ladder (and its pane sample) would be skipped entirely and this
    # test would no longer exercise "pane unavailable" at all. Two ticks
    # keeps the first one (where the pane really is sampled and found
    # unavailable) alive, with the second discovering the exit.
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    process = FakeProcess(alive_for=2)
    observer = FakeObserver(pane=None)  # "no session by that name"

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, _IDLE_THRESHOLD_MINUTES,
        fs=fs, process=process, clock=FakeClock(), observer=observer,
        sleep=_no_sleep,
    )

    assert rc == 0
    assert observer.pane_content_calls == [_SESSION_NAME]
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    assert [entry["kind"] for entry in entries] == [
        "supervisor-attach",
        "supervisor-heartbeat",
        "supervisor-heartbeat",
        "supervisor-detach",
    ]


# --- Story 3.5: harness_run_id unavailable --------------------------------------


def test_harness_run_id_unavailable_journals_once_and_stays_heartbeat_only():
    """I/O matrix: the run-launch outcome entry's own ``harness_run_id``
    field is ``None`` -- a registered finding is journaled once at attach,
    and the tick loop continues heartbeats only; ``evaluate_idle`` is never
    consulted for this run."""
    fs = FakeFs(
        journal_text=_launch_outcome_line("acme-run-1", harness_run_id=None) + "\n"
    )
    process = FakeProcess(alive_for=2)
    observer = FakeObserver(pane="unchanged")

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, _IDLE_THRESHOLD_MINUTES,
        fs=fs, process=process, clock=FakeClock(), observer=observer,
        sleep=_no_sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    assert [entry["kind"] for entry in entries] == [
        "supervisor-attach",
        "idle-harness-run-id-unavailable",
        "supervisor-heartbeat",
        "supervisor-heartbeat",
        "supervisor-detach",
    ]
    unavailable = entries[1]
    assert unavailable["phase"] == "observation"
    assert unavailable["payload"]["finding"]["code"] == "MRS-SUPV-003"
    assert unavailable["payload"]["finding"]["severity"] == "warn"
    # The ladder is NEVER consulted for this run -- no pane/mtime sample is
    # even attempted (there is no valid session/log target to sample).
    assert observer.pane_content_calls == []
    assert observer.mtime_calls == []
    assert entries[-1]["payload"]["reason"] == "watched-process-exited"


def test_harness_run_id_blank_string_is_also_unavailable():
    """Defense in depth: an empty-string ``harness_run_id`` (a malformed or
    truncated write) is treated identically to ``None`` -- never used as a
    session-name fragment."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1", harness_run_id="") + "\n")

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, _IDLE_THRESHOLD_MINUTES,
        fs=fs, process=FakeProcess(alive_for=1), clock=FakeClock(), observer=FakeObserver(),
        sleep=_no_sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    assert entries[1]["kind"] == "idle-harness-run-id-unavailable"


# --- Story 3.5: the idle ladder itself ------------------------------------------


def test_first_threshold_crossing_fires_a_nudge_intent_then_outcome():
    """I/O matrix: no change for >= 1x threshold, last acted rung is NONE
    -> the ladder fires ``nudge``: ``idle-nudge`` intent then outcome
    journaled; ``send_text`` called against the resolved window."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")  # never changes -- keeps accumulating
    # threshold_s = 150 (2.5min) against a 60s tick. Corrected comment
    # (review finding): elapsed is measured from the FIRST SAMPLE's own
    # moment, not from tick-zero -- and that first sample is captured only
    # AFTER tick 1's own sleep, i.e. at t=60s, not t=0s. So tick 4 (t=240s)
    # crosses the threshold at elapsed = 240s - 60s = 180s, 180/150 = 1.2 ->
    # rung 1 -- NOT the "240/150 = 1.6" a tick-zero basis would suggest
    # (both floor to the same rung here, which is why this test stayed
    # correct despite the comment's wrong reasoning). Ticks 1-3 stay under
    # one threshold; tick 5 stays at the SAME rung (no re-fire).
    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 2.5,
        fs=fs, process=FakeProcess(alive_for=5), clock=clock, observer=observer,
        sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    kinds = [entry["kind"] for entry in entries]
    assert kinds.count("idle-nudge") == 2  # one intent, one outcome
    assert kinds == [
        "supervisor-attach",
        "supervisor-heartbeat",
        "supervisor-heartbeat",
        "supervisor-heartbeat",
        "idle-nudge",
        "idle-nudge",
        "supervisor-heartbeat",
        "supervisor-heartbeat",
        "supervisor-detach",
    ]
    intent, outcome = (entry for entry in entries if entry["kind"] == "idle-nudge")
    assert intent["phase"] == "intent"
    assert outcome["phase"] == "outcome"
    assert outcome["intent_id"] == intent["id"]
    assert intent["payload"] == {"session": _SESSION_NAME}
    assert outcome["payload"] == {"sent": True}
    assert observer.send_text_calls == [(_SESSION_NAME, supervisor_main._NUDGE_TEXT)]
    # fsync discipline: intent True (write-before-act), outcome False.
    intent_index = entries.index(intent)
    outcome_index = entries.index(outcome)
    assert fs.appended_lines[intent_index][2] is True
    assert fs.appended_lines[outcome_index][2] is False


def test_nudge_send_failure_registers_a_finding_but_still_advances_bookkeeping():
    """I/O matrix: ``send_text`` failure (no window resolves) is a
    registered finding, ladder still advances its own "last acted"
    bookkeeping so it doesn't retry nudge every tick."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle", send_text_result=False)

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 2.5,
        fs=fs, process=FakeProcess(alive_for=5), clock=clock, observer=observer,
        sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    nudge_outcomes = [e for e in entries if e["kind"] == "idle-nudge" and e["phase"] == "outcome"]
    assert len(nudge_outcomes) == 1  # not retried on tick 5, the same rung
    assert nudge_outcomes[0]["payload"]["sent"] is False
    assert nudge_outcomes[0]["payload"]["finding"]["code"] == "MRS-SUPV-001"
    assert nudge_outcomes[0]["payload"]["finding"]["severity"] == "warn"


def test_fresh_output_after_nudge_resets_the_window():
    """I/O matrix: a later sample's pane/mtime differs from its predecessor
    -> idle-elapsed and last-acted rung both reset to zero/NONE -- no
    further ladder action until a fresh full threshold elapses."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    # Ticks 1-4: "idle" (nudge fires at tick 4, elapsed=180s/150s=1.2).
    # Tick 5: "responded" -- a change, resetting the window.
    # Ticks 6-8: "responded" again (no further change) -- elapsed since the
    # reset reaches 180s by tick 8 (300-... wait: reference becomes tick5's
    # own moment; tick8 moment is 3 ticks later = 180s -> rung 1 (NUDGE)
    # again, proving the re-arm allowed a SECOND nudge.
    observer = FakeObserver(pane_sequence=["idle"] * 4 + ["responded"] * 4)

    # alive_for=9, not 8 (review finding): the ladder -- including the
    # SECOND nudge this test's whole point is to prove fires -- is now
    # gated on THIS tick's own fresh `watched_alive`, so tick 8 (where it
    # fires) must not be the LAST tick `FakeProcess` reports alive for.
    # `FakeObserver.pane_sequence` clamps to its last element for any tick
    # index beyond its own length, so the harmless extra 9th tick just
    # samples "responded" again.
    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 2.5,
        fs=fs, process=FakeProcess(alive_for=9), clock=clock, observer=observer,
        sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    nudge_intents = [e for e in entries if e["kind"] == "idle-nudge" and e["phase"] == "intent"]
    assert len(nudge_intents) == 2, "the reset must allow a SECOND nudge to fire"
    assert observer.send_text_calls == [
        (_SESSION_NAME, supervisor_main._NUDGE_TEXT),
        (_SESSION_NAME, supervisor_main._NUDGE_TEXT),
    ]


def test_second_threshold_crossing_fires_stop_and_retry():
    """I/O matrix: no change for >= 2x threshold since last reset -> the
    ladder fires ``stop-and-retry``: ``HarnessPort.stop`` then ``.resume``;
    ``watched_pid`` updated; ``idle-stop-and-retry`` intent/outcome
    journaled with ``{old_pid, new_pid}``; sample history cleared."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    # threshold_s = 90 (1.5min): tick3 crosses NUDGE(1), tick4 crosses
    # STOP_AND_RETRY(2). alive_for=8, not 4 (review finding): the ladder
    # block -- including this tick's own STOP_AND_RETRY action -- is now
    # gated on THIS tick's fresh `watched_alive`, so the firing tick must
    # not be the LAST one `FakeProcess` reports alive for, or the action
    # never runs at all. A generous margin (rather than the exact minimal
    # value) avoids coupling this test to the "one extra is_alive call is
    # consumed recomputing watched_alive after a successful pid swap"
    # mechanic (a separate fix): the loop simply keeps heartbeating a few
    # more ticks on the new pid's fresh (well under one threshold) idle
    # window and then exits naturally via "watched-process-exited" once
    # this budget is exhausted -- `stop`/`resume` are still each called
    # exactly once, which is all this test asserts.
    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.5,
        fs=fs, process=FakeProcess(alive_for=8), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    retry_entries = [e for e in entries if e["kind"] == "idle-stop-and-retry"]
    assert len(retry_entries) == 2  # one intent, one outcome
    intent, outcome = retry_entries
    assert intent["phase"] == "intent"
    assert intent["payload"] == {"harness_run_id": _HARNESS_RUN_ID, "old_pid": 4242}
    assert outcome["phase"] == "outcome"
    assert outcome["intent_id"] == intent["id"]
    assert outcome["payload"] == {"old_pid": 4242, "new_pid": harness.resume_result}

    assert harness.stop_calls == [(_HOME, _HARNESS_RUN_ID)]
    assert harness.resume_calls == [
        {"project": _HOME, "run_id": _HARNESS_RUN_ID, "log_path": _harness_log_path()}
    ]


def test_stop_and_retry_failure_registers_a_finding_and_keeps_watching_original_pid():
    """I/O matrix: ``stop`` or ``resume`` raising ``HarnessError`` is
    caught, reported via a registered finding in the outcome payload, and
    the tick loop continues watching the (possibly still-wedged) original
    pid rather than crashing."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    harness.fail_stop = HarnessError("bmad-loop binary not found")

    # alive_for=7, not 6 (review finding): the ladder -- including the
    # `defer` rung this test expects to eventually fire -- is now gated on
    # THIS tick's own fresh `watched_alive`, so the tick `defer` fires on
    # (tick 6, see below) must not be the LAST one `FakeProcess` reports
    # alive for.
    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.5,
        fs=fs, process=FakeProcess(alive_for=7), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    retry_outcomes = [
        e for e in entries if e["kind"] == "idle-stop-and-retry" and e["phase"] == "outcome"
    ]
    assert len(retry_outcomes) == 1
    payload = retry_outcomes[0]["payload"]
    assert payload["old_pid"] == 4242
    assert "new_pid" not in payload
    assert payload["finding"]["code"] == "MRS-SUPV-002"
    assert payload["finding"]["severity"] == "warn"
    # resume is never reached once stop raises.
    assert harness.resume_calls == []
    # Nothing resets watched_pid/samples on failure -- the SAME reference
    # point keeps accumulating, so the ladder naturally re-escalates to
    # `defer` later (proving the original pid is still what's tracked).
    defer_entries = [e for e in entries if e["kind"] == "idle-defer"]
    assert len(defer_entries) == 2


def test_stop_and_retry_stop_returns_false_skips_resume():
    """I/O matrix (review finding): ``HarnessPort.stop``'s own documented
    ``False`` return (no exception -- the watched run had already
    finished on its own) must skip ``resume()`` entirely rather than
    relaunching a run that already completed; the outcome records
    ``already_finished`` instead of a ``new_pid``."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    harness.stop_result = False

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.5,
        fs=fs, process=FakeProcess(alive_for=8), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    retry_outcomes = [
        e for e in entries if e["kind"] == "idle-stop-and-retry" and e["phase"] == "outcome"
    ]
    assert len(retry_outcomes) == 1
    assert retry_outcomes[0]["payload"] == {"old_pid": 4242, "already_finished": True}
    assert harness.resume_calls == []


def test_resume_failure_after_a_successful_stop_is_treated_as_unrecoverable_and_defers():
    """Review finding: a ``resume()`` failure occurring AFTER a successful
    ``stop()`` must be distinguished from a ``stop()`` failure -- the
    original pid is CONFIRMED dead here, not "possibly still wedged", so
    falling through to the ordinary tick loop would let the NEXT tick's
    routine ``is_alive`` reading (naturally ``False``) exit via the
    ordinary ``"watched-process-exited"`` detach, silently masking a
    failed recovery as an ordinary completion. This must instead defer:
    the SAME ``idle-stop-and-retry`` outcome records the failure and the
    final detach reports ``reason: "idle-deferred"`` -- no separate
    ``idle-defer`` kind is journaled, since this is a distinct path from
    reaching the third rung."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    harness.fail_resume = HarnessError("bmad-loop resume: connection refused")

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.5,
        fs=fs, process=FakeProcess(alive_for=8), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    retry_outcomes = [
        e for e in entries if e["kind"] == "idle-stop-and-retry" and e["phase"] == "outcome"
    ]
    assert len(retry_outcomes) == 1
    payload = retry_outcomes[0]["payload"]
    assert payload["old_pid"] == 4242
    assert "new_pid" not in payload
    assert payload["finding"]["code"] == "MRS-SUPV-002"
    assert payload["finding"]["severity"] == "warn"
    # `stop` DID succeed here -- distinct from the "stop itself failed"
    # scenario (a separate test), which keeps watching the original pid.
    assert harness.stop_calls == [(_HOME, _HARNESS_RUN_ID)]
    assert harness.resume_calls == [
        {"project": _HOME, "run_id": _HARNESS_RUN_ID, "log_path": _harness_log_path()}
    ]
    assert "idle-defer" not in [e["kind"] for e in entries]
    assert entries[-1]["kind"] == "supervisor-detach"
    assert entries[-1]["payload"]["reason"] == "idle-deferred"


def test_heartbeat_after_a_successful_pid_swap_reports_the_new_pids_fresh_reading():
    """Review finding: ``watched_alive`` used to be computed ONCE at the
    top of each tick, for the OLD pid, before the ladder ran -- when the
    ladder swaps ``watched_pid`` to a NEW pid mid-tick (a successful
    stop-and-retry), the heartbeat appended at the bottom of that SAME
    tick must reflect the NEW pid's own fresh liveness, never the stale
    OLD-pid reading taken before the swap."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    # alive_for=5: tick 4's own fresh (PRE-swap) reading is call #5 (True,
    # since 5<=5) -- the stale value a shape with no recompute would have
    # journaled -- but the RECOMPUTE this fix adds right after the swap is
    # call #6 (False, since 6<=5): the very first call this fake ever
    # answers `False` for. If the heartbeat below shows `True`, the
    # recompute never happened.
    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.5,
        fs=fs, process=FakeProcess(alive_for=5), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    retry_outcome = next(
        e for e in entries if e["kind"] == "idle-stop-and-retry" and e["phase"] == "outcome"
    )
    assert retry_outcome["payload"]["new_pid"] == harness.resume_result
    retry_index = entries.index(retry_outcome)
    # The heartbeat immediately following the retry outcome is THIS same
    # tick's own -- it must carry the freshly-recomputed (new pid) reading.
    heartbeat = entries[retry_index + 1]
    assert heartbeat["kind"] == "supervisor-heartbeat"
    assert heartbeat["payload"]["watched_alive"] is False


def test_already_retried_bounds_the_ladder_to_one_retry_cycle():
    """Review finding: without a persistent "already retried" gate, a
    persistently-wedged resumed process gets another full clean idle
    window every time the ladder resets -- cycling nudge -> stop-and-retry
    -> reset forever and never reaching the terminal ``defer`` rung. After
    ONE successful stop-and-retry, a SECOND idle recurrence on the new
    pid's fresh window must skip straight to ``defer`` instead of firing
    ``nudge``/``stop-and-retry`` again."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")  # never changes -- keeps re-idling forever
    harness = FakeHarness()

    # threshold_s = 90 (1.5min): tick3 NUDGE, tick4 STOP_AND_RETRY (success
    # -- pid swap, `already_retried` set). The new pid's own fresh window
    # then re-accumulates the SAME "idle" pane: tick5 NONE (first sample
    # post-reset), tick6 NONE (elapsed 60s < 90s), tick7 elapsed 120s would
    # ordinarily be a first NUDGE crossing -- but `already_retried` forces
    # straight to `defer` instead. alive_for=9 keeps every one of these
    # ticks (plus the post-swap recompute's own extra credit) non-terminal.
    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.5,
        fs=fs, process=FakeProcess(alive_for=9), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    kinds = [entry["kind"] for entry in entries]
    # Exactly ONE nudge and ONE stop-and-retry cycle -- never a second,
    # even though the pane stays "idle" forever after the reset.
    assert kinds.count("idle-nudge") == 2
    assert kinds.count("idle-stop-and-retry") == 2
    assert kinds.count("idle-defer") == 2
    assert kinds[-1] == "supervisor-detach"
    assert entries[-1]["payload"]["reason"] == "idle-deferred"
    # stop() called exactly twice (the retry, then the bounded defer);
    # resume() called exactly once (only the one successful retry).
    assert len(harness.stop_calls) == 2
    assert len(harness.resume_calls) == 1


def test_defer_calls_harness_stop_and_records_success():
    """Review finding: ``defer`` used to only journal an outcome and exit
    its own loop -- the watched harness process itself kept running,
    fully unsupervised. ``defer`` now makes a best-effort
    ``HarnessPort.stop`` call against it; when that succeeds, this outcome
    records ``stopped: True`` (the FAILURE case is covered by
    ``test_third_threshold_crossing_fires_defer_and_detaches`` below)."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()

    # threshold_s = 15 (0.25min) against a 60s tick: tick 2 alone (60s
    # elapsed since the first sample) already crosses THREE thresholds
    # (60/15=4, capped at DEFER) -- the ladder jumps straight there
    # without ever visiting nudge/stop-and-retry, isolating the DEFER
    # branch's own new `harness.stop` call from the (separately tested)
    # stop-and-retry rung.
    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 0.25,
        fs=fs, process=FakeProcess(alive_for=4), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    kinds = [entry["kind"] for entry in entries]
    assert "idle-nudge" not in kinds
    assert "idle-stop-and-retry" not in kinds
    assert kinds.count("idle-defer") == 2
    defer_outcome = next(
        e for e in entries if e["kind"] == "idle-defer" and e["phase"] == "outcome"
    )
    assert defer_outcome["payload"] == {"watched_pid": 4242, "stopped": True}
    assert harness.stop_calls == [(_HOME, _HARNESS_RUN_ID)]
    assert entries[-1]["payload"]["reason"] == "idle-deferred"


def test_ladder_skips_the_tick_where_the_process_exits_naturally():
    """Review finding: ``watched_alive`` is freshly computed every tick,
    but the ladder-evaluation block used to run UNCONDITIONALLY regardless
    of that tick's own value -- so a watched process that exits naturally
    (a genuinely successful completion) in the exact tick an idle
    threshold also crosses could still have the ladder fire against an
    already-exited process, producing a misleading ``idle-*`` outcome
    instead of the ordinary ``watched-process-exited`` detach. The ladder
    (including its own sample) must be skipped entirely for a tick whose
    OWN fresh ``watched_alive`` is ``False`` -- the heartbeat still
    appends unconditionally."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")  # never changes -- would ordinarily idle-escalate
    harness = FakeHarness()
    # threshold_s = 150 (2.5min, the same arithmetic as the first-nudge
    # test above): tick 4 -- 180s elapsed since the first sample -- would
    # be the FIRST tick to cross even the NUDGE(1) rung. alive_for=4 makes
    # tick 4 ALSO the LAST tick FakeProcess reports alive for -- the one
    # that discovers the watched process has genuinely exited -- so the
    # ladder must be skipped for that tick rather than fire against an
    # already-exited process.
    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 2.5,
        fs=fs, process=FakeProcess(alive_for=4), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    kinds = [entry["kind"] for entry in entries]
    assert not any(kind.startswith("idle-") for kind in kinds)
    assert kinds[-1] == "supervisor-detach"
    assert entries[-1]["payload"]["reason"] == "watched-process-exited"
    assert harness.stop_calls == []
    # The pane is sampled for ticks 1-3 (watched_alive True); tick 4
    # (where the process is discovered gone) skips the sample entirely.
    assert observer.pane_content_calls == [_SESSION_NAME] * 3


def test_third_threshold_crossing_fires_defer_and_detaches():
    """I/O matrix: no change for >= 3x threshold since the last reset ->
    the ladder fires ``defer`` (terminal): ``idle-defer`` intent/outcome
    journaled; supervisor writes ``supervisor-detach`` with ``reason:
    "idle-deferred"`` and exits its loop. No further ladder or heartbeat
    activity after detach."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    harness.fail_stop = HarnessError("unreachable")  # never resets progress

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.0,
        fs=fs, process=FakeProcess(alive_for=10), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    kinds = [entry["kind"] for entry in entries]
    assert kinds.count("idle-defer") == 2
    assert kinds[-1] == "supervisor-detach"
    assert entries[-1]["payload"]["reason"] == "idle-deferred"
    # Terminal: nothing after the detach entry.
    assert kinds.index("supervisor-detach") == len(kinds) - 1

    defer_intent, defer_outcome = (e for e in entries if e["kind"] == "idle-defer")
    assert defer_intent["phase"] == "intent"
    assert defer_outcome["phase"] == "outcome"
    assert defer_outcome["intent_id"] == defer_intent["id"]
    assert defer_intent["payload"] == {"watched_pid": 4242}
    # `stopped` (review finding): `defer` now makes a best-effort
    # `HarnessPort.stop` call against the watched harness process rather
    # than merely journaling and exiting -- this fixture's `fail_stop`
    # means that call also raises, so `stopped` is `False`, but the defer
    # outcome is still journaled and the loop still exits regardless.
    assert defer_outcome["payload"] == {"watched_pid": 4242, "stopped": False}


# --- main(): argv parsing + dispatch --------------------------------------------


def test_main_parses_argv_and_dispatches_to_run_supervisor(monkeypatch):
    calls: list[tuple[Path, str, str, int, Path, float]] = []

    def _fake_run_supervisor(home, slug, run_id, watched_pid, log_path, idle_threshold_minutes):
        calls.append((home, slug, run_id, watched_pid, log_path, idle_threshold_minutes))
        return 0

    monkeypatch.setattr(supervisor_main, "run_supervisor", _fake_run_supervisor)

    rc = main(
        [
            "/home/acme-loop",
            "acme",
            "acme-run-1",
            "4242",
            "/home/acme-loop/supervisor.log",
            "25",
        ]
    )

    assert rc == 0
    assert calls == [
        (
            Path("/home/acme-loop"),
            "acme",
            "acme-run-1",
            4242,
            Path("/home/acme-loop/supervisor.log"),
            25.0,
        )
    ]


def test_main_rejects_the_wrong_argument_count(capsys):
    rc = main(["only", "two"])
    assert rc != 0
    assert "usage" in capsys.readouterr().err.lower()


def test_main_rejects_a_non_integer_watched_pid(capsys):
    rc = main(["/home", "acme", "acme-run-1", "not-a-pid", "/home/supervisor.log", "25"])
    assert rc != 0
    assert "invalid watched pid" in capsys.readouterr().err.lower()


def test_main_rejects_a_zero_or_negative_watched_pid(capsys):
    """Review finding: ``os.kill(pid, 0)`` gives ``0``/negative pids
    special "signal a process GROUP" semantics rather than "no such
    process" -- a malformed invocation naming one of them must be refused
    cleanly rather than let ``is_alive`` silently probe an unintended
    target."""
    for bad_pid in ("0", "-1"):
        rc = main(["/home", "acme", "acme-run-1", bad_pid, "/home/supervisor.log", "25"])
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
        rc = main(["/home/acme-loop", bad_slug, "acme-run-1", "4242", "/home/s.log", "25"])
        assert rc != 0, f"slug {bad_slug!r} was accepted"
        assert "invalid project slug" in capsys.readouterr().err.lower()


def test_main_rejects_a_run_id_that_escapes_the_run_directory(capsys):
    """The ``run_id`` half of the same finding: it is the LAST path segment
    of the run directory, so a separator or a dot-segment in it relocates
    the journal just as effectively as a traversing slug does."""
    for bad_run_id in ("../../evil", "..", ".", "acme/run", "", "a\\b"):
        rc = main(["/home/acme-loop", "acme", bad_run_id, "4242", "/home/s.log", "25"])
        assert rc != 0, f"run_id {bad_run_id!r} was accepted"
        assert "invalid run id" in capsys.readouterr().err.lower()


def test_main_accepts_a_real_spin_minted_run_id(monkeypatch):
    """Negative control for the two guards above -- the real ``run_id``
    shape ``cli/spin.py`` mints (``<slug>-<timestamp>-<suffix>``) must still
    pass, or the guards would have broken every genuine invocation."""
    calls: list[str] = []

    def _fake_run_supervisor(home, slug, run_id, watched_pid, log_path, idle_threshold_minutes):
        calls.append(run_id)
        return 0

    monkeypatch.setattr(supervisor_main, "run_supervisor", _fake_run_supervisor)
    rc = main(
        [
            "/home/acme-loop",
            "acme",
            "acme-20260803T101112000Z-abcd1234",
            "4242",
            "/home/s.log",
            "25",
        ]
    )
    assert rc == 0
    assert calls == ["acme-20260803T101112000Z-abcd1234"]


def test_main_rejects_a_watched_pid_it_could_never_probe(capsys):
    """Review finding, the UPPER half of the positivity guard above.
    ``os.kill`` raises ``OverflowError`` above C ``INT_MAX`` (verified
    live), and ``PosixProcess.is_alive`` deliberately answers the
    conservative ``False`` for it -- correct for that port's two-valued
    contract, but ``run_supervisor`` then journals ``supervisor-detach``
    with ``reason: "watched-process-exited"``: a definitive claim about an
    exit it never observed, written into an append-only EVIDENCE journal.
    (A prior pass rejected a hardcoded ``watched_alive: true`` on exactly
    this ground.) Refused at the boundary instead, since this story's own
    Always bullet enumerates exactly two detach reasons."""
    for bad_pid in (str(2**31), str(2**63), "999999999999"):
        rc = main(["/home", "acme", "acme-run-1", bad_pid, "/home/s.log", "25"])
        assert rc != 0, f"pid {bad_pid} was accepted"
        assert "not probeable" in capsys.readouterr().err.lower()


def test_main_accepts_the_largest_probeable_pid(monkeypatch):
    """Negative control: the guard above must refuse only what ``os.kill``
    genuinely cannot convert, never a real (if implausibly large) pid."""
    calls: list[int] = []
    monkeypatch.setattr(
        supervisor_main,
        "run_supervisor",
        lambda home, slug, run_id, watched_pid, log_path, idle_threshold_minutes: (
            calls.append(watched_pid) or 0
        ),
    )
    rc = main(
        [
            "/home",
            "acme",
            "acme-run-1",
            str(supervisor_main._MAX_PROBEABLE_PID),
            "/home/s.log",
            "25",
        ]
    )
    assert rc == 0
    assert calls == [supervisor_main._MAX_PROBEABLE_PID]


def test_main_rejects_a_relative_home(capsys):
    """Review finding: ``home`` is the ROOT of the very path ``slug`` and
    ``run_id`` are guarded as segments of, and was the one argv element
    validated nowhere. A relative value resolves the journal against this
    process's own CWD (``spawn_detached`` sets that to the loop home), so
    the read silently lands elsewhere and the sidecar exits inert on a run
    it should have supervised -- the same split-brain
    ``cli/init.py::_loop_home_root`` anchors its own root to avoid."""
    for bad_home in ("relative/home", "", "."):
        rc = main([bad_home, "acme", "acme-run-1", "4242", "/home/s.log", "25"])
        assert rc != 0, f"home {bad_home!r} was accepted"
        assert "absolute path" in capsys.readouterr().err.lower()


def test_main_rejects_a_bare_string_argv(capsys):
    """Review finding, verified: a bare ``str`` satisfies ``Sequence[str]``
    and shreds one character per positional argument -- ``main("ab142")``
    returned 0 having dispatched ``run_supervisor(Path('a'), 'b', '1', 4,
    Path('2'))``, a RELATIVE home and a 1-char slug that pass every other
    gate, with no usage error at all. ``core/journal.py::fold`` and
    ``core/identity.py::resolve_feed`` each carry an explicit guard for
    this same footgun; this public entry point did not."""
    rc = main("ab142")
    assert rc != 0
    assert "sequence of strings" in capsys.readouterr().err.lower()


def test_main_rejects_a_non_string_argv_element(capsys):
    """The other half: a non-``str`` element cleared the arity gate and
    reached ``"/" in run_id`` as a raw ``TypeError``."""
    rc = main([Path("/home"), "acme", 3, "4242", "/home/s.log", "25"])
    assert rc != 0
    assert "usage" in capsys.readouterr().err.lower()


def test_main_rejects_a_non_numeric_idle_threshold(capsys):
    rc = main(["/home", "acme", "acme-run-1", "4242", "/home/s.log", "not-a-number"])
    assert rc != 0
    assert "invalid idle threshold minutes" in capsys.readouterr().err.lower()


def test_main_rejects_a_non_positive_idle_threshold(capsys):
    for bad_threshold in ("0", "-1", "-25"):
        rc = main(["/home", "acme", "acme-run-1", "4242", "/home/s.log", bad_threshold])
        assert rc != 0, f"threshold {bad_threshold!r} was accepted"
        assert "must be positive" in capsys.readouterr().err.lower()


def test_main_accepts_a_fractional_idle_threshold(monkeypatch):
    calls: list[float] = []
    monkeypatch.setattr(
        supervisor_main,
        "run_supervisor",
        lambda home, slug, run_id, watched_pid, log_path, idle_threshold_minutes: (
            calls.append(idle_threshold_minutes) or 0
        ),
    )
    rc = main(["/home", "acme", "acme-run-1", "4242", "/home/s.log", "0.5"])
    assert rc == 0
    assert calls == [0.5]


def test_inert_exit_prints_a_diagnostic_naming_the_run(capsys):
    """Follow-up review finding: the inert exit was COMPLETELY silent -- no
    journal write (correct, per the AC) but also nothing on this process's
    own stderr, which is redirected to ``supervisor.log`` and is the only
    diagnostic channel a detached sidecar has. An operator holding that log
    saw an empty file and could not tell the run had been examined at all."""
    fs = FakeFs(journal_text=_launch_outcome_line("some-other-run") + "\n")

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242,
        _LOG_PATH, _IDLE_THRESHOLD_MINUTES,
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
        _LOG_PATH, _IDLE_THRESHOLD_MINUTES,
        fs=fs, process=FakeProcess(alive_for=1), clock=FakeClock(),
        observer=FakeObserver(), sleep=_no_sleep,
    )

    assert rc == 0
    assert fs.appended_lines == []
    err = capsys.readouterr().err
    assert "unevaluable" in err.lower()
    assert "1 journal line" in err.lower()
