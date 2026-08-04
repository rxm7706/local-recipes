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
from pyforge.marshal.core.supervise import CeilingStatus
from pyforge.marshal.ports.harness import UsageSnapshot
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

    def __init__(self, *, alive_for: int, dead_pids: set[int] | None = None) -> None:
        self.alive_for = alive_for
        self.calls = 0
        # Pids this fake reports dead REGARDLESS of the call budget -- the
        # only way to model a specific process dying while others live,
        # which is what a `bmad-loop resume` that launched and was then
        # rejected looks like from the supervisor's side.
        self.dead_pids = dead_pids or set()

    def is_alive(self, pid: int) -> bool:
        self.calls += 1
        if pid in self.dead_pids:
            return False
        return self.calls <= self.alive_for


class FakeClock:
    def __init__(self) -> None:
        self.calls = 0

    def now(self) -> datetime:
        self.calls += 1
        return datetime(2026, 8, 3, 5, 45, 12, tzinfo=timezone.utc)

    def monotonic(self) -> float:
        # A frozen clock's monotonic reading is frozen too -- this fake
        # models a supervisor for which no time passes at all.
        return 1000.0


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
        # Advanced in LOCKSTEP with `_now` by default -- an ordinary host
        # where nothing suspends the process and nothing steps the wall
        # clock, so the two agree. `jump_wall_clock` below breaks that
        # agreement deliberately, which is the whole point of having both.
        self._monotonic = 1000.0

    def now(self) -> datetime:
        self.calls += 1
        return self._now

    def monotonic(self) -> float:
        return self._monotonic

    def sleep(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)
        self._monotonic += seconds

    def jump_wall_clock(self, seconds: float) -> None:
        """Advance the WALL clock only, leaving the monotonic reading where
        it was -- exactly what a host suspend or an NTP step looks like from
        inside this process (``CLOCK_MONOTONIC`` excludes suspended time and
        cannot be stepped). Used to prove the idle ladder scores elapsed
        time monotonically and so cannot be tricked into escalating against
        a healthy run by a clock that jumped."""
        self._now += timedelta(seconds=seconds)


class FakeObserver:
    def __init__(
        self,
        *,
        pane: str | None = None,
        pane_sequence: list[str | None] | None = None,
        send_text_result: bool = True,
        mtime: float | None = 1_760_000_000.0,
        mtime_sequence: list[float | None] | None = None,
        # Story 3.6's own budget-ceiling staleness query -- a SEPARATE
        # sequence from `mtime`/`mtime_sequence` above, keyed by `path.name
        # == "state.json"` (see `mtime()` below): the idle ladder's own
        # `harness_log_path` query and the budget block's `state.json` query
        # are two DIFFERENT paths in the same tick, so sharing one counter/
        # constant between them would make every pre-existing test's
        # `mtime_calls`/`mtime_sequence` assertion (indexed by call count)
        # silently start counting the WRONG query. Defaults to `float("inf")`
        # -- an mtime infinitely in the future can never be "stale" relative
        # to any `moment` a test's clock produces, so every pre-existing
        # test (none of which configures this) sees the budget token
        # ceilings stay perpetually fresh and unexercised, exactly like the
        # large default ceiling constants above keep them at
        # `CeilingStatus.NONE`.
        state_json_mtime: float | None = float("inf"),
    ) -> None:
        self.pane = pane
        self.pane_sequence = pane_sequence
        self.pane_content_calls: list[str] = []
        self.mtime_calls: list[Path] = []
        self.send_text_calls: list[tuple[str, str]] = []
        self.send_text_result = send_text_result
        # A real, CONSTANT float by default -- never `None` (review
        # finding). This fake used to return `None` from `mtime`
        # unconditionally, which no production run can ever do:
        # `cli/spin.py` opens `harness.log` before it spawns the supervisor
        # at all, so `mtime()` always finds the file. That single hardcoded
        # `None` is what let a dead "unobservable" guard -- one that
        # demanded pane AND mtime both be `None` -- pass three consecutive
        # review passes while the ladder was, in production, free to nudge,
        # hard-stop and relaunch a perfectly healthy run whose only problem
        # was that tmux was unreachable. A constant float is the honest
        # default: the log exists, and a quiet engine simply is not writing
        # to it.
        # `mtime_value`, not `mtime`: the attribute would otherwise shadow
        # the method of the same name on every instance.
        self.mtime_value = mtime
        self.mtime_sequence = mtime_sequence
        self.state_json_mtime = state_json_mtime
        self.state_json_mtime_calls: list[Path] = []

    def pane_content(self, session: str) -> str | None:
        self.pane_content_calls.append(session)
        if self.pane_sequence is not None:
            index = len(self.pane_content_calls) - 1
            return self.pane_sequence[min(index, len(self.pane_sequence) - 1)]
        return self.pane

    def mtime(self, path: Path) -> float | None:
        # Path-aware (Story 3.6): `state.json` (the budget block's own
        # staleness query) is answered from a SEPARATE field/counter than
        # every other path (the idle ladder's own `harness_log_path`) --
        # see this class's own docstring comment on `state_json_mtime`.
        if path.name == "state.json":
            self.state_json_mtime_calls.append(path)
            return self.state_json_mtime
        self.mtime_calls.append(path)
        if self.mtime_sequence is not None:
            index = len(self.mtime_calls) - 1
            return self.mtime_sequence[min(index, len(self.mtime_sequence) - 1)]
        return self.mtime_value

    def send_text(self, session: str, text: str) -> bool:
        self.send_text_calls.append((session, text))
        return self.send_text_result


class FakeHarness:
    """Fakes ``HarnessPort``'s ``stop``/``resume`` -- the idle ladder's
    ``stop-and-retry`` rung -- and (Story 3.6) ``usage_snapshot``, the
    budget ceilings' own usage-read seam. Defaults to succeeding (``stop``
    returns ``True``, ``resume`` returns ``resume_result``); a test injects
    ``fail_stop``/``fail_resume`` to exercise the ``HarnessError`` path, or
    sets ``stop_result = False`` to model ``stop()``'s own documented "the
    run had already finished" outcome (not an exception -- see that port
    method's own docstring). ``usage_snapshot_result`` defaults to ``None``
    (the "could not read usage" degrade every real adapter method shares) --
    every pre-existing test in this file that constructs a bare
    ``FakeHarness()`` therefore sees no story tracked and no token ceiling
    ever evaluated, matching ``FakeObserver``'s own inert-by-default
    ``state_json_mtime``."""

    def __init__(self) -> None:
        self.stop_calls: list[tuple[Path, str]] = []
        self.resume_calls: list[dict[str, object]] = []
        self.usage_snapshot_calls: list[tuple[Path, str]] = []
        self.fail_stop: Exception | None = None
        self.fail_resume: Exception | None = None
        self.stop_result: bool = True
        self.resume_result: int = 555555
        self.usage_snapshot_result: UsageSnapshot | None = None
        # A per-call sequence (mirrors `FakeObserver.pane_sequence`'s own
        # convention: indexed by call count, clamped to the last element) --
        # lets a test model a story TRANSITION across ticks, which a single
        # constant `usage_snapshot_result` cannot.
        self.usage_snapshot_sequence: list[UsageSnapshot | None] | None = None

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

    def usage_snapshot(self, project: Path, run_id: str) -> UsageSnapshot | None:
        self.usage_snapshot_calls.append((project, run_id))
        if self.usage_snapshot_sequence is not None:
            index = len(self.usage_snapshot_calls) - 1
            return self.usage_snapshot_sequence[min(index, len(self.usage_snapshot_sequence) - 1)]
        return self.usage_snapshot_result


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

# Story 3.6's 4 budget-ceiling arguments -- large, inert-by-default values
# (matching core.policy's own DEFAULT_POLICY) passed to every pre-existing
# `run_supervisor` call in this file that does not itself exercise the
# ceilings: combined with `FakeObserver`'s own default-fresh
# `state_json_mtime` (see that class below) and `FakeHarness.usage_snapshot`
# defaulting to `None`, every ceiling here stays at `CeilingStatus.NONE` for
# the whole life of every pre-existing test, so none of their journal-entry
# assertions change.
_MAX_TOKENS_PER_STORY = 4_000_000.0
_MAX_TOKENS_PER_RUN = 40_000_000.0
_MAX_WALL_CLOCK_MINUTES_PER_STORY = 240.0
_MAX_WALL_CLOCK_MINUTES_PER_RUN = 600.0

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


