"""Run one station's consumer on ``pyforge.events`` (Story 42.3, red-team A-1).

The chart ships this as a Deployment per station in ``events.consumers``:
``manage.py consume_events --station doctor``. Consumer group = station token
(AD-8). Each pass retries due pending entries then reads new ones; every
``--harvest-every`` passes it reclaims entries another consumer abandoned.
SIGTERM finishes the current pass and exits, so a handler is never cut off
mid-event by a rollout.
"""

from __future__ import annotations

import logging
import signal
import socket
import time
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from django_pyforge.events import STATION_TOKENS
from django_pyforge.events import EventFabric
from django_pyforge.events.adapters import station_handler
from django_pyforge.events.adapters import subscriptions_for
from django_pyforge.events.fabric import handler_timeout_ms

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Consume pyforge.events for one station (consumer group = station)."
    # Injectable broker + handler, mirroring `list_event_dlq`'s `client`: a
    # test drives the real command rather than a re-implementation of it.
    stealth_options = ("client", "handler")

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--station",
            required=True,
            help="station token; also the consumer group name",
        )
        parser.add_argument(
            "--consumer",
            default=None,
            help="consumer name within the group (default: <station>-<hostname>)",
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=1.0,
            help="seconds to sleep after a pass that handled nothing",
        )
        parser.add_argument(
            "--harvest-every",
            type=int,
            default=30,
            dest="harvest_every",
            help="run harvest_poison every N passes (0 disables)",
        )
        parser.add_argument(
            "--once",
            action="store_true",
            help="one pass (retry due entries, read new, harvest) then exit",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        station = options["station"]
        if station not in STATION_TOKENS:
            msg = f"--station must be a station token, got {station!r}"
            raise CommandError(msg)
        consumer = options.get("consumer") or f"{station}-{socket.gethostname()}"
        client = options.get("client")
        if client is None:
            import redis  # noqa: PLC0415 -- optional runtime driver

            client = redis.Redis.from_url(settings.REDIS_BROKER_URL, decode_responses=True)
        handler = options.get("handler") or station_handler(station)
        fabric = EventFabric(client)
        fabric.ensure_group(station)
        interval = max(0.0, float(options["interval"]))
        harvest_every = max(0, int(options["harvest_every"]))
        once = bool(options["once"])

        stop = {"requested": False}

        def _request_stop(signum: int, _frame: Any) -> None:
            stop["requested"] = True
            logger.info("consume_events stopping after this pass", extra={"signal": signum})

        previous = {}
        if not once:
            for sig in (signal.SIGTERM, signal.SIGINT):
                try:
                    previous[sig] = signal.signal(sig, _request_stop)
                except ValueError:
                    # Not the main thread (tests); the loop then ends on --once only.
                    pass

        self.stdout.write(
            f"consuming pyforge.events as group={station} consumer={consumer} "
            f"types={sorted(subscriptions_for(station))} "
            f"handler_timeout_ms={handler_timeout_ms()}",
        )
        passes = 0
        handled_total = 0
        moved_total = 0
        try:
            while True:
                passes += 1
                handled = fabric.consume(station, consumer, handler)
                handled_total += handled
                if once or (harvest_every and passes % harvest_every == 0):
                    moved_total += fabric.harvest_poison(station, consumer)
                if once or stop["requested"]:
                    break
                if handled == 0 and interval:
                    time.sleep(interval)
        finally:
            for sig, original in previous.items():
                signal.signal(sig, original)
        self.stdout.write(
            f"consume_events {station}: passes={passes} handled={handled_total} quarantined={moved_total}",
        )
