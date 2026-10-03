"""Story 27.1 — verification set scale floors and hollow-set refusal."""

from __future__ import annotations

import pandas as pd
import pytest

from pyforge.atlas.pipelines.derived_artifacts.identity_export_contract import (
    GIST_COLUMNS,
    IDENTITY_COMPLETE_EXPORT_COLUMNS,
)
from pyforge.atlas.pipelines.derived_artifacts.inventory_verification import (
    HollowVerificationSetError,
    verification_sets,
)
from pyforge.atlas.pipelines.derived_artifacts.nodes import (
    build_inventory_aoss_free_queue,
    build_inventory_verified_packages,
)


def _low_floor_params() -> dict:
    return {
        "verification_sets": {"cf_or_pm_floor": 0, "pypi_universe_floor": 0},
        "inventory_verified_packages": {"verification_timestamp_utc": "2026-08-30T12:00:00Z"},
    }


def test_verification_sets_refuses_empty_pypi_universe():
    with pytest.raises(HollowVerificationSetError, match="hollow_pypi_universe"):
        verification_sets(
            pd.DataFrame([{"conda_name": "a"}]),
            pd.DataFrame(columns=["pypi_name"]),
            pd.DataFrame(columns=["pypi_name"]),
            {"verification_sets": {"cf_or_pm_floor": 0, "pypi_universe_floor": 1}},
        )


def test_verification_sets_refuses_sub_floor_core_packages():
    with pytest.raises(HollowVerificationSetError, match="hollow_core_packages_enumerated"):
        verification_sets(
            pd.DataFrame([{"conda_name": "only-one"}]),
            pd.DataFrame([{"pypi_name": "only-one"}]),
            pd.DataFrame(columns=["pypi_name"]),
            {"verification_sets": {"cf_or_pm_floor": 2, "pypi_universe_floor": 0}},
        )


def test_verification_sets_refuses_empty_core_despite_large_mapping():
    """Parselmouth mapping names must not satisfy the core conda-forge floor."""
    mapping = pd.DataFrame([{"pypi_name": f"p{i}"} for i in range(30_000)])
    with pytest.raises(HollowVerificationSetError, match="hollow_core_packages_enumerated"):
        verification_sets(
            pd.DataFrame(columns=["conda_name"]),
            pd.DataFrame([{"pypi_name": "widget"}]),
            mapping,
            {},
        )


def test_build_inventory_verified_packages_propagates_hollow_error():
    universe = pd.DataFrame(
        [{"core_python_package_name": "x", "package_input_names": ["x"], "sources": [], "role": "N/A"}]
    )
    with pytest.raises(HollowVerificationSetError):
        build_inventory_verified_packages(
            universe,
            pd.DataFrame(columns=["conda_name"]),
            pd.DataFrame(columns=["pypi_name"]),
            pd.DataFrame(columns=["pypi_name"]),
            pd.DataFrame(columns=["core_python_package_name", "P"]),
            {"verification_sets": {"cf_or_pm_floor": 1, "pypi_universe_floor": 1}},
        )


def test_build_inventory_aoss_free_queue_propagates_hollow_error():
    with pytest.raises(HollowVerificationSetError):
        build_inventory_aoss_free_queue(
            pd.DataFrame([{"pypi_name": "a"}]),
            pd.DataFrame(columns=["conda_name"]),
            pd.DataFrame(columns=["pypi_name"]),
            pd.DataFrame(columns=["pypi_name"]),
            pd.DataFrame(columns=["core_python_package_name"]),
            pd.DataFrame(columns=["core_python_package_name"]),
            {"verification_sets": {"cf_or_pm_floor": 1, "pypi_universe_floor": 1}},
        )


def test_floors_count_after_norm_pkg():
    """Distinct raw values that normalize to one name count once toward the floor."""
    cf = pd.DataFrame([{"conda_name": "My_Pkg"}, {"conda_name": "my-pkg"}])
    pypi = pd.DataFrame([{"pypi_name": "widget"}])
    _, pypi_index, cf_or_pm = verification_sets(
        cf,
        pypi,
        pd.DataFrame(columns=["pypi_name"]),
        {"verification_sets": {"cf_or_pm_floor": 1, "pypi_universe_floor": 1}},
    )
    assert len(cf_or_pm) == 1
    assert "my-pkg" in cf_or_pm
    assert len(pypi_index) == 1


def test_gist_columns_are_subset_of_identity_complete_export_columns():
    export_cols = set(IDENTITY_COMPLETE_EXPORT_COLUMNS)
    missing = [c for c in GIST_COLUMNS if c not in export_cols]
    assert missing == [], f"GIST_COLUMNS not on export: {missing}"
