"""Meta test — the ``extract/`` no-execution zone AST denylist (Story 1.2).

NFR-S1: the extractor parses untrusted input as DATA, never executes it.
This guard AST-scans every module under the installed package's ``extract/``
and fails on:

* any import of ``subprocess``, ``jinja2``, ``pty``, ``ctypes``, or
  ``multiprocessing`` (any form);
* ``from os import <member>`` for any forbidden os member (``system``,
  ``popen``, the full ``exec*``/``spawn*`` families, ``posix_spawn``/
  ``posix_spawnp``) and ``from builtins import
  eval/exec/compile/__import__``;
* calls to ``eval``/``exec``/``compile``/``__import__`` — as bare names OR
  as attributes through any name bound to the ``builtins`` module
  (``import builtins; builtins.eval(...)``);
* calls to any forbidden os member through any name bound to the os
  module, or unsafe ``yaml.load`` (through any name bound to the yaml
  module; ``yaml.safe_load`` is legal).

Positively asserts the extract package exists and was scanned, and that the
detectors fire on synthetic violations — the guard is alive, not vacuous.

Bounds (stated, not aspirational): a best-effort STATIC check, like the 1.1
sole-ownership guard — ``getattr`` indirection, ``importlib`` dynamic
imports, and string-built attribute access are out of scope; the
socket-deny harness and the conformance suite are the behavioral backstop.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import python_deptry_osv_scanner

_PACKAGE_FILE = python_deptry_osv_scanner.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
EXTRACT_DIR = Path(_PACKAGE_FILE).resolve().parent / "extract"

FORBIDDEN_MODULES = frozenset(
    {"subprocess", "jinja2", "pty", "ctypes", "multiprocessing"}
)
FORBIDDEN_OS_MEMBERS = frozenset(
    {
        "system",
        "popen",
        # the exec* family (process-image replacement)
        "execl",
        "execle",
        "execlp",
        "execlpe",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        # the spawn* family
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        # posix_spawn proper
        "posix_spawn",
        "posix_spawnp",
    }
)
FORBIDDEN_BUILTIN_CALLS = frozenset({"eval", "exec", "compile", "__import__"})


def _extract_modules() -> list[Path]:
    return sorted(EXTRACT_DIR.rglob("*.py"))


def _module_aliases(tree: ast.Module, module: str) -> frozenset[str]:
    """Names bound to ``module`` itself (``import os as o`` etc.)."""
    names = {module}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Import):
            continue
        for alias in node.names:
            if alias.name.split(".")[0] == module:
                names.add(alias.asname or alias.name.split(".")[0])
    return frozenset(names)


def _violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    os_names = _module_aliases(tree, "os")
    yaml_names = _module_aliases(tree, "yaml")
    builtins_names = _module_aliases(tree, "builtins")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_MODULES:
                    found.append(f"import {alias.name} (line {node.lineno})")
        elif isinstance(node, ast.ImportFrom):
            top = (node.module or "").split(".")[0]
            if top in FORBIDDEN_MODULES:
                found.append(
                    f"from {node.module} import ... (line {node.lineno})"
                )
            elif top == "os":
                found.extend(
                    f"from os import {alias.name} (line {node.lineno})"
                    for alias in node.names
                    if alias.name in FORBIDDEN_OS_MEMBERS
                )
            elif top == "builtins":
                found.extend(
                    f"from builtins import {alias.name} (line {node.lineno})"
                    for alias in node.names
                    if alias.name in FORBIDDEN_BUILTIN_CALLS
                )
            elif top == "yaml":
                found.extend(
                    f"from yaml import load (line {node.lineno})"
                    for alias in node.names
                    if alias.name == "load"
                )
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_BUILTIN_CALLS:
                found.append(f"{func.id}() call (line {node.lineno})")
            elif isinstance(func, ast.Attribute) and isinstance(
                func.value, ast.Name
            ):
                base = func.value.id
                if base in os_names and func.attr in FORBIDDEN_OS_MEMBERS:
                    found.append(f"os.{func.attr}() call (line {node.lineno})")
                elif (
                    base in builtins_names
                    and func.attr in FORBIDDEN_BUILTIN_CALLS
                ):
                    found.append(
                        f"builtins.{func.attr}() call (line {node.lineno})"
                    )
                elif base in yaml_names and func.attr == "load":
                    found.append(f"yaml.load() call (line {node.lineno})")
    return found


def test_extract_zone_exists_and_is_scanned():
    """Non-vacuous proof: the zone exists and the guard has a surface."""
    assert EXTRACT_DIR.is_dir(), "extract/ missing from the installed package"
    modules = _extract_modules()
    assert len(modules) >= 2, (  # __init__.py + pyproject.py at minimum
        f"extract/ scan surface unexpectedly small: {modules}"
    )


@pytest.mark.parametrize("module_path", _extract_modules(), ids=lambda p: p.name)
def test_extract_module_has_no_execution_primitives(module_path: Path):
    tree = ast.parse(module_path.read_text(encoding="utf-8"), str(module_path))
    violations = _violations(tree)
    assert not violations, (
        f"{module_path.name} violates the no-execution zone (NFR-S1): "
        f"{violations}"
    )


def test_detector_fires_on_forbidden_imports():
    assert _violations(ast.parse("import subprocess\n"))
    assert _violations(ast.parse("import subprocess.run\n"))
    assert _violations(ast.parse("from subprocess import run\n"))
    assert _violations(ast.parse("import jinja2\n"))
    assert _violations(ast.parse("from jinja2 import Template\n"))
    assert _violations(ast.parse("from os import system\n"))
    assert _violations(ast.parse("from os import popen\n"))
    assert _violations(ast.parse("from builtins import eval\n"))
    assert not _violations(ast.parse("import tomllib\nimport os\n"))


def test_detector_fires_on_forbidden_calls():
    assert _violations(ast.parse("eval('x')\n"))
    assert _violations(ast.parse("exec('x')\n"))
    assert _violations(ast.parse("import os\nos.system('ls')\n"))
    assert _violations(ast.parse("import os as o\no.popen('ls')\n"))
    assert _violations(ast.parse("import yaml\nyaml.load(stream)\n"))
    assert _violations(ast.parse("import yaml as y\ny.load(stream)\n"))
    assert not _violations(ast.parse("import yaml\nyaml.safe_load(stream)\n"))
    assert not _violations(ast.parse("value = evaluate('x')\n"))


def test_detector_fires_on_compile_and_dunder_import():
    """compile() and __import__() are execution primitives too — the guard
    is alive on both, bare or via builtins."""
    assert _violations(ast.parse("compile('x', '<s>', 'eval')\n"))
    assert _violations(ast.parse("__import__('os')\n"))
    assert _violations(ast.parse("from builtins import compile\n"))
    assert _violations(ast.parse("from builtins import __import__\n"))
    assert not _violations(ast.parse("value = recompile('x')\n"))


def test_detector_fires_on_builtins_bound_attribute_calls():
    """``import builtins; builtins.eval(...)`` must not slip past the
    bare-name check — attribute calls through any name bound to the
    builtins module fire."""
    assert _violations(ast.parse("import builtins\nbuiltins.eval('x')\n"))
    assert _violations(ast.parse("import builtins as b\nb.exec('x')\n"))
    assert _violations(
        ast.parse("import builtins\nbuiltins.compile('x', '<s>', 'exec')\n")
    )
    assert _violations(ast.parse("import builtins\nbuiltins.__import__('os')\n"))
    assert not _violations(ast.parse("import builtins\nbuiltins.len([])\n"))


@pytest.mark.parametrize("member", sorted(FORBIDDEN_OS_MEMBERS))
def test_detector_fires_on_each_forbidden_os_member(member: str):
    """Guard-alive proof per os member: attribute call, aliased-module
    attribute call, AND the from-import form all fire."""
    assert _violations(ast.parse(f"import os\nos.{member}(x)\n"))
    assert _violations(ast.parse(f"import os as o\no.{member}(x)\n"))
    assert _violations(ast.parse(f"from os import {member}\n"))


def test_detector_ignores_benign_os_usage():
    assert not _violations(ast.parse("import os\nos.getcwd()\n"))
    assert not _violations(ast.parse("from os import path\n"))


def test_detector_fires_on_new_forbidden_imports():
    """pty, ctypes, and multiprocessing join subprocess/jinja2 on the
    forbidden-import list (every import form)."""
    assert _violations(ast.parse("import pty\n"))
    assert _violations(ast.parse("from pty import spawn\n"))
    assert _violations(ast.parse("import ctypes\n"))
    assert _violations(ast.parse("import ctypes.util\n"))
    assert _violations(ast.parse("from ctypes import CDLL\n"))
    assert _violations(ast.parse("import multiprocessing\n"))
    assert _violations(ast.parse("from multiprocessing import Process\n"))
    assert _violations(ast.parse("import multiprocessing.pool\n"))
    assert not _violations(ast.parse("import tomllib\nimport math\n"))
