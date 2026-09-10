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
    "loop_home_from_run_dir",
    "read_caveman_output_saved",
    "read_cocoindex_cache_hits",
    "read_codegraph_hits_vs_reads",
    "read_headroom_wire_saved",
    "read_planning_graph_tokens_saved",
    "read_dispatch_idle_timing",
)

COCOINDEX_INDEX_RELPATH = ".claude/data/pyforge-scribe/cocoindex-index.json"
GRAPH_STORE_RELPATH = ".claude/data/pyforge-scribe/graph.json"
PLANNING_GRAPH_TELEMETRY_RELPATH = (
    ".claude/data/pyforge-marshal/planning-graph/last-retrieval.json"
)
CODEGRAPH_STATS_RELPATH = ".claude/data/pyforge-marshal/layer-savings/codegraph.json"

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
