"""Consuming domain adapters validate payload shape (FR-20)."""

from __future__ import annotations

import logging
from typing import Any

from django_pyforge.events.constants import EVENT_TYPES
from django_pyforge.events.constants import STATION_TOKENS
from django_pyforge.events.constants import SUBSCRIPTIONS
from django_pyforge.events.fabric import Handler
from django_pyforge.events.fabric import UnregisteredEventTypeError

logger = logging.getLogger(__name__)


class PayloadShapeError(ValueError):
    """Invalid CloudEvent ``data`` for this adapter — not a stream-boundary error."""


class DomainAdapter:
    """Station-facing consumer: validate ``data`` here, never at XADD/parse."""

    event_type: str = ""
    required_data_keys: frozenset[str] = frozenset()

    def validate(self, event: dict[str, Any]) -> None:
        if event.get("type") not in EVENT_TYPES:
            msg = f"event type {event.get('type')!r} is not registered"
            raise PayloadShapeError(msg)
        if event.get("type") != self.event_type:
            msg = f"adapter {type(self).__name__} does not handle {event.get('type')!r}"
            raise PayloadShapeError(msg)
        data = event.get("data")
        if not isinstance(data, dict):
            msg = "event data must be an object"
            raise PayloadShapeError(msg)
        missing = self.required_data_keys - data.keys()
        if missing:
            msg = f"event data missing keys: {sorted(missing)}"
            raise PayloadShapeError(msg)

    def handle(self, event: dict[str, Any]) -> None:
        self.validate(event)
        self.apply(event)

    def apply(self, event: dict[str, Any]) -> None:
        return None


class RecipeAuditAdapter(DomainAdapter):
    event_type = "recipe.audit.failed"
    required_data_keys = frozenset({"package", "reason"})


class RemedyRequestedAdapter(DomainAdapter):
    event_type = "remedy.requested"
    required_data_keys = frozenset({"package", "remedy"})


class RecipeRebuildAdapter(DomainAdapter):
    event_type = "recipe.rebuild.requested"
    required_data_keys = frozenset({"package"})


class RemedyCompletedAdapter(DomainAdapter):
    event_type = "remedy.completed"
    required_data_keys = frozenset({"package", "outcome"})


# One adapter class per registered type. Station code may subclass and
# re-register (``register_adapter``) to attach its reaction; the shipped
# adapters validate the shape and log, which is what makes a consumer
# deployable before every station's reaction exists.
_ADAPTERS: dict[str, DomainAdapter] = {
    adapter.event_type: adapter
    for adapter in (
        RecipeAuditAdapter(),
        RemedyRequestedAdapter(),
        RecipeRebuildAdapter(),
        RemedyCompletedAdapter(),
    )
}


def register_adapter(adapter: DomainAdapter) -> None:
    if adapter.event_type not in EVENT_TYPES:
        msg = f"event type {adapter.event_type!r} is not registered in django-pyforge"
        raise UnregisteredEventTypeError(msg)
    _ADAPTERS[adapter.event_type] = adapter


def adapter_for(event_type: str) -> DomainAdapter | None:
    return _ADAPTERS.get(event_type)


def subscriptions_for(station: str) -> frozenset[str]:
    if station not in STATION_TOKENS:
        msg = f"station must be a station token, got {station!r}"
        raise ValueError(msg)
    return SUBSCRIPTIONS.get(station, frozenset())


def station_handler(station: str) -> Handler:
    """The handler ``consume_events --station <name>`` runs.

    Routes each event to the adapter for its type when the station
    subscribes to that type; anything else is acknowledged untouched (one
    stream, one group per station — AD-8 — so every group sees every entry).
    """
    subscribed = subscriptions_for(station)

    def handle(event: dict[str, Any]) -> None:
        event_type = str(event.get("type"))
        if event_type not in subscribed:
            return
        adapter = adapter_for(event_type)
        if adapter is None:
            return
        logger.info(
            "event received",
            extra={
                "station": station,
                "event_type": event_type,
                "event_id": event.get("id"),
            },
        )
        adapter.handle(event)

    return handle
