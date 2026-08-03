"""Unit tests for ``pyforge.marshal.adapters.clock_system`` (Story 3.4,
AD-4/AD-20) -- ``SystemClock``, a one-line wrapper. Real ``datetime.now``,
no mocking: there is nothing to fake, only to characterize.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from pyforge.marshal.adapters.clock_system import SystemClock


def test_now_returns_a_datetime():
    assert isinstance(SystemClock().now(), datetime)


def test_now_is_timezone_aware_utc():
    moment = SystemClock().now()
    assert moment.tzinfo is not None
    assert moment.utcoffset() == timezone.utc.utcoffset(None)


def test_now_advances_between_two_calls():
    """Follow-up review finding: this asserted only ``second >= first``, a
    condition a FROZEN clock satisfies -- so a ``SystemClock`` refactored to
    cache its first reading (precisely the bug the test's name claims to
    guard, and the one thing that would break the supervisor's heartbeat
    timestamps) passed it. Now asserts STRICT advancement across a real
    sleep, which ``datetime.now``'s microsecond resolution makes reliable,
    while keeping the non-strict check for the back-to-back case where two
    readings may legitimately land in the same tick."""
    clock = SystemClock()
    first = clock.now()
    second = clock.now()
    assert second >= first

    time.sleep(0.01)
    third = clock.now()
    assert third > first
