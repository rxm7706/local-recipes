"""Produce and consume CloudEvents 1.0 on redis-broker Streams (canopy AD-8).

Delivery semantics (Story 42.3, red-team A-2 / A-4, directive R-9):

* ``consume`` first retries this consumer's own pending entries whose backoff
  has elapsed (XPENDING for the idle time and delivery counter, XCLAIM to
  re-deliver — which is what advances the counter), then reads new entries.
  A handler failure leaves the entry pending, un-ACKed, with the error
  recorded; the next attempt waits ``backoff_ms(attempts)``.
* After ``EVENT_MAX_ATTEMPTS`` failed attempts a well-formed event is written
  to ``pyforge.events.dlq`` with the last error and only then ACKed. An entry
  that does not parse as a CloudEvent is quarantined on first sight.
* ``harvest_poison`` reclaims entries another consumer abandoned (idle at
  least the handler timeout — never a message a live consumer is still
  working on), quarantines the unparseable and the exhausted, and leaves the
  rest pending under the harvester for its retry pass.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from django_pyforge.events.constants import APPLIED_PREFIX
from django_pyforge.events.constants import DLQ
from django_pyforge.events.constants import DLQ_ATTEMPTS_FIELD
from django_pyforge.events.constants import DLQ_ERROR_FIELD
from django_pyforge.events.constants import DLQ_GROUP_FIELD
from django_pyforge.events.constants import DLQ_REASON_EXHAUSTED
from django_pyforge.events.constants import DLQ_REASON_FIELD
from django_pyforge.events.constants import DLQ_REASON_UNPARSEABLE
from django_pyforge.events.constants import DLQ_STREAM_ID_FIELD
from django_pyforge.events.constants import EVENT_APPLIED_TTL_SECONDS_DEFAULT
from django_pyforge.events.constants import EVENT_BACKOFF_BASE_MS_DEFAULT
from django_pyforge.events.constants import EVENT_BACKOFF_MAX_MS_DEFAULT
from django_pyforge.events.constants import EVENT_FIELD
from django_pyforge.events.constants import EVENT_HANDLER_TIMEOUT_MS_DEFAULT
from django_pyforge.events.constants import EVENT_MAX_ATTEMPTS_DEFAULT
from django_pyforge.events.constants import EVENT_STREAM_MAXLEN_DEFAULT
from django_pyforge.events.constants import EVENT_TYPES
from django_pyforge.events.constants import EXT_GIT_SHA
from django_pyforge.events.constants import EXT_LOOP_DEPTH
from django_pyforge.events.constants import EXT_SBOM_PURL
from django_pyforge.events.constants import EXT_SPEC_ID
from django_pyforge.events.constants import EXT_TRACEPARENT
from django_pyforge.events.constants import EXT_WORK_ITEM_ID
from django_pyforge.events.constants import LAST_ERROR_PREFIX
from django_pyforge.events.constants import LOOP_DEPTH_CEILING
from django_pyforge.events.constants import SPECVERSION
from django_pyforge.events.constants import STATION_TOKENS
from django_pyforge.events.constants import STREAM
from django_pyforge.events.tracing import TraceparentFormatError
from django_pyforge.events.tracing import bound_trace
from django_pyforge.events.tracing import current_traceparent
from django_pyforge.events.tracing import parse_traceparent

Handler = Callable[[dict[str, Any]], None]

logger = logging.getLogger(__name__)

_APPLIED_TTL_ENV = "DJANGO_PYFORGE_EVENT_APPLIED_TTL_SECONDS"
_STREAM_MAXLEN_ENV = "DJANGO_PYFORGE_EVENT_STREAM_MAXLEN"
_MAX_ATTEMPTS_ENV = "DJANGO_PYFORGE_EVENT_MAX_ATTEMPTS"
_BACKOFF_BASE_MS_ENV = "DJANGO_PYFORGE_EVENT_BACKOFF_BASE_MS"
_BACKOFF_MAX_MS_ENV = "DJANGO_PYFORGE_EVENT_BACKOFF_MAX_MS"
_HANDLER_TIMEOUT_MS_ENV = "DJANGO_PYFORGE_EVENT_HANDLER_TIMEOUT_MS"

_BATCH = 100


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if raw:
        return int(raw)
    return default


def _applied_ttl_seconds() -> int:
    return _env_int(_APPLIED_TTL_ENV, EVENT_APPLIED_TTL_SECONDS_DEFAULT)


def _event_stream_maxlen() -> int:
    return _env_int(_STREAM_MAXLEN_ENV, EVENT_STREAM_MAXLEN_DEFAULT)


def max_attempts() -> int:
    """Attempts a well-formed event gets before the DLQ (>= 1)."""
    return max(1, _env_int(_MAX_ATTEMPTS_ENV, EVENT_MAX_ATTEMPTS_DEFAULT))


def handler_timeout_ms() -> int:
    """The handler budget; also ``harvest_poison``'s default ``min_idle_time``."""
    return max(0, _env_int(_HANDLER_TIMEOUT_MS_ENV, EVENT_HANDLER_TIMEOUT_MS_DEFAULT))


