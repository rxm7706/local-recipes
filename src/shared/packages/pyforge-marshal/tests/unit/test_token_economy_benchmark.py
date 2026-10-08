"""Story 28.5 (CAP-9) — pinned wrapped-vs-unwrapped benchmark tests."""

from __future__ import annotations

from dataclasses import replace

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


def test_prompt_cache_hit_rate_computes_fraction():
    assert bench.prompt_cache_hit_rate(input_tokens=900, cache_read_tokens=100) == pytest.approx(0.1)
    assert bench.prompt_cache_hit_rate(input_tokens=0, cache_read_tokens=0) is None


def test_build_per_layer_artifact_voids_one_leg_only():
    baseline = replace(
        _leg(layers_mode="off", story_weighted_tokens=5000, task_phase="done"),
        prompt_cache_hit_rate=0.25,
        story_cost_estimate_usd=1.0,
    )
    isolated_ok = replace(
        _leg(layers_mode="on", story_weighted_tokens=4200, task_phase="done"),
        prompt_cache_hit_rate=0.5,
        story_cost_estimate_usd=0.8,
        context_layers=bench.context_layers_only_layer("wire"),
    )
    isolated_bad = replace(
        _leg(layers_mode="on", story_weighted_tokens=4100, task_phase="deferred"),
        prompt_cache_hit_rate=0.1,
        context_layers=bench.context_layers_only_layer("output"),
    )
    isolated = {name: isolated_ok for name in policy.CONTEXT_LAYER_NAMES}
    isolated["output"] = isolated_bad
    artifact = bench.build_per_layer_artifact(
        baseline_leg=baseline,
        isolated_legs=isolated,
        environment={"repo_root": "/tmp"},
        generated_at=__import__("datetime").datetime(2026, 10, 8, 12, 0, 0, tzinfo=__import__("datetime").UTC),
    )
    assert artifact.schema == bench.PER_LAYER_ARTIFACT_SCHEMA
    assert len(artifact.layer_legs) == 5
    wire_row = next(r for r in artifact.layer_legs if r["layer"] == "wire")
    output_row = next(r for r in artifact.layer_legs if r["layer"] == "output")
    assert wire_row["void"] is False
    assert wire_row["weighted_tokens_delta"] == -800
    assert wire_row["prompt_cache_hit_rate_baseline"] == 0.25
    assert wire_row["prompt_cache_hit_rate_isolated"] == 0.5
    assert output_row["void"] is True
    assert output_row["weighted_tokens_delta"] is None
