"""Meta test -- station packages must not ship a parallel plugin loader
(Story 32.1).

Best-effort STATIC scan of sibling station ``pyproject.toml`` files (and
``[project.entry-points.*]`` tables) plus an AST scan for ``import pluggy``. A group named
``pyforge.<token>.hooks`` or ``pyforge.<token>.plugins`` other than the
canonical ``pyforge.core.hooks`` is a conformance failure.

Out of scope (stated, not aspirational): dynamic loaders, and non-pyforge
groups such as pytest/django plugin entry points.

Non-vacuous proof: a synthetic ``pyforge.warden.hooks`` table IS flagged;
``pyforge.core.hooks`` and ``pytest11`` are not.

Names (steward Story 146.1, spec-pyforge-unifying-strategy:CAP-18, amended 2026-11-26): every name a package
registers on ``pyforge.core.hooks`` starts with its package token and a hyphen (``pyforge-mason`` registers
``mason-...``; ``pyforge-core`` registers ``core-...``), and no name is registered twice across the packages. The
registry never selects by this name (a station selects by an attribute such as ``plugin_id`` or ``engine_name``), so
the name only has to say whose plugin it is and stay unique in the shared group. The token is the package's
``[project].name`` without ``pyforge-``. The scan covers the ``pyforge-*`` packages under ``src/shared/packages/``
(core's own included), the packages that register on the group; a ``django-*`` portal or ``src/platform``
registers nothing there today and is outside it.
"""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path
from typing import Any

import pytest
from conftest import PACKAGES_ROOT, sibling_station_dirs, station_source_files

# Story 117.1 (spec-pyforge-core:CAP-14): this module reads every sibling station's pyproject.toml and src/ (through
# conftest) outside pyforge-core, so it runs in the core suite's live-tree half (`-m live_tree`), never in the package
# half a second root runs from the package alone.
pytestmark = pytest.mark.live_tree

_CANONICAL_GROUP = "pyforge.core.hooks"
_PARALLEL_GROUP = re.compile(r"^pyforge\.[^.]+\.(hooks|plugins)$")


def _flatten_entry_point_groups(table: dict[str, Any], prefix: str = "") -> dict[str, dict[str, Any]]:
    """Walk a PEP 621 ``[project.entry-points]`` table into dotted group
    names. Quoted groups (``"pyforge.warden.hooks"``) stay one key; unquoted
    nested tables (``[project.entry-points.pyforge.warden.hooks]``) are
    joined with dots."""
    groups: dict[str, dict[str, Any]] = {}
    if not isinstance(table, dict):
        return groups
    if table and all(isinstance(value, str) for value in table.values()):
        if prefix:
            groups[prefix] = table
        return groups
    for key, value in table.items():
        if not isinstance(value, dict):
            continue
        next_prefix = f"{prefix}.{key}" if prefix else key
        if value and all(isinstance(inner, str) for inner in value.values()):
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
    """Group names that are a pyforge hooks/plugins registration other than
    the canonical ``pyforge.core.hooks``."""
    violations: list[str] = []
    for group in entry_point_groups_from_toml(text):
        if group == _CANONICAL_GROUP:
            continue
        if _PARALLEL_GROUP.fullmatch(group):
            violations.append(group)
    return violations


def pluggy_import_violations(source: str) -> list[str]:
    """Flag ``import pluggy`` / ``from pluggy import ...`` — a second
    plugin loader for the same class of process-hook extension."""
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


def _station_pyprojects() -> list[Path]:
    return [station / "pyproject.toml" for station in sibling_station_dirs() if (station / "pyproject.toml").is_file()]


def registered_names_from_toml(text: str) -> list[str]:
    """The names a ``pyproject.toml`` registers on the canonical group, in file order."""
    return list(entry_point_groups_from_toml(text).get(_CANONICAL_GROUP, {}))


def unprefixed_names(package_name: str, names: list[str]) -> list[str]:
    """Names that do not start with the package token and a hyphen (``pyforge-mason`` -> ``mason-``)."""
    prefix = package_name.removeprefix("pyforge-") + "-"
    return [name for name in names if not name.startswith(prefix) or name == prefix]


def repeated_names(registrations: dict[str, list[str]]) -> dict[str, list[str]]:
    """Each name more than one package registers, with every package that registers it (TOML already refuses a
    name repeated inside one table)."""
    owners: dict[str, list[str]] = {}
    for package, names in registrations.items():
        for name in names:
            owners.setdefault(name, []).append(package)
    return {name: packages for name, packages in sorted(owners.items()) if len(packages) > 1}


def _package_pyprojects() -> list[Path]:
    """Every ``pyforge-*`` package's ``pyproject.toml``, ``pyforge-core``'s own included."""
    return [PACKAGES_ROOT / "pyforge-core" / "pyproject.toml", *_station_pyprojects()]


