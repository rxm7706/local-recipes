"""Every board's BSL model answers its declared query over a Parquet store (Story 37.3).

The dashboard integration suite reaches these builders, but only from `tests/integration`, which the
diff-scoped `unit` coverage gate does not count. Each case writes a two-row store shaped like the
board's dataset, reads it through the same seam the boards use (`duckdb_table_from_parquet`), and
checks that the grouped query returns every declared dimension and measure and that one measure's
grand total is right. Every column holds at least one value: an all-null column is written as Arrow
`null` and read back as INTEGER, so it is not the shape a pipeline writes. No network.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pyforge.atlas.semantic import models
from pyforge.atlas.semantic.query_helpers import bsl_query

_IDENTITY = {
    "Core_Python_Package_Name": ["alpha", "beta"],
    "P": ["P1", None],
    "Work": ["build", "triage"],
    "OpenTeams_Issue_URL": ["https://example.invalid/i/1", None],
    "Local_Build_Status": ["success", None],
    "Conda-Forge_FeedStock_URL": [None, "https://example.invalid/f/beta"],
    "Staged_Recipes_PR_URL": [None, "https://example.invalid/pr/2"],
    "Local_Recipes_URL": ["recipes/alpha", None],
}

# builder, store columns, the measure checked, its grand total over the two rows
CASES = [
    (models.build_maintainers_model, {"maintainer": ["a", "b"]}, "maintainer_count", 2),
    (
        models.build_vuln_history_model,
        {
            "conda_name": ["p", "q"],
            "severity": ["high", "low"],
            "since_days": [30, 30],
            "vuln_kev_affecting_current": [False, True],
            "then_count": [1, 2],
            "now_count": [3, 2],
        },
        "delta",
        2,
    ),
    (
        models.build_release_cadence_model,
        {"conda_name": ["p", "q"], "releases_30d": [0, 2], "releases_90d": [0, 2], "releases_365d": [0, 5]},
        "release_count_365d",
        5,
    ),
    (
        models.build_alternative_candidates_model,
        {
            "archived_name": ["old", "old"],
            "candidate_name": ["new1", "new2"],
            "latest_upload_age_days": [10, 800],
            "releases_30d": [1, 0],
            "total_versions": [3, 5],
            "similarity_score": [0.5, 1.0],
            "downloads_total": [10, 20],
        },
        "downloads_total",
        30,
    ),
    (
        models.build_scan_result_model,
        {
            "conda_name": ["p", "q"],
            "severity": ["high", "low"],
            "license_spdx": ["MIT", "GPL-3.0-only"],
            "fix_available": [True, False],
            "scan_status": ["ok", "ok"],
        },
        "finding_count",
        2,
    ),
    (
        models.build_env_inspect_model,
        {
            "conda_name": ["p", "q"],
            "license_spdx": ["MIT", "GPL-3.0-only"],
            "non_permissive_flag": [False, True],
            "vuln_critical": [1, 2],
            "vuln_high": [0, 4],
        },
        "vuln_high",
        4,
    ),
    (
        models.build_purl_export_model,
        {"artifact_name": ["purls.csv", "purls.json"], "regenerated_at": [1, 1], "row_count": [7, 8]},
        "row_count",
        15,
    ),
    (
        models.build_mapping_gap_model,
        {
            "conda_name": ["p", "q"],
            "classification": ["unmapped", "renamed"],
            "match_source": ["none", "pypi"],
            "match_confidence": ["low", "high"],
        },
        "gap_count",
        2,
    ),
    (
        models.build_universe_sbom_summary_model,
        {"component_purl": ["pkg:conda/p", "pkg:conda/q"], "slice": ["all", "all"], "with_vulns_count": [1, 3]},
        "with_vulns_count",
        4,
    ),
    (
        models.build_inventory_match_report_model,
        {
            "conda_name": ["p", "q"],
            "bucket": ["matched", "missing"],
            "freshness_percentile": [10.0, 90.0],
            "match_confidence": ["high", "low"],
        },
        "row_count",
        2,
    ),
    (
        models.build_add_handoff_report_model,
        {"conda_name": ["p", "q"], "readiness": ["ready", "blocked"], "license_blocker": [False, True]},
        "row_count",
        2,
    ),
    (
        models.build_library_futures_report_model,
        {
            "package_name": ["p", "q"],
            "futures_tier": ["A", "B"],
            "py314_readiness": ["ready", "unknown"],
            "futures_score": [0.5, 1.0],
        },
        "futures_score",
        0.75,
    ),
    (
        models.build_recommend_2027_model,
        {
            "package_name": ["p", "q"],
            "futures_tier": ["A", "B"],
            "lts_status": ["supported", "eol"],
            "eol_date": ["2027-01-01", "2025-01-01"],
            "futures_score": [0.25, 0.75],
        },
        "futures_score",
        0.5,
    ),
    (
        models.build_identity_catalog_model,
        {
            "P": ["P1", "P2"],
            "Rank": [1, 2],
            "Score": [9.0, 8.0],
            "Package": ["alpha", "beta"],
            "Work": ["build", "triage"],
            "Core_Python_Package_Name": ["alpha", "beta"],
            "Platforms": ["linux-64", "noarch"],
            "Apps": [1, 0],
            "Downloads": [100, 50],
            "Versions": [3, 1],
            "Vuln": [0, 1],
        },
        "package_count",
        2,
    ),
    (models.build_identity_ops_model, _IDENTITY, "package_count", 2),
    (
        models.build_bootstrap_index_health_model,
        {
            "catalog_entry": ["core_packages", "vcs_github_api_raw"],
            "tier": [0, 1],
            "regenerated_at": [1, 1],
            "row_count": [10, 5],
        },
        "row_count",
        15,
    ),
    (
        models.build_identity_export_snapshot_model,
        {
            "identity_source": ["inventory", "inventory"],
            "Core_Python_Package_Name": ["alpha", "beta"],
            "primary_purl": ["pkg:pypi/alpha", None],
            "OpenTeams_Issue_URL": [None, "https://example.invalid/i/2"],
        },
        "primary_purl_coverage_count",
        1,
    ),
    (
        models.build_live_catalog_coverage_model,
        {"field_name": ["license", "homepage"], "true_count": [3, 4], "total_count": [5, 5]},
        "total_count",
        10,
    ),
]


def _model(tmp_path: Path, builder, columns: dict, **kwargs):
    path = tmp_path / "store.parquet"
    pd.DataFrame(columns).to_parquet(path, index=False)
    return builder(models.duckdb_table_from_parquet(str(path)), **kwargs)


@pytest.mark.parametrize(("builder", "columns", "measure", "total"), CASES, ids=lambda c: getattr(c, "__name__", None))
def test_each_board_model_answers_its_declared_query(tmp_path, builder, columns, measure, total):
    model = _model(tmp_path, builder, columns)
    dimensions, measures = list(model.get_dimensions()), list(model.get_measures())

    grouped = bsl_query(model, dimensions=dimensions, measures=measures)
    (row,) = bsl_query(model, measures=[measure]).to_dict("records")

    assert set(grouped.columns) == {*dimensions, *measures} and 1 <= len(grouped) <= 2
    assert row[measure] == pytest.approx(total)


def test_the_release_cadence_trend_follows_the_legacy_classifier(tmp_path):
    columns = {"conda_name": ["p", "q"], "releases_30d": [0, 2], "releases_90d": [0, 2], "releases_365d": [0, 5]}
    model = _model(tmp_path, models.build_release_cadence_model, columns)

    out = bsl_query(model, dimensions=["conda_name", "trend_label"], measures=["release_count_30d"])

    assert dict(zip(out["conda_name"], out["trend_label"], strict=True)) == {"p": "silent", "q": "accelerating"}


def test_a_candidates_stage_is_the_adoption_stage_boards(tmp_path):
    """Story 37.7: find-alternative classifies a candidate with build_packages_model's classifier."""
    stage = {
        "latest_upload_age_days": [10, 800, 400, None],
        "releases_30d": [1, 0, 0, None],
        "total_versions": [3, 5, 2, None],
    }
    names = ["fresh", "silent", "declining", "unknown"]
    (tmp_path / "c").mkdir()
    (tmp_path / "p").mkdir()
    candidates = _model(
        tmp_path / "c",
        models.build_alternative_candidates_model,
        {
            "archived_name": ["old"] * 4,
            "candidate_name": names,
            "similarity_score": [1.0] * 4,
            "downloads_total": [1] * 4,
            **stage,
        },
    )
    packages = _model(
        tmp_path / "p",
        models.build_packages_model,
        {"conda_name": names, "latest_status": ["active"] * 4, "feedstock_archived": [0] * 4, **stage},
    )

    out = bsl_query(candidates, dimensions=["candidate_name", "adoption_stage"], measures=["similarity_score"])
    ref = bsl_query(packages, dimensions=["conda_name", "adoption_stage"], measures=["package_count"])

    assert (
        dict(zip(out["candidate_name"], out["adoption_stage"], strict=True))
        == dict(zip(ref["conda_name"], ref["adoption_stage"], strict=True))
        == {"fresh": "stable", "silent": "silent", "declining": "declining", "unknown": "unknown"}
    )


def test_the_identity_export_counts_each_gist_column_it_is_given(tmp_path):
    columns = {
        **_IDENTITY,
        "identity_source": ["inventory", None],
        "primary_type": ["pypi", None],
        "primary_purl": ["pkg:pypi/alpha", None],
        "conda_purl": [None, "pkg:conda/beta"],
    }
    model = _model(
        tmp_path,
        models.build_identity_complete_export_model,
        columns,
        gist_columns=("primary_purl", "Conda-Forge_FeedStock_URL"),
    )

    (row,) = bsl_query(
        model, measures=["identity_row_count", "filled_primary_purl", "filled_Conda_Forge_FeedStock_URL"]
    ).to_dict("records")

    assert (row["identity_row_count"], row["filled_primary_purl"], row["filled_Conda_Forge_FeedStock_URL"]) == (2, 1, 1)
