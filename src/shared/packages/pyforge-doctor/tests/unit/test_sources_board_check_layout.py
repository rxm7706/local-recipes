"""Story 30.2 — Guildhall layout gate follows the retired blob."""

from __future__ import annotations

from pathlib import Path

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import board


def test_layout_ok_when_console_blob_gone(tmp_path: Path) -> None:
    findings = board.gather_check_layout(tmp_path)
    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].source is Source.CHECK_LAYOUT


def test_layout_fails_if_data_js_returns(tmp_path: Path) -> None:
    path = tmp_path / "docs" / "dashboard" / "data.js"
    path.parent.mkdir(parents=True)
    path.write_text("window.DASHBOARD_DATA = {};\n", encoding="utf-8")
    findings = board.gather_check_layout(tmp_path)
    assert findings[0].status is DoctorStatus.FAIL
