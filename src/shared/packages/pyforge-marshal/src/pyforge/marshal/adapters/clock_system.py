"""``SystemClock`` -- the sole implementation of ``ports.ClockPort`` (Story
3.4, AD-4/AD-20): a one-line wrapper over ``datetime.now(timezone.utc)``,
mirroring ``cli/spin.py``'s own private ``_now_utc()`` helper exactly except
that THIS copy is reachable through the ``ClockPort`` seam, so
``supervisor/__main__.py`` can inject a fake clock in its own tests (AD-20's
whole point: every supervisor behaviour has a test that runs in
milliseconds against a synthetic sample sequence, never a real sleep).
"""

from __future__ import annotations

from datetime import datetime, timezone


class SystemClock:
    """``ports.ClockPort``'s sole implementation."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)
