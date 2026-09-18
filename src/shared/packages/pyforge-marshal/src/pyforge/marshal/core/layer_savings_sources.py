"""Per-layer savings readers for CAP-7 (Story 33.1).

Pure file readers -- no subprocess, no imports of headroom/cocoindex/graphify
(AD-4). Each getter returns a measured integer (or pair for structure-graph)
when its source is present, or a **named unavailable reason** string when the
source is genuinely absent. ``None`` is never returned for an attempted read:
that distinction is reserved for "layer not queried" at the ``LayerSavings``
aggregate level.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ..seed.model.kit import (
    CAVEMAN_SKILL_RELPATH,
    CCR_STORE_RELPATH,
    CODEGRAPH_INDEX_RELPATH,
)

__all__ = (
    "COCOINDEX_INDEX_RELPATH",
    "GRAPH_STORE_RELPATH",
    "PLANNING_GRAPH_TELEMETRY_RELPATH",
    "CODEGRAPH_STATS_RELPATH",
    "SILENT_LAYER_KEYS",
    "CONFIGURED_LAYER_KEYS",
    "HARNESS_CURRENCY",
    "UNKNOWN_HARNESS_CURRENCY",
    "loop_home_from_run_dir",
    "read_caveman_output_saved",
    "read_cocoindex_cache_hits",
    "read_codegraph_hits_vs_reads",
    "read_headroom_wire_saved",
    "read_planning_graph_tokens_saved",
    "read_dispatch_idle_timing",
    "classify_layer_kind",
    "currency_for_harness",
    "read_rollup_by_harness",
)

COCOINDEX_INDEX_RELPATH = ".claude/data/pyforge-scribe/cocoindex-index.json"
GRAPH_STORE_RELPATH = ".claude/data/pyforge-scribe/graph.json"
PLANNING_GRAPH_TELEMETRY_RELPATH = (
    ".claude/data/pyforge-marshal/planning-graph/last-retrieval.json"
)
CODEGRAPH_STATS_RELPATH = ".claude/data/pyforge-marshal/layer-savings/codegraph.json"

# Story 46.5 (CAP-193): the journal taxonomy distinguishing the 4
# harness-agnostic repo-default layers (Story 46.4's "silent" tier -- they
# run unconditionally, with no per-harness capability check) from the 1
# capability/config-resolved layer (`wire_compression_saved`, gated on
# `[wrapper]` policy AND the harness profile declaring wire support). These
# are the SAME 5 field names ``ports.harness.LayerSavings`` carries --
# ``classify_layer_kind`` is the single source of truth mapping each to its
# tier.
SILENT_LAYER_KEYS = (
    "output_compression_saved",
    "graph_hits_vs_file_reads",
    "derived_context_cache_hits",
    "planning_graph_tokens_saved",
)
CONFIGURED_LAYER_KEYS = ("wire_compression_saved",)

# Story 46.5: the per-harness binding currency table -- a Cursor-first
# station's savings are quota-burn, never a Claude-shaped USD number.
# ``UNKNOWN_HARNESS_CURRENCY`` is the honest degrade for an absent or
# unrecognized harness name (``currency_for_harness`` never raises), mirroring
# this epic's "a repo default can never claim a wrap a harness can't perform"
# ethos rather than silently defaulting to USD.
HARNESS_CURRENCY: dict[str, str] = {
    "claude": "usd",
    "cursor": "quota-burn",
    "copilot": "quota-burn",
    "gemini": "request-count",
    "devin": "acus",
}
UNKNOWN_HARNESS_CURRENCY = "unknown"

IntSavings = int | str
GraphStats = tuple[int, int] | str


def loop_home_from_run_dir(run_dir: Path) -> Path:
    """Resolve the loop home from a bmad-loop run directory."""
    return run_dir.parent.parent.parent


def read_headroom_wire_saved(home: Path) -> IntSavings:
    """Layer 1: sum wire compression savings from the loop-home CCR sqlite store."""
    store_dir = home / CCR_STORE_RELPATH
    db_path = store_dir / "ccr_store.db"
    if not db_path.is_file():
        if not store_dir.is_dir():
            return "ccr-store-directory-missing"
        return "ccr-store-database-missing"
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return "ccr-store-database-unreadable"
    try:
        rows = conn.execute("SELECT entry_json FROM ccr_entries").fetchall()
    except sqlite3.Error:
        return "ccr-store-schema-unreadable"
    finally:
        conn.close()
    if not rows:
        return 0
    total_saved = 0
    for (entry_json,) in rows:
        try:
            payload = json.loads(entry_json)
        except (json.JSONDecodeError, TypeError):
            continue
        original = payload.get("original_tokens")
        compressed = payload.get("compressed_tokens")
        if isinstance(original, int) and isinstance(compressed, int):
            total_saved += max(0, original - compressed)
    return total_saved


def read_caveman_output_saved(home: Path) -> IntSavings:
    """Layer 0: caveman/output compression delta from headroom's output ledger."""
    skill_path = home / CAVEMAN_SKILL_RELPATH
    if not skill_path.is_file():
        return "caveman-skill-not-deployed"
    ledger_path = home / CCR_STORE_RELPATH / "output_savings.json"
    if not ledger_path.is_file():
        return "output-savings-ledger-missing"
    try:
        payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "output-savings-ledger-unreadable"
    estimate = payload.get("estimate") if isinstance(payload, dict) else None
    if isinstance(estimate, dict):
        tokens_saved = estimate.get("tokens_saved")
        if isinstance(tokens_saved, int):
            return tokens_saved
    tokens_saved = payload.get("tokens_saved") if isinstance(payload, dict) else None
    if isinstance(tokens_saved, int):
        return tokens_saved
    return "output-savings-not-recorded"


