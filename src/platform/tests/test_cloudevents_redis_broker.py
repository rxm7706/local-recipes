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
import socket
import subprocess
import time
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
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
from django_pyforge.events import DomainAdapter
from django_pyforge.events import EventBrokerConfigError
from django_pyforge.events import EventFabric
from django_pyforge.events import MemoryRedis
from django_pyforge.events import PayloadShapeError
from django_pyforge.events import RecipeAuditAdapter
from django_pyforge.events import RemedyRequestedAdapter
from django_pyforge.events import TraceparentFormatError
from django_pyforge.events import UnregisteredEventTypeError
from django_pyforge.events import adapter_for
from django_pyforge.events import backoff_ms
from django_pyforge.events import bound_trace
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
from django_pyforge.events.constants import DLQ_QUARANTINED_AT_FIELD
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
from django_pyforge.events.fabric import redact_secrets
from django_pyforge.events.memory import DataError
from django_pyforge.events.tracing import parse_traceparent
from django_pyforge.events.tracing import traceparent_from_task_request
from django_pyforge.management.commands.consume_events import StopFlag
from django_pyforge.management.commands.consume_events import run_passes
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


def _pending(
    broker: Any, group: str, consumer: str | None = None
) -> list[dict[str, Any]]:
    """XPENDING rows -- the delivery counter and idle time, without
    re-delivering (unlike an XREADGROUP over the history)."""
    kwargs: dict[str, Any] = {"consumername": consumer} if consumer else {}
    return [
        dict(row)
        for row in broker.xpending_range(STREAM, group, "-", "+", 100, **kwargs)
    ]


def _pending_ids(broker: Any, group: str, consumer: str) -> list[str]:
    return [str(row["message_id"]) for row in _pending(broker, group, consumer)]


def _deliver_one(broker: MemoryRedis, group: str, consumer: str) -> str:
    """XREADGROUP one new entry to ``consumer`` and return its stream id."""
    rows = broker.xreadgroup(group, consumer, {STREAM: ">"}, count=1)
    return rows[0][1][0][0]


