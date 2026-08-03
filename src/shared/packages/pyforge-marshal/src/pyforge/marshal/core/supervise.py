"""The idle-strand decision core (Story 3.5, architecture spine AD-9/AD-20):
``Sample``/``LadderRung``/``evaluate_idle`` -- the pure function that turns
an accumulating sequence of tick-sampled observations into a position on the
3-rung idle ladder (``nudge`` -> ``stop-and-retry`` -> ``defer``).

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
    if not samples:
        return None
    reference_moment = samples[0].moment
    for previous, current in zip(samples, samples[1:]):
        if (
            current.pane_content != previous.pane_content
            or current.log_mtime != previous.log_mtime
        ):
            reference_moment = current.moment
    return reference_moment


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

    # Never `None` here -- the empty-`samples` case already returned above --
    # but spelled as an `or` fallback rather than an `assert`, which `-O`
    # strips and this package therefore never relies on for control flow.
    reference_moment = idle_since(samples) or samples[0].moment

    idle_elapsed_s = (samples[-1].moment - reference_moment).total_seconds()
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
