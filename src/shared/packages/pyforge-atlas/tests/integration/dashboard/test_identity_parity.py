"""Story 22.5 — Canvas vs Vizro identity parity gate (catalog / ops / workbook)."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from collections import Counter
from pathlib import Path

import pandas as pd
import vizro.models as vm

from pyforge.atlas.dashboard import app
from pyforge.atlas.dashboard import data as dash_data

# Shared GIST-schema fixture corpus — single source for canvas writers and Vizro loaders.
SHARED_GIST_CORPUS: tuple[dict[str, str | int], ...] = (
    {
        "P": "P1",
        "Rank": 1,
        "Score": 95,
        "Work": "Already tracked",
        "Core_Python_Package_Name": "alpha-pkg",
        "OpenTeams_Issue_URL": "https://github.com/x/y/issues/1",
        "Local_Build_Status": "success",
        "Conda-Forge_FeedStock_URL": "https://github.com/conda-forge/alpha-feedstock",
        "Staged_Recipes_PR_URL": "",
        "Local_Recipes_URL": "https://github.com/rxm7706/local-recipes/tree/main/recipes/alpha",
    },
    {
        "P": "P1",
        "Rank": 2,
        "Score": 80,
        "Work": "Create recipe",
        "Core_Python_Package_Name": "beta-pkg",
        "OpenTeams_Issue_URL": "",
        "Local_Build_Status": "",
        "Conda-Forge_FeedStock_URL": "",
        "Staged_Recipes_PR_URL": "",
        "Local_Recipes_URL": "",
    },
    {
        "P": "P2",
        "Rank": 3,
        "Score": 70,
        "Work": "File OpenTeams tracking issue [Conda-Forge Packaging]",
        "Core_Python_Package_Name": "gamma-pkg",
        "OpenTeams_Issue_URL": "https://github.com/x/y/issues/2",
        "Local_Build_Status": "failed",
        "Conda-Forge_FeedStock_URL": "",
        "Staged_Recipes_PR_URL": "https://github.com/conda-forge/staged-recipes/pull/1",
        "Local_Recipes_URL": "",
    },
    {
        "P": "P2",
        "Rank": 4,
        "Score": 65,
        "Work": "Needs PR",
        "Core_Python_Package_Name": "delta-pkg",
        "OpenTeams_Issue_URL": "https://github.com/x/y/issues/3",
        "Local_Build_Status": "build-clean-test-blocked",
        "Conda-Forge_FeedStock_URL": "https://github.com/conda-forge/delta-feedstock",
        "Staged_Recipes_PR_URL": "",
        "Local_Recipes_URL": "",
    },
    {
        "P": "P3",
        "Rank": 5,
        "Score": 50,
        "Work": "Needs PR",
        "Core_Python_Package_Name": "epsilon-pkg",
        "OpenTeams_Issue_URL": "",
        "Local_Build_Status": "not-attempted",
        "Conda-Forge_FeedStock_URL": "",
        "Staged_Recipes_PR_URL": "",
        "Local_Recipes_URL": "",
    },
)

_RANKED_EXPORT_COLUMNS = [
    "P",
    "Rank",
    "Score",
    "Package",
    "Work",
    "Core_Python_Package_Name",
    "Platforms",
    "Apps",
    "Downloads",
    "Versions",
    "Vuln",
    "Local_Build_Status",
    "OpenTeams_Issue_URL",
    "Conda-Forge_FeedStock_URL",
    "Staged_Recipes_PR_URL",
    "Local_Recipes_URL",
]


def _resolve_repo_root() -> Path:
    """Anchor-based repo-root walk-up (mirrors dashboard/data.py::default_data_root)."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists() or (parent / "_bmad-output").is_dir():
            return parent
    raise RuntimeError("repo root not found from test_identity_parity.py")


def _scripts_dir() -> Path:
    return _resolve_repo_root() / "scripts"


def _load_module(filename: str):
    script_path = _scripts_dir() / filename
    assert script_path.is_file(), f"script not found: {script_path}"
    module_name = script_path.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    scripts = str(_scripts_dir())
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _decode_data_blob(text: str, prefix: str) -> dict:
    assert text.startswith(prefix)
    remainder = text[len(prefix) :]
    data, _end = json.JSONDecoder().raw_decode(remainder)
    return data


def _gist_to_write_canvas_records(
    gist_rows: list[dict[str, str | int]],
) -> tuple[list[dict], dict[str, int]]:
    records: list[dict] = []
    for row in gist_rows:
        records.append(
            {
                "name": row["Core_Python_Package_Name"],
                "bucket": row["P"],
                "work": row["Work"],
                "rank": row["Rank"],
                "score100": row["Score"],
                "plat": 3,
                "apps": 1,
                "ic": 0,
                "lob": 0,
                "dl": 100,
                "ver": 5,
                "vuln": 0,
                "src": "manual",
                "why": "fixture",
                "priority_desc": "Critical",
                "risk": "",
                "latest": 0,
            }
        )
    counts = dict(Counter(r["bucket"] for r in records))
    return records, counts


