"""Story 22.1 / 23.9: priority.py shim reads inventory_priority_assignments and
writes identity_ranked_export.parquet for Vizro Epic 22."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _load_priority():
    script_path = SCRIPTS_DIR / "conda-forge-packaging-inventory-operations_priority.py"
    module_name = script_path.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


priority = _load_priority()


def _assignment_row(name: str, **extra) -> dict:
    row = {
        "core_python_package_name": name,
        "P": "P4",
        "Rank": 1,
        "Score": 88,
        "Work": "Already tracked",
        "Priority_Bucket_Description": "Used in one or more platform environments (platform_env_count > 0).",
        "Priority_Source": "platform",
        "Priority_Reason": "platform_env_count > 0",
        "Proposed_Priority": "P4",
        "Packaging_Work": "Already tracked",
        "Priority_Rank": 1,
        "Priority_Score": 88,
        "risk_level": "LOW",
        "vuln_status": "clean",
        "jfrog_latest_vuln_count": 0,
    }
    row.update(extra)
    return row


def _jfrog_row(name: str, **extra) -> dict:
    row = {
        "core_python_package_name": name,
        "platform_env_count": 2,
        "internal_app_count": 0,
        "internal_component_count": 1,
        "internal_lob_count": 0,
        "artifactory_downloads": 50,
        "artifactory_version_count": 5,
    }
    row.update(extra)
    return row


def _write_priority_assignments(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path)


def _write_jfrog_parquet(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path)


def test_normal_run_writes_ranked_parquet_and_optional_csv(monkeypatch, tmp_path, capsys):
    assignments_path = tmp_path / "inventory_priority_assignments.parquet"
    _write_priority_assignments(
        assignments_path,
        [_assignment_row("pkg-a", Work="Already tracked", P="P4")],
    )
    jfrog_path = tmp_path / "enterprise_jfrog_consumption.parquet"
    _write_jfrog_parquet(jfrog_path, [_jfrog_row("pkg-a")])
    ranked_export = tmp_path / "identity_ranked_export.parquet"
    ranked_csv = tmp_path / "identity_ranked.csv"
    canvas_path = tmp_path / "canvas.tsx"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--priority-assignments",
            str(assignments_path),
            "--jfrog-parquet",
            str(jfrog_path),
            "--ranked-export",
            str(ranked_export),
            "--ranked-csv",
            str(ranked_csv),
            "--canvas",
            str(canvas_path),
        ],
    )

    rc = priority.main()

    assert rc == 0
    assert ranked_export.is_file()
    ranked_df = pd.read_parquet(ranked_export)
    assert list(ranked_df.columns) == priority.RANKED_EXPORT_COLUMNS
    assert ranked_df.iloc[0]["Core_Python_Package_Name"] == "pkg-a"
    assert ranked_df.iloc[0]["P"] == "P4"
    assert ranked_df.iloc[0]["Work"] == "Already tracked"
    assert ranked_df.iloc[0]["Platforms"] == 2
    assert ranked_df.iloc[0]["Verification_Timestamp_UTC"]

    csv_df = pd.read_csv(ranked_csv)
    assert list(csv_df.columns) == priority.LEGACY_RANKED_CSV_COLUMNS
    assert csv_df.iloc[0]["Package"] == "pkg-a"
    assert csv_df.iloc[0]["P"] == "P4"
    assert "wrote" in capsys.readouterr().out


def test_missing_priority_assignments_exits_nonzero(monkeypatch, tmp_path, capsys):
    missing = tmp_path / "missing.parquet"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--priority-assignments",
            str(missing),
            "--ranked-export",
            str(tmp_path / "out.parquet"),
        ],
    )

    with pytest.raises(SystemExit) as exc:
        priority.main()

    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert str(missing) in err
    assert "pyforge-atlas-bootstrap" in err


def test_jfrog_only_package_not_in_assignments(monkeypatch, tmp_path):
    assignments_path = tmp_path / "inventory_priority_assignments.parquet"
    _write_priority_assignments(
        assignments_path,
        [_assignment_row("pkg-ranked", P="P5", Work="Create recipe")],
    )
    jfrog_path = tmp_path / "enterprise_jfrog_consumption.parquet"
    _write_jfrog_parquet(
        jfrog_path,
        [
            _jfrog_row("orphan-jfrog", platform_env_count=1),
            _jfrog_row("pkg-ranked", internal_app_count=3, platform_env_count=0),
        ],
    )
    ranked_export = tmp_path / "identity_ranked_export.parquet"
    canvas_path = tmp_path / "canvas.tsx"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--priority-assignments",
            str(assignments_path),
            "--jfrog-parquet",
            str(jfrog_path),
            "--ranked-export",
            str(ranked_export),
            "--canvas",
            str(canvas_path),
        ],
    )

    rc = priority.main()

    assert rc == 0
    ranked_df = pd.read_parquet(ranked_export)
    assert list(ranked_df["Core_Python_Package_Name"]) == ["pkg-ranked"]


def test_retired_workbook_flags_exit_two(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--xlsx",
            str(tmp_path / "Analysis_Dataset.xlsx"),
            "--ranked-export",
            str(tmp_path / "out.parquet"),
        ],
    )

    rc = priority.main()

    assert rc == 2
    assert "retired by Story 23.9" in capsys.readouterr().err