def backoff_ms(attempts: int) -> int:
    """Wait before the next attempt after ``attempts`` failed deliveries.

    ``base * 2**(attempts-1)`` capped at the max: with the defaults 1s, 2s,
    4s, 8s, then 16s ... 60s.
    """
    base = max(0, _env_int(_BACKOFF_BASE_MS_ENV, EVENT_BACKOFF_BASE_MS_DEFAULT))
    cap = max(0, _env_int(_BACKOFF_MAX_MS_ENV, EVENT_BACKOFF_MAX_MS_DEFAULT))
    exponent = max(0, attempts - 1)
    return min(base * (2**exponent), cap)


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


def last_error_key(stream_id: str) -> str:
    return f"{LAST_ERROR_PREFIX}{stream_id}"


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


def _pending_row(row: Any) -> tuple[str, str, int, int] | None:
    """``(stream_id, consumer, idle_ms, delivery_count)`` from an XPENDING row."""
    if isinstance(row, dict):
        return (
            _as_id(row.get("message_id")),
            str(row.get("consumer") or ""),
            int(row.get("time_since_delivered") or 0),
            int(row.get("times_delivered") or 0),
        )
    if isinstance(row, (list, tuple)) and len(row) >= 4:
        return (_as_id(row[0]), str(row[1]), int(row[2]), int(row[3]))
    return None


