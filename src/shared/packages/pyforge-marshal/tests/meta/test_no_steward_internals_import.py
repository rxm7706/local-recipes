"""Story 100.1 (CAP-292): steward is reached only through ``adapters/steward_cli.py``."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import pyforge.marshal

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent
_STEWARD_ADAPTER = PACKAGE_DIR / "adapters" / "steward_cli.py"
_STEWARD_ARGV_MARKERS = ("steward", "ci", "status")


def _package_modules() -> list[Path]:
    return sorted(PACKAGE_DIR.rglob("*.py"))


def _module_id(path: Path) -> str:
    return str(path.relative_to(PACKAGE_DIR))


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _steward_import_violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(
                alias.name
                for alias in node.names
                if alias.name == "pyforge.steward" or alias.name.startswith("pyforge.steward.")
            )
        elif isinstance(node, ast.ImportFrom):
            if node.module and (node.module == "pyforge.steward" or node.module.startswith("pyforge.steward.")):
                found.append(node.module)
    return found


def _steward_argv_violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "run":
            for arg in node.args:
                if isinstance(arg, (ast.List, ast.Tuple)):
                    elts = [e.value for e in arg.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
                    if len(elts) >= 4 and elts[1:4] == list(_STEWARD_ARGV_MARKERS):
                        found.append("steward ci status argv")
    return found


@pytest.mark.parametrize("path", _package_modules(), ids=_module_id)
def test_no_pyforge_steward_import(path: Path) -> None:
    if path.resolve() == _STEWARD_ADAPTER.resolve():
        return
    violations = _steward_import_violations(_parse(path))
    assert not violations, f"{_module_id(path)} imports pyforge.steward -- use adapters/steward_cli.py only"


@pytest.mark.parametrize("path", _package_modules(), ids=_module_id)
def test_no_steward_cli_argv_outside_adapter(path: Path) -> None:
    if path.resolve() == _STEWARD_ADAPTER.resolve():
        return
    violations = _steward_argv_violations(_parse(path))
    assert not violations, f"{_module_id(path)} invokes steward ci status outside the adapter"
