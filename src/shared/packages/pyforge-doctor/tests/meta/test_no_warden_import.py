"""Meta test -- AD-3 one-way dependency guard (Story 1.1).

Doctor's taxonomy structurally mirrors ``pyforge.warden``'s but never
imports from it (see ``models.py``'s module docstring for the rationale).
AST-scan every module in the installed ``pyforge.doctor`` package and fail
if any of them imports ``pyforge.warden`` or any of its submodules.

Positively proves the detector fires on a synthetic violation -- the guard
is alive, not vacuous -- mirroring the sole-ownership meta-test's own style.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pyforge.doctor

_PACKAGE_FILE = pyforge.doctor.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent


def _package_modules() -> list[Path]:
    return sorted(PACKAGE_DIR.rglob("*.py"))


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _warden_import_violations(tree: ast.Module) -> list[int]:
    violations: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pyforge.warden" or alias.name.startswith(
                    "pyforge.warden."
                ):
                    violations.append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "pyforge.warden" or module.startswith("pyforge.warden."):
                violations.append(node.lineno)
    return violations


def test_package_scan_surface_is_not_empty():
    modules = _package_modules()
    assert modules, "no-warden-import guard found no modules to scan"


def test_no_module_imports_pyforge_warden():
    for module_path in _package_modules():
        violations = _warden_import_violations(_parse(module_path))
        assert not violations, (
            f"{module_path.name} imports pyforge.warden at line(s) "
            f"{violations} -- AD-3 forbids Doctor from importing Warden"
        )


def test_guard_fires_on_synthetic_import_violation():
    plain = "import pyforge.warden\n"
    assert _warden_import_violations(ast.parse(plain)) == [1]
    submodule = "import pyforge.warden.models\n"
    assert _warden_import_violations(ast.parse(submodule)) == [1]
    from_import = "from pyforge.warden import models\n"
    assert _warden_import_violations(ast.parse(from_import)) == [1]
    from_submodule = "from pyforge.warden.verdict import exit_code_for\n"
    assert _warden_import_violations(ast.parse(from_submodule)) == [1]


def test_guard_does_not_fire_on_unrelated_imports():
    benign = (
        "import pyforge.doctor.models\n"
        "from pyforge.doctor import verdict\n"
        "import json\n"
    )
    assert _warden_import_violations(ast.parse(benign)) == []
