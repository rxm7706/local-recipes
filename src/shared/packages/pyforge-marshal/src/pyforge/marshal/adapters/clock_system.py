"""``SystemClock`` -- the sole implementation of ``ports.ClockPort`` (Story
3.4, AD-4/AD-20): a one-line wrapper over ``datetime.now(timezone.utc)``,
mirroring ``cli/spin.py``'s own private ``_now_utc()`` helper exactly except
that THIS copy is reachable through the ``ClockPort`` seam, so
``supervisor/__main__.py`` can inject a fake clock in its own tests (AD-20's
whole point: every supervisor behaviour has a test that runs in
milliseconds against a synthetic sample sequence, never a real sleep).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone


class SystemClock:
    """``ports.ClockPort``'s sole implementation."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def monotonic(self) -> float:
        # `time.monotonic`, never `time.time`: this reading exists precisely
        # to be immune to the wall-clock jumps `now` above is subject to
        # (see the port's own docstring). On Linux this is `CLOCK_MONOTONIC`,
        # which EXCLUDES time the host spent suspended -- which is the
        # behaviour the idle ladder wants, since a suspended session cannot
        # have been producing output during the gap either.
        return time.monotonic()
