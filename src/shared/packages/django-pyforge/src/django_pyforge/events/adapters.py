"""Consuming domain adapters validate payload shape (FR-20)."""

from __future__ import annotations

from typing import Any

from django_pyforge.events.constants import EVENT_TYPES


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
