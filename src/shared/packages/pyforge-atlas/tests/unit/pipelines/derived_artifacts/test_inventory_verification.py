"""Story 27.1 — verification set scale floors and hollow-set refusal."""

from __future__ import annotations

import pandas as pd
import pytest

from pyforge.atlas.pipelines.derived_artifacts.identity_export_contract import (
    GIST_COLUMNS,
    IDENTITY_COMPLETE_EXPORT_COLUMNS,
)
from pyforge.atlas.pipelines.derived_artifacts.inventory_verification import (
    DEFAULT_CORE_PACKAGES_ENUMERATED_FLOOR,
    DEFAULT_PYPI_UNIVERSE_FLOOR,
    HollowVerificationSetError,
    verification_sets,
)
from pyforge.atlas.pipelines.derived_artifacts.nodes import (
    build_inventory_aoss_free_queue,
    build_inventory_verified_packages,
)


def _low_floor_params() -> dict:
    return {
        "verification_sets": {"core_packages_enumerated_floor": 0, "pypi_universe_floor": 0},
        "inventory_verified_packages": {"verification_timestamp_utc": "2026-08-30T12:00:00Z"},
    }


def test_verification_sets_refuses_empty_pypi_universe():
    with pytest.raises(HollowVerificationSetError, match="hollow_pypi_universe"):
        verification_sets(
            pd.DataFrame([{"conda_name": "a"}]),
            pd.DataFrame(columns=["pypi_name"]),
            pd.DataFrame(columns=["pypi_name"]),
            {"verification_sets": {"core_packages_enumerated_floor": 0, "pypi_universe_floor": 1}},
        )


def test_verification_sets_refuses_sub_floor_core_packages():
    with pytest.raises(HollowVerificationSetError, match="hollow_core_packages_enumerated"):
        verification_sets(
            pd.DataFrame([{"conda_name": "only-one"}]),
            pd.DataFrame([{"pypi_name": "only-one"}]),
            pd.DataFrame(columns=["pypi_name"]),
            {"verification_sets": {"core_packages_enumerated_floor": 2, "pypi_universe_floor": 0}},
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
            {"verification_sets": {"core_packages_enumerated_floor": 1, "pypi_universe_floor": 1}},
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
            {"verification_sets": {"core_packages_enumerated_floor": 1, "pypi_universe_floor": 1}},
        )


def test_floors_count_after_norm_pkg():
    """Distinct raw values that normalize to one name count once toward the floor."""
    cf = pd.DataFrame([{"conda_name": "My_Pkg"}, {"conda_name": "my-pkg"}])
    pypi = pd.DataFrame([{"pypi_name": "widget"}])
    _, pypi_index, cf_or_pm = verification_sets(
        cf,
        pypi,
        pd.DataFrame(columns=["pypi_name"]),
        {"verification_sets": {"core_packages_enumerated_floor": 1, "pypi_universe_floor": 1}},
    )
    assert len(cf_or_pm) == 1
    assert "my-pkg" in cf_or_pm
    assert len(pypi_index) == 1


def test_gist_columns_are_subset_of_identity_complete_export_columns():
    export_cols = set(IDENTITY_COMPLETE_EXPORT_COLUMNS)
    missing = [c for c in GIST_COLUMNS if c not in export_cols]
    assert missing == [], f"GIST_COLUMNS not on export: {missing}"


def test_core_packages_enumerated_floor_key_moves_the_core_floor():
    core = pd.DataFrame([{"conda_name": f"c{i}"} for i in range(3)])
    pypi = pd.DataFrame([{"pypi_name": "widget"}])
    empty_mapping = pd.DataFrame(columns=["pypi_name"])
    cf, _, _ = verification_sets(
        core, pypi, empty_mapping, {"verification_sets": {"core_packages_enumerated_floor": 3}}
    )
    assert len(cf) == 3
    with pytest.raises(HollowVerificationSetError, match=r"3 normalized conda-forge core names \(floor 4\)"):
        verification_sets(core, pypi, empty_mapping, {"verification_sets": {"core_packages_enumerated_floor": 4}})


def test_default_floors_apply_when_the_block_is_absent():
    assert DEFAULT_CORE_PACKAGES_ENUMERATED_FLOOR == 30_000
    assert DEFAULT_PYPI_UNIVERSE_FLOOR == 1
    with pytest.raises(HollowVerificationSetError, match="floor 30000"):
        verification_sets(
            pd.DataFrame([{"conda_name": "numpy"}]),
            pd.DataFrame([{"pypi_name": "numpy"}]),
            pd.DataFrame(columns=["pypi_name"]),
            None,
        )


@pytest.mark.parametrize("key", ["cf_or_pm_floor", "core_floor"])
def test_unknown_floor_key_is_refused_not_silently_defaulted(key):
    with pytest.raises(ValueError, match=key):
        verification_sets(
            pd.DataFrame([{"conda_name": "numpy"}]),
            pd.DataFrame([{"pypi_name": "numpy"}]),
            pd.DataFrame(columns=["pypi_name"]),
            {"verification_sets": {key: 0}},
        )


@pytest.mark.parametrize(
    ("block", "named"),
    [
        (["core_packages_enumerated_floor"], "got list"),
        ("core_packages_enumerated_floor: 3", "got str"),
        (7, "got int"),
    ],
)
def test_a_non_mapping_verification_sets_block_is_a_named_error(block, named):
    with pytest.raises(ValueError, match=rf"params:verification_sets must be a mapping of floor keys .*{named}"):
        verification_sets(
            pd.DataFrame([{"conda_name": "numpy"}]),
            pd.DataFrame([{"pypi_name": "numpy"}]),
            pd.DataFrame(columns=["pypi_name"]),
            {"verification_sets": block},
        )


@pytest.mark.parametrize("key", ["core_packages_enumerated_floor", "pypi_universe_floor"])
@pytest.mark.parametrize("value", [None, "thirty thousand"])
def test_a_null_or_non_integer_floor_is_a_named_error(key, value):
    with pytest.raises(ValueError, match=rf"params:verification_sets\.{key} must be an integer, got {value!r}"):
        verification_sets(
            pd.DataFrame([{"conda_name": "numpy"}]),
            pd.DataFrame([{"pypi_name": "numpy"}]),
            pd.DataFrame(columns=["pypi_name"]),
            {"verification_sets": {key: value}},
        )
