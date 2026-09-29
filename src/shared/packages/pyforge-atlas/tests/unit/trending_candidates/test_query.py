"""``query_trending_candidates`` — CAP-3's whole query contract (Story 13.3, FR-66).

One test per I/O & Edge-Case Matrix row in the story spec (the parity row — "CLI --json
vs MCP tool, same filters" — is covered separately, in
``tests/mcp/test_read_surface.py``'s delegate-parity test).
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from pyforge.atlas.trending_candidates import query


def _row(*, repo_full_name, period, tier, reason, stars_total, **extra) -> dict:
    """A trending_candidates_classified-shaped row: the raw dataset's own columns
    (datasets/upstream_discovery.py) + the classifier's pypi_name/tier/reason
    (pipelines/upstream_discovery/nodes.py::_CLASSIFIER_NEW_COLS)."""
    row = {
        "repo_full_name": repo_full_name,
        "repo_url": f"https://github.com/{repo_full_name}",
        "description": None,
        "language": "Python",
        "stars_total": stars_total,
        "stars_today": None,
        "forks_total": None,
        "period": period,
        "source": "html_scrape",
        "fetched_at": 1_700_000_000,
        "pypi_name": repo_full_name.split("/")[-1],
        "tier": tier,
        "reason": reason,
    }
    row.update(extra)
    return row


_TIER1_REASON = "pure-python packaging shape, OSI-approved license MIT"
_TIER2_REASON = "rust-pyo3 packaging shape, OSI-approved license MIT"


def test_happy_path_default_filters(seed_catalog):
    """Matrix row 1: default filters keep only period=="weekly", tier 1/2, not
    already-on-cf, stars_total>=500 — sorted stars_total desc, ties by
    repo_full_name asc."""
    df = pd.DataFrame(
        [
            _row(repo_full_name="alice/libfoo", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=1200),
            # tie with alice/libfoo at 1200 stars -- tie-break proves repo_full_name asc
            _row(repo_full_name="zed/ziplib", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=1200),
            _row(repo_full_name="bob/rustcli", period="weekly", tier="2", reason=_TIER2_REASON, stars_total=900),
            _row(
                repo_full_name="carol/onconda",
                period="weekly",
                tier="skip",
                reason="already-on-conda-forge",
                stars_total=5000,
            ),
            _row(
                repo_full_name="dave/tiny", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=100
            ),  # below the 500 floor
            _row(
                repo_full_name="gina/dailyonly", period="daily", tier="1", reason=_TIER1_REASON, stars_total=2000
            ),  # wrong period
        ]
    )
    seed_catalog(df)

    result = query.query_trending_candidates()

    assert result["dataset"] == "trending_candidates_classified"
    assert result["filters"] == {
        "period": "weekly",
        "tier": "1,2",
        "top": 25,
        "not_on_cf": True,
        "min_stars": 500,
    }
    assert result["count"] == 3
    assert [c["repo_full_name"] for c in result["candidates"]] == [
        "alice/libfoo",
        "zed/ziplib",
        "bob/rustcli",
    ]


def test_tier_all_is_a_no_op(seed_catalog):
    """Matrix row 2: `--tier all` drops the tier filter entirely (a skip row survives
    alongside tier-1/2, still subject to the other default filters)."""
    df = pd.DataFrame(
        [
            _row(repo_full_name="alice/libfoo", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=1200),
            _row(
                repo_full_name="frank/skiplib", period="weekly", tier="skip", reason="no-pypi-artifact", stars_total=700
            ),
        ]
    )
    seed_catalog(df)

    result = query.query_trending_candidates(tier="all")

    assert result["count"] == 2
    assert {c["repo_full_name"] for c in result["candidates"]} == {
        "alice/libfoo",
        "frank/skiplib",
    }


def test_period_all_includes_every_period_duplicates_included(seed_catalog):
    """Matrix row 3: `--period all` surfaces every period's row (including the
    search-api-fallback period="all" tag), duplicates across periods included."""
    df = pd.DataFrame(
        [
            _row(repo_full_name="alice/libfoo", period="daily", tier="1", reason=_TIER1_REASON, stars_total=1200),
            _row(repo_full_name="alice/libfoo", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=1200),
            _row(repo_full_name="alice/libfoo", period="monthly", tier="1", reason=_TIER1_REASON, stars_total=1200),
            _row(
                repo_full_name="hank/fallback",
                period="all",
                tier="1",
                reason=_TIER1_REASON,
                stars_total=1600,
                source="search_api_fallback",
            ),
        ]
    )
    seed_catalog(df)

    result = query.query_trending_candidates(period="all")

    assert result["count"] == 4  # every period's row, duplicates included


def test_all_flag_includes_already_on_cf_rows(seed_catalog):
    """Matrix row 4: `--all` (not_on_cf=False) stops filtering out
    reason=="already-on-conda-forge" rows -- isolated from the tier filter by pinning
    `tier="skip"` on both sides (the reason this classifier assigns an on-cf skip is
    always tier "skip")."""
    df = pd.DataFrame(
        [
            _row(
                repo_full_name="carol/onconda",
                period="weekly",
                tier="skip",
                reason="already-on-conda-forge",
                stars_total=5000,
            ),
        ]
    )
    seed_catalog(df)

    default_result = query.query_trending_candidates(tier="skip")
    assert default_result["count"] == 0  # not_on_cf=True (default) excludes it

    all_result = query.query_trending_candidates(tier="skip", not_on_cf=False)
    assert all_result["count"] == 1
    assert all_result["candidates"][0]["repo_full_name"] == "carol/onconda"


def test_null_or_unparseable_stars_total_excluded_not_errored(seed_catalog):
    """Matrix row 5: a null OR unparseable stars_total fails the --min-stars floor --
    excluded, never an error."""
    df = pd.DataFrame(
        [
            _row(repo_full_name="erin/nostar", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=None),
            _row(
                repo_full_name="frank/badstar",
                period="weekly",
                tier="1",
                reason=_TIER1_REASON,
                stars_total="not-a-number",
            ),
            _row(repo_full_name="gail/goodstar", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=1000),
        ]
    )
    seed_catalog(df)

    result = query.query_trending_candidates()

    assert result["count"] == 1
    assert result["candidates"][0]["repo_full_name"] == "gail/goodstar"


def test_missing_dataset_degrades_to_empty_no_exception(seed_catalog):
    """Matrix row 6a: the dataset KEY entirely absent from the catalog (e.g. a name
    mismatch between `query.py::DATASET_NAME` and catalog.yml) degrades to count: 0 --
    never a crash. See `test_missing_parquet_file_degrades_to_empty_no_exception` below
    for the REALISTIC production "never ingested" shape (a declared entry whose backing
    file is simply missing), which this undeclared-key shortcut does not reproduce
    (review finding, Story 13.3)."""
    seed_catalog(None)

    result = query.query_trending_candidates()

    assert result["count"] == 0
    assert result["candidates"] == []


def test_missing_parquet_file_degrades_to_empty_no_exception(seed_parquet_catalog):
    """The realistic production "never ingested" shape: `trending_candidates_classified`
    IS declared in the catalog (as the real catalog.yml does), but its backing
    `.parquet` file doesn't exist yet -- the same `DatasetError` path, proven against
    the real dataset type this time (review finding, Story 13.3)."""
    seed_parquet_catalog(None)

    result = query.query_trending_candidates()

    assert result["count"] == 0
    assert result["candidates"] == []
    assert result["provenance_kind"] == "unavailable"


def test_build_stamp_propagates_through_a_real_parquet_dataset(seed_parquet_catalog, tmp_path):
    """The catalog.yml comment claims CAP-3 surfaces `build_stamp`/`build_stamp_newest`
    so staleness is always visible -- proven end-to-end here against a REAL
    `ParquetDataset` (a `MemoryDataset` always resolves to `provenance_kind:
    "unavailable"` and can't exercise this path at all; review finding, Story 13.3).
    Mirrors `test_read_dataset_pandas_parquet_reports_file_mtime_not_read_time`'s
    deliberately-old `os.utime` proof (equality, not merely "a stamp is present").
    ``tmp_path`` is the SAME directory `seed_parquet_catalog` wrote into (pytest caches
    a fixture per test), so recomputing the path here needs no catalog introspection."""
    import datetime
    import os

    df = pd.DataFrame(
        [
            _row(repo_full_name="alice/libfoo", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=1200),
        ]
    )
    seed_parquet_catalog(df)
    path = tmp_path / "trending_candidates_classified" / "trending_candidates_classified.parquet"
    old_ts = 1_600_000_000  # 2020-09-13, deliberately far from "now"
    os.utime(path, (old_ts, old_ts))

    result = query.query_trending_candidates()

    assert result["count"] == 1
    assert result["provenance_kind"] == "file-mtime"
    assert result["build_stamp"] == datetime.datetime.fromtimestamp(old_ts, tz=datetime.UTC).isoformat()


def test_empty_dataset_degrades_to_empty_no_exception(seed_catalog):
    """Matrix row 6b: a present-but-zero-row dataset also degrades to count: 0."""
    empty_df = pd.DataFrame(columns=["repo_full_name", "period", "tier", "reason", "stars_total"])
    seed_catalog(empty_df)

    result = query.query_trending_candidates()

    assert result["count"] == 0
    assert result["candidates"] == []


def test_top_actually_truncates(seed_catalog):
    """`--top` is a display cap over the already-qualifying set (review finding, Story
    13.3: no prior test ever seeded more matches than `top`'s default of 25). Seeds 30
    qualifying rows with distinct `stars_total` and asserts exactly `top` survive, and
    that they're the `top`-highest by the documented sort order."""
    rows = [
        _row(repo_full_name=f"user{i}/repo{i}", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=1000 + i)
        for i in range(30)
    ]
    seed_catalog(pd.DataFrame(rows))

    result = query.query_trending_candidates(top=5)

    assert result["count"] == 5
    assert result["filters"]["top"] == 5
    # Truncation is VISIBLE (second follow-up review finding, Story 13.3): with `count`
    # alone, "5 of 30" and an exhaustive 5 were the same response.
    assert result["rows"] == 30
    assert result["matched"] == 30
    # highest stars_total first: repo29 (1029) down to repo25 (1025)
    assert [c["repo_full_name"] for c in result["candidates"]] == [
        "user29/repo29",
        "user28/repo28",
        "user27/repo27",
        "user26/repo26",
        "user25/repo25",
    ]


def test_mixed_numeric_string_and_int_stars_total_does_not_crash_the_sort(seed_catalog):
    """Regression (review finding, Story 13.3, verified live): a numeric-LOOKING string
    stars_total (e.g. "1500") genuinely satisfies `>= min_stars` once coerced, so it
    SURVIVES the filter alongside a real int -- if the column isn't coerced in place,
    the surviving column is mixed str/int object dtype and `sort_values` raises
    `TypeError: '<' not supported between instances of 'str' and 'int'`."""
    df = pd.DataFrame(
        [
            _row(
                repo_full_name="a/numeric-string", period="weekly", tier="1", reason=_TIER1_REASON, stars_total="1500"
            ),
            _row(repo_full_name="b/real-int", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=2000),
        ]
    )
    seed_catalog(df)

    result = query.query_trending_candidates()  # must not raise

    assert result["count"] == 2
    assert [c["repo_full_name"] for c in result["candidates"]] == [
        "b/real-int",
        "a/numeric-string",
    ]
    # Integral star counts stay ints (follow-up review finding, Story 13.3): the
    # numeric coercion must not render a whole-number count as `1500.0`.
    assert [c["stars_total"] for c in result["candidates"]] == [2000, 1500]


def test_null_optional_column_serializes_to_json_safe_none(seed_catalog):
    """Regression (review finding, Story 13.3, verified live): a null `stars_today`
    (plausible whenever a row lacks a daily-delta signal) forces that column to
    float64 with NaN cells; `to_dict(orient="records")` carries the raw NaN through,
    which `json.dumps` renders as the invalid, non-RFC-8259 `NaN` token instead of
    `null`.

    TWO rows, deliberately (follow-up review finding, Story 13.3): the earlier
    single-all-None-row version of this test was a FALSE GREEN. One all-None row makes
    `stars_today` an **object** column — the one dtype where the original
    `capped.where(pd.notna(capped), None)` actually replaced anything. A column
    carrying BOTH a value and a null is **float64**, where `where(..., None)` casts
    the None straight back to NaN and is a silent no-op. This shape is what any real
    multi-row frame produces, and it must serialize strictly.
    """
    import json

    df = pd.DataFrame(
        [
            _row(
                repo_full_name="alice/libfoo",
                period="weekly",
                tier="1",
                reason=_TIER1_REASON,
                stars_total=1200,
                stars_today=7,
            ),
            _row(
                repo_full_name="bob/libbar",
                period="weekly",
                tier="1",
                reason=_TIER1_REASON,
                stars_total=900,
                stars_today=None,
            ),
        ]
    )
    # The dtype this test exists to cover -- pin it, so a future fixture edit that
    # collapses it back to `object` fails here instead of silently re-greening.
    assert df["stars_today"].dtype == "float64"
    seed_catalog(df)

    result = query.query_trending_candidates()

    assert result["candidates"][0]["stars_today"] == 7
    assert result["candidates"][1]["stars_today"] is None

    # Strict: `json.dumps` happily EMITS the bare `NaN` token, so dumping alone proves
    # nothing. Re-parse rejecting the non-RFC-8259 constants is what actually pins
    # CAP-3's "JSON output validates" success signal.
    def _reject(token):
        raise AssertionError(f"non-RFC-8259 token in envelope: {token}")

    json.loads(json.dumps(result), parse_constant=_reject)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"tier": "5"},
        {"tier": "1,bogus"},
        {"tier": ""},
        {"period": "century"},
        {"top": 0},
        {"top": -1},
        {"min_stars": -1},
        {"not_on_cf": "false"},
    ],
)
def test_invalid_input_raises_value_error(kwargs):
    """Matrix row 7: an unrecognized --tier token, or an out-of-range
    --period/--top/--min-stars, or a non-bool not_on_cf, raises ValueError --
    validated BEFORE any dataset load (no `seed_catalog` fixture used here: the
    session/catalog seam is never touched on the fail-fast path)."""
    with pytest.raises(ValueError):
        query.query_trending_candidates(**kwargs)


