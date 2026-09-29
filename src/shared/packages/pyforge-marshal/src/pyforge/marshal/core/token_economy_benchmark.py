"""The pinned wrapped-vs-unwrapped benchmark (Story 28.5, CAP-9).

Pure comparison and artifact shaping for a re-runnable counterfactual:
the same pinned story run twice — token-economy layers off, then on —
with an equivalence gate that voids the savings comparison when the on-leg
does not land identically to the off-leg (verdict, gate results, reviewer).

Weighted-token accounting reuses bmad-loop's existing ``weighted_total``
(``cache_read_weight = 0.1`` default); per-layer rows map Story 28.4's
``LayerSavings`` fields onto ``CONTEXT_LAYER_NAMES``. This module does no
I/O, no subprocess, no clock (AD-4).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Literal, TypedDict

from ..ports.harness import LayerSavings
from . import policy

LEDGER_KEY = "28-5-the-pinned-wrapped-vs-unwrapped-benchmark"
# Reuses the adapter conformance smoke story — a minimal, station-owned pin
# that already exists in every loop home's harness profile registry.
PINNED_BENCHMARK_STORY_KEY = "1-1-marshal-conformance-smoke"
ARTIFACT_SCHEMA = "marshal-token-economy-benchmark/v1"
DEFAULT_CACHE_READ_WEIGHT = 0.1

LayersMode = Literal["off", "on"]

#: Each context layer's savings field on ``LayerSavings`` (Story 28.4).
_LAYER_SAVINGS_ATTR: dict[str, str] = {
    "wire": "wire_compression_saved",
    "output": "output_compression_saved",
    "structure-graph": "graph_hits_vs_file_reads",
    "derived-context": "derived_context_cache_hits",
    "planning-graph": "planning_graph_tokens_saved",
}


class LayerComparisonRow(TypedDict, total=False):
    layer: str
    weighted_tokens_before: int | None
    weighted_tokens_after: int | None
    weighted_tokens_delta: int | None
    savings_before: object
    savings_after: object


@dataclass(frozen=True)
class BenchmarkLegRecord:
    """One benchmark leg's recorded facts — off or on."""

    layers_mode: LayersMode
    story_key: str
    task_phase: str
    reviewer_ran: bool
    gate_fingerprint: tuple[str, ...]
    story_weighted_tokens: int | None
    run_weighted_tokens: int
    cache_read_weight: float
    layer_savings: LayerSavings | None
    context_layers: Mapping[str, Mapping[str, object]]
    run_id: str | None = None
    policy_digest: str | None = None
    # Story 28.10 (CAP-11): advisory dollar estimates when catalog declared
    story_cost_estimate_usd: float | None = None
    layer_savings_usd: Mapping[str, float] | None = None


@dataclass(frozen=True)
class EquivalenceResult:
    passed: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class BenchmarkArtifact:
    """The comparison artifact CAP-9 emits."""

    schema: str
    ledger_key: str
    pinned_story_key: str
    generated_at: str
    policy_digest: str | None
    environment: Mapping[str, object]
    equivalence_gate: EquivalenceResult
    void: bool
    legs: Mapping[str, BenchmarkLegRecord]
    layer_comparison: tuple[LayerComparisonRow, ...]
    totals: Mapping[str, int | None]

    def to_json_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "ledger_key": self.ledger_key,
            "pinned_story_key": self.pinned_story_key,
            "generated_at": self.generated_at,
            "policy_digest": self.policy_digest,
            "environment": dict(self.environment),
            "equivalence_gate": {
                "passed": self.equivalence_gate.passed,
                "reasons": list(self.equivalence_gate.reasons),
            },
            "void": self.void,
            "legs": {key: _leg_to_dict(leg) for key, leg in self.legs.items()},
            "layer_comparison": list(self.layer_comparison),
            "totals": dict(self.totals),
        }


def _leg_to_dict(leg: BenchmarkLegRecord) -> dict[str, object]:
    payload: dict[str, object] = {
        "layers_mode": leg.layers_mode,
        "story_key": leg.story_key,
        "task_phase": leg.task_phase,
        "reviewer_ran": leg.reviewer_ran,
        "gate_fingerprint": list(leg.gate_fingerprint),
        "story_weighted_tokens": leg.story_weighted_tokens,
        "run_weighted_tokens": leg.run_weighted_tokens,
        "cache_read_weight": leg.cache_read_weight,
        "context_layers": {name: dict(entry) for name, entry in leg.context_layers.items()},
        "run_id": leg.run_id,
        "policy_digest": leg.policy_digest,
    }
    if leg.layer_savings is not None:
        payload["layer_savings"] = asdict(leg.layer_savings)
    else:
        payload["layer_savings"] = None
    if leg.story_cost_estimate_usd is not None:
        payload["story_cost_estimate_usd"] = leg.story_cost_estimate_usd
    if leg.layer_savings_usd is not None:
        payload["layer_savings_usd"] = dict(leg.layer_savings_usd)
    return payload


