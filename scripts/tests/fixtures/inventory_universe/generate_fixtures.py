#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "pyarrow"]
# ///
"""Regenerates the Story 23.8 frozen fixture pair:

- ``mini-workbook.xlsx`` -- a small, real .xlsx (hand-built XML, no openpyxl
  dependency) with one sheet per workbook-universe source, plus a 10,000-row
  filler block in the Conda-Forge sheet (the ``inventory_universe`` floor).
- ``catalog/`` -- the equivalent Parquet tree under a fake
  ``PYFORGE_ATLAS_DATA_ROOT``, including a hand-built ``inventory_universe.parquet``
  carrying the SAME distinct names as the workbook (so
  ``test_parity_workbook_vs_live_catalog_universe`` in
  ``test_conda_forge_packaging_inventory_operations_metrics.py`` gets identical
  CSV/MD output from both universe sources).

Re-run this script by hand (under git review) if the fixture content needs to
change: ``python3 scripts/tests/fixtures/inventory_universe/generate_fixtures.py``.
Both outputs are tracked in git -- this script is the reproducible source, not
itself consumed by the test.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd

HERE = Path(__file__).resolve().parent
WORKBOOK_PATH = HERE / "mini-workbook.xlsx"
CATALOG_ROOT = HERE / "catalog"

FILLER_COUNT = 10_000

# ---------------------------------------------------------------------------
# Shared package-name glossary (kept in one place so the workbook and the
# Parquet catalog can't silently drift apart).
# ---------------------------------------------------------------------------
WIDGET = "widget"  # present in Conda-Forge + Basilisk + CDO-ENT-JFROG
SCIPYISH = "scipyish"  # Basilisk-only
ANACONDA_MAIN_PKG = "anacondamainpkg"
ANACONDA_DIST_PKG = "anacondadistpkg"
AOSS_FREE_PKG = "aossfreepkg"  # also PyPI-verified -> lands in the AOSS-Free queue
AOSS_PREMIUM_PKG = "aosspremiumpkg"
MAINTAINER_PKG = "pytestpkg"  # CDO-ENT-CONDA, role=Maintainer
CO_MAINTAINER_PKG = "comaintpkg"  # CDO-ENT-CONDA, role=Co-Maintainer
OPENTEAMS_RULE_A_PKG = "richlib"
OPENTEAMS_RULE_B_PKG = "anotherpkg"
CLOSED_ONLY_PKG = "closedonlypkg"  # 10kClosed-only, dropped by the tenk filter
OUTPUT_TAB_PKG = "outputtabpkg"  # lives only on a skipped OUTPUT_TABS sheet

OPENTEAMS_TITLE_A = f"some ticket | {OPENTEAMS_RULE_A_PKG}"
OPENTEAMS_TITLE_B = f"[Conda-Forge Packaging] {OPENTEAMS_RULE_B_PKG}"
OPENTEAMS_TITLE_C = "Some CVE | 2026-08-12"  # rule c: RHS is a date, not a package


def _filler_names() -> list[str]:
    return [f"p{i}" for i in range(FILLER_COUNT)]


# ---------------------------------------------------------------------------
# .xlsx writer (raw zip + minimal OOXML, inline strings -- no sharedStrings.xml,
# no openpyxl dependency; mirrors XlsxReader's own read path in the target
# script exactly).
# ---------------------------------------------------------------------------


def _col_letter(idx: int) -> str:
    idx += 1
    letters = ""
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def _cell_xml(col: str, row_idx: int, value: str) -> str:
    if value == "":
        return f'<c r="{col}{row_idx}"/>'
    return f'<c r="{col}{row_idx}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'


def _sheet_xml(grid: list[list[str]]) -> str:
    rows_xml = []
    for i, row in enumerate(grid, start=1):
        cells = "".join(_cell_xml(_col_letter(j), i, v) for j, v in enumerate(row))
        rows_xml.append(f"<row>{cells}</row>")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(rows_xml)}</sheetData></worksheet>'
    )


def write_workbook(path: Path, sheets: dict[str, list[dict[str, str]]]) -> None:
    """``sheets``: sheet name -> list of row-dicts (dict order = header order,
    every row must share the same keys)."""
    sheet_entries = []
    rel_entries = []
    files: dict[str, str] = {}
    for idx, (name, rows) in enumerate(sheets.items(), start=1):
        headers = list(rows[0].keys()) if rows else []
        grid = [headers] + [[str(r.get(h, "")) for h in headers] for r in rows]
        files[f"xl/worksheets/sheet{idx}.xml"] = _sheet_xml(grid)
        sheet_entries.append(f'<sheet name="{escape(name)}" sheetId="{idx}" r:id="rId{idx}"/>')
        rel_entries.append(
            f'<Relationship Id="rId{idx}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{idx}.xml"/>'
        )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets>{"".join(sheet_entries)}</sheets></workbook>'
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{"".join(rel_entries)}</Relationships>'
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        for fname, content in files.items():
            zf.writestr(fname, content)


def _rows(col: str, names: list[str]) -> list[dict[str, str]]:
    return [{col: n} for n in names]


def build_workbook() -> None:
    sheets: dict[str, list[dict[str, str]]] = {
        "Conda-Forge": _rows("Package_Name", _filler_names() + [WIDGET]),
        "Basilisk": _rows("Package_Name", [WIDGET, SCIPYISH]),
        "Anaconda-Main": _rows("Package_Name", [ANACONDA_MAIN_PKG]),
        "Anaaconda-Dist": _rows("Package_Name", [ANACONDA_DIST_PKG]),
        "GAOSS-Free": _rows("Package_Name", [AOSS_FREE_PKG]),
        "GAOSS-Premium": _rows("Package_Name", [AOSS_PREMIUM_PKG]),
        "CDO-ENT-JFROG": _rows("Package_Name", [WIDGET]),
        "CDO-ENT-CONDA": [
            {"Package_Name": MAINTAINER_PKG, "Role": "Maintainer"},
            {"Package_Name": CO_MAINTAINER_PKG, "Role": "Co-Maintainer"},
        ],
        "OpenTeams": _rows(
            "Title",
            [OPENTEAMS_TITLE_A, OPENTEAMS_TITLE_B, OPENTEAMS_TITLE_C],
        ),
        "10kOpen": _rows("Package_Name", [WIDGET]),  # clone of CDO-ENT-JFROG
        "10kClosed": _rows("Package_Name", [CLOSED_ONLY_PKG]),
        "verified-all-packages": _rows("Package_Name", [OUTPUT_TAB_PKG]),  # OUTPUT_TABS, skipped
    }
    write_workbook(WORKBOOK_PATH, sheets)


# ---------------------------------------------------------------------------
# Equivalent Parquet catalog tree.
# ---------------------------------------------------------------------------


def _write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


def build_catalog() -> None:
    # Small (sub-30k-floor) Tier 0 sets -- degrades identically under BOTH
    # --analysis-xlsx and --live-catalog-only-universe runs since both read
    # this exact file via load_live_catalog(); the degrade itself is not part
    # of what this fixture pair is proving.
    _write_parquet(
        CATALOG_ROOT / "intermediate/core_packages_enumerated/core_packages_enumerated.parquet",
        pd.DataFrame({"conda_name": [WIDGET]}),
    )
    _write_parquet(
        CATALOG_ROOT / "intermediate/pypi_universe/pypi_universe.parquet",
        pd.DataFrame({"pypi_name": [AOSS_FREE_PKG]}),
    )
    _write_parquet(
        CATALOG_ROOT / "primary/pypi_conda_mapping/pypi_conda_mapping.parquet",
        pd.DataFrame({"pypi_name": pd.Series([], dtype="object")}),
    )

    # The OpenTeams board -- same 3 titles as the workbook's OpenTeams sheet.
    _write_parquet(
        CATALOG_ROOT / "raw/openteams_project_1_board_raw/openteams_project_1_board.parquet",
        pd.DataFrame({"title": [OPENTEAMS_TITLE_A, OPENTEAMS_TITLE_B, OPENTEAMS_TITLE_C]}),
    )

    # inventory_universe -- one row per name, mirroring build_inventory_universe's
    # own output shape (Story 23.8). 10kOpen/10kClosed are NOT represented (no
    # catalog source, by design).
    columns = [
        "core_python_package_name",
        "package_input_names",
        "sources",
        "in_cdo_ent_jfrog",
        "in_cdo_ent_conda",
        "in_openteams",
        "in_conda_forge",
        "in_basilisk",
        "in_anaconda_main",
        "in_anaconda_dist",
        "in_aoss_free",
        "in_aoss_premium",
        "role",
        "openteams_universe_member",
    ]

    def _row(
        name: str,
        sources: list[str],
        flags: set[str],
        role: str = "N/A",
        input_names: list[str] | None = None,
    ) -> dict:
        in_jfrog = "in_cdo_ent_jfrog" in flags
        in_conda_ent = "in_cdo_ent_conda" in flags
        return {
            "core_python_package_name": name,
            "package_input_names": input_names if input_names is not None else [name],
            "sources": sorted(sources),
            "in_cdo_ent_jfrog": in_jfrog,
            "in_cdo_ent_conda": in_conda_ent,
            "in_openteams": "in_openteams" in flags,
            "in_conda_forge": "in_conda_forge" in flags,
            "in_basilisk": "in_basilisk" in flags,
            "in_anaconda_main": "in_anaconda_main" in flags,
            "in_anaconda_dist": "in_anaconda_dist" in flags,
            "in_aoss_free": "in_aoss_free" in flags,
            "in_aoss_premium": "in_aoss_premium" in flags,
            "role": role,
            "openteams_universe_member": in_jfrog or in_conda_ent,
        }

    rows = [
        _row(name, ["tab:Conda-Forge"], {"in_conda_forge"}) for name in _filler_names()
    ]
    rows.append(
        _row(
            WIDGET,
            ["tab:Conda-Forge", "tab:Basilisk", "tab:CDO-ENT-JFROG"],
            {"in_conda_forge", "in_basilisk", "in_cdo_ent_jfrog"},
        )
    )
    rows.append(_row(SCIPYISH, ["tab:Basilisk"], {"in_basilisk"}))
    rows.append(_row(ANACONDA_MAIN_PKG, ["tab:Anaconda-Main"], {"in_anaconda_main"}))
    rows.append(_row(ANACONDA_DIST_PKG, ["tab:Anaaconda-Dist"], {"in_anaconda_dist"}))
    rows.append(_row(AOSS_FREE_PKG, ["tab:GAOSS-Free"], {"in_aoss_free"}))
    rows.append(_row(AOSS_PREMIUM_PKG, ["tab:GAOSS-Premium"], {"in_aoss_premium"}))
    rows.append(
        _row(MAINTAINER_PKG, ["tab:CDO-ENT-CONDA"], {"in_cdo_ent_conda"}, role="Maintainer")
    )
    rows.append(
        _row(CO_MAINTAINER_PKG, ["tab:CDO-ENT-CONDA"], {"in_cdo_ent_conda"}, role="Co-Maintainer")
    )
    # OpenTeams-sourced rows: the raw input name is the FULL title text (mirrors
    # parse_sheet_sources' Package_Name/name/raw_names/Item/Title fallback chain
    # -- an OpenTeams row has none of the first four, so it falls through to the
    # whole Title string, not just the extracted package name).
    rows.append(
        _row(
            OPENTEAMS_RULE_A_PKG,
            ["tab:OpenTeams"],
            {"in_openteams"},
            input_names=[OPENTEAMS_TITLE_A],
        )
    )
    rows.append(
        _row(
            OPENTEAMS_RULE_B_PKG,
            ["tab:OpenTeams"],
            {"in_openteams"},
            input_names=[OPENTEAMS_TITLE_B],
        )
    )

    frame = pd.DataFrame(rows, columns=columns)
    _write_parquet(CATALOG_ROOT / "derived/inventory_universe/inventory_universe.parquet", frame)


def main() -> None:
    build_workbook()
    build_catalog()
    size = WORKBOOK_PATH.stat().st_size
    print(f"wrote {WORKBOOK_PATH} ({size:,} bytes)")
    print(f"wrote catalog tree under {CATALOG_ROOT}")


if __name__ == "__main__":
    main()
