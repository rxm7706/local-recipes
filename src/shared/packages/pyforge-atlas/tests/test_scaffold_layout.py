"""Story A1 `kedro-test` gate: scaffold-layout invariants (AC-5/AC-6/AC-7)."""
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

MEMBER_DIR = Path(__file__).resolve().parents[1]

# Run-deps with no [project.dependencies] counterpart. `python` is the conda-side
# interpreter pin; pyproject states the same floor as `requires-python`.
CONDA_ONLY_RUN_DEPS = frozenset({"python"})


def test_member_dirs_exist():
    assert (MEMBER_DIR / "conf" / "base" / "catalog.yml").is_file()
    assert (MEMBER_DIR / "src" / "pyforge" / "atlas").is_dir()


def test_pep420_no_namespace_init():
    # PEP 420 implicit namespace package, warden-identical: there must be NO
    # src/pyforge/__init__.py (AC-7 tightening).
    assert not (MEMBER_DIR / "src" / "pyforge" / "__init__.py").exists()
    assert (MEMBER_DIR / "src" / "pyforge" / "atlas" / "__init__.py").is_file()


def test_pyproject_declares_hatchling_and_gate_extra():
    with open(MEMBER_DIR / "pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    assert pyproject["build-system"]["build-backend"] == "hatchling.build"
    assert "hatchling" in pyproject["build-system"]["requires"]
    # AC-8: pyforge-warden is the optional [gate] extra — the only
    # cross-package code dependency edge.
    gate = pyproject["project"]["optional-dependencies"]["gate"]
    assert gate == ["pyforge-warden"]
    # AC-7: Kedro resolves the dotted namespace package.
    assert pyproject["tool"]["kedro"]["package_name"] == "pyforge.atlas"
    # AC-6: wheel target ships the shared pyforge namespace root.
    assert pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == [
        "src/pyforge"
    ]


def _load(name: str) -> dict:
    with open(MEMBER_DIR / name, "rb") as f:
        return tomllib.load(f)


def _norm(name: str) -> str:
    """PEP 503 name normalization, so PyYAML and pyyaml compare equal."""
    return name.lower().replace("_", "-").replace(".", "-")


def _project_deps() -> dict[str, SpecifierSet]:
    return {
        _norm(req.name): req.specifier
        for req in (
            Requirement(s) for s in _load("pyproject.toml")["project"]["dependencies"]
        )
    }


def _run_deps() -> dict[str, str]:
    return {
        _norm(n): str(s)
        for n, s in _load("pixi.toml")["package"]["run-dependencies"].items()
    }


# AUD-ATLAS-010 made both manifests dependency-complete, which left 23 pins
# hand-duplicated across them with no single source of truth. These four guards
# are that source of truth: without them a one-sided edit ships a wheel and a
# .conda with different requirement sets, and the failure surfaces as an
# ImportError on a consumer's machine rather than here.
def test_run_dependencies_cover_every_project_dependency():
    missing = sorted(set(_project_deps()) - set(_run_deps()))
    assert not missing, (
        "declared in pyproject.toml [project.dependencies] but absent from "
        f"pixi.toml [package.run-dependencies]: {missing} — the built .conda "
        "would rely on these arriving as somebody else's transitive."
    )


def test_run_dependencies_add_nothing_undeclared():
    extra = sorted(set(_run_deps()) - set(_project_deps()) - CONDA_ONLY_RUN_DEPS)
    assert not extra, (
        "in pixi.toml [package.run-dependencies] but not in pyproject.toml "
        f"[project.dependencies]: {extra}"
    )


def test_shared_dependency_pins_agree():
    run_deps = _run_deps()
    drifted = {
        name: (str(spec), run_deps[name])
        for name, spec in _project_deps().items()
        if name in run_deps
        and SpecifierSet("" if run_deps[name] == "*" else run_deps[name]) != spec
    }
    assert not drifted, f"pin drift (pyproject, pixi): {drifted}"


def test_warden_is_never_a_conda_run_dependency():
    """AC-8: warden stays the optional [gate] extra. Baking it into the .conda
    would make that extra mandatory for external consumers."""
    assert "pyforge-warden" not in _run_deps()


def test_conda_package_version_matches_pyproject():
    assert (
        _load("pixi.toml")["package"]["version"]
        == _load("pyproject.toml")["project"]["version"]
    )
