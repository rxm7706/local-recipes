"""Unit coverage for `pyforge.atlas.dashboard.data` (Story 25.1).

The `dashboard-dryrun` integration gate exercises most loaders too, but only through
the "present store" success path and only in `tests/integration` -- which does not
count toward the diff-scoped `unit` coverage gate. These tests fill the gap the gate
never measured: the "missing Parquet" honest-empty branch for every loader (the
`_bsl_query_or_empty` early return), the degenerate-Parquet TypeError degrade, the
`default_data_root()` env-override branch, and `identity_workbook_gap_message` /
`load_identity_workbook`'s four gap-message branches plus its real join success path.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pyforge.atlas.dashboard import data

NOW = 1_700_000_000


# --------------------------------------------------------------------------- #
# default_data_root
# --------------------------------------------------------------------------- #


def test_default_data_root_honors_env_override(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PYFORGE_ATLAS_DATA_ROOT", str(tmp_path))
    assert data.default_data_root() == tmp_path


def test_default_data_root_walks_up_to_the_repo_root(monkeypatch):
    monkeypatch.delenv("PYFORGE_ATLAS_DATA_ROOT", raising=False)
    root = data.default_data_root()
    assert root.name == "data"
    assert (root.parent / ".git").exists() or (root.parent / "_bmad-output").is_dir()


# --------------------------------------------------------------------------- #
# _bsl_query_or_empty -- every thin loader's "backing Parquet absent" branch
# --------------------------------------------------------------------------- #

_NO_ARG_LOADERS = [
    data.load_feedstock_health,
    data.load_my_feedstocks,
    data.load_cve_watcher,
    data.load_version_downloads,
    data.load_release_cadence,
    data.load_find_alternative,
    data.load_scan_project,
    data.load_env_inspect,
    data.load_distribution_breakdown,
    data.load_export_purls,
    data.load_mapping_gap,
    data.load_universe_sbom,
    data.load_inventory_match,
    data.load_add_handoff,
    data.load_library_futures,
    data.load_recommend_2027,
    data.load_lts_registry_gap,
    data.load_cwe_seed_gap,
    data.load_spdx_schema_gap,
    data.load_license_map_gap,
    data.load_bootstrap_index_health,
    data.load_identity_export_snapshot,
    data.load_live_catalog_coverage,
    data.load_identity_catalog,
    data.load_identity_ops_priority,
    data.load_identity_ops_issues,
    data.load_identity_ops_builds,
    data.load_identity_ops_census,
]


@pytest.mark.parametrize("loader", _NO_ARG_LOADERS, ids=[fn.__name__ for fn in _NO_ARG_LOADERS])
def test_no_arg_loaders_degrade_to_empty_frame_when_parquet_absent(loader):
    got = loader("/definitely/not/a/real.parquet")
    assert isinstance(got, pd.DataFrame)
    assert got.empty


def test_no_arg_loaders_accept_none_too():
    assert data.load_feedstock_health(None).empty
    assert data.load_my_feedstocks(None).empty


@pytest.mark.parametrize(
    "loader",
    [data.load_staleness, data.load_query_atlas, data.load_detail, data.load_adoption_stage],
    ids=["staleness", "query_atlas", "detail", "adoption_stage"],
)
def test_now_arg_loaders_degrade_to_empty_frame_when_parquet_absent(loader):
    got = loader(None, now=NOW)
    assert isinstance(got, pd.DataFrame)
    assert got.empty


def test_load_estate_cache_defaults_to_data_root_when_no_parquet_given(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PYFORGE_ATLAS_DATA_ROOT", str(tmp_path))
    got = data.load_estate_cache()
    assert got.empty and list(got.columns) == ["sku", "units_total"]


# --------------------------------------------------------------------------- #
# _bsl_query_or_empty -- present-file success + degenerate-Parquet degrade
# --------------------------------------------------------------------------- #


def test_bsl_query_or_empty_success_path_with_real_parquet(tmp_path: Path):
    parquet = tmp_path / "core_feedstock_health.parquet"
    pd.DataFrame(
        {
            "feedstock_name": ["alpha", "beta"],
            "ci_status": ["failure", "success"],
            "open_prs": pd.array([1, 0], dtype="Int64"),
            "open_issues": pd.array([0, 2], dtype="Int64"),
        }
    ).to_parquet(parquet)
    got = data.load_feedstock_health(parquet)
    assert not got.empty
    assert set(got.columns) == {"feedstock_name", "ci_red", "has_open_prs", "has_open_issues"}
    red = dict(zip(got["feedstock_name"], got["ci_red"]))
    assert red == {"alpha": True, "beta": False}


def test_bsl_query_or_empty_degrades_on_degenerate_untyped_parquet(tmp_path: Path):
    """A PRESENT but 0-row, all-object-dtype Parquet round-trips untyped, so a metric
    predicate raises IbisTypeError (a TypeError subclass) -- the loader must degrade
    to the declared-column empty frame, never crash."""
    untyped = pd.DataFrame(
        {
            c: pd.Series([], dtype="object")
            for c in (
                "conda_name",
                "latest_status",
                "feedstock_archived",
                "latest_conda_upload",
                "downloads_total",
                "downloads_30d",
                "latest_upload_age_days",
                "releases_30d",
                "total_versions",
            )
        }
    )
    path = tmp_path / "untyped_packages.parquet"
    untyped.to_parquet(path)
    got = data.load_staleness(path, now=NOW)
    assert got.empty and list(got.columns) == ["conda_name", "staleness_age_days", "adoption_stage"]


# --------------------------------------------------------------------------- #
# identity_workbook_gap_message -- all four branches
# --------------------------------------------------------------------------- #


def test_identity_workbook_gap_message_both_present_is_none(tmp_path: Path):
    complete = tmp_path / "complete.parquet"
    enterprise = tmp_path / "enterprise.parquet"
    complete.write_bytes(b"x")
    enterprise.write_bytes(b"x")
    assert data.identity_workbook_gap_message(complete, enterprise) is None


def test_identity_workbook_gap_message_both_missing():
    msg = data.identity_workbook_gap_message(None, None)
    assert msg is not None
    assert data.IDENTITY_COMPLETE_EXPORT_PARQUET in msg
    assert data.ENTERPRISE_JFROG_CONSUMPTION_PARQUET in msg


def test_identity_workbook_gap_message_enterprise_missing(tmp_path: Path):
    complete = tmp_path / "complete.parquet"
    complete.write_bytes(b"x")
    msg = data.identity_workbook_gap_message(complete, tmp_path / "nope.parquet")
    assert msg is not None
    assert "Enterprise JFROG overlay missing" in msg
    assert data.ENTERPRISE_JFROG_CONSUMPTION_PARQUET in msg


def test_identity_workbook_gap_message_complete_missing(tmp_path: Path):
    enterprise = tmp_path / "enterprise.parquet"
    enterprise.write_bytes(b"x")
    msg = data.identity_workbook_gap_message(tmp_path / "nope.parquet", enterprise)
    assert msg is not None
    assert "Complete identity export missing" in msg
    assert data.IDENTITY_COMPLETE_EXPORT_PARQUET in msg


# --------------------------------------------------------------------------- #
# load_identity_workbook -- missing-file branches + real join success path
# --------------------------------------------------------------------------- #


def test_load_identity_workbook_returns_empty_when_either_side_is_none():
    got = data.load_identity_workbook(None, None)
    assert got.empty
    assert list(got.columns) == ["match_bucket", "package_count", "artifactory_downloads_total"]


def test_load_identity_workbook_returns_empty_when_either_side_missing_on_disk(tmp_path: Path):
    complete = tmp_path / "complete.parquet"
    complete.write_bytes(b"x")
    got = data.load_identity_workbook(str(complete), str(tmp_path / "nope.parquet"))
    assert got.empty


def test_load_identity_workbook_real_join_success(tmp_path: Path):
    complete = tmp_path / "identity_complete_export.parquet"
    pd.DataFrame(
        {
            "Core_Python_Package_Name": ["pkg-Alpha", "pkg_beta"],
            "primary_type": ["pypi", ""],
            "primary_purl": ["pkg:pypi/pkg-alpha", ""],
            "conda_purl": ["", "pkg:conda/pkg-beta?channel=conda-forge"],
            "Conda-Forge_FeedStock_URL": ["", ""],
        }
    ).to_parquet(complete)
    enterprise = tmp_path / "enterprise_jfrog_consumption.parquet"
    pd.DataFrame(
        {
            "repository_source": ["CDO-ENT-JFROG", "CDO-ENT-JFROG", "OTHER"],
            "core_python_package_name": ["pkg-alpha", "pkg-beta", "filtered-out"],
            "artifactory_downloads": pd.array([100, 50, 999], dtype="Int64"),
        }
    ).to_parquet(enterprise)

    got = data.load_identity_workbook(str(complete), str(enterprise))
    assert not got.empty
    assert set(got.columns) == {"match_bucket", "package_count", "artifactory_downloads_total"}
    by_bucket = dict(zip(got["match_bucket"], got["package_count"]))
    # pkg-alpha joins on PEP-503 name and is PyPI-verified only; pkg-beta is
    # conda-forge-verified only ("filtered-out" was dropped by the repository_source filter).
    assert by_bucket.get("pypi_only") == 1
    assert by_bucket.get("cf_only") == 1
    assert "filtered-out" not in got.to_string()