def _state_json_path() -> Path:
    return supervisor_main._bmad_loop_state_json_path(_HOME, _HARNESS_RUN_ID)


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
        _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
    # `harness=` is unset here, so `usage_snapshot` falls through to the real
    # `BmadLoopHarness()` default, which finds no real `state.json` on disk
    # and returns `None` -- Story 3.6's own `budget-usage-stale` finding
    # (`MRS-SUPV-006`) therefore fires exactly once, on the first tick, and
    # never again (`usage_stale` latches).
    assert [entry["kind"] for entry in entries] == [
        "supervisor-attach",
        "budget-usage-stale",
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
    # entries[1] is `budget-usage-stale` (see the comment above) -- the 3
    # heartbeats are entries[2:5].
    for heartbeat in entries[2:5]:
        assert heartbeat["payload"]["pid"] == supervisor_pid
        assert "sampled_at" in heartbeat["payload"]
    # The first two heartbeats sample a still-alive process; the THIRD is
    # the fresh, contemporaneous reading that discovers the watched process
    # has just exited -- `watched_alive` is a genuine per-tick observation
    # (review finding), never a hardcoded `True` that only a separate
    # `supervisor-detach` entry could ever contradict.
    assert [heartbeat["payload"]["watched_alive"] for heartbeat in entries[2:5]] == [
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
    # `state.json`'s own mtime (the budget block's staleness query) is a
    # SEPARATE `FakeObserver` counter (`state_json_mtime_calls`), not
    # `mtime_calls` -- see that fake's own `mtime()` docstring -- so this
    # assertion is unaffected by Story 3.6's new staleness query.
    assert observer.mtime_calls == [_harness_log_path()] * 2
    assert observer.state_json_mtime_calls == [_state_json_path()] * 2
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
        _HOME, "acme", "bogus-run", 1, _LOG_PATH, _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
        _HOME, "acme", "acme-run-1", 1, _LOG_PATH, _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
        _HOME, "acme", "acme-run-1", 1, _LOG_PATH, _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
        _HOME, "acme", "acme-run-1", 1, _LOG_PATH, _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=process, clock=FakeClock(), observer=observer,
        sleep=_no_sleep,
    )

    assert rc == 0
    assert observer.pane_content_calls == [_SESSION_NAME]
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    # `harness=` is unset, so `usage_snapshot` falls through to the real
    # `BmadLoopHarness()` default (no real `state.json` on disk), firing
    # Story 3.6's `budget-usage-stale` once on the first tick -- same as
    # `test_normal_attach_journals_attach_then_heartbeats_then_detach`.
    assert [entry["kind"] for entry in entries] == [
        "supervisor-attach",
        "budget-usage-stale",
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 2.5, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=5), clock=clock, observer=observer,
        sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    kinds = [entry["kind"] for entry in entries]
    assert kinds.count("idle-nudge") == 2  # one intent, one outcome
    # `harness=` is unset, so `usage_snapshot` falls through to the real
    # `BmadLoopHarness()` default (no real `state.json` on disk), firing
    # Story 3.6's `budget-usage-stale` once on the first tick -- same as
    # the other pre-existing tests above that don't inject a `FakeHarness`.
    assert kinds == [
        "supervisor-attach",
        "budget-usage-stale",
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 2.5, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
    # threshold_s = 150 (2.5min) against a 60s tick. `pane_sequence` is
    # indexed by CALL, not by tick, and a successful nudge now makes one
    # extra `pane_content` call of its own (the post-nudge re-capture that
    # rebases the baseline -- see the echo test below), so the calls run:
    #   0-3  ticks 1-4  "idle"        -> nudge fires at tick 4 (180s/150s)
    #   4    the nudge's own re-capture: the echoed text it just typed
    #   5    tick 5     "responded"   -- GENUINE fresh output: re-arms
    #   6-8  ticks 6-8  "responded"   -- no further change; 180s elapsed
    #                                    since the re-arm by tick 8 -> a
    #                                    SECOND nudge, which is the point.
    observer = FakeObserver(
        pane_sequence=["idle"] * 4 + ["idle+nudge echo"] + ["responded"] * 5
    )

    # alive_for=9, not 8 (review finding): the ladder -- including the
    # SECOND nudge this test's whole point is to prove fires -- is now
    # gated on THIS tick's own fresh `watched_alive`, so tick 8 (where it
    # fires) must not be the LAST tick `FakeProcess` reports alive for.
    # `FakeObserver.pane_sequence` clamps to its last element for any call
    # index beyond its own length, so the harmless extra calls just sample
    # "responded" again.
    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 2.5, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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


def test_the_nudge_text_carries_no_shell_metacharacters():
    """Review finding: ``send_text`` delivers this text as a literal
    keystroke stream followed by Enter, into whichever window tmux marks
    ACTIVE -- the agent's in the ordinary case, but whatever an attached
    operator last selected otherwise, and a plain shell once the agent's own
    process exits. The previous wording contained a ``;`` (a shell command
    separator) and a clause opening with ``if``, so a mis-targeted nudge ran
    one bogus command and then left the shell hanging at a ``>``
    continuation prompt forever -- which this same supervisor would then
    read back as a permanently unchanging pane."""
    text = supervisor_main._NUDGE_TEXT
    for metacharacter in ";|&$`'\"\\<>(){}[]*?!#\n\r":
        assert metacharacter not in text, f"{metacharacter!r} is shell-significant"


def test_every_ladder_journal_entry_conforms_to_the_frozen_journal_schema():
    """Review finding: the one ``jsonschema.validate`` call on this side ran
    over a run that produces only attach/heartbeat/detach entries. The three
    ladder kinds are the FIRST entries this module writes with ``phase:
    intent``, a populated ``intent_id``, and a nested ``finding`` object in
    the payload -- a mismatch in any of those shapes shipped green and would
    have surfaced only when a real supervisor wrote an unreadable line into
    a live run's journal."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle", send_text_result=False)  # forces MRS-SUPV-001
    harness = FakeHarness()
    harness.stop_result = False  # forces MRS-SUPV-002 on the retry rung

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.0, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=12), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    ladder_kinds = {e["kind"] for e in entries if e["kind"].startswith("idle-")}
    assert ladder_kinds == {"idle-nudge", "idle-stop-and-retry", "idle-defer"}
    # Both finding-bearing payload shapes are exercised above.
    assert any("finding" in e["payload"] for e in entries if e["phase"] == "outcome")

    schema = _journal_schema()
    for entry in entries:
        jsonschema.validate(instance=entry, schema=schema)


def test_the_nudges_own_echo_does_not_re_arm_the_idle_window():
    """Review finding, and the defect that made this ladder unable to
    escalate AT ALL: ``send_text`` types into the SAME pane ``pane_content``
    samples, so the tick after a nudge captures a pane containing the text
    the supervisor itself just typed. Read as "fresh output" that re-arms
    the window, the rung falls back to ``NONE`` and the run cycles nudge ->
    re-arm -> nudge forever without ever reaching ``stop-and-retry`` --
    which is precisely the wedged-session recovery FR-12 exists to perform.

    "Fresh output" means the SESSION's output, never this supervisor's own.
    The nudge therefore re-captures the pane and rebases its sample history
    onto that text while PRESERVING the idle anchor, so elapsed idle time
    keeps accruing and one more full threshold reaches the next rung."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    # threshold_s = 90 (1.5min), 60s tick. Calls: 0-2 ticks 1-3 "idle"
    # (nudge fires at tick 3, 120s/90s = 1.33); call 3 is the nudge's own
    # re-capture, which for the first time shows the echoed text; every
    # later call keeps showing it, because the session is genuinely wedged
    # and produces nothing further. Tick 4 (180s since the anchor) must
    # therefore reach STOP_AND_RETRY. Before the fix, tick 4's
    # "idle+nudge echo" differed from tick 3's "idle" and reset the rung to
    # NONE instead.
    observer = FakeObserver(pane_sequence=["idle"] * 3 + ["idle+nudge echo"] * 8)
    harness = FakeHarness()

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.5, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=8), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    kinds = [entry["kind"] for entry in entries]
    assert kinds.count("idle-nudge") == 2, "exactly one nudge firing"
    retry_outcome = next(
        e for e in entries if e["kind"] == "idle-stop-and-retry" and e["phase"] == "outcome"
    )
    assert retry_outcome["payload"]["new_pid"] == harness.resume_result
    assert harness.stop_calls == [(_HOME, _HARNESS_RUN_ID)]


def test_a_short_threshold_never_skips_a_ladder_rung():
    """Review finding: the ladder is a FIXED 3-rung sequence (this story's
    own Never clause), but ``evaluate_idle`` floor-divides elapsed idle time
    by the threshold -- so any threshold shorter than twice the fixed 60s
    tick lets ONE tick land several rungs above the last one acted on.
    Nothing validates the threshold against the tick, and
    ``core/policy.py``'s validator explicitly admits sub-minute values, so
    ``idle_threshold_minutes = 0.25`` used to reach ``DEFER`` on the second
    sample -- hard-stopping a healthy run without ever nudging it. Every
    rung must still be visited, in order, one per tick."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()

    # threshold_s = 15 against a 60s tick: tick 2 alone floor-divides to 4,
    # capped at DEFER. The clamp walks NUDGE -> STOP_AND_RETRY -> DEFER
    # instead, one rung per tick.
    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 0.25, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=12), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    ladder = [e["kind"] for e in entries if e["phase"] == "intent"]
    assert ladder[0] == "idle-nudge", "the first response is never a hard stop"
    assert "idle-stop-and-retry" in ladder
    assert ladder[-1] == "idle-defer"
    assert entries[-1]["payload"]["reason"] == "idle-deferred"


def test_an_unobservable_session_is_never_treated_as_idle():
    """Review finding: ``None != None`` is ``False``, so a sample history in
    which NOTHING was ever observed -- no pane (tmux missing from this
    detached sidecar's PATH, or the session torn down) and no harness log --
    never re-arms and reads as maximal idleness. That was tolerable while
    ``defer`` merely detached; now that it hard-stops the run, it turns a
    broken observation channel into a KILLED HEALTHY run. The ladder must
    only act on evidence it actually has."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    # `pane=None` with the fake's DEFAULT constant mtime float -- which is
    # what a real run looks like when tmux is unreachable (review finding).
    # `cli/spin.py` creates `harness.log` before spawning the supervisor, so
    # `mtime()` always finds it; the pane is the only channel that can
    # actually go dark, and it is the only one that observes the agent.
    observer = FakeObserver(pane=None)
    assert observer.mtime_value is not None, "the log exists in a real run"
    harness = FakeHarness()

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.0, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=10), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    kinds = [entry["kind"] for entry in entries]
    assert not any(kind.startswith("idle-") for kind in kinds), "no ladder action"
    assert harness.stop_calls == []
    assert observer.send_text_calls == []
    # Heartbeat-only supervision still runs, and the run ends its own way.
    assert kinds.count("supervisor-heartbeat") >= 1
    assert entries[-1]["payload"]["reason"] == "watched-process-exited"


def test_a_flaky_pane_capture_never_re_arms_the_idle_window():
    """Review finding: a pane capture that merely FLAKES -- a 5s
    ``capture-pane`` timeout under load, a window-teardown race -- returned
    ``None`` for one tick and then text again. Recorded as samples, that is
    TWO changes (text -> None, None -> text), and each one re-armed the idle
    window. A wedged session whose capture flaked once per threshold window
    could never accumulate a full threshold, and burned to the token cap
    without the ladder ever firing. Unobservable ticks are dropped, not
    recorded, so the idle anchor survives the gap and elapsed time keeps
    accruing across it."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    # Wedged: the same pane text throughout, but the capture flakes on every
    # other tick. Recorded as samples that is a change EVERY tick (text ->
    # None -> text ...), so the anchor reset every tick and a full threshold
    # could never accumulate -- the session stayed wedged forever with the
    # ladder permanently at rest. A single one-off flake only DELAYS
    # escalation by a tick, which is why this pattern recurs.
    observer = FakeObserver(
        pane_sequence=["stuck", None, "stuck", None, "stuck", None, "stuck", None]
    )
    harness = FakeHarness()

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.0, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=8), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    kinds = [json.loads(line)["kind"] for _, line, _ in fs.appended_lines]
    # The flakes must NOT have reset the window: the ladder still escalates.
    assert "idle-nudge" in kinds, "flaked ticks must not re-arm the window"


def test_a_wall_clock_jump_never_escalates_the_ladder():
    """Review finding: elapsed idle time is measured MONOTONICALLY, so a
    host suspend or an NTP step cannot be scored as accumulated idleness.

    A laptop suspended for an hour mid-run advances the wall clock across an
    interval in which the session was not running and could not possibly
    have produced output. Measured on `moment` alone, the first tick after
    wake crossed the threshold and nudged, and the tick after that hard-
    stopped and relaunched a perfectly healthy engine -- at the shipped
    25-minute default.
    """
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="working")
    harness = FakeHarness()

    real_sleep = clock.sleep
    ticks = {"n": 0}

    def _sleep_then_suspend(seconds: float) -> None:
        real_sleep(seconds)
        ticks["n"] += 1
        if ticks["n"] == 2:
            # One hour of wall clock, zero monotonic seconds: exactly what a
            # suspend looks like from inside this process.
            #
            # On the SECOND tick's sleep, deliberately: the jump has to land
            # between two samples to show up as a delta at all. Applied
            # during the first tick's sleep it is absorbed into the very
            # first sample's own `moment` and no elapsed calculation ever
            # sees it -- which makes the test vacuous.
            clock.jump_wall_clock(3600.0)

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 25.0, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=6), clock=clock, observer=observer,
        harness=harness, sleep=_sleep_then_suspend,
    )

    assert rc == 0
    kinds = [json.loads(line)["kind"] for _, line, _ in fs.appended_lines]
    assert not any(kind.startswith("idle-") for kind in kinds), (
        "a wall-clock jump is not elapsed idle time"
    )
    assert harness.stop_calls == []
    assert observer.send_text_calls == []


def test_a_resume_that_did_not_take_is_not_a_clean_completion():
    """Review finding: ``HarnessPort.resume`` returning a pid proves only
    that the spawn worked. ``bmad-loop resume`` exits non-zero -- after
    starting normally -- for an unknown run ref, a run whose engine it still
    considers alive, an already-finished run, or missing base skills. The
    supervisor journaled a fully successful ``{old_pid, new_pid}`` retry
    with no finding, then detached with the ordinary
    ``"watched-process-exited"``: a failed recovery written into an
    append-only EVIDENCE journal as a clean completion."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    # The resumed pid is dead from the moment it is handed over -- the
    # signature of a `resume` that launched and was then rejected.
    process = FakeProcess(alive_for=10, dead_pids={harness.resume_result})

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.0, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=process, clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    detach = entries[-1]
    assert detach["kind"] == "supervisor-detach"
    assert detach["payload"]["reason"] == "idle-retry-failed"
    assert detach["payload"]["finding"]["code"] == "MRS-SUPV-002"


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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.5, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.5, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
    ``False`` return (no exception) must skip ``resume()`` entirely rather
    than relaunching a run that may already have completed.

    The outcome records ``stopped: False`` plus a registered finding, NOT
    ``already_finished: True`` (second review finding): the port documents
    ``False`` as "any other determinable outcome", of which "already
    finished" is only one example, so asserting a completion here would
    write into an append-only evidence journal a claim this process never
    observed -- and one that contradicts the fresh ``is_alive`` reading
    from the very same tick that let the ladder run."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    harness.stop_result = False

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.5, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
    assert payload["stopped"] is False
    assert "already_finished" not in payload, "never assert an unobserved completion"
    assert "new_pid" not in payload
    assert payload["finding"]["code"] == "MRS-SUPV-002"
    assert payload["finding"]["severity"] == "warn"
    assert harness.resume_calls == []


def test_resume_failure_after_a_successful_stop_is_treated_as_unrecoverable_and_defers():
    """Review finding: a ``resume()`` failure occurring AFTER a successful
    ``stop()`` must be distinguished from a ``stop()`` failure -- the
    original pid is CONFIRMED dead here, not "possibly still wedged", so
    falling through to the ordinary tick loop would let the NEXT tick's
    routine ``is_alive`` reading (naturally ``False``) exit via the
    ordinary ``"watched-process-exited"`` detach, silently masking a
    failed recovery as an ordinary completion. This must instead end the
    loop: the SAME ``idle-stop-and-retry`` outcome records the failure and
    no separate ``idle-defer`` kind is journaled, since this is a distinct
    path from reaching the third rung.

    The detach reason is ``"idle-retry-failed"``, NOT ``"idle-deferred"``
    (second review finding): the ladder never reached its ``defer`` rung and
    no ``idle-defer`` pair exists to back that claim up, so a consumer
    counting deferrals by entry kind saw zero while one reading detach
    reasons saw one. A failed recovery is a materially different reason
    class from an exhausted idle ladder -- FR-16's own unit of capture."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    harness.fail_resume = HarnessError("bmad-loop resume: connection refused")

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.5, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
    assert entries[-1]["payload"]["reason"] == "idle-retry-failed"


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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.5, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
    ONE successful stop-and-retry, no SECOND stop-and-retry may ever fire:
    that rung and everything above it collapses to ``defer``.

    A second ``nudge`` IS still allowed (second review finding). The gate
    used to swallow every rung above ``NONE``, which collapsed the
    post-retry ladder to ``NONE -> DEFER`` -- so the FIRST threshold
    crossing on a freshly resumed run hard-stopped it, with none of the
    harmless-first-response grace an un-retried run gets. A resumed engine
    that goes quiet for one threshold may simply be running a long build;
    nudging it first costs nothing, and only the rung that actually kills
    work is bounded."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")  # never changes -- keeps re-idling forever
    harness = FakeHarness()

    # threshold_s = 90 (1.5min): tick3 NUDGE, tick4 STOP_AND_RETRY (success
    # -- pid swap, `already_retried` set). The new pid's own fresh window
    # then re-accumulates the SAME "idle" pane: tick5 NONE (first sample
    # post-reset), tick6 NONE (elapsed 60s < 90s), tick7 NUDGE again (the
    # grace this gate deliberately preserves), tick8 would ordinarily be a
    # second STOP_AND_RETRY -- but `already_retried` forces `defer` instead.
    # alive_for=12 keeps every one of those ticks (plus the post-swap
    # recompute's own extra `is_alive` call) non-terminal.
    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.5, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=12), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    kinds = [entry["kind"] for entry in entries]
    # Two nudges (one per idle window -- the grace survives the retry), but
    # exactly ONE stop-and-retry ever, even though the pane stays "idle"
    # forever after the reset. Each kind counts 2 entries per firing
    # (intent + outcome).
    assert kinds.count("idle-nudge") == 4
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
    records ``stopped: True`` and carries NO finding (the FAILURE case is
    covered by ``test_third_threshold_crossing_fires_defer_and_detaches``
    below)."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()

    # The ladder is walked rung by rung to reach `defer` (nudge tick3,
    # stop-and-retry tick4, nudge tick7, defer tick8 via the already-retried
    # gate). It used to be short-circuited here with a 15s threshold, which
    # made ONE tick jump straight from `NONE` to `DEFER` -- that shortcut is
    # exactly the rung-skipping the escalation clamp now (correctly)
    # forbids, and it has its own test below. `defer`'s own stop call is the
    # SECOND one the fake records, and its watched pid is the post-swap one.
    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.5, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=12), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    kinds = [entry["kind"] for entry in entries]
    assert kinds.count("idle-defer") == 2
    defer_outcome = next(
        e for e in entries if e["kind"] == "idle-defer" and e["phase"] == "outcome"
    )
    assert defer_outcome["payload"] == {
        "watched_pid": harness.resume_result,
        "stopped": True,
    }
    assert harness.stop_calls[-1] == (_HOME, _HARNESS_RUN_ID)
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 2.5, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.0, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
    #
    # A failed stop at the TERMINAL rung also registers a finding (second
    # review finding): it used to be swallowed into a bare `stopped: false`
    # with nothing at WARN tier anywhere, even though it is the worst case
    # this whole story exists to prevent -- the supervisor exits while the
    # wedged run keeps burning tokens with nobody watching it.
    assert defer_outcome["payload"]["watched_pid"] == 4242
    assert defer_outcome["payload"]["stopped"] is False
    assert defer_outcome["payload"]["finding"]["code"] == "MRS-SUPV-002"
    assert defer_outcome["payload"]["finding"]["severity"] == "warn"


class _AliveUntilStopped:
    """``is_alive`` reports ``True`` until the harness has been stopped
    ``after`` times.

    ``FakeProcess``'s call counter cannot express the one thing these tests
    need: a ``bmad-loop stop`` that actually KILLS the watched pid. Keying
    liveness off the fake harness's own ``stop_calls`` models the real POSIX
    consequence, which is what makes it possible to ask whether the
    heartbeat written in the SAME tick as a stop tells the truth about it."""

    def __init__(self, harness: FakeHarness, *, after: int) -> None:
        self.harness = harness
        self.after = after
        self.calls = 0

    def is_alive(self, pid: int) -> bool:
        self.calls += 1
        return len(self.harness.stop_calls) < self.after


def test_a_channel_that_breaks_mid_run_is_never_treated_as_idle():
    """Follow-up review finding: the "UNOBSERVABLE is not IDLE" guard tested
    the WHOLE history, so it only ever caught a channel that never worked
    from tick one. A channel that breaks MID-RUN (the engine's tmux window
    closed while it kept working in-process, `harness.log` never present)
    leaves exactly one stale observed sample alive at the front of the
    history -- the trim retains it, because going dark is itself a "change"
    -- so the all-`None` test stayed `False` forever and the ladder ran
    anyway, anchored on the instant the channel died. A perfectly healthy
    run was nudged, then genuinely hard-stopped and relaunched."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    # Three ticks of genuine, CHANGING output, then the pane goes dark for
    # good (`FakeObserver` clamps to the last element). `mtime` is always
    # None, so from tick 4 on nothing at all is observable.
    observer = FakeObserver(pane_sequence=["a", "b", "c", None])
    harness = FakeHarness()

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.0, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=8), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    kinds = [entry["kind"] for entry in entries]
    # Eight ticks at a 1-minute threshold: before the fix this reached
    # `idle-nudge`, `idle-stop-and-retry` AND `idle-defer` against a
    # perfectly healthy process.
    assert not any(kind.startswith("idle-") for kind in kinds), "no ladder action"
    assert harness.stop_calls == []
    assert observer.send_text_calls == []
    assert entries[-1]["payload"]["reason"] == "watched-process-exited"