class EventFabric:
    """XADD CloudEvents onto redis-broker; consume with attempts, backoff, DLQ."""

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
        traceparent = event.get(EXT_TRACEPARENT)
        if traceparent is not None and not parse_traceparent(traceparent):
            msg = f"{EXT_TRACEPARENT} must be a W3C Trace Context header, got {traceparent!r}"
            raise TraceparentFormatError(msg)
        if traceparent is None:
            # The publisher's own trace (the request, or the consumer that
            # reacted to the previous hop) rides the envelope by default.
            traceparent = current_traceparent()
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
        if traceparent:
            body[EXT_TRACEPARENT] = traceparent
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
        """One pass: retry due pending entries, then read new ones.

        Returns the number of events the handler completed. Never sleeps —
        an entry whose backoff has not elapsed is simply not attempted, so a
        caller polling in a loop does not spin on a failing event.
        """
        _require_station(group)
        self.ensure_group(group)
        handled = 0
        handled += self._retry_pending(group, consumer, handler)
        handled += self._drain(group, consumer, handler)
        return handled

    def harvest_poison(
        self,
        group: str,
        consumer: str,
        min_idle_time: int | None = None,
    ) -> int:
        """XAUTOCLAIM entries idle >= ``min_idle_time`` (default: the handler
        timeout); quarantine the unparseable and the exhausted; keep the rest
        pending under ``consumer`` for its retry pass. Returns entries moved
        to the DLQ.
        """
        _require_station(group)
        threshold = handler_timeout_ms() if min_idle_time is None else int(min_idle_time)
        result = self.broker.xautoclaim(STREAM, group, consumer, threshold, "0-0", count=_BATCH)
        messages = result[1] if result else []
        if not messages:
            return 0
        counts = {
            row[0]: row[3]
            for row in (_pending_row(item) for item in self._pending_rows(group, consumer))
            if row is not None
        }
        ceiling = max_attempts()
        moved = 0
        for stream_id, fields in messages:
            sid = _as_id(stream_id)
            if parse_cloudevent(fields) is None:
                self._quarantine(group, sid, fields, reason=DLQ_REASON_UNPARSEABLE, attempts=counts.get(sid, 0))
                moved += 1
                continue
            # The claim itself is a delivery, so an abandoned delivery counts
            # as a spent attempt — the same rule the retry pass applies.
            attempts = counts.get(sid, 0)
            if attempts >= ceiling:
                self._quarantine(group, sid, fields, reason=DLQ_REASON_EXHAUSTED, attempts=attempts)
                moved += 1
        return moved

    def _pending_rows(self, group: str, consumer: str | None = None) -> list[Any]:
        if not hasattr(self.broker, "xpending_range"):
            return []
        kwargs: dict[str, Any] = {}
        if consumer is not None:
            kwargs["consumername"] = consumer
        return self.broker.xpending_range(STREAM, group, "-", "+", _BATCH, **kwargs) or []

    def _retry_pending(self, group: str, consumer: str, handler: Handler) -> int:
        handled = 0
        ceiling = max_attempts()
        for item in self._pending_rows(group, consumer):
            row = _pending_row(item)
            if row is None:
                continue
            stream_id, _owner, idle, attempts = row
            if attempts >= ceiling:
                # Every attempt was spent and the last one never reported
                # back (the process died mid-handler). The recorded error,
                # if any, is what the DLQ entry carries.
                fields = self._fields_of(stream_id)
                if fields is not None:
                    self._quarantine(group, stream_id, fields, reason=DLQ_REASON_EXHAUSTED, attempts=attempts)
                else:
                    self.broker.xack(STREAM, group, stream_id)
                continue
            delay = backoff_ms(attempts)
            if idle < delay:
                continue
            claimed = self.broker.xclaim(STREAM, group, consumer, delay, [stream_id]) or []
            for claimed_id, fields in claimed:
                handled += self._apply(group, _as_id(claimed_id), fields, handler, attempt=attempts + 1)
        return handled

    def _fields_of(self, stream_id: str) -> dict[str, Any] | None:
        rows = self.broker.xrange(STREAM, stream_id, stream_id) or []
        for row_id, fields in rows:
            if _as_id(row_id) == stream_id:
                return dict(fields)
        return None

    def _drain(self, group: str, consumer: str, handler: Handler) -> int:
        rows = self.broker.xreadgroup(group, consumer, {STREAM: ">"}, count=_BATCH) or []
        handled = 0
        for _stream, messages in rows:
            for stream_id, fields in messages:
                handled += self._apply(group, _as_id(stream_id), fields, handler, attempt=1)
        return handled

    def _apply(
        self,
        group: str,
        stream_id: str,
        fields: dict[str, Any],
        handler: Handler,
        *,
        attempt: int,
    ) -> int:
        event = parse_cloudevent(fields)
        if event is None:
            self._quarantine(group, stream_id, fields, reason=DLQ_REASON_UNPARSEABLE, attempts=attempt)
            return 0
        key = applied_key(str(event["id"]))
        if not self._mark_applied(key):
            self.broker.xack(STREAM, group, stream_id)
            return 0
        try:
            with bound_trace(event.get(EXT_TRACEPARENT)):
                handler(event)
        except Exception as exc:
            self.broker.delete(key)
            error = f"{type(exc).__name__}: {exc}"
            self.broker.set(last_error_key(stream_id), error, ex=_applied_ttl_seconds())
            if attempt >= max_attempts():
                self._quarantine(group, stream_id, fields, reason=DLQ_REASON_EXHAUSTED, attempts=attempt, error=error)
                return 0
            logger.warning(
                "event handler failed; retry in %d ms",
                backoff_ms(attempt),
                extra={
                    "event_id": event.get("id"),
                    "event_type": event.get("type"),
                    "stream_id": stream_id,
                    "attempt": attempt,
                    "error": error,
                },
            )
            return 0
        self.broker.xack(STREAM, group, stream_id)
        self.broker.delete(last_error_key(stream_id))
        return 1

    def _quarantine(
        self,
        group: str,
        stream_id: str,
        fields: dict[str, Any],
        *,
        reason: str,
        attempts: int,
        error: str | None = None,
    ) -> None:
        """XADD the entry to the DLQ with its error, then ACK the original.

        Order matters: a crash between the two leaves a duplicate DLQ row,
        never a lost event. The error is always present — the one in hand,
        else the last one recorded, else what is known about the entry.
        """
        if error is None:
            error = self.broker.get(last_error_key(stream_id))
        if error is None:
            error = (
                "not a CloudEvents 1.0 envelope"
                if reason == DLQ_REASON_UNPARSEABLE
                else f"{attempts} attempt(s) spent; last handler error not recorded"
            )
        entry = dict(fields)
        entry[DLQ_REASON_FIELD] = reason
        entry[DLQ_ERROR_FIELD] = str(error)
        entry[DLQ_ATTEMPTS_FIELD] = str(attempts)
        entry[DLQ_GROUP_FIELD] = group
        entry[DLQ_STREAM_ID_FIELD] = stream_id
        entry["quarantined_at"] = str(int(time.time()))
        self.broker.xadd(DLQ, entry)
        self.broker.xack(STREAM, group, stream_id)
        self.broker.delete(last_error_key(stream_id))
        logger.error(
            "event quarantined on %s",
            DLQ,
            extra={"stream_id": stream_id, "group": group, "reason": reason, "attempts": attempts, "error": error},
        )

    def _mark_applied(self, key: str) -> bool:
        return bool(
            self.broker.set(key, "1", nx=True, ex=_applied_ttl_seconds()),
        )
