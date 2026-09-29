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
    # Stripped for the same reason `_validate_tier` strips (review finding, Story
    # 13.3): a whitespace-padded value reaching either flag through shell quoting or
    # an MCP client should behave the same way in both, and the tier sentinel already
    # accepts `" all "`. Without this, `--period " weekly "` raised while
    # `--tier " all "` succeeded — the same padding, two different outcomes.
    period = str(period).strip()
    if period not in _VALID_PERIODS:
        raise ValueError(f"invalid --period {period!r}: must be one of {sorted(_VALID_PERIODS)}")
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
    # The NORMALIZED tokens, not the outer-stripped input (second follow-up review
    # finding, Story 13.3): `_validate_period` returns its fully-stripped value and its
    # test pins "normalized, not echoed padded", but this returned `" 1 , 2 "` as
    # `"1 , 2"` — so two callers passing the same tier set got byte-different `filters`
    # blocks in the envelope for an identical candidate list.
    return ",".join(tokens)


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


_INF = float("inf")


def _narrow_integral_floats(frame: pd.DataFrame) -> pd.DataFrame:
    """Cast every float column holding only whole numbers to the nullable ``Int64``.

    The generalization of the ``stars_total`` fix (follow-up review finding, Story
    13.3): that fix was applied to ONE column, but pandas widens ANY count column to
    ``float64`` the moment one row is null, and `stars_today` is null for 2 of the 3
    fetched periods by construction (``datasets/upstream_discovery.py`` — the trending
    page carries a "today" delta only on the daily window) while ``forks_total`` is
    null whenever the scrape lacks the tag. So a two-row daily frame emitted
    ``"stars_today": 7.0`` for the row that HAS a delta — the identical "a count's
    emitted JSON type depends on unrelated rows" defect, one column over, in the
    operator's table and the machine-readable envelope alike (verified live).

    Skips any column carrying a non-finite or out-of-int64-range value, which cannot be
    represented as an ``Int64`` at all (``OverflowError``/``TypeError``).
    """
    narrowed = {}
    for column in frame.columns:
        series = frame[column]
        if not pd.api.types.is_float_dtype(series):
            continue
        non_null = series.dropna()
        if non_null.empty:
            continue
        if not (non_null.abs() != _INF).all() or not non_null.abs().lt(2**63).all():
            continue
        if non_null.eq(non_null.round()).all():
            narrowed[column] = series.astype("Int64")
    return frame.assign(**narrowed) if narrowed else frame


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

    then sorts ``stars_total`` descending / ``repo_full_name`` ascending / ``period``
    ascending (a TOTAL order, so ``--top``'s cap is deterministic — the third key was
    added because under ``period="all"`` one repo contributes up to 3 rows tied on both
    of the others) and caps to ``top``.

    The envelope reports three counts, not one (second follow-up review finding, Story
    13.3): ``rows`` (what the dataset held), ``matched`` (what the filters kept, BEFORE
    the cap) and ``count`` (what is actually returned). With ``count`` alone, a table
    whose rows are ALL tagged ``period="all"`` — the shape CAP-1 writes whenever the
    HTML scrape breaks across all 3 windows and it falls back to the Search API —
    answers the default ``period="weekly"`` query with a byte-identical "nothing here"
    to a healthy table nothing matched in, and a capped result is indistinguishable
    from an exhaustive one.

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
    rows_loaded = len(df)

    # Each filter applies only when its backing column exists — but when the column is
    # ABSENT and the filter was actually REQUESTED, the result is EMPTIED rather than
    # silently returned unfiltered (review finding, Story 13.3: verified live — a frame
    # with no `period` column returned every period's rows while `filters.period` still
    # reported "weekly", and one with no `reason` column returned an
    # already-on-conda-forge row under the default `--not-on-cf`, which is exactly the
    # row CAP-5's Mason handoff must never be given). Mirrors the `stars_total` branch
    # below and the Boundaries & Constraints rule it already states: never silently
    # pass a filter it cannot actually satisfy. A filter that was NOT requested
    # (`period="all"`, `tier="all"`, `not_on_cf=False`) needs no column and is skipped.
    if not df.empty and period != "all":
        df = df[df["period"] == period] if "period" in df.columns else df.iloc[0:0]

    if not df.empty and tier != "all":
        df = df[df["tier"].isin(_tier_tokens(tier))] if "tier" in df.columns else df.iloc[0:0]

    if not df.empty and not_on_cf:
        df = df[df["reason"] != REASON_ALREADY_ON_CF] if "reason" in df.columns else df.iloc[0:0]

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
            numeric = pd.to_numeric(df["stars_total"], errors="coerce")
            # A non-finite value is not a star count (follow-up review finding, Story
            # 13.3). A corrupt cell coercing to ±inf — the literal `"inf"`, or an
            # overflowing `"1e400"`, the same dirty-STRING class the coercion above
            # exists for — used to survive as a value that passes the floor and then
            # aborted the ENTIRE query in the integral narrowing
            # (`OverflowError: cannot convert float infinity to integer`, verified
            # live): a whole-query crash where the contract promises one excluded row.
            # Folded into NA so it takes the identical never-satisfies-the-floor path
            # a null/unparseable value already takes.
            numeric = numeric.where(numeric.abs() != _INF)
            df = df.assign(stars_total=numeric)
            df = df[df["stars_total"] >= min_stars]
        else:
            # No stars_total column at all: no row can actually satisfy the floor —
            # never silently pass a filter it cannot satisfy (Boundaries & Constraints).
            df = df.iloc[0:0]

    matched = len(df)

    if not df.empty:
        # `period` is the THIRD tie-break (follow-up review finding, Story 13.3).
        # Under `--period all` the same repo contributes up to 3 rows tied on BOTH
        # documented sort keys, so which of them survived `head(top)` was decided by
        # the physical row order of the parquet file: the identical data
        # re-materialized in a different order returned different rows for
        # `--period all --top 3` (verified live), contradicting this function's own
        # "a deterministic tie-break for --top's cap". A repo has at most one row per
        # period, so this makes the ordering total.
        sort_cols = [c for c in ("stars_total", "repo_full_name", "period") if c in df.columns]
        if sort_cols:
            df = df.sort_values(
                by=sort_cols,
                ascending=[c != "stars_total" for c in sort_cols],
            )

    capped = _narrow_integral_floats(df.head(top))
    # NaN survives to_dict() as the Python float `nan`, which `json.dumps` renders as
    # the bare, non-RFC-8259-conformant token `NaN` — breaking CAP-3's own literal
    # success signal ("JSON output validates against a documented schema", SPEC.md).
    #
    # `.astype(object)` FIRST is what makes the replacement actually take effect
    # (review finding, Story 13.3: verified live). On a float64 column,
    # `where(cond, None)` does NOT upcast — pandas casts the `None` straight back to
    # NaN and the cell survives unchanged, so the previous `capped.where(...)` alone
    # was a silent no-op for every float column. It only ever worked for an
    # all-null OBJECT column, which is precisely the single-row shape the test meant
    # to guard it used — a false green. Any real frame carrying BOTH a null and a
    # value in one optional column (e.g. `stars_today`, null whenever a row lacks a
    # daily delta) is float64, and leaked `NaN` into the emitted JSON.
    #
    # ±inf is masked for the SAME reason (follow-up review finding, Story 13.3):
    # `json.dumps` renders it as the bare `Infinity`/`-Infinity` token, equally
    # non-RFC-8259 and equally rejected by a strict parser (verified live). `pd.notna`
    # says True for inf, so it needs its own clause.
    json_safe = pd.notna(capped) & ~capped.isin([_INF, -_INF])
    candidates = capped.astype(object).where(json_safe, None).to_dict(orient="records")

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
        # rows -> matched -> count: what was there, what the filters kept, what the cap
        # returned (second follow-up review finding, Story 13.3 — see the docstring).
        # `rows`/`matched` are the ONLY signal separating "this table is fallback-shaped
        # (every row period='all') so your default weekly query cannot match" from
        # "nothing trending qualified", and the only one that makes truncation visible.
        "rows": rows_loaded,
        "matched": matched,
        "count": len(candidates),
        "candidates": candidates,
    }
