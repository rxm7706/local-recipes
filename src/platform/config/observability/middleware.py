"""Health-check observability middleware (Story 48.5 / R-21)."""

from __future__ import annotations

import time
from collections.abc import Callable

from django.http import HttpRequest
from django.http import HttpResponse

from config.observability.metrics import observe_health_check


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
        observe_health_check(success=200 <= response.status_code < 300, duration_seconds=duration)
        return response
