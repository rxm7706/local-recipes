"""Story 28.5 (CAP-9) — pinned wrapped-vs-unwrapped benchmark tests."""

from __future__ import annotations

import pytest

from pyforge.marshal.core import policy
from pyforge.marshal.core import token_economy_benchmark as bench
from pyforge.marshal.ports.harness import LayerSavings


def _all_off_layers() -> dict[str, dict[str, object]]:
    return {name: {"enabled": False, "aggressiveness": "medium"} for name in policy.CONTEXT_LAYER_NAMES}


def _all_on_layers() -> dict[str, dict[str, object]]:
    return {name: {"enabled": True, "aggressiveness": "medium"} for name in policy.CONTEXT_LAYER_NAMES}


def _leg(
    *,
    layers_mode: bench.LayersMode,
    story_weighted_tokens: int | None,
    layer_savings: LayerSavings | None = None,
    task_phase: str = "done",
    reviewer_ran: bool = True,
    gate_fingerprint: tuple[str, ...] = (),
) -> bench.BenchmarkLegRecord:
    return bench.BenchmarkLegRecord(
        layers_mode=layers_mode,
        story_key=bench.PINNED_BENCHMARK_STORY_KEY,
        task_phase=task_phase,
        reviewer_ran=reviewer_ran,
        gate_fingerprint=gate_fingerprint,
        story_weighted_tokens=story_weighted_tokens,
        run_weighted_tokens=story_weighted_tokens or 0,
        cache_read_weight=bench.DEFAULT_CACHE_READ_WEIGHT,
        layer_savings=layer_savings,
        context_layers=_all_off_layers() if layers_mode == "off" else _all_on_layers(),
    )


def test_build_layer_comparison_emits_all_five_layers():
    off = _leg(
        layers_mode="off",
        story_weighted_tokens=5000,
        layer_savings=None,
    )
    on = _leg(
        layers_mode="on",
        story_weighted_tokens=3500,
        layer_savings=LayerSavings(
            wire_compression_saved=2048,
            output_compression_saved=1024,
            graph_hits_vs_file_reads=(12, 3),
        ),
    )
    rows = bench.build_layer_comparison(off, on)
    assert len(rows) == len(policy.CONTEXT_LAYER_NAMES)
    wire = next(r for r in rows if r["layer"] == "wire")
    assert wire["savings_before"] is None
    assert wire["savings_after"] == 2048
    assert wire["weighted_tokens_before"] == 5000
    assert wire["weighted_tokens_after"] == 3500
    assert wire["weighted_tokens_delta"] == -1500


def test_equivalence_gate_passes_when_legs_match():
    off = _leg(layers_mode="off", story_weighted_tokens=5000)
    on = _leg(layers_mode="on", story_weighted_tokens=3500)
    result = bench.check_equivalence(off, on)
    assert result.passed
    assert result.reasons == ()


def test_equivalence_gate_fails_on_verdict_mismatch():
    off = _leg(layers_mode="off", story_weighted_tokens=5000, task_phase="done")
    on = _leg(layers_mode="on", story_weighted_tokens=3500, task_phase="deferred")
    result = bench.check_equivalence(off, on)
    assert not result.passed
    assert any("phase mismatch" in reason for reason in result.reasons)


def test_equivalence_gate_fails_when_reviewer_skipped():
    off = _leg(layers_mode="off", story_weighted_tokens=5000, reviewer_ran=False)
    on = _leg(layers_mode="on", story_weighted_tokens=3500, reviewer_ran=True)
    result = bench.check_equivalence(off, on)
    assert not result.passed
    assert any("reviewer" in reason for reason in result.reasons)


def test_equivalence_gate_fails_on_gate_fingerprint_mismatch():
    off = _leg(layers_mode="off", story_weighted_tokens=5000, gate_fingerprint=("a",))
    on = _leg(layers_mode="on", story_weighted_tokens=3500, gate_fingerprint=("b",))
    result = bench.check_equivalence(off, on)
    assert not result.passed
    assert any("gate results differ" in reason for reason in result.reasons)


def test_build_artifact_voids_comparison_when_equivalence_fails():
    off = _leg(layers_mode="off", story_weighted_tokens=5000)
    on = _leg(layers_mode="on", story_weighted_tokens=3500, task_phase="deferred")
    artifact = bench.build_artifact(
        off_leg=off,
        on_leg=on,
        environment={"repo_root": "/tmp"},
    )
    assert artifact.void
    assert not artifact.equivalence_gate.passed
    assert artifact.schema == bench.ARTIFACT_SCHEMA
    assert artifact.ledger_key == bench.LEDGER_KEY


def test_build_artifact_is_reproducible_from_round_trip_json():
    off = _leg(
        layers_mode="off",
        story_weighted_tokens=5000,
        layer_savings=LayerSavings(wire_compression_saved=100),
    )
    on = _leg(
        layers_mode="on",
        story_weighted_tokens=3200,
        layer_savings=LayerSavings(wire_compression_saved=2500, output_compression_saved=900),
    )
    artifact = bench.build_artifact(
        off_leg=off,
        on_leg=on,
        environment={"repo_root": "/tmp", "pinned_policy": "digest-abc"},
        generated_at=__import__("datetime").datetime(2026, 9, 1, 12, 0, 0, tzinfo=__import__("datetime").UTC),
        policy_digest="digest-abc",
    )
    payload = artifact.to_json_dict()
    off2 = bench.leg_from_mapping(payload["legs"]["layers_off"])
    on2 = bench.leg_from_mapping(payload["legs"]["layers_on"])
    artifact2 = bench.build_artifact(
        off_leg=off2,
        on_leg=on2,
        environment={"repo_root": "/tmp", "pinned_policy": "digest-abc"},
        generated_at=__import__("datetime").datetime(2026, 9, 1, 12, 0, 0, tzinfo=__import__("datetime").UTC),
        policy_digest="digest-abc",
    )
    assert artifact2.to_json_dict() == payload


def test_digest_context_layers_is_stable():
    layers = _all_on_layers()
    assert bench.digest_context_layers(layers) == bench.digest_context_layers(layers)
    off = _all_off_layers()
    assert bench.digest_context_layers(layers) != bench.digest_context_layers(off)


def test_leg_from_mapping_rejects_invalid_layers_mode():
    with pytest.raises(ValueError, match="layers_mode"):
        bench.leg_from_mapping(
            {
                "layers_mode": "maybe",
                "story_key": "x",
                "task_phase": "done",
                "reviewer_ran": True,
                "run_weighted_tokens": 0,
            }
        )
