"""Unit tests — the bundled conda→pypi map's real shape (Story 2.1) plus
the TSV→JSON converter script (``scripts/generate_conda_pypi_map.py``,
imported by path since it is a dev-only maintenance script, not part of
the installed package).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from pyforge.warden.mapping import load_conda_pypi_map

_SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent.parent / "scripts" / "generate_conda_pypi_map.py"
)


def _load_converter():
    spec = importlib.util.spec_from_file_location("generate_conda_pypi_map", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- the bundled map's real shape --------------------------------------------


def test_bundled_map_is_non_empty_and_correctly_shaped():
    mapping = load_conda_pypi_map()
    assert mapping
    for entry in mapping.values():
        assert isinstance(entry, dict)
        assert entry.keys() == {"pypi_name", "match_source", "match_confidence"}
        assert isinstance(entry["pypi_name"], str) and entry["pypi_name"]
        assert isinstance(entry["match_source"], str)
        assert entry["match_confidence"] in ("verified", "likely")


def test_bundled_map_never_flattened_to_name_to_name():
    """AC1: entries must never collapse to a bare pypi-name string."""
    mapping = load_conda_pypi_map()
    for entry in mapping.values():
        assert isinstance(entry, dict)


def test_bundled_map_has_no_none_match_source_entries():
    """Only rows with a real pypi_purl are bundled (match_source != "none")
    -- a plain map miss is already the correct "no candidate" signal. Every
    bundled entry's match_confidence is consequently a real tier too (never
    the TSV's own "n/a" absence marker)."""
    mapping = load_conda_pypi_map()
    for entry in mapping.values():
        assert isinstance(entry, dict)
        assert entry["match_source"] != "none"
        assert entry["match_confidence"] != "n/a"


# --- the TSV->JSON converter --------------------------------------------------


def test_converter_purl_name_extraction():
    converter = _load_converter()
    assert converter._purl_name("pkg:conda/numpy?channel=conda-forge") == "numpy"
    assert converter._purl_name("pkg:pypi/numpy") == "numpy"
    assert converter._purl_name("pkg:conda/py-yaml12@1.0.0?channel=conda-forge") == "py-yaml12"


def test_converter_filters_none_match_source(tmp_path):
    converter = _load_converter()
    tsv = tmp_path / "purls.tsv"
    tsv.write_text(
        "conda_purl\tpypi_purl\tmatch_source\tmatch_confidence\n"
        "pkg:conda/numpy?channel=conda-forge\tpkg:pypi/numpy\tparselmouth\tverified\n"
        "pkg:conda/_dvc?channel=conda-forge\t\tnone\tn/a\n"
        "pkg:conda/foo?channel=conda-forge\tpkg:pypi/foo-py\tname_coincidence\tlikely\n",
        encoding="utf-8",
    )

    entries = converter.convert(tsv)

    assert entries == {
        "foo": {
            "pypi_name": "foo-py",
            "match_source": "name_coincidence",
            "match_confidence": "likely",
        },
        "numpy": {
            "pypi_name": "numpy",
            "match_source": "parselmouth",
            "match_confidence": "verified",
        },
    }


def test_converter_rejects_a_tsv_missing_a_required_column(tmp_path):
    converter = _load_converter()
    tsv = tmp_path / "purls.tsv"
    tsv.write_text(
        "conda_purl\tpypi_purl\tmatch_source\n"  # match_confidence missing
        "pkg:conda/numpy?channel=conda-forge\tpkg:pypi/numpy\tparselmouth\n",
        encoding="utf-8",
    )

    try:
        converter.convert(tsv)
    except ValueError as exc:
        assert "match_confidence" in str(exc)
    else:
        raise AssertionError("expected ValueError for a missing required column")


def test_converter_skips_a_short_row_instead_of_crashing(tmp_path, capsys):
    converter = _load_converter()
    tsv = tmp_path / "purls.tsv"
    tsv.write_text(
        "conda_purl\tpypi_purl\tmatch_source\tmatch_confidence\n"
        "pkg:conda/numpy?channel=conda-forge\tpkg:pypi/numpy\tparselmouth\tverified\n"
        "pkg:conda/truncated?channel=conda-forge\n",  # missing 3 trailing columns
        encoding="utf-8",
    )

    entries = converter.convert(tsv)

    assert entries == {
        "numpy": {
            "pypi_name": "numpy",
            "match_source": "parselmouth",
            "match_confidence": "verified",
        }
    }
    assert "skipped 1" in capsys.readouterr().err


