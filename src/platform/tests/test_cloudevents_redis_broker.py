"""Steward 24.1 / 40.2 / 42.3: CloudEvents 1.0 on redis-broker Streams.

Story 42.3 (red-team A-1 / A-2 / A-4 / A-5, directive R-9) adds the delivery
semantics: attempts counted on the XPENDING delivery counter, exponential
backoff, DLQ for a well-formed event after N failures with its last error,
a real ``min_idle_time`` on harvest, the ``consume_events`` runner, the
Warden -> Doctor -> Mason vocabulary, and ``traceparent`` on the envelope.
"""

from __future__ import annotations

import json
import logging
import shutil
import signal
import subprocess
import time
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from celery import shared_task
from django.core.management import call_command
from django.core.management.base import CommandError
from django.http import HttpResponse
from django.urls import path
from django_pyforge.events import DLQ
from django_pyforge.events import EVENT_FIELD
from django_pyforge.events import EVENT_SCHEMAS
from django_pyforge.events import EVENT_TYPES
from django_pyforge.events import EXT_TRACEPARENT
from django_pyforge.events import STREAM
from django_pyforge.events import SUBSCRIPTIONS
from django_pyforge.events import DataschemaRequiredError
from django_pyforge.events import EventBrokerConfigError
from django_pyforge.events import EventFabric
from django_pyforge.events import MemoryRedis
from django_pyforge.events import PayloadShapeError
from django_pyforge.events import RecipeAuditAdapter
from django_pyforge.events import TraceparentFormatError
from django_pyforge.events import adapter_for
from django_pyforge.events import backoff_ms
from django_pyforge.events import connect_event_broker
from django_pyforge.events import current_traceparent
from django_pyforge.events import handler_timeout_ms
from django_pyforge.events import list_quarantined
from django_pyforge.events import max_attempts
from django_pyforge.events import register_adapter
from django_pyforge.events import station_handler
from django_pyforge.events import trace_headers
from django_pyforge.events import trace_id_of
from django_pyforge.events.constants import APPLIED_PREFIX
from django_pyforge.events.constants import DLQ_ATTEMPTS_FIELD
from django_pyforge.events.constants import DLQ_ERROR_FIELD
from django_pyforge.events.constants import DLQ_REASON_EXHAUSTED
from django_pyforge.events.constants import DLQ_REASON_FIELD
from django_pyforge.events.constants import DLQ_REASON_UNPARSEABLE
from django_pyforge.events.constants import EVENT_BACKOFF_BASE_MS_DEFAULT
from django_pyforge.events.constants import EVENT_MAX_ATTEMPTS_DEFAULT
from django_pyforge.events.constants import EXT_GIT_SHA
from django_pyforge.events.constants import EXT_SBOM_PURL
from django_pyforge.events.constants import EXT_SPEC_ID
from django_pyforge.events.fabric import applied_key
from django_pyforge.events.fabric import last_error_key
from django_pyforge.tasks import SUBJECT_HEADER
from django_pyforge.tasks import enqueue_supervised_run

GROUP = "warden"
CONSUMER = "warden-1"
DATASCHEMA = "https://example.invalid/schemas/recipe-audit.json"
BROKER_URL = "redis://broker.example.invalid:6379/0"
CACHE_URL = "redis://cache.example.invalid:6379/0"
TRACE_ID = "0af7651916cd43dd8448eb211c80319c"
TRACEPARENT = f"00-{TRACE_ID}-b7ad6b7169203331-01"
_DELIVERY_ENV = (
    "DJANGO_PYFORGE_EVENT_MAX_ATTEMPTS",
    "DJANGO_PYFORGE_EVENT_BACKOFF_BASE_MS",
    "DJANGO_PYFORGE_EVENT_BACKOFF_MAX_MS",
    "DJANGO_PYFORGE_EVENT_HANDLER_TIMEOUT_MS",
)


class CountingRedis(MemoryRedis):
    def __init__(self) -> None:
        super().__init__()
        self.xadd_count = 0
        self.xadd_names: list[str] = []
        self.xautoclaim_calls: list[tuple[str, str, str, int]] = []

    def xadd(self, name: str, fields: dict[str, object], **kwargs: object) -> str:
        self.xadd_count += 1
        self.xadd_names.append(name)
        return super().xadd(name, fields, **kwargs)

    def xautoclaim(
        self,
        name: str,
        groupname: str,
        consumername: str,
        min_idle_time: int,
        start_id: str = "0-0",
        count: int | None = None,
        **kwargs: object,
    ) -> tuple[str, list[tuple[str, dict[str, str]]]]:
        self.xautoclaim_calls.append((name, groupname, consumername, min_idle_time))
        return super().xautoclaim(
            name,
            groupname,
            consumername,
            min_idle_time,
            start_id,
            count,
        )


