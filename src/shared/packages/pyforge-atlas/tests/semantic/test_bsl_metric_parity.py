"""BSL metric-parity fixtures (Story D1, AC-4 — the AD-7 metric-semantics anchor).

Each core metric is proven to MATCH the legacy CLI formula. The DW-B1-1 discipline is
enforced structurally: the expected value on every assertion is computed by an
INDEPENDENT re-implementation of the legacy formula (a verbatim copy of the legacy
Python function, or the legacy SQL predicate translated to pandas) — NEVER by calling
the BSL expression under test. So a divergence between the Ibis port and the legacy
formula fails the gate; both sides never "compute the same thing".

Legacy sources (cited at each anchor):
- adoption stage: ``.claude/skills/conda-forge-expert/scripts/adoption_stage.py::_classify``
- staleness:      ``.../staleness_report.py`` (query-loop ``age_days``)
- actionable:     ``.../conda_forge_atlas.py`` (``v_actionable_packages`` view DDL)
- downloads:      ``core/nodes.py::compute_downloads``
- feedstock health: ``.../feedstock_health.py`` ``--filter`` predicates
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from pyforge.atlas.semantic import models


# ===========================================================================
# LEGACY ANCHORS — independent re-implementations of the legacy formulas.
# These are COPIED from the legacy source; they must not import the BSL layer.
# ===========================================================================


def _legacy_classify(latest_upload_age_days, releases_30d, total_versions):
    """VERBATIM copy of adoption_stage.py::_classify (do not refactor)."""
    if latest_upload_age_days is None and total_versions == 0:
        return "unknown"
    age = latest_upload_age_days or 99999
    if age > 730:
        return "silent"
    if age > 365:
        return "declining"
    if releases_30d >= 3:
        return "bleeding-edge"
    if releases_30d >= 1:
        return "stable"
    if age <= 365:
        return "mature"
    return "unknown"


def _legacy_staleness_age_days(now, ts):
    """Re-implements staleness_report.py: ``(now - ts) // 86400 if ts else None``."""
    return (now - ts) // 86400 if ts else None


def _legacy_is_actionable(conda_name, latest_status, feedstock_archived):
    """Re-implements the v_actionable_packages view WHERE clause."""
    return (
        conda_name is not None
        and (latest_status if latest_status is not None else "active") == "active"
        and (feedstock_archived if feedstock_archived is not None else 0) == 0
    )


def _legacy_ci_red(ci_status):
    """Re-implements feedstock_health.py --filter ci-red (mapped column)."""
    return ci_status in ("failure", "error")


# ===========================================================================
# helpers
# ===========================================================================

NOW = 1_700_000_000  # pinned wall clock for deterministic staleness


def _nullable_str(values):
    """A nullable string column whose SQL NULLs stay ``None``.

    pandas >=3 infers a bare list of strings as the ``str`` dtype, whose missing
    sentinel is NaN — so a fixture's ``None`` would reach the legacy anchors below as a
    TRUTHY NaN and the anchor would compute the WRONG expectation (its ``is not None``
    guard passes, then ``nan == 'active'`` is False). The nullable integer columns here
    are already explicit via ``pd.array(..., dtype='Int64')``; this is the string
    equivalent.
    """
    return pd.Series(values, dtype=object)


def _by_key(df, key, val):
    return {r[key]: r[val] for _, r in df.iterrows()}


# ===========================================================================
# adoption stage
# ===========================================================================


