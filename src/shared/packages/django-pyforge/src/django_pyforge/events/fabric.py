"""Produce and consume CloudEvents 1.0 on redis-broker Streams (canopy AD-8)."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from django_pyforge.events.constants import APPLIED_PREFIX
from django_pyforge.events.constants import DLQ
from django_pyforge.events.constants import EVENT_FIELD
from django_pyforge.events.constants import EVENT_TYPES
from django_pyforge.events.constants import EVENT_APPLIED_TTL_SECONDS_DEFAULT
from django_pyforge.events.constants import EVENT_STREAM_MAXLEN_DEFAULT
from django_pyforge.events.constants import EXT_GIT_SHA
from django_pyforge.events.constants import EXT_LOOP_DEPTH
from django_pyforge.events.constants import EXT_SBOM_PURL
from django_pyforge.events.constants import EXT_SPEC_ID
from django_pyforge.events.constants import EXT_WORK_ITEM_ID
from django_pyforge.events.constants import LOOP_DEPTH_CEILING
from django_pyforge.events.constants import SPECVERSION
from django_pyforge.events.constants import STATION_TOKENS
from django_pyforge.events.constants import STREAM

Handler = Callable[[dict[str, Any]], None]

_APPLIED_TTL_ENV = "DJANGO_PYFORGE_EVENT_APPLIED_TTL_SECONDS"
_STREAM_MAXLEN_ENV = "DJANGO_PYFORGE_EVENT_STREAM_MAXLEN"


def _applied_ttl_seconds() -> int:
    raw = os.environ.get(_APPLIED_TTL_ENV, "").strip()
    if raw:
        return int(raw)
    return EVENT_APPLIED_TTL_SECONDS_DEFAULT


def _event_stream_maxlen() -> int:
    raw = os.environ.get(_STREAM_MAXLEN_ENV, "").strip()
    if raw:
        return int(raw)
    return EVENT_STREAM_MAXLEN_DEFAULT


def _as_id(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode()
    return str(value)


class EventBrokerConfigError(ValueError):
    """Broker and cache URLs must differ (canopy AD-10)."""


class DataschemaRequiredError(ValueError):
    """CloudEvents dataschema is required (canopy AD-8)."""


class UnregisteredEventTypeError(ValueError):
    """Event type must be a dotted verb registered in django-pyforge."""


class LoopDepthExceededError(ValueError):
    """Publish halted at the pyforgeloopdepth ceiling (canopy AD-8)."""

    def __init__(self, depth: int, event_type: str = "") -> None:
        self.depth = depth
        self.event_type = event_type
        super().__init__(
            f"pyforgeloopdepth {depth} reached ceiling {LOOP_DEPTH_CEILING}; publish halted",
        )


def applied_key(event_id: str) -> str:
    return f"{APPLIED_PREFIX}{event_id}"


def _event_raw(fields: dict[str, Any]) -> str | None:
    raw = fields.get(EVENT_FIELD)
    if raw is None:
        return None
    if isinstance(raw, bytes):
        return raw.decode()
    return str(raw)


def parse_cloudevent(fields: dict[str, Any]) -> dict[str, Any] | None:
    raw = _event_raw(fields)
    if raw is None:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("specversion") != SPECVERSION:
        return None
    required = ("id", "source", "type", "dataschema")
    if any(not payload.get(key) for key in required):
        return None
    return payload


def list_quarantined(client: Any) -> list[tuple[str, dict[str, Any]]]:
    """Operator enumerate of ``pyforge.events.dlq``."""
    rows = client.xrange(DLQ, "-", "+") or []
    return [(stream_id, dict(fields)) for stream_id, fields in rows]


def connect_event_broker(
    broker_url: str,
    cache_url: str,
    *,
    client_factory: Callable[[str], Any] | None = None,
) -> EventFabric:
    """Bind fabric to redis-broker. Refuse a shared URL with redis-cache."""
    if broker_url == cache_url:
        msg = "redis-broker and redis-cache URLs must differ (canopy AD-10)"
        raise EventBrokerConfigError(msg)
    factory = client_factory or _default_redis
    return EventFabric(broker=factory(broker_url))


def _default_redis(url: str) -> Any:
    import redis  # noqa: PLC0415 -- optional runtime driver

    return redis.Redis.from_url(url, decode_responses=True)


def _require_station(group: str) -> None:
    if group not in STATION_TOKENS:
        msg = f"consumer group must be a station token, got {group!r}"
        raise ValueError(msg)


class EventFabric:
    """XADD CloudEvents onto redis-broker; consume with applied-id SET + DLQ harvest."""

    def __init__(self, broker: Any, cache: Any | None = None) -> None:
        self.broker = broker
        self.cache = cache

    def publish(self, event: dict[str, Any]) -> str:
        dataschema = event.get("dataschema")
        if not dataschema:
            msg = "dataschema is required on every CloudEvent (canopy AD-8)"
            raise DataschemaRequiredError(msg)
        event_type = event["type"]
        if event_type not in EVENT_TYPES:
            msg = f"event type {event_type!r} is not registered in django-pyforge"
            raise UnregisteredEventTypeError(msg)
        raw_depth = event.get(EXT_LOOP_DEPTH, 0)
        depth = int(raw_depth)
        if depth >= LOOP_DEPTH_CEILING:
            raise LoopDepthExceededError(depth=depth, event_type=str(event_type))
        event_id = event.get("id") or str(uuid4())
        body: dict[str, Any] = {
            "specversion": SPECVERSION,
            "id": event_id,
            "source": event["source"],
            "type": event_type,
            "dataschema": dataschema,
            EXT_SPEC_ID: event[EXT_SPEC_ID],
            EXT_GIT_SHA: event[EXT_GIT_SHA],
            EXT_SBOM_PURL: event[EXT_SBOM_PURL],
            EXT_LOOP_DEPTH: depth,
        }
        workitemid = event.get(EXT_WORK_ITEM_ID)
        if workitemid:
            body[EXT_WORK_ITEM_ID] = workitemid
        if "data" in event:
            body["data"] = event["data"]
        self.broker.xadd(
            STREAM,
            {EVENT_FIELD: json.dumps(body)},
            maxlen=_event_stream_maxlen(),
            approximate=True,
        )
        return str(event_id)

    def ensure_group(self, group: str) -> None:
        _require_station(group)
        try:
            self.broker.xgroup_create(STREAM, group, id="$", mkstream=True)
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise
            return

    def consume(self, group: str, consumer: str, handler: Handler) -> int:
        _require_station(group)
        self.ensure_group(group)
        handled = 0
        handled += self._drain(group, consumer, handler, start="0")
        handled += self._drain(group, consumer, handler, start=">")
        return handled

    def harvest_poison(self, group: str, consumer: str, min_idle_time: int = 0) -> int:
        """XAUTOCLAIM on ``pyforge.events``, then XADD DLQ and ACK the original."""
        _require_station(group)
        owners = self._pending_owners(group)
        result = self.broker.xautoclaim(STREAM, group, consumer, min_idle_time, "0-0")
        messages = result[1] if result else []
        moved = 0
        for stream_id, fields in messages:
            if parse_cloudevent(fields) is not None:
                previous = owners.get(_as_id(stream_id))
                if previous and previous != consumer:
                    self.broker.xclaim(
                        STREAM,
                        group,
                        previous,
                        min_idle_time,
                        stream_id,
                    )
                continue
            self.broker.xadd(DLQ, dict(fields))
            self.broker.xack(STREAM, group, stream_id)
            moved += 1
        return moved

    def _pending_owners(self, group: str) -> dict[str, str]:
        if not hasattr(self.broker, "xpending_range"):
            return {}
        rows = self.broker.xpending_range(STREAM, group, "-", "+", 1000) or []
        owners: dict[str, str] = {}
        for row in rows:
            if isinstance(row, dict):
                owners[_as_id(row.get("message_id"))] = str(row.get("consumer") or "")
            elif isinstance(row, (list, tuple)) and len(row) >= 2:
                owners[_as_id(row[0])] = str(row[1])
        return owners

    def _drain(
        self,
        group: str,
        consumer: str,
        handler: Handler,
        *,
        start: str,
    ) -> int:
        rows = self.broker.xreadgroup(group, consumer, {STREAM: start}, count=100) or []
        handled = 0
        for _stream, messages in rows:
            for stream_id, fields in messages:
                handled += self._apply(group, stream_id, fields, handler)
        return handled

    def _apply(
        self,
        group: str,
        stream_id: str,
        fields: dict[str, Any],
        handler: Handler,
    ) -> int:
        event = parse_cloudevent(fields)
        if event is None:
            return 0
        key = applied_key(str(event["id"]))
        if not self._mark_applied(key):
            self.broker.xack(STREAM, group, stream_id)
            return 0
        try:
            handler(event)
        except Exception:
            self.broker.delete(key)
            return 0
        self.broker.xack(STREAM, group, stream_id)
        return 1

    def _mark_applied(self, key: str) -> bool:
        return bool(
            self.broker.set(key, "1", nx=True, ex=_applied_ttl_seconds()),
        )