def digest_context_layers(context_layers: Mapping[str, Mapping[str, object]]) -> str:
    """Stable digest of a resolved ``[context]`` block for reproducibility."""
    canonical = json.dumps(
        {name: dict(context_layers[name]) for name in policy.CONTEXT_LAYER_NAMES if name in context_layers},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _savings_value(layer_savings: LayerSavings | None, layer: str) -> object:
    if layer_savings is None:
        return None
    attr = _LAYER_SAVINGS_ATTR[layer]
    return getattr(layer_savings, attr)


def build_layer_comparison(off_leg: BenchmarkLegRecord, on_leg: BenchmarkLegRecord) -> tuple[LayerComparisonRow, ...]:
    """Per-layer before/after rows (off = before, on = after)."""
    rows: list[LayerComparisonRow] = []
    for layer in policy.CONTEXT_LAYER_NAMES:
        before = _savings_value(off_leg.layer_savings, layer)
        after = _savings_value(on_leg.layer_savings, layer)
        row: LayerComparisonRow = {
            "layer": layer,
            "weighted_tokens_before": off_leg.story_weighted_tokens,
            "weighted_tokens_after": on_leg.story_weighted_tokens,
            "savings_before": before,
            "savings_after": after,
        }
        if off_leg.story_weighted_tokens is not None and on_leg.story_weighted_tokens is not None:
            row["weighted_tokens_delta"] = on_leg.story_weighted_tokens - off_leg.story_weighted_tokens
        else:
            row["weighted_tokens_delta"] = None
        rows.append(row)
    return tuple(rows)


def check_equivalence(off_leg: BenchmarkLegRecord, on_leg: BenchmarkLegRecord) -> EquivalenceResult:
    """Equivalence gate — comparison is void when this fails."""
    reasons: list[str] = []
    if off_leg.story_key != on_leg.story_key:
        reasons.append(f"story key mismatch: off={off_leg.story_key!r} on={on_leg.story_key!r}")
    if off_leg.task_phase != on_leg.task_phase:
        reasons.append(f"verdict phase mismatch: off={off_leg.task_phase!r} on={on_leg.task_phase!r}")
    if off_leg.task_phase != "done":
        reasons.append(f"off leg did not land (phase={off_leg.task_phase!r})")
    if on_leg.task_phase != "done":
        reasons.append(f"on leg did not land (phase={on_leg.task_phase!r})")
    if off_leg.gate_fingerprint != on_leg.gate_fingerprint:
        reasons.append(
            f"gate results differ: off={list(off_leg.gate_fingerprint)!r} on={list(on_leg.gate_fingerprint)!r}"
        )
    if not off_leg.reviewer_ran:
        reasons.append("off leg: independent reviewer did not run")
    if not on_leg.reviewer_ran:
        reasons.append("on leg: independent reviewer did not run")
    return EquivalenceResult(passed=not reasons, reasons=tuple(reasons))


def build_totals(off_leg: BenchmarkLegRecord, on_leg: BenchmarkLegRecord) -> dict[str, int | None]:
    delta: int | None = None
    if off_leg.story_weighted_tokens is not None and on_leg.story_weighted_tokens is not None:
        delta = on_leg.story_weighted_tokens - off_leg.story_weighted_tokens
    return {
        "weighted_tokens_before": off_leg.story_weighted_tokens,
        "weighted_tokens_after": on_leg.story_weighted_tokens,
        "weighted_tokens_delta": delta,
        "run_weighted_tokens_before": off_leg.run_weighted_tokens,
        "run_weighted_tokens_after": on_leg.run_weighted_tokens,
        "story_cost_estimate_usd_before": off_leg.story_cost_estimate_usd,
        "story_cost_estimate_usd_after": on_leg.story_cost_estimate_usd,
    }


def build_artifact(
    *,
    off_leg: BenchmarkLegRecord,
    on_leg: BenchmarkLegRecord,
    environment: Mapping[str, object],
    generated_at: datetime | None = None,
    policy_digest: str | None = None,
) -> BenchmarkArtifact:
    """Assemble the full comparison artifact."""
    equivalence = check_equivalence(off_leg, on_leg)
    instant = generated_at or datetime.now(tz=UTC)
    digest = policy_digest or off_leg.policy_digest or on_leg.policy_digest
    return BenchmarkArtifact(
        schema=ARTIFACT_SCHEMA,
        ledger_key=LEDGER_KEY,
        pinned_story_key=off_leg.story_key,
        generated_at=instant.strftime("%Y-%m-%dT%H:%M:%SZ"),
        policy_digest=digest,
        environment=environment,
        equivalence_gate=equivalence,
        void=not equivalence.passed,
        legs={"layers_off": off_leg, "layers_on": on_leg},
        layer_comparison=build_layer_comparison(off_leg, on_leg),
        totals=build_totals(off_leg, on_leg),
    )


def leg_from_mapping(payload: Mapping[str, object]) -> BenchmarkLegRecord:
    """Rehydrate a leg from JSON (reproducibility / recorded legs)."""
    savings_raw = payload.get("layer_savings")
    layer_savings: LayerSavings | None = None
    if isinstance(savings_raw, Mapping):
        layer_savings = LayerSavings(
            output_compression_saved=_optional_measurement(savings_raw.get("output_compression_saved")),
            wire_compression_saved=_optional_measurement(savings_raw.get("wire_compression_saved")),
            graph_hits_vs_file_reads=_optional_graph_stats(
                savings_raw.get("graph_hits_vs_file_reads"),
                savings_raw,
            ),
            derived_context_cache_hits=_optional_measurement(savings_raw.get("derived_context_cache_hits")),
            planning_graph_tokens_saved=_optional_measurement(savings_raw.get("planning_graph_tokens_saved")),
        )
    context_raw = payload.get("context_layers")
    context_layers: dict[str, dict[str, object]] = {}
    if isinstance(context_raw, Mapping):
        for name, entry in context_raw.items():
            if isinstance(entry, Mapping):
                context_layers[str(name)] = dict(entry)
    gate_raw = payload.get("gate_fingerprint")
    gate_fingerprint: tuple[str, ...] = ()
    if isinstance(gate_raw, Sequence) and not isinstance(gate_raw, (str, bytes)):
        gate_fingerprint = tuple(str(item) for item in gate_raw)
    mode = payload.get("layers_mode")
    if mode not in ("off", "on"):
        raise ValueError(f"invalid layers_mode: {mode!r}")
    return BenchmarkLegRecord(
        layers_mode=mode,
        story_key=str(payload["story_key"]),
        task_phase=str(payload["task_phase"]),
        reviewer_ran=bool(payload["reviewer_ran"]),
        gate_fingerprint=gate_fingerprint,
        story_weighted_tokens=_optional_int(payload.get("story_weighted_tokens")),
        run_weighted_tokens=int(payload["run_weighted_tokens"]),
        cache_read_weight=float(payload.get("cache_read_weight", DEFAULT_CACHE_READ_WEIGHT)),
        layer_savings=layer_savings,
        context_layers=context_layers,
        run_id=_optional_str(payload.get("run_id")),
        policy_digest=_optional_str(payload.get("policy_digest")),
        story_cost_estimate_usd=_optional_float(payload.get("story_cost_estimate_usd")),
        layer_savings_usd=_optional_float_mapping(payload.get("layer_savings_usd")),
    )


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_measurement(value: object) -> int | str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except TypeError, ValueError:
        return None


def _optional_graph_stats(value: object, savings_raw: Mapping[str, object]) -> tuple[int, int] | str | None:
    if isinstance(value, str):
        return value
    hits = savings_raw.get("graph_hits")
    if value is None and isinstance(hits, int):
        reads_raw = savings_raw.get("file_reads", 0)
        try:
            reads = int(reads_raw) if reads_raw is not None else 0
        except TypeError, ValueError:
            return None
        return (hits, reads)
    return _optional_pair(value)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_float_mapping(value: object) -> dict[str, float] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"expected a mapping, got {value!r}")
    return {str(key): float(entry) for key, entry in value.items()}


def _optional_pair(value: object) -> tuple[int, int] | None:
    if value is None:
        return None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 2:
        return (int(value[0]), int(value[1]))
    raise ValueError(f"expected a two-element sequence, got {value!r}")
