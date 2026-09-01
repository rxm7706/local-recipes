"""Story 23.4 — build_inventory_aoss_free_queue parity vs metrics.py."""

from __future__ import annotations

import csv
import importlib.util
import sys
import tempfile
from pathlib import Path

import pandas as pd

from pyforge.atlas.pipelines.derived_artifacts.nodes import (
    _INVENTORY_AOSS_FREE_QUEUE_COLUMNS,
    build_inventory_aoss_free_queue,
)

_REPO_ROOT = Path(__file__).resolve().parents[7]
_METRICS_SCRIPT = _REPO_ROOT / "scripts" / "conda-forge-packaging-inventory-operations_metrics.py"

_FIXED_TS = "2026-08-30T12:00:00Z"
_PARAMS = {"inventory_verified_packages": {"verification_timestamp_utc": _FIXED_TS}}


def _load_metrics_module():
    spec = importlib.util.spec_from_file_location("metrics_ref_aoss", _METRICS_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["metrics_ref_aoss"] = mod
    spec.loader.exec_module(mod)
    return mod


METRICS = _load_metrics_module()


def _run_both(
    *,
    aoss_names: list[str],
    pypi_names: list[str],
    cf_names: list[str],
    universe_jfrog: list[str],
    universe_conda: list[str],
) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    discovery_aoss_free_python_raw = pd.DataFrame([{"pypi_name": n} for n in aoss_names])
    core_packages_enumerated = pd.DataFrame([{"conda_name": n} for n in cf_names])
    pypi_universe = pd.DataFrame([{"pypi_name": n} for n in pypi_names])
    pypi_conda_mapping = pd.DataFrame(columns=["pypi_name"])
    enterprise_jfrog_consumption = pd.DataFrame(
        [{"core_python_package_name": n} for n in universe_jfrog]
    )
    enterprise_conda_maintainers = pd.DataFrame(
        [
            {
                "core_python_package_name": n,
                "role": "Maintainer",
                "feedstock_slug": "x",
                "repository_source": "CDO-ENT-CONDA",
            }
            for n in universe_conda
        ]
    )

    out = build_inventory_aoss_free_queue(
        discovery_aoss_free_python_raw,
        core_packages_enumerated,
        pypi_universe,
        pypi_conda_mapping,
        enterprise_jfrog_consumption,
        enterprise_conda_maintainers,
        _PARAMS,
    )

    cf_or_pm = {METRICS.norm_pkg(n) for n in cf_names}
    pypi_verified = {METRICS.norm_pkg(n): True for n in pypi_names}
    aoss_free = {METRICS.norm_pkg(n) for n in aoss_names}
    aoss_free_candidates = {
        pkg for pkg in aoss_free if pypi_verified.get(pkg, False) and pkg not in cf_or_pm
    }
    must_keep = {METRICS.norm_pkg(n) for n in universe_jfrog} | {METRICS.norm_pkg(n) for n in universe_conda}

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "queue.csv"
        queue = METRICS.write_aoss_free_queue(path, aoss_free_candidates, must_keep, _FIXED_TS)
        with path.open(encoding="utf-8") as f:
            ref_rows = list(csv.DictReader(f))

    assert queue == sorted(aoss_free_candidates - must_keep)
    return out, ref_rows


def test_aoss_free_eligible_row_appears_with_literal_reason():
    out, ref = _run_both(
        aoss_names=["eligible-pkg"],
        pypi_names=["eligible-pkg"],
        cf_names=[],
        universe_jfrog=[],
        universe_conda=[],
    )
    assert list(out.columns) == list(_INVENTORY_AOSS_FREE_QUEUE_COLUMNS)
    assert len(out) == 1
    assert out.iloc[0]["Package_Name"] == "eligible-pkg"
    assert out.iloc[0]["Reason"] == "On PyPI, not on conda-forge, not in CDO consumption (GAOSS-Free)"
    assert out.to_dict(orient="records") == ref


def test_aoss_listed_but_in_jfrog_universe_is_excluded():
    out, ref = _run_both(
        aoss_names=["in-universe-pkg"],
        pypi_names=["in-universe-pkg"],
        cf_names=[],
        universe_jfrog=["in-universe-pkg"],
        universe_conda=[],
    )
    assert out.empty
    assert ref == []


def test_aoss_listed_but_in_conda_universe_is_excluded():
    out, ref = _run_both(
        aoss_names=["conda-universe-pkg"],
        pypi_names=["conda-universe-pkg"],
        cf_names=[],
        universe_jfrog=[],
        universe_conda=["conda-universe-pkg"],
    )
    assert out.empty
    assert ref == []


def test_not_on_pypi_aoss_name_is_excluded():
    out, ref = _run_both(
        aoss_names=["not-on-pypi"],
        pypi_names=[],
        cf_names=[],
        universe_jfrog=[],
        universe_conda=[],
    )
    assert out.empty
    assert ref == []


def test_on_conda_forge_aoss_name_is_excluded():
    out, ref = _run_both(
        aoss_names=["already-on-cf"],
        pypi_names=["already-on-cf"],
        cf_names=["already-on-cf"],
        universe_jfrog=[],
        universe_conda=[],
    )
    assert out.empty
    assert ref == []


def test_done_checkpoint_matches_write_aoss_free_queue():
    out, ref = _run_both(
        aoss_names=["eligible-pkg", "in-universe-pkg", "not-on-pypi"],
        pypi_names=["eligible-pkg", "in-universe-pkg"],
        cf_names=[],
        universe_jfrog=["in-universe-pkg"],
        universe_conda=[],
    )
    assert out.to_dict(orient="records") == ref
