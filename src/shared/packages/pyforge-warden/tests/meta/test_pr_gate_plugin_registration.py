"""Meta test — Warden must not ship a parallel plugin loader (Story 9.1).

Canonical registration group is ``pyforge.core.hooks`` only. A
``pyforge.warden.(hooks|plugins)`` entry-point group, or ``import pluggy``
in ``hooks.py``, is a conformance failure.
"""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path
from typing import Any

from pyforge.core.hooks import ENTRY_POINT_GROUP as CORE_ENTRY_POINT_GROUP

import pyforge.warden
from pyforge.warden.hooks import ENTRY_POINT_GROUP

_PACKAGE_FILE = pyforge.warden.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent
HOOKS_PY = PACKAGE_DIR / "hooks.py"


def _warden_pyproject() -> Path:
    for candidate in (PACKAGE_DIR, *PACKAGE_DIR.parents):
        path = candidate / "pyproject.toml"
        if not path.is_file():
            continue
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        if data.get("project", {}).get("name") == "pyforge-warden":
            return path
    raise AssertionError("could not find pyforge-warden pyproject.toml")


PYPROJECT = _warden_pyproject()

_PARALLEL_GROUP = re.compile(r"^pyforge\.[^.]+\.(hooks|plugins)$")


def _flatten_entry_point_groups(table: dict[str, Any], prefix: str = "") -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    if not isinstance(table, dict):
        return groups
    # Empty table at a prefix is still a declared group
    # (``[project.entry-points."pyforge.warden.hooks"]`` with no entries).
    if prefix and not table:
        groups[prefix] = table
        return groups
    if table and all(isinstance(value, str) for value in table.values()):
        if prefix:
            groups[prefix] = table
        return groups
    for key, value in table.items():
        if not isinstance(value, dict):
            continue
        next_prefix = f"{prefix}.{key}" if prefix else key
        if not value:
            groups[next_prefix] = value
        elif all(isinstance(inner, str) for inner in value.values()):
            groups[next_prefix] = value
        else:
            groups.update(_flatten_entry_point_groups(value, next_prefix))
    return groups


def entry_point_groups_from_toml(text: str) -> dict[str, dict[str, Any]]:
    data = tomllib.loads(text)
    table = data.get("project", {}).get("entry-points", {})
    if not isinstance(table, dict):
        return {}
    return _flatten_entry_point_groups(table)


def parallel_loader_violations(text: str) -> list[str]:
    violations: list[str] = []
    for group in entry_point_groups_from_toml(text):
        if group == CORE_ENTRY_POINT_GROUP:
            continue
        if _PARALLEL_GROUP.fullmatch(group):
            violations.append(group)
    return violations


def pluggy_import_violations(source: str) -> list[str]:
    tree = ast.parse(source)
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pluggy" or alias.name.startswith("pluggy."):
                    hits.append(f"{node.lineno}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "pluggy" or module.startswith("pluggy."):
                hits.append(f"{node.lineno}: from {module} import ...")
    return hits


def test_entry_point_group_is_the_core_canonical_string():
    assert ENTRY_POINT_GROUP == CORE_ENTRY_POINT_GROUP == "pyforge.core.hooks"


def test_pyproject_has_no_parallel_warden_plugin_group():
    assert PYPROJECT.is_file(), f"missing {PYPROJECT}"
    text = PYPROJECT.read_text(encoding="utf-8")
    hits = parallel_loader_violations(text)
    assert not hits, (
        "pyforge-warden pyproject.toml declared a parallel plugin group "
        f"(only {CORE_ENTRY_POINT_GROUP!r} is allowed): {hits}"
    )
    groups = entry_point_groups_from_toml(text)
    canonical = groups.get(CORE_ENTRY_POINT_GROUP, {})
    assert canonical, f"pyforge-warden must declare plugins on {CORE_ENTRY_POINT_GROUP!r}"


def test_hooks_py_does_not_import_pluggy():
    assert HOOKS_PY.is_file(), f"missing {HOOKS_PY}"
    hits = pluggy_import_violations(HOOKS_PY.read_text(encoding="utf-8"))
    assert not hits, (
        f"pyforge.warden.hooks imports pluggy — a parallel plugin loader (use {CORE_ENTRY_POINT_GROUP!r}): {hits}"
    )


def test_detector_fires_on_a_synthetic_parallel_hooks_group():
    synthetic = """
[project.entry-points."pyforge.warden.hooks"]
gate = "pyforge.warden.hooks:GatePlugin"
"""
    assert parallel_loader_violations(synthetic) == ["pyforge.warden.hooks"]


def test_detector_fires_on_an_empty_parallel_hooks_group():
    synthetic = """
[project.entry-points."pyforge.warden.hooks"]
"""
    assert parallel_loader_violations(synthetic) == ["pyforge.warden.hooks"]


def test_detector_fires_on_a_synthetic_parallel_plugins_group():
    synthetic = """
[project.entry-points."pyforge.warden.plugins"]
gate = "pyforge.warden.plugins:GatePlugin"
"""
    assert parallel_loader_violations(synthetic) == ["pyforge.warden.plugins"]


def test_pluggy_detector_fires_on_a_synthetic_import():
    assert pluggy_import_violations("import pluggy\n")
    assert pluggy_import_violations("from pluggy import PluginManager\n")
