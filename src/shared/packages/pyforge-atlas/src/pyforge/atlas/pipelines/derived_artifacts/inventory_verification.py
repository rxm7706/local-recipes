"""Verification-set scale floors for inventory exports (Story 27.1).

Floors are read from ``params:verification_sets``: ``core_packages_enumerated_floor``
(normalized conda-forge core names) and ``pypi_universe_floor`` (normalized PyPI
names). The PyPI-to-conda mapping carries no floor. Any other key in that block is
refused, so a misspelt or retired key (``cf_or_pm_floor``) never falls back to a
default unnoticed.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from pyforge.core.errors import PyforgeError

DEFAULT_CORE_PACKAGES_ENUMERATED_FLOOR = 30_000
DEFAULT_PYPI_UNIVERSE_FLOOR = 1
FLOOR_KEYS: frozenset[str] = frozenset({"core_packages_enumerated_floor", "pypi_universe_floor"})


class HollowVerificationSetError(PyforgeError, ValueError):
    """A Tier-0 verification set is empty or below its scale floor after ``norm_pkg``."""


def _floor_block(parameters: dict[str, Any] | None) -> dict[str, Any]:
    block = (parameters or {}).get("verification_sets") or {}
    unknown = sorted(set(block) - FLOOR_KEYS)
    if unknown:
        raise ValueError(
            f"params:verification_sets has unknown key(s) {', '.join(unknown)}; "
            f"known keys: {', '.join(sorted(FLOOR_KEYS))}"
        )
    return dict(block)


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

    block = _floor_block(parameters)
    pypi_floor = int(block.get("pypi_universe_floor", DEFAULT_PYPI_UNIVERSE_FLOOR))
    core_floor = int(block.get("core_packages_enumerated_floor", DEFAULT_CORE_PACKAGES_ENUMERATED_FLOOR))

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
