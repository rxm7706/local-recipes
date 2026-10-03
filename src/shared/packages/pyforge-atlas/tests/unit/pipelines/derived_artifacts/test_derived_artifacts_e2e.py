"""Story 27.1 / DW-FU-23-5 — derived_artifacts via Kedro session (offline fixtures)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[8]
_MEMBER_DIR = Path(__file__).resolve().parents[4]
_FIXTURE_CATALOG = _REPO_ROOT / "scripts/tests/fixtures/inventory_universe/catalog"
_LOW_FLOOR = {
    "verification_sets": {"cf_or_pm_floor": 0, "pypi_universe_floor": 0},
    "inventory_verified_packages": {"verification_timestamp_utc": "2026-08-30T12:00:00Z"},
    "inventory_aoss_free_queue": {"verification_timestamp_utc": "2026-08-30T12:00:00Z"},
}


def _read(rel: str) -> pd.DataFrame:
    return pd.read_parquet(_FIXTURE_CATALOG / rel)


@pytest.mark.skipif(not _FIXTURE_CATALOG.is_dir(), reason="fixture catalog missing")
def test_derived_artifacts_inventory_nodes_via_kedro_session():
    from kedro.framework.session import KedroSession
    from kedro.framework.startup import bootstrap_project

    bootstrap_project(_MEMBER_DIR)
    universe = _read("derived/inventory_universe/inventory_universe.parquet")
    core = _read("intermediate/core_packages_enumerated/core_packages_enumerated.parquet")
    pypi = _read("intermediate/pypi_universe/pypi_universe.parquet")
    mapping = _read("primary/pypi_conda_mapping/pypi_conda_mapping.parquet")
    priority = pd.DataFrame(
        [
            {
                "core_python_package_name": "widget",
                "P": "P9",
                "Rank": 1,
                "Score": 90,
                "Work": "Already packaged",
            }
        ]
    )
    with KedroSession.create(project_path=_MEMBER_DIR, runtime_params=_LOW_FLOOR) as session:
        catalog = session.load_context().catalog
        catalog.save("inventory_universe", universe)
        catalog.save("core_packages_enumerated", core)
        catalog.save("pypi_universe", pypi)
        catalog.save("pypi_conda_mapping", mapping)
        catalog.save("inventory_priority_assignments", priority)

        session.run(
            pipeline_name="derived_artifacts",
            from_nodes=["build_inventory_verified_packages"],
            to_nodes=["build_inventory_verified_packages"],
        )

        verified = catalog.load("inventory_verified_packages")
    assert isinstance(verified, pd.DataFrame) and not verified.empty
