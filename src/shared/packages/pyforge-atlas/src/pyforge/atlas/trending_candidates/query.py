"""``query_trending_candidates`` — CAP-3's whole query contract (Story 13.3, FR-66).

The ONE pure function both the CLI (``__main__.py``) and the MCP tool
(``mcp/tools.py::query_trending_candidates``) delegate to, so identical filters yield
identical output BY CONSTRUCTION — no parallel filter logic to drift (Design Notes).

Read-side only: loads the already-materialized ``trending_candidates_classified``
dataset (Story 13.2, CAP-2) via the exact seam ``mcp/tools.py::read_dataset`` already
uses — ``_session.bootstrapped_session``/``_session.loaded_catalog`` +
``_provenance.load_with_provenance`` — then filters/sorts/caps with pandas. Zero new
fetch; offline-safe and idempotent after ingest (SPEC CAP-3 intent). This module lives
OUTSIDE ``mcp/`` on purpose (Design Notes): only ``mcp/tools.py``'s tool BODIES are
AD-7 AST-gated, so the pandas-using filter/sort/cap logic belongs here, one seam call
away, exactly like ``provenance.py`` already is for ``read_dataset``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from kedro.io.core import DatasetError

from pyforge.atlas import provenance as _provenance
from pyforge.atlas.mcp import session as _session
from pyforge.atlas.pipelines.upstream_discovery.nodes import REASON_ALREADY_ON_CF

DATASET_NAME = "trending_candidates_classified"

# tier-taxonomy.md's 3 tiers, plus the literal "all" (a --tier value, not a tier itself).
_VALID_TIERS = frozenset({"1", "2", "skip"})

# tier-taxonomy.md's 3 ingestion windows, plus "all" — an engineering-default 4th value
# (Design Notes): the GitHub Search-API-fallback rows carry the literal period="all" tag
# (datasets/upstream_discovery.py::_SEARCH_API_FALLBACK_PERIOD), which the taxonomy's 3
# enumerated windows alone could never reach.
_VALID_PERIODS = frozenset({"daily", "weekly", "monthly", "all"})


def _validate_period(period: str) -> str:
    if period not in _VALID_PERIODS:
        raise ValueError(
            f"invalid --period {period!r}: must be one of {sorted(_VALID_PERIODS)}"
        )
    return period


def _validate_tier(tier: str) -> str:
    stripped = str(tier).strip()
    if stripped == "all":
        return stripped
    tokens = [t.strip() for t in stripped.split(",")]
    bad = [t for t in tokens if t not in _VALID_TIERS]
    if bad:
        raise ValueError(
            f"unrecognized --tier token(s) {bad!r} in {tier!r}: each token must be one "
            f"of {sorted(_VALID_TIERS)}, or the literal 'all'"
        )
    return stripped


def _validate_top(top: int) -> int:
    if isinstance(top, bool) or not isinstance(top, int) or top <= 0:
        raise ValueError(f"--top must be a positive integer, got {top!r}")
    return top


def _validate_min_stars(min_stars: int) -> int:
    if isinstance(min_stars, bool) or not isinstance(min_stars, int) or min_stars < 0:
        raise ValueError(f"--min-stars must be a non-negative integer, got {min_stars!r}")
    return min_stars


def _validate_not_on_cf(not_on_cf: bool) -> bool:
    if not isinstance(not_on_cf, bool):
        raise ValueError(f"not_on_cf must be a bool, got {not_on_cf!r}")
    return not_on_cf


def _tier_tokens(tier: str) -> set[str]:
    return {t.strip() for t in tier.split(",")}


def query_trending_candidates(
    *,
    period: str = "weekly",
    tier: str = "1,2",
    top: int = 25,
    not_on_cf: bool = True,
    min_stars: int = 500,
    project_path: Path | str | None = None,
    env: str | None = None,
) -> dict[str, Any]:
    """Filter/sort/cap the CAP-2 classified candidate set (tier-taxonomy.md's
    Operator-surface parameters table).

    Validates every filter FIRST — an unrecognized ``tier`` token, or a ``period``/
    ``top``/``min_stars`` outside its valid range, raises ``ValueError`` naming the bad
    value BEFORE any dataset load (fail fast, Boundaries & Constraints). Then loads
    ``trending_candidates_classified`` through the identical seam ``read_dataset`` uses
    (one catalog build per call), and applies, in order:

    - period (skipped when ``period == "all"``) — the raw dataset's own
      ``period="all"`` tag on GitHub Search-API-fallback rows makes those rows
      reachable only through this explicit opt-in (Design Notes).
    - tier (skipped when ``tier == "all"``) — a comma-set membership test.
    - not_on_cf — excludes rows whose ``reason`` is exactly
      ``"already-on-conda-forge"``; no boolean ``on_cf`` column exists.
    - min_stars — a numeric floor on ``stars_total``; a null/unparseable value
      coerces to NaN and NEVER satisfies a ``>=`` comparison, so it is excluded,
      not errored.

    then sorts ``stars_total`` descending / ``repo_full_name`` ascending (a
    deterministic tie-break for ``--top``'s cap) and caps to ``top``.

    A missing/absent ``trending_candidates_classified`` (no backing file yet — the
    realistic "never ingested" state) degrades to an empty candidate set via the same
    ``DatasetError`` kedro's dataset-load wrapper raises for it — never a crash
    (CAP-1/CAP-2's never-hard-fail posture). An empty-but-present dataset degrades the
    same way through the ordinary empty-DataFrame filter path.
    """
    period = _validate_period(period)
    tier = _validate_tier(tier)
    top = _validate_top(top)
    not_on_cf = _validate_not_on_cf(not_on_cf)
    min_stars = _validate_min_stars(min_stars)

    with _session.bootstrapped_session(project_path, env=env) as s:
        catalog = _session.loaded_catalog(s)
        try:
            value, info = _provenance.load_with_provenance(catalog, DATASET_NAME)
        except DatasetError as exc:
            value = pd.DataFrame()
            info = _provenance.ProvenanceInfo(
                kind="unavailable",
                build_stamp=None,
                reason=f"{DATASET_NAME} unavailable: {exc}",
            )

    df = value if isinstance(value, pd.DataFrame) else pd.DataFrame(value)

    if not df.empty and period != "all" and "period" in df.columns:
        df = df[df["period"] == period]

    if not df.empty and tier != "all" and "tier" in df.columns:
        df = df[df["tier"].isin(_tier_tokens(tier))]

    if not df.empty and not_on_cf and "reason" in df.columns:
        df = df[df["reason"] != REASON_ALREADY_ON_CF]

    if not df.empty:
        if "stars_total" in df.columns:
            # Coerce ONCE and overwrite the column (not just a throwaway comparison
            # series): a surviving row's stars_total that started as a numeric-looking
            # STRING (e.g. "1500", which `>= min_stars` genuinely satisfies once
            # coerced) would otherwise keep its original str value post-filter,
            # leaving `stars_total` a mixed str/int object column — `sort_values`
            # on that raises `TypeError: '<' not supported between instances of
            # 'str' and 'int'` (review finding, Story 13.3: verified live). Coercing
            # the column itself keeps the filter and the sort looking at the exact
            # same numeric values, and also fixes the NaN-vs-None JSON-safety
            # concern below for this specific column.
            df = df.assign(stars_total=pd.to_numeric(df["stars_total"], errors="coerce"))
            df = df[df["stars_total"] >= min_stars]
        else:
            # No stars_total column at all: no row can actually satisfy the floor —
            # never silently pass a filter it cannot satisfy (Boundaries & Constraints).
            df = df.iloc[0:0]

    if not df.empty:
        sort_cols = [c for c in ("stars_total", "repo_full_name") if c in df.columns]
        if sort_cols:
            df = df.sort_values(
                by=sort_cols,
                ascending=[c != "stars_total" for c in sort_cols],
            )

    capped = df.head(top)
    # NaN survives to_dict() as the Python float `nan`, which `json.dumps` renders as
    # the bare, non-RFC-8259-conformant token `NaN` (review finding, Story 13.3:
    # verified live) — breaking CAP-3's own literal success signal ("JSON output
    # validates against a documented schema", SPEC.md). `where(notna, None)` maps
    # every NaN/NaT cell to a JSON-safe `null` before the dict conversion.
    candidates = capped.where(pd.notna(capped), None).to_dict(orient="records")

    return {
        "schema_version": _provenance.SCHEMA_VERSION,
        "dataset": DATASET_NAME,
        "provenance_kind": info.kind,
        "build_stamp": info.build_stamp,
        "build_stamp_newest": info.build_stamp_newest,
        "reason": info.reason,
        "filters": {
            "period": period,
            "tier": tier,
            "top": top,
            "not_on_cf": not_on_cf,
            "min_stars": min_stars,
        },
        "count": len(candidates),
        "candidates": candidates,
    }
