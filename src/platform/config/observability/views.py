"""Metrics exposition view (Story 48.5 / R-21)."""

from __future__ import annotations

from django.http import HttpRequest
from django.http import HttpResponse

from config.observability.metrics import metrics_content_type
from config.observability.metrics import metrics_payload


def metrics_view(_request: HttpRequest) -> HttpResponse:
    """Unauthenticated Prometheus scrape endpoint (cluster-internal only)."""
    return HttpResponse(metrics_payload(), content_type=metrics_content_type())