def test_whitespace_padded_all_tier_is_accepted(seed_catalog):
    """Edge case (review finding, Story 13.3): individual comma-separated tier tokens
    are stripped, but the top-level `tier == "all"` sentinel check previously compared
    the RAW string -- a whitespace-padded `" all "` was rejected as an unrecognized
    token instead of being treated as the "no filter" sentinel."""
    df = pd.DataFrame(
        [
            _row(
                repo_full_name="alice/libfoo", period="weekly", tier="skip", reason="no-pypi-artifact", stars_total=700
            ),
        ]
    )
    seed_catalog(df)

    result = query.query_trending_candidates(tier=" all ")  # must not raise

    assert result["count"] == 1


def test_whitespace_padded_period_is_accepted(seed_catalog):
    """Follow-up review finding, Story 13.3: `_validate_tier` stripped but
    `_validate_period` did not, so the SAME padding was accepted on one flag and
    rejected on the other (`--tier " all "` worked, `--period " weekly "` raised)."""
    df = pd.DataFrame(
        [
            _row(repo_full_name="alice/libfoo", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=1200),
        ]
    )
    seed_catalog(df)

    result = query.query_trending_candidates(period=" weekly ")  # must not raise

    assert result["count"] == 1
    assert result["filters"]["period"] == "weekly"  # normalized, not echoed padded


