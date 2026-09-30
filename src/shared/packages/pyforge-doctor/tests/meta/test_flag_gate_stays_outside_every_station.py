"""Structural contract -- CAP-2 of ``docs/governance/spec-feature-flag-governance/SPEC.md``
(doctor Story 34.2): the flag gate ships outside every station.

**Why it lives in Doctor's own package.** The flag gate judges every Smith's story specs and can
red any station's pull request, so under Charter section 6 ("the hand that builds is never the
gate that judges") no ``pyforge.<station>`` package may host it -- Doctor's included. Doctor is
constitutionally advisory (``sources/*.py`` Findings never gate a PR by themselves), so the
contract is a build-breaking test in ``tests/meta/``, not a ``sources/`` Finding. It is the same
shape as ``test_coverage_gate_stays_outside_every_station.py`` (doctor Story 24.2,
``spec-coverage-gate-independence`` CAP-3), which this file follows deliberately: read that
module's docstring for the rationale on scanning source trees instead of installed packages, and
on why ``pyforge-core`` and ``pyforge-testing-kit`` are not scanned here.

**What the scan flags.** Every ``pyforge-<station>`` package's ``src/pyforge/<station>/`` tree
(all eight stations, Doctor's own included) is scanned for a module that EITHER:

* **defines** the gate -- a file named ``flag_gate.py`` or ``flag_gate_check.py`` (or a
  ``flag_gate/`` / ``flag_gate_check/`` package directory, ``__init__.py`` or not), anywhere under
  a station's tree; a nested reintroduction is the identical violation one directory deeper; or
* **imports** it -- any ``import`` / ``from ... import`` statement, absolute or relative, naming a
  module whose last dotted component is ``flag_gate`` or ``flag_gate_check``, or a dynamic
  ``importlib.import_module(...)`` / ``__import__(...)`` call whose string argument's last dotted
  component is one of them. The real gate lives at ``scripts/flag_gate_check.py`` and is invoked as
  a subprocess CLI (the ``flag-gate-check`` pixi task, ``detectors-ci``), never imported as a
  library by a station.

**Non-vacuous proof.** ``tmp_path`` builds a throwaway ``pyforge.<station>.flag_gate`` shim for
each of the eight stations in a tree shaped like ``src/shared/packages/pyforge-<station>/src/
pyforge/<station>/``, proves the scan flags it, then proves the real tree scans clean.

A second, narrower copy of this check lives in ``pyforge-core``'s own ``tests/meta/`` (see
``test_flag_gate_ci_trigger_companion.py``) so CI runs it on a PR that touches only one non-doctor
station: ``pyforge-core-test`` runs on any single-station change, this package's job does not.
Keep both copies' ``_defines_gate`` / ``_imports_gate`` bodies in sync when either changes; this
file stays the canonical, fully-documented, exhaustively-tested contract.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# tests/meta/test_x.py -> parents[3] is src/shared/packages/ (same arithmetic as the sibling
# test_coverage_gate_stays_outside_every_station.py).
PACKAGES_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = PACKAGES_ROOT.parents[2]

_EXCLUDED_PACKAGE_NAMES = frozenset({"pyforge-core", "pyforge-testing-kit"})

_GATE_NAMES = frozenset({"flag_gate", "flag_gate_check"})

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
    """Every ``pyforge-*`` package directory under ``root`` except the two non-station leaves --
    derived from the filesystem, never a hardcoded roster, so a ninth station needs no edit here."""
    return sorted(
        p
        for p in root.iterdir()
        if p.is_dir() and p.name.startswith("pyforge-") and p.name not in _EXCLUDED_PACKAGE_NAMES
    )


def _station_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for station_dir in _station_dirs(root):
        src_pyforge = station_dir / "src" / "pyforge"
        if src_pyforge.is_dir():
            files.extend(sorted(src_pyforge.rglob("*.py")))
    return files


def _defines_gate(path: Path) -> bool:
    """True when ``path`` IS, or lives inside, the module path ``pyforge.<station>.flag_gate`` /
    ``flag_gate_check`` -- a plain module, or ANY file inside a ``flag_gate/`` or ``flag_gate_check/``
    directory (``__init__.py`` or not, at any depth): a PEP 420 namespace package holding the gate
    under differently-named files is the identical violation one file deeper. Only the path below
    the ``pyforge`` package root is read, so a checkout directory's own name never trips it."""
    parts = path.parent.parts
    below_root = parts[len(parts) - parts[::-1].index("pyforge") :] if "pyforge" in parts else parts
    return path.stem in _GATE_NAMES or any(part in _GATE_NAMES for part in below_root)


