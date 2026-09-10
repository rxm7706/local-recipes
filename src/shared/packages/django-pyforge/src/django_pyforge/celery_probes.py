"""Celery queue-age probe helpers (Story 48.5 / R-21)."""

from __future__ import annotations

import logging
import time

from django_pyforge.queues import ALL_QUEUES

logger = logging.getLogger(__name__)


def oldest_queue_age_seconds(redis_client: object) -> float:
    """Return the maximum age in seconds of the head task across broker queues."""
    oldest = 0.0
    for queue in ALL_QUEUES:
        try:
            payload = redis_client.lindex(queue, 0)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 -- probe must not crash the beat task
            logger.warning("queue-age probe failed for queue %s", queue, exc_info=True)
            continue
        if not payload:
            continue
        age = _task_message_age_seconds(payload)
        oldest = max(oldest, age)
    return oldest


def _task_message_age_seconds(payload: bytes | str) -> float:
    """Best-effort age from a Celery/Kombu JSON message envelope."""
    import json

    try:
        raw = payload.decode() if isinstance(payload, bytes) else payload
        message = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return 0.0
    headers = message.get("headers") if isinstance(message, dict) else None
    if not isinstance(headers, dict):
        return 0.0
    published = headers.get("timestamp")
    if published is None:
        return 0.0
    try:
        published_at = float(published)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, time.time() - published_at)
