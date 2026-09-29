"""CI-trigger companion to doctor's CAP-3 structural contract (Story 24.2,
``docs/governance/spec-coverage-gate-independence/SPEC.md``).

The canonical, fully-documented, exhaustively-tested contract lives at
``pyforge-doctor/tests/meta/test_coverage_gate_stays_outside_every_station.py``
-- read that module's docstring for the full rationale (Charter §5/§6, the
defect this closes, what "structurally" means). This file exists solely to
close a CI-coverage gap that module cannot close by itself: `.github/
workflows/pyforge-station-tests.yml`'s ``doctor-test`` job runs only when
``src/shared/packages/pyforge-doctor/**`` (or the shared surface) changed,
so a PR touching exactly one OTHER station -- atlas, herald, mason, scribe,
steward, or warden -- never runs it, and the reintroduction CAP-3 exists to
catch would pass CI unnoticed for six of the eight stations it is supposed
to protect (found live in review, Story 24.2). ``pyforge-core-test``, by
contrast, already runs on ANY single-station change (Story 52.2, CAP-8 --
its own sole-ownership meta-tests scan every sibling station's tree for the
identical reason), so hosting a copy of the check here is the one placement
guaranteed to fire regardless of which station a PR touches.

The violation-detection predicates below are DELIBERATELY DUPLICATED, not
imported, from doctor's copy: ``pyforge-core`` does not and must not depend
on ``pyforge-doctor`` (the dependency direction is the reverse, and
CAP-1/CAP-3 exist precisely so a station's own package cannot host code
that judges another package's conformance), and a third shared home
(``pyforge-testing-kit``) is out of scope for this story -- it is a
declared stdlib leaf (``[project] dependencies = []``) that must not grow
package-specific violation logic. Keep both copies' ``_defines_evaluator``/
``_imports_evaluator`` bodies byte-identical when either changes; this file
carries no independent non-vacuous proof for every station (doctor's own
suite already parametrizes that across all eight) -- one representative
station is enough evidence here that the shared logic still fires.
"""

from __future__ import annotations

import ast
from pathlib import Path

from conftest import PACKAGES_ROOT, parse_module, station_source_files

_EXCLUDE = frozenset({"pyforge-testing-kit"})


def _defines_evaluator(path: Path) -> bool:
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
    return _imports_evaluator(parse_module(path))


def test_scan_surface_is_not_empty():
    files = station_source_files(exclude=_EXCLUDE)
    assert files, "coverage-gate CI-trigger companion found no sibling station source files to scan"


def test_no_sibling_station_defines_or_imports_the_coverage_gate_evaluator():
    offenders = {
        f.relative_to(PACKAGES_ROOT): _module_violations(f)
        for f in station_source_files(exclude=_EXCLUDE)
        if _module_violations(f)
    }
    assert not offenders, (
        f"the following files define or import the coverage-gate evaluator: "
        f"{offenders} -- CAP-3 (spec-coverage-gate-independence): no "
        f"pyforge.<station> module may evaluate or ship that same station's "
        f"own CI gate. The evaluator lives at scripts/coverage_gate.py; call "
        f"it, never import it."
    )


def test_guard_fires_on_a_planted_coverage_gate_module(tmp_path: Path):
    shim = tmp_path / "pyforge-marshal" / "src" / "pyforge" / "marshal" / "coverage_gate.py"
    shim.parent.mkdir(parents=True)
    shim.write_text("def evaluate() -> bool:\n    return True\n", encoding="utf-8")
    assert _module_violations(shim) == [1]


def test_guard_fires_on_a_dynamic_import_of_the_evaluator(tmp_path: Path):
    module = tmp_path / "pyforge-marshal" / "src" / "pyforge" / "marshal" / "cli.py"
    module.parent.mkdir(parents=True)
    module.write_text(
        "import importlib\nimportlib.import_module('scripts.coverage_gate')\n",
        encoding="utf-8",
    )
    assert _module_violations(module) == [2]


def test_guard_does_not_fire_on_an_unrelated_module(tmp_path: Path):
    module = tmp_path / "pyforge-marshal" / "src" / "pyforge" / "marshal" / "cli.py"
    module.parent.mkdir(parents=True)
    module.write_text("import json\n\n\ndef main() -> None:\n    json.dumps({})\n", encoding="utf-8")
    assert _module_violations(module) == []