def test_a_nudge_reporting_failed_delivery_still_neutralizes_its_own_echo():
    """Follow-up review finding: ``send_text`` sends the text and the
    submitting ``Enter`` as two separate tmux calls and reports only the
    SECOND one's fate, so a ``False`` return does not mean nothing was
    typed. The rebase that neutralizes the supervisor's own echo used to be
    conditioned on that return, so a paste that landed before a failing or
    timing-out ``Enter`` left the nudge text sitting in the observed pane
    with nothing collapsing it away -- reopening, through the
    partial-delivery door, the exact nudge -> re-arm -> nudge loop that
    makes this ladder unable to escalate at all."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    # Pane captures: tick1 sample, tick2 sample, then the post-nudge
    # re-capture and everything after it show the partially-delivered nudge
    # text -- a change the SESSION never produced.
    observer = FakeObserver(
        pane_sequence=["idle", "idle", "idle+nudge-echo"], send_text_result=False
    )
    harness = FakeHarness()

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.0, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=6), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    kinds = [entry["kind"] for entry in entries]
    # The delivery failure is still reported honestly...
    nudge_outcome = next(
        e for e in entries if e["kind"] == "idle-nudge" and e["phase"] == "outcome"
    )
    assert nudge_outcome["payload"]["sent"] is False
    assert nudge_outcome["payload"]["finding"]["code"] == "MRS-SUPV-001"
    # ...and the ladder still ESCALATES, which is the whole point: before
    # the fix the echo re-armed the window every cycle and `stop-and-retry`
    # was unreachable no matter how wedged the session was.
    assert "idle-stop-and-retry" in kinds
    assert harness.stop_calls != []


def test_history_pruning_preserves_the_idle_anchor():
    """Follow-up review finding: the history trim only fired on a tick that
    observed a CHANGE, so the runs that never observe one again -- exactly
    the wedged and unobservable ones -- grew one ``Sample`` per tick for
    their whole life. The no-change prune added alongside it must be
    semantics-preserving: with every sample from the second onward equal,
    ``idle_since`` has to derive the SAME reference moment from the pruned
    ``[first, second, latest]`` as it would from the full history, so the
    rung still crosses on exactly the tick it always did."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()

    # A 3-minute threshold against the fixed 60s tick: the history reaches
    # four samples (and is therefore pruned) at tick 4, which is also the
    # tick whose elapsed idle time first equals one full threshold. A prune
    # that moved the anchor would shift this crossing.
    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 3.0, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=5), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    kinds = [entry["kind"] for entry in entries]
    assert kinds.count("idle-nudge") == 2, "exactly one intent/outcome pair"
    # Three heartbeats precede it -- the nudge lands on the fourth tick, not
    # earlier (a lost anchor) and not later (a mis-pruned reference).
    assert kinds[: kinds.index("idle-nudge")].count("supervisor-heartbeat") == 3