def test_missing_period_column_empties_rather_than_ignoring_the_filter(seed_catalog):
    """Follow-up review finding, Story 13.3 (verified live): the period filter was
    guarded by `and "period" in df.columns`, so a frame WITHOUT that column silently
    skipped the filter entirely and returned every row — while `filters.period` still
    reported the value the caller asked for. A filter that cannot be evaluated must
    never be reported as satisfied (Boundaries & Constraints), which is exactly what
    the `stars_total` branch already did."""
    df = pd.DataFrame(
        [
            {"repo_full_name": "a/x", "tier": "1", "reason": _TIER1_REASON, "stars_total": 1000},
            {"repo_full_name": "b/y", "tier": "1", "reason": _TIER1_REASON, "stars_total": 900},
        ]
    )
    seed_catalog(df)

    result = query.query_trending_candidates()

    assert result["count"] == 0
    # ...but an explicit opt-out of the filter needs no column and still works.
    assert query.query_trending_candidates(period="all")["count"] == 2


def test_missing_reason_column_never_leaks_an_already_on_cf_row(seed_catalog):
    """Follow-up review finding, Story 13.3 (verified live): with no `reason` column
    the `--not-on-cf` filter was skipped silently, so an already-on-conda-forge repo
    could be returned under the DEFAULT filters — the one row CAP-5's Mason handoff
    must never be handed."""
    df = pd.DataFrame(
        [
            {"repo_full_name": "carol/onconda", "tier": "skip", "period": "weekly", "stars_total": 5000},
        ]
    )
    seed_catalog(df)

    result = query.query_trending_candidates(tier="skip")

    assert result["count"] == 0
    # `--all` asks for no on-cf filtering at all, so it needs no `reason` column.
    assert query.query_trending_candidates(tier="skip", not_on_cf=False)["count"] == 1


