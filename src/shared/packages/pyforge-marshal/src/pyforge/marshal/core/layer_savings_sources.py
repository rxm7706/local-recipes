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

# Story 46.5 (CAP-193): the two entry kinds this module joins, read-only, out
# of the SAME per-run `journal.jsonl` `cli/dispatch.py` / `supervisor/
# __main__.py` already write (`core/dispatch.py::KIND_DISPATCH_LAUNCH` and
# `supervisor/__main__.py::_BUDGET_USAGE_KIND`'s own values) -- hardcoded
# here, not imported, mirroring this module's own "no `core/journal.py`
# domain-model import" rule (module docstring) the same way
# `read_dispatch_idle_timing` hand-reads `entry["payload"]` instead of
# importing `JournalEntry`.
_DISPATCH_LAUNCH_KIND = "dispatch-launch"
_BUDGET_USAGE_KIND = "budget-usage"
_OUTCOME_PHASE = "outcome"

COCOINDEX_INDEX_RELPATH = ".claude/data/pyforge-scribe/cocoindex-index.json"
GRAPH_STORE_RELPATH = ".claude/data/pyforge-scribe/graph.json"
PLANNING_GRAPH_TELEMETRY_RELPATH = ".claude/data/pyforge-marshal/planning-graph/last-retrieval.json"
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
        except json.JSONDecodeError, TypeError:
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
    except OSError, json.JSONDecodeError:
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
        except OSError, json.JSONDecodeError:
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
    except OSError, json.JSONDecodeError:
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
    except OSError, json.JSONDecodeError:
        return "planning-graph-telemetry-unreadable"
    if isinstance(payload, dict):
        tokens_saved = payload.get("tokens_saved")
        if isinstance(tokens_saved, int):
            return tokens_saved
        if payload.get("grounded") is True:
            return 0
    return "planning-graph-tokens-not-recorded"


def read_dispatch_idle_timing(repo_root: Path, *, project_slug: str = "pyforge-marshal") -> dict[str, object]:
    """Q-14: one wave of per-session timing from dispatch journals."""
    runs_dir = repo_root / "_bmad-output/projects" / project_slug / "implementation-artifacts/dispatch-runs"
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


# Story 46.5 (CAP-193): the journal taxonomy split -- which `LayerSavings`
# fields (`ports/harness.py`, read-only reference) are the repo-default
# layers Story 46.4 makes harness-agnostic ("silent": no configuration, no
# opt-in, every harness gets them) vs. the one capability/config-resolved
# layer ("configured": `wire_compression_saved`, gated on whether a given
# harness's wire-wrap layer is enabled at all).
SILENT_LAYER_KEYS = (
    "output_compression_saved",
    "graph_hits_vs_file_reads",
    "derived_context_cache_hits",
    "planning_graph_tokens_saved",
)
CONFIGURED_LAYER_KEYS = ("wire_compression_saved",)


def classify_layer_kind(layer_key: str) -> str:
    """The single source of truth for the silent/configured taxonomy.
    Returns ``"silent"`` or ``"configured"``. Raises ``ValueError`` on an
    unrecognized key -- a new `LayerSavings` field added without updating
    this taxonomy is a programmer error and must fail loud, not silently
    mis-bucket (see this story's Design Notes)."""
    if layer_key in SILENT_LAYER_KEYS:
        return "silent"
    if layer_key in CONFIGURED_LAYER_KEYS:
        return "configured"
    raise ValueError(f"unrecognized layer_savings key: {layer_key!r}")


# Story 46.5 (CAP-193): the per-harness binding-currency table -- USD for
# Claude, quota-burn for Cursor/Copilot, request-count for Gemini, ACUs for
# Devin, never one blended token number (this epic's own "a repo default can
# never claim a wrap a harness can't perform" ethos, epic-46-context.md).
HARNESS_CURRENCY: dict[str, str] = {
    "claude": "usd",
    "cursor": "quota-burn",
    "copilot": "quota-burn",
    "gemini": "request-count",
    "devin": "acus",
}
UNKNOWN_HARNESS_CURRENCY = "unknown"


def currency_for_harness(profile_name: str | None) -> str:
    """Never raises: an absent/unrecognized harness name degrades to the
    honest ``"unknown"`` currency label rather than a crash or a silent USD
    default that would misrepresent a non-Claude station's savings."""
    if profile_name is None:
        return UNKNOWN_HARNESS_CURRENCY
    return HARNESS_CURRENCY.get(profile_name, UNKNOWN_HARNESS_CURRENCY)


