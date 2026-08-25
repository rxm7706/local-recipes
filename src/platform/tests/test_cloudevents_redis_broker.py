"""Steward 24.1: CloudEvents 1.0 on redis-broker Streams (canopy AD-8 / AD-10)."""

from __future__ import annotations

import json
from io import StringIO

import pytest
from django.core.management import call_command
from django_pyforge.events import DLQ
from django_pyforge.events import EVENT_FIELD
from django_pyforge.events import STREAM
from django_pyforge.events import DataschemaRequiredError
from django_pyforge.events import EventBrokerConfigError
from django_pyforge.events import EventFabric
from django_pyforge.events import MemoryRedis
from django_pyforge.events import connect_event_broker
from django_pyforge.events import list_quarantined
from django_pyforge.events.constants import APPLIED_PREFIX
from django_pyforge.events.constants import EXT_GIT_SHA
from django_pyforge.events.constants import EXT_SBOM_PURL
from django_pyforge.events.constants import EXT_SPEC_ID
from django_pyforge.events.fabric import applied_key

GROUP = "warden"
CONSUMER = "warden-1"
DATASCHEMA = "https://example.invalid/schemas/recipe-audit.json"
BROKER_URL = "redis://broker.example.invalid:6379/0"
CACHE_URL = "redis://cache.example.invalid:6379/0"


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


def _pending_ids(broker: MemoryRedis, group: str, consumer: str) -> list[str]:
    rows = broker.xreadgroup(group, consumer, {STREAM: "0"}, count=100)
    ids: list[str] = []
    for _stream, messages in rows:
        ids.extend(msg_id for msg_id, _fields in messages)
    return ids


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
    fabric.consume(GROUP, CONSUMER, handler)
    assert runs == [event_id]
    assert _pending_ids(broker, GROUP, CONSUMER) == []


def test_poison_harvest_xautoclaim_to_dlq() -> None:
    broker = CountingRedis()
    fabric = EventFabric(broker)
    fabric.ensure_group(GROUP)
    broker.xadd(STREAM, {EVENT_FIELD: "not-cloudevents-json"})
    good_id = fabric.publish(_envelope())
    runs: list[str] = []
    fabric.consume(GROUP, CONSUMER, lambda event: runs.append(event["id"]))
    assert runs == [good_id]
    moved = fabric.harvest_poison(GROUP, "dlq-harvester", min_idle_time=0)
    assert moved == 1
    assert broker.xautoclaim_calls == [(STREAM, GROUP, "dlq-harvester", 0)]
    assert _pending_ids(broker, GROUP, CONSUMER) == []
    assert _pending_ids(broker, GROUP, "dlq-harvester") == []
    quarantined = list_quarantined(broker)
    assert len(quarantined) == 1
    _qid, qfields = quarantined[0]
    assert qfields[EVENT_FIELD] == "not-cloudevents-json"
    more: list[str] = []
    fabric.consume(GROUP, CONSUMER, lambda event: more.append(event["id"]))
    assert more == []


def test_enumerate_dlq_returns_quarantined_and_empty() -> None:
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