def test_missing_tier_column_empties_rather_than_ignoring_the_filter(seed_catalog):
    """Follow-up review finding, Story 13.3: same silent-skip shape as the period and
    reason filters."""
    df = pd.DataFrame(
        [
            {"repo_full_name": "a/x", "period": "weekly", "reason": _TIER1_REASON, "stars_total": 1000},
        ]
    )
    seed_catalog(df)

    assert query.query_trending_candidates()["count"] == 0
    assert query.query_trending_candidates(tier="all")["count"] == 1


def test_integral_stars_total_survives_an_unrelated_null_row(seed_catalog):
    """Follow-up review finding, Story 13.3 (verified live): `pd.to_numeric` widens the
    column to float64 as soon as ANY row is null, so one unrelated null flipped every
    OTHER row's emitted `stars_total` from `1200` to `1200.0` — a machine-readable
    type that depended on unrelated rows, and `1200.0` in the operator's table."""
    df = pd.DataFrame(
        [
            _row(repo_full_name="alice/libfoo", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=1200),
            _row(
                repo_full_name="erin/nostar", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=None
            ),  # excluded, but widens dtype
        ]
    )
    seed_catalog(df)

    result = query.query_trending_candidates()

    assert result["count"] == 1
    stars = result["candidates"][0]["stars_total"]
    assert stars == 1200
    assert isinstance(stars, int) and not isinstance(stars, bool)


