"""Enumerate quarantined CloudEvents on pyforge.events.dlq."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand

from django_pyforge.events import DLQ
from django_pyforge.events import list_quarantined


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
            payload = fields.get("event", fields)
            self.stdout.write(f"{stream_id}\t{payload}")