def test_adoption_stage_matches_legacy_classify(parquet_table):
    # Rows exercise every branch + the boundaries (730, 365, releases 0/1/2/3, the
    # null-age+0-versions unknown branch, and the `age or 99999` falsy-zero quirk).
    df = pd.DataFrame(
        {
            "conda_name": ["silent", "declin", "bleed", "stable", "mature", "unknown",
                           "b730", "b365", "zeroage", "twoRel", "newpkg", "nulltv_old"],
            "latest_upload_age_days": pd.array(
                [800, 400, 10, 100, 200, None, 730, 365, 0, 50, None, None],
                dtype="Int64",
            ),
            # NULL releases/versions exercise the legacy call-site `... or 0` coalescing:
            #   newpkg     — NULL age + NULL total_versions → "unknown" (new/no-history)
            #   nulltv_old — NULL age + NON-NULL total_versions → age→99999 → "silent"
            "releases_30d": pd.array([0, 0, 3, 1, 0, 0, 0, 0, 5, 2, None, 0], dtype="Int64"),
            "total_versions": pd.array([1, 1, 5, 3, 4, 0, 2, 2, 1, 3, None, 5], dtype="Int64"),
        }
    )
    t = parquet_table(df, "adoption")
    model = models.build_packages_model(t, now_unix=NOW)
    got = _by_key(
        model.query(dimensions=["conda_name", "adoption_stage"]).execute(),
        "conda_name",
        "adoption_stage",
    )
    for _, r in df.iterrows():
        age = r["latest_upload_age_days"]
        age = None if pd.isna(age) else int(age)
        # mirror the legacy CALL SITE exactly (adoption_stage.py:106): the count args
        # are coalesced `... or 0` BEFORE _classify — so the anchor is faithful, not a
        # copy of the port's own coalescing.
        rel = 0 if pd.isna(r["releases_30d"]) else int(r["releases_30d"])
        tv = 0 if pd.isna(r["total_versions"]) else int(r["total_versions"])
        expected = _legacy_classify(age, rel, tv)
        assert got[r["conda_name"]] == expected, r["conda_name"]

    # Independent spot-anchors on the exact legacy boundaries (>730 / >365 are STRICT):
    #   b730 age==730 → not >730, but >365 → "declining"
    #   b365 age==365 → not >365, releases 0, age<=365 → "mature"
    #   zeroage age==0 → `0 or 99999`==99999 → >730 → "silent" (the falsy-zero quirk)
    #   newpkg NULL age + NULL total_versions → "unknown" (NOT "silent" — the call-site
    #     `total_versions or 0` fidelity; guards against the port dropping it)
    #   nulltv_old NULL age + total_versions=5 → age→99999 → "silent"
    assert got["b730"] == "declining"
    assert got["b365"] == "mature"
    assert got["zeroage"] == "silent"
    assert got["newpkg"] == "unknown"
    assert got["nulltv_old"] == "silent"


# ===========================================================================
# staleness
# ===========================================================================


def test_staleness_age_days_matches_legacy(parquet_table):
    # includes a NULL upload and a 0 upload → both legacy-None; a nullable-int column
    # round-trips through Parquet to float64, so this also guards the int64 re-cast.
    df = pd.DataFrame(
        {
            "conda_name": ["fresh", "old", "nullts", "zerots"],
            "latest_conda_upload": pd.array(
                [NOW - 5 * 86400, NOW - 900 * 86400, None, 0], dtype="Int64"
            ),
            # unused-by-staleness columns present so the model builds:
            "latest_status": ["active"] * 4,
            "feedstock_archived": pd.array([0, 0, 0, 0], dtype="Int64"),
            "downloads_total": pd.array([1, 1, 1, 1], dtype="Int64"),
            "downloads_30d": pd.array([1, 1, 1, 1], dtype="Int64"),
            "latest_upload_age_days": pd.array([5, 900, None, None], dtype="Int64"),
            "releases_30d": pd.array([0, 0, 0, 0], dtype="Int64"),
            "total_versions": pd.array([1, 1, 1, 1], dtype="Int64"),
        }
    )
    t = parquet_table(df, "stale")
    model = models.build_packages_model(t, now_unix=NOW)
    got = _by_key(
        model.query(dimensions=["conda_name", "staleness_age_days"]).execute(),
        "conda_name",
        "staleness_age_days",
    )
    for _, r in df.iterrows():
        ts = r["latest_conda_upload"]
        ts = None if pd.isna(ts) else int(ts)
        expected = _legacy_staleness_age_days(NOW, ts)
        actual = got[r["conda_name"]]
        if expected is None:
            assert actual is None or (isinstance(actual, float) and math.isnan(actual))
        else:
            assert int(actual) == expected, r["conda_name"]

    assert int(got["fresh"]) == 5
    assert int(got["old"]) == 900


