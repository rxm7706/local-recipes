#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "pyarrow", "pytest"]
# ///
"""Tests for conda-forge-packaging-inventory-operations_metrics.py's Story 23.9
thin-actuator contract over Atlas 23.4 Parquet exports.

Run directly with ``python3 -m pytest scripts/tests/`` — no pixi task.
"""

from __future__ import annotations

import csv
import importlib.util
import re
import sys
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent
    / "conda-forge-packaging-inventory-operations_metrics.py"
)

_FIXED_TS = "2026-08-30T12:00:00Z"


def _load_module():
    spec = importlib.util.spec_from_file_location("cfpio_metrics", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


metrics = _load_module()


def _sample_verified_row(
    pkg: str,
    *,
    pypi: str = "Yes",
    cf: str = "No",
    status: str = "High Priority Candidate",
    source: str = "tab:Conda-Forge",
    role: str = "N/A",
    priority: str = "P9",
) -> dict[str, str]:
    return {
        "Repository_Source": source,
        "Role": role,
        "Package_Input_Name": pkg,
        "Core_Python_Package_Name": pkg,
        "PyPI_Verified": pypi,
        "CondaForge_Verified": cf,
        "Priority_Bucket": priority,
        "Packaging_Candidate_Status": status,
        "PyPI_PURL": f"pkg:pypi/{pkg}" if pypi == "Yes" else "N/A",
        "PyPI_Package_URL": f"https://pypi.org/project/{pkg}/" if pypi == "Yes" else "N/A",
        "Conda-forge_PURL": f"pkg:conda/{pkg}?channel=conda-forge" if cf == "Yes" else "N/A",
        "Conda-Forge_Package_URL": f"https://anaconda.org/conda-forge/{pkg}/" if cf == "Yes" else "N/A",
        "Conda-Forge_FeedStock_URL": (
            f"https://github.com/conda-forge/{pkg}-feedstock" if cf == "Yes" else "N/A"
        ),
        "Verification_Timestamp_UTC": _FIXED_TS,
    }


def _sample_queue_row(pkg: str) -> dict[str, str]:
    return {
        "Package_Name": pkg,
        "Reason": "On PyPI, not on conda-forge, not in CDO consumption (GAOSS-Free)",
        "Verification_Timestamp_UTC": _FIXED_TS,
    }


def _write_verified_parquet(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=metrics.CSV_COLS).to_parquet(path, index=False)


def _write_queue_parquet(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=metrics._QUEUE_COLS).to_parquet(path, index=False)


def _make_catalog_root(
    root: Path,
    *,
    verified_rows: list[dict[str, str]] | None = None,
    queue_rows: list[dict[str, str]] | None = None,
    skip: frozenset[str] = frozenset(),
) -> None:
    if "inventory_verified_packages" not in skip:
        _write_verified_parquet(
            root / metrics._VERIFIED_PACKAGES_REL,
            verified_rows
            if verified_rows is not None
            else [_sample_verified_row("examplepkg")],
        )
    if "inventory_aoss_free_queue" not in skip:
        _write_queue_parquet(
            root / metrics._AOSS_QUEUE_REL,
            queue_rows if queue_rows is not None else [_sample_queue_row("queuepkg")],
        )


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Story 23.9 — zero xlsx surface on the metrics script
# ---------------------------------------------------------------------------


def test_metrics_script_has_zero_xlsx_surface():
    pattern = re.compile(r"openpyxl|load_workbook|XlsxReader|analysis-xlsx")
    hits: list[str] = []
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    for line_no, line in enumerate(text.splitlines(), 1):
        if pattern.search(line):
            hits.append(f"{SCRIPT_PATH}:{line_no}:{line}")
    assert hits == []


# ---------------------------------------------------------------------------
# load_atlas_exports() unit tests
# ---------------------------------------------------------------------------


def test_load_atlas_exports_reads_both_parquet_files(tmp_path: Path):
    root = tmp_path / "root"
    verified = [_sample_verified_row("alpha"), _sample_verified_row("beta")]
    queue = [_sample_queue_row("queue-one")]
    _make_catalog_root(root, verified_rows=verified, queue_rows=queue)
    result = metrics.load_atlas_exports(root)
    assert result.failed is False
    assert len(result.verified_rows) == 2
    assert len(result.queue_rows) == 1
    assert result.verified_rows[0]["Core_Python_Package_Name"] == "alpha"


def test_load_atlas_exports_missing_verified_fails(tmp_path: Path):
    root = tmp_path / "root"
    _make_catalog_root(root, skip=frozenset({"inventory_verified_packages"}))
    result = metrics.load_atlas_exports(root)
    assert result.failed is True
    assert any("inventory_verified_packages" in w for w in result.warnings)


def test_load_atlas_exports_missing_queue_fails(tmp_path: Path):
    root = tmp_path / "root"
    _make_catalog_root(root, skip=frozenset({"inventory_aoss_free_queue"}))
    result = metrics.load_atlas_exports(root)
    assert result.failed is True
    assert any("inventory_aoss_free_queue" in w for w in result.warnings)


def test_load_atlas_exports_unreadable_parquet_fails(tmp_path: Path):
    root = tmp_path / "root"
    _make_catalog_root(root)
    corrupt = root / metrics._VERIFIED_PACKAGES_REL
    corrupt.write_bytes(b"not a parquet file")
    result = metrics.load_atlas_exports(root)
    assert result.failed is True
    assert any("unreadable" in w for w in result.warnings)


def test_load_atlas_exports_missing_required_column_fails(tmp_path: Path):
    root = tmp_path / "root"
    path = root / metrics._VERIFIED_PACKAGES_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"Core_Python_Package_Name": ["only-col"]}).to_parquet(path, index=False)
    _write_queue_parquet(root / metrics._AOSS_QUEUE_REL, [_sample_queue_row("q")])
    result = metrics.load_atlas_exports(root)
    assert result.failed is True
    assert any("missing columns" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# main() wiring — Story 23.9 CLI contract
# ---------------------------------------------------------------------------


def test_analysis_xlsx_exits_2_with_pointer(tmp_path: Path, capsys):
    catalog_root = tmp_path / "catalog"
    _make_catalog_root(catalog_root)
    legacy_flag = "--analysis-" "xlsx"
    argv = [
        "metrics",
        "--live-catalog",
        str(catalog_root),
        legacy_flag,
        str(tmp_path / "book.xlsx"),
        "--output-csv",
        str(tmp_path / "out.csv"),
        "--output-md",
        str(tmp_path / "out.md"),
        "--skip-revised-prompt",
    ]
    with mock.patch.object(sys, "argv", argv):
        rc = metrics.main()
    assert rc == 2
    assert not (tmp_path / "out.csv").exists()
    err = capsys.readouterr().err
    assert "Story 23.9" in err
    assert "inventory_verified_packages" in err


def test_missing_live_catalog_exports_exits_2_before_output(tmp_path: Path):
    argv = [
        "metrics",
        "--live-catalog",
        str(tmp_path / "empty-root"),
        "--output-csv",
        str(tmp_path / "out.csv"),
        "--output-md",
        str(tmp_path / "out.md"),
        "--skip-revised-prompt",
    ]
    with mock.patch.object(sys, "argv", argv):
        rc = metrics.main()
    assert rc == 2
    assert not (tmp_path / "out.csv").exists()
    assert not (tmp_path / "out.md").exists()


def test_live_catalog_formats_csv_md_and_queue_from_exports(tmp_path: Path, capsys):
    catalog_root = tmp_path / "catalog"
    verified = [
        _sample_verified_row("widget", status="Already Packaged", cf="Yes"),
        _sample_verified_row("candidate", status="High Priority Candidate"),
    ]
    queue = [_sample_queue_row("extra-aoss")]
    _make_catalog_root(catalog_root, verified_rows=verified, queue_rows=queue)

    argv = [
        "metrics",
        "--live-catalog",
        str(catalog_root),
        "--output-csv",
        str(tmp_path / "out.csv"),
        "--output-md",
        str(tmp_path / "out.md"),
        "--skip-revised-prompt",
    ]
    with mock.patch.object(sys, "argv", argv):
        rc = metrics.main()
    assert rc == 0

    csv_rows = _read_csv_rows(tmp_path / "out.csv")
    assert len(csv_rows) == 2
    assert {row["Core_Python_Package_Name"] for row in csv_rows} == {"widget", "candidate"}

    md_text = (tmp_path / "out.md").read_text(encoding="utf-8")
    assert "Total final unique package count: **2**" in md_text
    assert "Already Packaged: **1**" in md_text
    assert "High Priority Candidate: **1**" in md_text

    queue_path = tmp_path / "aoss-free-queue-2026-08-30.csv"
    assert queue_path.exists()
    queue_rows = _read_csv_rows(queue_path)
    assert len(queue_rows) == 1
    assert queue_rows[0]["Package_Name"] == "extra-aoss"

    out = capsys.readouterr().out
    assert "Wrote CSV:" in out
    assert "Wrote AOSS-Free queue:" in out


def test_write_revised_prompt_echoes_live_catalog_only(tmp_path: Path):
    catalog_root = tmp_path / "catalog"
    _make_catalog_root(catalog_root)
    revised_prompt_path = tmp_path / "revised-prompt.md"
    argv = [
        "metrics",
        "--live-catalog",
        str(catalog_root),
        "--output-csv",
        str(tmp_path / "out.csv"),
        "--output-md",
        str(tmp_path / "out.md"),
        "--output-revised-prompt",
        str(revised_prompt_path),
    ]
    with mock.patch.object(sys, "argv", argv):
        rc = metrics.main()
    assert rc == 0
    text = revised_prompt_path.read_text(encoding="utf-8")
    assert f'--live-catalog "{catalog_root}"' in text
    assert "analysis-xlsx" not in text


if __name__ == "__main__":
    sys.exit(pytest.main([str(Path(__file__).resolve())]))
