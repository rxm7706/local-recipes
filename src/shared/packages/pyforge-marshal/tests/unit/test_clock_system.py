"""Unit tests for ``pyforge.marshal.adapters.clock_system`` (Story 3.4,
AD-4/AD-20) -- ``SystemClock``, a one-line wrapper. Real ``datetime.now``,
no mocking: there is nothing to fake, only to characterize.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pyforge.marshal.adapters.clock_system import SystemClock


def test_now_returns_a_datetime():
    assert isinstance(SystemClock().now(), datetime)


def test_now_is_timezone_aware_utc():
    moment = SystemClock().now()
    assert moment.tzinfo is not None
    assert moment.utcoffset() == timezone.utc.utcoffset(None)


def test_now_advances_between_two_calls():
    clock = SystemClock()
    first = clock.now()
    second = clock.now()
    assert second >= first
