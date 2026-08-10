"""``upstream_discovery`` pipeline nodes — GitHub-trending discovery trigger (Story 13.1,
FR-64 / CAP-1).

PURE ``params -> RefreshRequest`` trigger — mirrors
``pipelines/vulnerability/nodes.py::refresh_vdb_store`` exactly. ALL fetch + HTML/JSON
parsing IO lives in ``datasets/upstream_discovery.py`` (dataset-owned IO, AD-2); no
HTTP/parse imports here.
"""

from __future__ import annotations

from ...datasets.refresh import DAILY_SECONDS, RefreshRequest


def _coerce_cadence(ttls: dict, key: str) -> int:
    """Read a cadence (seconds) from ``params:ttls``; a missing / null / non-numeric
    value, OR a non-dict ``ttls`` (review finding, Story 13.1 — the precedent
    ``vulnerability/nodes.py::_coerce_cadence`` this mirrors only guards a falsy value,
    not a truthy non-dict), falls back to the daily default rather than crashing."""
    raw = ttls.get(key) if isinstance(ttls, dict) else None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return DAILY_SECONDS


def refresh_trending_candidates(ttls: dict) -> RefreshRequest:
    # CAP-1 — GitHub-trending discovery ingest (Story 13.1, FR-64; spec-upstream-discovery)
    """External-refresh asset for the GitHub-trending candidate snapshot. PURE: emits the
    ``RefreshRequest`` trigger ``TrendingSnapshotDataset`` consumes (which HONORS its
    cadence/force and invokes the dataset-owned injected fetch of the 3
    daily/weekly/monthly HTML pages + the Search API fallback — NO HTTP/parse import
    here). Cadence daily (``ttls.trending_candidates``; no legacy equivalent). Single
    writer of ``trending_candidates``."""
    return RefreshRequest(
        store="trending_candidates",
        cadence_seconds=_coerce_cadence(ttls, "trending_candidates"),
    )
