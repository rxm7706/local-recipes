#!/usr/bin/env python3
"""Story 27.1 / DW-FU-17-1 — inventory nodes + metrics actuator from fixture catalog."""

from __future__ import annotations

import hashlib
import importlib.util
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ATLAS_SRC = _REPO_ROOT / "src/shared/packages/pyforge-atlas/src"
if str(_ATLAS_SRC) not in sys.path:
    sys.path.insert(0, str(_ATLAS_SRC))

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures/inventory_universe/catalog"
METRICS_PATH = Path(__file__).resolve().parent.parent / (
    "conda-forge-packaging-inventory-operations_metrics.py"
)
SNAPSHOT_MD = Path(__file__).resolve().parent / "fixtures/inventory_universe/expected_report.md.sha256"
SNAPSHOT_CSV = Path(__file__).resolve().parent / "fixtures/inventory_universe/expected_report.csv.sha256"
_LOW_FLOOR = {
    "verification_sets": {"cf_or_pm_floor": 0, "pypi_universe_floor": 0},
    "inventory_verified_packages": {"verification_timestamp_utc": "2026-08-30T12:00:00Z"},
    "inventory_aoss_free_queue": {"verification_timestamp_utc": "2026-08-30T12:00:00Z"},
}


def _load_metrics():
    spec = importlib.util.spec_from_file_location("cfpio_metrics", METRICS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _read_fixture(rel: str) -> pd.DataFrame:
    return pd.read_parquet(FIXTURE_ROOT / rel)


@pytest.mark.skipif(not FIXTURE_ROOT.is_dir(), reason="fixture catalog missing")
def test_inventory_nodes_then_metrics_actuator_matches_snapshot(tmp_path: Path):
    from pyforge.atlas.pipelines.derived_artifacts.nodes import (
        build_inventory_aoss_free_queue,
        build_inventory_verified_packages,
    )

    catalog_out = tmp_path / "catalog"
    shutil.copytree(FIXTURE_ROOT, catalog_out)

    universe = _read_fixture("derived/inventory_universe/inventory_universe.parquet")
    core = _read_fixture("intermediate/core_packages_enumerated/core_packages_enumerated.parquet")
    pypi = _read_fixture("intermediate/pypi_universe/pypi_universe.parquet")
    mapping = _read_fixture("primary/pypi_conda_mapping/pypi_conda_mapping.parquet")
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
    aoss_src = pd.DataFrame([{"pypi_name": "aossfreepkg"}])
    jfrog = pd.DataFrame(columns=["core_python_package_name"])
    conda_maint = pd.DataFrame(columns=["core_python_package_name"])

    verified = build_inventory_verified_packages(
        universe, core, pypi, mapping, priority, _LOW_FLOOR
    )
    queue = build_inventory_aoss_free_queue(
        aoss_src, core, pypi, mapping, jfrog, conda_maint, _LOW_FLOOR
    )

    verified_path = (
        catalog_out / "derived/inventory_verified_packages/inventory_verified_packages.parquet"
    )
    queue_path = catalog_out / "derived/inventory_aoss_free_queue/inventory_aoss_free_queue.parquet"
    verified.to_parquet(verified_path, index=False)
    queue.to_parquet(queue_path, index=False)

    metrics = _load_metrics()
    md_path = tmp_path / "report.md"
    csv_path = tmp_path / "report.csv"
    argv = [
        "metrics",
        "--live-catalog",
        str(catalog_out),
        "--output-csv",
        str(csv_path),
        "--output-md",
        str(md_path),
        "--skip-revised-prompt",
    ]
    from unittest import mock

    with mock.patch.object(sys, "argv", argv):
        rc = metrics.main()
    assert rc == 0
    assert csv_path.is_file()
    md_digest = hashlib.sha256(md_path.read_bytes()).hexdigest()
    csv_digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    assert md_digest == SNAPSHOT_MD.read_text(encoding="utf-8").strip()
    assert csv_digest == SNAPSHOT_CSV.read_text(encoding="utf-8").strip()
