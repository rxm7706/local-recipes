#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "pyarrow", "pytest"]
# ///
"""Tests for conda-forge-packaging-inventory-operations_metrics.py's --live-catalog
contract (Story 21.3, Epic 21). Mirrors the
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


if __name__ == "__main__":
    sys.exit(pytest.main([str(Path(__file__).resolve())]))