def test_the_heartbeat_written_when_defer_stops_the_run_is_not_stale():
    """Follow-up review finding: the ``defer`` rung's own ``harness.stop``
    can kill the very pid this tick read as alive at its top, and this
    tick's heartbeat -- the LAST one this run will ever produce -- still
    appends afterwards. It carried the pre-stop reading, so a consumer
    reading the final heartbeat saw ``watched_alive: True`` for a process
    the supervisor itself had just stopped, immediately under an
    ``idle-defer`` outcome saying otherwise. The stop-and-retry branch
    already recomputed for exactly this reason."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    # `defer`'s stop is the SECOND one the ladder makes (stop-and-retry's is
    # the first), and only it is fatal to the watched process here.
    process = _AliveUntilStopped(harness, after=2)

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.5, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=process, clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    assert entries[-1]["payload"]["reason"] == "idle-deferred"
    heartbeats = [e for e in entries if e["kind"] == "supervisor-heartbeat"]
    assert heartbeats[-1]["payload"]["watched_alive"] is False


def test_the_heartbeat_written_when_a_resume_fails_is_not_stale():
    """The same defect class on the other branch that stops the watched
    process: ``stop()`` succeeded (so the old pid is CONFIRMED dead) and
    ``resume()`` then failed. That tick's heartbeat also appends after the
    fact, and also used to assert the dead pid was alive."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    harness.fail_resume = HarnessError("engine refused to resume")
    process = _AliveUntilStopped(harness, after=1)

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.5, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=process, clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    assert entries[-1]["payload"]["reason"] == "idle-retry-failed"
    heartbeats = [e for e in entries if e["kind"] == "supervisor-heartbeat"]
    assert heartbeats[-1]["payload"]["watched_alive"] is False


