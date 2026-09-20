"""Story 16.1 — mason's own pixi env satisfies `cfe.py`'s import floor.

`[feature.pyforge-mason.dependencies]` must declare every floor dependency
that is not otherwise guaranteed, at the same version floors as the rest of
the repo (`truststore` from `[feature.python.dependencies]`,
`conda-forge-metadata` from `[feature.vuln-db.dependencies]`). A regression
here silently re-disables the `recipe` verb family in `mason doctor`.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from packaging.specifiers import SpecifierSet

from pyforge.mason.cfe import CFE_IMPORT_FLOOR, probe_import_floor

_CANONICAL_FLOOR_SOURCES: dict[str, tuple[str, str]] = {
    "truststore": ("python", "truststore"),
    "conda-forge-metadata": ("vuln-db", "conda-forge-metadata"),
}


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


def _pixi_data() -> dict[str, object]:
    pixi_toml = _repo_root() / "pixi.toml"
    with pixi_toml.open("rb") as stream:
        return tomllib.load(stream)


def _pyforge_mason_dependencies() -> dict[str, object]:
    data = _pixi_data()
    return data["feature"]["pyforge-mason"]["dependencies"]


def _canonical_floor(distribution: str) -> str:
    feature_name, key = _CANONICAL_FLOOR_SOURCES[distribution]
    data = _pixi_data()
    return str(data["feature"][feature_name]["dependencies"][key])


def test_pyforge_mason_dependencies_pin_cfe_import_floor_gaps():
    """Dropping either floor package from the env must fail loud, not silently
    re-disable `recipe` in `mason doctor`."""
    deps = _pyforge_mason_dependencies()
    for distribution in _CANONICAL_FLOOR_SOURCES:
        floor = _canonical_floor(distribution)
        assert distribution in deps, (
            f"[feature.pyforge-mason.dependencies] must declare {distribution!r} "
            f"to satisfy CFE_IMPORT_FLOOR — without it mason doctor reports "
            f"unavailable_verbs=('recipe',)"
        )
        assert SpecifierSet(str(deps[distribution])) == SpecifierSet(floor), (
            f"{distribution!r} floor in [feature.pyforge-mason.dependencies] must "
            f"match the repo-wide canonical floor {floor!r}, got "
            f"{deps[distribution]!r}"
        )


def test_pyforge_mason_dependencies_floor_pins_are_ranges_not_exact():
    """Match the repo's NFR-C1-style convention: a floor, not an exact pin."""
    deps = _pyforge_mason_dependencies()
    for distribution in _CANONICAL_FLOOR_SOURCES:
        specifiers = SpecifierSet(str(deps[distribution]))
        assert any(specifier.operator in (">=", ">") for specifier in specifiers), (
            f"{distribution!r} must use a minimum floor (>= or >), got {deps[distribution]!r}"
        )


def test_pyforge_mason_env_imports_every_cfe_import_floor_module():
    """Real-interpreter probe: every `CFE_IMPORT_FLOOR` import name must
    resolve in the pyforge-mason pixi env (the test runner's interpreter)."""
    probe_import_floor.cache_clear()
    result = probe_import_floor(sys.executable)
    assert result.interpreter == sys.executable
    assert result.missing == (), (
        "CFE_IMPORT_FLOOR modules missing from the pyforge-mason env: "
        f"{result.missing!r} (distribution names; import names are "
        f"{ {k: CFE_IMPORT_FLOOR[k] for k in result.missing}!r})"
    )
