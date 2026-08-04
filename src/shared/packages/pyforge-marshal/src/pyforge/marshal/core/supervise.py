"""The idle-strand decision core (Story 3.5, architecture spine AD-9/AD-20):
``Sample``/``LadderRung``/``evaluate_idle`` -- the pure function that turns
an accumulating sequence of tick-sampled observations into a position on the
3-rung idle ladder (``nudge`` -> ``stop-and-retry`` -> ``defer``).

Story 3.6 (budget ceilings, architecture spine AD-20/AD-32) adds a SECOND,
unrelated pure decision to this module: ``CeilingStatus``/``evaluate_ceiling``
-- a single-observation (not a sequence) ceiling check over ``(observed,
limit)``, used by ``supervisor/__main__.py`` for the 4 new externally-
enforced budget ceilings (per-story/per-run x tokens/wall-clock, FR-13). It
shares this module's own "pure, no I/O, no port" discipline (AD-20) but
needs none of ``evaluate_idle``'s sequence-scanning machinery: a ceiling
check is a single comparison against the LATEST observed quantity, never a
history of samples.

Story 3.7 (escalation, deferral, and resume, architecture spine AD-20/AD-45)
adds a FOURTH pure decision, ``EscalationStatus``/``evaluate_escalation`` --
a single-observation classification (like ``evaluate_ceiling``, not a
sequence scan like ``evaluate_idle``) over bmad-loop's own run-level pause
fields, used by ``supervisor/__main__.py`` at loop-end to detect an
escalation exactly once, and by ``cli/spin.py``'s ``marshal factory resume``
as its live refusal gate.

**Why this is pure (AD-20).** The decision itself must be a function over a
``Sequence[Sample]`` alone: no port, no clock call, no I/O -- every value it
needs (the moment each sample was taken, what was observed) is a fact the
CALLER already gathered, mirroring this package's own established
convention (``core/journal.py``'s ``build_entry``, ``core/egress.py``'s
``build_gate_record``). This is what lets every ladder transition be tested
in milliseconds against a synthetic sample sequence, with no real clock or
subprocess anywhere near the test.

**Why floor-division over elapsed-since-last-change, not a stateful
counter.** ``evaluate_idle`` recomputes the CURRENT rung from scratch every
call: it scans ``samples`` for the most recent point where ``pane_content``
OR ``log_mtime`` differed from its predecessor (a "the session produced
fresh output" event), takes the elapsed time from THAT point to the last
sample's own moment, and floor-divides by ``threshold_s`` to land on a rung.
No external "what rung came before" state is threaded in -- that would
require the caller to already know the answer this function computes, and
would make two calls with the identical ``samples``/``threshold_s`` capable
of disagreeing depending on unmodeled history. The supervisor's own tick
loop (``supervisor/__main__.py``) is the only place that tracks "the last
rung it acted on" -- an ordinary imperative bookkeeping concern for deciding
whether THIS tick's freshly computed rung is new, not part of this pure
contract.

Fresh output re-arms the window (the spec's own Always bullet): a sample
whose ``pane_content``/``log_mtime`` differs from the one before it resets
the "idle since" reference point to that sample's own ``moment``, so
``evaluate_idle`` naturally returns ``LadderRung.NONE`` again immediately
after -- a session that responds to a nudge earns a full fresh threshold
before the ladder advances any further. The supervisor's own tick loop
mirrors this ``NONE`` back into its "last acted rung" bookkeeping, which is
what makes a later re-escalation possible without any special-cased reset
code on either side.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class LadderRung(StrEnum):
    """The 3-rung idle ladder plus its resting position, in ascending
    severity order (the order ``_RUNGS_IN_ORDER`` below encodes numerically
    for comparison -- this ``StrEnum`` itself carries no ordering)."""

    NONE = "none"
    NUDGE = "nudge"
    STOP_AND_RETRY = "stop-and-retry"
    DEFER = "defer"


#: The ladder's fixed rung sequence (the spec's own Never clause: "nudge ->
#: stop-and-retry -> defer is a fixed 3-rung sequence", never policy-shaped).
#: ``evaluate_idle`` indexes into this by floor-divided elapsed-threshold
#: multiples. It is PRIVATE to this module: cross-module callers reach the
#: ordering only through the public ``rung_index`` below (``StrEnum`` members
#: carry no intrinsic ordering, so an ordinal lookup table is the one place
#: this package expresses "how far up the ladder" a rung sits). Review
#: finding: this comment used to claim ``supervisor/__main__.py`` imports
#: this tuple, which it never did -- it imports ``rung_index``.
_RUNGS_IN_ORDER: tuple[LadderRung, ...] = (
    LadderRung.NONE,
    LadderRung.NUDGE,
    LadderRung.STOP_AND_RETRY,
    LadderRung.DEFER,
)


def rung_index(rung: LadderRung) -> int:
    """``rung``'s position in ``_RUNGS_IN_ORDER`` (0 = ``NONE`` .. 3 =
    ``DEFER``) -- the one place this package expresses ladder ordering,
    since ``LadderRung`` is a plain ``StrEnum`` with no intrinsic ``<``/``>``
    relationship. This is the module's PUBLIC ordering accessor and the only
    one ``supervisor/__main__.py`` imports (to compare a freshly computed
    rung against the last one it acted on, and to clamp escalation to one
    rung per tick)."""
    return _RUNGS_IN_ORDER.index(rung)


def rung_at(index: int) -> LadderRung:
    """The rung at ``index``, CLAMPED into ``_RUNGS_IN_ORDER``'s own range
    (below 0 -> ``NONE``, above 3 -> ``DEFER``) -- ``rung_index``'s inverse,
    and the only way a caller outside this module can name "one rung above
    this one" without reaching into the private tuple.

    ``supervisor/__main__.py`` uses it to clamp escalation to a single rung
    per tick (review finding): the ladder is a FIXED 3-rung sequence, but
    ``evaluate_idle`` floor-divides, so ONE tick can land several rungs
    higher than the last one acted on whenever ``threshold_s`` is small
    relative to the caller's own polling interval -- e.g. a 15s threshold
    sampled every 60s reaches ``DEFER`` on the second sample, never firing
    ``nudge`` or ``stop-and-retry`` at all. Clamping keeps the sequence
    intact for every threshold, instead of rejecting the small ones."""
    if index < 0:
        return _RUNGS_IN_ORDER[0]
    return _RUNGS_IN_ORDER[min(index, len(_RUNGS_IN_ORDER) - 1)]


@dataclass(frozen=True)
class Sample:
    """One tick's worth of externally-observed facts (AD-9: idleness is
    measured only from observable session output, never the agent's own
    self-report) -- ``moment`` (when this sample was taken, a caller-supplied
    ``ClockPort.now()`` reading), ``pane_content`` (the session's captured
    terminal text, already redacted at capture per AD-34, or ``None`` if
    unobservable), and ``log_mtime`` (the harness log's Unix mtime, or
    ``None`` if the file does not exist). Frozen and plain -- no validation
    beyond dataclass field typing, matching ``core/journal.py``'s own
    lightweight value-type convention for facts a caller already gathered."""

    moment: datetime
    pane_content: str | None
    log_mtime: float | None
    #: A SUSPEND-IMMUNE elapsed-time basis (``ClockPort.monotonic()``), kept
    #: alongside ``moment`` rather than replacing it (review finding).
    #: ``moment`` is a wall-clock reading, and wall clocks JUMP: a laptop
    #: suspended mid-run, or an NTP step, moves ``moment`` forward by the
    #: whole gap while the session was not running at all, and the ladder
    #: scored that gap as accumulated idleness. At the shipped 25-minute
    #: default a one-hour suspend meant a nudge on the first tick after
    #: wake and a genuine ``stop``+``resume`` of a perfectly healthy engine
    #: 60 seconds later. ``time.monotonic()`` excludes suspended time and
    #: cannot be stepped, so it is the correct basis for "how long has this
    #: been quiet"; ``moment`` remains the basis for everything a HUMAN or
    #: the journal reads, and stays the anchor ``idle_since`` returns.
    #:
    #: Optional, defaulting to ``None``, so a caller that has only wall-clock
    #: readings (every synthetic-sequence test that predates this field, and
    #: any future caller replaying journalled samples) keeps the previous
    #: behaviour exactly: ``evaluate_idle`` falls back to ``moment`` deltas
    #: whenever either endpoint lacks a monotonic reading, and uses the
    #: monotonic pair whenever both carry one.
    monotonic_s: float | None = None


def _anchor_index(samples: Sequence[Sample]) -> int:
    """The index of the most recent sample that showed fresh output --
    ``0`` when no change was ever observed. Assumes a NON-EMPTY ``samples``
    (both public callers guard first). Private: the single scan
    ``idle_since`` and ``evaluate_idle`` share, so the anchor they each
    derive genuinely cannot disagree."""
    anchor = 0
    for index, (previous, current) in enumerate(zip(samples, samples[1:]), start=1):
        if (
            current.pane_content != previous.pane_content
            or current.log_mtime != previous.log_mtime
        ):
            anchor = index
    return anchor


def idle_since(samples: Sequence[Sample]) -> datetime | None:
    """The moment ``samples`` last showed fresh output -- the reference point
    the idle window is measured FROM. ``samples[0].moment`` when no change
    was ever observed across the whole sequence, and ``None`` for an empty
    ``samples``. Pure; no validation beyond what the scan itself needs.

    Factored out of ``evaluate_idle`` (which delegates to it, so the two can
    never disagree) because the CALLER needs the same anchor for a reason
    the ladder decision alone does not cover: after the supervisor's own
    ``nudge`` types text into the observed pane, that pane's next capture
    differs from the previous one, and the change is the supervisor's OWN
    output rather than the session's. Left alone, that re-arms the very
    window the nudge was escalating from -- the ladder returns to ``NONE``
    and can never reach ``stop-and-retry``, no matter how wedged the session
    is (review finding). The caller fixes this by collapsing its sample
    history onto the post-nudge pane text while preserving THIS anchor, and
    it needs a way to ask for the anchor to do so.

    Raises ``TypeError`` for a bare ``str``/``bytes`` (or a non-``Sequence``)
    ``samples``, exactly as ``evaluate_idle`` does -- review finding: this is
    a PUBLIC function ``supervisor/__main__.py`` imports and calls directly,
    not only through its guarded sibling, and without this guard the same
    input that earns a documented ``TypeError`` one call over raised a raw
    ``AttributeError`` from inside the ``zip`` below. In the supervisor's own
    tick that exception class sits outside the ``except (FsError,
    ValueError)`` handler and would kill the sidecar with a traceback after
    ``supervisor-attach``."""
    if isinstance(samples, (str, bytes, bytearray)) or not isinstance(samples, Sequence):
        raise TypeError(
            "samples must be a sequence of Sample (not a bare str/bytes), "
            f"got {samples!r}"
        )
    anchor = idle_anchor(samples)
    return None if anchor is None else anchor.moment


def idle_anchor(samples: Sequence[Sample]) -> Sample | None:
    """The whole ``Sample`` ``idle_since`` reports the ``moment`` of --
    ``samples[0]`` when no change was ever observed, ``None`` for an empty
    ``samples``. Same guards, same scan.

    Public alongside ``idle_since`` because the supervisor's post-nudge
    rebase must preserve BOTH of the anchor's time readings, not just its
    wall-clock ``moment``: the rebase collapses the sample history onto the
    echoed pane text while pinning the idle window's origin, and pinning
    only ``moment`` while letting ``monotonic_s`` fall to the CURRENT tick's
    reading would restart the very elapsed count the rebase exists to
    preserve -- silently making ``stop-and-retry`` unreachable again, the
    exact defect the rebase was introduced to fix."""
    if isinstance(samples, (str, bytes, bytearray)) or not isinstance(samples, Sequence):
        raise TypeError(
            "samples must be a sequence of Sample (not a bare str/bytes), "
            f"got {samples!r}"
        )
    if not samples:
        return None
    return samples[_anchor_index(samples)]


def evaluate_idle(samples: Sequence[Sample], *, threshold_s: float) -> LadderRung:
    """Pure: the ladder rung ``samples`` justifies, given ``threshold_s``
    (seconds) as the per-rung idle window. No port, no clock call, no I/O.

    Walks ``samples`` once to find the most recent index at which
    ``pane_content`` OR ``log_mtime`` differs from its immediate
    predecessor -- fresh output, which re-arms the idle window (the spec's
    own Always bullet) -- and takes the reference "idle since" moment as
    that sample's own ``moment`` (or ``samples[0].moment`` if no change was
    ever observed across the whole sequence). The rung is
    ``min(idle_elapsed // threshold_s, DEFER)``: 0 (``NONE``) below one
    threshold, 1 (``NUDGE``) at one, 2 (``STOP_AND_RETRY``) at two, 3
    (``DEFER``, terminal) at three or more -- floor-divided and capped, never
    stepping past ``DEFER`` regardless of how far elapsed exceeds it.

    An empty ``samples`` (nothing observed yet) returns ``LadderRung.NONE``.
    Raises ``TypeError`` for a ``samples`` that is a bare ``str``/``bytes``
    (satisfies ``Sequence`` but shreds per character/byte -- the same
    footgun ``core/journal.py::fold``/``core/identity.py::resolve_feed``
    each guard against) or not a ``Sequence`` at all, and ``ValueError`` for
    a non-positive ``threshold_s`` (a zero or negative window has no
    meaningful floor-division result) -- including ``float('nan')``, which
    compares ``False`` against every relational operator and so must be
    rejected via a NEGATED ``>`` check, never a direct ``<= 0`` (review
    finding)."""
    if isinstance(samples, (str, bytes, bytearray)) or not isinstance(samples, Sequence):
        raise TypeError(
            "samples must be a sequence of Sample (not a bare str/bytes), "
            f"got {samples!r}"
        )
    if isinstance(threshold_s, bool) or not isinstance(threshold_s, (int, float)):
        raise TypeError(f"threshold_s must be a number, got {threshold_s!r}")
    # `not (threshold_s > 0)`, never `threshold_s <= 0` (review finding): IEEE
    # 754 makes EVERY comparison against `float('nan')` false, so `<= 0` let a
    # NaN threshold sail through this guard entirely instead of being
    # rejected like every other invalid value. Negating a `>` comparison
    # catches it (`nan > 0` is `False`, so `not False` is `True`) while still
    # accepting every genuinely positive value and rejecting zero/negative
    # ones exactly as before.
    if not (threshold_s > 0):
        raise ValueError(f"threshold_s must be positive, got {threshold_s!r}")
    if not samples:
        return LadderRung.NONE

    anchor = samples[_anchor_index(samples)]
    latest = samples[-1]

    # MONOTONIC when both endpoints carry one, wall-clock otherwise (review
    # finding). `moment` is a wall-clock reading and wall clocks JUMP -- a
    # host suspended mid-run, or an NTP step, advances it across an interval
    # in which the session was not running and could not possibly have
    # produced output. Scoring that gap as accumulated idleness fired a
    # nudge on the first tick after wake and a genuine `stop`+`resume` of a
    # healthy engine one tick later, at the shipped 25-minute default.
    # `time.monotonic()` does not advance across suspend and cannot be
    # stepped, so a monotonic pair measures what this function actually
    # means by "elapsed". The wall-clock fallback keeps every synthetic
    # sequence that supplies only `moment` behaving exactly as before.
    if anchor.monotonic_s is not None and latest.monotonic_s is not None:
        idle_elapsed_s = latest.monotonic_s - anchor.monotonic_s
    else:
        idle_elapsed_s = (latest.moment - anchor.moment).total_seconds()
    # Defensive floor at zero: a caller handing a non-chronological sequence
    # (the last sample's own moment earlier than the reference one) is a
    # contract violation this function does not otherwise validate for --
    # `//` on a negative float rounds toward negative infinity in Python, so
    # an un-clamped negative elapsed value would index BACKWARDS into
    # `_RUNGS_IN_ORDER` instead of degrading to `NONE`.
    idle_elapsed_s = max(idle_elapsed_s, 0.0)

    # A tiny epsilon before floor-dividing (verified live: `0.3 // 0.1 ==
    # 2.0`, not `3.0`, because binary floating point cannot represent either
    # operand exactly) -- without it, a sample sequence that has genuinely
    # reached an exact threshold multiple floors to the rung BELOW the one
    # it actually reached. Harmless at production timescales (a 60s tick
    # against a whole-minute threshold has ample floating-point headroom);
    # this only ever nudges a value that is already, to double precision,
    # indistinguishable from the boundary itself.
    ratio = idle_elapsed_s / threshold_s + 1e-9
    # An OVERFLOWING ratio is the terminal rung, never an exception (review
    # finding). `threshold_s` only has to be positive and finite to pass every
    # guard above, and a denormal-small one (`idle_threshold_minutes` in the
    # 1e-320 range -- absurd, but `core/policy.py`'s validator accepts it and
    # this function's own contract does not bound it) overflows this division
    # to `inf`. `int(inf)` raises `OverflowError`, which is neither `FsError`
    # nor `ValueError`, so it escapes `supervisor/__main__.py`'s own tick
    # handler entirely and kills the sidecar with a raw traceback after
    # `supervisor-attach` -- the dangling-attach state AD-9 forbids. An
    # infinite ratio means elapsed idle time dwarfs the window by every
    # measure available here, which IS `DEFER` by this function's own
    # floor-and-cap definition.
    if not math.isfinite(ratio):
        return _RUNGS_IN_ORDER[-1]
    index = int(ratio)
    index = min(index, len(_RUNGS_IN_ORDER) - 1)
    return _RUNGS_IN_ORDER[index]


# =============================================================================
# Story 3.6: budget ceilings (AD-20/AD-32, FR-13) -- CeilingStatus/
# evaluate_ceiling, a second and unrelated pure decision this module hosts
# for the same "no port, no clock call, no I/O" reason evaluate_idle above
# is pure: the supervisor's own tick loop gathers `observed`/`limit` as
# plain values (a monotonic elapsed-minutes reading, or a weighted token
# count read via HarnessPort.usage_snapshot) and this function makes no
# decision from anything but the two numbers it is handed.
# =============================================================================


class CeilingStatus(StrEnum):
    """One ceiling's position relative to its configured limit, in ascending
    severity order (this ``StrEnum`` itself carries no ordering -- exactly
    ``LadderRung``'s own convention above, for the same reason: the
    supervisor's tick loop tracks "the last status it acted on" per
    ceiling and needs to detect a RISING edge, never a `<`/`>` on the enum
    members themselves)."""

    NONE = "none"
    APPROACHING = "approaching"
    BREACHED = "breached"


#: The fixed ratio of ``limit`` at which a ceiling transitions from ``NONE``
#: to ``APPROACHING`` (the spec's own Always bullet: "'Approaching' is a
#: fixed 80% ratio, not a policy knob -- no real caller has asked for that to
#: be tunable", mirroring ``_TICK_SECONDS``'s own "no knob without a caller"
#: precedent above). Private: no caller outside this module needs the raw
#: ratio, only the ``CeilingStatus`` it produces.
_APPROACH_RATIO = 0.8


# =============================================================================
# Story 3.7: escalation detection (AD-20/AD-45, FR-15/16/17) -- a THIRD and
# unrelated pure decision this module hosts, for the identical "no port, no
# clock call, no I/O" reason `evaluate_idle`/`evaluate_ceiling` above are
# pure: the supervisor's own tick loop gathers the three inputs as plain
# values, already read off a `HarnessPort.run_status_snapshot` result, and
# this function makes no decision from anything but them.
# =============================================================================


class EscalationStatus(StrEnum):
    """Escalation's classification of ``RunState``'s own pause fields (Story
    3.7): ``NONE`` (not this kind of pause at all), ``UNRESOLVED`` (paused
    for escalation, and the story's task is still ``Phase.ESCALATED``), or
    ``RESOLVED`` (paused for escalation, but the story's task has already
    moved off ``ESCALATED`` -- bmad-loop's own ``rearm_escalation`` flips the
    task's phase back to ``pending`` WITHOUT clearing the pause itself; the
    caller resumes the run separately -- so this state is reachable only
    between a human resolving the escalation and the resume that actually
    clears it). This ``StrEnum`` itself carries no ordering, mirroring
    ``LadderRung``/``CeilingStatus``'s own convention -- no caller needs
    one."""

    NONE = "none"
    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"


def evaluate_escalation(
    paused_stage: str | None, paused_story_key: str | None, task_phase: str | None
) -> EscalationStatus:
    """Pure: classifies bmad-loop's own run-level pause fields
    (``RunState.paused_stage``/``.paused_story_key``, plus the paused
    story's own task ``phase``) into ``EscalationStatus``. No port, no clock
    call, no I/O -- every value is a fact the CALLER already gathered (via
    ``HarnessPort.run_status_snapshot``), mirroring ``evaluate_idle``/
    ``evaluate_ceiling``'s own "the decision core receives values, never
    reads them itself" convention (AD-20).

    ``UNRESOLVED`` iff ``paused_stage == "escalation" and paused_story_key is
    not None and task_phase == "escalated"`` -- the story's own intent-
    contract wording, verbatim. Otherwise: ``NONE`` when ``paused_stage`` is
    not ``"escalation"`` at all (not this kind of pause -- includes ``None``,
    every other pause stage bmad-loop names, and a malformed/unexpected
    value); ``RESOLVED`` when ``paused_stage == "escalation"`` but the
    ``UNRESOLVED`` condition does not hold (``paused_story_key`` missing, or
    the task's phase has already moved off ``"escalated"``) -- the only
    reachable shape is the human-resolved-but-not-yet-resumed window this
    class's own docstring describes.

    No type guard beyond ordinary equality: unlike ``evaluate_idle``'s
    ``threshold_s``/``evaluate_ceiling``'s ``limit``, none of these three
    inputs has an invalid-input class analogous to non-finite/non-numeric --
    every ``str | None`` value compares safely, and an unexpected string
    simply fails the equality checks it needs to (correctly classifying as
    ``NONE``/``RESOLVED``, never raising)."""
    if paused_stage != "escalation":
        return EscalationStatus.NONE
    if paused_story_key is not None and task_phase == "escalated":
        return EscalationStatus.UNRESOLVED
    return EscalationStatus.RESOLVED


def evaluate_ceiling(observed: float, limit: float) -> CeilingStatus:
    """Pure: ``observed`` against ``limit`` (both operate on comparable
    units -- e.g. minutes for wall-clock, weighted token count for tokens --
    the CALLER's own concern, never this function's). No port, no clock
    call, no I/O.

    ``BREACHED`` when ``observed >= limit``; ``APPROACHING`` when
    ``observed >= _APPROACH_RATIO * limit`` (and not yet breached); ``NONE``
    otherwise -- a single comparison, never a sequence scan (unlike
    ``evaluate_idle`` above, a ceiling has no "idle window" to re-arm; the
    supervisor's own tick loop is what tracks whether THIS observation is a
    rising edge over the LAST one it acted on).

    Guards ``limit`` exactly as ``evaluate_idle`` guards its own
    ``threshold_s``: raises ``TypeError`` for a non-numeric ``limit``
    (``bool`` included, since ``isinstance(True, int)`` is ``True`` in
    Python and a boolean limit is never a meaningful ceiling), and
    ``ValueError`` for a non-positive or non-finite ``limit`` -- via a
    NEGATED ``>`` comparison (`not (limit > 0)`), never a direct ``<= 0``:
    IEEE 754 makes every relational comparison against ``float('nan')``
    false, so a direct ``<= 0`` would let a NaN limit sail through instead
    of being rejected like every other invalid value (the identical review
    finding ``evaluate_idle``'s own ``threshold_s`` guard already documents
    and fixes). ``observed`` carries no such guard: a caller-derived
    quantity (elapsed monotonic minutes, a weighted token count) is always a
    plain, already-validated number by construction, and a negative
    ``observed`` (which cannot occur for either of this story's two metrics)
    would still produce a coherent, harmless ``NONE`` rather than a
    surprising exception."""
    if isinstance(limit, bool) or not isinstance(limit, (int, float)):
        raise TypeError(f"limit must be a number, got {limit!r}")
    if not (limit > 0):
        raise ValueError(f"limit must be positive, got {limit!r}")
    if not math.isfinite(limit):
        raise ValueError(f"limit must be finite, got {limit!r}")
    if observed >= limit:
        return CeilingStatus.BREACHED
    if observed >= _APPROACH_RATIO * limit:
        return CeilingStatus.APPROACHING
    return CeilingStatus.NONE
