"""Story 49.5 / CAP-11: redis-cache eviction must not destroy redis-broker state.

Story 40.2 split ``redis-cache`` (``allkeys-lru``, evictable) from
``redis-broker`` (``noeviction``, Celery queues + CloudEvents streams). CAP-11
requires a real-Redis test that fills the cache to its eviction limit while
broker traffic is in flight and proves queued tasks, stream entries, and PEL
entries survive — and that the same pressure on a single shared instance
would not pass.
"""

from __future__ import annotations

import json
import shutil
import signal
import socket
import subprocess
import time
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from pathlib import Path

import pytest
import redis
from django_pyforge.events import EVENT_FIELD
from django_pyforge.events import EXT_GIT_SHA
from django_pyforge.events import EXT_SBOM_PURL
from django_pyforge.events import EXT_SPEC_ID
from django_pyforge.events import STREAM
from django_pyforge.events import EventFabric
from django_pyforge.events import connect_event_broker
from django_pyforge.queues import DEFAULT_QUEUE

GROUP = "warden"
CONSUMER = "warden-1"
STALE_CONSUMER = "stale-consumer"
DATASCHEMA = "https://example.invalid/schemas/recipe-audit.json"
CACHE_MAXMEMORY = "1mb"
BROKER_MAXMEMORY = "32mb"
# Shared-instance regression needs headroom so allkeys-lru can eventually evict
# broker keys after cache-pressure keys rotate — 1mb OOMs before that happens.
SHARED_MAXMEMORY = "4mb"
_FILL_VALUE_BYTES = 50_000
_FILL_MAX_ITERATIONS = 10_000


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_redis(
    data_dir: Path,
    *,
    port: int,
    maxmemory: str,
    maxmemory_policy: str,
    appendonly: bool = False,
) -> subprocess.Popen:
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
        "--maxmemory",
        maxmemory,
        "--maxmemory-policy",
        maxmemory_policy,
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


def _envelope(**overrides: object) -> dict:
    body: dict = {
        "type": "recipe.audit.failed",
        "source": "/stations/warden",
        "dataschema": DATASCHEMA,
        EXT_SPEC_ID: "spec-49-5-cap-11-in-effect-the-eviction-test",
        EXT_GIT_SHA: "deadbeef",
        EXT_SBOM_PURL: "pkg:pypi/django-pyforge@0.1.0",
    }
    body.update(overrides)
    return body


def _seed_broker_state(broker_url: str) -> dict[str, Any]:
    """Queue a Celery-shaped task, publish a stream entry, and leave a PEL row."""
    client = redis.Redis.from_url(broker_url, decode_responses=True)
    fabric = EventFabric(client)
    fabric.ensure_group(GROUP)

    queued_task = json.dumps(
        {
            "body": "eyJ0YXNrIjogImR1bW15In0=",
            "headers": {},
            "properties": {},
            "content-type": "application/json",
            "content-encoding": "utf-8",
        },
    )
    client.lpush(DEFAULT_QUEUE, queued_task)

    event_id = fabric.publish(_envelope())
    client.xreadgroup(GROUP, STALE_CONSUMER, {STREAM: ">"}, count=1)

    pending = client.xpending(STREAM, GROUP)
    assert pending["pending"] == 1

    return {
        "queued_depth": client.llen(DEFAULT_QUEUE),
        "stream_len": client.xlen(STREAM),
        "event_id": event_id,
        "pending_count": pending["pending"],
    }


def _fill_cache_to_eviction(cache_url: str) -> None:
    """Drive redis-cache to its maxmemory ceiling under allkeys-lru."""
    client = redis.Redis.from_url(cache_url, decode_responses=False)
    info = client.info("memory")
    limit = int(info["maxmemory"])
    assert limit > 0, "cache maxmemory must be configured for this test"
    policy = str(info.get("maxmemory_policy", ""))
    assert "allkeys-lru" in policy, f"cache must use allkeys-lru, got {policy!r}"

    payload = b"x" * _FILL_VALUE_BYTES
    evicted_before = int(client.info("stats").get("evicted_keys", 0))
    index = 0
    # Under allkeys-lru, used_memory stays below maxmemory while keys rotate out;
    # evicted_keys is the reliable signal that eviction pressure is real.
    while int(client.info("stats").get("evicted_keys", 0)) == evicted_before:
        try:
            client.set(f"cache-pressure:{index}", payload)
        except redis.exceptions.OutOfMemoryError:
            # Saturated with only noeviction-safe keys left — enough pressure.
            break
        index += 1
        if index > _FILL_MAX_ITERATIONS:
            pytest.fail("cache fill did not trigger allkeys-lru evictions")

    keys_before = client.dbsize()
    for extra in range(50):
        client.set(f"cache-pressure:tail:{extra}", payload)
    keys_after = client.dbsize()
    assert keys_after <= keys_before + 5, (
        "expected allkeys-lru to evict under sustained writes"
    )
    assert int(client.info("memory")["used_memory"]) <= limit


