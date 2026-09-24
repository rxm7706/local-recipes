"""Structural contract -- CAP-3 of
``docs/governance/spec-coverage-gate-independence/SPEC.md`` (doctor Story
24.2).

Charter §5 -- the outcome/mechanism rule ("the hand that builds is never the
gate that judges") -- is why this contract lives in Doctor's OWN package
even though it also judges Doctor's own tree: Doctor is the Smith Charter
§6 already names as the Marshal's judge (*"the Doctor holds the verdict on
the Marshal's conformance -- the one station that would otherwise grade
itself,"* ratified 2026-07-28, ruled BROADLY 2026-09-14 to reach *any* check
that can red a station's own pull request, not only the three practices
named at ratification). Doctor's ``sources/marshal.py`` is the independence
exemplar this Spec's CAP-1 already copied; this module is the same shape
applied fleet-wide and enforced as a build-breaking test rather than an
advisory Finding -- Doctor is constitutionally advisory
(``sources/*.py`` Findings never gate a PR by themselves), so this
contract intentionally lives in ``tests/meta/`` and not in ``sources/``.

**The defect this closes.** ``pyforge/marshal/coverage_gate.py`` shipped
inside the marshal package for weeks -- the evaluator for a fleet-wide CI
gate governing all eight stations, marshal included -- and nothing asked
whether a station's own package evaluated that same station's own gate.
Doctor Story 24.1 (CAP-1/CAP-2) moved the evaluator and its thresholds to
``scripts/coverage_gate.py`` / ``docs/governance/coverage-thresholds.toml``,
outside every ``pyforge.<station>`` package, and added a MARSHAL-SCOPED
regression test (``pyforge-marshal/tests/meta/test_ad3_ad4_import_linter.py
::test_old_coverage_gate_module_path_resolves_nowhere``) proving the old
in-package import path no longer resolves. That test is necessarily
narrow -- it can only prove marshal never reintroduces ITS OWN copy. CAP-3
asks for the general case: reintroducing this SHAPE, in ANY of the eight
stations, must fail a test structurally -- not wait for a future audit to
notice a ninth station did the identical thing. This module is that
general contract.

**What "structurally" means here.** Every ``pyforge-<station>`` package's
own ``src/pyforge/<station>/`` tree is scanned (all eight stations Epic 24
treats alike -- see ``_EIGHT_STATIONS`` below -- Doctor's own tree
included; there is no legitimate reason for Doctor to define or import the
evaluator either) for a module that EITHER:

* **defines** the evaluator -- a file named ``coverage_gate.py`` (or a
  ``coverage_gate/`` package directory, ``__init__.py`` or not) anywhere
  under a station's ``src/pyforge/<station>/`` tree -- deliberately not
  restricted to a direct child: a nested reintroduction is the identical
  violation one directory deeper, and the marshal shim this closes is one
  instance of the shape, not its only legal position; or
* **imports** it -- any ``import``/``from ... import`` statement, absolute
  or relative, naming a module whose last dotted component is
  ``coverage_gate``, OR a dynamic ``importlib.import_module(...)``/
  ``__import__(...)`` call whose string argument's last dotted component
  is ``coverage_gate`` (a station package importing the relocated
  ``scripts/coverage_gate.py`` as a library -- statically or dynamically
  -- would be the same class of violation wearing a different hat: the
  eight ``pyforge-<station>-coverage-gate`` pixi tasks and
  ``coverage-gates.yml`` invoke it as a subprocess CLI, never as an
  import).

``pyforge-core`` and ``pyforge-testing-kit`` are excluded from the scan
roster: neither has its own ``pyforge-<station>-coverage-gate`` pixi task
(the eight named in ``_EIGHT_STATIONS`` are the complete roster
``coverage-gates.yml`` gates), so neither is a "station" in this contract's
sense -- CAP-3's own text scopes the prohibition to ``pyforge.<station>``
modules, and neither package is one.

**Non-vacuous proof, per CAP-3's own Given/When/Then.** ``pytest``'s
``tmp_path`` fixture builds a throwaway ``pyforge.<station>.coverage_gate``
shim (parametrized across all eight stations, not just marshal) in a temp
tree structurally identical to ``src/shared/packages/pyforge-<station>/
src/pyforge/<station>/`` and proves the scan flags it, then proves the
REAL, current (moved) repo tree scans clean -- mirroring
``test_no_warden_import.py``'s "guard fires on synthetic violation, guard
is silent on the real tree" style, applied fleet-wide the way
``pyforge-core``'s ``test_process_sole_ownership.py`` applies its own
subprocess guard fleet-wide.

**Divergence from Doctor's own sibling meta tests, deliberate.** Every
OTHER file in this directory (``test_no_warden_import.py``,
``test_atlas_sole_mcp_import.py``, ...) scans the INSTALLED
``pyforge.doctor`` package via ``pyforge.doctor.__file__``, because they
only ever need to see Doctor's own tree. This module instead scans SOURCE
trees (reads files from disk, ``pyforge-core``'s
``tests/meta/conftest.py`` convention) because it must reach the other
seven stations' trees too -- ``pyforge-doctor`` does not depend on or
install them, so there is no installed-package path to them at all. A
second, narrower copy of this same check lives in ``pyforge-core``'s own
``tests/meta/`` (see that file's docstring) purely so CI runs it on a PR
that touches only one non-doctor, non-marshal station: this package's own
CI job triggers on Doctor's own changed path, which such a PR never
touches; ``pyforge-core-test`` already runs on any single-station change
(Story 52.2), so it is the only job guaranteed to catch that case. Keep
both copies' violation-detection logic in sync when either changes; this
file stays the canonical, fully-documented, exhaustively-tested contract.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# tests/meta/test_x.py -> parents[3] is src/shared/packages/ (mirrors
# pyforge-core's tests/meta/conftest.py::PACKAGES_ROOT arithmetic exactly --
# same directory depth from this file to that one).
PACKAGES_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = PACKAGES_ROOT.parents[2]

_EXCLUDED_PACKAGE_NAMES = frozenset({"pyforge-core", "pyforge-testing-kit"})

_EIGHT_STATIONS = frozenset(
    {
        "pyforge-atlas",
        "pyforge-doctor",
        "pyforge-herald",
        "pyforge-marshal",
        "pyforge-mason",
        "pyforge-scribe",
        "pyforge-steward",
        "pyforge-warden",
    }
)


def _station_dirs(root: Path) -> list[Path]:
    """Every ``pyforge-*`` package directory under ``root`` except the two
    non-station leaves -- derived from the filesystem, never a hardcoded
    roster, so a ninth station needs no edit here (mirrors ``pyforge-core``'s
    ``tests/meta/conftest.py::sibling_station_dirs``)."""
    return sorted(
        p for p in root.iterdir() if p.is_dir() and p.name.startswith("pyforge-") and p.name not in _EXCLUDED_PACKAGE_NAMES
    )


def _station_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for station_dir in _station_dirs(root):
        src_pyforge = station_dir / "src" / "pyforge"
        if src_pyforge.is_dir():
            files.extend(sorted(src_pyforge.rglob("*.py")))
    return files


def _defines_evaluator(path: Path) -> bool:
    """True when ``path`` itself IS, or lives inside, the module path
    ``pyforge.<station>.coverage_gate`` -- a plain module (the exact shape
    the marshal violation took) or ANY file inside a ``coverage_gate/``
    directory, ``__init__.py`` or not: a PEP 420 namespace package (no
    ``__init__.py``) holding the evaluator's implementation under
    differently-named files is the identical violation one file deeper."""
    if path.stem == "coverage_gate":
        return True
    return path.parent.name == "coverage_gate"


def _imports_evaluator(tree: ast.Module) -> list[int]:
    violations: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[-1] == "coverage_gate":
                    violations.append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None and node.module.split(".")[-1] == "coverage_gate":
                violations.append(node.lineno)
            for alias in node.names:
                if alias.name == "coverage_gate":
                    violations.append(node.lineno)
        elif isinstance(node, ast.Call):
            # Dynamic reintroduction: importlib.import_module("...coverage_gate")
            # or __import__("...coverage_gate") never appears as an
            # ast.Import/ImportFrom node at all -- a station module using
            # either to load the relocated scripts/coverage_gate.py (or a
            # reintroduced copy) as a library would otherwise scan clean.
            func = node.func
            is_import_module_call = isinstance(func, ast.Attribute) and func.attr == "import_module"
            is_dunder_import_call = isinstance(func, ast.Name) and func.id == "__import__"
            if (is_import_module_call or is_dunder_import_call) and node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                    if first_arg.value.split(".")[-1] == "coverage_gate":
                        violations.append(node.lineno)
    return sorted(set(violations))


def _module_violations(path: Path) -> list[int]:
    if _defines_evaluator(path):
        return [1]
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return _imports_evaluator(tree)


def test_station_dirs_matches_the_eight_stations_the_coverage_gate_judges():
    assert {p.name for p in _station_dirs(PACKAGES_ROOT)} == _EIGHT_STATIONS


def test_real_tree_scan_surface_is_not_empty():
    files = _station_source_files(PACKAGES_ROOT)
    assert files, "coverage-gate class-structural guard found no station source files to scan"


def test_the_real_evaluator_lives_outside_every_scanned_tree():
    """Sanity check on the "moved layout" this contract must pass against:
    the real evaluator lives at ``scripts/coverage_gate.py`` -- outside
    every ``src/pyforge/<station>/`` tree this contract scans -- so it is
    never itself a false-positive input to the scan below."""
    evaluator = REPO_ROOT / "scripts" / "coverage_gate.py"
    assert evaluator.is_file(), f"expected {evaluator} to exist (doctor Story 24.1)"
    assert evaluator not in _station_source_files(PACKAGES_ROOT)


@pytest.mark.parametrize(
    "module_path",
    _station_source_files(PACKAGES_ROOT),
    ids=lambda p: str(p.relative_to(PACKAGES_ROOT)),
)
def test_no_station_defines_or_imports_the_coverage_gate_evaluator(module_path: Path):
    violations = _module_violations(module_path)
    assert not violations, (
        f"{module_path} defines or imports the coverage-gate evaluator at "
        f"line(s) {violations} -- CAP-3 (spec-coverage-gate-independence): no "
        f"pyforge.<station> module may evaluate or ship that same station's "
        f"own CI gate (Charter §5/§6). The evaluator lives at "
        f"scripts/coverage_gate.py; call it, never import it."
    )


# --- non-vacuous proof: the guard is alive, not vacuous, for EVERY station ---


@pytest.mark.parametrize("station", sorted(_EIGHT_STATIONS))
def test_guard_fires_on_a_planted_coverage_gate_module_for_any_station(tmp_path: Path, station: str):
    """The defect this story closes was never marshal-specific -- CAP-3
    exists because a NINTH station reintroducing the identical shape would
    have gone just as unnoticed. Proves the contract catches the class,
    parametrized across all eight stations rather than only the one that
    actually shipped the violation."""
    station_name = station.removeprefix("pyforge-")
    shim = tmp_path / station / "src" / "pyforge" / station_name / "coverage_gate.py"
    shim.parent.mkdir(parents=True)
    shim.write_text("def evaluate() -> bool:\n    return True\n", encoding="utf-8")

    files = _station_source_files(tmp_path)
    assert shim in files
    assert _module_violations(shim) == [1]


def test_guard_fires_on_a_planted_coverage_gate_package(tmp_path: Path):
    shim = tmp_path / "pyforge-marshal" / "src" / "pyforge" / "marshal" / "coverage_gate" / "__init__.py"
    shim.parent.mkdir(parents=True)
    shim.write_text("", encoding="utf-8")
    assert _module_violations(shim) == [1]


def test_guard_fires_on_an_absolute_import_of_the_evaluator(tmp_path: Path):
    module = tmp_path / "pyforge-marshal" / "src" / "pyforge" / "marshal" / "cli.py"
    module.parent.mkdir(parents=True)
    module.write_text("import scripts.coverage_gate\n", encoding="utf-8")
    assert _module_violations(module) == [1]


def test_guard_fires_on_a_from_import_of_the_evaluator(tmp_path: Path):
    module = tmp_path / "pyforge-marshal" / "src" / "pyforge" / "marshal" / "cli.py"
    module.parent.mkdir(parents=True)
    module.write_text("from scripts import coverage_gate\n", encoding="utf-8")
    assert _module_violations(module) == [1]


def test_guard_fires_on_a_relative_import_of_the_evaluator(tmp_path: Path):
    module = tmp_path / "pyforge-marshal" / "src" / "pyforge" / "marshal" / "cli.py"
    module.parent.mkdir(parents=True)
    module.write_text("from . import coverage_gate as gate\n", encoding="utf-8")
    assert _module_violations(module) == [1]


def test_guard_does_not_fire_on_an_unrelated_module(tmp_path: Path):
    module = tmp_path / "pyforge-marshal" / "src" / "pyforge" / "marshal" / "cli.py"
    module.parent.mkdir(parents=True)
    module.write_text(
        "import json\nfrom pathlib import Path\n\n\ndef main() -> None:\n    json.dumps({})\n    Path('.').exists()\n",
        encoding="utf-8",
    )
    assert _module_violations(module) == []