def _envelope(**overrides: object) -> dict:
    body: dict = {
        "type": "recipe.audit.failed",
        "source": "/stations/warden",
        "dataschema": DATASCHEMA,
        EXT_SPEC_ID: "spec-24-1-cloudevents-on-redis-broker",
        EXT_GIT_SHA: "deadbeef",
        EXT_SBOM_PURL: "pkg:pypi/django-pyforge@0.1.0",
    }
    body.update(overrides)
    return body


def _pending(broker: Any, group: str, consumer: str | None = None) -> list[dict[str, Any]]:
    """XPENDING rows -- the delivery counter and idle time, without
    re-delivering (unlike an XREADGROUP over the history)."""
    kwargs: dict[str, Any] = {"consumername": consumer} if consumer else {}
    return [dict(row) for row in broker.xpending_range(STREAM, group, "-", "+", 100, **kwargs)]


def _pending_ids(broker: Any, group: str, consumer: str) -> list[str]:
    return [str(row["message_id"]) for row in _pending(broker, group, consumer)]


@pytest.fixture
def default_delivery_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the documented defaults so the schedule under test is the shipped one."""
    for name in _DELIVERY_ENV:
        monkeypatch.delenv(name, raising=False)


def test_consumer_down_delivers_once_on_return() -> None:
    broker = MemoryRedis()
    fabric = EventFabric(broker)
    fabric.ensure_group(GROUP)
    event_id = fabric.publish(_envelope())
    runs: list[str] = []
    fabric.consume(GROUP, CONSUMER, lambda event: runs.append(event["id"]))
    fabric.consume(GROUP, CONSUMER, lambda event: runs.append(event["id"]))
    assert runs == [event_id]


def test_no_double_apply_on_pending_redelivery() -> None:
    broker = MemoryRedis()
    fabric = EventFabric(broker)
    fabric.ensure_group(GROUP)
    event_id = fabric.publish(_envelope())
    delivered = broker.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=1)
    _stream, messages = delivered[0]
    _msg_id, fields = messages[0]
    payload = json.loads(fields[EVENT_FIELD])
    runs: list[str] = []

    def handler(event: dict) -> None:
        runs.append(event["id"])

    handler(payload)
    broker.set(applied_key(event_id), "1")
    # The entry is pending under CONSUMER from the read above; the retry pass
    # re-claims it once its backoff has elapsed and finds it already applied.
    broker.advance_ms(backoff_ms(1))
    fabric.consume(GROUP, CONSUMER, handler)
    assert runs == [event_id]
    assert _pending_ids(broker, GROUP, CONSUMER) == []


def test_ack_only_after_handler_returns() -> None:
    """Never: a consumer that ACKs before the handler returns."""
    broker = MemoryRedis()
    fabric = EventFabric(broker)
    fabric.ensure_group(GROUP)
    fabric.publish(_envelope())
    seen: dict[str, list[str]] = {}

    def handler(event: dict) -> None:
        seen["during"] = _pending_ids(broker, GROUP, CONSUMER)

    fabric.consume(GROUP, CONSUMER, handler)
    assert len(seen["during"]) == 1
    assert _pending_ids(broker, GROUP, CONSUMER) == []


def test_unparseable_entry_is_quarantined_on_first_sight_with_error() -> None:
    broker = CountingRedis()
    fabric = EventFabric(broker)
    fabric.ensure_group(GROUP)
    broker.xadd(STREAM, {EVENT_FIELD: "not-cloudevents-json"})
    good_id = fabric.publish(_envelope())
    runs: list[str] = []
    fabric.consume(GROUP, CONSUMER, lambda event: runs.append(event["id"]))
    assert runs == [good_id]
    assert _pending_ids(broker, GROUP, CONSUMER) == []
    quarantined = list_quarantined(broker)
    assert len(quarantined) == 1
    _qid, qfields = quarantined[0]
    assert qfields[EVENT_FIELD] == "not-cloudevents-json"
    assert qfields[DLQ_REASON_FIELD] == DLQ_REASON_UNPARSEABLE
    assert qfields[DLQ_ERROR_FIELD]
    more: list[str] = []
    fabric.consume(GROUP, CONSUMER, lambda event: more.append(event["id"]))
    assert more == []


def test_well_formed_poison_lands_in_dlq_after_max_attempts_with_last_error(
    default_delivery_env: None,
) -> None:
    """CAP-8 success clause: a poisoned event lands in the DLQ instead of
    retrying forever. Fails without Story 42.3 -- the old ``_apply`` deleted
    the applied key, never ACKed, and re-ran the handler on every call."""
    broker = MemoryRedis()
    fabric = EventFabric(broker)
    fabric.ensure_group(GROUP)
    event_id = fabric.publish(_envelope(data={"package": "demo"}))
    calls: list[str] = []

    def doctor_handler(event: dict) -> None:
        calls.append(event["id"])
        raise KeyError("reason")

    ceiling = max_attempts()
    assert ceiling == EVENT_MAX_ATTEMPTS_DEFAULT
    assert fabric.consume(GROUP, CONSUMER, doctor_handler) == 0
    assert calls == [event_id]
    (stream_id,) = _pending_ids(broker, GROUP, CONSUMER)
    assert broker.get(last_error_key(stream_id)) == "KeyError: 'reason'"
    assert broker.get(applied_key(event_id)) is None
    for attempts in range(1, ceiling):
        assert len(calls) == attempts
        assert _pending(broker, GROUP, CONSUMER)[0]["times_delivered"] == attempts
        broker.advance_ms(backoff_ms(attempts))
        fabric.consume(GROUP, CONSUMER, doctor_handler)
    assert len(calls) == ceiling

    quarantined = list_quarantined(broker)
    assert len(quarantined) == 1
    _qid, fields = quarantined[0]
    assert json.loads(fields[EVENT_FIELD])["id"] == event_id
    assert fields[DLQ_REASON_FIELD] == DLQ_REASON_EXHAUSTED
    assert fields[DLQ_ERROR_FIELD] == "KeyError: 'reason'"
    assert fields[DLQ_ATTEMPTS_FIELD] == str(ceiling)
    assert fields["group"] == GROUP
    assert _pending(broker, GROUP) == []
    assert broker.get(applied_key(event_id)) is None

    broker.advance_ms(60 * 60 * 1000)
    for _ in range(3):
        fabric.consume(GROUP, CONSUMER, doctor_handler)
    assert len(calls) == ceiling


def test_retry_delays_follow_documented_backoff_and_consumer_does_not_spin(
    default_delivery_env: None,
) -> None:
    schedule = [backoff_ms(attempts) for attempts in range(1, max_attempts())]
    assert schedule == [1_000, 2_000, 4_000, 8_000]
    assert backoff_ms(1) == EVENT_BACKOFF_BASE_MS_DEFAULT
    assert backoff_ms(40) == 60_000

    broker = MemoryRedis()
    fabric = EventFabric(broker)
    fabric.ensure_group(GROUP)
    fabric.publish(_envelope())
    calls: list[float] = []

    def handler(event: dict) -> None:
        calls.append(1.0)
        raise RuntimeError("still broken")

    fabric.consume(GROUP, CONSUMER, handler)
    assert len(calls) == 1
    for _ in range(25):
        fabric.consume(GROUP, CONSUMER, handler)
    assert len(calls) == 1, "a failing event must not be re-attempted before its backoff"
    for attempts, delay in enumerate(schedule, start=1):
        broker.advance_ms(delay // 2)
        fabric.consume(GROUP, CONSUMER, handler)
        assert len(calls) == attempts, f"attempt {attempts + 1} ran before {delay} ms elapsed"
        broker.advance_ms(delay - delay // 2)
        fabric.consume(GROUP, CONSUMER, handler)
        assert len(calls) == attempts + 1, f"attempt {attempts + 1} did not run at {delay} ms"
    assert len(list_quarantined(broker)) == 1


def test_harvest_claims_only_entries_idle_past_threshold(default_delivery_env: None) -> None:
    broker = CountingRedis()
    fabric = EventFabric(broker)
    fabric.ensure_group(GROUP)
    ids = [fabric.publish(_envelope()) for _ in range(2)]
    broker.xadd(STREAM, {EVENT_FIELD: "not-cloudevents-json"})
    # A consumer that read three entries and died before ACKing any.
    broker.xreadgroup(GROUP, "dead-1", {STREAM: ">"}, count=10)
    assert len(_pending_ids(broker, GROUP, "dead-1")) == 3

    threshold = handler_timeout_ms()
    assert threshold == 5 * 60 * 1000
    assert fabric.harvest_poison(GROUP, CONSUMER) == 0
    assert broker.xautoclaim_calls == [(STREAM, GROUP, CONSUMER, threshold)]
    assert len(_pending_ids(broker, GROUP, "dead-1")) == 3, "harvest stole live messages"
    assert list_quarantined(broker) == []

    broker.advance_ms(threshold - 1_000)
    assert fabric.harvest_poison(GROUP, CONSUMER) == 0
    assert len(_pending_ids(broker, GROUP, "dead-1")) == 3

    broker.advance_ms(1_000)
    assert fabric.harvest_poison(GROUP, CONSUMER) == 1
    assert _pending_ids(broker, GROUP, "dead-1") == []
    (_qid, qfields), = list_quarantined(broker)
    assert qfields[EVENT_FIELD] == "not-cloudevents-json"
    assert qfields[DLQ_REASON_FIELD] == DLQ_REASON_UNPARSEABLE
    assert qfields[DLQ_ERROR_FIELD]
    # The well-formed entries now sit under the harvester with the claim
    # counted as a delivery; its retry pass runs them after that backoff.
    rows = _pending(broker, GROUP, CONSUMER)
    assert {row["times_delivered"] for row in rows} == {2}
    runs: list[str] = []
    fabric.consume(GROUP, CONSUMER, lambda event: runs.append(event["id"]))
    assert runs == []
    broker.advance_ms(backoff_ms(2))
    fabric.consume(GROUP, CONSUMER, lambda event: runs.append(event["id"]))
    assert sorted(runs) == sorted(ids)
    assert _pending(broker, GROUP) == []


def test_harvest_quarantines_exhausted_entry_with_recorded_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Never: a DLQ write without the error recorded -- even when the consumer
    that saw the error is gone and the harvest is what quarantines it."""
    monkeypatch.setenv("DJANGO_PYFORGE_EVENT_MAX_ATTEMPTS", "2")
    broker = MemoryRedis()
    fabric = EventFabric(broker)
    fabric.ensure_group(GROUP)
    event_id = fabric.publish(_envelope())

    def crashing(event: dict) -> None:
        raise RuntimeError("doctor handler crashed")

    fabric.consume(GROUP, "dead-1", crashing)
    assert len(_pending_ids(broker, GROUP, "dead-1")) == 1
    broker.advance_ms(handler_timeout_ms() + 1)
    assert fabric.harvest_poison(GROUP, CONSUMER) == 1
    (_qid, fields), = list_quarantined(broker)
    assert json.loads(fields[EVENT_FIELD])["id"] == event_id
    assert fields[DLQ_REASON_FIELD] == DLQ_REASON_EXHAUSTED
    assert fields[DLQ_ERROR_FIELD] == "RuntimeError: doctor handler crashed"
    assert fields[DLQ_ATTEMPTS_FIELD] == "2"
    assert _pending(broker, GROUP) == []