def test_integral_optional_columns_also_survive_an_unrelated_null_row(seed_catalog):
    """Follow-up review finding, Story 13.3 (verified live): the integral-narrowing fix
    above was applied to `stars_total` ALONE, but `stars_today` is null for 2 of the 3
    fetched periods BY CONSTRUCTION and `forks_total` is null whenever the scrape lacks
    the tag — so pandas widened those to float64 too and emitted `7.0`/`3.0` for the
    rows that do carry a count, the identical defect one column over."""
    df = pd.DataFrame(
        [
            _row(
                repo_full_name="alice/libfoo",
                period="daily",
                tier="1",
                reason=_TIER1_REASON,
                stars_total=1200,
                stars_today=7,
                forks_total=3,
            ),
            _row(
                repo_full_name="bob/libbar",
                period="daily",
                tier="1",
                reason=_TIER1_REASON,
                stars_total=900,
                stars_today=None,
                forks_total=None,
            ),
        ]
    )
    seed_catalog(df)

    top_row = query.query_trending_candidates(period="daily")["candidates"][0]

    assert df["stars_today"].dtype == "float64"  # the dtype the bug needs; pin it
    for column, expected in (("stars_today", 7), ("forks_total", 3)):
        value = top_row[column]
        assert value == expected
        assert isinstance(value, int) and not isinstance(value, bool), (
            f"{column} emitted as {value!r} ({type(value).__name__})"
        )


def test_non_finite_stars_total_is_excluded_not_a_whole_query_crash(seed_catalog):
    """Follow-up review finding, Story 13.3 (verified live): a corrupt cell coercing to
    +/-inf — the literal `"inf"`, or an overflowing `"1e400"`, the same dirty-STRING
    class the numeric coercion exists for — reached the integral narrowing and raised
    `OverflowError: cannot convert float infinity to integer`, aborting the ENTIRE query
    where the contract promises one excluded row."""
    for bad in (float("inf"), float("-inf"), "inf", "1e400"):
        df = pd.DataFrame(
            [
                _row(repo_full_name="a/corrupt", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=bad),
                _row(repo_full_name="b/good", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=900),
            ]
        )
        seed_catalog(df)

        result = query.query_trending_candidates()

        assert [c["repo_full_name"] for c in result["candidates"]] == ["b/good"], bad


def test_non_finite_optional_value_serializes_to_json_safe_none(seed_catalog):
    """Follow-up review finding, Story 13.3 (verified live): the NaN->None guard used
    `pd.notna`, which says True for inf — so `json.dumps` emitted the bare `Infinity`
    token, as non-RFC-8259 as the `NaN` the previous pass fixed and rejected by any
    strict parser."""
    df = pd.DataFrame(
        [
            _row(
                repo_full_name="alice/libfoo",
                period="weekly",
                tier="1",
                reason=_TIER1_REASON,
                stars_total=1200,
                stars_today=float("inf"),
            ),
            _row(
                repo_full_name="bob/libbar",
                period="weekly",
                tier="1",
                reason=_TIER1_REASON,
                stars_total=900,
                stars_today=1.0,
            ),
        ]
    )
    seed_catalog(df)

    result = query.query_trending_candidates()

    assert result["candidates"][0]["stars_today"] is None

    def _reject(token):  # `json.dumps` happily EMITS Infinity; dumping proves nothing
        raise AssertionError(f"non-RFC-8259 token in the envelope: {token}")

    json.loads(json.dumps(result), parse_constant=_reject)


