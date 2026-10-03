"""Verification-set scale floors for inventory exports (Story 27.1)."""

from __future__ import annotations

from typing import Any

import pandas as pd

DEFAULT_CF_OR_PM_FLOOR = 30_000
DEFAULT_PYPI_UNIVERSE_FLOOR = 1


class HollowVerificationSetError(ValueError):
    """A Tier-0 verification set is empty or below its scale floor after ``norm_pkg``."""


def _floor_override(parameters: dict[str, Any] | None, key: str, default: int) -> int:
    params = parameters or {}
    block = params.get("verification_sets") or {}
    if key not in block and key == "core_packages_enumerated_floor":
        raw = block.get("cf_or_pm_floor", default)
    else:
        raw = block.get(key, default)
    return int(raw)


def verification_sets(
    core_packages_enumerated: pd.DataFrame,
    pypi_universe: pd.DataFrame,
    pypi_conda_mapping: pd.DataFrame,
    parameters: dict[str, Any] | None = None,
) -> tuple[set[str], set[str], set[str]]:
    """Build normalized verification sets and refuse hollow conda-forge / PyPI inputs."""
    from . import nodes as _nodes

    cf_packages = _nodes._names_from_column(core_packages_enumerated, "conda_name")
    pypi_index = _nodes._names_from_column(pypi_universe, "pypi_name")
    parselmouth_pypi = _nodes._names_from_column(pypi_conda_mapping, "pypi_name")
    cf_or_pm = cf_packages | parselmouth_pypi

    pypi_floor = _floor_override(parameters, "pypi_universe_floor", DEFAULT_PYPI_UNIVERSE_FLOOR)
    core_floor = _floor_override(
        parameters, "core_packages_enumerated_floor", DEFAULT_CF_OR_PM_FLOOR
    )

    if len(pypi_index) < pypi_floor:
        raise HollowVerificationSetError(
            f"hollow_pypi_universe: {len(pypi_index)} normalized PyPI names (floor {pypi_floor})"
        )
    if len(cf_packages) < core_floor:
        raise HollowVerificationSetError(
            f"hollow_core_packages_enumerated: {len(cf_packages)} normalized "
            f"conda-forge core names (floor {core_floor})"
        )
    return cf_packages, pypi_index, cf_or_pm