def test_event_vocabulary_registered_with_dataschemas() -> None:
    chain = (
        "recipe.audit.failed",
        "remedy.requested",
        "recipe.rebuild.requested",
        "remedy.completed",
    )
    for event_type in chain:
        assert event_type in EVENT_TYPES
        assert EVENT_SCHEMAS[event_type].startswith("urn:pyforge:schema:events:")
        adapter = adapter_for(event_type)
        assert adapter is not None
        assert adapter.event_type == event_type
    assert {"recipe.audit.failed", "remedy.completed"} <= SUBSCRIPTIONS["doctor"]
    assert {"remedy.requested", "recipe.rebuild.requested"} <= SUBSCRIPTIONS["mason"]
    for station, types in SUBSCRIPTIONS.items():
        assert types <= EVENT_TYPES, station

    broker = MemoryRedis()
    fabric = EventFabric(broker)
    for event_type in chain:
        fabric.publish(_envelope(type=event_type, dataschema=EVENT_SCHEMAS[event_type]))
    landed = [json.loads(row[1][EVENT_FIELD])["type"] for row in broker.xrange(STREAM, "-", "+")]
    assert landed == list(chain)


def test_station_handler_routes_subscribed_types_only() -> None:
    seen: list[str] = []

    class SpyAudit(RecipeAuditAdapter):
        def apply(self, event: dict) -> None:
            seen.append(event["id"])

    register_adapter(SpyAudit())
    try:
        doctor = station_handler("doctor")
        doctor({"type": "recipe.audit.failed", "id": "a", "data": {"package": "p", "reason": "r"}})
        doctor({"type": "remedy.requested", "id": "b", "data": {"package": "p", "remedy": "x"}})
        assert seen == ["a"]
        with pytest.raises(PayloadShapeError):
            doctor({"type": "recipe.audit.failed", "id": "c", "data": {"package": "p"}})
        mason = station_handler("mason")
        mason({"type": "recipe.audit.failed", "id": "d", "data": {"package": "p", "reason": "r"}})
        assert seen == ["a"]
        with pytest.raises(PayloadShapeError):
            mason({"type": "remedy.requested", "id": "e", "data": {}})
    finally:
        register_adapter(RecipeAuditAdapter())
    with pytest.raises(ValueError, match="station token"):
        station_handler("nope")