def _free_port() -> int:
    """An ephemeral port the kernel just handed out (never time-derived)."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


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
    broker.set(applied_key(event_id, GROUP), "1")
    # The entry is pending under CONSUMER from the read above; the retry pass
    # re-claims it once its backoff has elapsed and finds it already applied.
    broker.advance_ms(backoff_ms(1))
    fabric.consume(GROUP, CONSUMER, handler)
    assert runs == [event_id]
    assert _pending_ids(broker, GROUP, CONSUMER) == []


def test_each_group_applies_independently() -> None:
    """Review P1: the applied mark is per GROUP. Doctor's consumer reading a
    `remedy.requested` first (and ACKing it untouched) must not stop mason's
    group from running its handler on the same entry."""
    broker = MemoryRedis()
    fabric = EventFabric(broker)
    fabric.ensure_group("doctor")
    fabric.ensure_group("mason")
    seen: list[tuple[str, str]] = []

    class SpyRemedy(RemedyRequestedAdapter):
        def apply(self, event: dict) -> None:
            seen.append(("mason", event["id"]))

    register_adapter(SpyRemedy())
    try:
        event_id = fabric.publish(
            _envelope(type="remedy.requested", data={"package": "p", "remedy": "bump"}),
        )
        assert fabric.consume("doctor", "doctor-1", station_handler("doctor")) == 1
        assert seen == []
        assert _pending(broker, "doctor") == []
        assert fabric.consume("mason", "mason-1", station_handler("mason")) == 1
        assert seen == [("mason", event_id)]
        assert _pending(broker, "mason") == []
        assert broker.get(applied_key(event_id, "doctor")) == "1"
        assert broker.get(applied_key(event_id, "mason")) == "1"
    finally:
        register_adapter(RemedyRequestedAdapter())


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
    assert qfields[DLQ_QUARANTINED_AT_FIELD].isdigit()
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
    assert broker.get(applied_key(event_id, GROUP)) is None
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
    assert broker.get(applied_key(event_id, GROUP)) is None

    broker.advance_ms(60 * 60 * 1000)
    for _ in range(3):
        fabric.consume(GROUP, CONSUMER, doctor_handler)
    assert len(calls) == ceiling


def test_max_attempts_one_quarantines_after_first_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DJANGO_PYFORGE_EVENT_MAX_ATTEMPTS", "1")
    broker = MemoryRedis()
    fabric = EventFabric(broker)
    fabric.ensure_group(GROUP)
    fabric.publish(_envelope())
    calls: list[int] = []

    def failing(event: dict) -> None:
        calls.append(1)
        raise RuntimeError("once is enough")

    assert fabric.consume(GROUP, CONSUMER, failing) == 0
    assert calls == [1]
    ((_qid, fields),) = list_quarantined(broker)
    assert fields[DLQ_REASON_FIELD] == DLQ_REASON_EXHAUSTED
    assert fields[DLQ_ATTEMPTS_FIELD] == "1"
    assert fields[DLQ_ERROR_FIELD] == "RuntimeError: once is enough"
    assert _pending(broker, GROUP) == []
    broker.advance_ms(60_000)
    fabric.consume(GROUP, CONSUMER, failing)
    assert calls == [1]


def test_entry_already_at_ceiling_is_quarantined_without_a_handler_call(
    default_delivery_env: None,
) -> None:
    """Review P14: the process died after the last XCLAIM and before it
    reported back, so XPENDING already shows ``ceiling`` deliveries."""
    broker = MemoryRedis()
    fabric = EventFabric(broker)
    fabric.ensure_group(GROUP)
    event_id = fabric.publish(_envelope())
    ceiling = max_attempts()
    stream_id = _deliver_one(broker, GROUP, CONSUMER)
    for _ in range(ceiling - 1):
        assert broker.xclaim(STREAM, GROUP, CONSUMER, 0, [stream_id])
    assert _pending(broker, GROUP, CONSUMER)[0]["times_delivered"] == ceiling
    broker.set(last_error_key(stream_id), "RuntimeError: died before reporting")
    calls: list[int] = []
    assert fabric.consume(GROUP, CONSUMER, lambda event: calls.append(1)) == 0
    assert calls == []
    ((_qid, fields),) = list_quarantined(broker)
    assert json.loads(fields[EVENT_FIELD])["id"] == event_id
    assert fields[DLQ_REASON_FIELD] == DLQ_REASON_EXHAUSTED
    assert fields[DLQ_ATTEMPTS_FIELD] == str(ceiling)
    assert fields[DLQ_ERROR_FIELD] == "RuntimeError: died before reporting"
    assert _pending(broker, GROUP) == []
    assert broker.get(last_error_key(stream_id)) is None


def test_exhausted_entry_trimmed_from_stream_is_acked_with_an_error_log(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Review P8a: MAXLEN trimmed the entry while it was still pending, so
    there is nothing to quarantine -- the ACK is logged at ERROR, not silent."""
    monkeypatch.setenv("DJANGO_PYFORGE_EVENT_MAX_ATTEMPTS", "2")
    broker = MemoryRedis()
    fabric = EventFabric(broker)
    fabric.ensure_group(GROUP)
    fabric.publish(_envelope())
    stream_id = _deliver_one(broker, GROUP, CONSUMER)
    assert broker.xclaim(STREAM, GROUP, CONSUMER, 0, [stream_id])
    broker.set(last_error_key(stream_id), "RuntimeError: died")
    assert broker.xdel(STREAM, stream_id) == 1
    calls: list[int] = []
    with caplog.at_level(logging.ERROR, logger="django_pyforge.events.fabric"):
        assert fabric.consume(GROUP, CONSUMER, lambda event: calls.append(1)) == 0
    assert calls == []
    assert _pending(broker, GROUP) == []
    assert list_quarantined(broker) == []
    records = [r for r in caplog.records if "no longer in" in r.getMessage()]
    assert len(records) == 1
    record = records[0]
    assert record.stream_id == stream_id  # type: ignore[attr-defined]
    assert record.group == GROUP  # type: ignore[attr-defined]
    assert record.attempts == 2  # type: ignore[attr-defined]
    assert record.error == "RuntimeError: died"  # type: ignore[attr-defined]


