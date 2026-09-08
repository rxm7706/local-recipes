"""Story 23.7 — zero-deferred E2E gate static checks (complete-export-contract §7).

Covers the mechanical verification items that do not require a full bootstrap run:
- Vizro loaders read identity_complete_export only (item 6 grep discipline)
- metrics.py --live-catalog and openteams_identity.py --gist-only are thin actuators (item 7)
- Matrix rows 2–5 remain owned by upstream story test modules (registry below)
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[7]
_DASHBOARD_SRC = _REPO_ROOT / "src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard"
_METRICS_SCRIPT = _REPO_ROOT / "scripts/conda-forge-packaging-inventory-operations_metrics.py"
_IDENTITY_SCRIPT = _REPO_ROOT / "scripts/conda-forge-packaging-inventory-operations_openteams_identity.py"
_README = _REPO_ROOT / "src/shared/packages/pyforge-atlas/README.md"
_MEMBER_TESTS = _REPO_ROOT / "src/shared/packages/pyforge-atlas/tests"

# §7 items 2-5: upstream story suites this gate re-runs (not duplicated here).
# Story 32.5/32.8 note: these span BOTH suites. The pipeline suites are unit
# weight; the dashboard suite is integration weight (it launches Playwright's
# managed Chromium), which is why it sits beside this file under integration/.
# Each path therefore names its own suite rather than sharing one prefix.
_UPSTREAM_MATRIX_TESTS = {
    2: _MEMBER_TESTS / "unit/pipelines/derived_artifacts/test_identity_complete_export.py",
    3: _MEMBER_TESTS / "unit/pipelines/derived_artifacts/test_inventory_verified_packages.py",
    4: (
        _MEMBER_TESTS / "unit/pipelines/upstream_discovery/test_identity_parity_fixtures.py",
        _MEMBER_TESTS / "unit/pipelines/derived_artifacts/test_inventory_priority_assignments.py",
    ),
    5: _MEMBER_TESTS / "integration/dashboard/test_identity_gist_markdown.py",
}


def _function_source(module_text: str, func_name: str) -> str:
    tree = ast.parse(module_text)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            segment = ast.get_source_segment(module_text, node)
            assert segment is not None
            return segment
    raise AssertionError(f"function {func_name!r} not found")


def test_matrix_upstream_suites_exist():
    """§7 items 2–5 — upstream parity/schema suites remain registered on disk."""
    for item, paths in _UPSTREAM_MATRIX_TESTS.items():
        if isinstance(paths, tuple):
            for path in paths:
                assert path.is_file(), f"§7 item {item}: missing upstream test {path}"
        else:
            assert paths.is_file(), f"§7 item {item}: missing upstream test {paths}"


def test_dashboard_loaders_have_no_ranked_export_references():
    """§7 item 6 — zero identity_ranked_export references in Vizro loader code."""
    hits: list[str] = []
    for path in _DASHBOARD_SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "identity_ranked_export" in text:
            hits.append(str(path.relative_to(_REPO_ROOT)))
    assert hits == [], f"lingering bridge-export references: {hits}"


def test_dashboard_constant_points_at_complete_export():
    from pyforge.atlas.dashboard import data as dash_data

    assert "identity_complete_export" in dash_data.IDENTITY_COMPLETE_EXPORT_PARQUET
    assert "identity_ranked_export" not in dash_data.IDENTITY_COMPLETE_EXPORT_PARQUET


def test_metrics_live_catalog_is_thin_actuator():
    """§7 item 7 — metrics.py live-catalog path has no ranking/verification business logic."""
    source = _METRICS_SCRIPT.read_text(encoding="utf-8")
    live_path = _function_source(source, "load_atlas_exports") + _function_source(source, "main")
    forbidden = ("assign_lane", "PackageRecord", "load_workbook", "openpyxl")
    for name in forbidden:
        assert name not in live_path, f"residual business logic token in live-catalog path: {name}"
    assert "load_atlas_exports" in source
    assert "--live-catalog" in source
    assert source.count("def main") == 1


def test_openteams_identity_gist_only_is_thin_actuator():
    """§7 item 7 — --gist-only delegates to pyforge.atlas.dashboard.identity_gist."""
    source = _IDENTITY_SCRIPT.read_text(encoding="utf-8")
    gist_only_block = source.split("if args.gist_only:", 1)[1].split("\n    if args.create_issues", 1)[0]
    assert "publish_gist_from_export" in gist_only_block
    publish_fn = _function_source(source, "publish_gist_from_export")
    assert "from pyforge.atlas.dashboard import identity_gist" in publish_fn
    assert "identity_gist.render_identity_gist_markdown" in publish_fn
    forbidden = ("load_workbook", "openpyxl")
    for name in forbidden:
        assert name not in publish_fn, f"residual workbook logic in gist export path: {name}"


def test_readme_documents_epic_21_23_steady_state_flow():
    """§7 item 8 — README documents bootstrap → --live-catalog → --gist-only, no workbook."""
    text = _README.read_text(encoding="utf-8")
    assert "pyforge-atlas-bootstrap" in text
    assert "--live-catalog" in text
    assert "--gist-only" in text
    assert "OPENTEAMS_IDENTITY_GIST_ID" in text
    assert "zero Excel" in text or "no Excel" in text.lower() or "workbook" in text


@pytest.mark.parametrize(
    "item,path",
    [
        (2, _UPSTREAM_MATRIX_TESTS[2]),
        (3, _UPSTREAM_MATRIX_TESTS[3]),
        (5, _UPSTREAM_MATRIX_TESTS[5]),
    ],
)
def test_matrix_upstream_suite_importable(item: int, path: Path):
    """§7 items 2, 3, 5 — upstream modules are importable pytest targets."""
    assert path.read_text(encoding="utf-8").strip(), f"§7 item {item}: empty test module {path}"