def test_consume_events_command_runs_one_pass_for_station() -> None:
    _ensure_django()
    broker = MemoryRedis()
    fabric = EventFabric(broker)
    fabric.ensure_group("doctor")
    fabric.publish(_envelope(data={"package": "demo", "reason": "cve"}))
    fabric.publish(_envelope(type="remedy.requested", data={"package": "demo", "remedy": "bump"}))
    broker.xadd(STREAM, {EVENT_FIELD: "garbage"})
    out = StringIO()
    call_command(
        "consume_events",
        station="doctor",
        consumer="doctor-test",
        client=broker,
        once=True,
        stdout=out,
    )
    text = out.getvalue()
    assert "group=doctor consumer=doctor-test" in text
    assert "handled=2" in text
    assert "quarantined=0" in text
    assert _pending(broker, "doctor") == []
    assert len(list_quarantined(broker)) == 1
    # A station outside the tokens is refused before any Redis call.
    with pytest.raises(CommandError, match="station token"):
        call_command("consume_events", station="nope", client=broker, once=True, stdout=StringIO())
    # Retries go through the same command: a failing handler keeps the entry
    # pending, and a later pass after the backoff quarantines it.
    fabric.publish(_envelope(data={"package": "demo", "reason": "cve"}))
    calls: list[int] = []

    def failing(event: dict) -> None:
        calls.append(1)
        raise RuntimeError("no remedy")

    for attempts in range(1, max_attempts() + 1):
        call_command(
            "consume_events",
            station="doctor",
            consumer="doctor-test",
            client=broker,
            handler=failing,
            once=True,
            stdout=StringIO(),
        )
        assert len(calls) == attempts
        broker.advance_ms(backoff_ms(attempts))
    assert len(list_quarantined(broker)) == 2
    assert _pending(broker, "doctor") == []


