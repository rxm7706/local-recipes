"""Core pipeline node unit tests (Story B1, Task 4 / AC-1, AC-2, AC-3, AC-4).

Every node is tested independently on ``pandas.DataFrame`` in/out, NO live network.
Includes the carried-over Phase B.5 ``_pick_feedstock`` unit tests (AC-2) and the
Phase F provenance-discipline fixture tests (AC-4).
"""

from __future__ import annotations

import pandas as pd

from pyforge.atlas.pipelines.core.nodes import (
    _pick_feedstock,
    attribute_feedstocks,
    build_dependency_graph,
    compute_downloads,
    compute_feedstock_health,
    compute_version_download_history,
    detect_latest_status,
    enumerate_conda_packages,
)


# -- Phase B ---------------------------------------------------------------

def test_enumerate_conda_packages_dedups_to_latest_build_and_seconds():
    repo = pd.DataFrame(
        {
            "conda_name": ["numpy", "numpy", "pandas"],
            "version": ["1.0", "2.0", "3.0"],
            # ms timestamps (repodata per-build) — must normalize to seconds
            "timestamp": [1_600_000_000_000, 1_700_000_000_000, 1_650_000_000_000],
        }
    )
    channel = pd.DataFrame({"conda_name": ["numpy", "pandas"], "subdirs": [["noarch"], ["linux-64"]]})
    out = enumerate_conda_packages(repo, channel)
    row = out.set_index("conda_name")
    assert row.loc["numpy", "latest_version"] == "2.0"  # newest build wins
    assert set(out["conda_name"]) == {"numpy", "pandas"}


def test_enumerate_empty_repodata_is_empty_frame():
    out = enumerate_conda_packages(pd.DataFrame(), pd.DataFrame())
    assert list(out.columns) == ["conda_name", "latest_version", "subdirs"]
    assert out.empty


# -- Phase B.5 (_pick_feedstock carried-over unit tests, AC-2) --------------

def test_pick_feedstock_empty_returns_none():
    assert _pick_feedstock("dbt", []) is None
    assert _pick_feedstock("dbt", None) is None


def test_pick_feedstock_dedicated_wins_over_umbrella():
    # len>1 and pkg_name in feedstocks -> the dedicated feedstock (CFA:1586-1590)
    assert _pick_feedstock("dbt-bigquery", ["dbt", "dbt-bigquery"]) == "dbt-bigquery"


def test_pick_feedstock_else_first():
    assert _pick_feedstock("dbt", ["dbt"]) == "dbt"
    # pkg not among a multi list -> first
    assert _pick_feedstock("x", ["a", "b"]) == "a"


def test_pick_feedstock_survives_nan_and_string_cells():
    import numpy as np
    # a missing cell arrives as NaN (truthy) — must NOT crash len(nan)
    assert _pick_feedstock("x", np.nan) is None
    # a bare string is treated as a single-element list
    assert _pick_feedstock("dbt", "dbt") == "dbt"


def test_attribute_feedstocks_handles_nan_feedstocks_cell():
    import numpy as np
    src = pd.DataFrame({"conda_name": ["a", "b"], "feedstocks": [["a"], np.nan]})
    out = attribute_feedstocks(src)
    m = dict(zip(out["conda_name"], out["feedstock_name"]))
    assert m["a"] == "a"
    assert m["b"] is None  # NaN cell -> None, no crash


def test_attribute_feedstocks_node():
    src = pd.DataFrame(
        {
            "conda_name": ["dbt-bigquery", "numpy", "orphan"],
            "feedstocks": [["dbt", "dbt-bigquery"], ["numpy"], []],
        }
    )
    out = attribute_feedstocks(src)
    m = dict(zip(out["conda_name"], out["feedstock_name"]))
    assert m["dbt-bigquery"] == "dbt-bigquery"
    assert m["numpy"] == "numpy"
    assert m["orphan"] is None


# -- Phase B.6 (LITE: presence -> active; no yanked scan, AC-6) -------------

def test_detect_latest_status_is_lite_presence_active():
    repo = pd.DataFrame({"conda_name": ["a", "a", "b"], "version": ["1", "2", "1"]})
    out = detect_latest_status(repo, pd.DataFrame())
    assert set(out["conda_name"]) == {"a", "b"}
    assert set(out["latest_status"].unique()) == {"active"}


# -- Phase F provenance discipline (AC-4) ----------------------------------

def _s3():
    return pd.DataFrame(
        {
            "conda_name": ["numpy", "numpy", "numpy", "pandas"],
            "month": ["2026-05", "2026-06", "2026-06", "2026-06"],
            "platform": ["linux-64", "linux-64", "osx-64", "linux-64"],
            "pyver": ["3.11", "3.12", "bad", "3.11"],  # 'bad' is dirty -> filtered
            "channel": ["main", "main", "main", "main"],
            "downloads": [10, 20, 5, 7],
        }
    )


