"""Story E1 gate (FR-11, AD-20/AD-17/AD-8) — verifies in ``kedro-test`` (Wave E has no new
named gate). Covers: the payload round-trip preserves the payload EXACTLY (incl. the AD-17
stamp), the a2a/ module is the SINGLE schema source (AD-20), every authoring-fed payload
carries its injected build stamp (AD-17), an insight references a BSL metric by identifier
(AD-8), and the in-process analytical→authoring hand-off. Fully offline + deterministic.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

from pyforge.atlas.a2a import (
    A2ADecodeError,
    A2ATransportError,
    AtlasAlert,
    AtlasInsight,
    AuthoringInbox,
    Severity,
    build_alert_payload,
    build_insight_payload,
    decode_payload,
    from_message,
    hand_off,
    to_message,
)
from pyforge.atlas.a2a.schema import _BasePayload
from pyforge.atlas.semantic import METRIC_PROVENANCE

# A frozen, injected build stamp (AD-17) — never datetime.now(), so the gate is deterministic.
STAMP = "2026-07-18T00:00:00Z"

ATLAS_PKG = Path(importlib.import_module("pyforge.atlas").__file__).resolve().parent
A2A_PREFIX = "a2a/"


# --------------------------------------------------------------------------------------
# fixtures — one insight + one alert, deliberately exercising nested/optional/unicode.
# --------------------------------------------------------------------------------------
@pytest.fixture
def insight() -> AtlasInsight:
    return build_insight_payload(
        subject="numpy",
        metric_id="staleness_age_days",
        value=412,  # an int — must NOT become 412.0 across the round-trip
        detail={"maintainer": "rxm7706", "feedstocks": ["numpy-feedstock", "scipy-feedstock"]},
        build_stamp=STAMP,
    )


@pytest.fixture
def alert() -> AtlasAlert:
    return build_alert_payload(
        subject="requests-feedstock",
        severity=Severity.high,
        rule="FR-10:contract-violation",
        evidence={"expected_rows": 1000, "actual_rows": 3, "π": "unïcode ✓"},
        build_stamp=STAMP,
    )


# --------------------------------------------------------------------------------------
# AC core — round-trip preserves the payload EXACTLY, including the timestamp.
# --------------------------------------------------------------------------------------
def test_insight_round_trip_is_exact(insight: AtlasInsight):
    restored = from_message(to_message(insight))
    assert restored == insight
    assert restored.build_stamp == STAMP  # AD-17 stamp survives
    assert restored.value == 412 and isinstance(restored.value, int)  # no float drift
    assert restored.detail == insight.detail  # nested list/dict preserved


def test_alert_round_trip_is_exact(alert: AtlasAlert):
    restored = from_message(to_message(alert))
    assert restored == alert
    assert restored.build_stamp == STAMP
    assert restored.severity is Severity.high
    assert restored.evidence["actual_rows"] == 3 and isinstance(restored.evidence["actual_rows"], int)
    assert restored.evidence["π"] == "unïcode ✓"  # unicode preserved


def test_decode_payload_string_round_trip(insight: AtlasInsight, alert: AtlasAlert):
    for payload in (insight, alert):
        assert decode_payload(payload.model_dump_json()) == payload


def test_message_id_is_deterministic(insight: AtlasInsight):
    # No uuid / now() — same payload → same content-addressed id (reproducible gate).
    assert to_message(insight).message_id == to_message(insight).message_id


# --------------------------------------------------------------------------------------
# AC — the in-process analytical→authoring hand-off (transport resolved: direct-message).
# --------------------------------------------------------------------------------------
def test_analytical_to_authoring_hand_off(insight: AtlasInsight, alert: AtlasAlert):
    inbox = AuthoringInbox()  # the conda-forge-expert authoring side
    got_insight = hand_off(insight, inbox)  # cf_atlas analytical side hands off
    got_alert = hand_off(alert, inbox)
    assert got_insight == insight and got_alert == alert
    # the authoring agent received BOTH payloads, in order, exactly.
    assert inbox.payloads == (insight, alert)


# --------------------------------------------------------------------------------------
# AD-17 — every payload carries an injected build stamp; construction without one fails.
# --------------------------------------------------------------------------------------
def test_ad17_stamp_required_and_injected():
    with pytest.raises(ValueError):
        build_insight_payload(subject="numpy", metric_id="staleness_age_days", build_stamp="")
    with pytest.raises(TypeError):
        build_alert_payload(subject="x", severity="high", rule="r")  # type: ignore[call-arg]


def test_ad17_stamp_on_the_wire_envelope(insight: AtlasInsight):
    # The stamp is mirrored into the a2a Message metadata for cheap envelope inspection.
    from google.protobuf import json_format

    meta = json_format.MessageToDict(to_message(insight).metadata)
    assert meta["build_stamp"] == STAMP
    assert meta["atlas_kind"] == "insight"


# --------------------------------------------------------------------------------------
# AD-8 — an insight references a BSL metric by identifier, never re-implements it.
# --------------------------------------------------------------------------------------
def test_ad8_insight_metric_must_be_a_bsl_identifier():
    # every known BSL metric id is accepted…
    for metric_id in METRIC_PROVENANCE:
        assert build_insight_payload(subject="s", metric_id=metric_id, build_stamp=STAMP)
    # …and an unknown identifier is rejected (no ad-hoc metric can enter the channel).
    with pytest.raises(ValueError, match="unknown BSL metric id"):
        build_insight_payload(subject="s", metric_id="totally_made_up_metric", build_stamp=STAMP)


# --------------------------------------------------------------------------------------
# AD-20 — the a2a/ module is the SINGLE schema source: one family, no second dialect.
# --------------------------------------------------------------------------------------
def test_ad20_schema_family_is_defined_in_a2a_module():
    assert AtlasInsight.__module__ == "pyforge.atlas.a2a.schema"
    assert AtlasAlert.__module__ == "pyforge.atlas.a2a.schema"


def test_ad20_no_competing_payload_schema_outside_a2a():
    """No module outside ``a2a/`` may define a class named like an inter-agent payload
    schema (``*Payload`` / ``*Alert`` / ``*Insight``) — that is the "second dialect" the
    architecture review warned against. The single family lives in a2a/schema.py only."""
    offenders: dict[str, list[str]] = {}
    for path in sorted(ATLAS_PKG.rglob("*.py")):
        if str(path.relative_to(ATLAS_PKG)).startswith(A2A_PREFIX):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        named = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
            and node.name.endswith(("Payload", "Alert", "Insight"))
        ]
        if named:
            offenders[str(path.relative_to(ATLAS_PKG))] = named
    assert not offenders, (
        "AD-20 violation — a competing alert/insight payload schema exists outside the "
        f"a2a/ module (the single schema source): {offenders}"
    )


def test_ad20_only_a2a_schema_subclasses_the_base():
    """Belt-and-suspenders: no module re-subclasses the payload base outside a2a/schema."""
    for sub in _BasePayload.__subclasses__():
        assert sub.__module__ == "pyforge.atlas.a2a.schema", (
            f"AD-20 violation — {sub.__name__} extends the payload base outside a2a/schema"
        )


# --------------------------------------------------------------------------------------
# edge cases — degrade with a controlled error, never an uncaught crash.
# --------------------------------------------------------------------------------------
def test_unknown_kind_on_decode_does_not_crash():
    with pytest.raises(A2ADecodeError, match="unknown payload kind"):
        decode_payload('{"kind": "prophecy", "subject": "x", "build_stamp": "t"}')


def test_malformed_json_on_decode_does_not_crash():
    with pytest.raises(A2ADecodeError):
        decode_payload("{not json")


def test_schema_validation_failure_is_controlled():
    # extra/forbidden field → controlled A2ADecodeError, not a raw ValidationError bubbling up.
    with pytest.raises(A2ADecodeError):
        decode_payload('{"kind": "alert", "subject": "x", "build_stamp": "t", "rule": "r", '
                        '"severity": "high", "bogus": 1}')


def test_missing_evidence_is_allowed_and_empty(alert: AtlasAlert):
    a = build_alert_payload(subject="x", severity="low", rule="r", build_stamp=STAMP)
    assert a.evidence == {}
    assert from_message(to_message(a)) == a


def test_none_and_optional_insight_fields_round_trip():
    a = build_insight_payload(subject="x", metric_id="is_actionable", value=None, build_stamp=STAMP)
    restored = from_message(to_message(a))
    assert restored == a and restored.value is None and restored.detail == {}


def test_non_json_native_field_fails_fast_at_construction():
    # a set is not JSON-native — pydantic would silently coerce it to a list (a silent
    # round-trip mutation), so we reject it at construction with a controlled error.
    with pytest.raises(ValueError, match="non-JSON-native"):
        build_insight_payload(
            subject="x", metric_id="is_actionable", value={"s": {1, 2, 3}}, build_stamp=STAMP
        )
    with pytest.raises(ValueError, match="non-JSON-native"):
        build_alert_payload(
            subject="x", severity="low", rule="r", evidence={"o": object()}, build_stamp=STAMP
        )


def test_non_finite_floats_are_rejected():
    # JSON has no NaN/Infinity; pydantic would silently serialize them to null (nan -> None),
    # so they are rejected at construction rather than corrupting the round-trip.
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="non-finite float"):
            build_insight_payload(subject="x", metric_id="is_actionable", value=bad, build_stamp=STAMP)


def test_from_message_without_payload_part_raises():
    import a2a.types as a2a_types

    empty = a2a_types.Message(message_id="x", role=a2a_types.Role.ROLE_AGENT, parts=[])
    with pytest.raises(A2ATransportError, match="no atlas payload"):
        from_message(empty)


def test_large_payload_round_trips(alert: AtlasAlert):
    big = build_alert_payload(
        subject="x",
        severity="critical",
        rule="r",
        evidence={f"k{i}": "v" * 100 for i in range(500)},
        build_stamp=STAMP,
    )
    assert from_message(to_message(big)) == big