def test_traceparent_rides_envelope_and_binds_consumer_context() -> None:
    structlog = pytest.importorskip("structlog")
    broker = MemoryRedis()
    fabric = EventFabric(broker)
    fabric.ensure_group(GROUP)
    fabric.publish(_envelope(traceparent=TRACEPARENT))
    payload = json.loads(broker.xrange(STREAM, "-", "+")[0][1][EVENT_FIELD])
    assert payload[EXT_TRACEPARENT] == TRACEPARENT
    seen: dict[str, Any] = {}

    def handler(event: dict) -> None:
        seen["traceparent"] = current_traceparent()
        seen["headers"] = trace_headers()
        seen["context"] = dict(structlog.contextvars.get_contextvars())

    fabric.consume(GROUP, CONSUMER, handler)
    assert trace_id_of(seen["traceparent"]) == TRACE_ID
    assert trace_id_of(seen["headers"]["traceparent"]) == TRACE_ID
    assert seen["context"]["trace_id"] == TRACE_ID
    assert seen["context"]["traceparent"] == TRACEPARENT
    assert "trace_id" not in structlog.contextvars.get_contextvars()
    with pytest.raises(TraceparentFormatError):
        fabric.publish(_envelope(traceparent="not-a-trace"))
    assert len(broker.xrange(STREAM, "-", "+")) == 1


_PROBE: dict[str, Any] = {}


def _publish_probe_view(request: Any) -> HttpResponse:
    fabric = EventFabric(_PROBE["broker"])
    event_id = fabric.publish(_envelope(data={"package": "demo", "reason": "cve"}))
    return HttpResponse(event_id)


urlpatterns = [
    path("publish-probe/", _publish_probe_view, name="publish_probe"),
]


@shared_task(name="tests.cloudevents.react")
def _react(event_id: str) -> str:
    logger = logging.getLogger("django_pyforge.tests.react")
    structlog = pytest.importorskip("structlog")
    _PROBE["task_headers"] = dict(_react.request.headers or {})
    _PROBE["task_context"] = dict(structlog.contextvars.get_contextvars())
    logger.info("consumer_reaction", extra={"event_id": event_id})
    return event_id


