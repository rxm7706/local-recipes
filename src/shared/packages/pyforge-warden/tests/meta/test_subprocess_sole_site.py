"""Meta test — ``engines.py`` is the package's sole subprocess site (Story 11.3).

AST-scans every module under the installed ``pyforge.warden`` package
(subpackages included) except top-level ``engines.py`` and fails on:

* any import of ``subprocess`` (any form, including inside ``if TYPE_CHECKING:``);
* ``os.system`` / ``os.popen`` called through any name bound to ``os``, or
  imported with ``from os import``;
* ``asyncio.create_subprocess_exec`` / ``create_subprocess_shell`` called bare,
  from-imported, or through any name bound to ``asyncio``, and an import of
  ``asyncio.subprocess``.

Positively asserts the scan surface is non-vacuous, that excluded ``engines.py``
still imports ``subprocess``, and that each detector fires on synthetic source.

Bounds match ``test_extract_no_execution.py``: static only — ``getattr``,
``importlib`` and plain-assignment aliasing are out of scope.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import pyforge.warden

_PACKAGE_FILE = pyforge.warden.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent
ENGINES_MODULE = PACKAGE_DIR / "engines.py"

FORBIDDEN_OS_MEMBERS = frozenset({"system", "popen"})
FORBIDDEN_ASYNCIO_MEMBERS = frozenset({"create_subprocess_exec", "create_subprocess_shell"})


def _warden_modules() -> list[Path]:
    return sorted(path for path in PACKAGE_DIR.rglob("*.py") if path != ENGINES_MODULE)


def _module_aliases(tree: ast.Module, module: str) -> frozenset[str]:
    names = {module}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Import):
            continue
        for alias in node.names:
            if alias.name.split(".")[0] == module:
                names.add(alias.asname or alias.name.split(".")[0])
    return frozenset(names)


def _attr_root(func: ast.Attribute) -> str | None:
    node: ast.expr = func.value
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _subprocess_violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    os_names = _module_aliases(tree, "os")
    asyncio_names = _module_aliases(tree, "asyncio")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "subprocess":
                    found.append(f"import {alias.name} (line {node.lineno})")
                elif alias.name == "asyncio.subprocess" or alias.name.startswith("asyncio.subprocess."):
                    found.append(f"import {alias.name} (line {node.lineno})")
        elif isinstance(node, ast.ImportFrom):
            top = (node.module or "").split(".")[0]
            if top == "subprocess":
                found.append(f"from {node.module} import ... (line {node.lineno})")
            elif top == "os":
                found.extend(
                    f"from os import {alias.name} (line {node.lineno})"
                    for alias in node.names
                    if alias.name in FORBIDDEN_OS_MEMBERS
                )
            elif top == "asyncio":
                found.extend(
                    f"from asyncio import {alias.name} (line {node.lineno})"
                    for alias in node.names
                    if alias.name in FORBIDDEN_ASYNCIO_MEMBERS | {"subprocess"}
                )
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_ASYNCIO_MEMBERS:
                found.append(f"{func.id}() call (line {node.lineno})")
            elif isinstance(func, ast.Attribute):
                if func.attr in FORBIDDEN_ASYNCIO_MEMBERS and _attr_root(func) in asyncio_names:
                    found.append(f"asyncio.{func.attr}() call (line {node.lineno})")
                elif isinstance(func.value, ast.Name):
                    base = func.value.id
                    if base in os_names and func.attr in FORBIDDEN_OS_MEMBERS:
                        found.append(f"os.{func.attr}() call (line {node.lineno})")
    return found


def test_package_has_multiple_modules_and_engines_imports_subprocess():
    modules = _warden_modules()
    assert len(modules) > 1, f"expected more than one scannable module, got {modules!r}"
    engines_tree = ast.parse(ENGINES_MODULE.read_text(encoding="utf-8"), str(ENGINES_MODULE))
    assert any(
        alias.name.split(".")[0] == "subprocess"
        for node in ast.walk(engines_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    ) or any(
        (node.module or "").split(".")[0] == "subprocess"
        for node in ast.walk(engines_tree)
        if isinstance(node, ast.ImportFrom)
    ), "engines.py must import subprocess (guard-alive positive control)"


@pytest.mark.parametrize("module_path", _warden_modules(), ids=lambda p: p.relative_to(PACKAGE_DIR).as_posix())
def test_warden_module_has_no_subprocess_outside_engines(module_path: Path):
    tree = ast.parse(module_path.read_text(encoding="utf-8"), str(module_path))
    violations = _subprocess_violations(tree)
    rel = module_path.relative_to(PACKAGE_DIR).as_posix()
    assert not violations, f"{rel} violates the sole subprocess site (engines.py only): {violations}"


def test_detector_fires_on_subprocess_import():
    assert _subprocess_violations(ast.parse("import subprocess\n"))
    assert _subprocess_violations(ast.parse("import subprocess as sp\n"))
    assert _subprocess_violations(ast.parse("from subprocess import run\n"))
    assert _subprocess_violations(
        ast.parse("from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import subprocess\n")
    )
    assert not _subprocess_violations(ast.parse("import json\n"))


def test_detector_fires_on_os_system_and_popen():
    assert _subprocess_violations(ast.parse("import os\nos.system('x')\n"))
    assert _subprocess_violations(ast.parse("from os import popen\n"))
    assert not _subprocess_violations(ast.parse("import os\nos.getcwd()\n"))


def test_detector_fires_on_asyncio_subprocess_api():
    assert _subprocess_violations(ast.parse("import asyncio\nasyncio.create_subprocess_exec(x)\n"))
    assert _subprocess_violations(ast.parse("from asyncio import create_subprocess_shell\n"))
    assert _subprocess_violations(ast.parse("import asyncio.subprocess\n"))
    assert not _subprocess_violations(ast.parse("import asyncio\nasyncio.run(main())\n"))
