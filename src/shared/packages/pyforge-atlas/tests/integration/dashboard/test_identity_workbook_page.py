"""Story 22.4 — identity-workbook Vizro page parity with write_workbook_canvas output."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pandas as pd
import vizro.models as vm

from pyforge.atlas.dashboard import data as dash_data
from pyforge.atlas.semantic import models
from pyforge.atlas.semantic.query_helpers import bsl_query

REPO_ROOT = Path(__file__).resolve().parents[7]
SCRIPTS_DIR = REPO_ROOT / "scripts"

_WORKBOOK_DIMENSIONS = ["match_bucket"]
_WORKBOOK_MEASURES = ["package_count", "artifactory_downloads_total"]


def _load_module(filename: str):
    script_path = SCRIPTS_DIR / filename
    assert script_path.is_file(), f"script not found: {script_path}"
    module_name = script_path.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _decode_data_blob(text: str, prefix: str) -> dict:
    assert text.startswith(prefix)
    remainder = text[len(prefix) :]
    data, _end = json.JSONDecoder().raw_decode(remainder)
    return data


def _hand_built_fixture() -> tuple[list[dict[str, str]], list[dict[str, object]]]:
    """Four JFROG packages covering both / pypi_only / cf_only / neither buckets."""
    records = [
        {
            "Core_Python_Package_Name": "both-pkg",
            "primary_type": "pypi",
            "primary_purl": "pkg:pypi/both-pkg",
            "conda_purl": "pkg:conda/both-pkg?channel=conda-forge",
            "Conda-Forge_FeedStock_URL": "https://github.com/conda-forge/both-feedstock",
        },
        {
            "Core_Python_Package_Name": "pypi-only-pkg",
            "primary_type": "pypi",
            "primary_purl": "pkg:pypi/pypi-only-pkg",
            "conda_purl": "",
            "Conda-Forge_FeedStock_URL": "",
        },
        {
            "Core_Python_Package_Name": "cf-only-pkg",
            "primary_type": "",
            "primary_purl": "",
            "conda_purl": "pkg:conda/cf-only-pkg?channel=conda-forge",
            "Conda-Forge_FeedStock_URL": "https://github.com/conda-forge/cf-only-feedstock",
        },
        {
            "Core_Python_Package_Name": "neither-pkg",
            "primary_type": "",
            "primary_purl": "",
            "conda_purl": "",
            "Conda-Forge_FeedStock_URL": "",
        },
    ]
    jfrog_rows = [
        {
            "core_python_package_name": "both-pkg",
            "repository_source": "CDO-ENT-JFROG",
            "artifactory_downloads": 100,
            "platform_env_count": 1,
            "internal_app_count": 0,
            "artifactory_version_count": 5,
            "internal_component_count": 0,
            "internal_lob_count": 0,
            "packaging_tier": "A",
            "verification_timestamp_utc": "2026-08-30T00:00:00Z",
        },
        {
            "core_python_package_name": "pypi-only-pkg",
            "repository_source": "CDO-ENT-JFROG",
            "artifactory_downloads": 80,
            "platform_env_count": 0,
            "internal_app_count": 1,
            "artifactory_version_count": 3,
            "internal_component_count": 0,
            "internal_lob_count": 0,
            "packaging_tier": "B",
            "verification_timestamp_utc": "2026-08-30T00:00:00Z",
        },
        {
            "core_python_package_name": "cf-only-pkg",
            "repository_source": "CDO-ENT-JFROG",
            "artifactory_downloads": 60,
            "platform_env_count": 0,
            "internal_app_count": 0,
            "artifactory_version_count": 2,
            "internal_component_count": 0,
            "internal_lob_count": 0,
            "packaging_tier": "C",
            "verification_timestamp_utc": "2026-08-30T00:00:00Z",
        },
        {
            "core_python_package_name": "neither-pkg",
            "repository_source": "CDO-ENT-JFROG",
            "artifactory_downloads": 40,
            "platform_env_count": 0,
            "internal_app_count": 0,
            "artifactory_version_count": 1,
            "internal_component_count": 0,
            "internal_lob_count": 0,
            "packaging_tier": "D",
            "verification_timestamp_utc": "2026-08-30T00:00:00Z",
        },
        {
            "core_python_package_name": "orphan-jfrog-pkg",
            "repository_source": "CDO-ENT-JFROG",
            "artifactory_downloads": 10,
            "platform_env_count": 0,
            "internal_app_count": 0,
            "artifactory_version_count": 1,
            "internal_component_count": 0,
            "internal_lob_count": 0,
            "packaging_tier": "D",
            "verification_timestamp_utc": "2026-08-30T00:00:00Z",
        },
    ]
    return records, jfrog_rows


def _records_to_ranked_export_df(records: list[dict[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(records)


def _write_workbook_canvas_data(
    records: list[dict[str, str]],
    jfrog_rows: list[dict[str, object]],
    tmp_path: Path,
) -> dict:
    dashboards = _load_module("openteams_identity_dashboards.py")
    identity = _load_module("conda-forge-packaging-inventory-operations_openteams_identity.py")
    helpers = types.SimpleNamespace(**vars(identity))
    export_path = tmp_path / "derived/identity_complete_export/identity_complete_export.parquet"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Core_Python_Package_Name": "anchor"}]).to_parquet(export_path)
    jfrog_path = tmp_path / "derived/enterprise_jfrog_consumption/enterprise_jfrog_consumption.parquet"
    jfrog_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(jfrog_rows).to_parquet(jfrog_path)
    canvas_path = tmp_path / "identity-workbook.canvas.tsx"
    dashboards.write_workbook_canvas(canvas_path, records, export_path, "identity-fixture", helpers)
    return _decode_data_blob(canvas_path.read_text(encoding="utf-8"), dashboards._CANVAS_PREFIX)


def _bucket_counts(loader_df: pd.DataFrame) -> dict[str, int]:
    if loader_df.empty:
        return {}
    out: dict[str, int] = {}
    for _, row in loader_df.iterrows():
        out[str(row["match_bucket"])] = int(row["package_count"])
    return out


def test_identity_workbook_loaders_empty_when_both_parquets_absent():
    got = dash_data.load_identity_workbook(None, None)
    assert got.empty
    assert list(got.columns) == [*_WORKBOOK_DIMENSIONS, *_WORKBOOK_MEASURES]


def test_identity_workbook_loader_empty_when_ranked_only(write_parquet):
    ranked_path = write_parquet(_records_to_ranked_export_df(_hand_built_fixture()[0]), "ranked")
    got = dash_data.load_identity_workbook(ranked_path, "/nope/enterprise.parquet")
    assert got.empty
    assert list(got.columns) == [*_WORKBOOK_DIMENSIONS, *_WORKBOOK_MEASURES]


def test_identity_workbook_loader_empty_when_enterprise_only(write_parquet, tmp_path):
    _, jfrog_rows = _hand_built_fixture()
    enterprise_path = tmp_path / "enterprise.parquet"
    pd.DataFrame(jfrog_rows).to_parquet(enterprise_path)
    got = dash_data.load_identity_workbook("/nope/ranked.parquet", enterprise_path)
    assert got.empty


def test_identity_workbook_gap_message_names_both_missing():
    msg = dash_data.identity_workbook_gap_message("/nope/ranked.parquet", "/nope/enterprise.parquet")
    assert dash_data.IDENTITY_COMPLETE_EXPORT_PARQUET in msg
    assert dash_data.ENTERPRISE_JFROG_CONSUMPTION_PARQUET in msg


def test_identity_workbook_gap_message_names_enterprise_only(write_parquet):
    ranked_path = write_parquet(_records_to_ranked_export_df(_hand_built_fixture()[0]), "ranked")
    msg = dash_data.identity_workbook_gap_message(ranked_path, "/nope/enterprise.parquet")
    assert dash_data.ENTERPRISE_JFROG_CONSUMPTION_PARQUET in msg
    assert "Story 23.2" in msg


def test_identity_workbook_gap_message_names_ranked_only(tmp_path):
    _, jfrog_rows = _hand_built_fixture()
    enterprise_path = tmp_path / "enterprise.parquet"
    pd.DataFrame(jfrog_rows).to_parquet(enterprise_path)
    msg = dash_data.identity_workbook_gap_message("/nope/ranked.parquet", enterprise_path)
    assert dash_data.IDENTITY_COMPLETE_EXPORT_PARQUET in msg
    assert "Story 23.5" in msg


def test_identity_workbook_page_card_names_both_missing(dashboard):
    page = next(p for p in dashboard.pages if p.id == "identity-workbook")
    about = next(c for c in page.components if c.id == "identity-workbook--about")
    assert dash_data.IDENTITY_COMPLETE_EXPORT_PARQUET in about.text
    assert dash_data.ENTERPRISE_JFROG_CONSUMPTION_PARQUET in about.text


def test_identity_workbook_page_has_external_reference_card(dashboard):
    page = next(p for p in dashboard.pages if p.id == "identity-workbook")
    external = next(c for c in page.components if c.id == "identity-workbook--external")
    dashboards = _load_module("openteams_identity_dashboards.py")
    for row in dashboards.EXTERNAL_LIVE:
        assert row[0] in external.text


def test_identity_workbook_parity_with_write_workbook_canvas(tmp_path, write_parquet):
    records, jfrog_rows = _hand_built_fixture()
    data = _write_workbook_canvas_data(records, jfrog_rows, tmp_path)
    ranked_path = write_parquet(_records_to_ranked_export_df(records), "identity_complete_export")
    enterprise_path = tmp_path / "derived/enterprise_jfrog_consumption/enterprise_jfrog_consumption.parquet"
    loader_df = dash_data.load_identity_workbook(ranked_path, enterprise_path)
    got = _bucket_counts(loader_df)
    canvas = data["jfrogMap"]
    assert got.get("both", 0) == canvas["both"]
    assert got.get("pypi_only", 0) == canvas["pypiOnly"]
    assert got.get("cf_only", 0) == canvas["cfOnly"]
    assert got.get("neither", 0) == canvas["neither"]


def test_identity_workbook_page_is_bsl_driven(tmp_path, write_parquet):
    records, jfrog_rows = _hand_built_fixture()
    ranked_path = write_parquet(_records_to_ranked_export_df(records), "identity_complete_export")
    enterprise_path = tmp_path / "derived/enterprise_jfrog_consumption/enterprise_jfrog_consumption.parquet"
    enterprise_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(jfrog_rows).to_parquet(enterprise_path)
    got = dash_data.load_identity_workbook(ranked_path, enterprise_path)
    import ibis

    con = ibis.duckdb.connect()
    ranked = models.duckdb_table_from_parquet(ranked_path, connection=con)
    enterprise = models.duckdb_table_from_parquet(str(enterprise_path), connection=con)
    enterprise = enterprise.filter(enterprise.repository_source == "CDO-ENT-JFROG")
    join_key = dash_data._ibis_pep503
    ent = enterprise.mutate(_join_key=join_key(enterprise.core_python_package_name))
    ent = ent.filter(ent._join_key.length() >= 2).distinct(on=["_join_key"], keep="first")
    ranked_side = ranked.mutate(_join_key=join_key(ranked.Core_Python_Package_Name)).distinct(
        on=["_join_key"], keep="last"
    )
    feedstock_col = "Conda-Forge_FeedStock_URL"
    ranked_pick = ranked_side.select(
        "_join_key",
        "primary_type",
        "primary_purl",
        "conda_purl",
        **{feedstock_col: ranked_side[feedstock_col]},
    )
    joined = ent.left_join(ranked_pick, "_join_key")
    expected = bsl_query(
        models.build_identity_workbook_model(joined),
        dimensions=_WORKBOOK_DIMENSIONS,
        measures=_WORKBOOK_MEASURES,
    )
    pd.testing.assert_frame_equal(
        got.sort_values("match_bucket").reset_index(drop=True),
        expected.sort_values("match_bucket").reset_index(drop=True),
    )


def test_identity_workbook_page_has_grid(dashboard):
    page = next(p for p in dashboard.pages if p.id == "identity-workbook")
    grids = [c for c in page.components if isinstance(c, vm.AgGrid)]
    assert len(grids) == 1
    assert grids[0].id == "identity-workbook--grid"
