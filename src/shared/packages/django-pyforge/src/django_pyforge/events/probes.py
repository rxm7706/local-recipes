"""Event-stream lag probe helpers (Story 48.5 / R-21)."""

from __future__ import annotations

import logging

from django_pyforge.events.constants import STATION_TOKENS, STREAM

logger = logging.getLogger(__name__)


def event_stream_lag_seconds(redis_client: object) -> float:
    """Return the maximum idle time of pending entries across station groups."""
    lag = 0.0
    for station in STATION_TOKENS:
        group = station
        try:
            pending = redis_client.xpending(STREAM, group)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001, S112 -- missing group/stream is normal pre-deploy
            continue
        if not pending:
            continue
        count = (
            pending[0]
            if isinstance(pending, (list, tuple))
            else pending.get("pending", 0)
        )
        if not count:
            continue
        try:
            details = redis_client.xpending_range(  # type: ignore[attr-defined]
                STREAM,
                group,
                min="-",
                max="+",
                count=1,
            )
        except Exception:
            logger.warning("event lag probe failed for group %s", group, exc_info=True)
            continue
        if not details:
            continue
        entry = details[0]
        idle_ms = (
            entry[2]
            if isinstance(entry, (list, tuple))
            else entry.get("time_since_delivered", 0)
        )
        lag = max(lag, float(idle_ms) / 1000.0)
    return lag
