"""Story 23.4 — build_inventory_aoss_free_queue parity vs legacy reference."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import pandas as pd

from pyforge.atlas.pipelines.derived_artifacts.nodes import (
    _INVENTORY_AOSS_FREE_QUEUE_COLUMNS,
    build_inventory_aoss_free_queue,
    norm_pkg,
)

_FIXED_TS = "2026-08-30T12:00:00Z"
_PARAMS = {"inventory_verified_packages": {"verification_timestamp_utc": _FIXED_TS}}
_AOSS_FREE_QUEUE_REASON = "On PyPI, not on conda-forge, not in CDO consumption (GAOSS-Free)"


def _write_aoss_free_queue_ref(
    path: Path,
    aoss_free_names: set[str],
    universe_names: set[str],
    timestamp: str,
) -> list[str]:
    queue = sorted(aoss_free_names - universe_names)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["Package_Name", "Reason", "Verification_Timestamp_UTC"],
        )
        w.writeheader()
        for pkg in queue:
            w.writerow(
                {
                    "Package_Name": pkg,
                    "Reason": _AOSS_FREE_QUEUE_REASON,
                    "Verification_Timestamp_UTC": timestamp,
                }
            )
    return queue


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
    enterprise_jfrog_consumption = pd.DataFrame([{"core_python_package_name": n} for n in universe_jfrog])
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

    cf_or_pm = {norm_pkg(n) for n in cf_names}
    pypi_verified = {norm_pkg(n): True for n in pypi_names}
    aoss_free = {norm_pkg(n) for n in aoss_names}
    aoss_free_candidates = {pkg for pkg in aoss_free if pypi_verified.get(pkg, False) and pkg not in cf_or_pm}
    must_keep = {norm_pkg(n) for n in universe_jfrog} | {norm_pkg(n) for n in universe_conda}

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "queue.csv"
        queue = _write_aoss_free_queue_ref(path, aoss_free_candidates, must_keep, _FIXED_TS)
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
