"""CI-trigger companion to doctor's CAP-2 structural contract (Story 34.2,
``docs/governance/spec-feature-flag-governance/SPEC.md``).

The canonical, fully-documented, exhaustively-tested contract lives at
``pyforge-doctor/tests/meta/test_flag_gate_stays_outside_every_station.py`` -- read that module's
docstring for the full rationale (Charter section 6, what "structurally" means). This file exists
for the reason ``test_coverage_gate_ci_trigger_companion.py`` beside it exists: the ``doctor-test``
job in ``.github/workflows/pyforge-station-tests.yml`` runs only when
``src/shared/packages/pyforge-doctor/**`` (or the shared surface) changed, so a PR touching exactly
one OTHER station never runs the canonical copy, and a station reintroducing the gate would pass CI
unnoticed. ``pyforge-core-test`` already runs on ANY single-station change (Story 52.2), so hosting
a narrower copy here is the one placement guaranteed to fire whichever station a PR touches.

The violation-detection predicates below are DELIBERATELY DUPLICATED, not imported, from doctor's
copy: ``pyforge-core`` does not and must not depend on ``pyforge-doctor``. Keep both copies'
``_defines_gate`` / ``_imports_gate`` bodies in sync when either changes; this file carries one
representative planted-module proof (doctor's suite parametrizes it across all eight stations).
"""

from __future__ import annotations

import ast
from pathlib import Path

from conftest import PACKAGES_ROOT, parse_module, station_source_files

_EXCLUDE = frozenset({"pyforge-testing-kit"})

_GATE_NAMES = frozenset({"flag_gate", "flag_gate_check"})


def _defines_gate(path: Path) -> bool:
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
    return _imports_gate(parse_module(path))


def test_scan_surface_is_not_empty():
    files = station_source_files(exclude=_EXCLUDE)
    assert files, "flag-gate CI-trigger companion found no sibling station source files to scan"


def test_no_sibling_station_defines_or_imports_the_flag_gate():
    offenders = {
        f.relative_to(PACKAGES_ROOT): _module_violations(f)
        for f in station_source_files(exclude=_EXCLUDE)
        if _module_violations(f)
    }
    assert not offenders, (
        f"the following files define or import the flag gate: {offenders} -- CAP-2 "
        f"(spec-feature-flag-governance): no pyforge.<station> module may host the gate that "
        f"judges every station's stories. The gate lives at scripts/flag_gate_check.py; run it as "
        f"a subprocess (`flag-gate-check`), never import it."
    )


def test_guard_fires_on_a_planted_flag_gate_module(tmp_path: Path):
    shim = tmp_path / "pyforge-marshal" / "src" / "pyforge" / "marshal" / "flag_gate.py"
    shim.parent.mkdir(parents=True)
    shim.write_text("def judge() -> bool:\n    return True\n", encoding="utf-8")
    assert _module_violations(shim) == [1]


def test_guard_fires_on_a_planted_flag_gate_check_module_in_another_station(tmp_path: Path):
    shim = tmp_path / "pyforge-herald" / "src" / "pyforge" / "herald" / "flag_gate_check.py"
    shim.parent.mkdir(parents=True)
    shim.write_text("", encoding="utf-8")
    assert _module_violations(shim) == [1]


def test_guard_fires_on_a_dynamic_import_of_the_gate(tmp_path: Path):
    module = tmp_path / "pyforge-marshal" / "src" / "pyforge" / "marshal" / "cli.py"
    module.parent.mkdir(parents=True)
    module.write_text("import importlib\nimportlib.import_module('scripts.flag_gate_check')\n", encoding="utf-8")
    assert _module_violations(module) == [2]


def test_guard_fires_on_a_static_import_of_the_gate(tmp_path: Path):
    module = tmp_path / "pyforge-marshal" / "src" / "pyforge" / "marshal" / "cli.py"
    module.parent.mkdir(parents=True)
    module.write_text("from scripts import flag_gate_check\n", encoding="utf-8")
    assert _module_violations(module) == [1]


def test_guard_does_not_fire_on_an_unrelated_module(tmp_path: Path):
    module = tmp_path / "pyforge-marshal" / "src" / "pyforge" / "marshal" / "cli.py"
    module.parent.mkdir(parents=True)
    module.write_text("import json\n\n\ndef main() -> None:\n    json.dumps({})\n", encoding="utf-8")
    assert _module_violations(module) == []