def test_the_defer_finding_names_the_run_once_and_reads_as_one_sentence():
    """Follow-up review finding: the non-raising half of ``defer``'s stop
    handling built a COMPLETE sentence ("bmad-loop reported harness run
    '...' was not stopped") and then interpolated it into a frame that
    already said "could not stop harness run ", producing the doubled,
    unreadable "could not stop harness run bmad-loop reported harness run
    '...' was not stopped". The frame names the run; the detail says only
    what is known about why."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    # `stop()`'s own documented non-raising `False`, at BOTH rungs: the
    # stop-and-retry rung skips its resume and resets nothing, so the ladder
    # keeps escalating to `defer`, where the same `False` comes back.
    harness.stop_result = False

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1.0, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=8), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    defer_outcome = next(
        e for e in entries if e["kind"] == "idle-defer" and e["phase"] == "outcome"
    )
    message = defer_outcome["payload"]["finding"]["message"]
    assert message.count("harness run") == 1
    assert message == (
        f"defer: could not stop harness run {_HARNESS_RUN_ID!r} -- bmad-loop "
        "reported it was not stopped -- the run may still be running, now "
        "unsupervised"
    )


def test_run_supervisor_rejects_a_threshold_that_overflows_to_infinite_seconds(capsys):
    """Follow-up review finding, two defects one guard: ``main()`` checked
    ``idle_threshold_minutes`` for finiteness, but the ladder consumes
    ``minutes * 60`` -- and a finite-but-enormous value overflows that
    product to ``inf``, which is precisely the value both that guard and
    ``core/policy.py``'s validator exist to reject (every elapsed/``inf``
    floor-divides to ``NONE``, silently disabling the idle ladder for the
    run's whole life). ``run_supervisor`` is also a public entry point in
    its own right and carried no threshold guard at all, so a bad value
    surfaced a tick later as a ``ValueError`` misreported as "cannot append
    to journal", leaving a ``supervisor-attach`` with no matching detach."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, 1e308, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=3), clock=AdvancingClock(),
        observer=FakeObserver(pane="idle"), harness=FakeHarness(), sleep=_no_sleep,
    )

    assert rc == 1
    # Rejected BEFORE anything is journaled: no dangling `supervisor-attach`.
    assert fs.appended_lines == []
    assert "positive finite" in capsys.readouterr().err


def test_run_supervisor_rejects_a_non_numeric_threshold(capsys):
    """Review finding: the guard began with an unprotected ``float()``, 13
    lines before the try/except that would have contained it. A direct
    caller -- which this guard's own justification names as the reason it
    exists -- got a raw ``TypeError``/``ValueError`` out of the function
    instead of the clean non-zero return, so the failure mode the guard
    exists to handle escaped through the guard itself.

    (A NUMERIC string like ``"25"`` is deliberately absent below: ``float``
    converts it, so it is a valid threshold, not a rejected one.)"""
    for bad_threshold in ("abc", "", None, object(), [25]):
        fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")

        rc = run_supervisor(
            _HOME, "acme", "acme-run-1", 4242, _LOG_PATH, bad_threshold, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
            fs=fs, process=FakeProcess(alive_for=3), clock=AdvancingClock(),
            observer=FakeObserver(pane="idle"), harness=FakeHarness(), sleep=_no_sleep,
        )

        assert rc == 1, bad_threshold
        # Rejected BEFORE anything is journaled: no dangling attach.
        assert fs.appended_lines == [], bad_threshold
        assert "positive finite" in capsys.readouterr().err


# --- Story 3.6: budget ceilings (AD-20/AD-32) ------------------------------------
#
# `AdvancingClock` makes elapsed monotonic minutes equal the TICK COUNT
# (each `sleep(_TICK_SECONDS)` advances `.monotonic()` by exactly 60s, and
# `run_started_monotonic`/`story_started_monotonic` are captured before any
# tick runs) -- so a `max_wall_clock_minutes_per_*` of ``N`` breaches on the
# tick whose 1-indexed count first reaches ``N``, and approaches on the
# first tick whose count is ``>= 0.8 * N`` while still ``< N``.


def test_run_wall_clock_ceiling_approaching_journals_a_budget_warn():
    """I/O matrix: ``run_elapsed_minutes >= 0.8 * limit``, not yet breached
    -> one ``budget-warn`` observation on the rising edge; the run
    continues (never a ``budget-stop``)."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN,
        _MAX_WALL_CLOCK_MINUTES_PER_STORY, 2.5,
        # `alive_for=3`: the pre-loop `is_alive` reading is call #1, so only
        # ticks 1-2 (calls #2-#3) see `watched_alive=True` and run the
        # budget block at all -- tick 2's own elapsed (2.0min) is the one
        # that crosses `0.8 * 2.5 = 2.0`.
        fs=fs, process=FakeProcess(alive_for=3), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    kinds = [entry["kind"] for entry in entries]
    assert kinds.count("budget-warn") == 1
    assert "budget-stop" not in kinds
    assert harness.stop_calls == []
    warn_entry = next(e for e in entries if e["kind"] == "budget-warn")
    assert warn_entry["phase"] == "observation"
    assert warn_entry["payload"]["scope"] == "run"
    assert warn_entry["payload"]["metric"] == "wall_clock"
    assert warn_entry["payload"]["finding"]["code"] == "MRS-SUPV-004"
    assert warn_entry["payload"]["finding"]["severity"] == "warn"
    # The ordinary exit: the ceiling never breached within `alive_for=2`.
    assert entries[-1]["payload"]["reason"] == "watched-process-exited"


def test_run_wall_clock_ceiling_breach_stops_and_detaches():
    """I/O matrix: ``run_elapsed_minutes >= limit`` -> ``budget-stop``
    intent/outcome, best-effort ``HarnessPort.stop``, detach reason
    ``budget-run-wall_clock-exceeded``. Never ``stop-and-retry``."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN,
        _MAX_WALL_CLOCK_MINUTES_PER_STORY, 1.5,
        fs=fs, process=FakeProcess(alive_for=10), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    kinds = [entry["kind"] for entry in entries]
    # Two entries share this kind -- one intent, one outcome (mirrors the
    # idle ladder's own `idle-defer` pair).
    assert kinds.count("budget-stop") == 2
    # Terminal: the budget-stop pair, then this tick's own ordinary
    # heartbeat, then the final detach -- nothing after.
    assert kinds[-3:] == ["budget-stop", "supervisor-heartbeat", "supervisor-detach"]
    assert harness.stop_calls == [(_HOME, _HARNESS_RUN_ID)]

    stop_intent, stop_outcome = (e for e in entries if e["kind"] == "budget-stop")
    assert stop_intent["phase"] == "intent"
    assert stop_outcome["phase"] == "outcome"
    assert stop_outcome["intent_id"] == stop_intent["id"]
    assert stop_intent["payload"]["scope"] == "run"
    assert stop_intent["payload"]["metric"] == "wall_clock"
    assert stop_outcome["payload"]["stopped"] is True
    assert "finding" not in stop_outcome["payload"]

    assert entries[-1]["payload"]["reason"] == "budget-run-wall_clock-exceeded"


def test_run_wall_clock_ceiling_breach_with_a_failed_stop_still_detaches():
    """I/O matrix: "A failed stop is recorded (MRS-SUPV-005) but the loop
    still exits" -- mirrors the idle ladder's own ``defer``-with-failed-stop
    shape, one code higher in the SAME area."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    harness.fail_stop = HarnessError("unreachable")

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN,
        _MAX_WALL_CLOCK_MINUTES_PER_STORY, 1.5,
        fs=fs, process=FakeProcess(alive_for=10), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    stop_intent, stop_outcome = (e for e in entries if e["kind"] == "budget-stop")
    assert stop_outcome["payload"]["stopped"] is False
    assert stop_outcome["payload"]["finding"]["code"] == "MRS-SUPV-005"
    assert stop_outcome["payload"]["finding"]["severity"] == "warn"
    assert entries[-1]["payload"]["reason"] == "budget-run-wall_clock-exceeded"


def test_story_wall_clock_ceiling_breach_uses_the_story_scope_reason():
    """The per-story sibling of the two tests above -- ``harness_run_id``
    must resolve a current story (via ``usage_snapshot``) before the
    per-story wall-clock ceiling has anything to measure from."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    harness.usage_snapshot_result = UsageSnapshot(
        story_key="3.6",
        story_weighted_tokens=100,
        run_weighted_tokens=100,
        sample_path=_HOME / ".bmad-loop" / "runs" / _HARNESS_RUN_ID / "state.json",
    )

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN,
        1.5, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=10), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    stop_intent, stop_outcome = (e for e in entries if e["kind"] == "budget-stop")
    assert stop_intent["payload"]["scope"] == "story"
    assert stop_intent["payload"]["metric"] == "wall_clock"
    assert entries[-1]["payload"]["reason"] == "budget-story-wall_clock-exceeded"


