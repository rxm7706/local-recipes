"""Story 22.3 — identity-ops Vizro page parity with write_ops_canvas output."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pandas as pd
import pytest
import vizro.models as vm

from pyforge.atlas.dashboard import data as dash_data
from pyforge.atlas.semantic import models
from pyforge.atlas.semantic.query_helpers import bsl_query

REPO_ROOT = Path(__file__).resolve().parents[7]
SCRIPTS_DIR = REPO_ROOT / "scripts"

_CENSUS_DIMENSIONS = ["has_feedstock", "has_staged_pr", "has_local_recipe"]
_BUILD_STATUS_COLS = {
    "success": 2,
    "build-clean-test-blocked": 3,
    "failed": 4,
    "not-attempted": 5,
    "blank": 6,
}


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


def _hand_built_fixture() -> list[dict[str, str]]:
    return [
        {
            "Core_Python_Package_Name": "alpha-pkg",
            "P": "P1",
            "Work": "Already tracked",
            "Local_Build_Status": "success",
            "OpenTeams_Issue_URL": "https://github.com/x/y/issues/1",
            "Conda-Forge_FeedStock_URL": "https://github.com/conda-forge/alpha-feedstock",
            "Staged_Recipes_PR_URL": "",
            "Local_Recipes_URL": "https://github.com/rxm7706/local-recipes/tree/main/recipes/alpha",
        },
        {
            "Core_Python_Package_Name": "beta-pkg",
            "P": "P1",
            "Work": "Create recipe",
            "Local_Build_Status": "",
            "OpenTeams_Issue_URL": "",
            "Conda-Forge_FeedStock_URL": "",
            "Staged_Recipes_PR_URL": "",
            "Local_Recipes_URL": "",
        },
        {
            "Core_Python_Package_Name": "gamma-pkg",
            "P": "P2",
            "Work": "File OpenTeams tracking issue [Conda-Forge Packaging]",
            "Local_Build_Status": "failed",
            "OpenTeams_Issue_URL": "https://github.com/x/y/issues/2",
            "Conda-Forge_FeedStock_URL": "",
            "Staged_Recipes_PR_URL": "https://github.com/conda-forge/staged-recipes/pull/1",
            "Local_Recipes_URL": "",
        },
    ]


def _records_to_ranked_export_df(records: list[dict[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "P": [r["P"] for r in records],
            "Work": [r["Work"] for r in records],
            "Core_Python_Package_Name": [r["Core_Python_Package_Name"] for r in records],
            "Local_Build_Status": [r["Local_Build_Status"] for r in records],
            "OpenTeams_Issue_URL": [r["OpenTeams_Issue_URL"] for r in records],
            "Conda-Forge_FeedStock_URL": [r["Conda-Forge_FeedStock_URL"] for r in records],
            "Staged_Recipes_PR_URL": [r["Staged_Recipes_PR_URL"] for r in records],
            "Local_Recipes_URL": [r["Local_Recipes_URL"] for r in records],
        }
    )


def _write_ops_canvas_data(records: list[dict], tmp_path: Path, monkeypatch) -> dict:
    dashboards = _load_module("openteams_identity_dashboards.py")
    identity = _load_module("conda-forge-packaging-inventory-operations_openteams_identity.py")
    monkeypatch.setattr(identity, "overlay_live_local", lambda _records, _dir: None)
    monkeypatch.setattr(identity, "load_local_recipe_type", lambda _dir: {})
    helpers = types.SimpleNamespace(**vars(identity))
    canvas_path = tmp_path / "identity-ops.canvas.tsx"
    dashboards.write_ops_canvas(canvas_path, records, "identity-fixture", helpers)
    return _decode_data_blob(canvas_path.read_text(encoding="utf-8"), dashboards._CANVAS_PREFIX)


def test_identity_ops_parity_with_write_ops_canvas(tmp_path, write_parquet, monkeypatch):
    """Priority/Issues/Builds pane totals match write_ops_canvas DATA on a shared fixture."""
    records = _hand_built_fixture()
    data = _write_ops_canvas_data(records, tmp_path, monkeypatch)
    parquet_path = write_parquet(_records_to_ranked_export_df(records), "identity_complete_export")

    priority_df = dash_data.load_identity_ops_priority(parquet_path)
    priority_totals = priority_df.groupby("P", as_index=False)["package_count"].sum()
    for p, count in data["priorityCounts"].items():
        row = priority_totals.loc[priority_totals["P"] == p, "package_count"]
        assert not row.empty
        assert int(row.iloc[0]) == count

    issues_df = dash_data.load_identity_ops_issues(parquet_path)
    for p, have, miss, _miss_pct in data["issues"]["byP"]:
        if have == 0 and miss == 0:
            continue
        have_row = issues_df.loc[
            (issues_df["P"] == p) & (issues_df["has_open_issue"] == True), "package_count"  # noqa: E712
        ]
        miss_row = issues_df.loc[
            (issues_df["P"] == p) & (issues_df["has_open_issue"] == False), "package_count"  # noqa: E712
        ]
        have_got = int(have_row.iloc[0]) if len(have_row) else 0
        miss_got = int(miss_row.iloc[0]) if len(miss_row) else 0
        assert have_got == have
        assert miss_got == miss

    builds_df = dash_data.load_identity_ops_builds(parquet_path)
    builds_by_status = dict(zip(builds_df["Local_Build_Status"], builds_df["package_count"]))
    for status, col_idx in _BUILD_STATUS_COLS.items():
        canvas_total = sum(row[col_idx] for row in data["buildByType"])
        assert int(builds_by_status.get(status, 0)) == canvas_total


def test_identity_ops_census_is_bsl_driven(write_parquet):
    """Census pane equals an independent build_identity_ops_model query (no canvas anchor)."""
    records = _hand_built_fixture()
    parquet_path = write_parquet(_records_to_ranked_export_df(records), "identity_complete_export")

    got = dash_data.load_identity_ops_census(parquet_path)
    table = models.duckdb_table_from_parquet(parquet_path)
    expected = bsl_query(
        models.build_identity_ops_model(table),
        dimensions=_CENSUS_DIMENSIONS,
        measures=["package_count"],
    )
    pd.testing.assert_frame_equal(
        got.sort_values(_CENSUS_DIMENSIONS).reset_index(drop=True),
        expected.sort_values(_CENSUS_DIMENSIONS).reset_index(drop=True),
    )


@pytest.mark.parametrize(
    ("loader", "columns"),
    [
        (dash_data.load_identity_ops_priority, ["P", "Work", "package_count"]),
        (dash_data.load_identity_ops_issues, ["P", "has_open_issue", "package_count"]),
        (dash_data.load_identity_ops_builds, ["Local_Build_Status", "package_count"]),
        (dash_data.load_identity_ops_census, [*_CENSUS_DIMENSIONS, "package_count"]),
    ],
)
def test_identity_ops_loaders_empty_when_parquet_absent(loader, columns):
    got = loader("/nope.parquet")
    assert got.empty
    assert list(got.columns) == columns


def test_identity_ops_page_has_four_panes(dashboard):
    page = next(p for p in dashboard.pages if p.id == "identity-ops")
    grids = [c for c in page.components if isinstance(c, vm.AgGrid)]
    assert len(grids) == 4
    assert {g.id for g in grids} == {
        "identity-ops--priority-grid",
        "identity-ops--issues-grid",
        "identity-ops--builds-grid",
        "identity-ops--census-grid",
    }