@pytest.mark.django_db
def test_trace_id_from_request_reaches_celery_headers_and_structlog(client, settings) -> None:
    """AC: an event published from a request with a ``traceparent``, handled by
    a consumer that enqueues Celery work, carries the same trace id into the
    task headers and the structlog context."""
    settings.ROOT_URLCONF = __name__
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    broker = MemoryRedis()
    _PROBE.clear()
    _PROBE["broker"] = broker
    EventFabric(broker).ensure_group("doctor")

    response = client.get("/publish-probe/", HTTP_TRACEPARENT=TRACEPARENT)
    assert response.status_code == 200
    payload = json.loads(broker.xrange(STREAM, "-", "+")[0][1][EVENT_FIELD])
    assert trace_id_of(payload.get(EXT_TRACEPARENT)) == TRACE_ID, payload

    def doctor_handler(event: dict) -> None:
        _react.apply_async(args=[event["id"]], headers=trace_headers())

    assert EventFabric(broker).consume("doctor", "doctor-test", doctor_handler) == 1
    assert trace_id_of(_PROBE["task_headers"].get("traceparent")) == TRACE_ID
    assert _PROBE["task_context"].get("trace_id") == TRACE_ID


def test_enqueue_supervised_run_carries_traceparent_header(monkeypatch: pytest.MonkeyPatch) -> None:
    from django_pyforge import tasks  # noqa: PLC0415

    captured: dict[str, Any] = {}

    def fake_apply_async(**kwargs: Any) -> str:
        captured.update(kwargs)
        return "queued"

    monkeypatch.setattr(tasks.execute_supervised_run, "apply_async", fake_apply_async)
    from django_pyforge.events import bound_trace  # noqa: PLC0415

    with bound_trace(TRACEPARENT):
        enqueue_supervised_run("run-1", "warden", "audit", {}, subject="agent-1", task_id="task-1")
    assert captured["headers"][SUBJECT_HEADER] == "agent-1"
    assert trace_id_of(captured["headers"]["traceparent"]) == TRACE_ID
    captured.clear()
    enqueue_supervised_run("run-2", "warden", "audit", {}, subject="agent-1", task_id="task-2")
    # Outside the bound trace the header is whatever trace (if any) this test
    # process runs under -- never the one from the previous enqueue.
    assert captured["headers"][SUBJECT_HEADER] == "agent-1"
    assert trace_id_of(captured["headers"].get("traceparent")) != TRACE_ID


def test_enumerate_dlq_returns_quarantined_and_empty() -> None:
    _ensure_django()
    broker = MemoryRedis()
    assert list_quarantined(broker) == []
    empty = StringIO()
    call_command("list_event_dlq", client=broker, stdout=empty)
    assert "(empty)" in empty.getvalue()
    broker.xadd(DLQ, {EVENT_FIELD: '{"specversion":"1.0"}'})
    listed = list_quarantined(broker)
    assert len(listed) == 1
    out = StringIO()
    call_command("list_event_dlq", client=broker, stdout=out)
    assert listed[0][0] in out.getvalue()


def test_broker_only_never_writes_cache_and_refuses_same_url() -> None:
    spies: dict[str, CountingRedis] = {}

    def factory(url: str) -> CountingRedis:
        client = CountingRedis()
        spies[url] = client
        return client

    cache = CountingRedis()
    fabric = connect_event_broker(BROKER_URL, CACHE_URL, client_factory=factory)
    fabric.cache = cache
    fabric.publish(_envelope())
    assert CACHE_URL not in spies
    assert spies[BROKER_URL].xadd_count == 1
    assert spies[BROKER_URL].xadd_names == [STREAM]
    assert cache.xadd_count == 0
    with pytest.raises(EventBrokerConfigError):
        connect_event_broker(BROKER_URL, BROKER_URL, client_factory=factory)


def test_publish_without_dataschema_raises_and_stream_unchanged() -> None:
    broker = MemoryRedis()
    fabric = EventFabric(broker)
    before = broker.xrange(STREAM, "-", "+")
    with pytest.raises(DataschemaRequiredError):
        fabric.publish(_envelope(dataschema=""))
    with pytest.raises(DataschemaRequiredError):
        fabric.publish(
            {
                "type": "recipe.audit.failed",
                "source": "/stations/warden",
                EXT_SPEC_ID: "spec-24-1",
                EXT_GIT_SHA: "deadbeef",
                EXT_SBOM_PURL: "pkg:pypi/django-pyforge@0.1.0",
            },
        )
    assert broker.xrange(STREAM, "-", "+") == before


