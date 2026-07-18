"""Schedule-as-fixtures for the § 3.4 refresh assets (Story B5 — AC-1).

Dagster scheduling is C1's job (DW-B5-2): B5 encodes the cadence DECLARATIVELY in
`params:refresh_cadences` and proves it == the legacy tasks' TTLs here, as a fixture.
`dagster` is NEVER imported in package code (AD-1); the live `dagster-dryrun` gate runs
once C1 exists. C1 consumes `params:refresh_cadences` to emit the Dagster Schedules.
"""

from __future__ import annotations

import pathlib

import yaml

from pyforge.atlas.datasets.refresh import LEGACY_REFRESH_TTLS, WEEKLY_SECONDS

_MEMBER_DIR = pathlib.Path(__file__).resolve().parents[2]
_PARAMETERS_YML = _MEMBER_DIR / "conf" / "base" / "parameters.yml"
_CATALOG_YML = _MEMBER_DIR / "conf" / "base" / "catalog.yml"
_ATLAS_PKG = _MEMBER_DIR / "src" / "pyforge" / "atlas"


def _params() -> dict:
    return yaml.safe_load(_PARAMETERS_YML.read_text(encoding="utf-8"))


def _refresh_cadences() -> dict:
    return dict(_params().get("refresh_cadences", {}))


def test_refresh_cadences_equal_legacy_ttls():
    # AC-1: the declarative cadence == the legacy tasks' TTLs (schedule-as-fixture).
    assert _refresh_cadences() == LEGACY_REFRESH_TTLS


def test_cadences_cross_check_against_the_independent_ttls_block():
    # BH-9 guard: don't let the cadence be a same-file tautology — cross-check the two
    # stores that ALSO carry a row-level `ttls` entry (authored in A2 from the legacy
    # TTLs) against an INDEPENDENT source. If a legacy TTL drifts, updating `ttls` without
    # `refresh_cadences` (or vice-versa) now fails this gate.
    params = _params()
    cadences = dict(params.get("refresh_cadences", {}))
    ttls = dict(params.get("ttls", {}))
    for store in ("vulnerability_osv_offline_store", "pypi_conda_map_store"):
        assert store in ttls, store
        assert cadences[store] == ttls[store], store


def test_all_three_stores_are_weekly():
    cadences = _refresh_cadences()
    assert set(cadences) == {
        "vulnerability_vdb_store",
        "vulnerability_osv_offline_store",
        "pypi_conda_map_store",
    }
    assert all(v == WEEKLY_SECONDS for v in cadences.values())


def test_cadence_keys_are_real_catalog_stores():
    catalog_text = _CATALOG_YML.read_text(encoding="utf-8")
    for store in _refresh_cadences():
        assert f"\n{store}:" in catalog_text, store


def test_no_dagster_import_in_the_refresh_surface():
    """Dagster wiring is C1 (DW-B5-2): the B5 refresh surface must not import dagster.
    (The whole-package guarantee is `tests/catalog/test_no_inline_io.py::test_ad1_import_direction`;
    this is a focused, self-documenting guard on the new files that names the C1 deferral.)"""
    b5_files = [
        _ATLAS_PKG / "datasets" / "refresh.py",
        _ATLAS_PKG / "pipelines" / "vulnerability" / "nodes.py",
        _ATLAS_PKG / "pipelines" / "pypi_intelligence" / "nodes.py",
    ]
    for path in b5_files:
        src = path.read_text(encoding="utf-8")
        assert "import dagster" not in src, path
        assert "from dagster" not in src, path
