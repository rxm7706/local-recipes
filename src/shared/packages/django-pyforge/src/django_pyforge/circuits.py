"""In-tree PyBreaker-shaped wrapper that trips asyncio (FR-26, canopy AD-15).

``call`` matches PyBreaker: it does not await, so a raising coroutine looks
like success. ``acall`` awaits and records the failure. Do not add pybreaker
to pixi. ``fail_max`` is coarse protection, never an exact-count latch.
"""

from __future__ import annotations

import inspect
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Callable

FAIL_MAX = 5
FAIL_FAST_SECONDS = 0.5
RESET_TIMEOUT_SECONDS = 60.0


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Circuit is open; do not call the dependency."""


@dataclass(frozen=True)
class Degraded:
    reason: str = "circuit_open"


class CircuitBreaker:
    """Shared chrome breaker. Stations must not ship a second wrapper."""

    def __init__(
        self,
        *,
        name: str = "outbound",
        fail_max: int = FAIL_MAX,
        reset_timeout: float = RESET_TIMEOUT_SECONDS,
    ) -> None:
        self.name = name
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self._opened_at: float | None = None
        self._state = CircuitState.CLOSED

    @property
    def state(self) -> CircuitState:
        self._maybe_half_open()
        return self._state

    def _maybe_half_open(self) -> None:
        if self._state is CircuitState.OPEN and self._opened_at is not None:
            if time.monotonic() - self._opened_at >= self.reset_timeout:
                self._state = CircuitState.HALF_OPEN

    def _before(self) -> None:
        self._maybe_half_open()
        if self._state is CircuitState.OPEN:
            raise CircuitOpenError(self.name)

    def _success(self) -> None:
        self.failure_count = 0
        self._state = CircuitState.CLOSED
        self._opened_at = None

    def _failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.fail_max or self._state is CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """PyBreaker trap: does not await. Async callables count as success."""
        self._before()
        try:
            result = func(*args, **kwargs)
        except CircuitOpenError:
            raise
        except Exception:
            self._failure()
            raise
        self._success()
        return result

    async def acall(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        self._before()
        try:
            result = func(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
        except CircuitOpenError:
            raise
        except Exception:
            self._failure()
            raise
        self._success()
        return result

    async def call_or_degrade(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        try:
            return await self.acall(func, *args, **kwargs)
        except CircuitOpenError:
            return Degraded(reason="circuit_open")
