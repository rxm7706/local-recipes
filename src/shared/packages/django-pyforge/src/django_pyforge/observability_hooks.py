"""Optional observability hooks (Story 48.5 / R-21).

Platform registers concrete metric writers at startup; django-pyforge stays
importable without prometheus_client.
"""

from __future__ import annotations

from collections.abc import Callable

_mcp_duration_observer: Callable[[float], None] | None = None
_celery_queue_age_writer: Callable[[float], None] | None = None
_event_stream_lag_writer: Callable[[float], None] | None = None


def set_mcp_duration_observer(observer: Callable[[float], None] | None) -> None:
    global _mcp_duration_observer
    _mcp_duration_observer = observer


def set_celery_queue_age_writer(writer: Callable[[float], None] | None) -> None:
    global _celery_queue_age_writer
    _celery_queue_age_writer = writer


def set_event_stream_lag_writer(writer: Callable[[float], None] | None) -> None:
    global _event_stream_lag_writer
    _event_stream_lag_writer = writer


def observe_mcp_duration(duration_seconds: float) -> None:
    if _mcp_duration_observer is not None:
        _mcp_duration_observer(duration_seconds)


def publish_celery_queue_age(seconds: float) -> None:
    if _celery_queue_age_writer is not None:
        _celery_queue_age_writer(seconds)


def publish_event_stream_lag(seconds: float) -> None:
    if _event_stream_lag_writer is not None:
        _event_stream_lag_writer(seconds)