def _imports_gate(tree: ast.Module) -> list[int]:
    violations: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[-1] in _GATE_NAMES:
                    violations.append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None and node.module.split(".")[-1] in _GATE_NAMES:
                violations.append(node.lineno)
            for alias in node.names:
                if alias.name in _GATE_NAMES:
                    violations.append(node.lineno)
        elif isinstance(node, ast.Call):
            # Dynamic reintroduction: importlib.import_module("...flag_gate_check") or
            # __import__("...flag_gate_check") never appears as an ast.Import/ImportFrom node.
            func = node.func
            is_import_module_call = isinstance(func, ast.Attribute) and func.attr == "import_module"
            is_dunder_import_call = isinstance(func, ast.Name) and func.id == "__import__"
            if (is_import_module_call or is_dunder_import_call) and node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                    if first_arg.value.split(".")[-1] in _GATE_NAMES:
                        violations.append(node.lineno)
    return sorted(set(violations))


def _module_violations(path: Path) -> list[int]:
    if _defines_gate(path):
        return [1]
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return _imports_gate(tree)


def test_station_dirs_matches_the_eight_stations_the_gate_judges():
    assert {p.name for p in _station_dirs(PACKAGES_ROOT)} == _EIGHT_STATIONS


def test_real_tree_scan_surface_is_not_empty():
    files = _station_source_files(PACKAGES_ROOT)
    assert files, "flag-gate class-structural guard found no station source files to scan"


def test_the_real_gate_lives_outside_every_scanned_tree():
    """Sanity check on the layout this contract must pass against: the real gate lives at
    ``scripts/flag_gate_check.py`` -- outside every ``src/pyforge/<station>/`` tree this contract
    scans -- so it is never itself a false-positive input to the scan below."""
    gate = REPO_ROOT / "scripts" / "flag_gate_check.py"
    assert gate.is_file(), f"expected {gate} to exist (doctor Story 34.2)"
    assert gate not in _station_source_files(PACKAGES_ROOT)


@pytest.mark.parametrize(
    "module_path",
    _station_source_files(PACKAGES_ROOT),
    ids=lambda p: str(p.relative_to(PACKAGES_ROOT)),
)
def test_no_station_defines_or_imports_the_flag_gate(module_path: Path):
    violations = _module_violations(module_path)
    assert not violations, (
        f"{module_path} defines or imports the flag gate at line(s) {violations} -- CAP-2 "
        f"(spec-feature-flag-governance): no pyforge.<station> module may host the gate that "
        f"judges every station's stories (Charter section 6). The gate lives at "
        f"scripts/flag_gate_check.py; run it as a subprocess (`flag-gate-check`), never import it."
    )


# --- non-vacuous proof: the guard is alive, not vacuous, for EVERY station ---


@pytest.mark.parametrize("station", sorted(_EIGHT_STATIONS))
def test_guard_fires_on_a_planted_flag_gate_module_for_any_station(tmp_path: Path, station: str):
    """Proves the contract catches the class in each of the eight stations -- a planted
    ``pyforge.<station>.flag_gate`` module in a temporary tree fails it; the real tree passes."""
    station_name = station.removeprefix("pyforge-")
    shim = tmp_path / station / "src" / "pyforge" / station_name / "flag_gate.py"
    shim.parent.mkdir(parents=True)
    shim.write_text("def judge() -> bool:\n    return True\n", encoding="utf-8")

    assert shim in _station_source_files(tmp_path)
    assert _module_violations(shim) == [1]