def _cloudevent_present(client: Any, cloudevent_id: str) -> bool:
    for _stream_id, fields in client.xrange(STREAM, "-", "+", count=100):
        body = json.loads(fields[EVENT_FIELD])
        if body.get("id") == cloudevent_id:
            return True
    return False


def _broker_snapshot(broker_url: str, *, cloudevent_id: str) -> dict[str, Any]:
    client = redis.Redis.from_url(broker_url, decode_responses=True)
    stream_exists = bool(client.exists(STREAM))
    pending_count = 0
    stream_ids: list[str] = []
    if stream_exists:
        try:
            pending_count = int(client.xpending(STREAM, GROUP)["pending"])
            pending_rows = client.xpending_range(STREAM, GROUP, "-", "+", 10)
            stream_ids = [row["message_id"] for row in pending_rows]
        except redis.exceptions.ResponseError:
            stream_exists = False
    return {
        "queued_depth": client.llen(DEFAULT_QUEUE),
        "stream_len": client.xlen(STREAM) if stream_exists else 0,
        "pending_count": pending_count,
        "pending_ids": stream_ids,
        "event_in_stream": (
            _cloudevent_present(client, cloudevent_id) if stream_exists else False
        ),
    }


def _run_split_survival_scenario(
    tmp_path: Path,
    *,
    cache_port: int,
    broker_port: int,
) -> None:
    cache_dir = tmp_path / "cache"
    broker_dir = tmp_path / "broker"
    cache_dir.mkdir()
    broker_dir.mkdir()

    cache_proc = _start_redis(
        cache_dir,
        port=cache_port,
        maxmemory=CACHE_MAXMEMORY,
        maxmemory_policy="allkeys-lru",
    )
    broker_proc = _start_redis(
        broker_dir,
        port=broker_port,
        maxmemory=BROKER_MAXMEMORY,
        maxmemory_policy="noeviction",
        appendonly=True,
    )
    try:
        cache_url = f"redis://127.0.0.1:{cache_port}/0"
        broker_url = f"redis://127.0.0.1:{broker_port}/0"
        connect_event_broker(broker_url, cache_url)

        before = _seed_broker_state(broker_url)
        _fill_cache_to_eviction(cache_url)
        after = _broker_snapshot(broker_url, cloudevent_id=before["event_id"])

        assert after["queued_depth"] == before["queued_depth"]
        assert after["stream_len"] == before["stream_len"]
        assert after["pending_count"] == before["pending_count"]
        assert after["event_in_stream"]
        assert after["pending_ids"], (
            "PEL entry must survive cache eviction on split redis"
        )
    finally:
        _stop_redis(broker_proc)
        _stop_redis(cache_proc)


def test_broker_survives_cache_eviction_when_split(tmp_path: Path) -> None:
    """Split redis-cache/redis-broker: broker queues, streams, and PEL survive."""
    if shutil.which("redis-server") is None:
        pytest.skip("redis-server not on PATH (platform-dev env)")

    cache_port = _free_port()
    broker_port = _free_port()
    while broker_port == cache_port:
        broker_port = _free_port()

    _run_split_survival_scenario(
        tmp_path,
        cache_port=cache_port,
        broker_port=broker_port,
    )


def test_unsplit_redis_loses_broker_state_under_cache_pressure(tmp_path: Path) -> None:
    """Regression guard: one shared instance lets cache eviction destroy broker data."""
    if shutil.which("redis-server") is None:
        pytest.skip("redis-server not on PATH (platform-dev env)")

    shared_dir = tmp_path / "shared"
    shared_dir.mkdir()
    port = _free_port()
    # Shared instance uses cache policy — the unsafe composition CAP-11 guards against.
    proc = _start_redis(
        shared_dir,
        port=port,
        maxmemory=SHARED_MAXMEMORY,
        maxmemory_policy="allkeys-lru",
    )
    try:
        shared_url = f"redis://127.0.0.1:{port}/0"
        before = _seed_broker_state(shared_url)
        _fill_cache_to_eviction(shared_url)
        after = _broker_snapshot(shared_url, cloudevent_id=before["event_id"])

        broker_lost = (
            after["queued_depth"] < before["queued_depth"]
            or after["stream_len"] < before["stream_len"]
            or after["pending_count"] < before["pending_count"]
            or not after["event_in_stream"]
        )
        assert broker_lost, (
            "unsplit redis must lose broker-side state under cache eviction; "
            "otherwise the split survival test would pass vacuously"
        )
    finally:
        _stop_redis(proc)