def test_token_ceiling_breach_on_a_fresh_sample():
    """I/O matrix: "Per-story token ceiling, fresh sample" -- a resolved
    current story, ``state.json`` mtime within ``idle_threshold_minutes`` ->
    weighted per-story tokens compared to ``max_tokens_per_story``; breach
    stops the run exactly like a wall-clock breach does."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    # `state_json_mtime` defaults to `float("inf")` -- always fresh.
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    harness.usage_snapshot_result = UsageSnapshot(
        story_key="3.6",
        story_weighted_tokens=150,
        run_weighted_tokens=150,
        sample_path=_HOME / ".bmad-loop" / "runs" / _HARNESS_RUN_ID / "state.json",
    )

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        _IDLE_THRESHOLD_MINUTES, 100.0, _MAX_TOKENS_PER_RUN,
        _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=5), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    stop_intent, stop_outcome = (e for e in entries if e["kind"] == "budget-stop")
    assert stop_intent["payload"]["scope"] == "story"
    assert stop_intent["payload"]["metric"] == "tokens"
    assert stop_intent["payload"]["observed"] == 150
    assert stop_intent["payload"]["limit"] == 100.0
    assert entries[-1]["payload"]["reason"] == "budget-story-tokens-exceeded"
    # The state.json staleness query itself was made (path-aware, separate
    # from the idle ladder's own harness.log query).
    assert observer.state_json_mtime_calls


def test_stale_usage_sample_skips_both_token_ceilings_but_not_wall_clock():
    """I/O matrix: a stale/unresolvable ``state.json`` mtime journals
    ``MRS-SUPV-006`` ONCE (never on every tick) and skips BOTH token
    ceilings for that tick; the wall-clock ceilings remain evaluable and
    binding (AD-32's own "no ceiling exists that can only be evaluated from
    session-written data")."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    # Ancient mtime relative to any `moment` this clock ever produces.
    observer = FakeObserver(pane="idle", state_json_mtime=0.0)
    harness = FakeHarness()
    # Would BREACH immediately if the staleness gate did not skip it.
    harness.usage_snapshot_result = UsageSnapshot(
        story_key="3.6",
        story_weighted_tokens=10_000_000,
        run_weighted_tokens=10_000_000,
        sample_path=_HOME / ".bmad-loop" / "runs" / _HARNESS_RUN_ID / "state.json",
    )

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN,
        _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=3), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    kinds = [entry["kind"] for entry in entries]
    # Journaled once, at the FIRST tick, despite THREE ticks all being
    # stale -- never a flood of identical findings.
    assert kinds.count("budget-usage-stale") == 1
    assert "budget-stop" not in kinds
    assert "budget-warn" not in kinds
    stale_entry = next(e for e in entries if e["kind"] == "budget-usage-stale")
    assert stale_entry["phase"] == "observation"
    assert stale_entry["payload"]["finding"]["code"] == "MRS-SUPV-006"
    assert stale_entry["payload"]["finding"]["severity"] == "warn"
    # Never `unevaluable`, never a run-halting rung -- the run still exits
    # ordinarily (`watched-process-exited`, not any `budget-*-exceeded`).
    assert entries[-1]["payload"]["reason"] == "watched-process-exited"


def test_usage_read_failure_with_a_fresh_mtime_also_journals_stale_evidence():
    """Review finding: `usage_snapshot` returning `None` for a NON-staleness
    reason (a fresh `state.json` mtime, but the read/parse itself failed --
    a torn concurrent write, a momentary `bmad_loop` import failure) must
    NOT silently disable both token ceilings with zero diagnostic. Widened
    to fire the SAME `MRS-SUPV-006` a stale mtime fires, since the
    operational consequence -- both token ceilings unevaluable this tick,
    wall-clock remains binding -- is identical either way."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    # `state_json_mtime` defaults to `float("inf")` -- always FRESH.
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    harness.usage_snapshot_result = None  # the read itself failed

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN,
        _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=3), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    kinds = [entry["kind"] for entry in entries]
    assert kinds.count("budget-usage-stale") == 1
    stale_entry = next(e for e in entries if e["kind"] == "budget-usage-stale")
    assert stale_entry["payload"]["finding"]["code"] == "MRS-SUPV-006"
    assert "unreadable" in stale_entry["payload"]["finding"]["message"]
    assert entries[-1]["payload"]["reason"] == "watched-process-exited"


def test_a_breach_on_one_ceiling_suppresses_a_same_tick_warn_on_another():
    """Review finding: `_act_on_budget_transition`'s ``deferred`` guard used
    to sit only inside the ``BREACHED`` branch, so a DIFFERENT ceiling
    crossing into ``APPROACHING`` in the SAME tick -- after an earlier
    ceiling already breached and set ``deferred = True`` -- still journaled
    a ``budget-warn`` chronologically AFTER the terminal ``budget-stop``
    pair, for a run already ending. The run-level wall-clock ceiling
    breaches immediately (limit tiny); the run-level token ceiling
    simultaneously crosses into APPROACHING (80% of a much larger limit) on
    the very same tick -- only the breach may act."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    # 850 / 1_000 = 0.85 >= the fixed 0.8 approach ratio -- APPROACHING.
    harness.usage_snapshot_result = UsageSnapshot(
        story_key=None, story_weighted_tokens=None, run_weighted_tokens=850,
        sample_path=_HOME / ".bmad-loop" / "runs" / _HARNESS_RUN_ID / "state.json",
    )

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        # A 1-second-scale wall-clock-per-run ceiling breaches on tick 1;
        # the token-per-run ceiling (1_000) is evaluated in the SAME tick.
        _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, 1_000,
        _MAX_WALL_CLOCK_MINUTES_PER_STORY, 1e-9,
        fs=fs, process=FakeProcess(alive_for=3), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    kinds = [entry["kind"] for entry in entries]
    assert "budget-stop" in kinds
    # The token ceiling's own APPROACHING transition never got to fire --
    # the wall-clock breach's `deferred = True` (checked BEFORE either
    # branch now) suppressed it, even though 850 >= 0.8 * 1_000 is true.
    assert "budget-warn" not in kinds
    stop_index = kinds.index("budget-stop")
    detach_index = kinds.index("supervisor-detach")
    assert stop_index < detach_index
    assert entries[-1]["payload"]["reason"] == "budget-run-wall_clock-exceeded"


def test_no_single_current_story_skips_per_story_ceilings_only():
    """I/O matrix: zero or >1 non-terminal ``StoryTask`` -> ``usage_snapshot``
    reports ``story_key=None``; per-story ceilings are skipped, but per-run
    ceilings (wall-clock AND, on a fresh sample, tokens) are still
    evaluated."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    harness.usage_snapshot_result = UsageSnapshot(
        story_key=None,
        story_weighted_tokens=None,
        run_weighted_tokens=500,
        sample_path=_HOME / ".bmad-loop" / "runs" / _HARNESS_RUN_ID / "state.json",
    )

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, 400.0,
        _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=3), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    stop_intent, _stop_outcome = (e for e in entries if e["kind"] == "budget-stop")
    # The RUN token ceiling still fired -- 500 >= 400 -- even though no
    # single current story was ever resolvable.
    assert stop_intent["payload"]["scope"] == "run"
    assert stop_intent["payload"]["metric"] == "tokens"
    assert "budget-usage" not in [e["kind"] for e in entries]


def test_budget_usage_journals_the_canonical_feed_key_not_the_harness_slug():
    """REGRESSION (review finding): ``UsageSnapshot.story_key`` carries
    bmad-loop's OWN key spelling verbatim -- the full slug, verified live as
    e.g. ``"3-6-budget-ceilings-and-the-heaviest-story-advisory"`` -- while
    every other story identifier Marshal writes goes through
    ``render_feed_key`` (the dot form; see ``cli/spin.py``'s own
    ``data["preview"]``). Journaling the raw form put the SAME story under
    two identities in ONE run's evidence, so a consumer joining per-story
    cost back to the launch preview by exact match found nothing.

    The pre-existing transition tests never caught it because they hand-build
    ``UsageSnapshot(story_key="3.6", ...)`` -- already the dot form, a shape
    the real adapter never produces."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    sample_path = _HOME / ".bmad-loop" / "runs" / _HARNESS_RUN_ID / "state.json"
    harness.usage_snapshot_sequence = [
        UsageSnapshot(
            story_key="3-6-budget-ceilings-and-the-heaviest-story-advisory",
            story_weighted_tokens=1_000, run_weighted_tokens=1_000,
            sample_path=sample_path,
        ),
    ]

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN,
        _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=2), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    usage_entries = [e for e in entries if e["kind"] == "budget-usage"]
    assert usage_entries, "the run-end flush must journal the current story"
    assert usage_entries[-1]["payload"]["story_key"] == "3.6"