def _gist_to_ranked_export_df(gist_rows: list[dict[str, str | int]]) -> pd.DataFrame:
    if not gist_rows:
        return pd.DataFrame(columns=_RANKED_EXPORT_COLUMNS)
    return pd.DataFrame(
        {
            "P": [r["P"] for r in gist_rows],
            "Rank": [r["Rank"] for r in gist_rows],
            "Score": [r["Score"] for r in gist_rows],
            "Package": [r["Core_Python_Package_Name"] for r in gist_rows],
            "Work": [r["Work"] for r in gist_rows],
            "Core_Python_Package_Name": [r["Core_Python_Package_Name"] for r in gist_rows],
            "Platforms": [3] * len(gist_rows),
            "Apps": [1] * len(gist_rows),
            "Downloads": [100] * len(gist_rows),
            "Versions": [5] * len(gist_rows),
            "Vuln": [0] * len(gist_rows),
            "Local_Build_Status": [r["Local_Build_Status"] for r in gist_rows],
            "OpenTeams_Issue_URL": [r["OpenTeams_Issue_URL"] for r in gist_rows],
            "Conda-Forge_FeedStock_URL": [r["Conda-Forge_FeedStock_URL"] for r in gist_rows],
            "Staged_Recipes_PR_URL": [r["Staged_Recipes_PR_URL"] for r in gist_rows],
            "Local_Recipes_URL": [r["Local_Recipes_URL"] for r in gist_rows],
        }
    )


def _canvas_catalog_triples(data: dict) -> set[tuple[str, str, str]]:
    return {(row[1], row[13], row[0]) for row in data["rows"]}


def _vizro_catalog_triples(loader_df: pd.DataFrame) -> set[tuple[str, str, str]]:
    return set(
        zip(
            loader_df["P"],
            loader_df["Work"],
            loader_df["Core_Python_Package_Name"],
            strict=True,
        )
    )


def _vizro_ops_aggregates(parquet_path: str) -> tuple[dict, dict, int, int]:
    priority_df = dash_data.load_identity_ops_priority(parquet_path)
    priority_counts = {str(p): int(count) for p, count in priority_df.groupby("P")["package_count"].sum().items()}
    work_counts = {str(w): int(count) for w, count in priority_df.groupby("Work")["package_count"].sum().items()}
    issues_df = dash_data.load_identity_ops_issues(parquet_path)
    have = int(
        issues_df.loc[issues_df["has_open_issue"] == True, "package_count"].sum()  # noqa: E712
    )
    miss = int(
        issues_df.loc[issues_df["has_open_issue"] == False, "package_count"].sum()  # noqa: E712
    )
    return priority_counts, work_counts, have, miss


def _ops_helpers(monkeypatch):
    identity = _load_module("conda-forge-packaging-inventory-operations_openteams_identity.py")
    monkeypatch.setattr(identity, "overlay_live_local", lambda _records, _dir: None)
    monkeypatch.setattr(identity, "load_local_recipe_type", lambda _dir: {})
    return types.SimpleNamespace(**vars(identity))


def test_identity_catalog_matches_write_canvas_on_shared_fixture(tmp_path, write_parquet):
    gist_rows = list(SHARED_GIST_CORPUS)
    priority = _load_module("conda-forge-packaging-inventory-operations_priority.py")
    mapped_records, counts = _gist_to_write_canvas_records(gist_rows)

    canvas_path = tmp_path / "catalog.canvas.tsx"
    priority.write_canvas(canvas_path, mapped_records, counts, "identity-fixture")
    canvas_data = _decode_data_blob(canvas_path.read_text(encoding="utf-8"), priority._CANVAS_PREFIX)

    parquet_path = write_parquet(_gist_to_ranked_export_df(gist_rows), "identity_complete_export")
    loader_df = dash_data.load_identity_catalog(parquet_path)

    assert sorted(_canvas_catalog_triples(canvas_data)) == sorted(_vizro_catalog_triples(loader_df))


def test_identity_ops_pane_totals_match_write_ops_canvas_on_shared_fixture(tmp_path, write_parquet, monkeypatch):
    gist_rows = list(SHARED_GIST_CORPUS)
    dashboards = _load_module("openteams_identity_dashboards.py")
    helpers = _ops_helpers(monkeypatch)

    canvas_path = tmp_path / "identity-ops.canvas.tsx"
    dashboards.write_ops_canvas(canvas_path, gist_rows, "identity-fixture", helpers)
    canvas_data = _decode_data_blob(canvas_path.read_text(encoding="utf-8"), dashboards._CANVAS_PREFIX)

    parquet_path = write_parquet(_gist_to_ranked_export_df(gist_rows), "identity_complete_export")
    priority_counts, work_counts, have, miss = _vizro_ops_aggregates(parquet_path)

    assert canvas_data["priorityCounts"] == priority_counts
    assert canvas_data["workCounts"] == work_counts
    assert canvas_data["issues"]["have"] == have
    assert canvas_data["issues"]["miss"] == miss