def read_codegraph_hits_vs_reads(home: Path) -> GraphStats:
    """Layer 2: structure-graph hits vs file reads."""
    stats_path = home / CODEGRAPH_STATS_RELPATH
    if stats_path.is_file():
        try:
            payload = json.loads(stats_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return "codegraph-stats-unreadable"
        if isinstance(payload, dict):
            hits = payload.get("graph_hits", payload.get("hits"))
            reads = payload.get("file_reads", payload.get("reads"))
            if isinstance(hits, int) and isinstance(reads, int):
                return (hits, reads)
        return "codegraph-stats-shape-unrecognized"
    index_path = home / CODEGRAPH_INDEX_RELPATH
    if not index_path.is_file():
        return "codegraph-index-missing"
    return "codegraph-stats-not-recorded"


def read_cocoindex_cache_hits(home: Path) -> IntSavings:
    """Layer 3: derived-context cache hits from the cocoindex index sidecar."""
    index_path = home / COCOINDEX_INDEX_RELPATH
    if not index_path.is_file():
        return "cocoindex-index-missing"
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "cocoindex-index-unreadable"
    if isinstance(payload, dict):
        cache_hits = payload.get("cache_hits")
        if isinstance(cache_hits, int):
            return cache_hits
        skipped = payload.get("skipped_artifacts")
        if isinstance(skipped, list):
            return len(skipped)
    return "cocoindex-cache-hits-not-recorded"


def read_planning_graph_tokens_saved(home: Path) -> IntSavings:
    """Layer 4: planning-graph tokens saved from the last grounded retrieval."""
    telemetry_path = home / PLANNING_GRAPH_TELEMETRY_RELPATH
    if not telemetry_path.is_file():
        graph_path = home / GRAPH_STORE_RELPATH
        if not graph_path.is_file():
            return "planning-graph-store-missing"
        return "planning-graph-retrieval-not-recorded"
    try:
        payload = json.loads(telemetry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "planning-graph-telemetry-unreadable"
    if isinstance(payload, dict):
        tokens_saved = payload.get("tokens_saved")
        if isinstance(tokens_saved, int):
            return tokens_saved
        if payload.get("grounded") is True:
            return 0
    return "planning-graph-tokens-not-recorded"


def read_dispatch_idle_timing(
    repo_root: Path, *, project_slug: str = "pyforge-marshal"
) -> dict[str, object]:
    """Q-14: one wave of per-session timing from dispatch journals."""
    runs_dir = (
        repo_root
        / "_bmad-output/projects"
        / project_slug
        / "implementation-artifacts/dispatch-runs"
    )
    if not runs_dir.is_dir():
        return {
            "status": "no-dispatch-journals",
            "sessions": [],
            "recommended_idle_threshold_minutes": 25,
        }
    sessions: list[dict[str, object]] = []
    for journal_path in sorted(runs_dir.glob("*/journal.jsonl")):
        durations: list[float] = []
        for line in journal_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = entry.get("payload")
            if not isinstance(payload, dict):
                continue
            idle_seconds = payload.get("idle_seconds")
            if isinstance(idle_seconds, (int, float)):
                durations.append(float(idle_seconds))
        if durations:
            sessions.append(
                {
                    "run_id": journal_path.parent.name,
                    "idle_samples": len(durations),
                    "max_idle_seconds": max(durations),
                    "median_idle_seconds": sorted(durations)[len(durations) // 2],
                }
            )
    return {
        "status": "ok" if sessions else "no-idle-samples",
        "sessions": sessions,
        "recommended_idle_threshold_minutes": 25,
    }


def classify_layer_kind(layer_key: str) -> str:
    """Story 46.5: the single source of truth for the silent-vs-configured
    taxonomy. DOES raise on an unrecognized key -- unlike
    ``currency_for_harness``, an unknown ``LayerSavings`` field name is a
    programmer error (a new layer added to ``ports/harness.py`` without
    updating this taxonomy), not user-facing data absence, and should fail
    loud rather than silently mis-bucket."""
    if layer_key in SILENT_LAYER_KEYS:
        return "silent"
    if layer_key in CONFIGURED_LAYER_KEYS:
        return "configured"
    raise ValueError(f"unrecognized layer key: {layer_key!r}")


def currency_for_harness(profile_name: str | None) -> str:
    """Story 46.5: the per-harness binding-currency lookup. Never raises --
    ``None`` or an unrecognized harness name both degrade to the honest
    ``UNKNOWN_HARNESS_CURRENCY`` label rather than a crash or a silent USD
    default that would misrepresent a non-Claude station's savings."""
    if profile_name is None:
        return UNKNOWN_HARNESS_CURRENCY
    return HARNESS_CURRENCY.get(profile_name, UNKNOWN_HARNESS_CURRENCY)


# Story 46.5: the kinds this reader correlates, both already durably written
# into the SAME per-run ``journal.jsonl`` (``cli/dispatch.py``'s
# ``dispatch-launch`` outcome, ``supervisor/__main__.py``'s ``budget-usage``
# observations) -- hardcoded locally rather than imported, matching this
# module's own "pure JSONL reader, no domain-model import" discipline
# (`cli/status.py` redeclares its own local ``_BUDGET_USAGE_KIND`` for the
# identical reason).
_DISPATCH_LAUNCH_KIND = "dispatch-launch"
_BUDGET_USAGE_KIND = "budget-usage"
_OUTCOME_PHASE = "outcome"

_ALL_LAYER_FIELD_NAMES = SILENT_LAYER_KEYS + CONFIGURED_LAYER_KEYS


def _extract_layer_value(
    layer_savings: dict[str, object], field_name: str
) -> object | None:
    """One ``LayerSavings`` field's raw value out of a journal-written
    ``layer_savings`` payload dict, honoring
    ``supervisor/__main__.py::_layer_savings_payload``'s on-wire split of
    ``graph_hits_vs_file_reads`` into two sibling keys (``graph_hits``,
    ``file_reads``) when the value is a measured ``(hits, reads)`` pair
    rather than an unavailable-reason string -- the same normalization
    ``cli/status.py::_format_savings_summary`` already performs. Returns
    ``None`` when the field is absent from this payload (nothing to bucket)."""
    if field_name == "graph_hits_vs_file_reads":
        if "graph_hits_vs_file_reads" in layer_savings:
            return layer_savings["graph_hits_vs_file_reads"]
        if "graph_hits" in layer_savings and "file_reads" in layer_savings:
            return (layer_savings["graph_hits"], layer_savings["file_reads"])
        return None
    return layer_savings.get(field_name)


def _bucket_layer_savings(
    layer_savings: dict[str, object],
    silent: dict[str, object],
    configured: dict[str, object],
) -> None:
    """Classify and accumulate one run's ``layer_savings`` payload into the
    caller's ``silent``/``configured`` dicts, keyed by field name, each
    value a list of the raw per-run readings (string unavailable-reasons and
    numeric measurements alike -- no lossy aggregation)."""
    for field_name in _ALL_LAYER_FIELD_NAMES:
        value = _extract_layer_value(layer_savings, field_name)
        if value is None:
            continue
        target = silent if classify_layer_kind(field_name) == "silent" else configured
        target.setdefault(field_name, []).append(value)


def read_rollup_by_harness(
    repo_root: Path, *, project_slug: str = "pyforge-marshal"
) -> dict[str, object]:
    """Story 46.5 (CAP-193): per-harness savings rollup, keyed by binding
    currency -- never a cross-harness summed total.

    Mirrors ``read_dispatch_idle_timing``'s manual-JSONL-scan idiom. Per run
    under ``dispatch-runs/*/journal.jsonl``: extracts ``harness_profile``
    from the ``dispatch-launch`` kind's OUTCOME-phase entry, and the
    ``layer_savings`` dict from that run's LAST ``budget-usage``-kind entry
    (last-write-wins per run, matching
    ``cli/status.py::_gather_run_journal_facts``'s own convention). A run
    missing either is skipped entirely -- an incomplete run contributes no
    partial data, never an ``"unknown"`` bucket. Each present layer value is
    classified silent/configured via ``classify_layer_kind`` and bucketed
    under its harness's own ``currency`` (via ``currency_for_harness``)."""
    runs_dir = (
        repo_root
        / "_bmad-output/projects"
        / project_slug
        / "implementation-artifacts/dispatch-runs"
    )
    if not runs_dir.is_dir():
        return {"status": "no-dispatch-journals", "harnesses": {}}

    harnesses: dict[str, dict[str, object]] = {}

    for journal_path in sorted(runs_dir.glob("*/journal.jsonl")):
        harness_profile: str | None = None
        last_layer_savings: dict[str, object] | None = None
        for line in journal_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(entry, dict):
                continue
            payload = entry.get("payload")
            if not isinstance(payload, dict):
                continue
            kind = entry.get("kind")
            if kind == _DISPATCH_LAUNCH_KIND and entry.get("phase") == _OUTCOME_PHASE:
                profile = payload.get("harness_profile")
                if isinstance(profile, str) and profile:
                    harness_profile = profile
            elif kind == _BUDGET_USAGE_KIND:
                layer_savings = payload.get("layer_savings")
                if isinstance(layer_savings, dict):
                    # Last-write-wins per run: later lines overwrite earlier
                    # ones, matching `_gather_run_journal_facts`'s own
                    # `usage_entries[-1]` convention.
                    last_layer_savings = layer_savings

        if harness_profile is None or last_layer_savings is None:
            continue

        bucket = harnesses.setdefault(
            harness_profile,
            {
                "currency": currency_for_harness(harness_profile),
                "silent": {},
                "configured": {},
                "runs": 0,
            },
        )
        bucket["runs"] = int(bucket["runs"]) + 1  # type: ignore[arg-type]
        _bucket_layer_savings(last_layer_savings, bucket["silent"], bucket["configured"])  # type: ignore[arg-type]

    if not harnesses:
        return {"status": "no-savings-samples", "harnesses": {}}

    return {"status": "ok", "harnesses": harnesses}
