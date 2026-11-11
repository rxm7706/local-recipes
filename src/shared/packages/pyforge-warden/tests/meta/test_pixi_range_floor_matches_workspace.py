"""Meta test -- the fix-PR solver's pixi range floor is the workspace's
``requires-pixi`` floor (Story 14.4, WAR-D-R1).

Split out of ``test_engine_version_range_sync.py`` by Story 27.1 (a relay of
``spec-pyforge-steward:CAP-175``): this guard reads the repository root's
``pixi.toml``, outside the package, so it runs in the live-tree half; the
package-local range guards stay in the package half. A missing root
``pixi.toml`` is a failure here, never a skip -- the half runs only where the
tree is."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from packaging.specifiers import SpecifierSet

import pyforge.warden
from pyforge.warden.engines import PIXI_VERSION_RANGE

pytestmark = pytest.mark.live_tree

_PACKAGE_FILE = pyforge.warden.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
# .../src/pyforge/warden/__init__.py -> the package root (four directories up).
PACKAGE_ROOT = Path(_PACKAGE_FILE).resolve().parent.parent.parent.parent
# .../src/shared/packages/pyforge-warden -> the repo root, whose pixi.toml
# carries the workspace's ``requires-pixi`` floor (Story 14.4).
ROOT_PIXI_TOML = PACKAGE_ROOT.parents[3] / "pixi.toml"


def _floor(specifiers: SpecifierSet) -> list[str]:
    return [spec.version for spec in specifiers if spec.operator == ">="]


def test_pixi_range_floor_is_the_requires_pixi_floor():
    """Story 14.4 (WAR-D-R1): the fix-PR solver's ``PIXI_VERSION_RANGE`` and
    the root ``pixi.toml``'s ``requires-pixi`` move together -- a requires-pixi
    bump without the range (or the reverse) reds here."""
    from packaging.version import Version

    with ROOT_PIXI_TOML.open("rb") as stream:
        requires_pixi = SpecifierSet(tomllib.load(stream)["workspace"]["requires-pixi"])
    (workspace_floor,) = _floor(requires_pixi)
    assert _floor(PIXI_VERSION_RANGE) == [workspace_floor], (
        f"engines.py's PIXI_VERSION_RANGE ({PIXI_VERSION_RANGE}) and pixi.toml's "
        f"requires-pixi ({requires_pixi}) have drifted apart -- retest the "
        "fix-PR solver on the new pixi and edit both together"
    )
    assert Version(workspace_floor) in PIXI_VERSION_RANGE
