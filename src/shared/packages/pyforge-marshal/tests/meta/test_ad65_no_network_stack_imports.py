"""Meta test -- AD-65 / P-09's no-network-stack import guard (Story 12.3).

AST-scan every module in the installed ``pyforge.marshal`` package and fail
if any of them imports one of the forbidden network stacks:

- ``requests`` (any alias, absolute ``import`` / ``from ... import``)
- ``httpx`` (same)
- ``urllib.request`` (and ``urllib`` when imported as a module alias that
  would enable ``urllib.request`` access -- we match the literal module
  names ``urllib.request`` and ``urllib`` only on ``ImportFrom`` nodes with
  ``level == 0``)
- ``socket`` (same rule as ``requests``)

Mirrors ``tests/meta/test_p02_copier_sole_ownership.py``'s AST technique.
The architecture's AD-65 text names ``requests``/``httpx``/``urllib.request``
explicitly; Story 12.3's AC and epics extend that set with ``socket`` so
air-gapped adopters never carry a network stack at import time.

Bounds (stated, not aspirational): dynamic import (``importlib.import_module
("requests")``) is out of scope, matching every other import guard in this
package. The egress-counter integration test is the behavioral backstop.
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

_FORBIDDEN_ROOTS = frozenset({"requests", "httpx", "urllib", "urllib.request", "socket"})


def _package_modules() -> list[Path]:
    return sorted(PACKAGE_DIR.rglob("*.py"))


def _module_id(path: Path) -> str:
    return str(path.relative_to(PACKAGE_DIR))


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _forbidden_import_violations(tree: ast.Module) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if alias.name in _FORBIDDEN_ROOTS or root in _FORBIDDEN_ROOTS:
                    violations.append(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level != 0 or node.module is None:
                continue
            root = node.module.split(".", 1)[0]
            if node.module in _FORBIDDEN_ROOTS or root in _FORBIDDEN_ROOTS:
                violations.append(node.module)
    return violations


@pytest.mark.parametrize("path", _package_modules(), ids=_module_id)
def test_no_forbidden_network_stack_imports(path: Path):
    violations = _forbidden_import_violations(_parse(path))
    assert not violations, f"{_module_id(path)} imports forbidden network stack module(s): " + ", ".join(
        sorted(set(violations))
    )


def test_guard_is_alive_synthetic_socket_import_fires(tmp_path: Path):
    """Vacuity check: the scanner actually fires on a synthetic offender."""
    offender = tmp_path / "offender.py"
    offender.write_text("import socket\n", encoding="utf-8")
    violations = _forbidden_import_violations(_parse(offender))
    assert violations == ["socket"]
