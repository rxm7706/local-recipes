"""Run one station's consumer on ``pyforge.events`` (Story 42.3, red-team A-1).

The chart ships this as a Deployment per station in ``events.consumers``:
``manage.py consume_events --station doctor``. Consumer group = station token
(AD-8). Each pass retries due pending entries then reads new ones; every
``--harvest-every`` passes it reclaims entries another consumer abandoned.
SIGTERM stops the fabric from claiming or reading any further entry and
interrupts the idle wait; the handler already running always finishes, so a
rollout never cuts an event off mid-handler.
"""

from __future__ import annotations

import contextlib
import signal
import socket
import threading
from typing import TYPE_CHECKING
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from django_pyforge.events import STATION_TOKENS
from django_pyforge.events import EventFabric
from django_pyforge.events import connect_event_broker
from django_pyforge.events.adapters import station_handler
from django_pyforge.events.adapters import subscriptions_for
from django_pyforge.events.fabric import Handler
from django_pyforge.events.fabric import handler_timeout_ms

if TYPE_CHECKING:
    from collections.abc import Iterator


class StopFlag:
    """Set by SIGTERM/SIGINT (or a test); read by the fabric before each entry.

    A :class:`threading.Event`, so the idle wait is interruptible: the signal
    handler only sets it and does nothing else (no logging, no I/O -- it runs
    reentrantly inside whatever the main thread was doing).
    """

    def __init__(self) -> None:
        self._event = threading.Event()

    def request(self, *_args: Any) -> None:
        self._event.set()

    def is_set(self) -> bool:
        return self._event.is_set()

    @property
    def requested(self) -> bool:
        return self._event.is_set()

    def wait(self, timeout: float) -> bool:
        """Idle until ``timeout`` elapses or a stop is requested."""
        return self._event.wait(timeout)

    @contextlib.contextmanager
    def installed(self) -> Iterator[None]:
        previous: dict[int, Any] = {}
        for sig in (signal.SIGTERM, signal.SIGINT):
            # Not the main thread (tests): no handler, the loop ends on --once.
            with contextlib.suppress(ValueError):
                previous[sig] = signal.signal(sig, self.request)
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
    stop: StopFlag,
) -> tuple[int, int, int]:
    """``(passes, handled, quarantined)`` after the loop ends.

    The idle wait is taken only after a pass that handled nothing, and only
    for as long as no stop is requested.
    """
    passes = handled_total = moved_total = 0
    while True:
        passes += 1
        handled = fabric.consume(station, consumer, handler, should_stop=stop.is_set)
        handled_total += handled
        if once or (harvest_every and passes % harvest_every == 0):
            moved_total += fabric.harvest_poison(station, consumer)
        if once or stop.requested:
            return passes, handled_total, moved_total
        if handled == 0 and interval:
            stop.wait(interval)


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
            help="seconds to wait after a pass that handled nothing",
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
        subscribed = subscriptions_for(station)
        if not subscribed:
            # A consumer with nothing to react to would ACK the whole stream
            # and look healthy while doing nothing (SUBSCRIPTIONS is the map).
            msg = f"station {station!r} subscribes to no event type; nothing to consume"
            raise CommandError(msg)
        consumer = options.get("consumer") or f"{station}-{socket.gethostname()}"
        client = options.get("client")
        if client is None:
            # AD-10: the fabric binds to redis-broker and refuses a URL shared
            # with redis-cache.
            fabric = connect_event_broker(
                settings.REDIS_BROKER_URL,
                settings.REDIS_CACHE_URL,
            )
        else:
            fabric = EventFabric(client)
        handler = options.get("handler") or station_handler(station)
        fabric.ensure_group(station)
        once = bool(options["once"])
        self.stdout.write(
            f"consuming pyforge.events as group={station} consumer={consumer} "
            f"types={sorted(subscribed)} "
            f"handler_timeout_ms={handler_timeout_ms()}",
        )
        stop = StopFlag()
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
