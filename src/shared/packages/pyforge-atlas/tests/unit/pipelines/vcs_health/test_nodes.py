"""vcs_health pipeline node unit tests (Story B1, Task 4 / AC-1, AC-5)."""

from __future__ import annotations

import pandas as pd

from pyforge.atlas.datasets.refresh import WEEKLY_SECONDS, RefreshRequest
from pyforge.atlas.pipelines.vcs_health.nodes import (
    _REGISTRY_INPUTS,
    _ttl_cadence,
    detect_archived_feedstocks,
    enrich_maintainers,
    fetch_live_health,
    refresh_vcs_github_store,
    refresh_vcs_host_stores,
    refresh_vcs_registry_stores,
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
    assert set(maint["maintainer"]) == {"alice", "bob"}  # unique universe
    pairs = set(zip(pkg_maint["conda_name"], pkg_maint["maintainer"]))
    assert pairs == {("numpy", "alice"), ("numpy", "bob"), ("pandas", "bob")}


def test_enrich_maintainers_empty_is_columned_empty():
    maint, pkg_maint = enrich_maintainers(pd.DataFrame())
    assert list(maint.columns) == ["maintainer"]
    assert list(pkg_maint.columns) == ["conda_name", "maintainer"]


# -- Phase E.5 (archived-feedstock detection) -------------------------------


def test_detect_archived_feedstocks():
    api = pd.DataFrame({"feedstock_name": ["a", "b", "c"], "archived": [True, False, True]})
    out = detect_archived_feedstocks(api)
    assert set(out["feedstock_name"]) == {"a", "c"}


def test_detect_archived_handles_string_booleans():
    api = pd.DataFrame({"feedstock_name": ["a", "b"], "archived": ["true", "false"]})
    out = detect_archived_feedstocks(api)
    assert set(out["feedstock_name"]) == {"a"}  # 'false' NOT inverted to archived


def test_enrich_maintainers_handles_nan_maintainers_cell():
    import numpy as np

    g = pd.DataFrame({"feedstock_name": ["a", "b"], "conda_name": ["a", "b"], "maintainers": [["x"], np.nan]})
    maint, pkg = enrich_maintainers(g)  # NaN cell must not crash `for m in nan`
    assert set(maint["maintainer"]) == {"x"}
    assert set(pkg["conda_name"]) == {"a"}


# -- Phase K (pure merge; last_error convention preserved) -------------------


def test_track_upstream_versions_merges_hosts_and_preserves_last_error():
    gh = pd.DataFrame({"conda_name": ["numpy"], "upstream_version": ["2.0"], "last_error": [pd.NA]})
    gl = pd.DataFrame({"conda_name": ["rustpkg"], "upstream_version": ["9.9"]})
    cb = pd.DataFrame(
        # a 403 landed in last_error at the fetcher; the node preserves it
        {"conda_name": ["gitea-pkg"], "upstream_version": [pd.NA], "last_error": ["HTTP 403"]}
    )
    out = track_upstream_versions(gh, gl, cb)
    assert set(out["host"]) == {"github", "gitlab", "codeberg"}
    err = dict(zip(out["conda_name"], out["last_error"]))
    assert err["gitea-pkg"] == "HTTP 403"  # last_error convention preserved
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


# -- External-refresh trigger nodes (Story 21.2, review fix #10) ------------


def test_ttl_cadence_reads_the_key():
    assert _ttl_cadence({"vcs_upstream_versions": 12345}, "vcs_upstream_versions") == 12345


def test_ttl_cadence_falls_back_to_weekly_on_missing_key():
    assert _ttl_cadence({}, "vcs_upstream_versions") == WEEKLY_SECONDS
    assert _ttl_cadence(None, "vcs_upstream_versions") == WEEKLY_SECONDS


def test_ttl_cadence_falls_back_to_weekly_on_non_numeric_value():
    assert _ttl_cadence({"vcs_upstream_versions": "not-a-number"}, "vcs_upstream_versions") == WEEKLY_SECONDS
    assert _ttl_cadence({"vcs_upstream_versions": None}, "vcs_upstream_versions") == WEEKLY_SECONDS


def test_ttl_cadence_passes_through_zero_and_negative():
    # _ttl_cadence itself does not clamp -- it only guards against non-numeric /
    # missing values; RefreshRequest.cadence_seconds=0 is a legitimate "always due"
    # trigger, consumed downstream by the dataset's own _refresh_due check.
    assert _ttl_cadence({"vcs_upstream_versions": 0}, "vcs_upstream_versions") == 0
    assert _ttl_cadence({"vcs_upstream_versions": -5}, "vcs_upstream_versions") == -5


def test_refresh_vcs_github_store_returns_a_refresh_request_for_its_own_store():
    req = refresh_vcs_github_store({"vcs_upstream_versions": 999})
    assert isinstance(req, RefreshRequest)
    assert req.store == "vcs_github_api_raw"
    assert req.cadence_seconds == 999


def test_refresh_vcs_github_store_defaults_cadence_to_weekly():
    req = refresh_vcs_github_store({})
    assert req.cadence_seconds == WEEKLY_SECONDS


def test_refresh_vcs_host_stores_returns_one_request_per_host():
    gitlab_req, codeberg_req = refresh_vcs_host_stores({"vcs_upstream_versions": 555})
    assert (gitlab_req.store, gitlab_req.cadence_seconds) == ("vcs_gitlab_api_raw", 555)
    assert (codeberg_req.store, codeberg_req.cadence_seconds) == ("vcs_codeberg_api_raw", 555)


def test_refresh_vcs_registry_stores_returns_one_request_per_registry():
    reqs = refresh_vcs_registry_stores({"vcs_registry_versions": 777})
    assert len(reqs) == len(_REGISTRY_INPUTS) == 8
    stores = {r.store for r in reqs}
    assert stores == {f"vcs_registry_{r}_raw" for r in _REGISTRY_INPUTS}
    assert all(r.cadence_seconds == 777 for r in reqs)
