"""Meta test -- amended AD-51 (Story 12.5): zero ``typer``/``rich`` imports
under the installed ``pyforge.marshal`` package.

The superseded typer+rich CLI rule must never be reintroduced. AST-scans
every module the same way ``test_ad65_no_network_stack_imports.py`` does.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import pyforge.marshal

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent

_FORBIDDEN = frozenset({"typer", "rich"})


def _package_modules() -> list[Path]:
    return sorted(PACKAGE_DIR.rglob("*.py"))


def _module_id(path: Path) -> str:
    return str(path.relative_to(PACKAGE_DIR))


def _forbidden_import_violations(tree: ast.Module) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in _FORBIDDEN:
                    violations.append(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level != 0 or node.module is None:
                continue
            root = node.module.split(".", 1)[0]
            if root in _FORBIDDEN:
                violations.append(node.module)
    return violations


@pytest.mark.parametrize("path", _package_modules(), ids=_module_id)
def test_no_typer_or_rich_imports(path: Path):
    source = path.read_text(encoding="utf-8")
    violations = _forbidden_import_violations(ast.parse(source, filename=str(path)))
    assert not violations, f"{_module_id(path)} imports forbidden CLI stack module(s): " + ", ".join(
        sorted(set(violations))
    )


def test_guard_is_alive_synthetic_typer_import_fires(tmp_path: Path):
    offender = tmp_path / "offender.py"
    offender.write_text("import typer\n", encoding="utf-8")
    violations = _forbidden_import_violations(ast.parse(offender.read_text(encoding="utf-8"), filename=str(offender)))
    assert "typer" in violations
