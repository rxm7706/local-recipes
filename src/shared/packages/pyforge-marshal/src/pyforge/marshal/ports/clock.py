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