def test_identity_workbook_both_sides_degrade_honestly_on_same_fixture(tmp_path, write_parquet, monkeypatch):
    gist_rows = list(SHARED_GIST_CORPUS)
    dashboards = _load_module("openteams_identity_dashboards.py")
    priority = _load_module("conda-forge-packaging-inventory-operations_priority.py")
    helpers = _ops_helpers(monkeypatch)

    missing_export = tmp_path / "missing" / "identity_complete_export.parquet"
    canvas_path = tmp_path / "identity-workbook.canvas.tsx"
    dashboards.write_workbook_canvas(canvas_path, gist_rows, missing_export, "identity-fixture", helpers)
    canvas_text = canvas_path.read_text(encoding="utf-8")
    assert canvas_text.startswith(priority._CANVAS_PREFIX)
    canvas_data = _decode_data_blob(canvas_text, dashboards._CANVAS_PREFIX)
    assert isinstance(canvas_data["jfrogMap"], dict)
    assert isinstance(canvas_data["externalCounts"], list)

    complete_path = write_parquet(_gist_to_ranked_export_df(gist_rows), "identity_complete_export")
    enterprise_path = tmp_path / "missing-enterprise.parquet"
    loader_df = dash_data.load_identity_workbook(complete_path, enterprise_path)
    assert loader_df.empty

    gap_msg = dash_data.identity_workbook_gap_message(complete_path, enterprise_path)
    assert dash_data.ENTERPRISE_JFROG_CONSUMPTION_PARQUET in gap_msg

    assert any(page.id == "identity-workbook" for page in app.PAGE_INVENTORY)
    data_root = tmp_path / "data"
    complete_canonical = data_root / dash_data.IDENTITY_COMPLETE_EXPORT_PARQUET
    complete_canonical.parent.mkdir(parents=True, exist_ok=True)
    _gist_to_ranked_export_df(gist_rows).to_parquet(complete_canonical)
    dashboard = app.build_dashboard(
        data_root=str(data_root),
        build_stamp="2026-08-30T00:00:00Z",
        now=1_700_000_000,
    )
    page = next(p for p in dashboard.pages if p.id == "identity-workbook")
    about = next(c for c in page.components if c.id == "identity-workbook--about")
    assert dash_data.ENTERPRISE_JFROG_CONSUMPTION_PARQUET in about.text
    assert isinstance(next(c for c in page.components if c.id == "identity-workbook--grid"), vm.AgGrid)


def test_empty_corpus_degrades_honestly_on_both_sides(tmp_path, write_parquet, monkeypatch):
    gist_rows: list[dict[str, str | int]] = []
    priority = _load_module("conda-forge-packaging-inventory-operations_priority.py")
    dashboards = _load_module("openteams_identity_dashboards.py")
    helpers = _ops_helpers(monkeypatch)

    mapped_records, counts = _gist_to_write_canvas_records(gist_rows)
    catalog_path = tmp_path / "catalog-empty.canvas.tsx"
    priority.write_canvas(catalog_path, mapped_records, counts, "identity-fixture")
    catalog_data = _decode_data_blob(catalog_path.read_text(encoding="utf-8"), priority._CANVAS_PREFIX)
    assert catalog_data["rows"] == []

    ops_path = tmp_path / "ops-empty.canvas.tsx"
    dashboards.write_ops_canvas(ops_path, gist_rows, "identity-fixture", helpers)
    ops_data = _decode_data_blob(ops_path.read_text(encoding="utf-8"), dashboards._CANVAS_PREFIX)
    assert ops_data["n"] == 0
    assert ops_data["rows"] == []

    missing_export = tmp_path / "missing-export.parquet"
    workbook_path = tmp_path / "workbook-empty.canvas.tsx"
    dashboards.write_workbook_canvas(workbook_path, gist_rows, missing_export, "identity-fixture", helpers)
    workbook_data = _decode_data_blob(workbook_path.read_text(encoding="utf-8"), dashboards._CANVAS_PREFIX)
    assert workbook_data["neitherRows"] == []

    empty_parquet = write_parquet(_gist_to_ranked_export_df(gist_rows), "identity_complete_export")
    assert dash_data.load_identity_catalog(empty_parquet).empty
    assert dash_data.load_identity_ops_priority(empty_parquet).empty
    assert dash_data.load_identity_ops_issues(empty_parquet).empty
    assert dash_data.load_identity_workbook(empty_parquet, "/nope.parquet").empty
