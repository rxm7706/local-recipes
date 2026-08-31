#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "pyarrow", "pytest"]
# ///
"""Tests for conda-forge-packaging-inventory-operations_metrics.py's --live-catalog
contract (Story 21.3, Epic 21) and the workbook-free --analysis-xlsx-optional
contract (Story 23.8, Epic 23). Mirrors the
.claude/skills/bmad-review/scripts/tests/test_word_metrics.py convention: a bare
tests/ dir next to scripts/, run directly with `python3 -m pytest scripts/tests/` --
no pixi task (this story's spec, Boundaries -> Never).

The target script's filename has hyphens, so it is loaded via importlib rather
than a plain `import` statement. Every test is offline (see blocked_network
fixture) -- none of these tests may reach the real network.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent
    / "conda-forge-packaging-inventory-operations_metrics.py"
)
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "inventory_universe"
MINI_WORKBOOK_PATH = FIXTURES_DIR / "mini-workbook.xlsx"
MINI_CATALOG_ROOT = FIXTURES_DIR / "catalog"


def _load_module():
    spec = importlib.util.spec_from_file_location("cfpio_metrics", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Register in sys.modules BEFORE exec: dataclasses (module has several,
    # under `from __future__ import annotations`) resolve their field types
    # via sys.modules[cls.__module__] at class-definition time on Python 3.14.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


metrics = _load_module()


@pytest.fixture(autouse=True)
def blocked_network(monkeypatch):
    """Every test in this file must be offline. fetch_text/fetch_json raise
    immediately instead of attempting a real network call -- try_source's
    except-and-fallback then engages exactly as it would with no network
    reachable. Returns the two mocks so a test can also assert on call counts."""
    text_mock = mock.Mock(side_effect=RuntimeError("network disabled in tests"))
    json_mock = mock.Mock(side_effect=RuntimeError("network disabled in tests"))
    monkeypatch.setattr(metrics, "fetch_text", text_mock)
    monkeypatch.setattr(metrics, "fetch_json", json_mock)
    return {"fetch_text": text_mock, "fetch_json": json_mock}


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _write_minimal_xlsx(path: Path) -> None:
    """A workbook with zero sheets -- enough for XlsxReader to construct without
    error; parse_sheet_sources() then yields empty records/tab_packages."""
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets></sheets></workbook>"
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        "</Relationships>"
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", rels_xml)


def _write_curated_config(path: Path, groups: dict[str, list[str]]) -> None:
    data = {"groups": [{"name": name, "packages": pkgs} for name, pkgs in groups.items()]}
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_channeldata_json(path: Path, packages: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"packages": {p: {} for p in packages}}), encoding="utf-8")


def _write_parquet(path: Path, column: str, values: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({column: values}).to_parquet(path)


def _bulk_names(n: int, extra: list[str] | None = None) -> list[str]:
    names = [f"dummy-pkg-{i}" for i in range(n)]
    if extra:
        names.extend(extra)
    return names


def _make_catalog_root(
    root: Path,
    *,
    cf_names: list[str] | None = None,
    pypi_names: list[str] | None = None,
    mapping_names: list[str] | None = None,
    skip: frozenset[str] = frozenset(),
) -> None:
    """Build a --live-catalog PATH tree with the three Tier 0 Parquet outputs.
    `skip` names datasets to omit entirely (simulating "missing file")."""
    if "core_packages_enumerated" not in skip:
        _write_parquet(
            root / "intermediate/core_packages_enumerated/core_packages_enumerated.parquet",
            "conda_name",
            cf_names if cf_names is not None else _bulk_names(30_000),
        )
    if "pypi_universe" not in skip:
        _write_parquet(
            root / "intermediate/pypi_universe/pypi_universe.parquet",
            "pypi_name",
            pypi_names if pypi_names is not None else ["examplepkg"],
        )
    if "pypi_conda_mapping" not in skip:
        _write_parquet(
            root / "primary/pypi_conda_mapping/pypi_conda_mapping.parquet",
            "pypi_name",
            mapping_names if mapping_names is not None else [],
        )


def _run_main(
    tmp_path: Path,
    extra_args: list[str],
    curated: dict[str, list[str]] | None = None,
) -> int:
    xlsx_path = tmp_path / "analysis.xlsx"
    _write_minimal_xlsx(xlsx_path)
    curated_path = tmp_path / "curated.json"
    _write_curated_config(curated_path, curated or {})
    argv = [
        "conda-forge-packaging-inventory-operations-metrics",
        "--analysis-xlsx",
        str(xlsx_path),
        "--curated-config",
        str(curated_path),
        "--output-csv",
        str(tmp_path / "out.csv"),
        "--output-md",
        str(tmp_path / "out.md"),
        "--skip-revised-prompt",
        *extra_args,
    ]
    with mock.patch.object(sys, "argv", argv):
        return metrics.main()


def _run_main_no_xlsx(
    tmp_path: Path,
    extra_args: list[str],
    curated: dict[str, list[str]] | None = None,
) -> int:
    """Story 23.8: the same shape as _run_main() but WITHOUT --analysis-xlsx --
    the workbook-free invocation shape."""
    curated_path = tmp_path / "curated.json"
    _write_curated_config(curated_path, curated or {})
    argv = [
        "conda-forge-packaging-inventory-operations-metrics",
        "--curated-config",
        str(curated_path),
        "--output-csv",
        str(tmp_path / "out.csv"),
        "--output-md",
        str(tmp_path / "out.md"),
        "--skip-revised-prompt",
        *extra_args,
    ]
    with mock.patch.object(sys, "argv", argv):
        return metrics.main()


# ---------------------------------------------------------------------------
# load_live_catalog() unit tests -- I/O & Edge-Case Matrix rows
# ---------------------------------------------------------------------------


def test_all_three_present_above_floor(tmp_path: Path):
    root = tmp_path / "root"
    _make_catalog_root(
        root,
        cf_names=_bulk_names(30_000, ["examplepkg"]),
        pypi_names=["examplepkg", "otherpkg"],
        mapping_names=["examplepkg"],
    )
    result = metrics.load_live_catalog(root)
    assert result.failed == []
    assert result.warnings == []
    assert "examplepkg" in result.cf_packages
    assert "examplepkg" in result.pypi_index
    assert "examplepkg" in result.parselmouth_pypi


def test_core_packages_enumerated_missing_degrades_and_warns(tmp_path: Path):
    root = tmp_path / "root"
    _make_catalog_root(root, skip=frozenset({"core_packages_enumerated"}))
    result = metrics.load_live_catalog(root)
    assert result.cf_packages == set()
    assert "core_packages_enumerated" in result.failed
    assert any("core_packages_enumerated" in w for w in result.warnings)
    # the other two sets are unaffected
    assert "pypi_universe" not in result.failed
    assert "pypi_conda_mapping" not in result.failed


def test_core_packages_enumerated_below_floor_degrades_and_warns(tmp_path: Path):
    root = tmp_path / "root"
    _make_catalog_root(root, cf_names=_bulk_names(12_000))
    result = metrics.load_live_catalog(root)
    assert result.cf_packages == set()
    assert "core_packages_enumerated" in result.failed
    assert any(
        "core_packages_enumerated" in w and "below floor" in w for w in result.warnings
    )


def test_pypi_universe_missing_degrades_and_warns(tmp_path: Path):
    root = tmp_path / "root"
    _make_catalog_root(root, skip=frozenset({"pypi_universe"}))
    result = metrics.load_live_catalog(root)
    assert result.pypi_index == set()
    assert "pypi_universe" in result.failed


def test_pypi_universe_empty_degrades_and_warns(tmp_path: Path):
    root = tmp_path / "root"
    _make_catalog_root(root, pypi_names=[])
    result = metrics.load_live_catalog(root)
    assert result.pypi_index == set()
    assert "pypi_universe" in result.failed


def test_pypi_conda_mapping_missing_degrades_and_warns(tmp_path: Path):
    root = tmp_path / "root"
    _make_catalog_root(root, skip=frozenset({"pypi_conda_mapping"}))
    result = metrics.load_live_catalog(root)
    assert result.parselmouth_pypi == set()
    assert "pypi_conda_mapping" in result.failed


def test_pypi_conda_mapping_unreadable_degrades_and_warns(tmp_path: Path):
    root = tmp_path / "root"
    _make_catalog_root(root)
    corrupt = root / "primary/pypi_conda_mapping/pypi_conda_mapping.parquet"
    corrupt.parent.mkdir(parents=True, exist_ok=True)
    corrupt.write_bytes(b"not a parquet file")
    result = metrics.load_live_catalog(root)
    assert result.parselmouth_pypi == set()
    assert "pypi_conda_mapping" in result.failed


def test_pypi_conda_mapping_empty_has_no_floor(tmp_path: Path):
    """No documented floor for pypi_conda_mapping -- empty-but-readable is NOT a
    failure, unlike pypi_universe (floor 1)."""
    root = tmp_path / "root"
    _make_catalog_root(root, mapping_names=[])
    result = metrics.load_live_catalog(root)
    assert result.parselmouth_pypi == set()
    assert "pypi_conda_mapping" not in result.failed


# ---------------------------------------------------------------------------
# main() wiring -- CLI contract
# ---------------------------------------------------------------------------


def test_live_catalog_only_without_live_catalog_exits_2(tmp_path: Path):
    rc = _run_main(tmp_path, ["--live-catalog-only"])
    assert rc == 2
    assert not (tmp_path / "out.csv").exists()


def test_live_catalog_only_missing_root_exits_2_before_output(tmp_path: Path):
    missing_root = tmp_path / "does-not-exist"
    rc = _run_main(tmp_path, ["--live-catalog", str(missing_root), "--live-catalog-only"])
    assert rc == 2
    assert not (tmp_path / "out.csv").exists()
    assert not (tmp_path / "out.md").exists()


def test_live_catalog_only_sub_floor_exits_2_before_output(tmp_path: Path, capsys):
    root = tmp_path / "root"
    _make_catalog_root(root, cf_names=_bulk_names(12_000))
    rc = _run_main(tmp_path, ["--live-catalog", str(root), "--live-catalog-only"])
    assert rc == 2
    assert not (tmp_path / "out.csv").exists()
    assert not (tmp_path / "out.md").exists()
    err = capsys.readouterr().err
    assert "core_packages_enumerated" in err


def test_live_catalog_sub_floor_without_only_degrades_and_completes(tmp_path: Path, capsys):
    root = tmp_path / "root"
    # core_packages_enumerated is sub-floor (degrades cf_packages to set()) and
    # carries no "examplepkg" entry even above the floor line, so this proves
    # the degrade -- not a coincidental miss. pypi_universe/pypi_conda_mapping
    # stay at their defaults (examplepkg present / mapping empty) so PyPI_Verified
    # resolves independently of the degraded conda-forge set.
    _make_catalog_root(root, cf_names=_bulk_names(12_000))
    rc = _run_main(
        tmp_path,
        ["--live-catalog", str(root)],
        curated={"test-group": ["examplepkg"]},
    )
    assert rc == 0
    assert (tmp_path / "out.csv").exists()
    out = capsys.readouterr().out
    assert "Warnings (fallbacks used):" in out
    assert "core_packages_enumerated" in out
    csv_text = (tmp_path / "out.csv").read_text(encoding="utf-8")
    lines = [line for line in csv_text.splitlines() if line.startswith("curated:test-group")]
    assert len(lines) == 1
    # PyPI_Verified=Yes (pypi_universe unaffected), CondaForge_Verified=No
    # (cf_packages degraded to empty, parselmouth_pypi empty by default).
    assert ",Yes,No," in lines[0]


def test_live_catalog_success_no_http_fetch_for_replaced_sets(tmp_path: Path, blocked_network):
    root = tmp_path / "root"
    _make_catalog_root(
        root,
        cf_names=_bulk_names(30_000, ["examplepkg"]),
        pypi_names=["examplepkg"],
        mapping_names=["examplepkg"],
    )
    # anaconda_main is an UNTOUCHED acquisition (not one of the three replaced
    # sets) -- give it a valid local snapshot so it never falls through to a
    # live fetch either, keeping fetch_json's call count an unambiguous proof
    # for the three replaced sets specifically.
    main_channeldata = tmp_path / "main-channeldata.json"
    _write_channeldata_json(main_channeldata, ["someanacondapkg"])

    with mock.patch.object(
        metrics, "load_pypi_simple_names"
    ) as m_load_pypi, mock.patch.object(
        metrics, "load_parselmouth_pypi_names"
    ) as m_load_pm, mock.patch.object(
        metrics.urllib.request, "urlopen"
    ) as m_urlopen:
        rc = _run_main(
            tmp_path,
            [
                "--live-catalog",
                str(root),
                "--main-channeldata",
                str(main_channeldata),
                # old flags stay accepted-and-unused for the three replaced sets
                "--cf-channeldata",
                str(tmp_path / "bogus-cf-channeldata.json"),
                "--pypi-simple",
                str(tmp_path / "bogus-pypi-simple.html"),
                "--parselmouth",
                str(tmp_path / "bogus-parselmouth.json"),
            ],
        )
    assert rc == 0
    m_load_pypi.assert_not_called()
    m_load_pm.assert_not_called()
    m_urlopen.assert_not_called()
    blocked_network["fetch_json"].assert_not_called()


def test_live_catalog_computes_verification_from_parquet_alone(tmp_path: Path):
    root = tmp_path / "root"
    _make_catalog_root(
        root,
        cf_names=_bulk_names(30_000, ["examplepkg"]),
        pypi_names=["examplepkg"],
        mapping_names=[],
    )
    rc = _run_main(
        tmp_path,
        ["--live-catalog", str(root)],
        curated={"test-group": ["examplepkg"]},
    )
    assert rc == 0
    csv_text = (tmp_path / "out.csv").read_text(encoding="utf-8")
    lines = [line for line in csv_text.splitlines() if line.startswith("curated:test-group")]
    assert len(lines) == 1
    assert ",Yes,Yes," in lines[0]  # PyPI_Verified, CondaForge_Verified columns


def test_no_live_catalog_flag_reaches_try_source_and_local_file_path(tmp_path: Path):
    """Regression guard: omitting --live-catalog reaches the exact same
    try_source/local-file code path as before this story."""
    with mock.patch.object(
        metrics, "load_channeldata_names", wraps=metrics.load_channeldata_names
    ) as m_load_cd, mock.patch.object(
        metrics, "load_pypi_simple_names", wraps=metrics.load_pypi_simple_names
    ) as m_load_pypi, mock.patch.object(
        metrics, "load_parselmouth_pypi_names", wraps=metrics.load_parselmouth_pypi_names
    ) as m_load_pm:
        rc = _run_main(tmp_path, [])
    assert rc == 0
    m_load_cd.assert_called()
    m_load_pypi.assert_called()
    m_load_pm.assert_called()


# ---------------------------------------------------------------------------
# write_revised_prompt() -- echoes --live-catalog/--live-catalog-only
# ---------------------------------------------------------------------------


def test_write_revised_prompt_echoes_live_catalog_flags(tmp_path: Path):
    """_run_main() hardcodes --skip-revised-prompt for every other test in this
    file, so write_revised_prompt()'s --live-catalog/--live-catalog-only echo
    logic needs its own coverage: a run WITHOUT --skip-revised-prompt must
    regenerate the prompt doc with both flags present."""
    root = tmp_path / "root"
    _make_catalog_root(
        root,
        cf_names=_bulk_names(30_000, ["examplepkg"]),
        pypi_names=["examplepkg"],
        mapping_names=[],
    )
    xlsx_path = tmp_path / "analysis.xlsx"
    _write_minimal_xlsx(xlsx_path)
    curated_path = tmp_path / "curated.json"
    _write_curated_config(curated_path, {})
    revised_prompt_path = tmp_path / "revised-prompt.md"
    argv = [
        "conda-forge-packaging-inventory-operations-metrics",
        "--analysis-xlsx",
        str(xlsx_path),
        "--curated-config",
        str(curated_path),
        "--output-csv",
        str(tmp_path / "out.csv"),
        "--output-md",
        str(tmp_path / "out.md"),
        "--output-revised-prompt",
        str(revised_prompt_path),
        "--live-catalog",
        str(root),
        "--live-catalog-only",
    ]
    with mock.patch.object(sys, "argv", argv):
        rc = metrics.main()
    assert rc == 0
    text = revised_prompt_path.read_text(encoding="utf-8")
    assert f'--live-catalog "{root}"' in text
    assert "--live-catalog-only" in text


# ---------------------------------------------------------------------------
# Story 23.8 -- load_universe_from_catalog() unit tests
# ---------------------------------------------------------------------------


def _write_universe_parquet(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    pd.DataFrame(rows, columns=columns).to_parquet(path, index=False)


def _universe_row(name: str, sources: list[str], role: str = "N/A", member: bool = False) -> dict:
    return {
        "core_python_package_name": name,
        "package_input_names": [name],
        "sources": sources,
        "in_cdo_ent_jfrog": "tab:CDO-ENT-JFROG" in sources,
        "in_cdo_ent_conda": "tab:CDO-ENT-CONDA" in sources,
        "in_openteams": "tab:OpenTeams" in sources,
        "in_conda_forge": "tab:Conda-Forge" in sources,
        "in_basilisk": "tab:Basilisk" in sources,
        "in_anaconda_main": "tab:Anaconda-Main" in sources,
        "in_anaconda_dist": "tab:Anaaconda-Dist" in sources,
        "in_aoss_free": "tab:GAOSS-Free" in sources,
        "in_aoss_premium": "tab:GAOSS-Premium" in sources,
        "role": role,
        "openteams_universe_member": member,
    }


def test_universe_missing_fails(tmp_path: Path):
    result = metrics.load_universe_from_catalog(tmp_path / "root", floor=1)
    assert result.failed is True
    assert any("missing" in w for w in result.warnings)


def test_universe_unreadable_fails(tmp_path: Path):
    root = tmp_path / "root"
    path = root / "derived/inventory_universe/inventory_universe.parquet"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"not a parquet file")
    result = metrics.load_universe_from_catalog(root, floor=1)
    assert result.failed is True
    assert any("unreadable" in w for w in result.warnings)


def test_universe_sub_floor_fails(tmp_path: Path):
    root = tmp_path / "root"
    _write_universe_parquet(
        root / "derived/inventory_universe/inventory_universe.parquet",
        [_universe_row("onlyone", ["tab:Conda-Forge"])],
    )
    result = metrics.load_universe_from_catalog(root, floor=2)
    assert result.failed is True
    assert any("below floor" in w for w in result.warnings)


def test_universe_builds_records_tab_packages_and_roles(tmp_path: Path):
    root = tmp_path / "root"
    _write_universe_parquet(
        root / "derived/inventory_universe/inventory_universe.parquet",
        [
            _universe_row(
                "widget", ["tab:Conda-Forge", "tab:CDO-ENT-JFROG"], member=True
            ),
            _universe_row("maintpkg", ["tab:CDO-ENT-CONDA"], role="Maintainer", member=True),
            _universe_row("copkg", ["tab:CDO-ENT-CONDA"], role="Co-Maintainer", member=True),
        ],
    )
    result = metrics.load_universe_from_catalog(root, floor=1)
    assert result.failed is False
    assert set(result.records) == {"widget", "maintpkg", "copkg"}
    assert result.records["widget"].sources == {"tab:Conda-Forge", "tab:CDO-ENT-JFROG"}
    assert result.tab_packages["Conda-Forge"] == {"widget"}
    assert result.tab_packages["CDO-ENT-JFROG"] == {"widget"}
    assert result.tab_packages["CDO-ENT-CONDA"] == {"maintpkg", "copkg"}
    assert result.maint == {"maintpkg"}
    assert result.co == {"copkg"}


def test_universe_openteams_summary_reproduced_from_board(tmp_path: Path):
    root = tmp_path / "root"
    _write_universe_parquet(
        root / "derived/inventory_universe/inventory_universe.parquet",
        [_universe_row("filler", ["tab:Conda-Forge"])],
    )
    board_path = root / "raw/openteams_project_1_board_raw/openteams_project_1_board.parquet"
    board_path.parent.mkdir(parents=True)
    pd.DataFrame(
        {
            "title": [
                "some ticket | richlib",
                "[Conda-Forge Packaging] anotherpkg",
                "Some CVE | 2026-08-12",
            ]
        }
    ).to_parquet(board_path, index=False)
    result = metrics.load_universe_from_catalog(root, floor=1)
    assert result.openteams_summary.rows_used_a == 1
    assert result.openteams_summary.rows_used_b == 1
    assert result.openteams_summary.rows_ignored_c == 1
    assert result.openteams_summary.unique_packages == {"richlib", "anotherpkg"}


def test_universe_openteams_board_missing_degrades_to_empty_summary(tmp_path: Path):
    root = tmp_path / "root"
    _write_universe_parquet(
        root / "derived/inventory_universe/inventory_universe.parquet",
        [_universe_row("filler", ["tab:Conda-Forge"])],
    )
    result = metrics.load_universe_from_catalog(root, floor=1)
    assert result.failed is False
    assert result.openteams_summary.rows_used_a == 0
    assert result.openteams_summary.rows_used_b == 0
    assert result.openteams_summary.rows_ignored_c == 0
    assert any("openteams board missing" in w for w in result.warnings)


def test_universe_priority_source_present_uses_its_p_bucket(tmp_path: Path):
    root = tmp_path / "root"
    _write_universe_parquet(
        root / "derived/inventory_universe/inventory_universe.parquet",
        [_universe_row("widget", ["tab:Conda-Forge"])],
    )
    priority_path = root / "derived/inventory_priority_assignments/inventory_priority_assignments.parquet"
    priority_path.parent.mkdir(parents=True)
    pd.DataFrame({"core_python_package_name": ["widget"], "P": ["P3"]}).to_parquet(
        priority_path, index=False
    )
    result = metrics.load_universe_from_catalog(root, floor=1)
    assert result.priority_map == {"widget": "P3"}
    assert not any("Priority_Bucket defaulted to P9" in w for w in result.warnings)


def test_universe_priority_source_absent_warns_once(tmp_path: Path):
    root = tmp_path / "root"
    _write_universe_parquet(
        root / "derived/inventory_universe/inventory_universe.parquet",
        [_universe_row("widget", ["tab:Conda-Forge"])],
    )
    result = metrics.load_universe_from_catalog(root, floor=1)
    assert result.priority_map == {}
    matches = [w for w in result.warnings if "Priority_Bucket defaulted to P9" in w]
    assert len(matches) == 1


# ---------------------------------------------------------------------------
# Story 23.8 -- main() CLI contract: --analysis-xlsx optional
# ---------------------------------------------------------------------------


def test_neither_analysis_xlsx_nor_live_catalog_exits_2(tmp_path: Path, capsys):
    rc = _run_main_no_xlsx(tmp_path, [])
    assert rc == 2
    assert not (tmp_path / "out.csv").exists()
    err = capsys.readouterr().err
    assert "--analysis-xlsx" in err and "--live-catalog" in err


def test_live_catalog_without_xlsx_missing_universe_exits_2_even_without_only(tmp_path: Path):
    root = tmp_path / "root"
    _make_catalog_root(root, cf_names=_bulk_names(30_000), pypi_names=["x"])
    # no inventory_universe.parquet under root at all
    rc = _run_main_no_xlsx(tmp_path, ["--live-catalog", str(root)])
    assert rc == 2
    assert not (tmp_path / "out.csv").exists()
    assert not (tmp_path / "out.md").exists()


def test_live_catalog_only_without_xlsx_missing_universe_exits_2(tmp_path: Path):
    root = tmp_path / "root"
    _make_catalog_root(root, cf_names=_bulk_names(30_000), pypi_names=["x"])
    rc = _run_main_no_xlsx(tmp_path, ["--live-catalog", str(root), "--live-catalog-only"])
    assert rc == 2
    assert not (tmp_path / "out.csv").exists()


def test_live_catalog_without_xlsx_sub_floor_universe_exits_2(tmp_path: Path, capsys):
    """Unlike the three Tier 0 sets, a sub-floor universe is fatal even
    WITHOUT --live-catalog-only -- there is no usable output to degrade to."""
    root = tmp_path / "root"
    _make_catalog_root(root, cf_names=_bulk_names(30_000), pypi_names=["x"])
    _write_universe_parquet(
        root / "derived/inventory_universe/inventory_universe.parquet",
        [_universe_row("onlyone", ["tab:Conda-Forge"])],
    )
    rc = _run_main_no_xlsx(tmp_path, ["--live-catalog", str(root)])
    assert rc == 2
    assert not (tmp_path / "out.csv").exists()
    err = capsys.readouterr().err
    assert "below floor" in err


def test_live_catalog_only_without_xlsx_missing_tier0_dataset_exits_2(tmp_path: Path):
    """--live-catalog-only still gates the three 21.3 Tier 0 datasets even when
    the universe itself is present and above floor."""
    root = tmp_path / "root"
    _make_catalog_root(root, skip=frozenset({"core_packages_enumerated"}))
    rows = [_universe_row(f"pkg{i}", ["tab:Conda-Forge"]) for i in range(10_000)]
    _write_universe_parquet(root / "derived/inventory_universe/inventory_universe.parquet", rows)
    rc = _run_main_no_xlsx(tmp_path, ["--live-catalog", str(root), "--live-catalog-only"])
    assert rc == 2
    assert not (tmp_path / "out.csv").exists()


def test_workbook_free_run_completes_with_no_xlsx_opened(tmp_path: Path, blocked_network, capsys):
    root = tmp_path / "root"
    _make_catalog_root(root, skip=frozenset({"core_packages_enumerated", "pypi_universe", "pypi_conda_mapping"}))
    rows = [_universe_row(f"pkg{i}", ["tab:Conda-Forge"]) for i in range(10_000)]
    rows.append(_universe_row("widget", ["tab:CDO-ENT-JFROG"], member=True))
    _write_universe_parquet(root / "derived/inventory_universe/inventory_universe.parquet", rows)

    with mock.patch.object(metrics, "XlsxReader") as m_xlsx:
        rc = _run_main_no_xlsx(tmp_path, ["--live-catalog", str(root)])
    assert rc == 0
    m_xlsx.assert_not_called()
    blocked_network["fetch_text"].assert_not_called()
    blocked_network["fetch_json"].assert_not_called()
    assert (tmp_path / "out.csv").exists()
    csv_text = (tmp_path / "out.csv").read_text(encoding="utf-8")
    assert "pkg0" in csv_text
    assert "widget" in csv_text

    # I/O matrix row "10kClosed-only names": the known workbook-only delta
    # (Design Notes) is called out in the run summary, since no catalog
    # source exists to reproduce or count it live.
    out = capsys.readouterr().out
    assert "workbook-free run" in out
    assert "10kClosed" in out
    assert "spec-23-8-workbook-free-metrics-universe.md" in out


# ---------------------------------------------------------------------------
# Story 23.8 -- AC #2: workbook vs. --live-catalog universe parity
# ---------------------------------------------------------------------------


def _parse_csv(path: Path) -> dict[str, dict[str, str]]:
    import csv as csv_mod

    with path.open(newline="", encoding="utf-8") as f:
        return {row["Core_Python_Package_Name"]: row for row in csv_mod.DictReader(f)}


def _per_source_matrix_lines(md_text: str) -> list[str]:
    lines = md_text.splitlines()
    start = lines.index("## Per-Source Package Inclusion & Verification Matrix")
    section = lines[start:]
    end = next(i for i, line in enumerate(section) if i > 2 and line.startswith("## "))
    return [line for line in section[:end] if line.startswith("|") and "---" not in line]


@pytest.mark.skipif(not MINI_WORKBOOK_PATH.exists(), reason="frozen fixture pair not present")
def test_parity_workbook_vs_live_catalog_universe(tmp_path: Path):
    """AC #2 -- the frozen fixture pair (scripts/tests/fixtures/inventory_universe/):
    metrics.py run with --analysis-xlsx vs. with --live-catalog only must produce
    the same CSV rows and the same MD per-source matrix for every non-10kClosed
    package (`10kClosed` has no catalog source by design -- Design Notes).

    Excluded from the strict per-field comparison: `Verification_Timestamp_UTC`
    (each run stamps its own wall-clock time) and `Priority_Bucket` for the
    CDO-ENT-CONDA-sourced rows specifically -- the legacy `priority_bucket()`
    grants those an unconditional P4 via their `about:`/`tab:CDO-ENT-CONDA`
    sources, while this story's own I/O & Edge-Case Matrix mandates an
    unconditional P9-for-every-row default in workbook-free mode when no
    Story 23.3 `inventory_priority_assignments.parquet` exists yet (true here) --
    an intentional, spec-documented divergence, not a bug. Every OTHER row's
    Priority_Bucket (asserted below) matches, confirming the divergence is
    exactly this one, known, documented case.
    """
    xlsx_dir = tmp_path / "xlsx-run"
    xlsx_dir.mkdir()
    rc_xlsx = 0
    argv = [
        "conda-forge-packaging-inventory-operations-metrics",
        "--analysis-xlsx",
        str(MINI_WORKBOOK_PATH),
        "--live-catalog",
        str(MINI_CATALOG_ROOT),
        "--curated-config",
        str(_write_empty_curated(xlsx_dir)),
        "--output-csv",
        str(xlsx_dir / "out.csv"),
        "--output-md",
        str(xlsx_dir / "out.md"),
        "--skip-revised-prompt",
    ]
    with mock.patch.object(sys, "argv", argv):
        rc_xlsx = metrics.main()
    assert rc_xlsx == 0

    catalog_dir = tmp_path / "catalog-run"
    catalog_dir.mkdir()
    argv = [
        "conda-forge-packaging-inventory-operations-metrics",
        "--live-catalog",
        str(MINI_CATALOG_ROOT),
        "--curated-config",
        str(_write_empty_curated(catalog_dir)),
        "--output-csv",
        str(catalog_dir / "out.csv"),
        "--output-md",
        str(catalog_dir / "out.md"),
        "--skip-revised-prompt",
    ]
    with mock.patch.object(sys, "argv", argv):
        rc_catalog = metrics.main()
    assert rc_catalog == 0

    xlsx_rows = _parse_csv(xlsx_dir / "out.csv")
    catalog_rows = _parse_csv(catalog_dir / "out.csv")

    # 10kClosed's one name never appears on either side (dropped by the tenk
    # filter in xlsx mode; absent by construction in workbook-free mode).
    assert "closedonlypkg" not in xlsx_rows
    assert "closedonlypkg" not in catalog_rows
    # the output-tab-only name never appears either (OUTPUT_TABS skip).
    assert "outputtabpkg" not in xlsx_rows
    assert "outputtabpkg" not in catalog_rows

    assert set(xlsx_rows) == set(catalog_rows)

    ignore_fields = {"Verification_Timestamp_UTC"}
    cdo_ent_conda_names = {"pytestpkg", "comaintpkg"}
    for name, xlsx_row in xlsx_rows.items():
        catalog_row = catalog_rows[name]
        fields = ignore_fields | ({"Priority_Bucket"} if name in cdo_ent_conda_names else set())
        for field in xlsx_row:
            if field in fields:
                continue
            assert xlsx_row[field] == catalog_row[field], (name, field, xlsx_row[field], catalog_row[field])

    # the documented divergence, made explicit (not just excluded above):
    assert xlsx_rows["pytestpkg"]["Priority_Bucket"] == "P4"
    assert catalog_rows["pytestpkg"]["Priority_Bucket"] == "P9"
    # every OTHER row's Priority_Bucket really does match (both P9 here).
    for name in set(xlsx_rows) - cdo_ent_conda_names:
        assert xlsx_rows[name]["Priority_Bucket"] == catalog_rows[name]["Priority_Bucket"] == "P9"

    xlsx_md = (xlsx_dir / "out.md").read_text(encoding="utf-8")
    catalog_md = (catalog_dir / "out.md").read_text(encoding="utf-8")
    assert _per_source_matrix_lines(xlsx_md) == _per_source_matrix_lines(catalog_md)


def _write_empty_curated(directory: Path) -> Path:
    path = directory / "curated.json"
    _write_curated_config(path, {})
    return path


if __name__ == "__main__":
    sys.exit(pytest.main([str(Path(__file__).resolve())]))
