"""Unit and concurrency tests for the RateLimitedScheduler (Story B1, AC-7 / G-2).

Verifies token bucket math, continuous refill, stall detection under frozen clocks,
and thread-safety of the token scheduler under concurrent load.
"""

from __future__ import annotations

import threading
import time
from typing import Callable
import pytest

from pyforge.atlas.datasets.rate_limit import RateLimitedScheduler, parse_retry_after, resolve_worker_count


class MockClock:
    def __init__(self, start: float = 100.0) -> None:
        self.current_time = start

    def __call__(self) -> float:
        return self.current_time

    def tick(self, duration: float) -> None:
        self.current_time += duration


def make_mock_sleep(clock: MockClock) -> Callable[[float], None]:
    def sleep(duration: float) -> None:
        clock.tick(duration)
    return sleep


# -- 1. Worker count and Retry-After parsing tests -------------------------

def test_resolve_worker_count():
    assert resolve_worker_count("1") == 8
    assert resolve_worker_count("0") == 1
    assert resolve_worker_count(None) == 1
    assert resolve_worker_count("true") == 1


def test_parse_retry_after_delta():
    assert parse_retry_after("30") == 30.0
    assert parse_retry_after("-5") == 0.0
    assert parse_retry_after("120") == 60.0  # Capped at 60.0


def test_parse_retry_after_http_date():
    # target timestamp for "Wed, 21 Oct 2026 07:28:00 GMT" is 1792567680.0
    # delta is 30s when now is 1792567650.0
    assert parse_retry_after("Wed, 21 Oct 2026 07:28:00 GMT", now=1792567650.0) == 30.0
    # past date -> 0s when now is 1792567700.0
    assert parse_retry_after("Wed, 21 Oct 2026 07:28:00 GMT", now=1792567700.0) == 0.0


# -- 2. Scheduler Unit Tests ------------------------------------------------

def test_scheduler_init_validation():
    with pytest.raises(ValueError, match="rps must be > 0"):
        RateLimitedScheduler(rps=0)
    with pytest.raises(ValueError, match="bucket_capacity must be > 0"):
        RateLimitedScheduler(bucket_capacity=0)


def test_scheduler_starts_full_and_refills():
    clock = MockClock()
    sched = RateLimitedScheduler(rps=2.0, bucket_capacity=5, clock=clock)
    assert sched.tokens == 5.0

    # Acquire 3 tokens immediately
    assert sched.acquire(3) == 0.0
    assert sched.tokens == 2.0

    # Advance clock by 1 second -> should refill 2 tokens
    clock.tick(1.0)
    sched._refill()
    assert sched.tokens == 4.0

    # Advance clock by 10 seconds -> should cap at capacity (5)
    clock.tick(10.0)
    sched._refill()
    assert sched.tokens == 5.0


def test_scheduler_blocking_acquire():
    clock = MockClock()
    sleep = make_mock_sleep(clock)
    sched = RateLimitedScheduler(rps=2.0, bucket_capacity=5, clock=clock, sleep=sleep)

    # Empty the bucket
    sched.acquire(5)
    assert sched.tokens == 0.0

    # Attempt to acquire 2 tokens -> requires 1 second wait
    slept = sched.acquire(2)
    assert slept == 1.0
    assert sched.tokens == 0.0
    assert clock() == 101.0


def test_scheduler_acquire_above_capacity_raises():
    sched = RateLimitedScheduler(rps=2.0, bucket_capacity=5)
    with pytest.raises(ValueError, match="cannot acquire"):
        sched.acquire(6)


def test_scheduler_stall_detection():
    clock = MockClock()
    # A no-op sleep that does NOT advance the clock
    def noop_sleep(duration: float) -> None:
        pass

    sched = RateLimitedScheduler(rps=2.0, bucket_capacity=5, clock=clock, sleep=noop_sleep)
    sched.acquire(5)  # empty the bucket

    with pytest.raises(RuntimeError, match="cannot make progress"):
        sched.acquire(1)


# -- 3. Concurrency / Thread-Safety Tests -----------------------------------

def test_scheduler_concurrency_thread_safety():
    """Verify that multiple threads accessing the scheduler concurrently

    do not cause deadlock, type errors, or negative token values.
    """
    sched = RateLimitedScheduler(rps=100.0, bucket_capacity=10)
    errors = []

    def worker():
        try:
            for _ in range(20):
                sched.acquire(1)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Concurrent workers raised exceptions: {errors}"
    assert sched.tokens >= 0.0
