"""Health-check observability middleware (Story 48.5 / R-21)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from config.observability.metrics import observe_health_check

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest
    from django.http import HttpResponse

_HTTP_OK_RANGE_START = 200
_HTTP_OK_RANGE_END = 300


class HealthCheckMetricsMiddleware:
    """Record latency and success/failure for `/ht/` probes."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path.rstrip("/") != "/ht":
            return self.get_response(request)
        started = time.perf_counter()
        response = self.get_response(request)
        duration = time.perf_counter() - started
        ok = _HTTP_OK_RANGE_START <= response.status_code < _HTTP_OK_RANGE_END
        observe_health_check(success=ok, duration_seconds=duration)
        return response