def _ana():
    return pd.DataFrame(
        {
            "conda_name": ["numpy", "numpy", "scipy"],
            "version": ["1.0", "2.0", "1.0"],
            "downloads": [100, 200, 50],
        }
    )


def test_f_source_merged_when_both_present():
    downloads, plat, pyv, chan = compute_downloads(_ana(), _s3())
    src = dict(zip(downloads["conda_name"], downloads["downloads_source"]))
    assert src["numpy"] == "merged"    # in both s3 + anaconda
    assert src["pandas"] == "s3-parquet"  # s3 only
    assert src["scipy"] == "anaconda-api"  # anaconda only


def test_f_breakdowns_only_on_s3_path():
    # anaconda-only path: breakdowns MUST be empty (s3-only tables, CFA:538/549/572)
    downloads, plat, pyv, chan = compute_downloads(_ana(), pd.DataFrame())
    assert (downloads["downloads_source"] == "anaconda-api").all()
    assert plat.empty and pyv.empty and chan.empty
    assert downloads["downloads_30d"].isna().all()  # no monthly on anaconda path


def test_f_downloads_30d_is_latest_calendar_month_not_rolling():
    downloads, *_ = compute_downloads(pd.DataFrame(), _s3())
    d30 = dict(zip(downloads["conda_name"], downloads["downloads_30d"]))
    # latest month is 2026-06: numpy = 20 + 5 = 25 (NOT the 10 from 2026-05)
    assert d30["numpy"] == 25
    assert d30["pandas"] == 7


def test_f_pkg_python_regex_filter_drops_dirty_rows():
    _, _, pyv, _ = compute_downloads(pd.DataFrame(), _s3())
    # 'bad' pyver row is dropped before aggregation -> only clean 3.11 / 3.12
    assert set(pyv["pyver"].unique()) <= {"3.11", "3.12"}
    assert "bad" not in set(pyv["pyver"].unique())


# -- Phase I (explicit declared output, AC-3) ------------------------------

def test_compute_version_download_history_is_explicit_per_version():
    hist = compute_version_download_history(_ana())
    m = dict(zip(zip(hist["conda_name"], hist["version"]), hist["downloads"]))
    assert m[("numpy", "1.0")] == 100
    assert m[("numpy", "2.0")] == 200
    assert list(hist.columns) == ["conda_name", "version", "downloads"]


# -- Phase J (archived-feedstock skip-set filter at write site) -------------

def _cf_graph():
    return pd.DataFrame(
        {
            "feedstock_name": ["numpy", "numpy", "deadpkg"],
            "conda_name": ["numpy", "numpy", "deadpkg"],
            "depends_on": ["python", "libblas", "python"],
            "dep_type": ["run", "host", "run"],
            "feedstock_archived": [False, False, True],
            "maintainers": [["alice"], ["alice"], ["bob"]],
            "ci_status": ["green", "green", "red"],
            "open_prs": [0, 0, 3],
            "open_issues": [1, 1, 9],
        }
    )


def test_build_dependency_graph_skips_archived_feedstocks():
    edges = build_dependency_graph(_cf_graph())
    assert "deadpkg" not in set(edges["conda_name"])  # archived filtered at write site
    assert set(edges["depends_on"]) == {"python", "libblas"}


# -- Phase M (same archived scope filter at write SELECT) -------------------

def test_compute_feedstock_health_skips_archived():
    health = compute_feedstock_health(_cf_graph())
    assert set(health["feedstock_name"]) == {"numpy"}
    assert "deadpkg" not in set(health["feedstock_name"])


def test_archived_filter_handles_string_booleans_no_silent_inversion():
    # feedstock_archived as strings 'true'/'false' must NOT be inverted by astype(bool)
    g = pd.DataFrame(
        {
            "feedstock_name": ["live", "dead"],
            "conda_name": ["live", "dead"],
            "depends_on": ["python", "python"],
            "dep_type": ["run", "run"],
            "feedstock_archived": ["false", "true"],
        }
    )
    edges = build_dependency_graph(g)
    assert set(edges["conda_name"]) == {"live"}  # 'false' NOT treated as archived


def test_nodes_tolerate_missing_required_columns():
    # a mis-shaped (non-empty) frame lacking required columns returns a columned empty,
    # not a KeyError
    assert build_dependency_graph(pd.DataFrame({"x": [1]})).empty
    assert compute_feedstock_health(pd.DataFrame({"x": [1]})).empty
    assert enumerate_conda_packages(pd.DataFrame({"x": [1]}), pd.DataFrame()).empty
