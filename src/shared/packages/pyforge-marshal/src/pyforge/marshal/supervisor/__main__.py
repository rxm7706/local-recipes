"""The supervisor sidecar's actual entry point (Story 3.4/3.5, architecture
spine AD-9/AD-20/AD-25/AD-28/AD-30): ``python -m pyforge.marshal.supervisor
<home> <slug> <run_id> <watched_pid> <log_path> <idle_threshold_minutes>``.
``cli/spin.py`` detach-spawns exactly this invocation (via ``ProcessPort.
spawn_detached``) as the LAST step of a successful ``marshal factory spin``
-- see that module's own docstring for why "last", after the ``run-launch``
outcome entry append is attempted whether or not it itself succeeded.

**Order of operations (``run_supervisor``).** Read the run's own
``journal.jsonl`` ONCE (``FsPort.read_text`` + ``core.journal.fold``, plus
any sidecar blob that journal's own lines reference -- see "Why the read
side DOES load sidecars" below; the journal itself is never re-read, and
nothing is read again after this point) -> inert-check: if no
``kind: "run-launch"`` entry in
EITHER ``phase: intent`` or ``phase: outcome`` names THIS ``run_id``, exit
immediately, code 0, no journal write at all (AD-25: the journal is the
single source of run truth, so "was this run really started by Marshal" is
a journal question, never a lock file -- see this story's own Design
Notes). Accepting the INTENT phase too is load-bearing, not belt-and-
braces: ``cli/spin.py`` spawns this sidecar whether or not its own
outcome-entry append succeeded (``MRS-SPIN-006``), and AD-6's write-before-
act ordering guarantees the intent entry lands BEFORE any spawn is even
attempted -- so on the outcome-append-failure branch the intent entry is
the ONLY proof of Marshal ownership that exists, and an outcome-only check
would exit inert on a live run Marshal genuinely started. Then: append one
``observation`` entry (``kind="supervisor-attach"``, payload ``{pid,
watched_pid}``) -> resolve ``harness_run_id`` once, from that SAME
run-launch outcome entry's own payload (Story 3.5 -- see "Idle-strand
detection" below) -> take ONE ``ProcessPort.is_alive(watched_pid)`` reading
and loop while it holds AND the idle ladder has not deferred: sleep a fixed
60s tick (``_TICK_SECONDS`` -- no policy knob exists for this yet, and
inventing one against no real caller would be speculative surface, per this
codebase's own precedent), sample ``ClockPort.now()`` plus a FRESH
``is_alive`` reading plus (when ``harness_run_id`` resolved)
``SessionObserverPort.pane_content``/``mtime`` against the REAL session/log
target, evaluate the idle ladder and act on any escalation, then append one
``observation`` (``kind="supervisor-heartbeat"``, payload ``{pid,
watched_alive, sampled_at}``) -- ``watched_alive`` carries that tick's own
fresh reading, so the tick that discovers the watched process just died
journals one truthful ``false`` heartbeat rather than a tautological
``true`` -- and let that same reading (plus the ladder's own terminal
``defer``) decide whether another tick follows. When the loop ends, append
one final ``observation`` (``kind="supervisor-detach"``, payload ``{pid,
reason}`` -- ``"watched-process-exited"``, Story 3.5's own terminal ladder
rung ``"idle-deferred"``, or ``"idle-retry-failed"`` when a
``stop-and-retry``'s ``resume`` failed after its ``stop`` had already
succeeded) and exit 0.

**Idle-strand detection (Story 3.5, AD-9/AD-20, FR-12).** The two
placeholder gaps Story 3.4 explicitly left for this story are closed here:
the tmux SESSION passed to the observer is no longer Marshal's own
``run_id`` (a name no live tmux session was ever actually keyed by) but
``f"bmad-loop-{harness_run_id}"`` -- the harness's OWN self-minted run id,
recovered ONCE at attach from the run-launch outcome entry's own
``harness_run_id`` field (the SAME fold already read for the inert-check,
never a second read) -- and the log path sampled for mtime is no longer
this sidecar's OWN redirected log but the run's real ``harness.log``
(``_HARNESS_LOG_FILENAME``, the SAME literal ``cli/spin.py``'s own
``_LOG_FILENAME`` names). If ``harness_run_id`` cannot be resolved (the
outcome entry is missing entirely -- ``MRS-SPIN-006``'s own scenario -- or
its ``harness_run_id`` field is ``None``/blank -- ``MRS-SPIN-004``'s own
scenario), a ``MRS-SUPV-003`` finding is journaled ONCE at attach (a new
``kind="idle-harness-run-id-unavailable"`` observation) and the ladder is
never evaluated for this run -- the tick loop continues heartbeat-only, per
this story's own Always bullet: "if it is unavailable, the ladder cannot
act ... no crash, no guess."

Each tick (when ``harness_run_id`` resolved) accumulates one
``core.supervise.Sample`` (the fresh clock reading, the freshly captured
pane text, the freshly read log mtime) into this invocation's own
in-memory list, and calls the PURE ``core.supervise.evaluate_idle`` over
the WHOLE accumulated sequence -- no port, no clock call, no I/O inside
that function itself (AD-20). The computed ``LadderRung`` is compared
against the rung this tick loop last acted on (``core.supervise.
rung_index``, since ``LadderRung`` carries no intrinsic ordering); a HIGHER
rung is acted on and journaled as one ``intent`` entry then one ``outcome``
entry (matching the existing ``Phase`` pairing rule -- never a single
combined entry), and the bookkeeping variable is then synced to the
freshly computed rung regardless of whether an action fired -- which is
what lets "fresh output re-arms the window" happen with NO special-cased
reset code here: a sample whose pane/mtime changed makes
``evaluate_idle`` itself return ``NONE`` again on the very next call, and
syncing the bookkeeping variable down to that ``NONE`` is what lets a LATER
full threshold re-escalate the ladder from scratch.

- ``nudge`` (first threshold crossing): ``SessionObserverPort.send_text``
  delivers a short continuation prompt into the resolved window. A ``False``
  return (no window resolved, or delivery failed) registers ``MRS-SUPV-001``
  in the outcome payload -- the ladder still advances its own bookkeeping,
  so a failed nudge is not retried every tick. On SUCCESS the pane is
  re-captured and the sample history collapsed onto that text while keeping
  ``core.supervise.idle_since``'s own anchor: the nudge types into the very
  pane this loop samples, so without the rebase its own echo reads as fresh
  output, re-arms the window it was escalating from, and the ladder cycles
  nudge -> re-arm -> nudge forever without ever reaching the next rung
  (review finding). "Fresh output" means the SESSION's, never this
  supervisor's own.
- ``stop-and-retry`` (second threshold crossing): ``HarnessPort.stop`` then
  ``.resume`` against ``harness_run_id`` -- confirmed live (this story's own
  Design Notes) as the one supported pairing for recovering an unresponsive
  engine, never a bare re-``bmad-loop run``. On success, ``watched_pid`` is
  replaced by the new pid, the sample history is CLEARED (a fresh engine
  attempt starts its own fresh idle window), and the bookkeeping rung resets
  to ``NONE``. The three failure shapes are deliberately distinct: ``stop``
  itself raising registers ``MRS-SUPV-002`` and keeps watching the
  (possibly still-wedged) ORIGINAL pid, so the ladder naturally re-escalates
  to ``defer``; ``stop`` returning ``False`` skips ``resume`` entirely and
  records ``stopped: false`` with its own ``MRS-SUPV-002`` (never an
  ``already_finished`` claim this process did not observe); and ``resume``
  raising AFTER a successful ``stop`` leaves the original pid confirmed
  dead, so the loop ends via ``"idle-retry-failed"`` rather than letting the
  next tick mask a failed recovery as an ordinary completion. At most ONE
  stop-and-retry ever fires per run (``already_retried``): a later idle
  recurrence may still earn a ``nudge``, but that rung and everything above
  it collapses to ``defer``.
- ``defer`` (third threshold crossing, terminal): a best-effort
  ``HarnessPort.stop`` against the watched run (a deferred run must not keep
  burning tokens unsupervised; a failure here is tolerated but registers
  ``MRS-SUPV-002``, since it is the worst case this story exists to
  prevent), journaled, then the tick loop's own final ``supervisor-detach``
  carries ``reason: "idle-deferred"`` instead of
  ``"watched-process-exited"`` -- no further ladder or heartbeat activity
  follows.

Two guards sit between ``evaluate_idle`` and those branches, both review
findings. Escalation is clamped to ONE rung per tick (``rung_at``): the
ladder is a fixed 3-rung sequence, but ``evaluate_idle`` floor-divides, so
any threshold shorter than twice ``_TICK_SECONDS`` would otherwise let a
single tick jump straight to ``defer`` and hard-stop a healthy run without
ever nudging it. And a sample history in which NOTHING was ever observed
(no pane AND no log mtime, for every sample) is treated as ``NONE`` rather
than as idleness -- ``None != None`` is ``False``, so such a history never
re-arms and reads as maximal idleness, which since ``defer`` gained its
stop call would turn a broken observation channel into a killed HEALTHY
run. The ladder acts only on evidence it actually has.

Every append here is a ``Phase.OBSERVATION`` entry EXCEPT the three ladder
actions above, which are ``Phase.INTENT`` then ``Phase.OUTCOME`` pairs
(AD-6's write-before-act: the intent is fsynced BEFORE the action is
attempted, matching ``cli/spin.py``'s own launch-intent convention) --
every other write here uses ``fsync=False``, since an observation carries
no invariant a crash between the write and an fsync would silently
violate. A journal append failure (``FsError``) at ANY point -- the attach
entry, a heartbeat, a ladder action, or the final detach -- is fatal to
this process: it prints a diagnostic to its own stderr (already redirected
to ``log_path`` by the parent's ``spawn_detached`` call -- this module
never opens ``log_path`` itself) and exits non-zero rather than looping
forever against a journal it cannot durably write to. A dead supervisor
with no further heartbeats is itself a later-detectable condition (AD-9: "a
dead supervisor is a reported condition ... never silence") -- surfacing it
as a `status` finding is a later epic's own FR-36..40 scope, explicitly out
of this story's Surface.

**Why the read side DOES load sidecars.** ``core.journal.fold`` accepts an
optional ``sidecars`` mapping for large, sidecar-referenced payloads, and
quarantines any line whose ``sidecar_ref`` it cannot resolve
(``MRS-JOURNAL-002``) -- a quarantined line never reaches ``by_kind``, so
it is invisible to the inert-check above. This module used to supply no
mapping at all, on the stated ground that both ``cli/spin.py`` payloads are
"always small enough to inline". That was FALSE for the intent entry
(review finding, reproduced live): ``cli/spin.py`` puts its whole echoed
``preview`` -- one rendered feed key per RESOLVED story, unbounded -- into
that payload, which crosses ``core.journal.SIDECAR_THRESHOLD_BYTES`` at
roughly 150 stories and is then written as a ``{"sidecar_ref": ...}``
placeholder. On the ``MRS-SPIN-006`` branch (the outcome append itself
failed) that sidecar-referenced intent is the ONLY ownership proof on disk
-- exactly the case the phase-widening above exists to serve -- so a
large-project run whose outcome could not be journaled went silently
unsupervised. Each referenced blob is therefore read alongside the journal
(``_sidecar_refs`` + ``FsPort.read_text``) and handed to ``fold``.

This does not weaken AD-9's "touches no other externally-writable input for
its own control flow": no blob's CONTENT can redirect anything here. The
inert-check reads only ``kind``/``phase``/``run_id``, all of which live in
the journal LINE itself; resolving a sidecar only decides whether that line
survives folding at all. Refs are accepted solely in
``prepare_for_write``'s own ``blobs/<name>`` shape (no separators, no dot
segments) so a corrupt or forged ref cannot walk this read out of the run
directory, and ``fold`` independently re-validates every ref against the
owning entry's own id before resolving it.

**Why this module duplicates, rather than imports, ``cli/spin.py``'s own
``_tier3_path``/``_run_dir``/``_format_entry_ts`` helpers.** This story's
own new import-linter contract forbids ``pyforge.marshal.supervisor`` from
importing ``pyforge.marshal.cli`` AT ALL (AD-9: no control channel back
into the session's own front door, structural) -- so even though these
three helpers are pure, private, and byte-for-byte reusable, importing them
from ``cli/spin.py`` would violate the very contract this story exists to
add. Each is reproduced here verbatim rather than promoted to a shared
module neither story's own Code Map asks for (Simplicity First: match what
each story actually needs, not a speculative third location). The same
applies to ``_HARNESS_LOG_FILENAME`` (Story 3.5): it duplicates
``cli/spin.py``'s own ``_LOG_FILENAME`` literal for the identical reason.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from pathlib import Path

from ..adapters.clock_system import SystemClock
from ..adapters.fs_local import FsError, LocalFs
from ..adapters.harness_bmadloop import BmadLoopHarness, HarnessError
from ..adapters.observer_mux import MultiplexerObserver
from ..adapters.process_posix import PosixProcess
from ..core import policy
from ..core.journal import (
    JournalEntryId,
    Phase,
    build_entry,
    fold,
    prepare_for_write,
)
from ..core.model import Finding, Severity
from ..core.supervise import (
    LadderRung,
    Sample,
    evaluate_idle,
    idle_since,
    rung_at,
    rung_index,
)
from ..ports.clock import ClockPort
from ..ports.fs import FsPort
from ..ports.harness import HarnessPort
from ..ports.observer import SessionObserverPort
from ..ports.process import ProcessPort

# Matches cli/spin.py's own _JOURNAL_FILENAME/_LAUNCH_KIND/_LOG_FILENAME --
# duplicated, not imported, per this module's own docstring (the new AD-9
# contract forbids importing anything from pyforge.marshal.cli at all).
_JOURNAL_FILENAME = "journal.jsonl"
_LAUNCH_KIND = "run-launch"
_HARNESS_LOG_FILENAME = "harness.log"

# The idle ladder's own journal kinds (Story 3.5) -- each fires as one
# Phase.INTENT entry then one Phase.OUTCOME entry, never combined.
_NUDGE_KIND = "idle-nudge"
_STOP_AND_RETRY_KIND = "idle-stop-and-retry"
_DEFER_KIND = "idle-defer"
_HARNESS_RUN_ID_UNAVAILABLE_KIND = "idle-harness-run-id-unavailable"

# No policy knob exists for this yet (this story's own Never clause) -- a
# fixed constant is the only defensible value with no real caller to size a
# knob against.
_TICK_SECONDS = 60.0

# C `INT_MAX`: the largest pid `os.kill(pid, 0)` can convert at all (above
# it, CPython raises `OverflowError` before the kernel is ever consulted --
# verified live). `main()`'s own upper-bound guard below explains why this
# is refused at the boundary rather than absorbed by `is_alive`.
_MAX_PROBEABLE_PID = 2**31 - 1

# The idle ladder's nudge text (Story 3.5) -- delivered verbatim via
# `SessionObserverPort.send_text` into the session's live window, as if
# typed and submitted at its prompt. Plain, short, and non-committal: this
# sidecar cannot know what the agent was doing, only that it stopped
# producing observable output.
#
# Deliberately free of shell metacharacters (review finding). `send_text`
# delivers this as a literal keystroke stream followed by Enter, and the
# window it resolves is whichever one tmux marks ACTIVE -- which is the
# agent's in the ordinary case, but is whatever an attached operator last
# selected otherwise, and is a plain shell once the agent's own process
# exits. The previous wording contained a `;` (a shell command separator)
# and a clause opening with `if`, so a mis-targeted nudge did not merely
# land harmlessly in the wrong pane: it ran one bogus command and then left
# the shell hanging at a `>` continuation prompt forever -- which this same
# supervisor would then read back as a permanently unchanging pane. With no
# `;`, `|`, `&`, `$`, backtick or quote anywhere in it, the worst case is
# now a single "command not found" line.
_NUDGE_TEXT = (
    "Marshal idle check. No output has been observed from this session for "
    "a while. Please continue if you are still working, or report your "
    "current status if you are blocked or waiting on something."
)


def _tier3_path(home: Path, slug: str) -> Path:
    """Duplicates ``cli/spin.py``'s own helper of the same name verbatim --
    see this module's own docstring for why it cannot be imported instead."""
    return home / "_bmad-output" / "projects" / slug / "implementation-artifacts"


