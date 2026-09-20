"""Story 23.6 — BSL gist markdown parity vs legacy ``openteams_identity_dashboards.render``."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pandas as pd
import pytest

from pyforge.atlas.dashboard import identity_gist
from pyforge.atlas.pipelines.derived_artifacts.nodes import build_identity_complete_export

_REPO_ROOT = Path(__file__).resolve().parents[7]
_SCRIPT_DIR = _REPO_ROOT / "scripts"
_FIXTURE_JSON = (
    _REPO_ROOT / "src/shared/packages/pyforge-atlas/tests/fixtures/inventory_identity/complete_export_expected.json"
)
_FIXED_TS = "2026-08-30T12:00:00Z"
_PARAMS = {"identity_complete_export": {"verification_timestamp_utc": _FIXED_TS}}


def _load_corpus() -> dict:
    return json.loads(_FIXTURE_JSON.read_text(encoding="utf-8"))


def _build_export_df(corpus: dict) -> pd.DataFrame:
    return build_identity_complete_export(
        pd.DataFrame(corpus["identity_packages_primary"]),
        pd.DataFrame(corpus["inventory_priority_assignments"]),
        pd.DataFrame(corpus.get("enterprise_jfrog_consumption") or []),
        pd.DataFrame([]),
        pd.DataFrame(corpus.get("inventory_verified_packages") or []),
        pd.DataFrame([]),
        pd.DataFrame([]),
        pd.DataFrame(corpus.get("inventory_universe") or []),
        _PARAMS,
    )


def _ensure_openpyxl_stub() -> None:
    import types

    if getattr(sys.modules.get("openpyxl"), "_identity_gist_stub", False):
        return

    class _Worksheet:
        def iter_rows(self, values_only=True):
            return iter([])

    class _Workbook:
        sheetnames: list[str] = []

        def __getitem__(self, _name: str) -> _Worksheet:
            return _Worksheet()

        def close(self) -> None:
            return None

    stub = types.ModuleType("openpyxl")
    stub.load_workbook = lambda *_args, **_kwargs: _Workbook()
    stub._identity_gist_stub = True
    sys.modules["openpyxl"] = stub


def _legacy_render(records: list[dict[str, str]], export_path: Path) -> str:
    import importlib.util

    _ensure_openpyxl_stub()
    if str(_SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPT_DIR))
    dash_path = _SCRIPT_DIR / "openteams_identity_dashboards.py"
    spec = importlib.util.spec_from_file_location("openteams_identity_dashboards", dash_path)
    dash_mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(dash_mod)

    helpers = types.SimpleNamespace(
        overlay_live_local=identity_gist._overlay_live_local,
        load_local_recipe_type=identity_gist.load_local_recipe_type,
        row_recipe_type=identity_gist.row_recipe_type,
        pep503_name=identity_gist._pep503_name,
        packaging_name_from_title=lambda _title: None,
        read_xlsx_tab=lambda _xlsx, _tab: [],
        file_sha256=identity_gist._file_sha256,
        md_table=identity_gist.md_table,
        _as_int=identity_gist._as_int,
        P_ORDER=identity_gist.P_ORDER,
        RECIPE_TYPE_ORDER=identity_gist.RECIPE_TYPE_ORDER,
        GIST_FILENAME=identity_gist.GIST_FILENAME,
        REPO_ROOT=_REPO_ROOT,
        WORK_DASH_ORDER=identity_gist.WORK_DASH_ORDER,
    )
    return dash_mod.render(records, export_path, "offline-test", "identity-fixture", helpers=helpers)


def _extract_metric(text: str, label: str) -> int | None:
    for line in text.splitlines():
        if label in line and "**" in line:
            parts = line.split("**")
            for part in parts:
                cleaned = part.replace(",", "").strip()
                if cleaned.isdigit():
                    return int(cleaned)
    return None


@pytest.fixture()
def export_paths(tmp_path):
    corpus = _load_corpus()
    export_df = _build_export_df(corpus)
    export_dir = tmp_path / "derived/identity_complete_export"
    export_dir.mkdir(parents=True)
    export_path = export_dir / "identity_complete_export.parquet"
    export_df.to_parquet(export_path, index=False)

    jfrog_dir = tmp_path / "derived/enterprise_jfrog_consumption"
    jfrog_dir.mkdir(parents=True)
    jfrog_path = jfrog_dir / "enterprise_jfrog_consumption.parquet"
    jfrog_rows = corpus.get("enterprise_jfrog_consumption") or []
    if jfrog_rows:
        jfrog_df = pd.DataFrame(jfrog_rows)
        jfrog_df["repository_source"] = "CDO-ENT-JFROG"
        jfrog_df["core_python_package_name"] = jfrog_df.get("core_python_package_name", jfrog_df.get("name", ""))
        jfrog_df.to_parquet(jfrog_path, index=False)

    records = [
        {str(k): ("" if pd.isna(v) else str(v).strip()) for k, v in row.items()}
        for row in export_df.to_dict(orient="records")
    ]
    identity_gist._overlay_live_local(records, _REPO_ROOT / "recipes")
    return export_path, records


def test_workbook_tabs_section_absent(export_paths):
    export_path, _ = export_paths
    _, dashboards_md = identity_gist.render_identity_gist_markdown(
        export_path, gist_id="offline-test", repo_root=_REPO_ROOT
    )
    assert "## Workbook tabs" not in dashboards_md


def test_bsl_dashboard_counts_match_legacy_on_fixture(export_paths):
    export_path, records = export_paths
    _, dashboards_md = identity_gist.render_identity_gist_markdown(
        export_path, gist_id="offline-test", repo_root=_REPO_ROOT
    )
    legacy_md = _legacy_render(records, export_path)

    for label in (
        "have an OpenTeams",
        "Feedstock exists",
        "Needs staged-recipes",
        "CFE success",
    ):
        new_val = _extract_metric(dashboards_md, label.split()[0])
        old_val = _extract_metric(legacy_md, label.split()[0])
        if new_val is not None and old_val is not None:
            assert new_val == old_val, f"mismatch for {label}: {new_val} vs {old_val}"

    assert f"rows_identity: {len(records)}" in dashboards_md
    assert dashboards_md.count("P5") >= 1


def test_missing_export_raises():
    with pytest.raises(identity_gist.IdentityGistError, match="not found"):
        identity_gist.render_identity_gist_markdown(Path("/nonexistent/export.parquet"))


def test_empty_export_raises(tmp_path):
    path = tmp_path / "empty.parquet"
    pd.DataFrame(columns=["Core_Python_Package_Name"]).to_parquet(path, index=False)
    with pytest.raises(identity_gist.IdentityGistError, match="empty"):
        identity_gist.render_identity_gist_markdown(path)
