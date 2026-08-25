"""Steward 25.1: asyncio circuit wrapper trips and degrades (canopy AD-15)."""

from __future__ import annotations

import ast
import asyncio
import time
from pathlib import Path

import pytest
from django_pyforge.circuits import FAIL_FAST_SECONDS
from django_pyforge.circuits import FAIL_MAX
from django_pyforge.circuits import CircuitBreaker
from django_pyforge.circuits import CircuitOpenError
from django_pyforge.circuits import CircuitState
from django_pyforge.circuits import Degraded

CHROME_CIRCUITS = (
    Path(__file__).resolve().parents[2]
    / "shared"
    / "packages"
    / "django-pyforge"
    / "src"
    / "django_pyforge"
    / "circuits.py"
)

# Well above FAIL_MAX so Redis-style skipped increments still open (FR-26 coarse).
SURPLUS = 20


async def _boom() -> None:
    msg = "outbound down"
    raise RuntimeError(msg)


async def _hang() -> None:
    await asyncio.sleep(FAIL_FAST_SECONDS * 8)
    msg = "should not be awaited when open"
    raise RuntimeError(msg)


def _hammer_acall(breaker: CircuitBreaker) -> None:
    for _ in range(SURPLUS):
        try:
            asyncio.run(breaker.acall(_boom))
        except (RuntimeError, CircuitOpenError):
            continue


def test_repeated_failures_open_circuit_caller_degrades_within_budget() -> None:
    breaker = CircuitBreaker(fail_max=FAIL_MAX, reset_timeout=3600)
    _hammer_acall(breaker)
    assert breaker.state is CircuitState.OPEN

    started = time.perf_counter()
    result = asyncio.run(breaker.call_or_degrade(_hang))
    elapsed = time.perf_counter() - started

    assert isinstance(result, Degraded)
    assert result.reason == "circuit_open"
    assert elapsed < FAIL_FAST_SECONDS


def test_failing_asyncio_call_registers_as_failure_not_success() -> None:
    breaker = CircuitBreaker(fail_max=FAIL_MAX, reset_timeout=3600)
    with pytest.raises(RuntimeError, match="outbound down"):
        asyncio.run(breaker.acall(_boom))
    assert breaker.failure_count >= 1
    assert breaker.state is CircuitState.CLOSED
    _hammer_acall(breaker)
    assert breaker.state is CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        asyncio.run(breaker.acall(_hang))


def test_fail_max_is_coarse_never_exact_count() -> None:
    breaker = CircuitBreaker(fail_max=FAIL_MAX, reset_timeout=3600)
    _hammer_acall(breaker)
    assert breaker.state is CircuitState.OPEN
    assert breaker.failure_count >= FAIL_MAX


def test_removing_wrapper_makes_the_test_fail() -> None:
    tree = ast.parse(CHROME_CIRCUITS.read_text(encoding="utf-8"))
    acall = None
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "CircuitBreaker":
            continue
        for item in node.body:
            if isinstance(item, ast.AsyncFunctionDef) and item.name == "acall":
                acall = item
    assert acall is not None, "CircuitBreaker.acall is the wrapper"
    assert any(isinstance(n, ast.Await) for n in ast.walk(acall)), (
        "acall must await; without it async failures look like success"
    )

    trap = CircuitBreaker(fail_max=FAIL_MAX, reset_timeout=3600)
    for _ in range(SURPLUS):
        leftover = trap.call(_boom)
        leftover.close()
    assert trap.state is CircuitState.CLOSED

    wrapped = CircuitBreaker(fail_max=FAIL_MAX, reset_timeout=3600)
    _hammer_acall(wrapped)
    assert wrapped.state is CircuitState.OPEN
