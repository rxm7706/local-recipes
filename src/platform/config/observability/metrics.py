"""Prometheus metrics for the R-21 observability contract (Story 48.5)."""

from __future__ import annotations

from pathlib import Path

import yaml
from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_client import Counter
from prometheus_client import Gauge
from prometheus_client import Histogram
from prometheus_client import generate_latest

SLO_CONTRACT_PATH = Path(__file__).with_name("slo-contract.yaml")

HEALTH_CHECK_SUCCESS = Counter(
    "pyforge_health_check_success_total",
    "Successful /ht/ health check responses",
)
HEALTH_CHECK_FAILURE = Counter(
    "pyforge_health_check_failure_total",
    "Failed /ht/ health check responses",
)
HEALTH_CHECK_DURATION = Histogram(
    "pyforge_health_check_duration_seconds",
    "Latency of /ht/ health check requests",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

MCP_REQUEST_DURATION = Histogram(
    "pyforge_mcp_request_duration_seconds",
    "Latency of POST /stations/<name>/mcp dispatch",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

CELERY_QUEUE_OLDEST_AGE = Gauge(
    "pyforge_celery_queue_oldest_age_seconds",
    "Age in seconds of the oldest pending task on monitored Celery queues",
)

EVENT_STREAM_LAG = Gauge(
    "pyforge_event_stream_lag_seconds",
    "Oldest pending entry idle time on the main event stream consumer groups",
)

DOCTOR_FLAG_KILL_SWITCH_TOTAL = Counter(
    "pyforge_doctor_flag_kill_switch_total",
    "Doctor flag kill-switch activations",
    ["flag", "reason"],
)

_configured = False


def load_slo_contract() -> dict:
    """Return parsed SLO contract YAML."""
    return yaml.safe_load(SLO_CONTRACT_PATH.read_text(encoding="utf-8"))


def configure_metrics() -> bool:
    """Idempotent metrics registration hook (metrics register at import)."""
    global _configured  # noqa: PLW0603
    if _configured:
        return False
    _configured = True
    return True


def metrics_payload() -> bytes:
    """Prometheus text exposition for GET /metrics."""
    return generate_latest()


def metrics_content_type() -> str:
    return CONTENT_TYPE_LATEST


def observe_health_check(*, success: bool, duration_seconds: float) -> None:
    HEALTH_CHECK_DURATION.observe(duration_seconds)
    if success:
        HEALTH_CHECK_SUCCESS.inc()
    else:
        HEALTH_CHECK_FAILURE.inc()


def observe_mcp_duration(duration_seconds: float) -> None:
    MCP_REQUEST_DURATION.observe(duration_seconds)


def set_celery_queue_oldest_age(seconds: float) -> None:
    CELERY_QUEUE_OLDEST_AGE.set(max(0.0, seconds))


def set_event_stream_lag(seconds: float) -> None:
    EVENT_STREAM_LAG.set(max(0.0, seconds))


def record_flag_kill_switch(flag: str, reason: str) -> None:
    DOCTOR_FLAG_KILL_SWITCH_TOTAL.labels(flag=flag, reason=reason).inc()
