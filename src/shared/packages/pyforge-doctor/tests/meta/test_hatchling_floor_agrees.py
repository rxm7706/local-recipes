"""Meta test -- one hatchling floor for every doctor build (Story 41.4, DW-1-1-3).

The wheel/sdist build reads ``pyproject.toml [build-system] requires``, the
conda build reads the package ``pixi.toml [package.host-dependencies]``, and
the dev environment reads the root ``pixi.toml``'s
``[feature.pyforge-doctor.dependencies]``. Three unconstrained-or-divergent
pins let the two builds resolve different hatchling versions silently; this
reds the moment any of the three drifts from the others.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

_PACKAGE_DIR = Path(__file__).resolve().parents[2]
try:
    _REPO_ROOT: Path | None = Path(__file__).resolve().parents[6]
except IndexError:
    _REPO_ROOT = None


def _load(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _pyproject_spec() -> str:
    requires = _load(_PACKAGE_DIR / "pyproject.toml")["build-system"]["requires"]
    matches = [r for r in requires if r.replace(" ", "").startswith("hatchling")]
    assert len(matches) == 1, f"expected one hatchling requirement, got {requires}"
    return matches[0].replace(" ", "").removeprefix("hatchling")


def test_package_builds_share_one_hatchling_floor():
    pyproject = _pyproject_spec()
    package_pixi = _load(_PACKAGE_DIR / "pixi.toml")["package"]["host-dependencies"]["hatchling"]
    assert pyproject.startswith(">="), f"pyproject.toml leaves hatchling without a floor: {pyproject!r}"
    assert package_pixi == pyproject, f"package pixi.toml hatchling {package_pixi!r} != pyproject.toml {pyproject!r}"


def test_root_feature_matches_the_package_floor():
    if _REPO_ROOT is None or not (_REPO_ROOT / "pixi.toml").is_file():
        pytest.skip("not running inside the local-recipes monorepo checkout")
    root = _load(_REPO_ROOT / "pixi.toml")["feature"]["pyforge-doctor"]["dependencies"]["hatchling"]
    assert root == _pyproject_spec(), f"root pixi.toml pyforge-doctor hatchling {root!r} != the package floor"
