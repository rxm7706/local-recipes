"""``ClockPort`` -- AD-20's injected clock reading (Story 3.4). A Protocol
definition only (Structural Seed: ``ports/`` declares shapes, never
implementations); implemented solely by ``adapters/clock_system.py``
(AD-4). Not an egress port: a clock reading never leaves this host, let
alone a durable or third-party sink.

One method, ``now``: AD-20 requires the supervisor's own idle detection,
budget enforcement, and escalation decisions (Story 3.5's own
``core/supervise.py``, explicitly out of THIS story's Surface) to be pure
functions over a sample sequence -- which means every clock reading a
future decision consumes must already be a plain value by the time it
reaches that pure core, never a live ``datetime.now()`` call buried inside
it. This story wires the seam (the supervisor's own loop calls ``now()``
once per tick) without yet making any decision from what it reads (see
``supervisor/__main__.py``'s own docstring).

``core/**`` never calls this Protocol directly (AD-4: ``core/**`` forbids
``time``/``os``/``subprocess``/``adapters`` imports) -- only
``supervisor/__main__.py`` holds a ``ClockPort`` reference today; a future
``core/supervise.py`` (Story 3.5) will consume the plain ``datetime`` values
this seam already produces, never the port itself.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class ClockPort(Protocol):
    def now(self) -> datetime:
        """The current instant, timezone-AWARE and UTC (``tzinfo`` is never
        ``None``, never a non-UTC offset) -- mirrors every other clock read
        in this package (``cli/spin.py``'s own ``_now_utc``,
        ``core.egress.build_gate_record``'s own UTC-only ``timestamp``
        contract). Never raises: a system clock read has no failure mode
        this package needs to model."""
        ...

    def monotonic(self) -> float:
        """A monotonic reading in fractional seconds from an UNSPECIFIED
        origin -- comparable only against another reading from this same
        method, in this same process. Never raises.

        Exists because ``now`` cannot answer "how long has this been quiet"
        (review finding, Story 3.5). A wall clock JUMPS: a host suspended
        mid-run, or an NTP step, advances ``now`` across an interval in
        which the supervised session was not running at all, and
        ``core/supervise.py`` scored that gap as accumulated idleness --
        enough, at the shipped 25-minute default, to nudge and then hard-stop
        and relaunch a perfectly healthy engine within two ticks of a
        laptop waking up. A monotonic reading does not advance across
        suspend and cannot be stepped backward or forward, so it is the
        correct basis for every ELAPSED-time decision.

        The division of labour is deliberate: ``now`` remains the basis for
        every value a human or the append-only journal reads (timestamps
        must be real wall-clock instants), and ``monotonic`` is the basis
        for durations. Both readings are taken by the caller and passed into
        the pure core as plain values, never called from inside it (AD-20)."""
        ...
