"""Steward 24.1 / 40.2: CloudEvents 1.0 on redis-broker Streams."""

from __future__ import annotations

import json
import shutil
import signal
import subprocess
import time
from io import StringIO
from pathlib import Path

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
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)

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