def test_period_all_truncation_does_not_depend_on_physical_row_order(seed_catalog):
    """Follow-up review finding, Story 13.3 (verified live): under `--period all` the
    same repo contributes up to 3 rows tied on BOTH documented sort keys, so which of
    them survived `head(top)` was decided by the parquet file's row order — the same
    data re-materialized in a different order returned different rows, contradicting
    this function's own documented "deterministic tie-break for --top's cap"."""
    rows = [
        _row(repo_full_name=name, period=period, tier="1", reason=_TIER1_REASON, stars_total=1000)
        for name in ("o/r0", "o/r1")
        for period in ("daily", "weekly", "monthly")
    ]

    seen = set()
    for order in ([0, 1, 2, 3, 4, 5], [2, 0, 1, 5, 3, 4], [5, 4, 3, 2, 1, 0]):
        seed_catalog(pd.DataFrame([rows[i] for i in order]))
        result = query.query_trending_candidates(period="all", top=3)
        seen.add(tuple((c["repo_full_name"], c["period"]) for c in result["candidates"]))

    assert len(seen) == 1, f"truncation varied with input order: {seen}"


def test_a_fallback_shaped_table_is_reported_present_not_silently_empty(seed_catalog):
    """Second follow-up review finding, Story 13.3.

    `datasets/upstream_discovery.py` falls back to the GitHub Search API when the HTML
    scrape yields zero rows across ALL THREE windows, and stamps every fallback row
    `period="all"` — so a fully-populated, freshly-refreshed table can consist entirely
    of rows the DEFAULT `--period weekly` cannot match. With `count` as the only count in
    the envelope, that degraded state was byte-identical to a healthy table nothing
    qualified in: `count: 0` under a fresh `build_stamp`. `rows` distinguishes them."""
    df = pd.DataFrame(
        [
            _row(
                repo_full_name="alice/libfoo",
                period="all",
                tier="1",
                reason=_TIER1_REASON,
                stars_total=1200,
                source="search_api_fallback",
            ),
            _row(
                repo_full_name="bob/rustcli",
                period="all",
                tier="2",
                reason=_TIER2_REASON,
                stars_total=900,
                source="search_api_fallback",
            ),
        ]
    )
    seed_catalog(df)

    default = query.query_trending_candidates()
    assert default["count"] == 0 and default["candidates"] == []
    assert default["rows"] == 2, "the data IS there — only the period filter excluded it"
    assert default["matched"] == 0

    # The same table, seen through the explicit opt-in the Design Notes document.
    opted_in = query.query_trending_candidates(period="all")
    assert opted_in["rows"] == 2 and opted_in["matched"] == 2 and opted_in["count"] == 2


def test_an_empty_dataset_reports_zero_rows_not_just_zero_count(seed_catalog):
    """The other side of the same signal: nothing ingested reports `rows: 0`, which is
    what makes a nonzero `rows` with `matched: 0` mean "your filters", not "no data"."""
    seed_catalog(pd.DataFrame())

    result = query.query_trending_candidates()

    assert result["rows"] == 0 and result["matched"] == 0 and result["count"] == 0


def test_a_whitespace_padded_tier_list_is_echoed_normalized(seed_catalog):
    """Second follow-up review finding, Story 13.3: `_validate_period` returns its
    fully-stripped value (pinned by `test_whitespace_padded_period_is_accepted`'s
    "normalized, not echoed padded"), but `_validate_tier` echoed `" 1 , 2 "` back as
    `"1 , 2"` — so two callers sending the same tier set got byte-different envelopes
    for an identical candidate list."""
    df = pd.DataFrame(
        [
            _row(repo_full_name="alice/libfoo", period="weekly", tier="1", reason=_TIER1_REASON, stars_total=1200),
        ]
    )
    seed_catalog(df)

    padded = query.query_trending_candidates(tier=" 1 , 2 ")
    plain = query.query_trending_candidates(tier="1,2")

    assert padded["filters"]["tier"] == "1,2"
    assert padded == plain
