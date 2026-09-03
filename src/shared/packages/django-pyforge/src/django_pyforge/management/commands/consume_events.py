"""Run one station's consumer on ``pyforge.events`` (Story 42.3, red-team A-1).

The chart ships this as a Deployment per station in ``events.consumers``:
``manage.py consume_events --station doctor``. Consumer group = station token
(AD-8). Each pass retries due pending entries then reads new ones; every
``--harvest-every`` passes it reclaims entries another consumer abandoned.
SIGTERM finishes the current pass and exits, so a handler is never cut off
mid-event by a rollout.
"""

from __future__ import annotations

import contextlib
import logging
import signal
import socket
import time
from typing import TYPE_CHECKING
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from django_pyforge.events import STATION_TOKENS
from django_pyforge.events import EventFabric
from django_pyforge.events.adapters import station_handler
from django_pyforge.events.adapters import subscriptions_for
from django_pyforge.events.fabric import Handler
from django_pyforge.events.fabric import handler_timeout_ms

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class _StopFlag:
    """Set by SIGTERM/SIGINT; the loop checks it after every pass."""

    def __init__(self) -> None:
        self.requested = False

    def _request(self, signum: int, _frame: Any) -> None:
        self.requested = True
        logger.info("consume_events stopping after this pass", extra={"signal": signum})

    @contextlib.contextmanager
    def installed(self) -> Iterator[None]:
        previous: dict[int, Any] = {}
        for sig in (signal.SIGTERM, signal.SIGINT):
            # Not the main thread (tests): no handler, the loop ends on --once.
            with contextlib.suppress(ValueError):
                previous[sig] = signal.signal(sig, self._request)
        try:
            yield
        finally:
            for sig, original in previous.items():
                signal.signal(sig, original)


def run_passes(
    fabric: EventFabric,
    station: str,
    consumer: str,
    handler: Handler,
    *,
    interval: float,
    harvest_every: int,
    once: bool,
    stop: _StopFlag,
) -> tuple[int, int, int]:
    """``(passes, handled, quarantined)`` after the loop ends."""
    passes = handled_total = moved_total = 0
    while True:
        passes += 1
        handled = fabric.consume(station, consumer, handler)
        handled_total += handled
        if once or (harvest_every and passes % harvest_every == 0):
            moved_total += fabric.harvest_poison(station, consumer)
        if once or stop.requested:
            return passes, handled_total, moved_total
        if handled == 0 and interval:
            time.sleep(interval)


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

            client = redis.Redis.from_url(
                settings.REDIS_BROKER_URL,
                decode_responses=True,
            )
        handler = options.get("handler") or station_handler(station)
        fabric = EventFabric(client)
        fabric.ensure_group(station)
        once = bool(options["once"])
        self.stdout.write(
            f"consuming pyforge.events as group={station} consumer={consumer} "
            f"types={sorted(subscriptions_for(station))} "
            f"handler_timeout_ms={handler_timeout_ms()}",
        )
        stop = _StopFlag()
        with stop.installed() if not once else contextlib.nullcontext():
            passes, handled, moved = run_passes(
                fabric,
                station,
                consumer,
                handler,
                interval=max(0.0, float(options["interval"])),
                harvest_every=max(0, int(options["harvest_every"])),
                once=once,
                stop=stop,
            )
        self.stdout.write(
            f"consume_events {station}: passes={passes} handled={handled} "
            f"quarantined={moved}",
        )
