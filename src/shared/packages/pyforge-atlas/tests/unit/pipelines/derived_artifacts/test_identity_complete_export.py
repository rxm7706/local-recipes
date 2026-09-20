"""Story 23.5 — build_identity_complete_export parity vs GIST_COLUMNS + §4 schema."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd
import pytest

from pyforge.atlas.pipelines.derived_artifacts.nodes import (
    _IDENTITY_COMPLETE_EXPORT_COLUMNS,
    build_identity_complete_export,
)

_REPO_ROOT = Path(__file__).resolve().parents[8]
_IDENTITY_SCRIPT = _REPO_ROOT / "scripts" / "conda-forge-packaging-inventory-operations_openteams_identity.py"
_FIXTURE_DIR = _REPO_ROOT / "src/shared/packages/pyforge-atlas/tests/fixtures/inventory_identity"

_FIXED_TS = "2026-08-30T12:00:00Z"
_PARAMS = {"identity_complete_export": {"verification_timestamp_utc": _FIXED_TS}}


def _gist_columns_from_script() -> list[str]:
    """Parse ``GIST_SCHEMA`` names without importing the legacy script (openpyxl)."""
    source = _IDENTITY_SCRIPT.read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "GIST_SCHEMA":
                    schema = ast.literal_eval(node.value)
                    return [str(row[0]) for row in schema]
    raise RuntimeError(f"GIST_SCHEMA not found in {_IDENTITY_SCRIPT}")


GIST_COLUMNS = _gist_columns_from_script()


def _identity_row(
    name: str,
    *,
    identity_source: str = "inventory",
    issue_url: str = "",
    conda_purl: str = "",
    feedstock_url: str = "",
) -> dict:
    return {
        "Core_Python_Package_Name": name,
        "OpenTeams_Title": f"[Conda-Forge Packaging] {name}",
        "identity_source": identity_source,
        "associator_key": name,
        "associator_status": "inventory-derived",
        "primary_purl": f"pkg:pypi/{name}",
        "primary_type": "pypi",
        "alternative_purls": "",
        "cpes": "",
        "conda_purl": conda_purl,
        "source_repository_url": "",
        "OpenTeams_Issue_URL": issue_url,
        "Conda-Forge_FeedStock_URL": feedstock_url,
        "Conda-Forge_Metadata_URL": "",
        "Staged_Recipes_PR_URL": "",
        "Local_Recipes_URL": "",
        "Local_Build_Status": "",
        "Verification_Timestamp_UTC": "2026-01-01T00:00:00Z",
    }


def _priority_row(name: str, **extra: object) -> dict:
    base = {
        "core_python_package_name": name,
        "P": "P4",
        "Rank": 1,
        "Score": 88,
        "Work": "Create recipe",
        "Priority_Bucket_Description": "Used in one or more platform environments (platform_env_count > 0).",
        "Priority_Source": "platform",
        "Priority_Reason": "platform_env_count>0",
        "risk_level": "LOW",
        "vuln_status": "clean",
        "jfrog_latest_vuln_count": 0,
    }
    base.update(extra)
    return base


def _jfrog_row(name: str, **extra: object) -> dict:
    base = {
        "core_python_package_name": name,
        "platform_env_count": 2,
        "internal_app_count": 1,
        "artifactory_downloads": 50,
        "artifactory_version_count": 5,
        "internal_component_count": 3,
        "internal_lob_count": 1,
    }
    base.update(extra)
    return base


def _verified_row(name: str, **extra: object) -> dict:
    base = {
        "Core_Python_Package_Name": name,
        "Repository_Source": "tab:Conda-Forge",
        "Role": "Maintainer",
        "PyPI_Verified": "Yes",
        "CondaForge_Verified": "Yes",
        "Packaging_Candidate_Status": "Already Packaged",
    }
    base.update(extra)
    return base


def _universe_row(name: str, **flags: bool) -> dict:
    base = {
        "core_python_package_name": name,
        "in_basilisk": False,
        "in_aoss_free": False,
        "in_aoss_premium": False,
        "in_anaconda_main": False,
        "in_anaconda_dist": False,
    }
    base.update(flags)
    return base


def _run(
    identity_rows: list[dict],
    *,
    priority_rows: list[dict] | None = None,
    jfrog_rows: list[dict] | None = None,
    verified_rows: list[dict] | None = None,
    universe_rows: list[dict] | None = None,
    cross_rows: list[dict] | None = None,
    tier3_rows: list[dict] | None = None,
    jfrog_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    return build_identity_complete_export(
        pd.DataFrame(identity_rows),
        pd.DataFrame(priority_rows or []),
        jfrog_df if jfrog_df is not None else pd.DataFrame(jfrog_rows or []),
        pd.DataFrame([]),
        pd.DataFrame(verified_rows or []),
        pd.DataFrame(cross_rows or []),
        pd.DataFrame(tier3_rows or []),
        pd.DataFrame(universe_rows or []),
        _PARAMS,
    )


def test_output_has_exactly_63_byte_identical_column_names():
    out = _run([_identity_row("sample-pkg")])
    assert set(out.columns) == set(_IDENTITY_COMPLETE_EXPORT_COLUMNS)
    assert len(out.columns) == 63


def test_gist_columns_are_strict_subset_of_complete_export():
    out = _run([_identity_row("gist-pkg")])
    assert set(GIST_COLUMNS) <= set(out.columns)


def test_happy_path_populates_ranking_jfrog_and_verification():
    out = _run(
        [_identity_row("happy-pkg", issue_url="https://github.com/org/repo/issues/1")],
        priority_rows=[_priority_row("happy-pkg")],
        jfrog_rows=[_jfrog_row("happy-pkg")],
        verified_rows=[_verified_row("happy-pkg")],
        universe_rows=[_universe_row("happy-pkg", in_basilisk=True)],
        cross_rows=[
            {
                "conda_name": "happy-pkg",
                "in_pytorch": True,
                "in_bioconda": False,
                "in_nvidia": False,
                "in_robostack": False,
                "in_selfexplainml": False,
            }
        ],
        tier3_rows=[
            {
                "pypi_name": "happy-pkg",
                "in_homebrew": True,
                "in_nixpkgs": False,
                "in_spack": False,
                "in_debian": False,
                "in_fedora": False,
            }
        ],
    )
    row = out.iloc[0]
    assert row["Package"] == "happy-pkg"
    assert row["P"] == "P4"
    assert row["Platforms"] == 2
    assert row["Vuln"] == "clean"
    assert row["JFROG_vuln_status"] == "clean"
    assert row["platform_env_count"] == 2
    assert row["OpenTeams_Batch"] == row["Work"] == "Create recipe"
    assert row["OpenTeams_Coverage"] == "Have_Issue"
    assert row["PyPI_Verified"] == "Yes"
    assert row["in_basilisk"]
    assert row["in_pytorch"]
    assert row["in_homebrew"]
    assert row["Verification_Timestamp_UTC"] == _FIXED_TS


def test_absent_enterprise_parquet_degrades_artifactory_columns_only():
    out = _run(
        [_identity_row("no-jfrog")],
        priority_rows=[_priority_row("no-jfrog", vuln_status="affected_latest", risk_level="HIGH")],
        jfrog_df=None,
    )
    row = out.iloc[0]
    assert pd.isna(row["Platforms"])
    assert pd.isna(row["internal_component_count"])
    assert row["Vuln"] == "affected_latest"
    assert row["JFROG_risk_level"] == "HIGH"


def test_missing_priority_row_survives_with_blank_ranking():
    out = _run([_identity_row("orphan-pkg")], priority_rows=[])
    row = out.iloc[0]
    assert row["Core_Python_Package_Name"] == "orphan-pkg"
    assert pd.isna(row["P"])
    assert pd.isna(row["Rank"])
    assert pd.isna(row["Work"])


def test_board_only_row_has_blank_verification_and_enterprise():
    out = _run(
        [
            _identity_row(
                "board-only-pkg",
                identity_source="openteams-board",
                issue_url="https://github.com/org/repo/issues/99",
            )
        ],
        priority_rows=[_priority_row("board-only-pkg")],
        jfrog_rows=[_jfrog_row("board-only-pkg")],
        verified_rows=[_verified_row("board-only-pkg")],
    )
    row = out.iloc[0]
    assert row["identity_source"] == "openteams-board"
    assert pd.isna(row["PyPI_Verified"])
    assert pd.isna(row["CondaForge_Verified"])
    assert pd.isna(row["Packaging_Candidate_Status"])
    assert pd.isna(row["Repository_Source"])
    assert pd.isna(row["Platforms"])
    assert pd.isna(row["internal_component_count"])
    assert row["OpenTeams_Cohort"] == ""


def test_absent_tier3_source_yields_false_not_failure():
    out = _run([_identity_row("no-tier3")], tier3_rows=None)
    row = out.iloc[0]
    assert not row["in_debian"]
    assert not row["in_fedora"]


def test_openteams_cohort_jfrog_new_vs_on_cf():
    out_new = _run(
        [_identity_row("jfrog-new")],
        jfrog_rows=[_jfrog_row("jfrog-new")],
        verified_rows=[_verified_row("jfrog-new", CondaForge_Verified="No")],
    )
    assert out_new.iloc[0]["OpenTeams_Cohort"] == "JFROG_NEW"

    out_cf = _run(
        [_identity_row("jfrog-cf", conda_purl="pkg:conda/jfrog-cf?channel=conda-forge")],
        jfrog_rows=[_jfrog_row("jfrog-cf")],
        verified_rows=[_verified_row("jfrog-cf", CondaForge_Verified="Yes")],
    )
    assert out_cf.iloc[0]["OpenTeams_Cohort"] == "JFROG_ON_CF"


def test_empty_identity_yields_empty_typed_frame():
    out = _run([])
    assert out.empty
    assert list(out.columns) == list(_IDENTITY_COMPLETE_EXPORT_COLUMNS)


@pytest.mark.skipif(not _FIXTURE_DIR.exists(), reason="fixture corpus not present")
def test_fixture_corpus_column_parity():
    corpus = json.loads((_FIXTURE_DIR / "complete_export_expected.json").read_text(encoding="utf-8"))
    out = _run(
        corpus["identity_packages_primary"],
        priority_rows=corpus.get("inventory_priority_assignments"),
        jfrog_rows=corpus.get("enterprise_jfrog_consumption"),
        verified_rows=corpus.get("inventory_verified_packages"),
        universe_rows=corpus.get("inventory_universe"),
        cross_rows=corpus.get("pypi_cross_channel_flags"),
        tier3_rows=corpus.get("pypi_tier3_channel_flags"),
    )
    assert list(out.columns) == corpus["expected_columns"]
    got = out.to_dict(orient="records")[0]
    expected = corpus["expected_rows"][0]
    for key, exp in expected.items():
        assert key in got
        if pd.isna(exp):
            assert pd.isna(got[key])
        else:
            assert got[key] == exp
