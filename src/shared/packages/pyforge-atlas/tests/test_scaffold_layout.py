"""Story A1 `kedro-test` gate: scaffold-layout invariants (AC-5/AC-6/AC-7)."""
import tomllib
from pathlib import Path

MEMBER_DIR = Path(__file__).resolve().parents[1]


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
