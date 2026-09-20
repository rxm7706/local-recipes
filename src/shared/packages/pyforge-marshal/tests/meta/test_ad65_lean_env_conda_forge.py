"""Meta test -- NFR-A2 lean-env conda-forge provisioning (Story 12.3).

The ``pyforge-marshal`` pixi environment is deliberately lean
(``no-default-feature = true``) and every runtime dependency in the member
``pixi.toml`` resolves from conda-forge via pixi-build-python -- there is no
``pip:``/PyPI run-dependency surface on the package itself. Story 12.1 wired
the copier pin; this guard catches a future drift back to PyPI-only deps that
would break air-gapped installs.

This is a STATIC manifest check, not a network probe: the repo's own packaging
discipline (member ``[package.run-dependencies]`` + root env feature) is the
oracle.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pyforge.marshal

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_ROOT = Path(_PACKAGE_FILE).resolve().parent.parent.parent.parent
MEMBER_PIXI = PACKAGE_ROOT / "pixi.toml"
ROOT_PIXI = PACKAGE_ROOT.parent.parent.parent.parent / "pixi.toml"


def _member_run_dependencies() -> dict[str, object]:
    with MEMBER_PIXI.open("rb") as stream:
        data = tomllib.load(stream)
    return data["package"]["run-dependencies"]


def test_member_pixi_run_dependencies_contain_no_pip_prefixes():
    run_deps = _member_run_dependencies()
    pip_like = [
        name for name in run_deps if isinstance(name, str) and (name.startswith("pip:") or name.startswith("pypi:"))
    ]
    assert not pip_like, f"pip/pypi run-dependencies forbidden for air-gap lean env: {pip_like}"


def test_root_env_pyforge_marshal_is_lean_no_default_feature():
    with ROOT_PIXI.open("rb") as stream:
        data = tomllib.load(stream)
    env = data["environments"]["pyforge-marshal"]
    assert env.get("no-default-feature") is True, (
        "pyforge-marshal env must stay lean (no-default-feature = true) for air-gap installs"
    )
    assert env.get("features") == ["pyforge-marshal"]