def test_jira_optional_envelope_lands_on_stream() -> None:
    broker = MemoryRedis()
    fabric = EventFabric(broker)
    event_id = fabric.publish(_envelope())
    rows = broker.xrange(STREAM, "-", "+")
    assert len(rows) == 1
    payload = json.loads(rows[0][1][EVENT_FIELD])
    assert payload["specversion"] == "1.0"
    assert payload["id"] == event_id
    assert payload[EXT_SPEC_ID]
    assert payload[EXT_GIT_SHA]
    assert payload[EXT_SBOM_PURL]
    assert "workitemid" not in payload
    assert "jira" not in payload
    assert broker.get(f"{APPLIED_PREFIX}{event_id}") is None
    with_item = fabric.publish(_envelope(workitemid="PYF-24-1"))
    rows = broker.xrange(STREAM, "-", "+")
    payloads = [json.loads(row[1][EVENT_FIELD]) for row in rows]
    tagged = next(item for item in payloads if item["id"] == with_item)
    assert tagged["workitemid"] == "PYF-24-1"
    assert "jira" not in tagged


def test_applied_key_carries_ttl() -> None:
    broker = MemoryRedis()
    fabric = EventFabric(broker)
    key = applied_key("event-1")
    assert fabric._mark_applied(key)  # noqa: SLF001 -- TTL contract
    assert broker.ttl(key) > 0


def _ensure_django() -> None:
    import django  # noqa: PLC0415

    django.setup()