def test_budget_usage_falls_back_to_the_raw_key_when_it_cannot_be_normalized():
    """An unparseable harness key is still better attribution than none --
    ``normalize`` is the sole parser (AD-23), never a second-guessing regex,
    so a key it rejects is journaled verbatim rather than dropped."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    sample_path = _HOME / ".bmad-loop" / "runs" / _HARNESS_RUN_ID / "state.json"
    harness.usage_snapshot_sequence = [
        UsageSnapshot(
            story_key="not-a-story-key", story_weighted_tokens=1_000,
            run_weighted_tokens=1_000, sample_path=sample_path,
        ),
    ]

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN,
        _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=2), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    usage_entries = [e for e in entries if e["kind"] == "budget-usage"]
    assert usage_entries[-1]["payload"]["story_key"] == "not-a-story-key"


def test_no_budget_observation_is_journaled_after_a_terminal_budget_stop():
    """REGRESSION (review finding): the ``deferred`` guard added one pass
    earlier sits INSIDE ``_act_on_budget_transition``, so it suppressed a
    second same-tick ``budget-warn`` but nothing else. A ceiling that
    breached wrote its terminal ``budget-stop`` pair and execution then FELL
    THROUGH -- spending another ``usage_snapshot`` read against a run just
    killed and appending ``budget-usage``/``budget-usage-stale``
    observations CHRONOLOGICALLY AFTER the terminal pair, for a run already
    ending.

    The end-of-run ``budget-usage`` flush is the one legitimate exception:
    it is written deliberately after the loop, before the detach entry."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN,
        _MAX_WALL_CLOCK_MINUTES_PER_STORY, 1.5,
        fs=fs, process=FakeProcess(alive_for=10), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    kinds = [entry["kind"] for entry in entries]
    stop_outcome_index = max(
        i for i, e in enumerate(entries)
        if e["kind"] == "budget-stop" and e["phase"] == "outcome"
    )
    assert "budget-usage-stale" not in kinds[stop_outcome_index:], (
        "a stale-evidence observation landed after the terminal budget-stop"
    )


def test_story_transition_journals_usage_for_the_outgoing_story():
    """I/O matrix: the current story key differs from the last observed one
    -> one ``budget-usage`` observation attributes the OUTGOING story's last
    known weighted tokens as ``cost_estimate`` (the spec's own Always
    bullet: no dollar pricing table exists, so the weighted-token total
    itself IS the cost proxy); per-story elapsed/tally resets for the new
    one."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    sample_path = _HOME / ".bmad-loop" / "runs" / _HARNESS_RUN_ID / "state.json"
    harness.usage_snapshot_sequence = [
        UsageSnapshot(
            story_key="3.6", story_weighted_tokens=1_000, run_weighted_tokens=1_000,
            sample_path=sample_path,
        ),
        UsageSnapshot(
            story_key="3.6", story_weighted_tokens=2_000, run_weighted_tokens=2_000,
            sample_path=sample_path,
        ),
        UsageSnapshot(
            story_key="3.7", story_weighted_tokens=50, run_weighted_tokens=2_050,
            sample_path=sample_path,
        ),
    ]

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN,
        _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=4), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    usage_entries = [e for e in entries if e["kind"] == "budget-usage"]
    # TWO entries (review finding): the mid-run transition away from "3.6"
    # AND the run-end flush of "3.7" (which the watched process's own exit
    # ends before any LATER transition could ever be observed for it) --
    # the fix for "a run's final story never got a budget-usage entry at
    # all" (this story's own acceptance criterion: "consumption is
    # journaled per story").
    assert len(usage_entries) == 2
    assert usage_entries[0]["phase"] == "observation"
    assert usage_entries[0]["payload"] == {
        "story_key": "3.6",
        "cost_estimate": 2_000,
    }
    assert usage_entries[1]["phase"] == "observation"
    assert usage_entries[1]["payload"] == {
        "story_key": "3.7",
        "cost_estimate": 50,
    }
    # Every new Story 3.6 entry kind still conforms to the packaged, frozen
    # journal contract -- the same schema-validation discipline Story 3.5's
    # own `test_normal_attach_journals_attach_then_heartbeats_then_detach`
    # applies to the FIRST producer of `Phase.OBSERVATION` entries.
    schema = _journal_schema()
    for entry in entries:
        jsonschema.validate(instance=entry, schema=schema)


def test_story_transition_with_zero_weighted_tokens_journals_a_null_cost_estimate():
    """The spec's own Never clause: ``cost_estimate`` "stays null only if
    bmad-loop's own state ever reports zero sessions for a task" --
    operationally, a weighted total of exactly 0 (the shape
    ``UsageSnapshot``'s own 4 fields can express)."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    sample_path = _HOME / ".bmad-loop" / "runs" / _HARNESS_RUN_ID / "state.json"
    harness.usage_snapshot_sequence = [
        UsageSnapshot(
            story_key="3.6", story_weighted_tokens=0, run_weighted_tokens=0,
            sample_path=sample_path,
        ),
        UsageSnapshot(
            story_key="3.7", story_weighted_tokens=10, run_weighted_tokens=10,
            sample_path=sample_path,
        ),
    ]

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN,
        _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=3), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    usage_entries = [e for e in entries if e["kind"] == "budget-usage"]
    # TWO entries, same reason as the previous test's own review-finding
    # comment: the transition away from "3.6" AND the run-end flush of the
    # still-current "3.7".
    assert len(usage_entries) == 2
    assert usage_entries[0]["payload"] == {"story_key": "3.6", "cost_estimate": None}
    assert usage_entries[1]["payload"] == {"story_key": "3.7", "cost_estimate": 10}


