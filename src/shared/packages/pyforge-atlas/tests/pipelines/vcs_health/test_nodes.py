"""vcs_health pipeline node unit tests (Story B1, Task 4 / AC-1, AC-5)."""

from __future__ import annotations

import pandas as pd

from pyforge.atlas.pipelines.vcs_health.nodes import (
    detect_archived_feedstocks,
    enrich_maintainers,
    fetch_live_health,
    track_registry_versions,
    track_upstream_versions,
)


# -- Phase E (maintainer enrichment; cross-pipeline core_cf_graph_raw) -------

def test_enrich_maintainers_emits_universe_and_long_form():
    g = pd.DataFrame(
        {
            "feedstock_name": ["numpy", "pandas"],
            "conda_name": ["numpy", "pandas"],
            "maintainers": [["alice", "bob"], ["bob"]],
        }
    )
    maint, pkg_maint = enrich_maintainers(g)
    assert set(maint["maintainer"]) == {"alice", "bob"}       # unique universe
    pairs = set(zip(pkg_maint["conda_name"], pkg_maint["maintainer"]))
    assert pairs == {("numpy", "alice"), ("numpy", "bob"), ("pandas", "bob")}


def test_enrich_maintainers_empty_is_columned_empty():
    maint, pkg_maint = enrich_maintainers(pd.DataFrame())
    assert list(maint.columns) == ["maintainer"]
    assert list(pkg_maint.columns) == ["conda_name", "maintainer"]


# -- Phase E.5 (archived-feedstock detection) -------------------------------

def test_detect_archived_feedstocks():
    api = pd.DataFrame(
        {"feedstock_name": ["a", "b", "c"], "archived": [True, False, True]}
    )
    out = detect_archived_feedstocks(api)
    assert set(out["feedstock_name"]) == {"a", "c"}


def test_detect_archived_handles_string_booleans():
    api = pd.DataFrame({"feedstock_name": ["a", "b"], "archived": ["true", "false"]})
    out = detect_archived_feedstocks(api)
    assert set(out["feedstock_name"]) == {"a"}  # 'false' NOT inverted to archived


def test_enrich_maintainers_handles_nan_maintainers_cell():
    import numpy as np
    g = pd.DataFrame(
        {"feedstock_name": ["a", "b"], "conda_name": ["a", "b"], "maintainers": [["x"], np.nan]}
    )
    maint, pkg = enrich_maintainers(g)  # NaN cell must not crash `for m in nan`
    assert set(maint["maintainer"]) == {"x"}
    assert set(pkg["conda_name"]) == {"a"}


# -- Phase K (pure merge; last_error convention preserved) -------------------

def test_track_upstream_versions_merges_hosts_and_preserves_last_error():
    gh = pd.DataFrame(
        {"conda_name": ["numpy"], "upstream_version": ["2.0"], "last_error": [pd.NA]}
    )
    gl = pd.DataFrame({"conda_name": ["rustpkg"], "upstream_version": ["9.9"]})
    cb = pd.DataFrame(
        # a 403 landed in last_error at the fetcher; the node preserves it
        {"conda_name": ["gitea-pkg"], "upstream_version": [pd.NA], "last_error": ["HTTP 403"]}
    )
    out = track_upstream_versions(gh, gl, cb)
    assert set(out["host"]) == {"github", "gitlab", "codeberg"}
    err = dict(zip(out["conda_name"], out["last_error"]))
    assert err["gitea-pkg"] == "HTTP 403"       # last_error convention preserved
    assert list(out.columns) == ["conda_name", "host", "upstream_version", "last_error"]


def test_track_upstream_versions_all_empty():
    out = track_upstream_versions(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    assert out.empty and list(out.columns) == ["conda_name", "host", "upstream_version", "last_error"]


# -- Phase L (8-registry merge) ---------------------------------------------

def test_track_registry_versions_tags_each_registry():
    npm = pd.DataFrame({"conda_name": ["left-pad"], "upstream_version": ["1.3.0"]})
    crates = pd.DataFrame({"conda_name": ["serde"], "upstream_version": ["1.0"]})
    empty = pd.DataFrame()
    out = track_registry_versions(npm, empty, empty, empty, crates, empty, empty, empty)
    m = dict(zip(out["conda_name"], out["registry"]))
    assert m["left-pad"] == "npm"
    assert m["serde"] == "crates"
    assert set(out.columns) == {"conda_name", "registry", "upstream_version"}


# -- Phase N (live health projection) ---------------------------------------

def test_fetch_live_health_projects_signals():
    api = pd.DataFrame(
        {
            "feedstock_name": ["numpy", "numpy"],
            "stars": [100, 100],
            "last_commit": ["2026-07-01", "2026-07-01"],
            "open_issues": [3, 3],
        }
    )
    out = fetch_live_health(api)
    assert len(out) == 1  # dedup on feedstock_name
    assert out.iloc[0]["stars"] == 100