def _run_dir(home: Path, slug: str, run_id: str) -> Path:
    """Duplicates ``cli/spin.py``'s own helper of the same name verbatim."""
    return _tier3_path(home, slug) / "runs" / run_id


def _format_entry_ts(moment: datetime) -> str:
    """Duplicates ``cli/spin.py``'s own helper of the same name verbatim --
    ``core.journal.JournalEntry``'s own ``ts`` form:
    ``YYYY-MM-DDTHH:MM:SS.mmmZ``."""
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def _sidecar_refs(lines: Sequence[str]) -> tuple[str, ...]:
    """Every ``{"sidecar_ref": <str>}`` payload placeholder named by
    ``lines``, in order, deduplicated -- ``core.journal.fold``'s own
    ``sidecars`` mapping is keyed by exactly these strings (see this
    module's own docstring for why the read side needs them at all).

    Deliberately tolerant: a line this scan cannot parse is SKIPPED, never
    raised on -- ``fold`` is the one place a malformed line is judged, and
    quarantining is its job, not this helper's. Refs are accepted only in
    ``core.journal._sidecar_path_for``'s own ``blobs/<name>`` shape, with
    no path separators and no dot segments in ``<name>``, so a corrupt or
    forged ref can never walk the caller's ``read_text`` outside the run
    directory."""
    refs: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if '"sidecar_ref"' not in line:
            continue
        try:
            document = json.loads(line)
        except (ValueError, TypeError, RecursionError):
            continue
        if not isinstance(document, Mapping):
            continue
        payload = document.get("payload")
        if not isinstance(payload, Mapping) or len(payload) != 1:
            continue
        ref = payload.get("sidecar_ref")
        if not isinstance(ref, str) or not ref.startswith("blobs/"):
            continue
        name = ref[len("blobs/") :]
        if not name or "/" in name or "\\" in name or name in (".", ".."):
            continue
        if ref not in seen:
            seen.add(ref)
            refs.append(ref)
    return tuple(refs)


