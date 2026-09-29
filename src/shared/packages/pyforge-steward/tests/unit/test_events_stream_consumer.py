"""Story 48.6 — EventsStreamConsumer and browser relay unit tests."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("django", reason="requires pyforge-steward[dashboard]")
pytest.importorskip("channels", reason="requires pyforge-steward[dashboard]")
pytest.importorskip("jwt", reason="django-pyforge assertion verification")

_PKG_ROOT = Path(__file__).resolve().parents[2]
_DJANGO_PYFORGE_SRC = _PKG_ROOT.parent / "django-pyforge" / "src"
if str(_DJANGO_PYFORGE_SRC) not in sys.path:
    sys.path.insert(0, str(_DJANGO_PYFORGE_SRC))

from django.conf import settings  # noqa: E402
from django_pyforge.assertion.schema import CLAIM_SUB  # noqa: E402
from django_pyforge.events.browser_relay import (
    matches_subject,  # noqa: E402
    tail_events,  # noqa: E402
)
from django_pyforge.events.constants import (
    EVENT_FIELD,  # noqa: E402
    EVENT_SCHEMAS,  # noqa: E402
    STREAM,  # noqa: E402
)
from django_pyforge.events.memory import MemoryRedis  # noqa: E402

if not settings.configured:
    settings.configure(
        REDIS_BROKER_URL="redis://memory",
        PYFORGE_ASSERTION_PUBLIC_KEY="configured",
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "pyforge-steward-events-stream-test",
            },
        },
    )

from pyforge.steward.dashboard.consumers import EventsStreamConsumer  # noqa: E402


def _run_started_event(*, subject: str) -> dict[str, object]:
    return {
        "specversion": "1.0",
        "id": f"evt-{subject}",
        "source": "/stations/warden",
        "type": "run.started",
        "dataschema": EVENT_SCHEMAS["run.started"],
        "data": {"run_id": "run-1", "station": "warden", "subject": subject},
    }


def test_matches_subject_requires_data_subject():
    event = _run_started_event(subject="alice")
    assert matches_subject(event, "alice")
    assert not matches_subject(event, "bob")
    assert not matches_subject({"type": "run.started"}, "alice")


def test_tail_events_yields_new_stream_entries_with_memory_redis():
    broker = MemoryRedis()

    async def _collect() -> list[str]:
        bodies: list[str] = []
        async for _sid, fields in tail_events(
            "redis://memory",
            last_id="$",
            stop=lambda: len(bodies) >= 2,
            client=broker,
        ):
            raw = fields.get(EVENT_FIELD)
            if raw:
                bodies.append(raw)
        return bodies

    async def _run() -> list[str]:
        task = asyncio.create_task(_collect())
        await asyncio.sleep(0.05)
        broker.xadd(
            STREAM,
            {EVENT_FIELD: json.dumps(_run_started_event(subject="alice"))},
        )
        broker.xadd(
            STREAM,
            {EVENT_FIELD: json.dumps(_run_started_event(subject="bob"))},
        )
        return await asyncio.wait_for(task, timeout=2.0)

    assert len(asyncio.run(_run())) == 2


def test_consumer_relay_filters_by_subject():
    broker = MemoryRedis()
    broker.xadd(
        STREAM,
        {EVENT_FIELD: json.dumps(_run_started_event(subject="alice"))},
    )
    broker.xadd(
        STREAM,
        {EVENT_FIELD: json.dumps(_run_started_event(subject="bob"))},
    )

    async def _run() -> list[dict]:
        forwarded: list[dict] = []
        async for _sid, fields in tail_events(
            "redis://memory",
            last_id="0",
            stop=lambda: len(forwarded) >= 1,
            client=broker,
        ):
            from django_pyforge.events.browser_relay import cloudevent_from_fields

            event = cloudevent_from_fields(fields)
            if event is None or not matches_subject(event, "alice"):
                continue
            forwarded.append(event)
        return forwarded

    forwarded = asyncio.run(_run())
    assert len(forwarded) == 1
    assert forwarded[0]["data"]["subject"] == "alice"


def test_consumer_connect_rejects_missing_token():
    async def _run() -> list[int]:
        consumer = EventsStreamConsumer()
        consumer.scope = {
            "type": "websocket",
            "path": "/ws/events/",
            "query_string": b"",
            "headers": [],
        }
        closed: list[int] = []

        async def _close(*, code: int) -> None:
            closed.append(code)

        consumer.close = _close  # type: ignore[method-assign]
        await consumer.connect()
        return closed

    assert asyncio.run(_run()) == [4401]


def test_relay_loop_sends_matching_cloudevent_frame(monkeypatch):
    broker = MemoryRedis()

    class _AsyncMemoryRedis:
        def __init__(self, memory: MemoryRedis) -> None:
            self._memory = memory

        def xread(self, streams, count=None, block=None):
            async def _read():
                return self._memory.xread(streams, count=count, block=block)

            return _read()

        async def aclose(self) -> None:
            return None

    async def _run() -> list[str]:
        consumer = EventsStreamConsumer()
        consumer._subject = "alice"
        consumer._stop_relay = False
        frames: list[str] = []

        async def _capture_send(*, text_data: str | None = None, **kwargs: object) -> None:
            if text_data:
                frames.append(text_data)
                consumer._stop_relay = True

        consumer.send = _capture_send  # type: ignore[method-assign]
        monkeypatch.setattr(
            "pyforge.steward.dashboard.consumers._broker_url",
            lambda: "redis://memory",
        )
        monkeypatch.setattr(
            "redis.asyncio.from_url",
            lambda *_args, **_kwargs: _AsyncMemoryRedis(broker),
        )
        relay = asyncio.create_task(consumer._relay_loop())
        await asyncio.sleep(0.05)
        broker.xadd(
            STREAM,
            {EVENT_FIELD: json.dumps(_run_started_event(subject="alice"))},
        )
        broker.xadd(
            STREAM,
            {EVENT_FIELD: json.dumps(_run_started_event(subject="bob"))},
        )
        await asyncio.wait_for(relay, timeout=2.0)
        return frames

    frames = asyncio.run(_run())
    assert len(frames) == 1
    payload = json.loads(frames[0])
    assert payload["data"]["subject"] == "alice"


def test_consumer_connect_accepts_verified_subject(monkeypatch):
    async def _run() -> tuple[bool, str | None]:
        consumer = EventsStreamConsumer()
        consumer.scope = {
            "type": "websocket",
            "path": "/ws/events/",
            "query_string": b"token=opaque",
            "headers": [],
        }
        accepted = False

        async def _accept() -> None:
            nonlocal accepted
            accepted = True

        async def _close(*, code: int) -> None:
            raise AssertionError(f"unexpected close {code}")

        def _verify(_token: str, *, audience: str, public_pem: str) -> dict[str, object]:
            assert audience == "mcp:events"
            assert public_pem == "configured"
            return {CLAIM_SUB: "alice"}

        monkeypatch.setattr(
            "pyforge.steward.dashboard.consumers.verify_assertion_claims",
            _verify,
        )
        monkeypatch.setattr(
            "pyforge.steward.dashboard.consumers._assertion_public_pem",
            lambda: "configured",
        )
        monkeypatch.setattr(
            "pyforge.steward.dashboard.consumers._broker_url",
            lambda: "redis://memory",
        )
        consumer.accept = _accept  # type: ignore[method-assign]
        consumer.close = _close  # type: ignore[method-assign]
        await consumer.connect()
        subject = consumer._subject
        await consumer.disconnect(1000)
        return accepted, subject

    accepted, subject = asyncio.run(_run())
    assert accepted
    assert subject == "alice"
