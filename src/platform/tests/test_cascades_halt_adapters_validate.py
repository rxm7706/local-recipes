"""Steward 24.2: loop-depth ceiling, type registry, adapter validation (canopy AD-8)."""

from __future__ import annotations

import json

import pytest
from django_pyforge.events import EVENT_FIELD
from django_pyforge.events import STREAM
from django_pyforge.events import EventFabric
from django_pyforge.events import LoopDepthExceededError
from django_pyforge.events import MemoryRedis
from django_pyforge.events import PayloadShapeError
from django_pyforge.events import UnregisteredEventTypeError
from django_pyforge.events.adapters import RecipeAuditAdapter
from django_pyforge.events.constants import EXT_GIT_SHA
from django_pyforge.events.constants import EXT_LOOP_DEPTH
from django_pyforge.events.constants import EXT_SBOM_PURL
from django_pyforge.events.constants import EXT_SPEC_ID
from django_pyforge.events.constants import LOOP_DEPTH_CEILING
from django_pyforge.events.fabric import parse_cloudevent

GROUP = "warden"
CONSUMER = "warden-1"
DATASCHEMA = "https://example.invalid/schemas/recipe-audit.json"


def _envelope(**overrides: object) -> dict:
    body: dict = {
        "type": "recipe.audit.failed",
        "source": "/stations/warden",
        "dataschema": DATASCHEMA,
        EXT_SPEC_ID: "spec-24-2-cascades-halt-adapters-validate",
        EXT_GIT_SHA: "deadbeef",
        EXT_SBOM_PURL: "pkg:pypi/django-pyforge@0.1.0",
        "data": {"package": "demo", "reason": "cycle"},
    }
    body.update(overrides)
    return body


def _stream_payloads(broker: MemoryRedis) -> list[dict]:
    return [json.loads(row[1][EVENT_FIELD]) for row in broker.xrange(STREAM, "-", "+")]


def test_deliberate_cycle_halts_when_pyforgeloopdepth_reaches_8() -> None:
    broker = MemoryRedis()
    fabric = EventFabric(broker)
    fabric.ensure_group(GROUP)
    halted: list[LoopDepthExceededError] = []

    def bounce(event: dict) -> None:
        nxt = int(event.get(EXT_LOOP_DEPTH, 0)) + 1
        try:
            fabric.publish(_envelope(**{EXT_LOOP_DEPTH: nxt}))
        except LoopDepthExceededError as exc:
            halted.append(exc)

    fabric.publish(_envelope(**{EXT_LOOP_DEPTH: 0}))
    for _ in range(LOOP_DEPTH_CEILING + 2):
        fabric.consume(GROUP, CONSUMER, bounce)

    assert halted
    assert halted[0].depth == LOOP_DEPTH_CEILING
    depths = [int(payload[EXT_LOOP_DEPTH]) for payload in _stream_payloads(broker)]
    assert max(depths) == LOOP_DEPTH_CEILING - 1
    assert LOOP_DEPTH_CEILING not in depths

    before = broker.xrange(STREAM, "-", "+")
    with pytest.raises(LoopDepthExceededError) as seen:
        fabric.publish(_envelope(**{EXT_LOOP_DEPTH: LOOP_DEPTH_CEILING}))
    assert seen.value.depth == LOOP_DEPTH_CEILING
    assert broker.xrange(STREAM, "-", "+") == before


def test_event_type_is_dotted_verb_registered_in_django_pyforge() -> None:
    broker = MemoryRedis()
    fabric = EventFabric(broker)
    event_id = fabric.publish(_envelope())
    payload = _stream_payloads(broker)[0]
    assert payload["id"] == event_id
    assert payload["type"] == "recipe.audit.failed"
    assert "." in payload["type"]

    before = broker.xrange(STREAM, "-", "+")
    with pytest.raises(UnregisteredEventTypeError):
        fabric.publish(_envelope(type="not.a.registered.verb"))
    with pytest.raises(UnregisteredEventTypeError):
        fabric.publish(_envelope(type="undotted"))
    assert broker.xrange(STREAM, "-", "+") == before


def test_payload_shape_rejected_in_adapter_not_stream_boundary() -> None:
    broker = MemoryRedis()
    fabric = EventFabric(broker)
    fabric.ensure_group(GROUP)
    bad = _envelope(data={"package": "demo"})
    fabric.publish(bad)
    rows = broker.xrange(STREAM, "-", "+")
    parsed = parse_cloudevent(rows[0][1])
    assert parsed is not None
    assert parsed["data"] == {"package": "demo"}

    delivered: list[dict] = []
    fabric.consume(GROUP, CONSUMER, delivered.append)
    assert len(delivered) == 1

    adapter = RecipeAuditAdapter()
    with pytest.raises(PayloadShapeError):
        adapter.validate(delivered[0])
    with pytest.raises(PayloadShapeError):
        adapter.handle(delivered[0])