def _resolve_harness_run_id(fold_result, run_id: str) -> str | None:
    """The run-launch OUTCOME entry's own ``harness_run_id`` field (Story
    3.5) -- recovered from the SAME fold this module's own inert-check
    already computed, never a second read. ``None`` if no matching outcome
    entry exists (``MRS-SPIN-006``'s own scenario: the outcome append
    itself failed, so only the intent entry -- which carries no
    ``harness_run_id`` field at all -- proves ownership) or its
    ``harness_run_id`` field is ``None``/blank (``MRS-SPIN-004``'s own
    scenario: the harness's self-minted id could not be confirmed within
    ``spin``'s own poll window). Either way the idle ladder has no
    session/harness target to act against for this run."""
    for entry in fold_result.by_kind(_LAUNCH_KIND):
        if entry.run_id == run_id and entry.phase is Phase.OUTCOME:
            candidate = entry.payload.get("harness_run_id")
            return candidate if isinstance(candidate, str) and candidate else None
    return None


def run_supervisor(
    home: Path,
    slug: str,
    run_id: str,
    watched_pid: int,
    # Story 3.4's own placeholder mtime-observation target -- kept ONLY for
    # the argv contract's own shape/stability (never renumbered or removed;
    # doing so is out of this fix's own scope). Story 3.5 replaced its one
    # real use with the internally-derived `harness_log_path` below, so
    # `log_path` itself is no longer read anywhere in this function's body.
    log_path: Path,
    idle_threshold_minutes: float,
    *,
    fs: FsPort | None = None,
    process: ProcessPort | None = None,
    clock: ClockPort | None = None,
    observer: SessionObserverPort | None = None,
    harness: HarnessPort | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """The sidecar's own testable core -- everything ``__main__``'s own
    ``main()`` does after parsing argv. Every collaborator is DI'd with an
    adapter default (matching ``cli/spin.py``'s own ``fs``/``harness``
    convention), including ``sleep`` -- injecting a no-op callable is how
    this story's own tests exercise a multi-tick heartbeat/ladder loop in
    milliseconds rather than minutes (AD-20's own "every supervisor
    behaviour has a test that runs in milliseconds" requirement); a real
    invocation's own bounded-iteration-count safety valve is
    ``ProcessPort.is_alive`` itself eventually reporting ``False`` (or the
    idle ladder itself deferring), which a test controls directly through a
    fake ``ProcessPort``/``ClockPort``."""
    fs = fs if fs is not None else LocalFs()
    process = process if process is not None else PosixProcess()
    clock = clock if clock is not None else SystemClock()
    observer = observer if observer is not None else MultiplexerObserver()
    harness = harness if harness is not None else BmadLoopHarness()

    run_dir = _run_dir(home, slug, run_id)
    journal_path = run_dir / _JOURNAL_FILENAME

    try:
        text = fs.read_text(journal_path)
    except (FsError, ValueError) as exc:
        # Cannot even determine whether this run is one Marshal started --
        # the only safe reading of "inert on a run it did not start" is to
        # STAY inert rather than assume ownership this read cannot prove.
        #
        # `ValueError` alongside `FsError` (review finding): `LocalFs.
        # read_text` translates only `(OSError, UnicodeDecodeError)`, but an
        # embedded NUL byte in a path makes `Path.read_text` raise a PLAIN
        # `ValueError` -- the same CPython split this story already guards at
        # `spawn_detached`'s `open()`, at `run()`'s `subprocess.run`, and in
        # both `observer_mux` methods. Unreachable through `main()` today
        # (`execve` argv cannot carry a NUL), but this is the FIRST call
        # `run_supervisor` makes, and it is a public function a future
        # non-argv entry point can reach directly.
        print(f"supervisor: cannot read journal {journal_path}: {exc}", file=sys.stderr)
        return 0

    lines = text.split("\n") if text is not None else []
    # Sidecar-referenced payloads must be resolvable or `fold` quarantines
    # the whole line -- including a `run-launch` intent whose unbounded
    # `preview` payload crossed the inline threshold (review finding; see
    # this module's own docstring for why the previous "always small enough
    # to inline" rationale was false and what it cost). A blob this read
    # cannot get hold of maps to `None`, which `fold` treats exactly as it
    # already treats an absent one.
    sidecars: dict[str, str | None] = {}
    for ref in _sidecar_refs(lines):
        try:
            sidecars[ref] = fs.read_text(run_dir / ref)
        except (FsError, ValueError):
            sidecars[ref] = None
    fold_result = fold(lines, sidecars=sidecars)
    # Widened to accept EITHER phase (review finding, both reviewers):
    # checking ONLY the OUTCOME entry meant that when cli/spin.py's own
    # outcome-journal append itself fails (MRS-SPIN-006 -- a live harness
    # process already exists, but its outcome never made it to disk), this
    # check found nothing and concluded "not started by Marshal", exiting
    # silently inert on a run Marshal genuinely DID start -- a live,
    # unsupervised harness process with no signal anywhere that supervision
    # was lost. AD-6's write-before-act guarantees the INTENT entry lands
    # BEFORE any spawn is even attempted, independent of whatever happens to
    # the LATER outcome write, so an intent entry alone already proves this
    # run was Marshal-started.
    started_by_marshal = any(
        entry.phase in (Phase.INTENT, Phase.OUTCOME) and entry.run_id == run_id
        for entry in fold_result.by_kind(_LAUNCH_KIND)
    )
    if not started_by_marshal:
        # The AC's own "inert on a run it did not start" -- no JOURNAL write
        # at all, not even a failed-attempt record: there is nothing this
        # process may legitimately claim happened against a run it did not
        # launch.
        #
        # A diagnostic on this process's OWN stderr, though, is not a
        # journal write and costs nothing (review finding): this exit used
        # to be completely silent, so an operator holding a
        # `supervisor.log` could not tell the legitimate "not my run" case
        # apart from the pathological one where the run-launch line IS
        # present but `fold` could not evaluate it (a torn/truncated append,
        # a stray non-JSON byte) -- which quarantines the line, empties
        # `by_kind`, and silently strands a genuinely Marshal-started run
        # with no supervision. The two other inert paths here already print;
        # this one now does too, and names the quarantine count so the two
        # causes are distinguishable at a glance. (Making a quarantined
        # run-launch line itself RECOVERABLE is the separately-logged
        # deferred item -- this only makes it visible.)
        quarantined = len(fold_result.quarantined)
        if quarantined:
            print(
                f"supervisor: no run-launch entry for run {run_id} in "
                f"{journal_path}, but {quarantined} journal line(s) were "
                "unevaluable -- staying inert, though this run's ownership "
                "could not be proven either way",
                file=sys.stderr,
            )
        else:
            print(
                f"supervisor: no run-launch entry for run {run_id} in "
                f"{journal_path} -- not a run Marshal started, staying inert",
                file=sys.stderr,
            )
        return 0

    harness_run_id = _resolve_harness_run_id(fold_result, run_id)

    writer_id = f"supervisor-{os.getpid()}"
    pid = os.getpid()
    counter = 0

    def _write_entry(
        kind: str,
        phase: Phase,
        payload: Mapping[str, object],
        *,
        intent_id: JournalEntryId | None = None,
        fsync: bool,
    ) -> JournalEntryId:
        nonlocal counter
        entry_id = JournalEntryId(writer_id, counter)
        entry = build_entry(
            id=entry_id,
            ts=_format_entry_ts(clock.now()),
            run_id=run_id,
            kind=kind,
            phase=phase,
            intent_id=intent_id,
            payload=payload,
        )
        counter += 1
        prepared = prepare_for_write(entry)
        if prepared.sidecar_relative_path is not None:
            fs.write_text_atomic(
                run_dir / prepared.sidecar_relative_path, prepared.sidecar_content
            )
        fs.append_line(journal_path, prepared.line, fsync=fsync)
        return entry_id

    def _append(kind: str, payload: Mapping[str, object]) -> None:
        _write_entry(kind, Phase.OBSERVATION, payload, fsync=False)

    def _append_intent(kind: str, payload: Mapping[str, object]) -> JournalEntryId:
        return _write_entry(kind, Phase.INTENT, payload, fsync=True)

    def _append_outcome(
        kind: str, intent_id: JournalEntryId, payload: Mapping[str, object]
    ) -> None:
        _write_entry(kind, Phase.OUTCOME, payload, intent_id=intent_id, fsync=False)

    try:
        _append("supervisor-attach", {"pid": pid, "watched_pid": watched_pid})

        # --- Story 3.5: resolve the ladder's real session/log target, or --
        # journal once that it cannot act at all for this run.
        session_name: str | None = None
        harness_log_path: Path | None = None
        if harness_run_id is not None:
            # bmad_loop's own fixed formula (confirmed live against the
            # installed 0.9.0 runs.py::session_name) -- keyed by the
            # HARNESS's own self-minted run id, never Marshal's own run_id.
            session_name = f"bmad-loop-{harness_run_id}"
            harness_log_path = run_dir / _HARNESS_LOG_FILENAME
        else:
            unavailable_finding = Finding(
                code="MRS-SUPV-003",
                severity=Severity.WARN,
                message=(
                    f"run {run_id}'s harness_run_id is unavailable -- the "
                    "idle ladder cannot act for this run; continuing "
                    "heartbeat-only supervision"
                ),
            )
            _append(
                _HARNESS_RUN_ID_UNAVAILABLE_KIND,
                {"finding": unavailable_finding.to_json_dict()},
            )

        threshold_s = float(idle_threshold_minutes) * 60.0
        samples: list[Sample] = []
        last_acted_rung = LadderRung.NONE
        deferred = False
        # The `supervisor-detach` reason this loop will carry when it ends,
        # or `None` for the ordinary "the watched process exited" case
        # (review finding). Two DIFFERENT conditions used to share the single
        # `deferred` flag and therefore the single `"idle-deferred"` reason:
        # the terminal `defer` rung, and a `stop-and-retry` whose `resume()`
        # failed after its `stop()` had already succeeded. The second is not
        # a deferral -- no `idle-defer` intent/outcome pair exists for it --
        # so a consumer counting deferrals by entry kind saw zero while one
        # reading detach reasons saw one, and the run was labelled with a
        # reason class (FR-16's own unit) that misdescribes what happened.
        detach_reason: str | None = None
        # Set the FIRST (and only) time a stop-and-retry fully succeeds
        # (``stop()`` AND ``resume()`` both), and NEVER reset afterwards --
        # unlike `samples`/`last_acted_rung`, which restart a fresh idle
        # window for the new pid (review finding, bounded-retry ladder):
        # without this, a persistently-wedged resumed process gets another
        # full clean idle window every tick forever, and the ladder can
        # cycle nudge -> stop-and-retry -> reset indefinitely, never reaching
        # the terminal `defer` rung. Checked below, right after computing
        # each tick's rung: any FURTHER idle recurrence once this is `True`
        # skips straight to `defer`, guaranteeing at most one retry cycle.
        already_retried = False

        # `watched_alive` is carried across iterations rather than
        # re-derived from a second `is_alive` call at the top of the loop
        # (review finding, Story 3.4): the PREVIOUS shape checked is_alive()
        # BEFORE sleeping, to decide whether to enter a tick at all, then
        # unconditionally wrote `watched_alive: True` into the heartbeat
        # that followed -- a value that could ONLY ever be True (the loop
        # body cannot run otherwise) and that was already up to
        # `_TICK_SECONDS` stale relative to `sampled_at` by the time it was
        # written. This shape instead takes exactly ONE fresh reading per
        # tick, immediately before sampling `moment` -- the SAME reading
        # both fills the heartbeat's own `watched_alive` field (honest and
        # contemporaneous, never a tautology) and decides whether another
        # tick follows, so a tick that finds the watched process just died
        # still journals ONE truthful `watched_alive: False` heartbeat
        # before the final `supervisor-detach`, rather than a silent jump
        # straight from a string of `True` heartbeats to detach.
        watched_alive = process.is_alive(watched_pid)
        while watched_alive and not deferred:
            sleep(_TICK_SECONDS)
            moment = clock.now()
            watched_alive = process.is_alive(watched_pid)

            # `watched_alive` gates the whole block (review finding): this
            # value is THIS tick's own fresh reading, so if the watched
            # process exited naturally in the very tick an idle threshold
            # also crosses, the ladder must not fire against a process that
            # is already gone -- a genuinely successful completion must
            # never be misreported as an `idle-defer` outcome. The ordinary
            # heartbeat below still appends unconditionally either way.
            if watched_alive and session_name is not None and harness_log_path is not None:
                # Sampled against the REAL session/log target (Story 3.5,
                # closing the two placeholder gaps this module's own
                # docstring names) -- feeds the pure `evaluate_idle` decision
                # (AD-20): no port, no clock call, no I/O inside that
                # function itself.
                pane_content = observer.pane_content(session_name)
                log_mtime = observer.mtime(harness_log_path)
                samples.append(
                    Sample(moment=moment, pane_content=pane_content, log_mtime=log_mtime)
                )
                # Bound the history (review finding): `evaluate_idle` needs
                # only the most recent CHANGE point and the latest sample, so
                # once this tick observed a change, everything before the
                # previous sample is dead weight. Without this the list grows
                # one pane capture per tick for the whole life of the run --
                # unbounded memory in a sidecar designed to outlive multi-day
                # runs, plus an O(n) rescan every 60s. Dropping only on a
                # CHANGE keeps the semantics identical: the retained pair
                # still pins the same reference moment `idle_since` would
                # have found in the full history.
                if len(samples) > 2 and (
                    samples[-1].pane_content != samples[-2].pane_content
                    or samples[-1].log_mtime != samples[-2].log_mtime
                ):
                    del samples[:-2]

                if all(
                    sample.pane_content is None and sample.log_mtime is None
                    for sample in samples
                ):
                    # UNOBSERVABLE is not IDLE (review finding). `None !=
                    # None` is `False`, so an all-`None` history never
                    # re-arms and reads as maximal idleness -- and since
                    # `defer` now hard-stops the run rather than merely
                    # detaching, that turns a broken observation channel
                    # (tmux missing from this detached sidecar's PATH, the
                    # session torn down, `harness.log` absent) into a killed
                    # HEALTHY run. The ladder must only act on evidence it
                    # actually has; a run it cannot see at all gets
                    # heartbeat-only supervision, exactly like one whose
                    # `harness_run_id` never resolved.
                    rung = LadderRung.NONE
                else:
                    rung = evaluate_idle(samples, threshold_s=threshold_s)

                # One rung per tick, never a jump (review finding): the
                # ladder is a FIXED 3-rung sequence (this story's own Never
                # clause), but `evaluate_idle` floor-divides, so any
                # threshold shorter than twice `_TICK_SECONDS` lets a single
                # tick land two or three rungs higher than the last one
                # acted on -- `idle_threshold_minutes = 0.25` reaches `DEFER`
                # on the second sample and hard-stops a healthy run without
                # ever nudging it. Nothing validates the threshold against
                # the tick (and `core/policy.py`'s validator explicitly
                # admits sub-minute values), so the sequence is kept intact
                # here instead of rejecting the small thresholds.
                if rung_index(rung) > rung_index(last_acted_rung) + 1:
                    rung = rung_at(rung_index(last_acted_rung) + 1)

                if already_retried and rung_index(rung) >= rung_index(
                    LadderRung.STOP_AND_RETRY
                ):
                    # Bounded-retry gate (review finding): one retry cycle
                    # already happened for this run and is never undone, so
                    # a further idle recurrence on the new pid's window can
                    # never earn a SECOND stop-and-retry -- it escalates
                    # straight to the terminal rung. `nudge` is deliberately
                    # left reachable (this gate used to swallow it too,
                    # collapsing the post-retry ladder to NONE -> DEFER):
                    # the first response to a resumed run going quiet should
                    # still be the harmless one, not an immediate hard stop
                    # of what may simply be a long build or test.
                    rung = LadderRung.DEFER

                if rung_index(rung) > rung_index(last_acted_rung):
                    if rung is LadderRung.NUDGE:
                        intent_id = _append_intent(_NUDGE_KIND, {"session": session_name})
                        sent = observer.send_text(session_name, _NUDGE_TEXT)
                        outcome_payload: dict[str, object] = {"sent": sent}
                        if not sent:
                            # The ladder still advances its own bookkeeping
                            # below (this story's own I/O matrix) -- a
                            # failed nudge is not retried every tick.
                            nudge_finding = Finding(
                                code="MRS-SUPV-001",
                                severity=Severity.WARN,
                                message=(
                                    f"could not deliver a nudge to session "
                                    f"{session_name!r} -- no window resolved "
                                    "or delivery failed"
                                ),
                            )
                            outcome_payload["finding"] = nudge_finding.to_json_dict()
                        else:
                            # The nudge's own echo must not re-arm the very
                            # window it was escalating from (review finding,
                            # and the defect that made this ladder unable to
                            # reach `stop-and-retry` at all). `send_text`
                            # types into the SAME pane `pane_content`
                            # samples, so the next tick's capture differs
                            # from this one's, `evaluate_idle` reads that as
                            # fresh output, the rung falls back to `NONE`,
                            # and the run cycles nudge -> re-arm -> nudge
                            # forever while staying wedged. "Fresh output"
                            # means the SESSION's output, never this
                            # supervisor's own.
                            #
                            # Fixed by collapsing the history onto the
                            # post-nudge pane text while PRESERVING the idle
                            # anchor `idle_since` had already established:
                            # the echoed text becomes the baseline every
                            # later sample is compared against (so it counts
                            # as no change), and elapsed idle time keeps
                            # accruing from where it genuinely started, so
                            # one more full threshold reaches
                            # `stop-and-retry`. Genuine agent output after
                            # the nudge still differs from that baseline and
                            # still re-arms, exactly as before. A `None`
                            # re-capture (the pane became unobservable in the
                            # same instant) degrades to the previous
                            # behaviour rather than inventing a baseline.
                            anchor = idle_since(samples) or moment
                            samples[:] = [
                                Sample(
                                    moment=anchor,
                                    pane_content=observer.pane_content(session_name),
                                    log_mtime=log_mtime,
                                )
                            ]
                        _append_outcome(_NUDGE_KIND, intent_id, outcome_payload)
                    elif rung is LadderRung.STOP_AND_RETRY:
                        intent_id = _append_intent(
                            _STOP_AND_RETRY_KIND,
                            {"harness_run_id": harness_run_id, "old_pid": watched_pid},
                        )
                        try:
                            stopped = harness.stop(home, harness_run_id)
                        except HarnessError as exc:
                            # `stop()` itself could not even be run (review
                            # finding: distinct from a `resume()` failure
                            # below) -- the tick loop continues watching the
                            # (possibly still-wedged) ORIGINAL pid rather
                            # than crashing (this story's own I/O matrix) --
                            # neither `watched_pid` nor the sample history
                            # changes, so the ladder naturally re-escalates
                            # to `defer` once elapsed time crosses the third
                            # threshold.
                            retry_finding = Finding(
                                code="MRS-SUPV-002",
                                severity=Severity.WARN,
                                message=(
                                    "stop-and-retry failed for harness run "
                                    f"{harness_run_id!r}: {exc}"
                                ),
                            )
                            _append_outcome(
                                _STOP_AND_RETRY_KIND,
                                intent_id,
                                {
                                    "old_pid": watched_pid,
                                    "finding": retry_finding.to_json_dict(),
                                },
                            )
                        else:
                            if not stopped:
                                # `stop()`'s own documented `False`: the run
                                # was not stopped. `resume()` must never be
                                # called after it -- doing so could relaunch
                                # a run that already completed.
                                #
                                # Recorded as `stopped: false` and NOT as
                                # `already_finished: true` (review finding):
                                # the port documents `False` as "any other
                                # determinable outcome", of which "already
                                # finished" is only ONE example -- a
                                # rejected run id, a run owned by another
                                # host, or any other non-launch failure
                                # reports identically. Writing the
                                # already-finished reading into an
                                # append-only EVIDENCE journal asserted a
                                # completion this process never observed,
                                # and directly contradicted its OWN fresh
                                # `is_alive` reading from the top of this
                                # same tick, which is what let the ladder
                                # run at all. The WARN says what is actually
                                # known: the wedged run was not stopped, and
                                # no retry was attempted.
                                not_stopped_finding = Finding(
                                    code="MRS-SUPV-002",
                                    severity=Severity.WARN,
                                    message=(
                                        "stop-and-retry: bmad-loop reported "
                                        f"harness run {harness_run_id!r} was "
                                        "not stopped, so no resume was "
                                        "attempted"
                                    ),
                                )
                                _append_outcome(
                                    _STOP_AND_RETRY_KIND,
                                    intent_id,
                                    {
                                        "old_pid": watched_pid,
                                        "stopped": False,
                                        "finding": not_stopped_finding.to_json_dict(),
                                    },
                                )
                            else:
                                try:
                                    new_pid = harness.resume(
                                        home, harness_run_id, log_path=harness_log_path
                                    )
                                except HarnessError as exc:
                                    # `stop()` succeeded -- the original pid
                                    # is CONFIRMED dead, not "possibly still
                                    # wedged" -- so a `resume()` failure
                                    # here is distinct from the
                                    # `stop()`-failed branch above (review
                                    # finding): falling through would let
                                    # the NEXT tick's ordinary `is_alive`
                                    # reading (naturally `False`) exit the
                                    # loop via the routine
                                    # "watched-process-exited" detach,
                                    # silently masking a failed recovery as
                                    # an ordinary completion. Treated as
                                    # unrecoverable instead: `deferred` ends
                                    # the loop the same way reaching
                                    # `defer` itself would.
                                    resume_finding = Finding(
                                        code="MRS-SUPV-002",
                                        severity=Severity.WARN,
                                        message=(
                                            "stop-and-retry: stop succeeded "
                                            "but resume failed for harness "
                                            f"run {harness_run_id!r}: {exc}"
                                        ),
                                    )
                                    _append_outcome(
                                        _STOP_AND_RETRY_KIND,
                                        intent_id,
                                        {
                                            "old_pid": watched_pid,
                                            "finding": resume_finding.to_json_dict(),
                                        },
                                    )
                                    deferred = True
                                    # NOT `"idle-deferred"` (review
                                    # finding): the ladder never reached its
                                    # `defer` rung, and no `idle-defer`
                                    # intent/outcome pair exists to back
                                    # that claim up. This is a failed
                                    # recovery, a materially different
                                    # reason class from an exhausted idle
                                    # ladder.
                                    detach_reason = "idle-retry-failed"
                                else:
                                    _append_outcome(
                                        _STOP_AND_RETRY_KIND,
                                        intent_id,
                                        {"old_pid": watched_pid, "new_pid": new_pid},
                                    )
                                    # A successful retry starts its own
                                    # fresh idle window (this story's own
                                    # Always bullet): the new engine
                                    # attempt gets a clean sample history
                                    # and the ladder resets to its resting
                                    # position. `already_retried` is set
                                    # here, and ONLY here, never reset --
                                    # the ladder's own bounded-retry gate
                                    # (review finding): a further idle
                                    # recurrence on this fresh window
                                    # escalates straight to `defer` instead
                                    # of repeating this branch.
                                    watched_pid = new_pid
                                    samples.clear()
                                    rung = LadderRung.NONE
                                    already_retried = True
                                    # Stale `watched_alive` (review
                                    # finding): this tick's own heartbeat
                                    # append below still runs AFTER this
                                    # branch and would otherwise carry the
                                    # OLD pid's reading taken at the top of
                                    # the tick -- recompute against the NEW
                                    # pid so the heartbeat this tick writes
                                    # is honest.
                                    watched_alive = process.is_alive(watched_pid)
                    elif rung is LadderRung.DEFER:
                        intent_id = _append_intent(_DEFER_KIND, {"watched_pid": watched_pid})
                        # Best-effort (review finding): a failed stop must
                        # never block the defer outcome from being
                        # journaled, nor keep this loop running against a
                        # process it has already decided to abandon --
                        # `defer` is terminal either way, whether or not the
                        # stop call itself succeeded.
                        defer_payload: dict[str, object] = {"watched_pid": watched_pid}
                        try:
                            stopped = harness.stop(home, harness_run_id)
                        except HarnessError as exc:
                            stopped = False
                            defer_detail = f"{harness_run_id!r}: {exc}"
                        else:
                            defer_detail = (
                                f"bmad-loop reported harness run "
                                f"{harness_run_id!r} was not stopped"
                            )
                        defer_payload["stopped"] = stopped
                        if not stopped:
                            # A failed stop at the TERMINAL rung is the worst
                            # case this whole story exists to prevent, and it
                            # used to be journaled as a bare `stopped: false`
                            # with no registered finding at all (review
                            # finding) -- unlike the identical call one
                            # branch up, which registers MRS-SUPV-002. The
                            # supervisor is about to exit; if the stop did
                            # not take, the wedged run keeps burning tokens
                            # with nobody watching it and nothing above WARN
                            # tier anywhere saying so.
                            defer_finding = Finding(
                                code="MRS-SUPV-002",
                                severity=Severity.WARN,
                                message=(
                                    "defer: could not stop harness run "
                                    f"{defer_detail} -- the run may still be "
                                    "running, now unsupervised"
                                ),
                            )
                            defer_payload["finding"] = defer_finding.to_json_dict()
                        _append_outcome(_DEFER_KIND, intent_id, defer_payload)
                        deferred = True
                        detach_reason = "idle-deferred"
                # Synced regardless of whether an action fired above: this
                # is what makes "fresh output re-arms the window" work with
                # no special-cased reset -- a sample whose pane/mtime
                # changed makes `evaluate_idle` itself return `NONE` again,
                # and mirroring that back into this bookkeeping variable is
                # what lets a LATER full threshold re-escalate from scratch.
                last_acted_rung = rung

            _append(
                "supervisor-heartbeat",
                {
                    "pid": pid,
                    "watched_alive": watched_alive,
                    "sampled_at": _format_entry_ts(moment),
                },
            )

        _append(
            "supervisor-detach",
            {"pid": pid, "reason": detach_reason or "watched-process-exited"},
        )
    except (FsError, ValueError) as exc:
        # AD-30's own journal is unwritable -- looping forever against it
        # would spin this process indefinitely with zero further signal.
        # Exit non-zero instead: a dead supervisor with no further
        # heartbeats, alongside a watched pid that is (or later becomes)
        # itself dead, is the later-detectable condition AD-9 promises
        # (surfacing it via `status` is a later epic's own scope).
        #
        # `ValueError` alongside `FsError` (review finding): the READ above
        # was widened for exactly this CPython split one pass earlier, and
        # the WRITE side -- the one that runs every 60s for this process's
        # whole life -- was left narrow. `LocalFs.append_line` and
        # `LocalFs.write_text_atomic` both translate only `OSError`, and
        # `fs_local.py`'s own `write_redacted_atomic` docstring records a
        # bare `ValueError` from `_tmp_sibling` escaping that very clause.
        # An uncaught one here kills the sidecar with a raw traceback AFTER
        # `supervisor-attach` is journaled -- the dangling attach with no
        # matching detach AD-9 says must never happen.
        print(f"supervisor: cannot append to journal {journal_path}: {exc}", file=sys.stderr)
        return 1

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Parse ``sys.argv`` (or an injected ``argv`` for testing) into
    ``run_supervisor``'s six positional arguments and relay its exit code.
    This is the ONLY place this module reads its own command line -- AD-9's
    "reads argv once at start and touches no other externally-writable
    input for its own control flow" is literal here: no further read of
    ``sys.argv``, no ``input()``, no ``sys.stdin`` read, anywhere in this
    package."""
    # A bare `str` satisfies `Sequence[str]` and shreds one character per
    # positional argument (review finding, verified: `main("ab142")` used to
    # return 0 having dispatched `run_supervisor(Path('a'), 'b', '1', 4,
    # Path('2'))` -- a RELATIVE home and a 1-char slug that both pass the
    # gates below -- with no usage error at all), and a non-`str` element
    # reached `"/" in run_id` as a raw `TypeError` past the arity gate.
    # `core/journal.py::fold` and `core/identity.py::resolve_feed` each
    # carry an explicit, documented guard for this same footgun; this
    # module's own public entry point did not.
    if isinstance(argv, (str, bytes, bytearray)):
        print(
            f"supervisor: argv must be a sequence of strings, got {type(argv).__name__}",
            file=sys.stderr,
        )
        return 1
    args = list(sys.argv[1:]) if argv is None else list(argv)
    if len(args) != 6 or not all(isinstance(arg, str) for arg in args):
        print(
            "usage: python -m pyforge.marshal.supervisor <home> <slug> "
            "<run_id> <watched_pid> <log_path> <idle_threshold_minutes>",
            file=sys.stderr,
        )
        return 1
    (
        home,
        slug,
        run_id,
        watched_pid_text,
        log_path_text,
        idle_threshold_minutes_text,
    ) = args
    # `home` is the ROOT of the very path `slug` and `run_id` are guarded as
    # segments of, and was the one argv element validated nowhere (review
    # finding). A relative value resolves the journal against this process's
    # own CWD -- which `spawn_detached` sets to the loop home, so the read
    # silently lands somewhere else entirely and this sidecar exits inert on
    # a run it should have supervised. `cli/init.py::_loop_home_root`
    # anchors its own root to absolute for the identical reason ("left
    # relative, the two writers land in DIFFERENT directories"); this second
    # entry point re-derives the same paths, so it refuses rather than
    # re-anchors -- a relative home here means the caller is malformed, not
    # that a default needs filling in.
    if not Path(home).is_absolute():
        print(f"supervisor: home must be an absolute path, got {home!r}", file=sys.stderr)
        return 1
    # `slug` and `run_id` are BOTH path components of the journal this
    # process reads AND appends to (`_run_dir`), so an unvalidated value
    # composes a path outside the run directory -- `slug="../.."`, or a
    # `run_id` carrying a separator -- and `FsPort.append_line` opens
    # O_CREAT. `cli/spin.py` refuses a malformed slug via this same
    # `core.policy._is_valid_project_slug` before ANY filesystem touch
    # (`core/journal.py` applies it to run-id minting too); this second
    # entry point re-derives the identical paths, so it needs the identical
    # gate (review finding -- `main()` guarded `watched_pid` for exactly
    # this "malformed direct invocation" reachability class while leaving
    # the two arguments that actually become path segments open). Importing
    # `core.policy` is allowed here: this story's new AD-9 contract forbids
    # `supervisor` -> `cli`, never `supervisor` -> `core`.
    if not policy._is_valid_project_slug(slug):
        print(f"supervisor: invalid project slug {slug!r}", file=sys.stderr)
        return 1
    if not run_id or "/" in run_id or "\\" in run_id or run_id in (".", ".."):
        print(f"supervisor: invalid run id {run_id!r}", file=sys.stderr)
        return 1
    try:
        watched_pid = int(watched_pid_text)
    except ValueError:
        print(f"supervisor: invalid watched pid {watched_pid_text!r}", file=sys.stderr)
        return 1
    if watched_pid <= 0:
        # POSIX's `kill()` gives 0 and negative pids special, non-"single
        # process" meanings (the caller's own process group, or a named
        # process group) -- review finding: `os.kill(watched_pid, 0)` inside
        # `is_alive` would silently probe one of THOSE instead of raising or
        # returning False, so a corrupted/malformed invocation could make
        # this sidecar believe an unintended target is "alive" forever
        # rather than failing cleanly. `cli/spin.py`'s own caller always
        # passes a real, positive `Popen.pid`, so this can only trigger via
        # a malformed direct invocation -- guarded here regardless, the same
        # "raise/refuse rather than silently misinterpret" discipline every
        # other boundary in this package already applies.
        print(f"supervisor: watched pid must be positive, got {watched_pid}", file=sys.stderr)
        return 1
    if watched_pid > _MAX_PROBEABLE_PID:
        # The upper half of the same guard (review finding). `is_alive` is
        # deliberately two-valued and answers the CONSERVATIVE `False` for a
        # pid it cannot even probe -- an `os.kill` `OverflowError` above C
        # `INT_MAX` reads identically to a genuine ESRCH. That is right for
        # that port's own contract, but this module then journals
        # `supervisor-detach` with `reason: "watched-process-exited"` -- a
        # definitive claim about an exit it never observed, written into an
        # append-only EVIDENCE journal. (An earlier pass rejected a
        # hardcoded `watched_alive: true` on exactly this ground: a field
        # that can only ever carry one value is not an observation.) This
        # story's own Always bullet enumerates exactly TWO detach reasons
        # (Story 3.5 adds `"idle-deferred"` alongside the original
        # `"watched-process-exited"`), so the honest fix is at the boundary
        # rather than a third reason code: refuse a pid this process could
        # never probe, the same "raise/refuse rather than silently
        # misinterpret" discipline the non-positive guard above already
        # applies.
        print(
            f"supervisor: watched pid {watched_pid} is not probeable "
            f"(above {_MAX_PROBEABLE_PID})",
            file=sys.stderr,
        )
        return 1
    try:
        idle_threshold_minutes = float(idle_threshold_minutes_text)
    except ValueError:
        print(
            f"supervisor: invalid idle threshold minutes "
            f"{idle_threshold_minutes_text!r}",
            file=sys.stderr,
        )
        return 1
    # `not (x > 0)` plus an explicit finiteness check, never a bare `<= 0`
    # (review finding -- the exact footgun `core/supervise.py`'s own guard
    # documents, repeated here). IEEE 754 makes EVERY comparison against
    # `float('nan')` false, so `<= 0` passed a NaN threshold straight
    # through; `evaluate_idle` then raised `ValueError` on the first ladder
    # tick, which this module's own journal-write handler catches and
    # reports as "cannot append to journal" -- blaming the journal for an
    # argv defect and leaving a `supervisor-attach` with no matching
    # `supervisor-detach`, the dangling-attach state AD-9 forbids. `inf`
    # passed too, and silently disabled the ladder for the run's whole life
    # (every elapsed/inf floor-divides to rung `NONE`). `core/policy.py`
    # rejects both at the policy layer, but this is a separate public entry
    # point reachable with any argv at all.
    if not (idle_threshold_minutes > 0) or not math.isfinite(idle_threshold_minutes):
        print(
            f"supervisor: idle threshold minutes must be a positive finite "
            f"number, got {idle_threshold_minutes}",
            file=sys.stderr,
        )
        return 1
    return run_supervisor(
        Path(home), slug, run_id, watched_pid, Path(log_path_text), idle_threshold_minutes
    )


if __name__ == "__main__":
    raise SystemExit(main())
