"""Enumerate quarantined CloudEvents on pyforge.events.dlq."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand

from django_pyforge.events import DLQ
from django_pyforge.events import list_quarantined
from django_pyforge.events.constants import DLQ_ATTEMPTS_FIELD
from django_pyforge.events.constants import DLQ_ERROR_FIELD
from django_pyforge.events.constants import DLQ_GROUP_FIELD
from django_pyforge.events.constants import DLQ_QUARANTINED_AT_FIELD
from django_pyforge.events.constants import DLQ_REASON_FIELD
from django_pyforge.events.constants import DLQ_STREAM_ID_FIELD
from django_pyforge.events.constants import EVENT_FIELD

# Story 42.3: the metadata every quarantine writes next to the event.
_META_FIELDS = (
    DLQ_REASON_FIELD,
    DLQ_ATTEMPTS_FIELD,
    DLQ_GROUP_FIELD,
    DLQ_STREAM_ID_FIELD,
    DLQ_QUARANTINED_AT_FIELD,
    DLQ_ERROR_FIELD,
)


def format_entry(stream_id: str, fields: dict[str, Any]) -> str:
    """One line: ``<dlq id>\\t<reason=.. attempts=.. ...>\\t<event>``."""
    meta = " ".join(f"{name}={fields[name]}" for name in _META_FIELDS if name in fields)
    payload = fields.get(EVENT_FIELD, fields)
    return f"{stream_id}\t{meta or '-'}\t{payload}"


class Command(BaseCommand):
    help = "List quarantined CloudEvents on pyforge.events.dlq (canopy AD-8)."
    stealth_options = ("client",)

    def handle(self, *args: Any, **options: Any) -> None:
        client = options.get("client")
        if client is None:
            import redis  # noqa: PLC0415 -- optional runtime driver

            client = redis.Redis.from_url(
                settings.REDIS_BROKER_URL,
                decode_responses=True,
            )
        entries = list_quarantined(client)
        if not entries:
            self.stdout.write(f"{DLQ}: (empty)")
            return
        for stream_id, fields in entries:
            self.stdout.write(format_entry(stream_id, fields))
