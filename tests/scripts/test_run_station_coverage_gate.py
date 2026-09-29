"""Driver-level contracts for scripts/run_station_coverage_gate.py (Story 19.3).

Added 2026-09-20 (doctor Story 24.1 review pass, spec-coverage-gate-independence
CAP-1): this driver's evaluator import was repointed the same way as
scripts/coverage_gates_ci.py (a `_SCRIPTS_DIR` sys.path insert + `from
coverage_gate import (...)`), but unlike that sibling -- covered by
test_coverage_gates_ci_driver.py's `_load_driver()` fixture -- nothing loaded
or executed this module, so a future change to `_SCRIPTS_DIR`'s computation
could silently break every `pyforge-<station>-test-coverage` pixi task (all
eight stations) with zero automated signal. Mirrors
test_coverage_gates_ci_driver.py's own `_load_driver()` shape.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DRIVER = REPO / "scripts" / "run_station_coverage_gate.py"


def _load_driver():
    spec = importlib.util.spec_from_file_location("run_station_coverage_gate", DRIVER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def driver():
    return _load_driver()


def test_module_loads_and_exposes_main(driver):
    assert callable(driver.main)


def test_module_resolves_the_moved_evaluator(driver):
    """The `from coverage_gate import (...)` repoint (CAP-1) actually landed --
    these names come from scripts/coverage_gate.py, not a stale in-package copy."""
    assert callable(driver.evaluate_coverage_payload)
    assert callable(driver.package_root)
    assert callable(driver.package_src)
    assert callable(driver.thresholds_for)


def test_suite_test_paths_maps_unit_to_unit_and_meta(driver, tmp_path: Path):
    root = tmp_path / "pkg"
    (root / "tests" / "unit").mkdir(parents=True)
    (root / "tests" / "meta").mkdir(parents=True)
    assert driver._suite_test_paths(root, "unit") == [
        root / "tests" / "unit",
        root / "tests" / "meta",
    ]
    assert driver._suite_test_paths(root, "integration") == []


def test_main_rejects_an_unknown_suite(driver):
    assert driver.main(["--station", "marshal", "--suites", "bogus"]) == 2