# ===========================================================================
# actionable scope
# ===========================================================================


def test_is_actionable_matches_legacy_view(parquet_table):
    df = pd.DataFrame(
        {
                "conda_name": ["a", "b", "c", "d", "e"],
                "latest_status": _nullable_str(["active", "archived", None, "active", "active"]),
            "feedstock_archived": pd.array([0, 0, 0, 1, None], dtype="Int64"),
            "downloads_total": pd.array([1, 1, 1, 1, 1], dtype="Int64"),
            "downloads_30d": pd.array([1, 1, 1, 1, 1], dtype="Int64"),
            "latest_conda_upload": pd.array([NOW] * 5, dtype="Int64"),
            "latest_upload_age_days": pd.array([1, 1, 1, 1, 1], dtype="Int64"),
            "releases_30d": pd.array([0, 0, 0, 0, 0], dtype="Int64"),
            "total_versions": pd.array([1, 1, 1, 1, 1], dtype="Int64"),
        }
    )
    t = parquet_table(df, "actionable")
    model = models.build_packages_model(t, now_unix=NOW)
    got = _by_key(
        model.query(dimensions=["conda_name", "is_actionable"]).execute(),
        "conda_name",
        "is_actionable",
    )
    for _, r in df.iterrows():
        fa = r["feedstock_archived"]
        fa = None if pd.isna(fa) else int(fa)
        expected = _legacy_is_actionable(r["conda_name"], r["latest_status"], fa)
        assert bool(got[r["conda_name"]]) == expected, r["conda_name"]
    # a=active/0 → True ; b=archived-status → False ; c=NULL-status(→active) → True ;
    # d=feedstock_archived=1 → False ; e=NULL-archived(→0) → True.
    assert [bool(got[k]) for k in ["a", "b", "c", "d", "e"]] == [True, False, True, False, True]

    # actionable_count measure agrees with the row-level dimension (3 actionable).
    n = model.query(measures=["actionable_count"]).execute()["actionable_count"].iloc[0]
    assert int(n) == 3


# ===========================================================================
# downloads
# ===========================================================================


def test_downloads_measures_match_legacy_sum(parquet_table):
    df = pd.DataFrame(
        {
            "conda_name": ["a", "b", "c"],
            "latest_status": ["active", "active", "active"],
            "feedstock_archived": pd.array([0, 0, 0], dtype="Int64"),
            "downloads_total": pd.array([100, 200, None], dtype="Int64"),
            "downloads_30d": pd.array([10, 20, 5], dtype="Int64"),
            "latest_conda_upload": pd.array([NOW] * 3, dtype="Int64"),
            "latest_upload_age_days": pd.array([1, 1, 1], dtype="Int64"),
            "releases_30d": pd.array([0, 0, 0], dtype="Int64"),
            "total_versions": pd.array([1, 1, 1], dtype="Int64"),
        }
    )
    t = parquet_table(df, "downloads")
    model = models.build_packages_model(t, now_unix=NOW)
    res = model.query(measures=["downloads_total", "downloads_30d"]).execute()
    # legacy: a plain sum over the migrated core_downloads column (NULL skipped).
    assert int(res["downloads_total"].iloc[0]) == 100 + 200
    assert int(res["downloads_30d"].iloc[0]) == 10 + 20 + 5


# ===========================================================================
# feedstock health
# ===========================================================================