def test_broker_without_xpending_is_refused() -> None:
    """Review P8b: no XPENDING means no attempt counter -- refuse, never run
    unbounded."""

    class NoPendingRedis(MemoryRedis):
        xpending_range = None

    broker = NoPendingRedis()
    fabric = EventFabric(broker)
    fabric.ensure_group(GROUP)
    fabric.publish(_envelope())
    with pytest.raises(TypeError, match="XPENDING"):
        fabric.consume(GROUP, CONSUMER, lambda event: None)


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
    assert len(calls) == 1, (
        "a failing event must not be re-attempted before its backoff"
    )
    for attempts, delay in enumerate(schedule, start=1):
        broker.advance_ms(delay // 2)
        fabric.consume(GROUP, CONSUMER, handler)
        assert len(calls) == attempts, (
            f"attempt {attempts + 1} ran before {delay} ms elapsed"
        )
        broker.advance_ms(delay - delay // 2)
        fabric.consume(GROUP, CONSUMER, handler)
        assert len(calls) == attempts + 1, (
            f"attempt {attempts + 1} did not run at {delay} ms"
        )
    assert len(list_quarantined(broker)) == 1


def test_knob_floors_never_reach_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """Review P10: a 0 ms backoff re-claims at once (incl. entries a harvester
    just took); a 0 ms harvest threshold steals live messages (A-4)."""
    monkeypatch.setenv("DJANGO_PYFORGE_EVENT_BACKOFF_BASE_MS", "0")
    monkeypatch.setenv("DJANGO_PYFORGE_EVENT_BACKOFF_MAX_MS", "0")
    monkeypatch.setenv("DJANGO_PYFORGE_EVENT_HANDLER_TIMEOUT_MS", "0")
    assert backoff_ms(1) == 1
    assert backoff_ms(7) == 1
    assert handler_timeout_ms() == 1


def test_harvest_claims_only_entries_idle_past_threshold(
    default_delivery_env: None,
) -> None:
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
    assert len(_pending_ids(broker, GROUP, "dead-1")) == 3, (
        "harvest stole live messages"
    )
    assert list_quarantined(broker) == []

    broker.advance_ms(threshold - 1_000)
    assert fabric.harvest_poison(GROUP, CONSUMER) == 0
    assert len(_pending_ids(broker, GROUP, "dead-1")) == 3

    broker.advance_ms(1_000)
    assert fabric.harvest_poison(GROUP, CONSUMER) == 1
    assert _pending_ids(broker, GROUP, "dead-1") == []
    ((_qid, qfields),) = list_quarantined(broker)
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
    ((_qid, fields),) = list_quarantined(broker)
    assert json.loads(fields[EVENT_FIELD])["id"] == event_id
    assert fields[DLQ_REASON_FIELD] == DLQ_REASON_EXHAUSTED
    assert fields[DLQ_ERROR_FIELD] == "RuntimeError: doctor handler crashed"
    assert fields[DLQ_ATTEMPTS_FIELD] == "2"
    assert _pending(broker, GROUP) == []


def test_recorded_error_redacts_url_userinfo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Review P15: driver exceptions embed DSNs; the DLQ is never trimmed."""
    assert (
        redact_secrets("redis://:pw@host:6379/0 and https://u:p@x/y")
        == "redis://***@host:6379/0 and https://***@x/y"
    )
    assert redact_secrets("KeyError: 'reason'") == "KeyError: 'reason'"
    assert (
        redact_secrets("see https://example.org/no-userinfo")
        == "see https://example.org/no-userinfo"
    )
    monkeypatch.setenv("DJANGO_PYFORGE_EVENT_MAX_ATTEMPTS", "1")
    broker = MemoryRedis()
    fabric = EventFabric(broker)
    fabric.ensure_group(GROUP)
    fabric.publish(_envelope())

    def failing(event: dict) -> None:
        msg = "could not connect to postgres://platform_app:s3cret@db:5432/platform"
        raise ConnectionError(msg)

    fabric.consume(GROUP, CONSUMER, failing)
    ((_qid, fields),) = list_quarantined(broker)
    assert fields[DLQ_ERROR_FIELD] == (
        "ConnectionError: could not connect to postgres://***@db:5432/platform"
    )
    assert "s3cret" not in json.dumps(fields)


def test_memory_xclaim_pins_redis_py_list_contract() -> None:
    """Review P13b: redis-py's XCLAIM rejects a bare id with DataError; the
    in-memory double must not accept a call shape the driver refuses."""
    broker = MemoryRedis()
    fabric = EventFabric(broker)
    fabric.ensure_group(GROUP)
    fabric.publish(_envelope())
    stream_id = _deliver_one(broker, GROUP, CONSUMER)
    with pytest.raises(DataError):
        broker.xclaim(STREAM, GROUP, CONSUMER, 0, stream_id)
    with pytest.raises(DataError):
        broker.xclaim(STREAM, GROUP, CONSUMER, 0, [])
    assert broker.xclaim(STREAM, GROUP, CONSUMER, 0, [stream_id])


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
    landed = [
        json.loads(row[1][EVENT_FIELD])["type"]
        for row in broker.xrange(STREAM, "-", "+")
    ]
    assert landed == list(chain)


def test_register_adapter_refuses_unregistered_type() -> None:
    """Review P16: a registration mistake is an UnregisteredEventTypeError,
    not a payload-shape error."""

    class Stray(DomainAdapter):
        event_type = "not.registered"

    with pytest.raises(UnregisteredEventTypeError):
        register_adapter(Stray())
    assert adapter_for("not.registered") is None


def test_station_handler_routes_subscribed_types_only() -> None:
    seen: list[str] = []

    class SpyAudit(RecipeAuditAdapter):
        def apply(self, event: dict) -> None:
            seen.append(event["id"])

    register_adapter(SpyAudit())
    try:
        doctor = station_handler("doctor")
        doctor(
            {
                "type": "recipe.audit.failed",
                "id": "a",
                "data": {"package": "p", "reason": "r"},
            }
        )
        doctor(
            {
                "type": "remedy.requested",
                "id": "b",
                "data": {"package": "p", "remedy": "x"},
            }
        )
        assert seen == ["a"]
        with pytest.raises(PayloadShapeError):
            doctor({"type": "recipe.audit.failed", "id": "c", "data": {"package": "p"}})
        mason = station_handler("mason")
        mason(
            {
                "type": "recipe.audit.failed",
                "id": "d",
                "data": {"package": "p", "reason": "r"},
            }
        )
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
    fabric.publish(
        _envelope(type="remedy.requested", data={"package": "demo", "remedy": "bump"})
    )
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
    # A station outside the tokens, or one that subscribes to nothing (review
    # P7), is refused before any Redis call.
    with pytest.raises(CommandError, match="station token"):
        call_command(
            "consume_events",
            station="nope",
            client=broker,
            once=True,
            stdout=StringIO(),
        )
    with pytest.raises(CommandError, match="subscribes to no event type"):
        call_command(
            "consume_events",
            station="atlas",
            client=broker,
            once=True,
            stdout=StringIO(),
        )
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


class _TracingFabric(EventFabric):
    """Records the order of consume / harvest / wait calls for run_passes."""

    def __init__(self, broker: Any) -> None:
        super().__init__(broker)
        self.trace: list[tuple[str, Any]] = []

    def consume(self, *args: Any, **kwargs: Any) -> int:
        handled = super().consume(*args, **kwargs)
        self.trace.append(("consume", handled))
        return handled

    def harvest_poison(self, *args: Any, **kwargs: Any) -> int:
        self.trace.append(("harvest", None))
        return super().harvest_poison(*args, **kwargs)


class _RecordingStop(StopFlag):
    def __init__(self, fabric: _TracingFabric, stop_on_wait: int | None = None) -> None:
        super().__init__()
        self._fabric = fabric
        self._stop_on_wait = stop_on_wait
        self.waits = 0

    def wait(self, timeout: float) -> bool:
        self.waits += 1
        self._fabric.trace.append(("wait", timeout))
        if self._stop_on_wait is not None and self.waits >= self._stop_on_wait:
            self.request()
            return True
        return False


def test_run_passes_stops_after_pass_harvests_on_schedule_and_waits_only_when_idle() -> (
    None
):
    """Review P3: a stop requested mid-pass ends the loop after that pass
    (no further entry claimed/read, the in-flight handler finishes);
    harvest runs on pass N of ``harvest_every``; the idle wait is taken only
    after a pass that handled nothing."""
    # (a) the handler itself requests the stop while entries remain.
    broker = MemoryRedis()
    fabric = _TracingFabric(broker)
    fabric.ensure_group("doctor")
    ids = [
        fabric.publish(_envelope(data={"package": f"p{i}", "reason": "r"}))
        for i in range(3)
    ]
    stop = _RecordingStop(fabric)
    handled_ids: list[str] = []

    def stopping_handler(event: dict) -> None:
        handled_ids.append(event["id"])
        if event["id"] == ids[1]:
            stop.request()

    result = run_passes(
        fabric,
        "doctor",
        "doctor-1",
        stopping_handler,
        interval=0.5,
        harvest_every=2,
        once=False,
        stop=stop,
    )
    assert result == (1, 2, 0)
    assert handled_ids == ids[:2]
    assert fabric.trace == [("consume", 2)]
    assert stop.waits == 0
    # The third entry was delivered by the batch read but never attempted:
    # still pending under this consumer, for the next pass or a harvest.
    assert _pending_ids(broker, "doctor", "doctor-1") == [
        _pending_ids(broker, "doctor", "doctor-1")[0]
    ]
    assert len(_pending(broker, "doctor")) == 1

    # (b) an idle loop: harvest on passes 2 and 4, waits only after idle passes.
    broker = MemoryRedis()
    fabric = _TracingFabric(broker)
    fabric.ensure_group("doctor")
    fabric.publish(_envelope(data={"package": "p", "reason": "r"}))
    stop = _RecordingStop(fabric, stop_on_wait=2)
    result = run_passes(
        fabric,
        "doctor",
        "doctor-1",
        lambda event: None,
        interval=0.5,
        harvest_every=2,
        once=False,
        stop=stop,
    )
    assert result == (4, 1, 0)
    assert fabric.trace == [
        ("consume", 1),
        ("consume", 0),
        ("harvest", None),
        ("wait", 0.5),
        ("consume", 0),
        ("wait", 0.5),
        ("consume", 0),
        ("harvest", None),
    ]


def test_parse_traceparent_rejects_version_ff_and_zero_ids() -> None:
    """Review P17: W3C forbids version ``ff``."""
    assert parse_traceparent(TRACEPARENT) == (TRACE_ID, "b7ad6b7169203331")
    assert parse_traceparent(f"ff-{TRACE_ID}-b7ad6b7169203331-01") is None
    assert parse_traceparent(f"00-{'0' * 32}-b7ad6b7169203331-01") is None
    assert parse_traceparent(f"00-{TRACE_ID}-{'0' * 16}-01") is None
    assert parse_traceparent(None) is None


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


def test_bound_trace_restores_outer_context_even_when_body_raises() -> None:
    """Review P9: exit restores the outer structlog values (not merely
    unbinds) and resets the contextvar whatever raised inside."""
    structlog = pytest.importorskip("structlog")
    from django_pyforge.events.tracing import _current_traceparent

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(trace_id="outer", traceparent="outer-tp")
    try:
        with pytest.raises(RuntimeError, match="inside"), bound_trace(TRACEPARENT):
            assert structlog.contextvars.get_contextvars()["trace_id"] == TRACE_ID
            assert _current_traceparent.get() == TRACEPARENT
            msg = "inside"
            raise RuntimeError(msg)
        assert structlog.contextvars.get_contextvars()["trace_id"] == "outer"
        assert structlog.contextvars.get_contextvars()["traceparent"] == "outer-tp"
        assert _current_traceparent.get() is None
        with bound_trace("garbage"):
            assert structlog.contextvars.get_contextvars()["trace_id"] == "outer"
    finally:
        structlog.contextvars.clear_contextvars()


def test_traceparent_from_task_request_reads_both_shapes() -> None:
    """Review P2: a worker exposes custom headers as request attributes; the
    eager path keeps them under ``request.headers``."""
    attribute_form = SimpleNamespace(traceparent=TRACEPARENT, headers=None)
    headers_form = SimpleNamespace(headers={"traceparent": TRACEPARENT})
    assert traceparent_from_task_request(attribute_form) == TRACEPARENT
    assert traceparent_from_task_request(headers_form) == TRACEPARENT
    assert traceparent_from_task_request(SimpleNamespace(headers=None)) is None
    assert (
        traceparent_from_task_request(SimpleNamespace(headers={"traceparent": "bad"}))
        is None
    )
    assert (
        traceparent_from_task_request(SimpleNamespace(traceparent="bad", headers=None))
        is None
    )
    assert traceparent_from_task_request(None) is None


def test_task_receiver_rebinds_traceparent_after_structlog_rebuilds_context() -> None:
    """Review P2: django-structlog's task_prerun clears + rebuilds the task's
    contextvars and then sends ``bind_extra_task_metadata``; the receiver in
    django_pyforge.tasks must put the trace back for either request shape."""
    structlog = pytest.importorskip("structlog")
    signals = pytest.importorskip("django_structlog.celery.signals")
    import django_pyforge.tasks  # noqa: F401 -- connects the receiver

    requests = (
        SimpleNamespace(traceparent=TRACEPARENT, headers=None),
        SimpleNamespace(headers={"traceparent": TRACEPARENT}),
    )
    try:
        for request in requests:
            structlog.contextvars.clear_contextvars()
            signals.bind_extra_task_metadata.send(
                sender=None,
                task=SimpleNamespace(request=request),
                logger=None,
            )
            context = structlog.contextvars.get_contextvars()
            assert context["trace_id"] == TRACE_ID, request
            assert context["traceparent"] == TRACEPARENT
        structlog.contextvars.clear_contextvars()
        signals.bind_extra_task_metadata.send(
            sender=None,
            task=SimpleNamespace(request=SimpleNamespace(headers=None)),
            logger=None,
        )
        assert "trace_id" not in structlog.contextvars.get_contextvars()
    finally:
        structlog.contextvars.clear_contextvars()


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
def test_trace_id_from_request_reaches_celery_headers_and_structlog(
    client, settings
) -> None:
    """AC: an event published from a request with a ``traceparent``, handled by
    a consumer that enqueues Celery work, carries the same trace id into the
    task headers and the structlog context.

    Under CELERY_TASK_ALWAYS_EAGER the task runs inside the consumer's
    ``bound_trace``, so the structlog half here proves the request -> envelope
    -> consumer -> header chain; the worker-side rebind (django-structlog's
    prerun receiver, which never fires in-process) is proven by
    ``test_task_receiver_rebinds_traceparent_after_structlog_rebuilds_context``.
    """
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


def test_enqueue_supervised_run_carries_traceparent_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from django_pyforge import tasks

    captured: dict[str, Any] = {}

    def fake_apply_async(**kwargs: Any) -> str:
        captured.update(kwargs)
        return "queued"

    monkeypatch.setattr(tasks.execute_supervised_run, "apply_async", fake_apply_async)

    with bound_trace(TRACEPARENT):
        enqueue_supervised_run(
            "run-1", "warden", "audit", {}, subject="agent-1", task_id="task-1"
        )
    assert captured["headers"][SUBJECT_HEADER] == "agent-1"
    assert trace_id_of(captured["headers"]["traceparent"]) == TRACE_ID
    captured.clear()
    enqueue_supervised_run(
        "run-2", "warden", "audit", {}, subject="agent-1", task_id="task-2"
    )
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
    # Review P5: a row the fabric quarantined shows its metadata, not only
    # the event.
    fabric = EventFabric(broker)
    fabric.ensure_group(GROUP)
    fabric.publish(_envelope())
    stream_id = _deliver_one(broker, GROUP, CONSUMER)
    fabric._quarantine(  # noqa: SLF001 -- the operator-facing shape is the contract
        GROUP,
        stream_id,
        {EVENT_FIELD: '{"specversion":"1.0","id":"e-1"}'},
        reason=DLQ_REASON_EXHAUSTED,
        attempts=5,
        error="KeyError: 'reason'",
    )
    out = StringIO()
    call_command("list_event_dlq", client=broker, stdout=out)
    lines = out.getvalue().splitlines()
    assert len(lines) == 2
    assert "reason=exhausted" in lines[1]
    assert "attempts=5" in lines[1]
    assert f"group={GROUP}" in lines[1]
    assert f"stream_id={stream_id}" in lines[1]
    assert "quarantined_at=" in lines[1]
    assert "error=KeyError: 'reason'" in lines[1]
    assert lines[1].endswith('{"specversion":"1.0","id":"e-1"}')


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


def test_consume_events_binds_the_broker_through_the_ad10_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Review P6: without an injected client the command goes through
    ``connect_event_broker``, so a broker URL shared with the cache is refused."""
    _ensure_django()
    from django.conf import settings

    monkeypatch.setattr(settings, "REDIS_BROKER_URL", BROKER_URL)
    monkeypatch.setattr(settings, "REDIS_CACHE_URL", BROKER_URL)
    with pytest.raises(EventBrokerConfigError):
        call_command("consume_events", station="doctor", once=True, stdout=StringIO())


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
    assert broker.get(f"{APPLIED_PREFIX}{GROUP}:{event_id}") is None
    with_item = fabric.publish(_envelope(workitemid="PYF-24-1"))
    rows = broker.xrange(STREAM, "-", "+")
    payloads = [json.loads(row[1][EVENT_FIELD]) for row in rows]
    tagged = next(item for item in payloads if item["id"] == with_item)
    assert tagged["workitemid"] == "PYF-24-1"
    assert "jira" not in tagged


def test_applied_key_carries_ttl() -> None:
    broker = MemoryRedis()
    fabric = EventFabric(broker)
    key = applied_key("event-1", GROUP)
    assert key == f"{APPLIED_PREFIX}{GROUP}:event-1"
    assert fabric._mark_applied(key)  # noqa: SLF001 -- TTL contract
    assert broker.ttl(key) > 0


def _ensure_django() -> None:
    import django

    django.setup()


@pytest.mark.django_db
def test_execute_supervised_run_leaves_no_celery_result_key(tmp_path, settings) -> None:
    # `settings` is pytest-django's fixture: the broker/result overrides below are
    # restored after the test instead of leaking into every later settings assertion.
    pytest.importorskip("pytest_django")
    _ensure_django()
    from django.core.management import call_command as django_call_command

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

        import redis

        client = redis.Redis.from_url(broker_url, decode_responses=True)

        def _noop_runner(_payload: dict) -> dict:
            return {"ok": True}

        from django_pyforge import supervisor
        from django_pyforge.tasks import execute_supervised_run

        # tasks.py binds lookup_runner by name at import, so rebinding the
        # supervisor attribute never reached it; register through the registry.
        supervisor.register_runner("warden", "noop", _noop_runner)
        try:
            from django_pyforge.models import RunState

            run = RunState.objects.create(
                station="warden",
                status=RunState.Status.PENDING,
            )
            execute_supervised_run.delay(str(run.pk), "warden", "noop", {})
        finally:
            supervisor._runners.pop(("warden", "noop"), None)  # noqa: SLF001 -- no unregister API

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


def test_real_redis_retry_backoff_dlq_and_harvest(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The delivery semantics against a real redis-server (platform-dev env):
    XPENDING/XCLAIM/XAUTOCLAIM as Redis actually answers them, not the
    in-memory model."""
    if shutil.which("redis-server") is None:
        pytest.skip("redis-server not on PATH (platform-dev env)")
    monkeypatch.setenv("DJANGO_PYFORGE_EVENT_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("DJANGO_PYFORGE_EVENT_BACKOFF_BASE_MS", "100")
    monkeypatch.setenv("DJANGO_PYFORGE_EVENT_BACKOFF_MAX_MS", "1000")
    monkeypatch.setenv("DJANGO_PYFORGE_EVENT_HANDLER_TIMEOUT_MS", "300")

    import redis

    data_dir = tmp_path / "broker"
    data_dir.mkdir()
    port = _free_port()
    proc = _start_redis(data_dir, appendonly=False, port=port)
    try:
        client = redis.Redis.from_url(
            f"redis://127.0.0.1:{port}/0", decode_responses=True
        )
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
        ((_qid, fields),) = list_quarantined(client)
        assert json.loads(fields[EVENT_FIELD])["id"] == event_id
        assert fields[DLQ_REASON_FIELD] == DLQ_REASON_EXHAUSTED
        assert fields[DLQ_ERROR_FIELD] == "RuntimeError: real redis boom"
        assert fields[DLQ_ATTEMPTS_FIELD] == "3"
        assert client.xpending(STREAM, GROUP)["pending"] == 0
        assert not client.exists(applied_key(event_id, GROUP))

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

    import redis

    data_dir = tmp_path / "broker-aof"
    data_dir.mkdir()
    port = _free_port()
    url = f"redis://127.0.0.1:{port}/0"

    proc = _start_redis(data_dir, appendonly=appendonly, port=port)
    try:
        client = redis.Redis.from_url(url, decode_responses=True)
        fabric = EventFabric(client)
        fabric.ensure_group(GROUP)
        event_id = fabric.publish(_envelope())
        pending = client.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=1)
        assert pending
        key = applied_key(event_id, GROUP)
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