def _registrations() -> dict[str, list[str]]:
    """Each package's ``[project].name`` with the names its ``pyproject.toml`` registers on the canonical group."""
    registrations: dict[str, list[str]] = {}
    for path in _package_pyprojects():
        text = path.read_text(encoding="utf-8")
        registrations[tomllib.loads(text)["project"]["name"]] = registered_names_from_toml(text)
    return registrations


def test_scan_surface_is_not_empty():
    assert sibling_station_dirs(), f"no sibling pyforge-* stations under {PACKAGES_ROOT}"
    assert _station_pyprojects(), "no sibling station pyproject.toml files to scan"


def test_no_sibling_station_declares_a_parallel_plugin_group():
    failures: list[str] = []
    for path in _station_pyprojects():
        hits = parallel_loader_violations(path.read_text(encoding="utf-8"))
        if hits:
            failures.append(f"{path}: {hits}")
    assert not failures, (
        "sibling station pyproject.toml declared a parallel plugin group "
        f"(only {_CANONICAL_GROUP!r} is allowed): {failures}"
    )


def test_no_sibling_station_imports_pluggy():
    failures: list[str] = []
    for path in station_source_files():
        hits = pluggy_import_violations(path.read_text(encoding="utf-8"))
        if hits:
            failures.append(f"{path}: {hits}")
    assert not failures, (
        "sibling station source imports pluggy — a parallel plugin loader "
        f"(use {_CANONICAL_GROUP!r} / pyforge.core.hooks instead): {failures}"
    )


def test_detector_fires_on_a_synthetic_parallel_hooks_group():
    """Non-vacuous: a station-shaped ``pyforge.warden.hooks`` group IS flagged."""
    synthetic = """
[project.entry-points."pyforge.warden.hooks"]
gate = "pyforge.warden.hooks:GatePlugin"
"""
    assert parallel_loader_violations(synthetic) == ["pyforge.warden.hooks"]


def test_detector_fires_on_a_synthetic_parallel_plugins_group():
    synthetic = """
[project.entry-points."pyforge.mason.plugins"]
tool = "pyforge.mason.plugins:Tool"
"""
    assert parallel_loader_violations(synthetic) == ["pyforge.mason.plugins"]


def test_detector_fires_on_unquoted_nested_entry_point_tables():
    synthetic = """
[project.entry-points.pyforge.herald.hooks]
x = "herald.hooks:X"
"""
    assert parallel_loader_violations(synthetic) == ["pyforge.herald.hooks"]


def test_detector_does_not_fire_on_the_canonical_group():
    allowed = """
[project.entry-points."pyforge.core.hooks"]
core-dummy = "pyforge.core.hooks:DummyPlugin"
"""
    assert parallel_loader_violations(allowed) == []


def test_detector_does_not_fire_on_pytest_or_django_plugin_groups():
    other = """
[project.entry-points.pytest11]
mine = "pkg.plugin"
[project.entry-points.django]
app = "pkg.apps:App"
"""
    assert parallel_loader_violations(other) == []


def test_pluggy_detector_fires_on_a_synthetic_import():
    assert pluggy_import_violations("import pluggy\n")
    assert pluggy_import_violations("from pluggy import PluginManager\n")


def test_pluggy_detector_does_not_fire_on_unrelated_imports():
    assert not pluggy_import_violations("import importlib.metadata\n")


def test_every_registered_name_starts_with_its_package_token():
    registrations = _registrations()
    assert sum(len(names) for names in registrations.values()) >= 2, f"no {_CANONICAL_GROUP!r} names found to check"
    failures = {package: bad for package, names in registrations.items() if (bad := unprefixed_names(package, names))}
    assert not failures, (
        f"a name registered on {_CANONICAL_GROUP!r} must start with its package token and a hyphen "
        f"(pyforge-mason registers mason-...): {failures}"
    )


def test_no_name_is_registered_twice_across_the_packages():
    repeats = repeated_names(_registrations())
    assert not repeats, f"a name is registered on {_CANONICAL_GROUP!r} by more than one package: {repeats}"


def test_name_check_fires_on_a_bare_name_and_on_a_bare_prefix():
    synthetic = """
[project.entry-points."pyforge.core.hooks"]
rattler-build = "pyforge.mason.engines.build_hooks:RattlerBuildPlugin"
mason- = "pyforge.mason.engines.build_hooks:CondaBuildPlugin"
mason-engine-conda-build = "pyforge.mason.engines.build_hooks:CondaBuildPlugin"
"""
    assert unprefixed_names("pyforge-mason", registered_names_from_toml(synthetic)) == ["rattler-build", "mason-"]


def test_name_check_reads_a_hyphenated_package_token():
    assert unprefixed_names("pyforge-testing-kit", ["testing-kit-fake", "testing-fake"]) == ["testing-fake"]


def test_repeat_check_fires_on_a_name_two_packages_register():
    repeats = repeated_names({"pyforge-mason": ["mason-a"], "pyforge-steward": ["mason-a", "steward-b"]})
    assert repeats == {"mason-a": ["pyforge-mason", "pyforge-steward"]}
