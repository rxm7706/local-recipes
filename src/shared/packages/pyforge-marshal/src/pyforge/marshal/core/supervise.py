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
#: multiples; ``supervisor/__main__.py`` imports it to compare a freshly
#: computed rung against the one it last acted on (``StrEnum`` members carry
#: no intrinsic ordering, so an ordinal lookup table is the one place this
#: package expresses "how far up the ladder" a rung sits).
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
    relationship. Used both here (to build the return value) and by
    ``supervisor/__main__.py`` (to compare a freshly computed rung against
    the last one it acted on)."""
    return _RUNGS_IN_ORDER.index(rung)


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

    reference_moment = samples[0].moment
    for previous, current in zip(samples, samples[1:]):
        if (
            current.pane_content != previous.pane_content
            or current.log_mtime != previous.log_mtime
        ):
            reference_moment = current.moment

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
    index = int(ratio)
    index = min(index, len(_RUNGS_IN_ORDER) - 1)
    return _RUNGS_IN_ORDER[index]
