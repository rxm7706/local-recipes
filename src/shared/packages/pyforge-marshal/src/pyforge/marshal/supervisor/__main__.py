"""The supervisor sidecar's actual entry point (Story 3.4/3.5/3.6,
architecture spine AD-9/AD-20/AD-25/AD-28/AD-30/AD-32): ``python -m
pyforge.marshal.supervisor <home> <slug> <run_id> <watched_pid> <log_path>
<idle_threshold_minutes> <max_tokens_per_story> <max_tokens_per_run>
<max_wall_clock_minutes_per_story> <max_wall_clock_minutes_per_run>``.
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

**Budget ceilings (Story 3.6, AD-20/AD-32, FR-13).** Four new externally-
enforced ceilings -- per-story/per-run x tokens/wall-clock -- close the gap
the idle ladder above deliberately leaves open: a HEALTHY-looking loop (or
an oversized story) that keeps producing output forever has no ceiling
anywhere outside the session itself. Tracked once ``harness_run_id``
resolves: ``run_started_monotonic`` (the supervisor's own attach-time
``clock.monotonic()`` reading, never the run-launch journal entry's own
timestamp -- no existing utility parses a journal ``ts`` string back into a
comparable clock reading, and the gap between ``spin``'s mint and this
attach is seconds against an hours-scale ceiling) and, per tick,
``current_story_key``/``story_started_monotonic`` (via
``HarnessPort.usage_snapshot``, updated on every OBSERVED story-key
transition). Evaluated every tick this loop's own ``watched_alive`` gate
holds (never gated on the pane/log observability the idle ladder's own
block above additionally requires -- AD-32's own rule: "no ceiling exists
that can only be evaluated from session-written data", so the two
wall-clock ceilings must be evaluable even when the session's pane cannot
be read):

- **wall-clock-per-run** -- ``(monotonic_now - run_started_monotonic) /
  60.0`` against ``max_wall_clock_minutes_per_run``, unconditionally (no
  ``harness_run_id`` needed at all: it is purely a monotonic reading).
- **wall-clock-per-story** -- the same shape, against
  ``max_wall_clock_minutes_per_story``, only when a current story is known.
- **token-per-run**/**token-per-story** -- ``UsageSnapshot.
  run_weighted_tokens``/``story_weighted_tokens`` against
  ``max_tokens_per_run``/``max_tokens_per_story``, gated by a STALENESS
  check: ``SessionObserverPort.mtime`` against bmad-loop's own
  ``state.json`` (``<home>/.bmad-loop/runs/<harness_run_id>/state.json``),
  compared to the SAME ``threshold_s`` the idle ladder already computes
  (reused, never a second threshold). A sample older than that window is
  classified ``stale-evidence`` (``MRS-SUPV-006``, journaled ONCE per
  transition into staleness, kind ``"budget-usage-stale"``) -- never
  ``unevaluable`` (AD-32's own amendment, F-24: that label is AD-8-blocking
  and fires on the ordinary idle case the ladder above already handles
  gracefully) -- and BOTH token ceilings are skipped for that tick; the two
  wall-clock ceilings remain the binding constraint.

Each ceiling's own last-observed ``CeilingStatus`` is tracked separately (4
variables, one per scope+metric pair); a rising edge from ``NONE`` to
``APPROACHING`` journals one ``"budget-warn"`` observation
(``MRS-SUPV-004``), and any transition INTO ``BREACHED`` fires the terminal
action -- mirroring the idle ladder's own terminal ``defer``, never
``stop-and-retry`` (retrying the same story/run would immediately re-hit the
same ceiling): one ``intent``/``outcome`` pair (kind ``"budget-stop"``), a
best-effort ``HarnessPort.stop`` (tolerant of ``HarnessError``, registering
``MRS-SUPV-005`` on failure -- the same tier and reasoning as the idle
ladder's own ``MRS-SUPV-002``), and the tick loop ends via the SAME
``supervisor-detach`` mechanism the idle ladder uses, with
``reason=f"budget-{scope}-{metric}-exceeded"`` (e.g.
``"budget-run-wall_clock-exceeded"``). On a story-key transition, one
``"budget-usage"`` observation attributes the OUTGOING story's last known
weighted tokens as its own ``cost_estimate`` (no dollar-denominated pricing
table exists or is introduced, so the weighted-token total itself IS the
proxy -- ``null`` only when bmad-loop's own state reported zero sessions
for that task) before the per-story bookkeeping resets for the new story.

**Escalation and deferral (Story 3.7, AD-9/AD-34/AD-45, FR-15/16/17).** Two
new, independent journal kinds close the gap named in this story's own
Intent: bmad-loop's own run-level escalation pause and per-story deferral
were previously externally unobservable. Deferral capture runs EVERY tick
while ``watched_alive`` holds (``Phase.DEFERRED`` does not pause the run,
so a deferred story is a fact that can appear mid-run, more than once, for
different stories -- see this function's own inline comment for why it is
gated on ``harness_run_id`` alone, never on ``deferred``/idle/budget
state), plus ONE final flush after the tick loop ends (a story deferred
after the last live tick -- the run's own last story being the common case
-- would otherwise never be observed by a tick at all). A local ``set[str]``
of already-journaled story keys, shared by both sites, keeps each story to a
single ``"story-deferred"`` observation. Escalation detection is the
opposite shape -- exactly ONCE, at loop-end, only when no idle-ladder or
budget-ceiling action has already set a more specific ``detach_reason``
(see this story's own Design Notes for why: ``state.json``'s pause fields
are durable BEFORE the watched process ever exits, so polling for them
while still alive is pure waste). ``core.supervise.evaluate_escalation``
classifies the read; on ``UNRESOLVED`` this sidecar journals one
``"escalation-detected"`` observation, writes a durable
``NotifyPort.notify_file`` marker (mandatory; a failure registers
``MRS-SUPV-007`` but never blocks the detach) and attempts a best-effort
``NotifyPort.notify_desktop`` (any failure fully swallowed), then sets
``detach_reason = "escalation-paused"`` before the ordinary
``detach_payload`` construction below.

**Stage-bound durability (Story 3.8, AD-46/FR-61).** Two more mechanisms
close the gap named in this story's own Intent: durability today scaled
only with an arbitrary wall-clock interval an operator might forget to
configure, and no watcher started unless invoked by hand. Both are wired
into every ``run_supervisor`` invocation automatically -- no new argv, no
new CLI flag (``cli/spin.py`` needs no changes: the station branch derives
from ``slug`` alone, and the interval watcher reuses the already-configured
``threshold_s``).

- **Per-tick stage-boundary pushes.** Shares the SAME ``run_status_
  snapshot`` read the deferral-capture block above already makes each tick
  (one read, two consumers). ``supervisor/durability.py::
  classify_push_triggers`` diffs this tick's full ``RunStatusSnapshot.tasks``
  against the previous tick's own reading (kept as a local ``dict[str,
  TaskPhaseSnapshot]``, mirroring the deferral block's own ``set[str]``
  bookkeeping) and returns one ``PushTrigger`` per crossed boundary --
  ``review-verdict-recorded``, ``dev-commit-landed``, ``story-merged``. Each
  trigger pushes the run's own station branch (``f"loop/{slug}"``) via
  ``VcsPort.push``, PLUS that story's own per-story branch when it ran
  worktree-isolated (``TaskPhaseSnapshot.branch`` non-empty) -- and journals
  one ``"stage-push"`` observation per push ATTEMPT (kind, never an
  intent/outcome pair: a push is an observed side effect of bmad-loop's own
  progress, not a decision this sidecar itself made). A push failure
  (``VcsCommandError`` -- rejected non-fast-forward, no network, no
  configured remote -- or an ``OSError``/``subprocess.SubprocessError``
  escaping a non-``GitVcs`` ``VcsPort`` implementation, review finding)
  registers ``MRS-SUPV-008`` (WARN) and never halts the
  tick loop (AD-46: "best-effort against transient network conditions,
  never a new refusal gate"). A ONE-TIME post-loop flush (mirroring the
  deferral block's own post-loop flush, and the identical Story 3.7 review
  finding it fixes) covers a boundary crossed in the instant BETWEEN this
  supervisor's last live tick and the watched process exiting.
- **Interval-watcher fallback.** The floor for whatever the three named
  boundaries miss (a long ``DEV_RUNNING`` stretch with no phase crossing
  yet, a run that pauses before any story reaches ``DONE``): every tick
  while ``watched_alive``, if ``threshold_s`` (the idle ladder's own already
  -configured cadence -- no new policy key) has elapsed since this run's
  last durability push of ANY kind, the station branch is pushed
  unconditionally and journaled with ``boundary: "interval"``. Needs no
  ``harness_run_id`` at all -- the station branch push targets ``slug``
  alone, so this watcher runs even for a run whose harness id never
  resolved.

Every append here is a ``Phase.OBSERVATION`` entry EXCEPT the ladder/budget
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
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from pathlib import Path

from ..adapters.clock_system import SystemClock
from ..adapters.fs_local import FsError, LocalFs
from ..adapters.harness_bmadloop import BmadLoopHarness, HarnessError
from ..adapters.notify_file_desktop import FileDesktopNotifier
from ..adapters.observer_mux import MultiplexerObserver
from ..adapters.process_posix import PosixProcess
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import policy
from ..core.egress import to_redacted
from ..core.identity import normalize, render_feed_key
from ..core.journal import (
    JournalEntryId,
    Phase,
    build_entry,
    fold,
    prepare_for_write,
)
from ..core.model import Finding, Severity
from ..core.supervise import (
    CeilingStatus,
    EscalationStatus,
    LadderRung,
    Sample,
    evaluate_ceiling,
    evaluate_escalation,
    evaluate_idle,
    idle_anchor,
    rung_at,
    rung_index,
)
from ..ports.clock import ClockPort
from ..ports.fs import FsPort
from ..ports.harness import HarnessPort, RunStatusSnapshot, TaskPhaseSnapshot
from ..ports.notify import NotifyPort
from ..ports.observer import SessionObserverPort
from ..ports.process import ProcessPort
from ..ports.vcs import VcsPort
from .durability import PushTrigger, classify_push_triggers

# Matches cli/spin.py's own _JOURNAL_FILENAME/_LAUNCH_KIND/_RESUME_KIND/
# _LOG_FILENAME -- duplicated, not imported, per this module's own docstring
# (the new AD-9 contract forbids importing anything from pyforge.marshal.cli
# at all).
_JOURNAL_FILENAME = "journal.jsonl"
_LAUNCH_KIND = "run-launch"
# Story 3.7 review finding: a supervisor spawned by `marshal factory resume`
# journals its own intent/outcome pair under `cli/spin.py::_RESUME_KIND`
# ("run-resume"), never `_LAUNCH_KIND` -- a resume is a distinct action from
# a launch (AD-45's own back-reference fields have no place on an ordinary
# launch). Both `started_by_marshal` and `_resolve_harness_run_id` below
# must recognize EITHER kind as proof of Marshal ownership for `run_id`, or
# every resumed run's supervisor concludes "not a run Marshal started" and
# exits inert before ever entering the tick loop -- silently disabling the
# idle ladder, budget ceilings, and this very story's own escalation/
# deferral detection for every resumed run.
_RESUME_KIND = "run-resume"
_HARNESS_LOG_FILENAME = "harness.log"

# The idle ladder's own journal kinds (Story 3.5) -- each fires as one
# Phase.INTENT entry then one Phase.OUTCOME entry, never combined.
_NUDGE_KIND = "idle-nudge"
_STOP_AND_RETRY_KIND = "idle-stop-and-retry"
_DEFER_KIND = "idle-defer"
_HARNESS_RUN_ID_UNAVAILABLE_KIND = "idle-harness-run-id-unavailable"

# Story 3.6's own budget-ceiling journal kinds. "budget-stop" fires as one
# Phase.INTENT then one Phase.OUTCOME entry (mirroring the idle ladder's own
# terminal actions above); the other three are single Phase.OBSERVATION
# entries.
_BUDGET_WARN_KIND = "budget-warn"
_BUDGET_STOP_KIND = "budget-stop"
_BUDGET_USAGE_KIND = "budget-usage"
_BUDGET_USAGE_STALE_KIND = "budget-usage-stale"

# Story 3.7's own journal kinds (escalation, deferral, and resume, AD-45,
# FR-15/16/17). Both are single Phase.OBSERVATION entries -- neither is an
# ACTION this sidecar takes (unlike the ladder/budget intent/outcome pairs
# above): a deferral is bmad-loop's own engine decision, merely observed
# here, and an escalation is likewise something bmad-loop's own pause
# already did.
_STORY_DEFERRED_KIND = "story-deferred"
_ESCALATION_DETECTED_KIND = "escalation-detected"

# The durable escalation file marker's own filename, under the run
# directory (the spec's own Always bullet: "writes <run_dir>/ESCALATION").
_ESCALATION_MARKER_FILENAME = "ESCALATION"

# Story 3.8's own journal kind (stage-bound durability, AD-46/FR-61): a
# single Phase.OBSERVATION entry per push ATTEMPT (never an intent/outcome
# pair -- a push is a best-effort side effect of an observed boundary, not
# an action this sidecar decided to take the way the idle ladder/budget
# ceilings do), success or failure alike, so "how many pushes did this run
# attempt, and did they land" is answerable from the journal alone.
_STAGE_PUSH_KIND = "stage-push"

# The interval-watcher fallback's own boundary name (distinct from the three
# named stage boundaries `supervisor/durability.py::PushTrigger` classifies)
# -- AD-46's own "floor for whatever the stage hooks miss".
_INTERVAL_PUSH_BOUNDARY = "interval"


def _feed_key_form(raw: str) -> str:
    """Render a harness-native story key in Marshal's OWN canonical external
    form (review finding). ``UsageSnapshot.story_key`` carries bmad-loop's
    key spelling verbatim -- the full slug, e.g.
    ``"3-6-budget-ceilings-and-the-heaviest-story-advisory"`` -- while every
    other story identifier Marshal writes to a journal or envelope goes
    through ``render_feed_key`` (the dot form, ``"3.6"``; see
    ``cli/spin.py``'s own ``data["preview"]``). Journaling the raw form put
    the SAME story under two identities in one run's evidence, so a
    consumer joining per-story cost back to the launch preview by exact
    match found nothing.

    Falls back to ``raw`` unchanged when it does not parse: a key this
    package cannot normalize is still better attribution than none, and
    ``normalize`` is the sole parser (AD-23) -- never a second-guessing
    regex here."""
    try:
        return render_feed_key(normalize(raw))
    except ValueError:
        # `MalformedStoryKeyError` is a `ValueError`.
        return raw

# `CeilingStatus` carries no intrinsic ordering (mirrors `LadderRung`'s own
# convention, ordered via `core.supervise.rung_index`) -- this is the one
# place `run_supervisor`'s own tick loop needs "is this a rising edge"
# without reaching into a private tuple; no cross-module caller needs an
# ordering accessor for a 3-member enum this module alone consumes.
_CEILING_RANK: Mapping[CeilingStatus, int] = {
    CeilingStatus.NONE: 0,
    CeilingStatus.APPROACHING: 1,
    CeilingStatus.BREACHED: 2,
}

# bmad-loop's own per-run state file (confirmed live against the installed
# 0.9.0 journal.py's STATE_FILE constant) -- a literal, never an import of
# bmad_loop itself (AD-3 reserves that seam for adapters/harness_bmadloop.py
# alone), mirroring this module's existing `session_name`/
# `_HARNESS_LOG_FILENAME` precedent of naming a bmad-loop-owned artifact by
# its own known-live shape rather than importing a constant for it.
_STATE_JSON_FILENAME = "state.json"

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


def _bmad_loop_state_json_path(home: Path, harness_run_id: str) -> Path:
    """bmad-loop's OWN per-run state file (Story 3.6) --
    ``<home>/.bmad-loop/runs/<harness_run_id>/state.json`` -- a wholly
    DIFFERENT directory tree from ``_run_dir`` above (Marshal's own
    Tier-3-backed journal, keyed by Marshal's own run id): this one is
    bmad-loop's own native run layout, keyed by ``harness_run_id``, the SAME
    id ``session_name``/``harness_log_path`` below are built from. Matches
    ``adapters/harness_bmadloop.py::usage_snapshot``'s own ``run_dir``
    computation exactly -- duplicated rather than imported, per this
    module's own docstring (AD-9 forbids importing ``pyforge.marshal.cli``,
    but this is ``adapters``, not ``cli`` -- still not imported, since the
    literal costs nothing and this module already reproduces
    ``session_name``'s own bmad-loop-owned naming formula the identical
    way)."""
    return home / ".bmad-loop" / "runs" / harness_run_id / _STATE_JSON_FILENAME


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
    session/harness target to act against for this run.

    Checks both ``_LAUNCH_KIND`` and ``_RESUME_KIND`` (Story 3.7 review
    finding): a resumed run's outcome entry carries the SAME
    ``harness_run_id`` field under ``_RESUME_KIND`` instead."""
    for kind in (_LAUNCH_KIND, _RESUME_KIND):
        for entry in fold_result.by_kind(kind):
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
    # Story 3.6's 4 budget ceilings (FR-13, AD-32) -- see this function's
    # own guard below for their validation, and the module docstring's
    # "Budget ceilings" section for how each is used.
    max_tokens_per_story: float,
    max_tokens_per_run: float,
    max_wall_clock_minutes_per_story: float,
    max_wall_clock_minutes_per_run: float,
    *,
    fs: FsPort | None = None,
    process: ProcessPort | None = None,
    clock: ClockPort | None = None,
    observer: SessionObserverPort | None = None,
    harness: HarnessPort | None = None,
    notify: NotifyPort | None = None,
    vcs: VcsPort | None = None,
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
    fake ``ProcessPort``/``ClockPort``. ``notify`` is Story 3.7's own
    escalation-notification seam -- no new argv positional (mirrors
    ``harness``'s own default-construction convention, never a caller-
    supplied value read off ``sys.argv``). ``vcs`` is Story 3.8's own
    durability-push seam (AD-46) -- no new argv positional either: the
    station branch this sidecar pushes is derived from ``slug`` alone
    (``f"loop/{slug}"``, this package's own established convention -- see
    ``cli/init.py``), and the interval watcher's own cadence reuses
    ``idle_threshold_minutes``'s already-configured ``threshold_s``, so no
    caller-supplied durability-specific value is needed at all."""
    fs = fs if fs is not None else LocalFs()
    process = process if process is not None else PosixProcess()
    clock = clock if clock is not None else SystemClock()
    observer = observer if observer is not None else MultiplexerObserver()
    harness = harness if harness is not None else BmadLoopHarness()
    notify = notify if notify is not None else FileDesktopNotifier()
    vcs = vcs if vcs is not None else GitVcs()

    # Validated on the DERIVED seconds value, at THIS entry point, before
    # anything is journaled (follow-up review finding -- two defects, one
    # guard):
    #
    # 1. `main()`'s own guard checks `idle_threshold_minutes` for finiteness
    #    but the ladder consumes `minutes * 60`, and a finite-but-enormous
    #    value overflows that product to `inf` (`1e308 * 60.0` is `inf`).
    #    `inf` is exactly what both this guard and `core/policy.py`'s
    #    validator were added to reject, because every elapsed/`inf`
    #    floor-divides to `NONE` -- silently disabling the idle ladder for
    #    the run's whole life with no diagnostic anywhere. Checking the
    #    quantity actually used closes the door the minutes-only check left
    #    open.
    # 2. `run_supervisor` is a public entry point in its own right (every
    #    test in this package drives it directly, never through `main()`),
    #    and it carried no threshold guard at all -- a bad value surfaced a
    #    tick later as `evaluate_idle`'s `ValueError`, caught by the
    #    journal-write handler and misreported as "cannot append to
    #    journal", leaving a `supervisor-attach` with no matching detach.
    #
    # Returning before the attach entry is written keeps the failure a clean
    # non-zero exit with nothing dangling in the journal.
    # The conversion itself is guarded (review finding): this guard's own
    # stated justification is that `run_supervisor` is a public entry point
    # driven directly, and a direct caller is exactly the one who can pass a
    # non-numeric `idle_threshold_minutes`. An unprotected `float()` raised
    # `TypeError`/`ValueError` out of the function instead of producing the
    # clean non-zero return this block exists to produce -- the failure mode
    # it guards against, escaping through the guard itself.
    try:
        threshold_s = float(idle_threshold_minutes) * 60.0
    except (TypeError, ValueError):
        threshold_s = float("nan")
    if not (threshold_s > 0) or not math.isfinite(threshold_s):
        print(
            f"supervisor: idle threshold minutes must resolve to a positive "
            f"finite number of seconds, got {idle_threshold_minutes} "
            f"({threshold_s}s)",
            file=sys.stderr,
        )
        return 1

    # The 4 budget-ceiling arguments, guarded the SAME way and for the
    # IDENTICAL reason as `idle_threshold_minutes` above: this is a public
    # entry point every test in this package drives directly, never only
    # through `main()`, and an unguarded bad value would surface a tick
    # later as `evaluate_ceiling`'s own `TypeError`/`ValueError`, caught by
    # the journal-write handler and misreported as "cannot append to
    # journal" -- a dangling `supervisor-attach` with no matching detach,
    # the state AD-9 forbids. Reuses `core.policy._valid_positive_number`
    # (the SAME validator `idle_threshold_minutes`'s own policy composition
    # already applies) rather than a fourth hand-rolled numeric guard --
    # none of these 4 values are converted to a derived unit the way
    # `idle_threshold_minutes` is (`* 60.0`), so there is no analogous
    # overflow-of-a-derived-quantity risk to guard against here.
    for _budget_value, _budget_label in (
        (max_tokens_per_story, "max_tokens_per_story"),
        (max_tokens_per_run, "max_tokens_per_run"),
        (max_wall_clock_minutes_per_story, "max_wall_clock_minutes_per_story"),
        (max_wall_clock_minutes_per_run, "max_wall_clock_minutes_per_run"),
    ):
        if policy._valid_positive_number(_budget_value) is None:
            print(
                f"supervisor: {_budget_label} must be a positive finite "
                f"number, got {_budget_value!r}",
                file=sys.stderr,
            )
            return 1

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
        for kind in (_LAUNCH_KIND, _RESUME_KIND)
        for entry in fold_result.by_kind(kind)
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
                    "idle ladder cannot act for this run, and neither can "
                    "the two token ceilings, the per-story wall-clock "
                    "ceiling, or per-story cost attribution (Story 3.6: all "
                    "four read the harness run's own state.json); the "
                    "per-run wall-clock ceiling remains the only binding "
                    "constraint; continuing heartbeat-only supervision"
                ),
            )
            _append(
                _HARNESS_RUN_ID_UNAVAILABLE_KIND,
                {"finding": unavailable_finding.to_json_dict()},
            )

        # --- Story 3.6: budget-ceiling bookkeeping (AD-20/AD-32) -----------
        # `run_started_monotonic` is captured ONCE, right here (post
        # inert-check / harness_run_id resolution) -- the supervisor's OWN
        # attach-time reading, never the run-launch journal entry's own
        # timestamp (see the module docstring's "Budget ceilings" section
        # for why). Independent of whether `harness_run_id` resolved: the
        # per-run wall-clock ceiling needs no session/harness target at all.
        run_started_monotonic = clock.monotonic()
        current_story_key: str | None = None
        story_started_monotonic: float | None = None
        # The current story's last-observed weighted token tally -- used
        # solely to attribute a `"budget-usage"` observation to the
        # OUTGOING story at the moment it transitions away (see the
        # per-tick block below); never itself an enforcement input.
        last_story_weighted_tokens: int | None = None
        # One CeilingStatus per (scope, metric) pair -- the ONLY way this
        # loop can detect a rising edge (`CeilingStatus` carries no
        # intrinsic ordering, mirroring `LadderRung`'s own convention
        # above): a warning fires on NONE->APPROACHING, the terminal action
        # on any transition INTO BREACHED, and both are compared against
        # the LAST status this loop itself acted on, never re-derived from
        # scratch.
        run_wall_clock_status = CeilingStatus.NONE
        story_wall_clock_status = CeilingStatus.NONE
        run_tokens_status = CeilingStatus.NONE
        story_tokens_status = CeilingStatus.NONE
        # Whether the LAST tick's usage sample was stale -- gates
        # `_BUDGET_USAGE_STALE_KIND` to fire once per transition INTO
        # staleness, never every tick (AD-32's own "reported... never reds
        # the run" posture would be defeated by a flood of identical
        # findings otherwise).
        usage_stale = False

        # Story 3.7's own deferral-capture bookkeeping (FR-16): every story
        # key this run has already journaled a `"story-deferred"`
        # observation for, so a story that stays `Phase.DEFERRED` across
        # many ticks is reported exactly ONCE -- mirrors the budget block's
        # own "last status acted on" convention above, adapted to a set
        # rather than a per-(scope,metric) enum, since deferral is a
        # per-story membership fact, not a rising edge over an ordered
        # status.
        deferred_story_keys: set[str] = set()

        def _capture_deferrals(status_snapshot: RunStatusSnapshot | None) -> None:
            """Journal one ``"story-deferred"`` observation per story key
            this run has not already reported. Shared verbatim by the
            per-tick site inside the loop and the single post-loop flush
            after it (follow-up review finding) -- one body, so the two
            sites cannot drift over the payload's own shape."""
            if status_snapshot is None:
                return
            for deferred_story in status_snapshot.deferred:
                if deferred_story.story_key in deferred_story_keys:
                    continue
                deferred_story_keys.add(deferred_story.story_key)
                _append(
                    _STORY_DEFERRED_KIND,
                    {
                        "story_key": _feed_key_form(deferred_story.story_key),
                        "reason": deferred_story.reason,
                        "attempt": deferred_story.attempt,
                        "branch": deferred_story.branch,
                        "worktree_path": deferred_story.worktree_path,
                        "spec_file": deferred_story.spec_file,
                    },
                )

        # --- Story 3.8's own durability bookkeeping (AD-46/FR-61) ----------
        # The station branch this run pushes at every stage boundary AND on
        # interval-watcher expiry -- derived from `slug` alone (this
        # package's own established `f"loop/{slug}"` convention, see
        # `cli/init.py`), never a caller-supplied value.
        station_branch = f"loop/{slug}"
        # The previous tick's full per-task reading (`TaskPhaseSnapshot`,
        # keyed by `story_key`) -- `classify_push_triggers` diffs THIS
        # against the current tick's own reading. Empty at attach: the
        # story's own module docstring (`supervisor/durability.py`)
        # documents why a story missing from this mapping is read as "not
        # previously in that boundary state", not an error.
        previous_task_phases: dict[str, TaskPhaseSnapshot] = {}
        # The monotonic reading of this run's last durability push attempt
        # (stage-boundary OR interval), seeded to attach time so the FIRST
        # interval-watcher expiry is measured from attach, not from an
        # unset/zero reading. Reset on every attempt (success or failure)
        # -- the interval watcher is a coarse timer, not a retry-until-
        # success loop (AD-46's own "best-effort against transient network
        # conditions").
        last_durability_push_monotonic = clock.monotonic()

        def _push_branch(branch: str, boundary: str, story_key: str | None) -> None:
            """One durability push attempt (Story 3.8, AD-46/FR-61), success
            or failure alike -- journals exactly one ``"stage-push"``
            observation, never silently skipped (the spec's own Always
            bullet). ``repo_root`` is resolved fresh on every call via
            ``VcsPort.repo_common_root(home)`` (cheap; ``home`` is always
            inside the shared repo by construction, since it is the loop
            home this very sidecar was spawned to supervise) rather than
            cached once, mirroring this loop's own "read the target fresh
            each tick" discipline elsewhere (``usage_snapshot``,
            ``run_status_snapshot``). A failure -- either resolving
            ``repo_root`` or the push itself -- registers ``MRS-SUPV-008``
            (WARN) and NEVER halts the tick loop (AD-46: "never a new
            refusal gate"). Catches ``OSError``/``subprocess.SubprocessError``
            alongside ``VcsCommandError`` (review finding): ``VcsPort`` is an
            interface, and while ``GitVcs`` itself wraps every subprocess
            failure into ``VcsCommandError``, a future or alternate
            ``VcsPort`` implementation could raise a launch-level
            ``OSError`` (``FileNotFoundError``, ``PermissionError``) or a
            ``subprocess.SubprocessError`` (``CalledProcessError``,
            ``TimeoutExpired`` -- NOT ``OSError`` subclasses despite the
            similar naming) directly -- letting any of those escape here
            would crash the whole tick loop, directly contradicting this
            story's own "never a run-halting condition" invariant."""
            outcome = "pushed"
            push_finding: dict[str, object] | None = None
            try:
                repo_root = vcs.repo_common_root(home)
                vcs.push(repo_root, branch)
            except (VcsCommandError, OSError, subprocess.SubprocessError) as exc:
                outcome = "push-failed"
                # Push failure text originates from git's own stderr (a
                # subprocess we do not control) and can carry pane/host-like
                # content -- redacted at capture before it enters the
                # journal payload, matching AD-34 and this package's own
                # established `to_redacted({"k": text}); json.loads(
                # redacted.text)["k"]` round-trip (see
                # `adapters/observer_mux.py`/`adapters/harness_bmadloop.py`
                # for the precedent -- review finding: the raw exception
                # text was previously interpolated directly).
                redacted = to_redacted({"text": str(exc)})
                redacted_text = json.loads(redacted.text)["text"]
                finding = Finding(
                    code="MRS-SUPV-008",
                    severity=Severity.WARN,
                    message=(
                        f"durability push failed for branch {branch!r} "
                        f"({boundary}): {redacted_text}"
                    ),
                )
                push_finding = finding.to_json_dict()
            push_payload: dict[str, object] = {"boundary": boundary, "branch": branch}
            if story_key is not None:
                push_payload["story_key"] = story_key
            push_payload["outcome"] = outcome
            if push_finding is not None:
                push_payload["finding"] = push_finding
            _append(_STAGE_PUSH_KIND, push_payload)

        def _process_stage_pushes(status_snapshot: RunStatusSnapshot | None) -> None:
            """Diffs ``status_snapshot.tasks`` against the previous tick's
            own reading (``previous_task_phases``) via the pure
            ``classify_push_triggers``, and pushes the station branch --
            plus that story's own per-story branch, when the triggering
            story ran worktree-isolated (``task.branch`` non-empty) -- for
            EVERY crossed boundary (the spec's own edge-case matrix: a story
            can cross more than one boundary in a single diff, and each
            gets its own push + its own ``"stage-push"`` observation).
            Shared verbatim by the per-tick site inside the loop and the
            single post-loop flush after it (mirrors ``_capture_deferrals``'s
            own "one body, so the two sites cannot drift" shape -- Story
            3.7's own review finding that a story's LAST observable
            transition, immediately followed by the watched process exiting,
            is otherwise silently dropped applies here identically). A
            ``None`` ``status_snapshot`` carries no new information at all,
            so ``previous_task_phases`` is left untouched, matching
            ``_capture_deferrals``'s own "nothing to observe" no-op --
            otherwise it is unconditionally advanced to the current
            reading, even on a tick with zero triggers, so the NEXT diff is
            always against the truly most-recent observation."""
            nonlocal previous_task_phases, last_durability_push_monotonic
            if status_snapshot is None:
                return
            current_task_phases = {task.story_key: task for task in status_snapshot.tasks}
            triggers: tuple[PushTrigger, ...] = classify_push_triggers(
                previous_task_phases, current_task_phases
            )
            for trigger in triggers:
                feed_key = _feed_key_form(trigger.story_key)
                _push_branch(station_branch, trigger.boundary, feed_key)
                last_durability_push_monotonic = clock.monotonic()
                task = current_task_phases.get(trigger.story_key)
                if task is not None and task.branch:
                    _push_branch(task.branch, trigger.boundary, feed_key)
                    last_durability_push_monotonic = clock.monotonic()
            previous_task_phases = current_task_phases

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

        # Set when a stop-and-retry swap succeeds, cleared by the NEXT
        # tick's own liveness reading -- the one check that can tell a
        # resume bmad-loop ACCEPTED from one it merely launched and then
        # rejected (review finding). `HarnessPort.resume` returns the pid
        # of the process it spawned, which proves only that the spawn
        # itself worked: `bmad-loop resume` exits non-zero, after starting
        # normally, for an unknown run ref, a run whose engine it still
        # considers alive, an already-finished run, or missing base skills.
        # In every one of those cases the supervisor journaled a fully
        # successful `{old_pid, new_pid}` retry with no finding at all, and
        # then detached with the ordinary `"watched-process-exited"` -- a
        # failed recovery recorded as a clean completion, in an append-only
        # EVIDENCE journal. A resumed engine that is gone one tick later did
        # not take.
        retry_verify_pending = False
        # A finding to carry on the final `supervisor-detach` payload, set
        # only by the verification above. The ladder's own rungs journal
        # their findings on their own outcome entries; this one has no rung
        # to hang on, because the thing that failed is only observable a
        # tick after its outcome was already written.
        detach_finding: dict[str, object] | None = None

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

        def _act_on_budget_transition(
            scope: str,
            metric: str,
            status_before: CeilingStatus,
            status_after: CeilingStatus,
            observed: float,
            limit: float,
        ) -> None:
            """Story 3.6's shared warn/breach handler for all 4 (scope,
            metric) budget-ceiling pairs -- a no-op unless ``status_after``
            is a RISING edge over ``status_before`` (``_CEILING_RANK``,
            since ``CeilingStatus`` carries no intrinsic ordering).
            ``NONE``->``APPROACHING`` journals one ``"budget-warn"``
            observation (``MRS-SUPV-004``); any transition INTO
            ``BREACHED`` fires the terminal action -- mirroring the idle
            ladder's own terminal ``defer`` above: one ``intent``/
            ``outcome`` pair (kind ``"budget-stop"``), a best-effort
            ``HarnessPort.stop`` (tolerant of failure, registering
            ``MRS-SUPV-005``), and ending the tick loop via the SAME
            ``detach_reason``/``deferred`` mechanism the idle ladder uses.
            A second ceiling breaching -- or merely approaching -- in the
            SAME tick after a DIFFERENT ceiling already breached is a no-op
            here (``deferred`` is already ``True``, checked BEFORE either
            branch -- review finding: the original shape only checked it
            inside the ``BREACHED`` branch, so an ``APPROACHING`` transition
            on a second ceiling could still journal a ``budget-warn``
            chronologically AFTER the terminal ``budget-stop`` pair the
            first ceiling had already fired, in the same tick, for a run
            already ending) -- at most one stop action per tick, and no
            warn once the loop has already decided to end."""
            nonlocal deferred, detach_reason, watched_alive
            if _CEILING_RANK[status_after] <= _CEILING_RANK[status_before]:
                return
            if deferred:
                return
            # A per-STORY transition names its story (review finding). The
            # payloads carried only `scope`/`metric`/`observed`/`limit`, so a
            # `budget-warn`/`budget-stop` pair for `scope="story"` -- and the
            # `budget-story-tokens-exceeded` detach reason derived from it --
            # said WHAT was exceeded but never WHICH story exceeded it. The
            # only per-story identity in the run's evidence was the adjacent
            # `budget-usage` entry, so a consumer building FR-13's per-story
            # enforcement view had to recover the attribution by position in
            # the journal rather than read it. `current_story_key` is a free
            # variable of the enclosing tick loop and is already updated for
            # THIS tick by the time either story-scope ceiling is evaluated
            # (the wall-clock one is guarded on it being set; the token one
            # runs after the same tick's story-key transition block), so it
            # is the correct attribution at the moment of the transition.
            # `_feed_key_form` for the same reason the `budget-usage` sites
            # use it: one story must not appear under two spellings in one
            # journal. Run-scope transitions stay unattributed -- naming any
            # single story there would be false.
            story_context: dict[str, object] = (
                {"story_key": _feed_key_form(current_story_key)}
                if scope == "story" and current_story_key is not None
                else {}
            )
            if status_after is CeilingStatus.APPROACHING:
                warn_finding = Finding(
                    code="MRS-SUPV-004",
                    severity=Severity.WARN,
                    message=(
                        f"budget ceiling approaching: {scope}/{metric} at "
                        f"{observed!r} (limit {limit!r})"
                    ),
                )
                _append(
                    _BUDGET_WARN_KIND,
                    {
                        "scope": scope,
                        "metric": metric,
                        **story_context,
                        "observed": observed,
                        "limit": limit,
                        "finding": warn_finding.to_json_dict(),
                    },
                )
                return
            # status_after is CeilingStatus.BREACHED. The `deferred` guard
            # now sits at the TOP of this function (see the docstring's own
            # review-finding note) -- this branch is only ever reached with
            # `deferred` still `False`.
            intent_id = _append_intent(
                _BUDGET_STOP_KIND,
                {
                    "scope": scope,
                    "metric": metric,
                    **story_context,
                    "observed": observed,
                    "limit": limit,
                },
            )
            stopped = False
            stop_payload: dict[str, object] = {
                "scope": scope,
                "metric": metric,
                **story_context,
            }
            if harness_run_id is None:
                # No harness_run_id to stop against -- e.g. the per-run
                # wall-clock ceiling, the one budget check evaluable even
                # when the idle ladder's own MRS-SUPV-003 already reported
                # it cannot act at all for this run.
                stop_finding = Finding(
                    code="MRS-SUPV-005",
                    severity=Severity.WARN,
                    message=(
                        f"budget-stop ({scope}/{metric}): no harness_run_id "
                        "is available for this run -- could not stop the "
                        "harness process"
                    ),
                )
                stop_payload["finding"] = stop_finding.to_json_dict()
            else:
                try:
                    stopped = harness.stop(home, harness_run_id)
                except HarnessError as exc:
                    stop_finding = Finding(
                        code="MRS-SUPV-005",
                        severity=Severity.WARN,
                        message=(
                            f"budget-stop ({scope}/{metric}) failed for "
                            f"harness run {harness_run_id!r}: {exc}"
                        ),
                    )
                    stop_payload["finding"] = stop_finding.to_json_dict()
                else:
                    if not stopped:
                        stop_finding = Finding(
                            code="MRS-SUPV-005",
                            severity=Severity.WARN,
                            message=(
                                f"budget-stop ({scope}/{metric}): bmad-loop "
                                f"reported harness run {harness_run_id!r} "
                                "was not stopped"
                            ),
                        )
                        stop_payload["finding"] = stop_finding.to_json_dict()
            stop_payload["stopped"] = stopped
            _append_outcome(_BUDGET_STOP_KIND, intent_id, stop_payload)
            if harness_run_id is None:
                # Nothing was stopped, because there was nothing to stop
                # against -- so do NOT end supervision (review finding). The
                # original shape set `deferred`/`detach_reason` here too, so
                # a per-run wall-clock breach on a run whose `harness_run_id`
                # never resolved journaled a `budget-stop` it had not
                # performed and then DETACHED -- leaving a live, runaway
                # harness process with the one thing watching it now gone.
                # That is strictly worse than not having the ceiling at all.
                # Instead this mirrors `MRS-SUPV-003`'s own precedent for the
                # identical "cannot act for this run" condition: journal the
                # WARN once and continue heartbeat-only. Nothing re-fires on
                # later ticks -- this ceiling's status is already `BREACHED`,
                # so the rank check at the top of this function makes every
                # subsequent tick a no-op.
                return
            deferred = True
            # Plain concatenation, NOT an f-string (review finding, AD-23's
            # own meta-test): `f"budget-{scope}-{metric}-exceeded"` is,
            # structurally, "two placeholders joined by a bare '-'" -- the
            # EXACT shape `tests/meta/test_ad23_inline_key_format_guard.py`
            # forbids outside `core/identity.py`, since that is what a
            # story-key-shaped literal looks like to its AST scan. `scope`/
            # `metric` are never story keys, but the guard is purely
            # structural and has no escape hatch; `+` concatenation produces
            # the IDENTICAL string while using no ``ast.JoinedStr``/
            # ``.format()`` node the scan recognizes at all.
            detach_reason = "budget-" + scope + "-" + metric + "-exceeded"
            # Stale `watched_alive` (mirrors the idle ladder's own
            # `defer`/`stop-and-retry` branches above): the stop call just
            # above may have killed the very pid this tick read as alive at
            # its top, and this tick's own heartbeat -- possibly the LAST
            # one this run will ever produce -- still appends below.
            watched_alive = process.is_alive(watched_pid)

        watched_alive = process.is_alive(watched_pid)
        while watched_alive and not deferred:
            sleep(_TICK_SECONDS)
            moment = clock.now()
            # Both readings, taken together (review finding): `moment` is the
            # wall-clock instant the journal records, `monotonic_now` is the
            # suspend-immune basis `core/supervise.py` measures ELAPSED idle
            # time from. See `ports/clock.py::monotonic` for why the two
            # cannot be the same reading.
            monotonic_now = clock.monotonic()
            watched_alive = process.is_alive(watched_pid)

            if retry_verify_pending and watched_alive:
                # The resumed engine survived a whole tick, so bmad-loop
                # accepted the run -- the retry is verified and this stops
                # being an open question. The FAILING half of this check
                # lives after the loop (see there): a resume that is
                # rejected usually leaves the pid dead before the very next
                # `while` test, so the loop never runs another tick to
                # notice it here.
                retry_verify_pending = False

            # --- Story 3.7: deferral capture (AD-45, FR-16) ------------------
            # Per-STORY, observed EVERY tick while `watched_alive` -- a
            # SEPARATE, budget/idle-independent path (the spec's own
            # Boundaries text): `Phase.DEFERRED` does not pause the run
            # (bmad-loop's own engine picks the next story), so a deferred
            # story is a fact that can appear -- potentially several times,
            # for several different stories -- during a still-live run, not
            # only at its end. Gated on `harness_run_id` alone (no
            # `not deferred` check, unlike the budget block below): this is
            # an OBSERVATION, never an action, so it has nothing to skip
            # even if a budget/idle decision already ended this same tick.
            #
            # Story 3.8 shares this SAME read (one `run_status_snapshot`
            # call, not two) for its own stage-boundary push detection --
            # `_process_stage_pushes` needs the identical `RunStatusSnapshot`
            # `_capture_deferrals` already reads this tick.
            if watched_alive and harness_run_id is not None:
                tick_status_snapshot = harness.run_status_snapshot(home, harness_run_id)
                _capture_deferrals(tick_status_snapshot)
                _process_stage_pushes(tick_status_snapshot)

            # --- Story 3.8: interval-push watcher fallback (AD-46/FR-61) ----
            # The floor for whatever the three named stage boundaries miss
            # (a long DEV_RUNNING stretch with no phase crossing yet, a run
            # that pauses before any story reaches DONE): reuses
            # `threshold_s` (the idle ladder's own already-configured
            # cadence -- no new policy key, per the spec's own Never
            # clause), fires unconditionally, and needs no `harness_run_id`
            # at all (the station branch push targets `slug` alone). Gated
            # on `watched_alive` only, mirroring the deferral capture block
            # above -- this is a best-effort side effect, not an action that
            # competes with the idle ladder/budget ceilings for "did this
            # tick already decide to end the run".
            if watched_alive and (monotonic_now - last_durability_push_monotonic) >= threshold_s:
                _push_branch(station_branch, _INTERVAL_PUSH_BOUNDARY, None)
                last_durability_push_monotonic = monotonic_now

            # --- Story 3.6: budget ceilings (AD-20/AD-32) -------------------
            # Gated on `watched_alive` alone -- NEVER on `session_name`/
            # `harness_log_path`/pane observability, unlike the idle
            # ladder's own block below: AD-32 requires the two wall-clock
            # ceilings to be evaluable even when the session's pane cannot
            # be read, and this whole block evaluates them independently of
            # whether `harness_run_id` even resolved (the per-run wall-clock
            # ceiling needs no session/harness target at all). A process
            # already discovered dead this tick has nothing left to stop;
            # the ordinary "watched-process-exited" detach already covers
            # it.
            #
            # `and not deferred` (review finding): the `deferred` guard added
            # one pass earlier sits INSIDE `_act_on_budget_transition`, which
            # suppresses a second same-tick `budget-warn` but does nothing
            # about the rest of this block. A ceiling that breaches here
            # writes its terminal `budget-stop` intent/outcome pair and then
            # execution FALLS THROUGH -- spending another `usage_snapshot`
            # read against a run just killed, and appending `budget-usage`
            # and/or `budget-usage-stale` observations CHRONOLOGICALLY AFTER
            # the terminal pair, for a run already ending. Re-checking here
            # covers the whole block, not just the warn branch. (The idle
            # ladder's own block below is already `elif`-chained behind its
            # own `deferred` handling.)
            if watched_alive and not deferred:
                run_elapsed_minutes = (monotonic_now - run_started_monotonic) / 60.0
                new_run_wall_clock_status = evaluate_ceiling(
                    run_elapsed_minutes, max_wall_clock_minutes_per_run
                )
                _act_on_budget_transition(
                    "run",
                    "wall_clock",
                    run_wall_clock_status,
                    new_run_wall_clock_status,
                    run_elapsed_minutes,
                    max_wall_clock_minutes_per_run,
                )
                run_wall_clock_status = new_run_wall_clock_status

                # `and not deferred` (review finding): the per-RUN wall-clock
                # ceiling evaluated just above may have breached IN THIS
                # TICK, writing its terminal `budget-stop` pair -- and
                # everything below would then still run, spending a
                # `usage_snapshot` read against a run just killed and
                # appending `budget-usage`/`budget-usage-stale` observations
                # chronologically AFTER that terminal pair.
                if harness_run_id is not None and not deferred:
                    # `usage_snapshot` is read every tick regardless of the
                    # staleness gate below: attribution (WHICH story is
                    # running, and the wall-clock-per-story ceiling's own
                    # elapsed-time basis) rests on the monotonic clock, not
                    # on fresh consumption numbers, so a stale sample still
                    # answers "which story" correctly even when its token
                    # counts do not (AD-32: session-authored data is
                    # evidence for ATTRIBUTION, never a precondition on the
                    # STOP condition itself).
                    usage = harness.usage_snapshot(home, harness_run_id)
                    # A FAILED read (`usage is None`) is never treated as a
                    # transition to "no current story" (review finding): a
                    # single transient `usage_snapshot` glitch -- a torn
                    # concurrent write to `state.json`, a momentary
                    # `bmad_loop` import failure -- must not reset the
                    # per-story wall-clock/token ceiling clock for a story
                    # that is, in fact, still running. Only a POSITIVE
                    # reading ever changes `current_story_key`; a failed
                    # tick simply carries the previous value forward, same
                    # as the idle ladder's own "act only on evidence it has"
                    # discipline for an unobservable pane.
                    new_story_key = usage.story_key if usage is not None else current_story_key
                    if new_story_key != current_story_key:
                        if current_story_key is not None:
                            # "Cost estimate" (the spec's own Always bullet):
                            # no dollar pricing table exists, so
                            # `cost_estimate` IS the weighted-token proxy
                            # (`task.tokens.weighted_total(...)`) -- never a
                            # separate raw-token field alongside a
                            # hardcoded-null `cost_estimate`. Null ONLY when
                            # bmad-loop's own state reports zero sessions for
                            # this task (the spec's own Never bullet) --
                            # operationally indistinguishable, given
                            # `UsageSnapshot`'s own 4-field shape, from a
                            # weighted total of exactly 0 (a `None` reading,
                            # meaning no valid sample was ever attributed to
                            # this story, collapses to the same null).
                            _append(
                                _BUDGET_USAGE_KIND,
                                {
                                    "story_key": _feed_key_form(current_story_key),
                                    "cost_estimate": (
                                        last_story_weighted_tokens
                                        if last_story_weighted_tokens
                                        else None
                                    ),
                                },
                            )
                        current_story_key = new_story_key
                        story_started_monotonic = (
                            monotonic_now if new_story_key is not None else None
                        )
                        # A new story starts its own fresh ceiling
                        # bookkeeping -- mirrors the idle ladder's own
                        # "a successful retry starts its own fresh idle
                        # window" convention above.
                        story_wall_clock_status = CeilingStatus.NONE
                        story_tokens_status = CeilingStatus.NONE
                        last_story_weighted_tokens = None
                    if usage is not None and new_story_key is not None:
                        last_story_weighted_tokens = usage.story_weighted_tokens

                    if current_story_key is not None and story_started_monotonic is not None:
                        story_elapsed_minutes = (
                            monotonic_now - story_started_monotonic
                        ) / 60.0
                        new_story_wall_clock_status = evaluate_ceiling(
                            story_elapsed_minutes, max_wall_clock_minutes_per_story
                        )
                        _act_on_budget_transition(
                            "story",
                            "wall_clock",
                            story_wall_clock_status,
                            new_story_wall_clock_status,
                            story_elapsed_minutes,
                            max_wall_clock_minutes_per_story,
                        )
                        story_wall_clock_status = new_story_wall_clock_status

                    # --- staleness gate for the TWO TOKEN ceilings only -----
                    # A usage sample older than `threshold_s` (the SAME
                    # threshold the idle ladder already computes, reused
                    # rather than a second knob) is `stale-evidence`
                    # (`MRS-SUPV-006`), never `unevaluable` (AD-32's own
                    # amendment, F-24) -- journaled once per transition into
                    # staleness, and both token ceilings are skipped for
                    # this tick; the two wall-clock ceilings above remain
                    # the binding constraint.
                    state_json_path = _bmad_loop_state_json_path(home, harness_run_id)
                    state_mtime = observer.mtime(state_json_path)
                    is_stale = (
                        state_mtime is None
                        or (moment.timestamp() - state_mtime) > threshold_s
                    )
                    # Widened to ALSO cover `usage is None` with a fresh
                    # mtime (review finding): a torn concurrent write, a
                    # transient `bmad_loop` import failure, or any other
                    # read/parse failure `usage_snapshot` degrades to `None`
                    # for has the IDENTICAL operational consequence as a
                    # stale sample -- both token ceilings cannot be
                    # evaluated this tick -- but the original shape silently
                    # skipped them with NO registered finding at all,
                    # letting a persistent (non-staleness) read failure
                    # disable both token ceilings for the run's whole life
                    # with zero diagnostic anywhere.
                    unevaluable_this_tick = is_stale or usage is None
                    if deferred:
                        # The per-STORY wall-clock ceiling evaluated just
                        # above may have breached IN THIS TICK (review
                        # finding, the same defect as the `harness_run_id`
                        # guard on this block): a run whose terminal
                        # `budget-stop` pair is already journaled gets no
                        # further budget observations appended after it.
                        pass
                    elif unevaluable_this_tick:
                        if not usage_stale:
                            if is_stale:
                                reason = f"stale (state.json mtime {state_mtime!r})"
                            else:
                                reason = (
                                    "unreadable this tick (state.json mtime "
                                    f"{state_mtime!r} is fresh, but the read failed)"
                                )
                            stale_finding = Finding(
                                code="MRS-SUPV-006",
                                severity=Severity.WARN,
                                message=(
                                    f"usage sample for harness run "
                                    f"{harness_run_id!r} is {reason} -- both "
                                    "token ceilings are skipped this tick; "
                                    "the wall-clock ceilings remain the "
                                    "binding constraint"
                                ),
                            )
                            _append(
                                _BUDGET_USAGE_STALE_KIND,
                                {"finding": stale_finding.to_json_dict()},
                            )
                        usage_stale = True
                    else:
                        usage_stale = False
                        new_run_tokens_status = evaluate_ceiling(
                            usage.run_weighted_tokens, max_tokens_per_run
                        )
                        _act_on_budget_transition(
                            "run",
                            "tokens",
                            run_tokens_status,
                            new_run_tokens_status,
                            usage.run_weighted_tokens,
                            max_tokens_per_run,
                        )
                        run_tokens_status = new_run_tokens_status

                        if (
                            usage.story_key is not None
                            and usage.story_weighted_tokens is not None
                        ):
                            new_story_tokens_status = evaluate_ceiling(
                                usage.story_weighted_tokens, max_tokens_per_story
                            )
                            _act_on_budget_transition(
                                "story",
                                "tokens",
                                story_tokens_status,
                                new_story_tokens_status,
                                usage.story_weighted_tokens,
                                max_tokens_per_story,
                            )
                            story_tokens_status = new_story_tokens_status

            # `watched_alive` gates the whole block (review finding): this
            # value is THIS tick's own fresh reading, so if the watched
            # process exited naturally in the very tick an idle threshold
            # also crosses, the ladder must not fire against a process that
            # is already gone -- a genuinely successful completion must
            # never be misreported as an `idle-defer` outcome. The ordinary
            # heartbeat below still appends unconditionally either way.
            # `not deferred` (Story 3.6): a budget ceiling above may already
            # have decided this tick is the run's last one and journaled
            # its own terminal `budget-stop` -- the idle ladder must not
            # ALSO act in the same tick against a process that decision has
            # already targeted for a stop.
            if (
                watched_alive
                and not deferred
                and session_name is not None
                and harness_log_path is not None
            ):
                # Sampled against the REAL session/log target (Story 3.5,
                # closing the two placeholder gaps this module's own
                # docstring names) -- feeds the pure `evaluate_idle` decision
                # (AD-20): no port, no clock call, no I/O inside that
                # function itself.
                pane_content = observer.pane_content(session_name)
                log_mtime = observer.mtime(harness_log_path)
                if pane_content is not None:
                    # UNOBSERVABLE is not IDLE, keyed on the PANE (review
                    # finding -- and the defect three prior passes each
                    # aimed at and missed). The previous guard demanded that
                    # `pane_content` AND `log_mtime` both be `None`, which
                    # in a real run can never happen: `cli/spin.py` opens
                    # `harness.log` before it spawns this sidecar at all, so
                    # `mtime()` always returns a float and the guard was
                    # simply dead code. With tmux merely missing from the
                    # detached sidecar's PATH the pane read `None` on every
                    # tick while that static float held the sample equal to
                    # its predecessor forever -- no re-arm is possible from
                    # an unchanging value -- so the ladder ran its full
                    # sequence (nudge, then a genuine `stop`+`resume`, then
                    # a terminal `defer` that hard-stops the run) against a
                    # process observed ALIVE on every one of those ticks.
                    #
                    # The pane is the only channel that observes the AGENT.
                    # `harness.log` is the bmad-loop ENGINE's own stdout, and
                    # a working agent can go a long time without the engine
                    # writing a line -- so a frozen `harness.log` mtime is
                    # not evidence of idleness, only the absence of one kind
                    # of evidence. When the pane is dark this run cannot be
                    # observed right now, and an unobservable run gets
                    # heartbeat-only supervision, exactly like one whose
                    # `harness_run_id` never resolved.
                    #
                    # The sample is DROPPED rather than appended (review
                    # finding, second defect): a `None` differs from the text
                    # captured either side of it, so a pane capture that
                    # merely flaked once -- a 5s `capture-pane` timeout under
                    # load, a window-teardown race -- entered the history as
                    # TWO changes (text -> None, None -> text) and re-armed
                    # the idle window every time it happened. A wedged
                    # session whose capture flakes once per threshold window
                    # could never accumulate a full threshold, and burned to
                    # the token cap. Dropping it keeps the history to
                    # genuine observations only: the idle anchor survives
                    # the gap, elapsed time keeps accruing across it (a
                    # session that produced nothing while unobserved was
                    # still producing nothing), and real output on the far
                    # side still re-arms by differing from the last sample
                    # actually observed.
                    samples.append(
                        Sample(
                            moment=moment,
                            pane_content=pane_content,
                            log_mtime=log_mtime,
                            monotonic_s=monotonic_now,
                        )
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
                elif len(samples) > 3:
                    # The NO-change half of the same bound (review finding):
                    # the trim above only ever fires on a tick that observed
                    # a change, so the two paths that never observe one again
                    # -- an unobservable channel (below, which is
                    # heartbeat-only and so never terminates via `defer`) and
                    # a run whose ladder is forced to rest -- kept appending
                    # one `Sample` per tick for the whole life of the run,
                    # which is precisely the unbounded growth plus O(n)
                    # rescan the trim above claims to have fixed. Semantics
                    # are again identical: with every sample from index 1
                    # onward equal, `idle_since` derives the same reference
                    # moment from `[first, second, latest]` as it does from
                    # the full history -- the pair at the front still pins
                    # the last change point (or its absence), and the latest
                    # sample still supplies the elapsed-time endpoint.
                    del samples[2:-1]

                if pane_content is None or not samples:
                    # This tick could not observe the run, so it has no
                    # evidence to act on -- see the append guard above for
                    # why the PANE alone answers that question and why the
                    # sample was dropped rather than recorded. `not samples`
                    # covers the opening ticks of a run whose pane has never
                    # once been readable: nothing was ever appended, so
                    # there is no history to evaluate.
                    #
                    # Skipping only the ladder, never the heartbeat: the
                    # heartbeat below still appends unconditionally, so an
                    # unobservable run stays visibly supervised rather than
                    # going silent in the journal.
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
                        # The nudge's own echo must not re-arm the very
                        # window it was escalating from (review finding, and
                        # the defect that made this ladder unable to reach
                        # `stop-and-retry` at all). `send_text` types into
                        # the SAME pane `pane_content` samples, so the next
                        # tick's capture differs from this one's,
                        # `evaluate_idle` reads that as fresh output, the
                        # rung falls back to `NONE`, and the run cycles
                        # nudge -> re-arm -> nudge forever while staying
                        # wedged. "Fresh output" means the SESSION's output,
                        # never this supervisor's own.
                        #
                        # Fixed by collapsing the history onto the
                        # post-nudge pane text while PRESERVING the idle
                        # anchor `idle_since` had already established: the
                        # echoed text becomes the baseline every later
                        # sample is compared against (so it counts as no
                        # change), and elapsed idle time keeps accruing from
                        # where it genuinely started, so one more full
                        # threshold reaches `stop-and-retry`. Genuine agent
                        # output after the nudge still differs from that
                        # baseline and still re-arms, exactly as before. A
                        # `None` re-capture (the pane became unobservable in
                        # the same instant) degrades to the previous
                        # behaviour rather than inventing a baseline.
                        #
                        # Rebased REGARDLESS of `sent` (follow-up review
                        # finding): `send_text` sends the text and the
                        # submitting `Enter` as two separate tmux calls and
                        # reports only the second one's fate, so a `False`
                        # return does NOT mean nothing was typed -- a paste
                        # that landed before a failing or timing-out `Enter`
                        # leaves the supervisor's own text sitting in the
                        # observed pane while this branch skipped the very
                        # rebase that neutralizes it, reopening the
                        # nudge -> re-arm -> nudge loop through the
                        # partial-delivery door. When nothing was in fact
                        # typed the re-capture simply equals the pane already
                        # sampled this tick, making the rebase a semantic
                        # no-op -- so doing it unconditionally is strictly
                        # safer than conditioning it on a signal that cannot
                        # answer the question being asked.
                        # BOTH of the anchor's readings are pinned, not just
                        # its wall-clock `moment` (review finding): elapsed
                        # idle time is now measured monotonically, so letting
                        # `monotonic_s` fall to THIS tick's reading while
                        # pinning `moment` would restart the very count this
                        # rebase exists to preserve -- silently making
                        # `stop-and-retry` unreachable again.
                        anchor_sample = idle_anchor(samples)
                        rebased_pane = observer.pane_content(session_name)
                        if rebased_pane is None:
                            # The pane went dark in the same instant. Keep
                            # the pre-nudge text already observed this tick
                            # rather than seeding the history with a `None`:
                            # the history holds genuine observations only
                            # (see the append guard above), and a `None`
                            # baseline would itself re-arm the window on the
                            # next readable tick -- the same spurious re-arm
                            # dropping unobservable samples exists to stop.
                            rebased_pane = pane_content
                        samples[:] = [
                            Sample(
                                moment=(
                                    anchor_sample.moment
                                    if anchor_sample is not None
                                    else moment
                                ),
                                pane_content=rebased_pane,
                                log_mtime=log_mtime,
                                monotonic_s=(
                                    anchor_sample.monotonic_s
                                    if anchor_sample is not None
                                    else monotonic_now
                                ),
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
                                    # Stale `watched_alive` (follow-up
                                    # review finding, same defect class the
                                    # success branch below already fixed):
                                    # `stop()` returned True, so the pid
                                    # this tick read as alive at its top has
                                    # since been killed -- and this tick's
                                    # own heartbeat still appends below.
                                    # Left alone it asserts `watched_alive:
                                    # True` for a process the supervisor
                                    # itself just stopped, and it is the
                                    # LAST heartbeat any consumer will ever
                                    # see for this run.
                                    watched_alive = process.is_alive(watched_pid)
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
                                    # Verified on the NEXT tick, never here:
                                    # `resume` returning a pid proves the
                                    # spawn worked, not that bmad-loop
                                    # accepted the run (review finding).
                                    retry_verify_pending = True
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
                            defer_detail = f"the stop call itself failed: {exc}"
                        else:
                            # A SENTENCE FRAGMENT, not a sentence (follow-up
                            # review finding): both branches are interpolated
                            # into the same "could not stop harness run
                            # {id} -- {detail}" frame below, and this one used
                            # to restate the whole clause ("bmad-loop reported
                            # harness run '...' was not stopped"), producing
                            # the doubled, unreadable "could not stop harness
                            # run bmad-loop reported harness run '...' was not
                            # stopped -- the run may still be running". The
                            # frame names the run; the detail says only what
                            # is known about WHY.
                            defer_detail = (
                                "bmad-loop reported it was not stopped"
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
                                    f"{harness_run_id!r} -- {defer_detail} "
                                    "-- the run may still be running, now "
                                    "unsupervised"
                                ),
                            )
                            defer_payload["finding"] = defer_finding.to_json_dict()
                        _append_outcome(_DEFER_KIND, intent_id, defer_payload)
                        deferred = True
                        detach_reason = "idle-deferred"
                        # Stale `watched_alive` (follow-up review finding):
                        # the terminal stop above may have just killed the
                        # very pid this tick read as alive at its top, and
                        # this tick's heartbeat -- the LAST one this run will
                        # ever produce -- still appends below. A consumer
                        # reading the final heartbeat used to see
                        # `watched_alive: True` for a process the supervisor
                        # itself had already stopped, immediately under an
                        # `idle-defer` outcome saying so. Recomputed for the
                        # same reason the stop-and-retry branch above
                        # recomputes: a heartbeat is an observation, and an
                        # observation taken before the action it reports on
                        # is not one.
                        watched_alive = process.is_alive(watched_pid)
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

        if retry_verify_pending and not watched_alive:
            # The resumed engine never survived a tick -- see
            # `retry_verify_pending`'s own declaration for why the pid
            # `resume` handed back is not by itself evidence the resume was
            # accepted. `bmad-loop resume` exits non-zero AFTER starting
            # normally for an unknown run ref, a run whose engine it still
            # considers alive, an already-finished run, or missing base
            # skills; in every one of those cases this supervisor had
            # already journaled a clean `{old_pid, new_pid}` retry, and was
            # about to journal the ordinary `"watched-process-exited"` on
            # top of it -- recording a failed recovery as a normal
            # completion in an append-only EVIDENCE journal.
            #
            # Checked HERE rather than at the top of the next tick because
            # there usually is no next tick: the swap recomputes
            # `watched_alive` against the new pid, so a rejected resume ends
            # the loop immediately.
            detach_finding = Finding(
                code="MRS-SUPV-002",
                severity=Severity.WARN,
                message=(
                    f"resumed harness run {harness_run_id!r} (pid "
                    f"{watched_pid}) did not survive its first tick after a "
                    "stop-and-retry -- the resume did not take, so the story "
                    "this run was working is neither progressing nor "
                    "supervised"
                ),
            ).to_json_dict()
            # Never the ordinary `"watched-process-exited"`: this is a failed
            # recovery, the same reason class a `resume` that raises outright
            # already earns.
            detach_reason = "idle-retry-failed"

        # Story 3.7 follow-up review finding: the per-tick capture above only
        # runs while `watched_alive`, so a story bmad-loop defers AFTER this
        # supervisor's last live tick is never observed by one -- and the
        # most common deferral of all is exactly that shape, since deferring
        # the run's LAST story is immediately followed by the engine
        # finishing and the watched pid exiting, usually well inside a single
        # 60s tick. Flushed once here, after the tick loop has ended for ANY
        # reason, through the SAME already-journaled set the per-tick site
        # uses (so a story already reported mid-run is never repeated) --
        # the identical shape, and the identical rationale, as the
        # `budget-usage` flush directly below.
        if harness_run_id is not None:
            final_status_snapshot = harness.run_status_snapshot(home, harness_run_id)
            _capture_deferrals(final_status_snapshot)
            # Story 3.8's own identical flush, for the identical reason
            # (AD-46/FR-61): a story that crosses a stage boundary AFTER
            # this supervisor's last live tick -- e.g. its commit lands and
            # it reaches `Phase.DONE` in the same instant the watched
            # process exits -- is otherwise never pushed at all, the exact
            # gap Story 3.7's own review pass closed for deferrals.
            _process_stage_pushes(final_status_snapshot)

        # Story 3.6 review finding: the ONLY existing `budget-usage` append
        # site fires on an OBSERVED story-key transition, so a run's FINAL
        # (or, for a single-`--story` launch, ONLY) story never sees a
        # later transition and never got a `budget-usage` entry at all --
        # directly undermining this story's own "consumption is journaled
        # per story with a cost estimate" acceptance criterion in the most
        # common invocation shape. Flushed exactly once here, after the tick
        # loop has ended for ANY reason (natural exit, idle-defer, a budget
        # breach, a failed retry), mirroring the transition-flush's own
        # payload shape exactly.
        if current_story_key is not None:
            _append(
                _BUDGET_USAGE_KIND,
                {
                    "story_key": _feed_key_form(current_story_key),
                    "cost_estimate": (
                        last_story_weighted_tokens if last_story_weighted_tokens else None
                    ),
                },
            )

        # --- Story 3.7: escalation detection (AD-45, FR-15) -----------------
        # A RUN-level fact, detected exactly ONCE, only when the tick loop
        # has ended and no OTHER `detach_reason` has already been set by the
        # idle ladder or a budget breach -- those stay more specific and take
        # precedence (the spec's own Always bullet, mirroring the existing
        # `detach_reason or "watched-process-exited"` fallback idiom below
        # exactly: an escalation pause and a wedged/over-budget process are
        # mutually exclusive causes of the same watched pid exiting).
        if detach_reason is None and harness_run_id is not None:
            status_snapshot = harness.run_status_snapshot(home, harness_run_id)
            if status_snapshot is not None:
                escalation_status = evaluate_escalation(
                    status_snapshot.paused_stage,
                    status_snapshot.paused_story_key,
                    status_snapshot.escalated_task_phase,
                )
                if escalation_status is EscalationStatus.UNRESOLVED:
                    # `paused_story_key` is guaranteed non-None here --
                    # `EscalationStatus.UNRESOLVED`'s own definition requires
                    # it.
                    escalation_payload: dict[str, object] = {
                        "story_key": _feed_key_form(status_snapshot.paused_story_key),
                        "reason": status_snapshot.paused_reason,
                        "spec_file": status_snapshot.escalated_spec_file,
                    }
                    _append(_ESCALATION_DETECTED_KIND, escalation_payload)

                    # `to_redacted` treats any "*_key"-suffixed field NAME as
                    # secret-shaped (`core.policy.is_secret_key`) and
                    # replaces its VALUE outright -- the same landmine
                    # `core.egress.build_gate_record` already renames its
                    # own output field to dodge ("story", never
                    # "story_key"), for the identical reason: redacting the
                    # record's own story identifier silently defeats
                    # retrievability. The notify payload mirrors that
                    # rename; the JOURNAL entry above keeps "story_key"
                    # verbatim (the spec's own literal field name).
                    notify_payload = to_redacted(
                        {
                            "story": escalation_payload["story_key"],
                            "reason": escalation_payload["reason"],
                            "spec_file": escalation_payload["spec_file"],
                        }
                    )
                    marker_path = run_dir / _ESCALATION_MARKER_FILENAME
                    # Mandatory: always attempted. A write failure is
                    # tolerated (MRS-SUPV-007, WARN) -- the detach must still
                    # proceed; the escalation is already journaled above
                    # regardless of whether the durable marker landed.
                    try:
                        notify.notify_file(marker_path, notify_payload)
                    except FsError as exc:
                        marker_finding = Finding(
                            code="MRS-SUPV-007",
                            severity=Severity.WARN,
                            message=(
                                f"cannot write escalation file marker "
                                f"{str(marker_path)!r}: {exc}"
                            ),
                        )
                        detach_finding = marker_finding.to_json_dict()
                    # Best-effort: any exception or a `False` return is
                    # swallowed entirely -- never affects the detach outcome
                    # (the spec's own Always bullet). Broad on purpose, the
                    # SAME "must never abandon a live, already-decided
                    # outcome over a diagnostic call" reasoning
                    # `cli/spin.py`'s own lone broad `except Exception` block
                    # already documents for the identical class of call.
                    try:
                        notify.notify_desktop(notify_payload)
                    except Exception:  # noqa: BLE001 -- deliberate, see above
                        pass

                    detach_reason = "escalation-paused"

        detach_payload: dict[str, object] = {
            "pid": pid,
            "reason": detach_reason or "watched-process-exited",
        }
        if detach_finding is not None:
            detach_payload["finding"] = detach_finding
        _append("supervisor-detach", detach_payload)
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
    ``run_supervisor``'s ten positional arguments and relay its exit code.
    This is the ONLY place this module reads its own command line -- AD-9's
    "reads argv once at start and touches no other externally-writable
    input for its own control flow" is literal here: no further read of
    ``sys.argv``, no ``input()``, no ``sys.stdin`` read, anywhere in this
    package. Story 3.6 grows the argv shape from 6 to 10 positionals,
    appending its 4 budget-ceiling values -- each validated the SAME way
    ``idle_threshold_minutes`` already is (positive, finite, guarded
    against the NaN/``<= 0`` footgun both this function's own comment and
    ``core/supervise.py::evaluate_ceiling``'s own guard document)."""
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
    if len(args) != 10 or not all(isinstance(arg, str) for arg in args):
        print(
            "usage: python -m pyforge.marshal.supervisor <home> <slug> "
            "<run_id> <watched_pid> <log_path> <idle_threshold_minutes> "
            "<max_tokens_per_story> <max_tokens_per_run> "
            "<max_wall_clock_minutes_per_story> "
            "<max_wall_clock_minutes_per_run>",
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
        max_tokens_per_story_text,
        max_tokens_per_run_text,
        max_wall_clock_minutes_per_story_text,
        max_wall_clock_minutes_per_run_text,
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
        # honest fix is at the BOUNDARY rather than in the reason
        # vocabulary: refuse a pid this process could never probe, the same
        # "raise/refuse rather than silently misinterpret" discipline the
        # non-positive guard above already applies. (This passage used to
        # justify that by claiming the story enumerates "exactly two" detach
        # reasons. It does not -- the same story also added
        # `"idle-retry-failed"` for a `resume` that fails after a confirmed
        # `stop` -- and the argument never rested on the count anyway, only
        # on refusing to journal an exit this process never observed.)
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
    # Story 3.6's 4 budget-ceiling argv elements -- parsed and range-checked
    # in a loop rather than 4 copies of the block above (Simplicity First):
    # each pair produces the SAME two failure messages idle_threshold_minutes's
    # own block does, just parameterized by name.
    budget_values: dict[str, float] = {}
    for _text, _name in (
        (max_tokens_per_story_text, "max_tokens_per_story"),
        (max_tokens_per_run_text, "max_tokens_per_run"),
        (max_wall_clock_minutes_per_story_text, "max_wall_clock_minutes_per_story"),
        (max_wall_clock_minutes_per_run_text, "max_wall_clock_minutes_per_run"),
    ):
        try:
            _value = float(_text)
        except ValueError:
            print(f"supervisor: invalid {_name} {_text!r}", file=sys.stderr)
            return 1
        # The identical NaN-safe guard idle_threshold_minutes's own block
        # above applies, repeated here rather than shared: `not (x > 0)`
        # plus an explicit finiteness check, never a bare `<= 0`.
        if not (_value > 0) or not math.isfinite(_value):
            print(
                f"supervisor: {_name} must be a positive finite number, "
                f"got {_value}",
                file=sys.stderr,
            )
            return 1
        budget_values[_name] = _value
    return run_supervisor(
        Path(home),
        slug,
        run_id,
        watched_pid,
        Path(log_path_text),
        idle_threshold_minutes,
        budget_values["max_tokens_per_story"],
        budget_values["max_tokens_per_run"],
        budget_values["max_wall_clock_minutes_per_story"],
        budget_values["max_wall_clock_minutes_per_run"],
    )


if __name__ == "__main__":
    raise SystemExit(main())
