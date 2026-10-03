"""Story 27.1 / DW-FU-23-5 — derived_artifacts nodes over fixture corpus (offline)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from pyforge.atlas.pipelines.derived_artifacts.nodes import (
    build_identity_complete_export,
    build_inventory_aoss_free_queue,
    build_inventory_verified_packages,
)

_REPO_ROOT = Path(__file__).resolve().parents[8]
_FIXTURE_JSON = (
    _REPO_ROOT / "src/shared/packages/pyforge-atlas/tests/fixtures/inventory_identity/complete_export_expected.json"
)
_LOW_FLOOR = {
    "verification_sets": {"cf_or_pm_floor": 0, "pypi_universe_floor": 0},
    "identity_complete_export": {"verification_timestamp_utc": "2026-08-30T12:00:00Z"},
    "inventory_verified_packages": {"verification_timestamp_utc": "2026-08-30T12:00:00Z"},
}


def _corpus() -> dict:
    return json.loads(_FIXTURE_JSON.read_text(encoding="utf-8"))


def test_derived_artifacts_inventory_nodes_over_fixture_corpus():
    corpus = _corpus()
    universe = pd.DataFrame(corpus.get("inventory_universe") or [])
    core = pd.DataFrame([{"conda_name": "already-packaged"}])
    pypi = pd.DataFrame([{"pypi_name": "high-priority"}, {"pypi_name": "already-packaged"}])
    mapping = pd.DataFrame(columns=["pypi_name"])
    priority = pd.DataFrame(corpus.get("inventory_priority_assignments") or [])

    verified = build_inventory_verified_packages(
        universe,
        core,
        pypi,
        mapping,
        priority,
        _LOW_FLOOR,
    )
    assert not verified.empty

    queue = build_inventory_aoss_free_queue(
        pd.DataFrame([{"pypi_name": "aossfreepkg"}]),
        core,
        pypi,
        mapping,
        pd.DataFrame(corpus.get("enterprise_jfrog_consumption") or []),
        pd.DataFrame([]),
        _LOW_FLOOR,
    )
    assert isinstance(queue, pd.DataFrame)

    complete = build_identity_complete_export(
        pd.DataFrame(corpus["identity_packages_primary"]),
        priority,
        pd.DataFrame(corpus.get("enterprise_jfrog_consumption") or []),
        pd.DataFrame([]),
        verified,
        pd.DataFrame([]),
        pd.DataFrame([]),
        universe,
        _LOW_FLOOR,
    )
    assert not complete.empty
    assert complete.iloc[0]["Verification_Timestamp_UTC"] == "2026-08-30T12:00:00Z"