def test_converter_skips_an_unrecognized_confidence_tier(tmp_path):
    converter = _load_converter()
    tsv = tmp_path / "purls.tsv"
    tsv.write_text(
        "conda_purl\tpypi_purl\tmatch_source\tmatch_confidence\n"
        "pkg:conda/numpy?channel=conda-forge\tpkg:pypi/numpy\tparselmouth\tunknown-tier\n",
        encoding="utf-8",
    )

    entries = converter.convert(tsv)

    assert entries == {}


def test_converter_skips_an_empty_extracted_name(tmp_path):
    converter = _load_converter()
    tsv = tmp_path / "purls.tsv"
    tsv.write_text(
        "conda_purl\tpypi_purl\tmatch_source\tmatch_confidence\n"
        "pkg:conda/?channel=conda-forge\tpkg:pypi/numpy\tparselmouth\tverified\n",
        encoding="utf-8",
    )

    entries = converter.convert(tsv)

    assert entries == {}


def test_converter_duplicate_conda_name_keeps_the_more_trusted_row(tmp_path):
    """A later, lower-trust row must never silently downgrade an
    already-resolved higher-trust identity (order-independent)."""
    converter = _load_converter()
    tsv = tmp_path / "purls.tsv"
    tsv.write_text(
        "conda_purl\tpypi_purl\tmatch_source\tmatch_confidence\n"
        "pkg:conda/numpy?channel=conda-forge\tpkg:pypi/numpy\tparselmouth\tverified\n"
        "pkg:conda/numpy?channel=conda-forge\tpkg:pypi/numpy-py\tname_coincidence\tlikely\n",
        encoding="utf-8",
    )

    entries = converter.convert(tsv)

    assert entries == {
        "numpy": {
            "pypi_name": "numpy",
            "match_source": "parselmouth",
            "match_confidence": "verified",
        }
    }


def test_converter_duplicate_conda_name_upgrades_to_a_later_more_trusted_row(tmp_path):
    converter = _load_converter()
    tsv = tmp_path / "purls.tsv"
    tsv.write_text(
        "conda_purl\tpypi_purl\tmatch_source\tmatch_confidence\n"
        "pkg:conda/numpy?channel=conda-forge\tpkg:pypi/numpy-py\tname_coincidence\tlikely\n"
        "pkg:conda/numpy?channel=conda-forge\tpkg:pypi/numpy\tparselmouth\tverified\n",
        encoding="utf-8",
    )

    entries = converter.convert(tsv)

    assert entries == {
        "numpy": {
            "pypi_name": "numpy",
            "match_source": "parselmouth",
            "match_confidence": "verified",
        }
    }


def test_converter_output_is_sorted_by_key(tmp_path):
    converter = _load_converter()
    tsv = tmp_path / "purls.tsv"
    tsv.write_text(
        "conda_purl\tpypi_purl\tmatch_source\tmatch_confidence\n"
        "pkg:conda/zeta?channel=conda-forge\tpkg:pypi/zeta\tparselmouth\tverified\n"
        "pkg:conda/alpha?channel=conda-forge\tpkg:pypi/alpha\tparselmouth\tverified\n",
        encoding="utf-8",
    )

    entries = converter.convert(tsv)

    assert list(entries.keys()) == ["alpha", "zeta"]


def test_converter_main_writes_json(tmp_path):
    converter = _load_converter()
    tsv = tmp_path / "purls.tsv"
    tsv.write_text(
        "conda_purl\tpypi_purl\tmatch_source\tmatch_confidence\n"
        "pkg:conda/numpy?channel=conda-forge\tpkg:pypi/numpy\tparselmouth\tverified\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "out.json"

    argv = sys.argv
    sys.argv = ["generate_conda_pypi_map.py", str(tsv), "--out", str(out_path)]
    try:
        converter.main()
    finally:
        sys.argv = argv

    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written == {
        "numpy": {
            "pypi_name": "numpy",
            "match_source": "parselmouth",
            "match_confidence": "verified",
        }
    }