def test_execute_supervised_run_leaves_no_celery_result_key(tmp_path) -> None:
    pytest.importorskip("pytest_django")
    _ensure_django()
    from django.conf import settings  # noqa: PLC0415
    from django.core.management import call_command as django_call_command  # noqa: PLC0415

    django_call_command("migrate", verbosity=0, interactive=False)
    redis_server = shutil.which("redis-server")
    if redis_server is None:
        pytest.skip("redis-server not on PATH (platform-dev env)")

    data_dir = tmp_path / "redis-data"
    data_dir.mkdir()
    port = 16379 + (int(time.time()) % 1000)
    proc = subprocess.Popen(  # noqa: S603
        [
            redis_server,
            "--port",
            str(port),
            "--dir",
            str(data_dir),
            "--save",
            "",
            "--appendonly",
            "no",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(0.3)
        broker_url = f"redis://127.0.0.1:{port}/0"
        settings.CELERY_BROKER_URL = broker_url
        settings.CELERY_RESULT_BACKEND = broker_url
        settings.CELERY_TASK_IGNORE_RESULT = True
        settings.CELERY_TASK_ALWAYS_EAGER = True
        settings.CELERY_TASK_EAGER_PROPAGATES = True

        import redis  # noqa: PLC0415

        client = redis.Redis.from_url(broker_url, decode_responses=True)

        def _noop_runner(_payload: dict) -> dict:
            return {"ok": True}

        import django_pyforge.supervisor as supervisor  # noqa: PLC0415
        from django_pyforge.tasks import execute_supervised_run  # noqa: PLC0415

        original = supervisor.lookup_runner
        supervisor.lookup_runner = lambda _station, _tool: _noop_runner
        try:
            from django_pyforge.models import RunState  # noqa: PLC0415

            run = RunState.objects.create(
                station="warden",
                status=RunState.Status.PENDING,
            )
            execute_supervised_run.delay(str(run.pk), "warden", "noop", {})
        finally:
            supervisor.lookup_runner = original

        meta_keys = [key for key in client.keys("celery-task-meta-*")]
        assert meta_keys == []
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)


def _start_redis(data_dir: Path, *, appendonly: bool, port: int) -> subprocess.Popen:
    redis_server = shutil.which("redis-server")
    assert redis_server is not None
    args = [
        redis_server,
        "--port",
        str(port),
        "--dir",
        str(data_dir),
        "--save",
        "",
    ]
    if appendonly:
        args.extend(["--appendonly", "yes", "--appendfsync", "everysec"])
    else:
        args.extend(["--appendonly", "no"])
    proc = subprocess.Popen(  # noqa: S603
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(0.4)
    return proc


def _stop_redis(proc: subprocess.Popen) -> None:
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def test_real_redis_retry_backoff_dlq_and_harvest(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The delivery semantics against a real redis-server (platform-dev env):
    XPENDING/XCLAIM/XAUTOCLAIM as Redis actually answers them, not the
    in-memory model."""
    if shutil.which("redis-server") is None:
        pytest.skip("redis-server not on PATH (platform-dev env)")
    monkeypatch.setenv("DJANGO_PYFORGE_EVENT_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("DJANGO_PYFORGE_EVENT_BACKOFF_BASE_MS", "100")
    monkeypatch.setenv("DJANGO_PYFORGE_EVENT_BACKOFF_MAX_MS", "1000")
    monkeypatch.setenv("DJANGO_PYFORGE_EVENT_HANDLER_TIMEOUT_MS", "300")

    import redis  # noqa: PLC0415

    data_dir = tmp_path / "broker"
    data_dir.mkdir()
    port = 18379 + (int(time.time()) % 1000)
    proc = _start_redis(data_dir, appendonly=False, port=port)
    try:
        client = redis.Redis.from_url(f"redis://127.0.0.1:{port}/0", decode_responses=True)
        fabric = EventFabric(client)
        fabric.ensure_group(GROUP)
        event_id = fabric.publish(_envelope(traceparent=TRACEPARENT))
        calls: list[float] = []

        def handler(event: dict) -> None:
            assert event[EXT_TRACEPARENT] == TRACEPARENT
            calls.append(time.monotonic())
            raise RuntimeError("real redis boom")

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not client.xlen(DLQ):
            fabric.consume(GROUP, CONSUMER, handler)
            time.sleep(0.02)
        assert len(calls) == 3, calls
        assert calls[1] - calls[0] >= 0.1
        assert calls[2] - calls[1] >= 0.2
        (_qid, fields), = list_quarantined(client)
        assert json.loads(fields[EVENT_FIELD])["id"] == event_id
        assert fields[DLQ_REASON_FIELD] == DLQ_REASON_EXHAUSTED
        assert fields[DLQ_ERROR_FIELD] == "RuntimeError: real redis boom"
        assert fields[DLQ_ATTEMPTS_FIELD] == "3"
        assert client.xpending(STREAM, GROUP)["pending"] == 0
        assert not client.exists(applied_key(event_id))

        # Harvest: entries a dead consumer abandoned are reclaimed only once
        # idle past the handler timeout; the unparseable one is quarantined,
        # the good one is retried by the harvester after its backoff.
        client.xadd(STREAM, {EVENT_FIELD: "not-json"})
        good_id = fabric.publish(_envelope())
        client.xreadgroup(GROUP, "dead-1", {STREAM: ">"}, count=10)
        assert client.xpending(STREAM, GROUP)["pending"] == 2
        assert fabric.harvest_poison(GROUP, CONSUMER) == 0
        assert client.xpending(STREAM, GROUP)["pending"] == 2
        time.sleep(0.35)
        assert fabric.harvest_poison(GROUP, CONSUMER) == 1
        assert client.xlen(DLQ) == 2
        rows = client.xpending_range(STREAM, GROUP, "-", "+", 10, consumername=CONSUMER)
        assert len(rows) == 1
        assert rows[0]["times_delivered"] == 2
        runs: list[str] = []
        fabric.consume(GROUP, CONSUMER, lambda event: runs.append(event["id"]))
        assert runs == [], "claimed entry re-attempted before its backoff"
        time.sleep(0.25)
        fabric.consume(GROUP, CONSUMER, lambda event: runs.append(event["id"]))
        assert runs == [good_id]
        assert client.xpending(STREAM, GROUP)["pending"] == 0
    finally:
        _stop_redis(proc)


@pytest.mark.parametrize("appendonly", [True, False])
def test_broker_restart_durability(tmp_path, appendonly: bool) -> None:
    if shutil.which("redis-server") is None:
        pytest.skip("redis-server not on PATH (platform-dev env)")

    import redis  # noqa: PLC0415

    data_dir = tmp_path / "broker-aof"
    data_dir.mkdir()
    port = 17379 + (int(time.time()) % 1000)
    url = f"redis://127.0.0.1:{port}/0"

    proc = _start_redis(data_dir, appendonly=appendonly, port=port)
    try:
        client = redis.Redis.from_url(url, decode_responses=True)
        fabric = EventFabric(client)
        fabric.ensure_group(GROUP)
        event_id = fabric.publish(_envelope())
        pending = client.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=1)
        assert pending
        key = applied_key(event_id)
        fabric._mark_applied(key)  # noqa: SLF001 -- durability fixture
        client.xadd(STREAM, {EVENT_FIELD: "not-json"})
        client.xadd(DLQ, {EVENT_FIELD: '{"specversion":"1.0","id":"dlq-1"}'})
        assert client.xpending(STREAM, GROUP)["pending"] >= 1
        assert client.exists(key)
        assert client.xlen(DLQ) >= 1
    finally:
        time.sleep(1.5)
        _stop_redis(proc)

    proc = _start_redis(data_dir, appendonly=appendonly, port=port)
    try:
        client = redis.Redis.from_url(url, decode_responses=True)
        if not appendonly:
            assert client.xlen(STREAM) == 0
            assert client.xlen(DLQ) == 0
            assert not client.exists(key)
            return
        assert client.xlen(STREAM) >= 1
        assert client.xpending(STREAM, GROUP)["pending"] >= 1
        assert client.xlen(DLQ) >= 1
        assert client.exists(key)
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)