def test_single_story_run_with_no_transition_still_journals_one_budget_usage_entry():
    """Review finding: a `marshal factory spin --story <key>` launch (a
    common, single-story invocation) NEVER observes a story-key transition
    -- the run's only story is current from the first tick to the process's
    own exit. Before the run-end flush fix, this shape produced ZERO
    `budget-usage` entries at all, silently failing this story's own
    acceptance criterion ("consumption is journaled per story") for the
    single-story case specifically."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1") + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()
    sample_path = _HOME / ".bmad-loop" / "runs" / _HARNESS_RUN_ID / "state.json"
    harness.usage_snapshot_result = UsageSnapshot(
        story_key="3.6", story_weighted_tokens=4_200, run_weighted_tokens=4_200,
        sample_path=sample_path,
    )

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN,
        _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=3), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    usage_entries = [e for e in entries if e["kind"] == "budget-usage"]
    assert len(usage_entries) == 1
    assert usage_entries[0]["payload"] == {"story_key": "3.6", "cost_estimate": 4_200}
    # The flush lands BEFORE the final `supervisor-detach`, never after.
    detach_index = next(i for i, e in enumerate(entries) if e["kind"] == "supervisor-detach")
    usage_index = next(i for i, e in enumerate(entries) if e["kind"] == "budget-usage")
    assert usage_index < detach_index


def test_harness_run_id_unavailable_still_evaluates_the_run_wall_clock_ceiling():
    """I/O matrix / AD-32's own rule: the per-run wall-clock ceiling needs
    no ``harness_run_id`` at all -- it must stay evaluable even when the
    idle ladder itself cannot act (``MRS-SUPV-003``'s own scenario)."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1", harness_run_id=None) + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN,
        _MAX_WALL_CLOCK_MINUTES_PER_STORY, 1.5,
        fs=fs, process=FakeProcess(alive_for=10), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    kinds = [entry["kind"] for entry in entries]
    assert "budget-stop" in kinds
    # No harness_run_id to stop against -- best-effort, never raised.
    assert harness.stop_calls == []
    stop_outcome = next(
        e for e in entries if e["kind"] == "budget-stop" and e["phase"] == "outcome"
    )
    assert stop_outcome["payload"]["stopped"] is False
    assert stop_outcome["payload"]["finding"]["code"] == "MRS-SUPV-005"
    # Supervision CONTINUES: nothing was stopped, so detaching here would
    # only blind the one process watching a live, runaway harness (review
    # finding -- this assertion previously pinned the opposite, a detach
    # with `reason="budget-run-wall_clock-exceeded"` for a stop that never
    # happened). Mirrors `MRS-SUPV-003`'s own "cannot act for this run;
    # continuing heartbeat-only supervision" precedent, and the run ends on
    # the ordinary watched-process-exited path instead.
    assert entries[-1]["payload"]["reason"] == "watched-process-exited"


def test_a_budget_breach_with_no_harness_run_id_never_re_fires_on_later_ticks():
    """The rising-edge latch is what makes "continue heartbeat-only" safe
    (review finding): once the ceiling reads ``BREACHED`` the rank check
    makes every later tick a no-op, so a breach that could not be acted on
    journals exactly ONE ``budget-stop`` pair rather than one per tick for
    the rest of the run's life."""
    fs = FakeFs(journal_text=_launch_outcome_line("acme-run-1", harness_run_id=None) + "\n")
    clock = AdvancingClock()
    observer = FakeObserver(pane="idle")
    harness = FakeHarness()

    rc = run_supervisor(
        _HOME, "acme", "acme-run-1", 4242, _LOG_PATH,
        _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN,
        _MAX_WALL_CLOCK_MINUTES_PER_STORY, 1.5,
        fs=fs, process=FakeProcess(alive_for=20), clock=clock, observer=observer,
        harness=harness, sleep=clock.sleep,
    )

    assert rc == 0
    entries = [json.loads(line) for _, line, _ in fs.appended_lines]
    stops = [e for e in entries if e["kind"] == "budget-stop"]
    assert len(stops) == 2, "exactly one intent + one outcome, never one pair per tick"
    assert [e["phase"] for e in stops] == ["intent", "outcome"]


# --- main(): argv parsing + dispatch --------------------------------------------


def test_main_parses_argv_and_dispatches_to_run_supervisor(monkeypatch):
    calls: list[tuple[Path, str, str, int, Path, float, float, float, float, float]] = []

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
        calls.append(
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

    rc = main(
        [
            "/home/acme-loop",
            "acme",
            "acme-run-1",
            "4242",
            "/home/acme-loop/supervisor.log",
            "25",
            "4000000",
            "40000000",
            "240",
            "600",
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
            4000000.0,
            40000000.0,
            240.0,
            600.0,
        )
    ]


def test_main_rejects_the_wrong_argument_count(capsys):
    rc = main(["only", "two"])
    assert rc != 0
    assert "usage" in capsys.readouterr().err.lower()


def test_main_rejects_a_non_integer_watched_pid(capsys):
    rc = main(
        [
            "/home",
            "acme",
            "acme-run-1",
            "not-a-pid",
            "/home/supervisor.log",
            "25",
            "4000000",
            "40000000",
            "240",
            "600",
        ]
    )
    assert rc != 0
    assert "invalid watched pid" in capsys.readouterr().err.lower()


def test_main_rejects_a_zero_or_negative_watched_pid(capsys):
    """Review finding: ``os.kill(pid, 0)`` gives ``0``/negative pids
    special "signal a process GROUP" semantics rather than "no such
    process" -- a malformed invocation naming one of them must be refused
    cleanly rather than let ``is_alive`` silently probe an unintended
    target."""
    for bad_pid in ("0", "-1"):
        rc = main(
            [
                "/home",
                "acme",
                "acme-run-1",
                bad_pid,
                "/home/supervisor.log",
                "25",
                "4000000",
                "40000000",
                "240",
                "600",
            ]
        )
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
        rc = main(
            [
                "/home/acme-loop",
                bad_slug,
                "acme-run-1",
                "4242",
                "/home/s.log",
                "25",
                "4000000",
                "40000000",
                "240",
                "600",
            ]
        )
        assert rc != 0, f"slug {bad_slug!r} was accepted"
        assert "invalid project slug" in capsys.readouterr().err.lower()


def test_main_rejects_a_run_id_that_escapes_the_run_directory(capsys):
    """The ``run_id`` half of the same finding: it is the LAST path segment
    of the run directory, so a separator or a dot-segment in it relocates
    the journal just as effectively as a traversing slug does."""
    for bad_run_id in ("../../evil", "..", ".", "acme/run", "", "a\\b"):
        rc = main(
            [
                "/home/acme-loop",
                "acme",
                bad_run_id,
                "4242",
                "/home/s.log",
                "25",
                "4000000",
                "40000000",
                "240",
                "600",
            ]
        )
        assert rc != 0, f"run_id {bad_run_id!r} was accepted"
        assert "invalid run id" in capsys.readouterr().err.lower()


def test_main_accepts_a_real_spin_minted_run_id(monkeypatch):
    """Negative control for the two guards above -- the real ``run_id``
    shape ``cli/spin.py`` mints (``<slug>-<timestamp>-<suffix>``) must still
    pass, or the guards would have broken every genuine invocation."""
    calls: list[str] = []

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
            "4000000",
            "40000000",
            "240",
            "600",
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
        rc = main(
            [
                "/home",
                "acme",
                "acme-run-1",
                bad_pid,
                "/home/s.log",
                "25",
                "4000000",
                "40000000",
                "240",
                "600",
            ]
        )
        assert rc != 0, f"pid {bad_pid} was accepted"
        assert "not probeable" in capsys.readouterr().err.lower()


def test_main_accepts_the_largest_probeable_pid(monkeypatch):
    """Negative control: the guard above must refuse only what ``os.kill``
    genuinely cannot convert, never a real (if implausibly large) pid."""
    calls: list[int] = []

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
        calls.append(watched_pid)
        return 0

    monkeypatch.setattr(supervisor_main, "run_supervisor", _fake_run_supervisor)
    rc = main(
        [
            "/home",
            "acme",
            "acme-run-1",
            str(supervisor_main._MAX_PROBEABLE_PID),
            "/home/s.log",
            "25",
            "4000000",
            "40000000",
            "240",
            "600",
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
        rc = main(
            [
                bad_home,
                "acme",
                "acme-run-1",
                "4242",
                "/home/s.log",
                "25",
                "4000000",
                "40000000",
                "240",
                "600",
            ]
        )
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
    rc = main(
        [
            "/home",
            "acme",
            "acme-run-1",
            "4242",
            "/home/s.log",
            "not-a-number",
            "4000000",
            "40000000",
            "240",
            "600",
        ]
    )
    assert rc != 0
    assert "invalid idle threshold minutes" in capsys.readouterr().err.lower()


def test_main_rejects_a_non_positive_or_non_finite_idle_threshold(capsys):
    """``nan``/``inf`` alongside zero and the negatives (review finding).
    The guard used to be a bare ``<= 0``, the exact footgun
    ``core/supervise.py``'s own guard documents: IEEE 754 makes EVERY
    comparison against ``nan`` false, so a NaN threshold sailed through and
    only surfaced one tick later as ``evaluate_idle``'s ``ValueError`` --
    which this module's journal-write handler catches and reports as
    "cannot append to journal", blaming the journal for an argv defect and
    leaving a ``supervisor-attach`` with no matching ``supervisor-detach``.
    ``inf`` passed too, and silently disabled the ladder for the run's whole
    life (every elapsed/inf floor-divides to rung ``NONE``)."""
    for bad_threshold in ("0", "-1", "-25", "nan", "NaN", "inf", "-inf", "Infinity"):
        rc = main(
            [
                "/home",
                "acme",
                "acme-run-1",
                "4242",
                "/home/s.log",
                bad_threshold,
                "4000000",
                "40000000",
                "240",
                "600",
            ]
        )
        assert rc != 0, f"threshold {bad_threshold!r} was accepted"
        assert "must be a positive finite number" in capsys.readouterr().err.lower()


def test_main_accepts_a_fractional_idle_threshold(monkeypatch):
    calls: list[float] = []

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
        calls.append(idle_threshold_minutes)
        return 0

    monkeypatch.setattr(supervisor_main, "run_supervisor", _fake_run_supervisor)
    rc = main(
        [
            "/home",
            "acme",
            "acme-run-1",
            "4242",
            "/home/s.log",
            "0.5",
            "4000000",
            "40000000",
            "240",
            "600",
        ]
    )
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
        _LOG_PATH, _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
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
        _LOG_PATH, _IDLE_THRESHOLD_MINUTES, _MAX_TOKENS_PER_STORY, _MAX_TOKENS_PER_RUN, _MAX_WALL_CLOCK_MINUTES_PER_STORY, _MAX_WALL_CLOCK_MINUTES_PER_RUN,
        fs=fs, process=FakeProcess(alive_for=1), clock=FakeClock(),
        observer=FakeObserver(), sleep=_no_sleep,
    )

    assert rc == 0
    assert fs.appended_lines == []
    err = capsys.readouterr().err
    assert "unevaluable" in err.lower()
    assert "1 journal line" in err.lower()