def test_guard_fires_on_a_planted_flag_gate_check_module(tmp_path: Path):
    shim = tmp_path / "pyforge-doctor" / "src" / "pyforge" / "doctor" / "flag_gate_check.py"
    shim.parent.mkdir(parents=True)
    shim.write_text("", encoding="utf-8")
    assert _module_violations(shim) == [1]


@pytest.mark.parametrize("package", ["flag_gate", "flag_gate_check"])
def test_guard_fires_on_a_planted_gate_package_and_namespace_package(tmp_path: Path, package: str):
    pkg = tmp_path / "pyforge-marshal" / "src" / "pyforge" / "marshal" / package
    pkg.mkdir(parents=True)
    init = pkg / "__init__.py"
    init.write_text("", encoding="utf-8")
    nested = pkg / "deeper" / "evaluate.py"  # a PEP 420 namespace directory, one level further down
    nested.parent.mkdir()
    nested.write_text("def judge() -> bool:\n    return True\n", encoding="utf-8")

    assert _module_violations(init) == [1]
    assert _module_violations(nested) == [1]


def test_guard_fires_on_a_planted_nested_flag_gate_module(tmp_path: Path):
    shim = tmp_path / "pyforge-steward" / "src" / "pyforge" / "steward" / "deep" / "er" / "flag_gate.py"
    shim.parent.mkdir(parents=True)
    shim.write_text("", encoding="utf-8")
    assert _module_violations(shim) == [1]


@pytest.mark.parametrize(
    ("source", "line"),
    [
        ("import importlib\nimportlib.import_module('scripts.flag_gate_check')\n", 2),
        ("__import__('pyforge.marshal.flag_gate')\n", 1),
        ("import scripts.flag_gate_check\n", 1),
        ("import flag_gate_check as gate\n", 1),
        ("from scripts import flag_gate_check\n", 1),
        ("from scripts.flag_gate_check import main\n", 1),
        ("from . import flag_gate as gate\n", 1),
        ("from .flag_gate import judge\n", 1),
    ],
)
def test_guard_fires_on_every_import_form_of_the_gate(tmp_path: Path, source: str, line: int):
    module = tmp_path / "pyforge-marshal" / "src" / "pyforge" / "marshal" / "cli.py"
    module.parent.mkdir(parents=True)
    module.write_text(source, encoding="utf-8")
    assert _module_violations(module) == [line]


@pytest.mark.parametrize(
    "source",
    [
        "import importlib\nimportlib.import_module('pyforge.marshal.cli')\n",
        "import json\nfrom pathlib import Path\n\n\ndef main() -> None:\n    json.dumps({})\n    Path('.').exists()\n",
        "from pyforge.marshal import flag_gateway\n",  # a different name, not the gate
        "import subprocess\nsubprocess.run(['pixi', 'run', 'flag-gate-check'])\n",  # the sanctioned way: a subprocess
    ],
)
def test_guard_does_not_fire_on_an_unrelated_module(tmp_path: Path, source: str):
    module = tmp_path / "pyforge-marshal" / "src" / "pyforge" / "marshal" / "cli.py"
    module.parent.mkdir(parents=True)
    module.write_text(source, encoding="utf-8")
    assert _module_violations(module) == []


def test_guard_does_not_fire_on_a_module_that_only_resembles_the_gate_name(tmp_path: Path):
    module = tmp_path / "pyforge-marshal" / "src" / "pyforge" / "marshal" / "flag_gateway.py"
    module.parent.mkdir(parents=True)
    module.write_text("", encoding="utf-8")
    assert _module_violations(module) == []


def test_a_checkout_directory_named_like_the_gate_is_not_a_violation(tmp_path: Path):
    module = tmp_path / "flag_gate" / "pyforge-marshal" / "src" / "pyforge" / "marshal" / "cli.py"
    module.parent.mkdir(parents=True)
    module.write_text("", encoding="utf-8")
    assert _module_violations(module) == []