def test_feedstock_health_filters_match_legacy(parquet_table):
    df = pd.DataFrame(
        {
            "feedstock_name": ["red", "err", "green", "prs", "issues", "clean"],
            "ci_status": _nullable_str(
                ["failure", "error", "success", "success", "success", None]
            ),
            "open_prs": pd.array([0, 0, 0, 3, 0, None], dtype="Int64"),
            "open_issues": pd.array([0, 0, 0, 0, 2, None], dtype="Int64"),
        }
    )
    t = parquet_table(df, "fhealth")
    model = models.build_feedstock_health_model(t)

    ci = _by_key(
        model.query(dimensions=["feedstock_name", "ci_red"]).execute(),
        "feedstock_name",
        "ci_red",
    )
    for _, r in df.iterrows():
        assert bool(ci[r["feedstock_name"]]) == _legacy_ci_red(r["ci_status"]), r["feedstock_name"]

    prs = _by_key(
        model.query(dimensions=["feedstock_name", "has_open_prs"]).execute(),
        "feedstock_name",
        "has_open_prs",
    )
    for _, r in df.iterrows():
        exp = (0 if pd.isna(r["open_prs"]) else int(r["open_prs"])) > 0  # COALESCE(...,0)>0
        assert bool(prs[r["feedstock_name"]]) == exp, r["feedstock_name"]

    issues = _by_key(
        model.query(dimensions=["feedstock_name", "has_open_issues"]).execute(),
        "feedstock_name",
        "has_open_issues",
    )
    for _, r in df.iterrows():
        exp = (0 if pd.isna(r["open_issues"]) else int(r["open_issues"])) > 0
        assert bool(issues[r["feedstock_name"]]) == exp, r["feedstock_name"]

    # counts agree with the row-level dimensions.
    counts = model.query(
        measures=["ci_red_count", "open_prs_count", "open_issues_count", "feedstock_count"]
    ).execute()
    assert int(counts["ci_red_count"].iloc[0]) == 2  # failure + error
    assert int(counts["open_prs_count"].iloc[0]) == 1
    assert int(counts["open_issues_count"].iloc[0]) == 1
    assert int(counts["feedstock_count"].iloc[0]) == 6


# ===========================================================================
# empty-input robustness (Reviewer B — empty/missing datasets)
# ===========================================================================


# explicit per-column dtypes so the EMPTY frame round-trips to a proper typed Parquet
# schema (an all-empty object column would round-trip to a null type and break string
# comparisons — a fixture artifact, not a model bug; real catalog Parquet is typed).
_PACKAGES_EMPTY_DTYPES = {
    "conda_name": "string", "latest_status": "string", "feedstock_archived": "Int64",
    "latest_conda_upload": "Int64", "downloads_total": "Int64", "downloads_30d": "Int64",
    "latest_upload_age_days": "Int64", "releases_30d": "Int64", "total_versions": "Int64",
}
_FHEALTH_EMPTY_DTYPES = {
    "feedstock_name": "string", "ci_status": "string", "open_prs": "Int64", "open_issues": "Int64",
}


@pytest.mark.parametrize(
    "builder,dtypes",
    [
        (models.build_packages_model, _PACKAGES_EMPTY_DTYPES),
        (models.build_feedstock_health_model, _FHEALTH_EMPTY_DTYPES),
    ],
)
def test_models_build_and_query_on_empty_input(parquet_table, builder, dtypes):
    df = pd.DataFrame({c: pd.array([], dtype=d) for c, d in dtypes.items()})
    t = parquet_table(df, "empty")
    model = builder(t)
    # every count measure over an empty table returns 0 (a real integer, NOT NULL) and
    # never raises — a filter-count of matches must be 0 on no data, not NaN.
    if builder is models.build_packages_model:
        measures = ["package_count", "actionable_count"]
    else:
        measures = ["feedstock_count", "ci_red_count", "open_prs_count", "open_issues_count"]
    res = model.query(measures=measures).execute()
    for m in measures:
        val = res[m].iloc[0]
        assert not pd.isna(val), f"{m} is NULL on empty input (should be 0)"
        assert int(val) == 0, m

    # Reviewer-B NIT: a raw SUM measure (downloads_total/_30d) INTENTIONALLY returns NULL
    # (not 0) on an empty set — this is the deliberate "absent → NULL, never a fabricated
    # 0" design also relied on by the maintainer ⋈ (an absent package sums to NULL). Pin it
    # so a downstream page/consumer treats an empty whole-catalog SUM as NULL, not 0.
    if builder is models.build_packages_model:
        sums = model.query(measures=["downloads_total", "downloads_30d"]).execute()
        assert pd.isna(sums["downloads_total"].iloc[0])
        assert pd.isna(sums["downloads_30d"].iloc[0])
