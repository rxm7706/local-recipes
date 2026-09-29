"""FR-7 / Story 30.2 — Guildhall generator must stay gone."""

from __future__ import annotations

from pathlib import Path

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import board


def test_retired_console_ok_on_empty_tree(tmp_path: Path) -> None:
    findings = board.gather_dashboard_drift(tmp_path)
    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].source is Source.DASHBOARD_DRIFT


def test_reintroduced_generate_py_fails(tmp_path: Path) -> None:
    path = tmp_path / "docs" / "dashboard" / "generate.py"
    path.parent.mkdir(parents=True)
    path.write_text("# resurrected\n", encoding="utf-8")
    findings = board.gather_dashboard_drift(tmp_path)
    assert any(f.status is DoctorStatus.FAIL and "generate.py" in f.message for f in findings)


def test_reintroduced_data_js_fails(tmp_path: Path) -> None:
    path = tmp_path / "docs" / "dashboard" / "data.js"
    path.parent.mkdir(parents=True)
    path.write_text("window.DASHBOARD_DATA = {};\n", encoding="utf-8")
    findings = board.gather_dashboard_drift(tmp_path)
    assert any(f.status is DoctorStatus.FAIL and "data.js" in f.message for f in findings)


def test_reintroduced_pixi_task_fails(tmp_path: Path) -> None:
    (tmp_path / "pixi.toml").write_text(
        '[feature.local-recipes.tasks.dashboard-gen]\ncmd = "true"\n',
        encoding="utf-8",
    )
    findings = board.gather_dashboard_drift(tmp_path)
    assert any(f.status is DoctorStatus.FAIL and "dashboard-gen" in f.message for f in findings)
