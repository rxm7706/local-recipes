#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest"]
# ///
"""Story 23.9 — assert zero workbook surface across ``scripts/`` quartet actuators."""

from __future__ import annotations

import re
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_PATTERN = re.compile(r"openpyxl|load_workbook|XlsxReader|analysis-xlsx")
_EXCLUDE_PARTS = frozenset({"tests", "fixtures"})


def _iter_script_sources() -> list[Path]:
    return sorted(
        path
        for path in SCRIPTS_DIR.rglob("*.py")
        if path.is_file()
        and not any(part in _EXCLUDE_PARTS for part in path.parts)
    )


def test_scripts_tree_has_zero_xlsx_surface():
    hits: list[str] = []
    for path in _iter_script_sources():
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            if _PATTERN.search(line):
                hits.append(f"{path}:{line_no}:{line}")
    assert hits == []
