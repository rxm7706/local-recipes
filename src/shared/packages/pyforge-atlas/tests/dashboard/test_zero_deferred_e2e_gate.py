"""Story 23.7 — zero-deferred E2E gate static checks (complete-export-contract §7).

Covers the mechanical verification items that do not require a full bootstrap run:
- Vizro loaders read identity_complete_export only (item 6 grep discipline)
- metrics.py --live-catalog and openteams_identity.py --gist-only are thin actuators (item 7)
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[7]
_DASHBOARD_SRC = _REPO_ROOT / "src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard"
_METRICS_SCRIPT = _REPO_ROOT / "scripts/conda-forge-packaging-inventory-operations_metrics.py"
_IDENTITY_SCRIPT = _REPO_ROOT / "scripts/conda-forge-packaging-inventory-operations_openteams_identity.py"
_README = _REPO_ROOT / "src/shared/packages/pyforge-atlas/README.md"


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
    """§7 item 7 — metrics.py --live-catalog path has no ranking/verification business logic."""
    source = _METRICS_SCRIPT.read_text(encoding="utf-8")
    forbidden_in_main_path = (
        "assign_lane",
        "PackageRecord",
        "packaging_status",
        "load_workbook",
        "openpyxl",
    )
    for name in forbidden_in_main_path:
        assert name not in source, f"residual business logic token in metrics.py: {name}"
    assert "load_atlas_exports" in source
    assert "--live-catalog" in source


def test_openteams_identity_gist_only_is_thin_actuator():
    """§7 item 7 — --gist-only delegates to pyforge.atlas.dashboard.identity_gist."""
    source = _IDENTITY_SCRIPT.read_text(encoding="utf-8")
    assert "if args.gist_only:" in source
    assert "publish_gist_from_export" in source
    assert "from pyforge.atlas.dashboard import identity_gist" in source
    assert "identity_gist.render_identity_gist_markdown" in source
    forbidden = ("load_workbook", "openpyxl")
    for name in forbidden:
        assert name not in source, f"residual workbook logic in identity script: {name}"


def test_readme_documents_epic_21_23_steady_state_flow():
    """§7 item 8 — README documents bootstrap → --live-catalog → --gist-only, no workbook."""
    text = _README.read_text(encoding="utf-8")
    assert "pyforge-atlas-bootstrap" in text
    assert "--live-catalog" in text
    assert "--gist-only" in text
    assert "OPENTEAMS_IDENTITY_GIST_ID" in text
    assert "zero Excel" in text or "no Excel" in text.lower() or "workbook" in text
