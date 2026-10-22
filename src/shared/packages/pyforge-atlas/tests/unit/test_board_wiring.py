"""Story 37.3 (spec-pyforge-atlas CAP-69): six boards read the datasets the pipelines write; Story 37.4
adds four more paths, read with ``pyforge.atlas.board_projections`` on.

Each loader runs on a frame shaped like its produced dataset (the columns the pipeline node
writes), and the board path is that dataset's catalog ``filepath``. No network.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from pyforge.atlas.dashboard import data
from pyforge.atlas.pipelines.derived_artifacts.nodes import (
    DISTRIBUTION_BREAKDOWN_COLUMNS,
    compose_distribution_breakdown,
)

CATALOG = Path(__file__).resolve().parents[2] / "conf" / "base" / "catalog.yml"


def _write(tmp_path: Path, frame: pd.DataFrame) -> Path:
    path = tmp_path / "store.parquet"
    frame.to_parquet(path, index=False)
    return path


@pytest.mark.parametrize(
    ("constant", "dataset"),
    [
        ("VERSION_DOWNLOADS_PARQUET", "core_version_download_history"),
        ("DISTRIBUTION_BREAKDOWN_PARQUET", "derived_distribution_breakdown"),
        ("LTS_REGISTRY_GAP_PARQUET", "seed_gaps_lts_registry_report"),
        ("CWE_SEED_GAP_PARQUET", "seed_gaps_cwe_report"),
        ("SPDX_SCHEMA_GAP_PARQUET", "seed_gaps_spdx_report"),
        ("LICENSE_MAP_GAP_PARQUET", "seed_gaps_license_map_report"),
        # Story 37.4 (with pyforge.atlas.board_projections on)
        ("BEHIND_UPSTREAM_PARQUET", "derived_behind_upstream"),
        ("CORE_DEPENDENCIES_PARQUET", "core_dependencies"),
        ("DERIVED_LIVE_CATALOG_COVERAGE_PARQUET", "derived_live_catalog_coverage"),
        ("DERIVED_UNIVERSE_SBOM_SUMMARY_PARQUET", "derived_universe_sbom_summary"),
    ],
)
def test_each_board_reads_the_path_its_dataset_is_written_to(constant, dataset):
    catalog = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))

    written = catalog[dataset]["filepath"].replace("${globals:paths.data_root}/", "")

    assert getattr(data, constant) == written


def test_version_downloads_reads_the_download_history_with_no_upload_date(tmp_path):
    frame = pd.DataFrame({"conda_name": ["a", "a"], "version": ["1", "2"], "downloads": [5, 7], "fetched_at": [1, 1]})

    out = data.load_version_downloads(_write(tmp_path, frame)).sort_values("version")

    assert out["downloads"].tolist() == [5, 7] and out["upload_date"].isna().all()  # null, never invented


def test_the_lts_board_reads_the_report_under_its_names(tmp_path):
    frame = pd.DataFrame(
        {"conda_name": ["p"], "pypi_name": ["p"], "slug": ["python"], "confidence": ["strong"], "matched_via": ["x"]}
    )

    out = data.load_lts_registry_gap(_write(tmp_path, frame))

    assert out.to_dict("records") == [
        {"product_name": "python", "tier": "strong", "matched_conda_name": "p", "candidate_count": 1}
    ]


def test_the_cwe_board_reads_the_report_and_leaves_the_impact_null(tmp_path):
    frame = pd.DataFrame(
        {"cwe_id": ["CWE-1"], "cwe_name": ["x"], "category": ["Injection"], "confidence": ["weak"], "matched": ["y"]}
    )

    (row,) = data.load_cwe_seed_gap(_write(tmp_path, frame)).to_dict("records")

    assert (row["cwe_id"], row["tier"], row["suggested_category"]) == ("CWE-1", "weak", "Injection")
    assert pd.isna(row["package_impact_count"])  # DW-B6-2: deferred, never a fabricated 0


def test_the_spdx_board_names_a_license_by_its_spdx_id_else_its_text(tmp_path):
    frame = pd.DataFrame(
        {"license": ["MIT", "Foo"], "spdx_id": [None, "Foo-1"], "packages": [3, 1], "tier": ["a", "b"]}
    )

    out = data.load_spdx_schema_gap(_write(tmp_path, frame)).set_index("license_id")

    assert out["package_usage_count"].to_dict() == {"MIT": 3, "Foo-1": 1}


def test_the_license_map_board_reads_the_report_under_its_names(tmp_path):
    frame = pd.DataFrame(
        {
            "license_raw": ["BSD"],
            "packages": [2],
            "candidates": ["x"],
            "confidence": ["weak"],
            "suggested_spdx": ["BSD-3-Clause"],
        }
    )

    out = data.load_license_map_gap(_write(tmp_path, frame))

    assert out.to_dict("records") == [
        {"license_raw": "BSD", "tier": "weak", "suggested_spdx": "BSD-3-Clause", "package_count": 2}
    ]


def test_the_distribution_table_joins_the_three_cuts_behind_a_facet():
    platform = pd.DataFrame({"conda_name": ["a"], "platform": ["linux-64"], "downloads": [9], "fetched_at": [1]})
    pyver = pd.DataFrame({"conda_name": ["a"], "pyver": ["3.12"], "downloads": [4], "fetched_at": [1]})
    channel = pd.DataFrame({"conda_name": ["a"], "channel": ["conda-forge"], "downloads": [13], "fetched_at": [1]})

    out = compose_distribution_breakdown(platform, pyver, channel)

    assert list(out.columns) == list(DISTRIBUTION_BREAKDOWN_COLUMNS)
    assert out[["facet", "bucket", "downloads_90d"]].values.tolist() == [
        ["platform", "linux-64", 9],
        ["python-version", "3.12", 4],
        ["channel", "conda-forge", 13],
    ]
    assert out["declared_python_min"].isna().all() and out["empirical_floor"].isna().all()


def test_the_distribution_table_is_empty_when_no_cut_is(tmp_path):
    empty = pd.DataFrame(columns=["conda_name", "platform", "downloads", "fetched_at"])

    out = compose_distribution_breakdown(empty, None, pd.DataFrame({"x": [1]}))

    assert out.empty and list(out.columns) == list(DISTRIBUTION_BREAKDOWN_COLUMNS)
    assert out["downloads_90d"].dtype == "Int64" and out["bucket"].dtype == "string"  # typed, never Arrow null


def test_the_distribution_board_reads_an_empty_composed_table(tmp_path):
    # a run with no download store composes an empty table; the board shows it empty, never a crash
    frame = compose_distribution_breakdown(None, None, None)

    out = data.load_distribution_breakdown(_write(tmp_path, frame))

    assert out.empty and {"facet", "bucket", "python_min_bump_status", "downloads_90d"} <= set(out.columns)


def test_the_distribution_board_reads_the_composed_table(tmp_path):
    platform = pd.DataFrame({"conda_name": ["a", "b"], "platform": ["linux-64", "osx-64"], "downloads": [9, 2]})
    frame = compose_distribution_breakdown(platform, None, None)

    out = data.load_distribution_breakdown(_write(tmp_path, frame)).sort_values("conda_name")

    assert out["downloads_90d"].tolist() == [9, 2] and set(out["python_min_bump_status"]) == {"unknown"}
