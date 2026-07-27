"""Meta test — the wheel's and the conda package's dependency sets stay in sync.

``pyproject.toml`` (hatchling: wheel/sdist + pip-visible metadata) and
``pixi.toml`` (pixi-build-python: the ``.conda``) each spell warden's runtime
requirements independently, with no single source of truth between them. A
one-sided edit therefore ships a conda package whose requirement set silently
diverges from the wheel's — and it fails *late*, at import time on a user's
machine, not here.

This guard exists because that drift shipped: ``packageurl-python`` (imported
unconditionally by ``sbom.py``) was declared in ``pyproject.toml`` but missing
from ``pixi.toml``'s ``[package.run-dependencies]``. The ``.conda`` still
worked, but only by accident — ``cyclonedx-python-lib`` happens to require
``packageurl-python (>=0.11,<2)``, so it arrived as an undeclared transitive.
The moment cyclonedx dropped or re-bounded it, ``from packageurl import
PackageURL`` would fail on an install that resolved perfectly. deptry could
not catch it either: it reads ``pyproject.toml``, where the dep was present.

Sibling precedent: ``pyforge-marshal``'s ``tests/meta/test_manifest_sync.py``
asserts strict set equality. Warden cannot, because two of its run-deps are
deliberately conda-only (see ``_CONDA_ONLY``), so parity is asserted as mutual
containment modulo that allowlist instead.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]

# Run-deps with no ``pyproject.toml`` counterpart, and why each is legitimate:
#   python       — a conda-side interpreter pin; pyproject's ``requires-python``
#                  is its equivalent, expressed in different machinery.
#   deptry,
#   osv-scanner  — the scanning ENGINES (NFR1/NFR2/OD1). They are external
#                  executables invoked by subprocess, consumed from conda-forge
#                  feedstocks and never importable Python distributions, so they
#                  cannot be pip requirements. Their pins are guarded separately
#                  by test_engine_version_range_sync.py.
_CONDA_ONLY = frozenset({"python", "deptry", "osv-scanner"})


def _load(name: str) -> dict:
    return tomllib.loads((_PACKAGE_ROOT / name).read_text(encoding="utf-8"))


def _normalize(name: str) -> str:
    """PEP 503 name normalization — ``PyYAML`` and ``pyyaml`` are one dep."""
    return name.lower().replace("_", "-").replace(".", "-")


def _pyproject_deps() -> dict[str, SpecifierSet]:
    return {
        _normalize(req.name): req.specifier
        for req in (
            Requirement(spec)
            for spec in _load("pyproject.toml")["project"]["dependencies"]
        )
    }


def _pixi_run_deps() -> dict[str, str]:
    return {
        _normalize(name): str(spec)
        for name, spec in _load("pixi.toml")["package"]["run-dependencies"].items()
    }


def test_every_pyproject_dependency_is_a_conda_run_dependency():
    """The direction that caught the ``packageurl-python`` drift: anything the
    wheel requires, the ``.conda`` must require too — never left to arrive as
    somebody else's transitive."""
    missing = sorted(set(_pyproject_deps()) - set(_pixi_run_deps()))
    assert not missing, (
        "declared in pyproject.toml [project.dependencies] but absent from "
        f"pixi.toml [package.run-dependencies]: {missing}. The conda package "
        "would rely on these arriving transitively — add them to pixi.toml."
    )


def test_every_conda_run_dependency_is_declared_or_allowlisted():
    """The reverse direction: a conda-only run-dep must be a deliberate,
    documented one, so the ``.conda`` cannot quietly grow a requirement the
    wheel never gets."""
    undeclared = sorted(set(_pixi_run_deps()) - set(_pyproject_deps()) - _CONDA_ONLY)
    assert not undeclared, (
        "in pixi.toml [package.run-dependencies] but neither declared in "
        f"pyproject.toml nor allowlisted as conda-only: {undeclared}. Either "
        "add it to pyproject.toml or justify it in _CONDA_ONLY."
    )


def test_shared_dependencies_carry_equivalent_pins():
    """Same dep, same constraint on both sides. pixi spells 'unconstrained' as
    ``"*"`` where pyproject spells it as the empty specifier; those are the
    same statement, so ``"*"`` normalizes to empty before comparing."""
    pixi = _pixi_run_deps()
    drifted = {
        name: (str(specifier), pixi[name])
        for name, specifier in _pyproject_deps().items()
        if name in pixi
        and SpecifierSet("" if pixi[name] == "*" else pixi[name]) != specifier
    }
    assert not drifted, f"pin drift (pyproject, pixi): {drifted}"


def test_conda_package_version_matches_pyproject():
    assert (
        _load("pixi.toml")["package"]["version"]
        == _load("pyproject.toml")["project"]["version"]
    )


def test_engine_allowlist_is_not_a_loophole():
    """A guard that allowlisted everything would be vacuous. The conda-only
    escape hatch must stay confined to the interpreter and the two engines."""
    assert _CONDA_ONLY == {"python", "deptry", "osv-scanner"}
    assert _CONDA_ONLY.isdisjoint(_pyproject_deps())
