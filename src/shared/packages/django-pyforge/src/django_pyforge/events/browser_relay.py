"""Non-group browser tail-read of ``pyforge.events`` (Story 48.6 / R-22).

Uses blocking ``XREAD`` (never ``XREADGROUP``) so live websocket relays do
not join station consumer groups or ACK entries on behalf of browsers.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from collections.abc import Callable
from typing import Any

from django_pyforge.events.constants import EVENT_FIELD
from django_pyforge.events.constants import STREAM
from django_pyforge.events.fabric import parse_cloudevent

StopCheck = Callable[[], bool]
_XREAD_BLOCK_MS = 5_000
_XREAD_COUNT = 50


def matches_subject(event: dict[str, Any], sub: str) -> bool:
    """True when ``event["data"]["subject"]`` equals ``sub``."""
    data = event.get("data")
    if not isinstance(data, dict):
        return False
    subject = data.get("subject")
    return isinstance(subject, str) and subject == sub


def _fields_raw(fields: dict[str, Any]) -> dict[str, Any]:
    return {_k if isinstance(_k, str) else str(_k): _v for _k, _v in fields.items()}


async def tail_events(
    broker_url: str,
    *,
    last_id: str = "$",
    stop: StopCheck,
    client: Any | None = None,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """Tail ``pyforge.events`` with ``XREAD``, yielding ``(stream_id, fields)``."""
    owned = client is None
    if owned:
        import redis.asyncio as aioredis  # noqa: PLC0415

        client = aioredis.from_url(broker_url, decode_responses=True)
    cursor = last_id
    try:
        while not stop():
            rows = await _xread(client, {STREAM: cursor})
            if not rows:
                await asyncio.sleep(0.05)
                continue
            for _stream, messages in rows:
                for stream_id, fields in messages:
                    if stop():
                        return
                    sid = stream_id if isinstance(stream_id, str) else str(stream_id)
                    cursor = sid
                    yield sid, _fields_raw(fields)
    finally:
        if owned:
            aclose = getattr(client, "aclose", None)
            if callable(aclose):
                await aclose()
            else:
                close = getattr(client, "close", None)
                if callable(close):
                    close()


async def _xread(client: Any, streams: dict[str, str]) -> list[list[Any]]:
    xread = getattr(client, "xread", None)
    if xread is None:
        msg = "event broker must support XREAD"
        raise TypeError(msg)
    if asyncio.iscoroutinefunction(xread):
        return await xread(
            streams,
            count=_XREAD_COUNT,
            block=_XREAD_BLOCK_MS,
        ) or []
    return await asyncio.to_thread(
        xread,
        streams,
        count=_XREAD_COUNT,
        block=_XREAD_BLOCK_MS,
    ) or []


def cloudevent_from_fields(fields: dict[str, Any]) -> dict[str, Any] | None:
    """Parse one stream entry's ``event`` field as a CloudEvent."""
    return parse_cloudevent(fields)


def cloudevent_json(fields: dict[str, Any]) -> str | None:
    """Return the raw CloudEvent JSON text frame for a stream entry."""
    event = parse_cloudevent(fields)
    if event is None:
        return None
    return json.dumps(event)