def read_rollup_by_harness(repo_root: Path, *, project_slug: str = "pyforge-marshal") -> dict[str, object]:
    """Per-harness savings rollup (Story 46.5, CAP-193). Mirrors
    ``read_dispatch_idle_timing``'s manual-JSONL-scan idiom: no
    ``core/journal.py`` domain-model import, plain ``json.loads`` per line.

    The join is READ-ONLY and single-pass per file: both signals it reads --
    the ``dispatch-launch`` kind's own ``outcome``-phase ``harness_profile``,
    and the run's LAST *non-empty* ``budget-usage``-kind ``layer_savings``
    payload -- already land in the SAME per-run ``journal.jsonl``
    (``cli/dispatch.py`` / ``supervisor/__main__.py``'s existing write
    paths, unchanged here), so the per-harness split is purely a read-time
    correlation keyed by ``run_id`` (the journal's parent directory name).

    Per-key merge across every non-empty ``budget-usage`` entry in the run,
    NOT whole-payload replacement: a terminal ``budget-usage`` flush can
    legitimately omit ``layer_savings`` (e.g. a final cost-only snapshot),
    and two non-empty entries in the same run can carry different,
    non-overlapping key subsets (``supervisor/__main__.py::
    _layer_savings_payload`` only includes a key when its ``LayerSavings``
    field ``is not None``) -- replacing the whole dict on each non-empty
    sighting would silently drop keys present only in an earlier entry, so
    this accumulates via ``dict.update`` instead (last non-null VALUE per
    key wins, not last entry wins). This remains an intentional, named
    divergence from ``cli/status.py::_gather_run_journal_facts``'s literal
    ``usage_entries[-1]`` convention (that function reports a single run's
    point-in-time cost readout, not a savings rollup) -- do not "fix" this
    to match it exactly.

    A run missing either signal entirely -- no ``dispatch-launch`` outcome
    naming a harness, or no ``budget-usage`` entry that ever carried a
    ``layer_savings`` dict -- is SKIPPED, never counted under an
    ``"unknown"`` bucket: an incomplete run contributes no partial data.

    Bucketing is driven off the payload's OWN ``layer_savings`` keys, not a
    hardcoded field-name tuple, so an unrecognized key actually reaches
    ``classify_layer_kind`` and can raise (see that function's docstring).

    Returns ``{"status": "ok"|"no-dispatch-journals"|"no-savings-samples",
    "harnesses": {<profile_name>: {"currency": ..., "silent": {...},
    "configured": {...}, "runs": N}}}`` -- never a cross-harness summed
    total.
    """
    runs_dir = repo_root / "_bmad-output/projects" / project_slug / "implementation-artifacts/dispatch-runs"
    if not runs_dir.is_dir():
        return {"status": "no-dispatch-journals", "harnesses": {}}

    harnesses: dict[str, dict[str, object]] = {}
    try:
        journal_paths = sorted(runs_dir.glob("*/journal.jsonl"))
    except OSError:
        # A permission-denied (or otherwise unreadable) subdirectory hit
        # during iteration skips the whole rollup rather than crashing
        # `marshal status --project <slug>` -- same degraded shape as the
        # directory-missing branch above.
        return {"status": "no-dispatch-journals", "harnesses": {}}

    for journal_path in journal_paths:
        try:
            text = journal_path.read_text(encoding="utf-8")
        except OSError, UnicodeDecodeError:
            # A filesystem race (removed/permission-changed between glob and
            # read), or a non-UTF-8 journal file, skips this one run,
            # matching this module's own per-line JSONDecodeError tolerance
            # -- never crashes the whole rollup.
            continue

        harness_profile: str | None = None
        accumulated_layer_savings: dict[str, object] = {}
        for line in text.splitlines():
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
                if isinstance(layer_savings, dict) and layer_savings:
                    accumulated_layer_savings.update(layer_savings)

        if harness_profile is None or not accumulated_layer_savings:
            # An incomplete run (missing either signal) contributes no
            # partial data -- never bucketed under "unknown".
            continue

        harness_bucket = harnesses.setdefault(
            harness_profile,
            {
                "currency": currency_for_harness(harness_profile),
                "silent": {},
                "configured": {},
                "runs": 0,
            },
        )
        harness_bucket["runs"] = harness_bucket["runs"] + 1  # type: ignore[operator]

        # `supervisor/__main__.py::_layer_savings_payload` writes
        # `graph_hits_vs_file_reads` two different ways on the wire: as a
        # single `graph_hits_vs_file_reads` string key, or -- when the
        # source value is the (hits, reads) tuple, the normal case -- split
        # into separate `graph_hits`/`file_reads` keys. Neither
        # `SILENT_LAYER_KEYS` nor `CONFIGURED_LAYER_KEYS` recognizes the
        # split names, so they must be recombined under the canonical key
        # before classification, or a real run's tuple-shaped payload makes
        # `classify_layer_kind` raise on live data instead of a genuine
        # schema-drift key.
        normalized_layer_savings = dict(accumulated_layer_savings)
        graph_hits = normalized_layer_savings.pop("graph_hits", None)
        file_reads = normalized_layer_savings.pop("file_reads", None)
        if graph_hits is not None or file_reads is not None:
            normalized_layer_savings["graph_hits_vs_file_reads"] = (graph_hits, file_reads)

        for layer_key, value in normalized_layer_savings.items():
            try:
                layer_kind = classify_layer_kind(layer_key)
            except ValueError:
                # An unrecognized key (schema drift not yet in the
                # taxonomy) skips just that key -- the rest of this run's
                # recognized keys still bucket normally, matching this
                # function's existing per-run/per-line tolerance idiom
                # rather than crashing `marshal status --project <slug>`.
                continue
            layer_kind_bucket = harness_bucket[layer_kind]
            layer_kind_bucket.setdefault(layer_key, []).append(value)  # type: ignore[union-attr]

    status = "ok" if harnesses else "no-savings-samples"
    return {"status": status, "harnesses": harnesses}
