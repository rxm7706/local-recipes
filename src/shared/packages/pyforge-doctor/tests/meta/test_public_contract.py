"""Story 57.2 (spec-pyforge-doctor CAP-97; FR-28 <- CAP-97; decision D1 of the 2026-11-10 cutover
readiness plan): Doctor's public contract is one companion file, and this module reds what it lacks.

``contract.md`` sits beside the station Spec. It is hand-written: nothing generates it and no CLI verb
renders it. This module reads the code and the file, each by an explicit path under the repository
root, and compares them both ways. A verb, option, MCP tool, feature-flag key, environment variable,
exit code, Source, check code, computed ``check=`` site or import that the code has and the file lacks
is reported *missing*; a line the file carries that no code backs is reported *stale*.

What it reads from the code:

* the parsers ``doctor`` (``pyforge.doctor.__main__._build_parser``) and the sources dispatcher
  (``pyforge.doctor.sources.__main__._build_parser``) build, walked verb by verb;
* ``DISPATCH``, the ``Source`` enum and ``sources.REGISTRY`` (scope and subject per Source);
* every ``check=`` keyword in the package, and the code a ``Finding(...)`` (under any name the module
  binds to it) with no ``check=`` passes in ``check``'s place (positionally, or through a ``*`` / ``**``
  argument), by AST: a string literal, a module-level constant (an f-string over other constants and
  ``Source.<M>.value`` included), or a helper parameter the helper never rebinds, resolved through the
  helper's call sites to the literal or constant each caller passes (a public helper's in every module;
  a private helper's in its own module and in each module that imports it by name, directly or through
  a re-export of any number of hops, never in a module that merely defines a function of the same
  name). Anything else is a *computed site*, and it must
  have its own row in ``## Computed check sites``; that is how "every diagnostic" holds without
  refactoring those call sites. The helper rule fails closed: a helper that no readable call binds, a
  method, a private helper reached through an attribute in any module, a private helper imported under
  another name (anywhere along a re-export chain) or by a module that also defines that name, a call
  whose ``*`` or ``**`` argument may
  bind the parameter (or that omits it with no default), and a helper loaded as a value (a callback) or
  a public helper imported under another name is itself a computed site, ``(module, helper,
  parameter)``. In a module whose ``check=`` reads ``<row>['kind']``, the item rows' ``"kind"`` values
  (``{"kind": ...}``, ``dict(kind=...)``, ``<row>['kind'] = ...``, ``<row>.update(kind=...)``,
  ``<row>.setdefault('kind', ...)``; never a Finding's ``evidence=``) are its codes, and a value no
  reading resolves is a computed site ``(module, function, value)``. The
  other codes of computed sites that can be enumerated are the strings a loop binds over a literal
  tuple and the ``HygieneFindingKind`` member a site names;
* every feature-flag read, ``(key, module, reader)``: ``pyforge.core.flags`` / ``django_pyforge.flags``
  readers and each OpenFeature ``get_<type>_value`` / ``_details`` method (sync and async), the key
  read positionally or by keyword (``key=``, ``flag_key=``), the reader under any name the module binds
  to it or on a name bound to a flags module; a key no reading resolves, a ``*`` / ``**`` key and a
  reader loaded as a value read ``<expr>``;
* the ``os.environ`` / ``os.environb`` / ``os.getenv`` reads (``get``, ``setdefault``, ``pop``,
  subscript, ``in``), under any name the module binds to them (``from os import environ as E``,
  ``E = os.environ``, a copy such as ``env = dict(os.environ)`` in its own function), the key read
  positionally or as ``key=`` (a key bound by a ``for`` loop over a literal tuple is a computed
  environment read, with its own row), and the keys set on a copy of ``os.environ`` for a child process;
* the exit constants of ``verdict.py``, the ``*_TOOL`` constants of django-doctor's ``mcp_asgi.py``,
  and the package's non-stdlib imports.

It reads the Spec folder and django-doctor, outside this package, so it is a live-tree module and runs
in ``pyforge-doctor-live-test``. The ``mutation`` tests feed the same comparison synthetic input (an
extra flag, verb, check code, feature-flag key, environment key, Source, MCP tool and computed site,
each reading rule's own fail-closed case, and a contract line no code backs) and prove each direction
fires; the live tree reads no flag key, so only they prove the flag-key reader.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import tomllib
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field, fields
from enum import StrEnum
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from pyforge.doctor import __main__ as doctor_cli
from pyforge.doctor import sources as doctor_sources
from pyforge.doctor.hygiene_definitions import HygieneFindingKind
from pyforge.doctor.models import Finding, Source
from pyforge.doctor.sources import __main__ as dispatcher

pytestmark = pytest.mark.live_tree

# Explicit paths, relative to the repository root (no root hand-off: nothing below takes a target).
_CONTRACT = "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/contract.md"
_PACKAGE = "src/shared/packages/pyforge-doctor"
_PACKAGE_SRC = f"{_PACKAGE}/src/pyforge/doctor"
_MCP_ASGI = "src/shared/packages/django-doctor/src/django_doctor_portal/mcp_asgi.py"

# Decision D1's sections, plus inputs and bridges (AC1 reads the same list).
_SECTIONS = (
    "CLI",
    "MCP tools",
    "Feature-flag keys",
    "Environment variables",
    "Exit codes",
    "Sources",
    "Check codes",
    "Computed check sites",
    "Bridges and import closure",
    "Inputs each source reads",
    "Identity constants",
    "Scripts outside the package",
    "Python floor",
)

# Every feature-flag read call, with where it takes its key: (position, keyword). pyforge.core.flags's and
# django_pyforge.flags's readers, and each OpenFeature client evaluation method (``get_<type>_value`` and
# ``get_<type>_details``, sync and async; the key is ``flag_key``). Doctor reads no key today (the kill
# switch takes one as an argument).
_FLAG_READERS: Mapping[str, tuple[int, str]] = {
    "read_boolean": (0, "key"),
    "kill_switch_on": (0, "key"),
    "require": (0, "key"),
    "disabled_help": (1, "key"),
    "evaluate_boolean": (0, "key"),
    "evaluate_cli_boolean": (0, "key"),
    **{
        f"get_{kind}_{form}{mode}": (0, "flag_key")
        for kind in ("boolean", "string", "integer", "float", "object")
        for form in ("value", "details")
        for mode in ("", "_async")
    },
}
# The modules whose functions are flag readers. Two of their names are too common to match anywhere, so they
# count only when bound from one of these modules (imported by name, or called on a name bound to the module).
_FLAG_MODULES = frozenset({"pyforge.core.flags", "django_pyforge.flags"})
_FLAG_MODULE_ONLY = frozenset({"require", "disabled_help"})
_ENUMS: Mapping[str, type[StrEnum]] = {"Source": Source}
_MODULE_LEVEL = "<module>"
# Where a positional ``Finding(...)`` carries its code: the dataclass's own field order.
_FINDING_CHECK_INDEX = [each.name for each in fields(Finding)].index("check")

Item = tuple[str, ...]


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / "_bmad-output").is_dir():
            return candidate
    raise AssertionError("could not locate the repository root (pixi.toml beside _bmad-output/)")


def _diff(label: str, code: Iterable[Item], contract: Iterable[Item]) -> list[str]:
    """Both directions, one line per item: what the code has and the file lacks, and the reverse."""
    code_set, contract_set = set(code), set(contract)
    missing = [f"missing from contract.md § {label}: {' | '.join(item)}" for item in sorted(code_set - contract_set)]
    stale = [
        f"stale in contract.md § {label} (no code backs it): {' | '.join(item)}"
        for item in sorted(contract_set - code_set)
    ]
    return missing + stale


# --------------------------------------------------------------------------------------------------
# The code side.
# --------------------------------------------------------------------------------------------------


def _package_modules(root: Path) -> dict[str, str]:
    """Every module of the package, keyed by its path under ``src/pyforge/doctor`` (posix)."""
    base = root / _PACKAGE_SRC
    return {
        path.relative_to(base).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(base.rglob("*.py"))
        if "__pycache__" not in path.parts
    }


def _cli_items(parsers: Iterable[argparse.ArgumentParser]) -> tuple[set[Item], set[Item]]:
    """Each verb path and each (verb path, option) the parsers accept; help is argparse's, not ours."""
    verbs: set[Item] = set()
    options: set[Item] = set()

    def walk(parser: argparse.ArgumentParser, path: str) -> None:
        verbs.add((path,))
        for action in parser._actions:
            if isinstance(action, argparse._HelpAction):
                continue
            if isinstance(action, argparse._SubParsersAction):
                for name, sub in action.choices.items():
                    walk(sub, f"{path} {name}")
                continue
            for name in action.option_strings or [action.dest]:
                options.add((path, name))

    for parser in parsers:
        walk(parser, parser.prog)
    return verbs, options


def _mcp_tool_items(text: str) -> set[Item]:
    """The ``*_TOOL`` constants of django-doctor's ``mcp_asgi.py``: (tool name, constant)."""
    items: set[Item] = set()
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name.endswith("_TOOL") and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                items.add((node.value.value, name))
    return items


def _exit_items(text: str) -> set[Item]:
    """``verdict.py``'s exit constants: (code, constant)."""
    items: set[Item] = set()
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if re.fullmatch(r"_?EXIT_[A-Z_]+", name) and isinstance(node.value, ast.Constant):
                items.add((str(node.value.value), name))
    return items


def _source_items(members: Iterable[StrEnum], registry: Iterable[Any], dispatch: Iterable[str]) -> set[Item]:
    """(Source, scope, subject station, dispatched) for every member of the Source enum; a member with no
    registration reads ``?`` for both."""
    by_value = {reg.source.value: reg for reg in registry}
    dispatched = set(dispatch)
    items: set[Item] = set()
    for member in members:
        reg = by_value.get(member.value)
        scope, subject = (reg.scope, reg.subject_station) if reg is not None else ("?", "?")
        items.add((member.value, scope, subject, "yes" if member.value in dispatched else "no"))
    return items


def _evaluate(node: ast.expr, consts: Mapping[str, str]) -> str | None:
    """A string the expression always evaluates to, or None: a literal, a module constant, an
    f-string or ``+`` over those, or ``Source.<M>.value``."""
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.Name):
        return consts.get(node.id)
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue) and value.conversion == -1 and value.format_spec is None:
                inner = _evaluate(value.value, consts)
                if inner is None:
                    return None
                parts.append(inner)
            else:
                return None
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _evaluate(node.left, consts), _evaluate(node.right, consts)
        return None if left is None or right is None else left + right
    if (
        isinstance(node, ast.Attribute)
        and node.attr == "value"
        and isinstance(node.value, ast.Attribute)
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id in _ENUMS
    ):
        member = _ENUMS[node.value.value.id].__members__.get(node.value.attr)
        return None if member is None else member.value
    return None


def _module_constants(tree: ast.Module) -> dict[str, str]:
    consts: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name, value = node.targets[0].id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            name, value = node.target.id, node.value
        else:
            continue
        resolved = _evaluate(value, consts)
        if resolved is None:
            consts.pop(name, None)
        else:
            consts[name] = resolved
    return consts


Function = ast.FunctionDef | ast.AsyncFunctionDef


def _walk(tree: ast.AST) -> Iterator[tuple[ast.AST, Function | None]]:
    """Every node with its nearest enclosing function (None at module level)."""
    stack: list[tuple[ast.AST, Function | None]] = [(tree, None)]
    while stack:
        node, function = stack.pop()
        yield node, function
        inner = node if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else function
        stack.extend((child, inner) for child in ast.iter_child_nodes(node))


def _function_name(function: Function | None) -> str:
    return _MODULE_LEVEL if function is None else function.name


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


@dataclass(frozen=True)
class EnvironNames:
    """The names a module binds to ``os.environ`` (or ``os.environb``) and to ``os.getenv``."""

    environ: frozenset[str] = frozenset({"environ", "environb"})
    getenv: frozenset[str] = frozenset({"getenv"})


def _environ_names(tree: ast.Module) -> EnvironNames:
    """``os.environ`` / ``os.environb`` / ``os.getenv`` and every other name a module binds to them: a
    ``from os import environ as E`` alias, and a plain assignment (``E = os.environ``, ``read = os.getenv``)."""
    environ, getenv = {"environ", "environb"}, {"getenv"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "os" and not node.level:
            for alias in node.names:
                if alias.name in ("environ", "environb"):
                    environ.add(alias.asname or alias.name)
                elif alias.name == "getenv":
                    getenv.add(alias.asname or alias.name)
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                target, value = node.targets[0].id, node.value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
                target, value = node.target.id, node.value
            else:
                continue
            names = EnvironNames(frozenset(environ), frozenset(getenv))
            if _is_environ(value, names) and target not in environ:
                environ.add(target)
                changed = True
            elif _is_getenv(value, names) and target not in getenv:
                getenv.add(target)
                changed = True
    return EnvironNames(frozenset(environ), frozenset(getenv))


def _is_environ(node: ast.expr, names: EnvironNames = EnvironNames()) -> bool:
    return (
        isinstance(node, ast.Attribute) and node.attr in ("environ", "environb") and isinstance(node.value, ast.Name)
    ) or (isinstance(node, ast.Name) and node.id in names.environ)


def _is_getenv(node: ast.expr, names: EnvironNames = EnvironNames()) -> bool:
    return (isinstance(node, ast.Attribute) and node.attr == "getenv") or (
        isinstance(node, ast.Name) and node.id in names.getenv
    )


def _environment_key(node: ast.AST, names: EnvironNames = EnvironNames()) -> ast.expr | None:
    """The key expression of an environment read, or None when ``node`` is not one. A read is
    ``<environ>.get`` / ``.setdefault`` / ``.pop``, ``getenv``, ``<environ>[...]`` and ``... in <environ>``,
    where ``<environ>`` is any name ``names`` binds to the environment (a copy of it included). A call's key
    is its first positional argument or its ``key=`` keyword (``os.getenv(key="K")``); a call that passes
    neither yields its ``*`` / ``**`` argument, which no reading resolves, so it is a computed read."""
    if isinstance(node, ast.Call):
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr in ("get", "setdefault", "pop")
            and _is_environ(func.value, names)
        ) or _is_getenv(func, names):
            if node.args:
                return node.args[0]
            for keyword in node.keywords:
                if keyword.arg in ("key", None):
                    return keyword.value
            return None
    if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load) and _is_environ(node.value, names):
        return node.slice
    if (
        isinstance(node, ast.Compare)
        and len(node.ops) == 1
        and isinstance(node.ops[0], (ast.In, ast.NotIn))
        and _is_environ(node.comparators[0], names)
    ):
        return node.left
    return None


def _module_literals(tree: ast.Module) -> dict[str, object]:
    """Module-level names bound to a plain literal (a tuple of tuples of strings, say)."""
    literals: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                literals[node.targets[0].id] = ast.literal_eval(node.value)
            except ValueError, TypeError, SyntaxError:
                continue
    return literals


def _loop_values(
    function: Function | None, name: str, consts: Mapping[str, str], literals: Mapping[str, object]
) -> tuple[str, ...] | None:
    """The strings a ``for`` loop (or comprehension) of the function binds to ``name``, when it iterates
    a literal or a module-level literal: ``for key in ("A", "B")``, ``for _n, check in _PAIRS``."""
    if function is None:
        return None
    for node in ast.walk(function):
        if not isinstance(node, (ast.For, ast.comprehension)):
            continue
        target = node.target
        if isinstance(target, ast.Name) and target.id == name:
            index: int | None = None
        elif isinstance(target, ast.Tuple) and any(isinstance(e, ast.Name) and e.id == name for e in target.elts):
            index = next(i for i, e in enumerate(target.elts) if isinstance(e, ast.Name) and e.id == name)
        else:
            continue
        values: list[object]
        if isinstance(node.iter, (ast.Tuple, ast.List, ast.Set)):
            values = []
            for element in node.iter.elts:
                if index is None:
                    values.append(_evaluate(element, consts))
                elif isinstance(element, (ast.Tuple, ast.List)) and len(element.elts) > index:
                    values.append(_evaluate(element.elts[index], consts))
                else:
                    values.append(None)
        elif isinstance(node.iter, ast.Name) and isinstance(literals.get(node.iter.id), (tuple, list, set, frozenset)):
            container = literals[node.iter.id]
            assert isinstance(container, (tuple, list, set, frozenset))
            values = [
                element
                if index is None
                else (element[index] if isinstance(element, (tuple, list)) and len(element) > index else None)
                for element in container
            ]
        else:
            continue
        if values and all(isinstance(value, str) for value in values):
            return tuple(sorted({value for value in values if isinstance(value, str)}))
    return None


def _is_environ_copy(node: ast.expr, names: EnvironNames) -> bool:
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "dict" and len(node.args) == 1:
            return _is_environ(node.args[0], names)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "copy":
            return _is_environ(node.func.value, names)
    if isinstance(node, ast.Dict):
        return any(key is None and _is_environ(value, names) for key, value in zip(node.keys, node.values, strict=True))
    return False


def _environ_copies(
    nodes: list[tuple[ast.AST, Function | None]], names: EnvironNames
) -> dict[int | None, frozenset[str]]:
    """The names bound to a copy of the environment (``dict(os.environ)``, ``os.environ.copy()``,
    ``{**os.environ}``, a copy of a copy), per function (its id; None at module level, which every function
    sees). A read through a copy is an environment read like any other."""
    copies: dict[int | None, set[str]] = {}
    changed = True
    while changed:
        changed = False
        for node, function in nodes:
            if not isinstance(node, ast.Assign):
                continue
            scope = None if function is None else id(function)
            seen = copies.setdefault(scope, set())
            local = EnvironNames(names.environ | copies.get(None, set()) | seen, names.getenv)
            if _is_environ_copy(node.value, local):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id not in seen:
                        seen.add(target.id)
                        changed = True
    return {scope: frozenset(bound) for scope, bound in copies.items()}


def _environment_key_value(node: ast.expr, consts: Mapping[str, str]) -> str | None:
    """An environment key's string: what ``_evaluate`` reads, or a bytes literal (``os.environb``) decoded."""
    if isinstance(node, ast.Constant) and isinstance(node.value, bytes):
        return node.value.decode("utf-8", "replace")
    return _evaluate(node, consts)


@dataclass
class CodeFacts:
    """What the package's AST says, keyed the way contract.md's tables are."""

    check_codes: set[Item] = field(default_factory=set)  # (module, code)
    computed_check_sites: set[Item] = field(default_factory=set)  # (module, function, expression)
    environment_read: set[Item] = field(default_factory=set)  # (key, module)
    computed_environment_reads: set[Item] = field(default_factory=set)  # (module, function, key expr, keys)
    environment_children: set[Item] = field(default_factory=set)  # (key, module)
    flag_keys: set[Item] = field(default_factory=set)  # (key, module, reader)
    imports: set[Item] = field(default_factory=set)  # (dotted module,)
    source_modules: dict[str, set[str]] = field(default_factory=dict)  # Source member name -> modules


@dataclass(frozen=True)
class FlagNames:
    """The names a module binds to a flag reader (a bare name -> the reader it is) and to a flags module."""

    readers: Mapping[str, str]
    modules: frozenset[str]


def _flag_reader_of(node: ast.expr, names: FlagNames) -> str | None:
    """The flag reader an expression names, or None: a bare name bound to one, or an attribute whose name is
    a reader's (a common name only on a flags module: ``fl.require``, ``pyforge.core.flags.require``)."""
    if isinstance(node, ast.Name):
        return names.readers.get(node.id)
    if isinstance(node, ast.Attribute) and node.attr in _FLAG_READERS:
        if node.attr not in _FLAG_MODULE_ONLY:
            return node.attr
        owner = node.value
        if (isinstance(owner, ast.Name) and owner.id in names.modules) or ast.unparse(owner) in _FLAG_MODULES:
            return node.attr
    return None


def _alias_assignments(tree: ast.Module) -> Iterator[tuple[str, ast.expr]]:
    """``target = value`` pairs of plain single-name assignments, annotated ones included."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            yield node.targets[0].id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            yield node.target.id, node.value


def _flag_names(tree: ast.Module) -> FlagNames:
    """Every name a module binds to a flag reader or a flags module: the readers' own names (but the common
    ones), ``from <flags module> import read_boolean as rb``, ``from pyforge.core import flags as fl``,
    ``import pyforge.core.flags as fl``, and a plain assignment (``rb = fl.read_boolean``,
    ``get = client.get_boolean_value``, ``fl2 = fl``)."""
    readers = {name: name for name in _FLAG_READERS if name not in _FLAG_MODULE_ONLY}
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for alias in node.names:
                bound = alias.asname or alias.name
                if alias.name in _FLAG_READERS and (
                    node.module in _FLAG_MODULES or alias.name not in _FLAG_MODULE_ONLY
                ):
                    readers[bound] = alias.name
                if f"{node.module}.{alias.name}" in _FLAG_MODULES:
                    modules.add(bound)
        elif isinstance(node, ast.Import):
            modules.update(alias.asname for alias in node.names if alias.name in _FLAG_MODULES and alias.asname)
    changed = True
    while changed:
        changed = False
        names = FlagNames(dict(readers), frozenset(modules))
        for target, value in _alias_assignments(tree):
            reader = _flag_reader_of(value, names)
            if reader is not None and target not in readers:
                readers[target] = reader
                changed = True
            elif isinstance(value, ast.Name) and value.id in modules and target not in modules:
                modules.add(target)
                changed = True
    return FlagNames(readers, frozenset(modules))


def _flag_key(call: ast.Call, reader: str, consts: Mapping[str, str]) -> str:
    """The key a reader call reads: its key argument (positional or keyword) evaluated, else ``<expr>``; a
    key a ``*`` / ``**`` argument may carry, or no key at all, reads ``<call>``."""
    position, keyword = _FLAG_READERS[reader]
    argument: ast.expr | None = next((each.value for each in call.keywords if each.arg == keyword), None)
    if argument is None:
        starred = [index for index, arg in enumerate(call.args) if isinstance(arg, ast.Starred)]
        if not (starred and starred[0] <= position) and position < len(call.args):
            argument = call.args[position]
    if argument is None:
        return f"<{ast.unparse(call)}>"
    key = _evaluate(argument, consts)
    return key if key is not None else f"<{ast.unparse(argument)}>"


def _flag_reads(module: str, tree: ast.Module, consts: Mapping[str, str]) -> set[Item]:
    """(key, module, reader) for every flag reader call in a module, and ``(<expr>, module, reader)`` for a
    reader loaded as a value (a callback, ``functools.partial``), whose key no reading resolves."""
    names = _flag_names(tree)
    # Loaded as a callee or bound by an alias assignment: read at the call, never as a value.
    called = {id(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)}
    called |= {id(value) for _target, value in _alias_assignments(tree) if _flag_reader_of(value, names) is not None}
    items: set[Item] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            reader = _flag_reader_of(node.func, names)
            if reader is not None:
                items.add((_flag_key(node, reader, consts), module, reader))
        elif (
            isinstance(node, (ast.Name, ast.Attribute))
            and isinstance(node.ctx, ast.Load)
            and id(node) not in called
            and (reader := _flag_reader_of(node, names)) is not None
        ):
            items.add((f"<{ast.unparse(node)}>", module, reader))
    return items


def _code_facts(modules: Mapping[str, str]) -> CodeFacts:
    facts = CodeFacts()
    trees = {module: ast.parse(text) for module, text in modules.items()}
    consts = {module: _module_constants(tree) for module, tree in trees.items()}
    literals = {module: _module_literals(tree) for module, tree in trees.items()}
    walked = {module: list(_walk(tree)) for module, tree in trees.items()}
    methods = {module: _methods(tree) for module, tree in trees.items()}
    environ = {module: _environ_names(tree) for module, tree in trees.items()}
    copies = {module: _environ_copies(walked[module], environ[module]) for module in trees}
    scoped: dict[tuple[str, int | None], EnvironNames] = {}

    def environ_in(module: str, function: Function | None) -> EnvironNames:
        """The module's environment names plus the copies its module level and ``function`` bind."""
        scope = None if function is None else id(function)
        if (module, scope) not in scoped:
            extra = copies[module].get(None, frozenset()) | copies[module].get(scope, frozenset())
            scoped[module, scope] = EnvironNames(environ[module].environ | extra, environ[module].getenv)
        return scoped[module, scope]

    findings = {module: _finding_names(tree) for module, tree in trees.items()}
    dotted = {module: _dotted(module) for module in trees}
    kind_modules: set[str] = set()
    helpers: list[tuple[str, Function, str]] = []  # (module, function, parameter)
    seen_helpers: set[tuple[str, int, str]] = set()

    def computed(module: str, function: Function | None, value: ast.expr) -> None:
        """A site no reading resolves: its row, plus the strings a loop binds to it over a literal."""
        if isinstance(value, ast.Name):
            looped = _loop_values(function, value.id, consts[module], literals[module])
            facts.check_codes.update((module, each) for each in looped or ())
        facts.computed_check_sites.add((module, _function_name(function), ast.unparse(value)))

    def resolve(module: str, function: Function | None, value: ast.expr) -> None:
        code = _evaluate(value, consts[module])
        if code is not None:
            facts.check_codes.add((module, code))
            return
        if (
            isinstance(value, ast.Name)
            and function is not None
            and value.id in _parameters(function)
            and not _rebinds(function, value.id)
        ):
            key = (module, id(function), value.id)
            if key not in seen_helpers:
                seen_helpers.add(key)
                helpers.append((module, function, value.id))
            return
        # A parameter the helper rebinds before ``check=`` no longer carries its callers' value.
        computed(module, function, value)
        if isinstance(value, ast.Subscript) and _evaluate(value.slice, {}) == "kind":
            kind_modules.add(module)
        if (
            isinstance(value, ast.Attribute)
            and value.attr == "value"
            and isinstance(value.value, ast.Attribute)
            and isinstance(value.value.value, ast.Name)
            and value.value.value.id == HygieneFindingKind.__name__
            and value.value.attr in HygieneFindingKind.__members__
        ):
            facts.check_codes.add((module, HygieneFindingKind[value.value.attr].value))

    for module, nodes in walked.items():
        for node, function in nodes:
            if isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if keyword.arg != "check":
                        continue
                    if isinstance(keyword.value, ast.Constant) and not isinstance(keyword.value.value, str):
                        continue  # subprocess.run(check=False): a flag, not a code
                    resolve(module, function, keyword.value)
                argument = _finding_check_argument(node, findings[module])
                if isinstance(argument, str):
                    facts.computed_check_sites.add((module, _function_name(function), argument))
                elif argument is not None:
                    resolve(module, function, argument)
            key_node = _environment_key(node, environ_in(module, function))
            if key_node is not None:
                key = _environment_key_value(key_node, consts[module])
                if key is not None:
                    facts.environment_read.add((key, module))
                else:
                    keys = (
                        _loop_values(function, key_node.id, consts[module], literals[module])
                        if isinstance(key_node, ast.Name)
                        else None
                    )
                    facts.computed_environment_reads.add(
                        (module, _function_name(function), ast.unparse(key_node), ", ".join(keys or ("?",)))
                    )
                    facts.environment_read.update((each, module) for each in keys or ())
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                facts.imports.update((name,) for name in _imported(node))
            if (
                isinstance(node, ast.Call)
                and _call_name(node) == "import_module"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                facts.imports.update((name,) for name in _external((node.args[0].value,)))
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "Source"
                and node.attr in Source.__members__
            ):
                facts.source_modules.setdefault(node.attr, set()).add(module)
        _children(module, nodes, consts[module], environ[module], facts)
        facts.flag_keys |= _flag_reads(module, trees[module], consts[module])

    # A helper's parameter carries the code its callers pass: resolve each call site until no new helper
    # appears. A public helper's calls are read in every module; a private helper's in its own module and
    # in each module that imports it by name (``from .<module> import _emit``), never in a module that
    # merely defines a function of the same name. It fails closed: a helper no readable call binds (or
    # leaves to its default), a method, a private helper reached through an attribute in any module
    # (``self._emit(...)``, ``<module>._emit(...)``), a call whose ``*`` or ``**`` argument may bind the
    # parameter or that omits it with no default, and the helper loaded as a value (a callback) or
    # imported under another name each make the helper a computed site of its own, (module, helper,
    # parameter), so the table must name it.
    while helpers:
        helper_module, definition, parameter = helpers.pop()
        helper_name = definition.name
        private = helper_name.startswith("_")
        positional = [arg.arg for arg in (*definition.args.posonlyargs, *definition.args.args)]
        index = positional.index(parameter) if parameter in positional else None
        default = _default(definition, parameter)
        readable = 0
        method = id(definition) in methods[helper_module]  # self/cls shifts every positional binding
        unreadable = method
        importers = _private_importers(walked, dotted, helper_module, helper_name) if private else {}
        for module, nodes in walked.items():
            if method:
                break
            if private and module != helper_module:
                how = importers.get(module)
                if how is None:
                    # Not imported by name, it is still reachable as an attribute (``<module>._emit``);
                    # any same-named attribute fails closed, since the AST cannot tell whose it is.
                    unreadable |= any(
                        isinstance(node, ast.Attribute) and node.attr == helper_name for node, _f in nodes
                    )
                    continue
                if how == "aliased" or _binds(trees[module], helper_name):
                    unreadable = True
                    continue
            called = {id(node.func) for node, _function in nodes if isinstance(node, ast.Call)}
            for node, function in nodes:
                if _names_as_value(node, helper_name, called):
                    unreadable = True
                    continue
                if not (isinstance(node, ast.Call) and _call_name(node) == helper_name):
                    continue
                if private and isinstance(node.func, ast.Attribute):
                    unreadable = True  # another object's method, or this one called as self._name(...)
                    continue
                how, bound = _bound(node, parameter, index)
                if how == "bound" and bound is not None:
                    resolve(module, function, bound)
                    readable += 1
                elif how == "default" and default is not None:
                    resolve(helper_module, definition, default)
                    readable += 1
                else:
                    unreadable = True
        if unreadable or not readable:
            facts.computed_check_sites.add((helper_module, helper_name, parameter))

    # A module whose ``check=`` reads ``<row>['kind']`` emits every ``"kind"`` its item rows carry: the
    # value of a ``"kind"`` key in a dict literal or a ``dict(kind=...)`` call, and of a
    # ``<row>['kind'] = ...`` assignment (never a Finding's ``evidence=``). A value no reading resolves
    # is a computed site of its own, (module, function, value).
    for module in kind_modules:
        evidence = {
            id(keyword.value)
            for node, _function in walked[module]
            if isinstance(node, ast.Call)
            for keyword in node.keywords
            if keyword.arg == "evidence"
        }
        for node, function in walked[module]:
            if id(node) in evidence:
                continue
            for value in _kind_values(node):
                code = _evaluate(value, consts[module])
                if code is None:
                    computed(module, function, value)
                else:
                    facts.check_codes.add((module, code))
    return facts


def _kind_values(node: ast.AST) -> list[ast.expr]:
    """The values an item row's ``"kind"`` takes at ``node``: ``{"kind": v}``, ``dict(kind=v)``,
    ``<row>["kind"] = v``, ``<row>.update(kind=v)`` and ``<row>.setdefault("kind", v)``."""
    if isinstance(node, ast.Dict):
        return [
            value
            for key, value in zip(node.keys, node.values, strict=True)
            if key is not None and _evaluate(key, {}) == "kind"
        ]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict":
        return [keyword.value for keyword in node.keywords if keyword.arg == "kind"]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr == "update":
            return [keyword.value for keyword in node.keywords if keyword.arg == "kind"]
        if node.func.attr == "setdefault" and len(node.args) == 2 and _evaluate(node.args[0], {}) == "kind":
            return [node.args[1]]
    if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(isinstance(target, ast.Subscript) and _evaluate(target.slice, {}) == "kind" for target in targets):
            return [node.value]
    return []


def _rebinds(function: Function, name: str) -> bool:
    """Whether the function's body binds ``name`` again (an assignment, a loop or ``with`` target, an
    ``except ... as``, an import, a match capture), so a parameter of that name stops carrying its
    callers' value."""
    for node in ast.walk(function):
        if isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, (ast.Store, ast.Del)):
            return True
        if isinstance(node, ast.ExceptHandler) and node.name == name:
            return True
        if isinstance(node, (ast.Import, ast.ImportFrom)) and any(
            (alias.asname or alias.name.split(".")[0]) == name for alias in node.names
        ):
            return True
        if isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name == name:
            return True
        if isinstance(node, ast.MatchMapping) and node.rest == name:
            return True
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and node is not function
            and node.name == name
        ):
            return True
    return False


def _binds(tree: ast.Module, name: str) -> bool:
    """Whether a module defines ``name`` itself (a function, a class or an assignment)."""
    return any(
        (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name)
        or (isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, ast.Store))
        for node in ast.walk(tree)
    )


def _dotted(module: str) -> str:
    """``sources/chain.py`` -> ``pyforge.doctor.sources.chain``; a package's ``__init__.py`` is the package."""
    parts = ["pyforge", "doctor", *module.removesuffix(".py").split("/")]
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _import_target(importer: str, node: ast.ImportFrom) -> str | None:
    """The dotted module a ``from ... import`` in ``importer`` names, relative levels resolved."""
    if not node.level:
        return node.module
    package = _dotted(importer).split(".")
    if not importer.endswith("__init__.py"):
        package.pop()
    if node.level > 1:
        package = package[: len(package) - (node.level - 1)]
    return ".".join([*package, *([node.module] if node.module else [])])


def _private_importers(
    walked: Mapping[str, list[tuple[ast.AST, Function | None]]],
    dotted: Mapping[str, str],
    helper_module: str,
    name: str,
) -> dict[str, str]:
    """Each module that imports the private helper ``name`` by name, and how (``"plain"`` or
    ``"aliased"``): from the module that defines it, or from a module that itself imports it plainly (a
    re-export, any number of hops: ``from .b import _emit`` where ``b`` imported it from ``a``)."""
    exporters = {dotted[helper_module]}
    importers: dict[str, str] = {}
    changed = True
    while changed:
        changed = False
        for module, nodes in walked.items():
            if module == helper_module or importers.get(module) == "aliased":
                continue
            hows = {_private_import(module, nodes, exporter, name) for exporter in exporters} - {None}
            how = "aliased" if "aliased" in hows else "plain" if hows else None
            if how is not None and importers.get(module) != how:
                importers[module] = how
                if how == "plain":
                    exporters.add(dotted[module])
                changed = True
    return importers


def _private_import(importer: str, nodes: list[tuple[ast.AST, Function | None]], target: str, name: str) -> str | None:
    """How ``importer`` imports ``name`` from the module ``target``: ``"plain"``, ``"aliased"`` (under
    another name, so its calls cannot be read by name) or None (it does not)."""
    how: str | None = None
    for node, _function in nodes:
        if isinstance(node, ast.ImportFrom) and _import_target(importer, node) == target:
            for alias in node.names:
                if alias.name == name:
                    if alias.asname not in (None, name):
                        return "aliased"
                    how = "plain"
    return how


def _finding_names(tree: ast.Module) -> frozenset[str]:
    """``Finding`` and every other name a module binds to it: a ``from ... import Finding as F`` alias,
    and a plain assignment (``F = Finding``)."""
    names = {Finding.__name__}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update(alias.asname for alias in node.names if alias.name == Finding.__name__ and alias.asname)
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Name)
                and node.value.id in names
                and node.targets[0].id not in names
            ):
                names.add(node.targets[0].id)
                changed = True
    return frozenset(names)


def _parameters(function: Function) -> set[str]:
    args = function.args
    return {arg.arg for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs)}


def _methods(tree: ast.Module) -> set[int]:
    """The ids of the functions defined directly in a class body."""
    return {
        id(child)
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        for child in node.body
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _names_as_value(node: ast.AST, name: str, called: set[int]) -> bool:
    """``name`` used other than as the callee of a call: a callback, a stored reference, an alias."""
    if isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, ast.Load):
        return id(node) not in called
    if isinstance(node, ast.Attribute) and node.attr == name and isinstance(node.ctx, ast.Load):
        return id(node) not in called
    if isinstance(node, ast.ImportFrom):
        return any(alias.name == name and alias.asname not in (None, name) for alias in node.names)
    return False


def _finding_check_argument(call: ast.Call, names: frozenset[str]) -> ast.expr | str | None:
    """The code a ``Finding(...)`` (under any name the module binds to it) with no ``check=`` passes: the
    positional argument in ``check``'s place, or, when a ``*`` / ``**`` argument may carry it, that
    argument unparsed (a computed site)."""
    if _call_name(call) not in names or any(keyword.arg == "check" for keyword in call.keywords):
        return None
    for position, argument in enumerate(call.args):
        if isinstance(argument, ast.Starred):
            return ast.unparse(argument)
        if position == _FINDING_CHECK_INDEX:
            return argument
    for keyword in call.keywords:
        if keyword.arg is None:
            return f"**{ast.unparse(keyword.value)}"
    return None


def _default(function: Function, parameter: str) -> ast.expr | None:
    args = function.args
    positional = [*args.posonlyargs, *args.args]
    offset = len(positional) - len(args.defaults)
    for position, arg in enumerate(positional):
        if arg.arg == parameter and position >= offset:
            return args.defaults[position - offset]
    for arg, kw_default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
        if arg.arg == parameter:
            return kw_default
    return None


def _bound(call: ast.Call, parameter: str, index: int | None) -> tuple[str, ast.expr | None]:
    """How a call binds a helper's parameter: ``("bound", <argument>)``; ``("default", None)`` when the
    call leaves it to the default; ``("unreadable", None)`` when a ``*`` or ``**`` argument may bind it."""
    for keyword in call.keywords:
        if keyword.arg == parameter:
            return "bound", keyword.value
    if index is not None:
        starred = [position for position, arg in enumerate(call.args) if isinstance(arg, ast.Starred)]
        if starred and starred[0] <= index:
            return "unreadable", None
        if index < len(call.args):
            return "bound", call.args[index]
    if any(keyword.arg is None for keyword in call.keywords):
        return "unreadable", None
    return "default", None


def _imported(node: ast.Import | ast.ImportFrom) -> list[str]:
    if isinstance(node, ast.Import):
        return _external(alias.name for alias in node.names)
    if node.level or node.module is None:
        return []
    return _external((node.module,))


def _external(names: Iterable[str]) -> list[str]:
    """Imports that leave the package and the standard library."""
    return [
        name
        for name in names
        if name.split(".")[0] not in sys.stdlib_module_names
        and name != "__future__"
        and not (name == "pyforge.doctor" or name.startswith("pyforge.doctor."))
    ]


def _children(
    module: str,
    nodes: list[tuple[ast.AST, Function | None]],
    consts: Mapping[str, str],
    environ: EnvironNames,
    facts: CodeFacts,
) -> None:
    """Keys set on a copy of ``os.environ`` handed to a child process: written, never read."""
    copies: set[tuple[str, str]] = set()  # (function, name)
    for node, function in nodes:
        if isinstance(node, ast.Assign) and _is_environ_copy(node.value, environ):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    copies.add((_function_name(function), target.id))
    for node, function in nodes:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Name)
                    and (_function_name(function), target.value.id) in copies
                ):
                    key = _evaluate(target.slice, consts)
                    facts.environment_children.add(
                        (key if key is not None else f"<{ast.unparse(target.slice)}>", module)
                    )


# --------------------------------------------------------------------------------------------------
# The contract side.
# --------------------------------------------------------------------------------------------------

Table = tuple[tuple[str, ...], list[tuple[str, ...]]]


def _sections(text: str) -> dict[str, str]:
    """``## <name>`` -> its body, up to the next ``## ``."""
    sections: dict[str, str] = {}
    current: str | None = None
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(lines)
            current, lines = line[3:].strip(), []
        elif current is not None:
            lines.append(line)
    if current is not None:
        sections[current] = "\n".join(lines)
    return sections


def _cells(line: str) -> tuple[str, ...]:
    return tuple(cell.strip() for cell in line.strip().strip("|").split("|"))


def _tables(body: str) -> list[Table]:
    tables: list[Table] = []
    header: tuple[str, ...] | None = None
    rows: list[tuple[str, ...]] = []
    for line in [*body.splitlines(), ""]:
        if line.strip().startswith("|"):
            cells = _cells(line)
            if header is None:
                header = cells
            elif not all(set(cell) <= set("-: ") for cell in cells):
                rows.append(cells)
        elif header is not None:
            tables.append((header, rows))
            header, rows = None, []
    return tables


def _ticks(cell: str) -> list[str]:
    return re.findall(r"`([^`]+)`", cell)


def _plain(cell: str) -> str:
    return cell.replace("`", "").strip()


def _column(header: tuple[str, ...], name: str) -> int:
    return header.index(name)


def _rows(sections: Mapping[str, str], section: str, first: str) -> Iterator[tuple[tuple[str, ...], tuple[str, ...]]]:
    """Each row of each table in ``section`` whose first header cell is ``first``."""
    for header, rows in _tables(sections.get(section, "")):
        if header and header[0] == first:
            for row in rows:
                yield header, row


@dataclass
class ContractFacts:
    verbs: set[Item] = field(default_factory=set)
    options: set[Item] = field(default_factory=set)
    mcp_tools: set[Item] = field(default_factory=set)
    flag_keys: set[Item] = field(default_factory=set)
    environment_read: set[Item] = field(default_factory=set)
    environment_children: set[Item] = field(default_factory=set)
    exit_codes: set[Item] = field(default_factory=set)
    sources: set[Item] = field(default_factory=set)
    source_capability: dict[str, str] = field(default_factory=dict)
    source_modules: dict[str, set[str]] = field(default_factory=dict)
    check_codes: set[Item] = field(default_factory=set)
    check_code_rows: set[Item] = field(default_factory=set)  # (source, module)
    computed_check_sites: set[Item] = field(default_factory=set)
    computed_environment_reads: set[Item] = field(default_factory=set)
    imports: set[Item] = field(default_factory=set)
    input_sources: set[Item] = field(default_factory=set)
    identity: set[Item] = field(default_factory=set)  # (constant, module, value)
    scripts: set[Item] = field(default_factory=set)
    python_floor: set[str] = field(default_factory=set)


def _contract_facts(text: str) -> ContractFacts:
    sections = _sections(text)
    facts = ContractFacts()
    for header, row in _rows(sections, "CLI", "Verb"):
        verb = _ticks(row[0])[0]
        if "Option" in header:
            facts.options.update((verb, option) for option in _ticks(row[_column(header, "Option")]))
        else:
            facts.verbs.add((verb,))
    for header, row in _rows(sections, "MCP tools", "Tool"):
        facts.mcp_tools.add((_ticks(row[0])[0], _ticks(row[_column(header, "Constant")])[0]))
    for header, row in _rows(sections, "Feature-flag keys", "Key"):
        facts.flag_keys.add(
            (_ticks(row[0])[0], _ticks(row[_column(header, "Module")])[0], _ticks(row[_column(header, "Reader")])[0])
        )
    for header, row in _rows(sections, "Environment variables", "Variable read"):
        facts.environment_read.add((_ticks(row[0])[0], _ticks(row[_column(header, "Module")])[0]))
    for header, row in _rows(sections, "Environment variables", "Variable set for a child process"):
        facts.environment_children.add((_ticks(row[0])[0], _ticks(row[_column(header, "Module")])[0]))
    for header, row in _rows(sections, "Exit codes", "Code"):
        if "Constant" in header:
            facts.exit_codes.add((_ticks(row[0])[0], _ticks(row[_column(header, "Constant")])[0]))
    for header, row in _rows(sections, "Sources", "Source"):
        source = _ticks(row[0])[0]
        facts.sources.add(
            (
                source,
                _plain(row[_column(header, "Scope")]),
                _plain(row[_column(header, "Subject")]),
                _plain(row[_column(header, "Dispatcher")]),
            )
        )
        facts.source_capability[source] = row[_column(header, "Governing capability")]
        facts.source_modules[source] = set(_ticks(row[_column(header, "Modules")]))
    for header, row in _rows(sections, "Check codes", "Source"):
        source, module = _ticks(row[0])[0], _ticks(row[_column(header, "Module")])[0]
        facts.check_code_rows.add((source, module))
        facts.check_codes.update((module, code) for code in _ticks(row[_column(header, "Codes")]))
    for header, row in _rows(sections, "Computed check sites", "Module"):
        module, function = _ticks(row[0])[0], _ticks(row[_column(header, "Function")])[0]
        if "Keys" in header:
            expression = _ticks(row[_column(header, "Key expression")])[0]
            keys = ", ".join(sorted(_ticks(row[_column(header, "Keys")])))
            facts.computed_environment_reads.add((module, function, expression, keys))
        else:
            facts.computed_check_sites.add((module, function, _ticks(row[_column(header, "Expression")])[0]))
    for _header, row in _rows(sections, "Bridges and import closure", "Import"):
        facts.imports.add((_ticks(row[0])[0],))
    for _header, row in _rows(sections, "Inputs each source reads", "Source"):
        facts.input_sources.add((_ticks(row[0])[0],))
    for header, row in _rows(sections, "Identity constants", "Constant"):
        facts.identity.add(
            (_ticks(row[0])[0], _ticks(row[_column(header, "Module")])[0], _ticks(row[_column(header, "Value")])[0])
        )
    for _header, row in _rows(sections, "Scripts outside the package", "Script"):
        facts.scripts.add((_ticks(row[0])[0],))
    facts.python_floor = set(_ticks(sections.get("Python floor", "")))
    return facts


# --------------------------------------------------------------------------------------------------
# Fixtures: the live tree, read once.
# --------------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def root() -> Path:
    return _repo_root()


@pytest.fixture(scope="module")
def contract_text(root: Path) -> str:
    return (root / _CONTRACT).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def contract(contract_text: str) -> ContractFacts:
    return _contract_facts(contract_text)


@pytest.fixture(scope="module")
def modules(root: Path) -> dict[str, str]:
    return _package_modules(root)


@pytest.fixture(scope="module")
def code(modules: dict[str, str]) -> CodeFacts:
    return _code_facts(modules)


def _parsers() -> list[argparse.ArgumentParser]:
    return [doctor_cli._build_parser()[0], dispatcher._build_parser()]


def _real_sources() -> set[Item]:
    return _source_items(Source, doctor_sources.REGISTRY, dispatcher.DISPATCH)


# --------------------------------------------------------------------------------------------------
# The live tree: code and contract agree, both ways.
# --------------------------------------------------------------------------------------------------


def test_contract_has_every_section(contract_text: str) -> None:
    headings = {line[3:].strip() for line in contract_text.splitlines() if line.startswith("## ")}
    assert [section for section in _SECTIONS if section not in headings] == []


def test_cli_verbs_and_options_match_the_contract(contract: ContractFacts) -> None:
    verbs, options = _cli_items(_parsers())
    assert _diff("CLI (verbs)", verbs, contract.verbs) + _diff("CLI (options)", options, contract.options) == []


def test_mcp_tools_match_the_contract(root: Path, contract: ContractFacts) -> None:
    tools = _mcp_tool_items((root / _MCP_ASGI).read_text(encoding="utf-8"))
    assert tools, "django-doctor's mcp_asgi.py declares no *_TOOL constant"
    assert _diff("MCP tools", tools, contract.mcp_tools) == []


def test_feature_flag_keys_match_the_contract(code: CodeFacts, contract: ContractFacts) -> None:
    assert _diff("Feature-flag keys", code.flag_keys, contract.flag_keys) == []


def test_environment_variables_match_the_contract(code: CodeFacts, contract: ContractFacts) -> None:
    assert (
        _diff("Environment variables (read)", code.environment_read, contract.environment_read)
        + _diff("Environment variables (set for a child)", code.environment_children, contract.environment_children)
        == []
    )


def test_exit_codes_match_the_contract(root: Path, contract: ContractFacts) -> None:
    codes = _exit_items((root / _PACKAGE_SRC / "verdict.py").read_text(encoding="utf-8"))
    assert {code for code, _constant in codes} == {"0", "2", "130"}
    assert _diff("Exit codes", codes, contract.exit_codes) == []


def test_sources_match_the_contract(contract: ContractFacts) -> None:
    assert _diff("Sources", _real_sources(), contract.sources) == []


def test_every_source_names_its_governing_capability(contract: ContractFacts) -> None:
    unnamed = [source for source, cell in contract.source_capability.items() if not re.search(r"\bCAP-\d+\b", cell)]
    assert unnamed == []


def test_every_source_row_names_the_modules_that_emit_it(code: CodeFacts, contract: ContractFacts) -> None:
    problems: list[str] = []
    for source, listed in sorted(contract.source_modules.items()):
        member = Source(source).name
        referencing = code.source_modules.get(member, set())
        if not listed:
            problems.append(f"{source}: no module listed")
        problems += [f"{source}: {module} never names Source.{member}" for module in sorted(listed - referencing)]
    assert problems == []


def test_check_codes_match_the_contract(code: CodeFacts, contract: ContractFacts) -> None:
    assert _diff("Check codes", code.check_codes, contract.check_codes) == []


def test_every_check_code_row_belongs_to_a_source_of_its_module(contract: ContractFacts) -> None:
    problems = [
        f"{source} | {module}"
        for source, module in sorted(contract.check_code_rows)
        if module not in contract.source_modules.get(source, set())
    ]
    without_codes = sorted({source for source, *_rest in contract.sources} - {s for s, _m in contract.check_code_rows})
    assert problems == []
    assert without_codes == []


def test_computed_sites_check_rows_equal_the_ast(code: CodeFacts, contract: ContractFacts) -> None:
    assert _diff("Computed check sites", code.computed_check_sites, contract.computed_check_sites) == []


def test_computed_sites_environment_rows_equal_the_ast(code: CodeFacts, contract: ContractFacts) -> None:
    assert (
        _diff(
            "Computed check sites (environment reads)",
            code.computed_environment_reads,
            contract.computed_environment_reads,
        )
        == []
    )


def test_import_closure_matches_the_contract(code: CodeFacts, contract: ContractFacts) -> None:
    assert _diff("Bridges and import closure", code.imports, contract.imports) == []


def test_inputs_name_every_source(contract: ContractFacts) -> None:
    assert _diff("Inputs each source reads", {(member.value,) for member in Source}, contract.input_sources) == []


def test_identity_constants_are_the_code_s(root: Path, modules: dict[str, str], contract: ContractFacts) -> None:
    assert contract.identity, "## Identity constants lists nothing"
    problems: list[str] = []
    schemas = {
        f"data/{path.name}": json.loads(path.read_text(encoding="utf-8")).get("$id")
        for path in sorted((root / _PACKAGE_SRC / "data").glob("*.json"))
    }
    listed_schemas = {module for constant, module, _value in contract.identity if constant == "$id"}
    problems += [f"schema {module}: no $id row" for module in sorted(set(schemas) - listed_schemas)]
    for constant, module, value in sorted(contract.identity):
        if constant == "$id":
            actual = schemas.get(module)
        else:
            actual = _module_constants(ast.parse(modules[module])).get(constant) if module in modules else None
        if actual != value:
            problems.append(f"{constant} in {module}: contract {value!r}, code {actual!r}")
    assert problems == []


def test_scripts_outside_the_package_exist(root: Path, contract: ContractFacts) -> None:
    assert contract.scripts, "## Scripts outside the package lists nothing"
    assert sorted(script for (script,) in contract.scripts if not (root / script).is_file()) == []


def test_python_floor_matches_pyproject(root: Path, contract: ContractFacts) -> None:
    pyproject = tomllib.loads((root / _PACKAGE / "pyproject.toml").read_text(encoding="utf-8"))
    floor = {pyproject["project"]["requires-python"], pyproject["tool"]["ruff"]["target-version"]}
    assert floor == {">=3.14", "py314"}
    assert floor <= contract.python_floor


# --------------------------------------------------------------------------------------------------
# Mutation: the same comparison, fed synthetic input, fires both ways.
# --------------------------------------------------------------------------------------------------

_SYNTHETIC = "sources/synthetic_mutation.py"


def _with_synthetic(modules: Mapping[str, str], text: str) -> dict[str, str]:
    return {**modules, _SYNTHETIC: text}


def test_mutation_an_extra_flag_is_missing(contract: ContractFacts) -> None:
    parser, check, *_rest = doctor_cli._build_parser()
    check.add_argument("--synthetic-flag", action="store_true")
    _verbs, options = _cli_items([parser, dispatcher._build_parser()])
    assert "missing from contract.md § CLI (options): doctor check | --synthetic-flag" in _diff(
        "CLI (options)", options, contract.options
    )


def test_mutation_an_extra_verb_is_missing(contract: ContractFacts) -> None:
    parser = doctor_cli._build_parser()[0]
    subparsers = next(action for action in parser._actions if isinstance(action, argparse._SubParsersAction))
    subparsers.add_parser("synthetic-verb")
    verbs, _options = _cli_items([parser])
    assert "missing from contract.md § CLI (verbs): doctor synthetic-verb" in _diff(
        "CLI (verbs)", verbs, contract.verbs
    )


def test_mutation_an_extra_check_code_is_missing(modules: dict[str, str], contract: ContractFacts) -> None:
    text = 'def gather():\n    return Finding(source=Source.WRITER_LOCK, check="synthetic-code", status=None)\n'
    facts = _code_facts(_with_synthetic(modules, text))
    assert f"missing from contract.md § Check codes: {_SYNTHETIC} | synthetic-code" in _diff(
        "Check codes", facts.check_codes, contract.check_codes
    )


def test_mutation_a_helper_argument_is_resolved_to_its_code(modules: dict[str, str], contract: ContractFacts) -> None:
    text = (
        "def _emit(check):\n"
        "    return Finding(source=Source.WRITER_LOCK, check=check, status=None)\n\n"
        "_CODE = f'{Source.WRITER_LOCK.value}-synthetic'\n\n"
        "def gather():\n"
        "    return (_emit('synthetic-helper-code'), _emit(check=_CODE))\n"
    )
    facts = _code_facts(_with_synthetic(modules, text))
    diff = _diff("Check codes", facts.check_codes, contract.check_codes)
    assert f"missing from contract.md § Check codes: {_SYNTHETIC} | synthetic-helper-code" in diff
    assert f"missing from contract.md § Check codes: {_SYNTHETIC} | writer-lock-synthetic" in diff
    assert not any(site[0] == _SYNTHETIC for site in facts.computed_check_sites)


_EMIT = "def _emit(check):\n    return Finding(source=Source.WRITER_LOCK, check=check, status=None)\n\n"

# A helper whose callers the AST cannot bind fails closed: (module, helper, parameter) is a computed site.
# Every case but "never-called" and "private-method" also has a readable direct call, so the one rule the
# case names is the only thing that can make the helper a site.
_UNREADABLE_HELPERS = {
    "method": (
        "class Emitter:\n"
        "    def emit_synthetic(self, check, detail=''):\n"
        "        return Finding(source=Source.WRITER_LOCK, check=check, status=None)\n\n"
        "def gather():\n"
        "    return Emitter().emit_synthetic('silent-code-a', 'detail')\n",
        "emit_synthetic | check",
    ),
    "private-method": (
        "class _Emitter:\n"
        "    def _emit(self, check):\n"
        "        return Finding(source=Source.WRITER_LOCK, check=check, status=None)\n\n"
        "    def gather(self):\n"
        "        return self._emit('silent-code-l')\n",
        "_emit | check",
    ),
    "callback": (
        _EMIT + "def gather():\n    return (_emit('synthetic-direct'), list(map(_emit, ['silent-code-d'])))\n",
        "_emit | check",
    ),
    "double-star": (
        # A default, so only the ``**`` rule (not the omitted-with-no-default one) can make it a site.
        "def _emit(check='synthetic-default'):\n"
        "    return Finding(source=Source.WRITER_LOCK, check=check, status=None)\n\n"
        "def gather():\n"
        "    return (_emit('synthetic-direct'), _emit(**{'check': 'silent-code-c'}))\n",
        "_emit | check",
    ),
    "omitted-without-default": (
        _EMIT + "def gather():\n    return (_emit('synthetic-direct'), _emit())\n",
        "_emit | check",
    ),
    "starred": (
        _EMIT + "def gather():\n    return (_emit('synthetic-direct'), _emit(*('silent-code-f',)))\n",
        "_emit | check",
    ),
    "never-called": (_EMIT, "_emit | check"),
    "private-attribute": (
        _EMIT + "def gather(other):\n    return (_emit('synthetic-direct'), other._emit('silent-code-g'))\n",
        "_emit | check",
    ),
    "aliased": (
        "from pyforge.doctor.sources.synthetic_mutation import emit as send\n\n"
        "def emit(check):\n"
        "    return Finding(source=Source.WRITER_LOCK, check=check, status=None)\n\n"
        "def gather():\n"
        "    return (emit('synthetic-direct'), send('silent-code-h'))\n",
        "emit | check",
    ),
    "rebound-parameter": (
        "def _emit(check):\n"
        "    check = check.strip()\n"
        "    return Finding(source=Source.WRITER_LOCK, check=check, status=None)\n\n"
        "def gather():\n"
        "    return _emit('silent-code-k')\n",
        "_emit | check",
    ),
}


@pytest.mark.parametrize("case", sorted(_UNREADABLE_HELPERS))
def test_mutation_an_unreadable_helper_is_a_computed_site(
    case: str, modules: dict[str, str], contract: ContractFacts
) -> None:
    text, site = _UNREADABLE_HELPERS[case]
    facts = _code_facts(_with_synthetic(modules, text))
    assert f"missing from contract.md § Computed check sites: {_SYNTHETIC} | {site}" in _diff(
        "Computed check sites", facts.computed_check_sites, contract.computed_check_sites
    )


# A private helper reached from a second module. The defining module has its own readable call, so only
# the second module can make the helper a site (or add a code).
_SYNTHETIC_CALLER = "sources/synthetic_caller.py"
_DEFINING = _EMIT + "def gather():\n    return _emit('synthetic-direct')\n"
_CROSS_MODULE = {
    "imported": ("from .synthetic_mutation import _emit\n\ndef gather():\n    return _emit('silent-code-b')\n", None),
    "imported-absolute": (
        "from pyforge.doctor.sources.synthetic_mutation import _emit\n\ndef gather():\n    return _emit('silent-code-m')\n",
        None,
    ),
    "imported-aliased": (
        "from .synthetic_mutation import _emit as send\n\ndef gather():\n    return send('silent-code-i')\n",
        "site",
    ),
    "module-attribute": (
        "from . import synthetic_mutation\n\ndef gather():\n    return synthetic_mutation._emit('silent-code-c')\n",
        "site",
    ),
    "imported-callback": (
        "from .synthetic_mutation import _emit\n\ndef gather():\n    return list(map(_emit, ['silent-code-j']))\n",
        "site",
    ),
    "imported-and-redefined": (
        "from .synthetic_mutation import _emit\n\n_emit = print\n\ndef gather():\n    return _emit('silent-code-n')\n",
        "site",
    ),
}


@pytest.mark.parametrize("case", sorted(_CROSS_MODULE))
def test_mutation_a_private_helper_reached_from_another_module(
    case: str, modules: dict[str, str], contract: ContractFacts
) -> None:
    caller, expect = _CROSS_MODULE[case]
    facts = _code_facts({**modules, _SYNTHETIC: _DEFINING, _SYNTHETIC_CALLER: caller})
    site = f"missing from contract.md § Computed check sites: {_SYNTHETIC} | _emit | check"
    sites = _diff("Computed check sites", facts.computed_check_sites, contract.computed_check_sites)
    if expect == "site":
        assert site in sites
    else:
        # A plain import reads like a local call: the code is the caller's, and the helper is no site.
        code = re.search(r"'(silent-code-\w)'", caller)
        assert code is not None
        assert f"missing from contract.md § Check codes: {_SYNTHETIC_CALLER} | {code.group(1)}" in _diff(
            "Check codes", facts.check_codes, contract.check_codes
        )
        assert site not in sites


def test_mutation_same_named_private_helpers_are_not_merged(modules: dict[str, str]) -> None:
    caller = _EMIT + "def gather():\n    return _emit('own-code')\n"
    facts = _code_facts({**modules, _SYNTHETIC: _DEFINING, _SYNTHETIC_CALLER: caller})
    ours = {item for item in facts.check_codes if item[0] in (_SYNTHETIC, _SYNTHETIC_CALLER)}
    assert ours == {(_SYNTHETIC, "synthetic-direct"), (_SYNTHETIC_CALLER, "own-code")}
    assert not any(site[0] in (_SYNTHETIC, _SYNTHETIC_CALLER) for site in facts.computed_check_sites)


# A private helper re-exported: the caller imports it from a module that imported it (any number of hops, a
# package ``__init__`` included). A plain chain reads like a local call; an alias anywhere makes it a site.
_SYNTHETIC_RELAY = "sources/synthetic_relay.py"
_RE_EXPORTED = {
    "one-hop": (
        {
            _SYNTHETIC_RELAY: "from .synthetic_mutation import _emit\n",
            _SYNTHETIC_CALLER: "from .synthetic_relay import _emit\n\ndef gather():\n    return _emit('silent-code-o')\n",
        },
        "silent-code-o",
    ),
    "two-hops": (
        {
            _SYNTHETIC_RELAY: "from .synthetic_mutation import _emit\n",
            "sources/synthetic_relay_two.py": "from pyforge.doctor.sources.synthetic_relay import _emit\n",
            _SYNTHETIC_CALLER: "from .synthetic_relay_two import _emit\n\ndef gather():\n    return _emit('silent-code-p')\n",
        },
        "silent-code-p",
    ),
    "package-init": (
        {
            "sources/__init__.py": "\nfrom .synthetic_mutation import _emit\n",
            _SYNTHETIC_CALLER: "from . import _emit\n\ndef gather():\n    return _emit('silent-code-q')\n",
        },
        "silent-code-q",
    ),
    "one-hop-aliased": (
        {
            _SYNTHETIC_RELAY: "from .synthetic_mutation import _emit\n",
            _SYNTHETIC_CALLER: "from .synthetic_relay import _emit as send\n\ndef gather():\n    return send('silent-code-r')\n",
        },
        None,
    ),
}


@pytest.mark.parametrize("case", sorted(_RE_EXPORTED))
def test_mutation_a_re_exported_private_helper_is_read(
    case: str, modules: dict[str, str], contract: ContractFacts
) -> None:
    files, code = _RE_EXPORTED[case]
    extra = {path: modules.get(path, "") + text for path, text in files.items()}
    facts = _code_facts({**modules, _SYNTHETIC: _DEFINING, **extra})
    site = f"missing from contract.md § Computed check sites: {_SYNTHETIC} | _emit | check"
    sites = _diff("Computed check sites", facts.computed_check_sites, contract.computed_check_sites)
    if code is None:
        assert site in sites
    else:
        assert f"missing from contract.md § Check codes: {_SYNTHETIC_CALLER} | {code}" in _diff(
            "Check codes", facts.check_codes, contract.check_codes
        )
        assert site not in sites


def test_mutation_a_positional_finding_is_read(modules: dict[str, str], contract: ContractFacts) -> None:
    text = (
        "def gather(rest, kwargs):\n"
        "    return (\n"
        "        Finding(Source.WRITER_LOCK, 'silent-code-e', None, '', {}),\n"
        "        Finding(Source.WRITER_LOCK, *rest),\n"
        "        Finding(Source.WRITER_LOCK, **kwargs),\n"
        "    )\n"
    )
    facts = _code_facts(_with_synthetic(modules, text))
    assert f"missing from contract.md § Check codes: {_SYNTHETIC} | silent-code-e" in _diff(
        "Check codes", facts.check_codes, contract.check_codes
    )
    sites = _diff("Computed check sites", facts.computed_check_sites, contract.computed_check_sites)
    assert f"missing from contract.md § Computed check sites: {_SYNTHETIC} | gather | *rest" in sites
    assert f"missing from contract.md § Computed check sites: {_SYNTHETIC} | gather | **kwargs" in sites


def test_mutation_a_finding_under_another_name_is_read(modules: dict[str, str], contract: ContractFacts) -> None:
    text = (
        "from pyforge.doctor.models import Finding as Report\n\n"
        "def gather():\n"
        "    return Report(Source.WRITER_LOCK, 'silent-code-alias', None, '', {})\n"
    )
    facts = _code_facts(_with_synthetic(modules, text))
    assert f"missing from contract.md § Check codes: {_SYNTHETIC} | silent-code-alias" in _diff(
        "Check codes", facts.check_codes, contract.check_codes
    )


def test_mutation_an_extra_environment_key_is_missing(modules: dict[str, str], contract: ContractFacts) -> None:
    text = "import os\n\ndef token():\n    return os.environ.get('PYFORGE_SYNTHETIC_KEY')\n"
    facts = _code_facts(_with_synthetic(modules, text))
    assert f"missing from contract.md § Environment variables: PYFORGE_SYNTHETIC_KEY | {_SYNTHETIC}" in _diff(
        "Environment variables", facts.environment_read, contract.environment_read
    )


_ENVIRONMENT_FORMS = {
    "getenv-keyword": "import os\n\ndef token():\n    return os.getenv(key='PYFORGE_SYNTHETIC_KEY')\n",
    "environ-get-keyword": "import os\n\ndef token():\n    return os.environ.get(key='PYFORGE_SYNTHETIC_KEY')\n",
    "environ-assigned": "import os\n\nENV = os.environ\n\ndef token():\n    return ENV.get('PYFORGE_SYNTHETIC_KEY')\n",
    "environ-imported-as": "from os import environ as ENV\n\ndef token():\n    return ENV['PYFORGE_SYNTHETIC_KEY']\n",
    "getenv-imported-as": "from os import getenv as read\n\ndef token():\n    return read('PYFORGE_SYNTHETIC_KEY')\n",
    "copy-dict": "import os\n\ndef token():\n    env = dict(os.environ)\n    return env.get('PYFORGE_SYNTHETIC_KEY')\n",
    "copy-method": "import os\n\ndef token():\n    env = os.environ.copy()\n    return env['PYFORGE_SYNTHETIC_KEY']\n",
    "copy-unpacked": "import os\n\ndef token():\n    env = {**os.environ}\n    return 'PYFORGE_SYNTHETIC_KEY' in env\n",
    "copy-of-a-copy": (
        "import os\n\ndef token():\n    env = dict(os.environ)\n    child = env.copy()\n"
        "    return child.get('PYFORGE_SYNTHETIC_KEY')\n"
    ),
    "copy-module-level": "import os\n\n_ENV = dict(os.environ)\n\ndef token():\n    return _ENV.get('PYFORGE_SYNTHETIC_KEY')\n",
    "setdefault": "import os\n\ndef token():\n    return os.environ.setdefault('PYFORGE_SYNTHETIC_KEY', '')\n",
    "pop": "import os\n\ndef token():\n    return os.environ.pop('PYFORGE_SYNTHETIC_KEY', None)\n",
    "environb": "import os\n\ndef token():\n    return os.environb.get(b'PYFORGE_SYNTHETIC_KEY')\n",
    "environb-imported-as": "from os import environb as ENVB\n\ndef token():\n    return ENVB[b'PYFORGE_SYNTHETIC_KEY']\n",
}


@pytest.mark.parametrize("case", sorted(_ENVIRONMENT_FORMS))
def test_mutation_an_environment_read_in_another_form_is_missing(
    case: str, modules: dict[str, str], contract: ContractFacts
) -> None:
    facts = _code_facts(_with_synthetic(modules, _ENVIRONMENT_FORMS[case]))
    assert f"missing from contract.md § Environment variables: PYFORGE_SYNTHETIC_KEY | {_SYNTHETIC}" in _diff(
        "Environment variables", facts.environment_read, contract.environment_read
    )


def test_mutation_a_copy_is_read_only_in_its_own_function(modules: dict[str, str]) -> None:
    """A name bound to a copy in one function is no environment in another; a key set on it is a child's."""
    text = (
        "import os\n\n"
        "def child():\n    env = dict(os.environ)\n    env['PYFORGE_SYNTHETIC_CHILD'] = '1'\n    return env\n\n"
        "def other(env):\n    return env.get('NOT_AN_ENVIRONMENT_KEY')\n"
    )
    facts = _code_facts(_with_synthetic(modules, text))
    assert ("PYFORGE_SYNTHETIC_CHILD", _SYNTHETIC) in facts.environment_children
    assert not any(module == _SYNTHETIC for _key, module in facts.environment_read)


# Every form a feature-flag read takes: the key positional or by keyword, a constant, each OpenFeature
# evaluation method, the reader under an alias or reached through a flags module, and the fail-closed forms
# (a computed key, a ``*`` argument, the reader loaded as a value) whose key reads ``<expr>``.
_FLAG_FORMS = {
    "positional": (
        "from pyforge.core.flags import read_boolean\n\ndef gate():\n    return read_boolean('pyforge.synthetic')\n",
        "pyforge.synthetic",
        "read_boolean",
    ),
    "keyword": (
        "from pyforge.core.flags import read_boolean\n\n"
        "def gate():\n    return read_boolean(default=True, key='pyforge.synthetic')\n",
        "pyforge.synthetic",
        "read_boolean",
    ),
    "constant": (
        "from pyforge.core.flags import read_boolean\n\n_KEY = 'pyforge.synthetic'\n\n"
        "def gate():\n    return read_boolean(_KEY)\n",
        "pyforge.synthetic",
        "read_boolean",
    ),
    "openfeature-keyword": (
        "def gate(client):\n    return client.get_boolean_value(flag_key='pyforge.synthetic', default_value=False)\n",
        "pyforge.synthetic",
        "get_boolean_value",
    ),
    "openfeature-positional": (
        "def gate(client):\n    return client.get_string_value('pyforge.synthetic', '')\n",
        "pyforge.synthetic",
        "get_string_value",
    ),
    "openfeature-details-async": (
        "async def gate(client):\n"
        "    return await client.get_object_details_async(default_value={}, flag_key='pyforge.synthetic')\n",
        "pyforge.synthetic",
        "get_object_details_async",
    ),
    "aliased-import": (
        "from pyforge.core.flags import read_boolean as rb\n\ndef gate():\n    return rb('pyforge.synthetic')\n",
        "pyforge.synthetic",
        "read_boolean",
    ),
    "module-alias": (
        "from pyforge.core import flags as fl\n\ndef gate():\n    return fl.require('pyforge.synthetic')\n",
        "pyforge.synthetic",
        "require",
    ),
    "module-import-as": (
        "import pyforge.core.flags as fl\n\ndef gate():\n    return fl.disabled_help('help', key='pyforge.synthetic')\n",
        "pyforge.synthetic",
        "disabled_help",
    ),
    "module-dotted": (
        "import pyforge.core.flags\n\n"
        "def gate():\n    return pyforge.core.flags.disabled_help('help', 'pyforge.synthetic')\n",
        "pyforge.synthetic",
        "disabled_help",
    ),
    "assigned": (
        "from pyforge.core import flags\n\nswitch = flags.kill_switch_on\n\n"
        "def gate():\n    return switch('pyforge.synthetic')\n",
        "pyforge.synthetic",
        "kill_switch_on",
    ),
    "assigned-method": (
        "def gate(client):\n    get = client.get_integer_value\n    return get('pyforge.synthetic', 0)\n",
        "pyforge.synthetic",
        "get_integer_value",
    ),
    "django-aliased": (
        "from django_pyforge.flags import evaluate_boolean as evaluate\n\n"
        "def gate():\n    return evaluate('pyforge.synthetic')\n",
        "pyforge.synthetic",
        "evaluate_boolean",
    ),
    "computed": (
        "from pyforge.core.flags import read_boolean\n\ndef gate(prefix):\n    return read_boolean(prefix + '.synthetic')\n",
        "<prefix + '.synthetic'>",
        "read_boolean",
    ),
    "starred": (
        "from pyforge.core.flags import read_boolean\n\ndef gate(args):\n    return read_boolean(*args)\n",
        "<read_boolean(*args)>",
        "read_boolean",
    ),
    "callback": (
        "from pyforge.core.flags import read_boolean\n\ndef gate(keys):\n    return list(map(read_boolean, keys))\n",
        "<read_boolean>",
        "read_boolean",
    ),
}


@pytest.mark.parametrize("case", sorted(_FLAG_FORMS))
def test_mutation_a_flag_key_in_each_form_is_missing(
    case: str, modules: dict[str, str], contract: ContractFacts
) -> None:
    text, key, reader = _FLAG_FORMS[case]
    facts = _code_facts(_with_synthetic(modules, text))
    assert f"missing from contract.md § Feature-flag keys: {key} | {_SYNTHETIC} | {reader}" in _diff(
        "Feature-flag keys", facts.flag_keys, contract.flag_keys
    )


def test_mutation_a_listed_flag_key_is_neither_missing_nor_stale(modules: dict[str, str]) -> None:
    """A ``Key | Module | Reader`` row parses to exactly the item the code side reads."""
    text, key, reader = _FLAG_FORMS["aliased-import"]
    facts = _code_facts(_with_synthetic(modules, text))
    listed = _contract_facts(
        f"## Feature-flag keys\n\n| Key | Module | Reader |\n|---|---|---|\n| `{key}` | `{_SYNTHETIC}` | `{reader}` |\n"
    )
    assert listed.flag_keys == {(key, _SYNTHETIC, reader)}
    assert _diff("Feature-flag keys", facts.flag_keys, listed.flag_keys) == []


def test_mutation_a_common_name_off_a_flags_module_is_no_flag_key(modules: dict[str, str]) -> None:
    """``require`` and ``disabled_help`` count only when bound from a flags module."""
    text = (
        "def require(name):\n    return name\n\n"
        "def gate(other):\n    return require('pyforge.synthetic'), other.disabled_help('help', 'pyforge.synthetic')\n"
    )
    facts = _code_facts(_with_synthetic(modules, text))
    assert not any(item[1] == _SYNTHETIC for item in facts.flag_keys)


def test_mutation_an_extra_source_is_missing(contract: ContractFacts) -> None:
    synthetic = StrEnum("Synthetic", {**{m.name: m.value for m in Source}, "SYNTHETIC": "synthetic-source"})
    registry = [
        *doctor_sources.REGISTRY,
        SimpleNamespace(source=synthetic.SYNTHETIC, scope="repo", subject_station="fleet"),
    ]
    items = _source_items(synthetic, registry, [*dispatcher.DISPATCH, "synthetic-source"])
    assert "missing from contract.md § Sources: synthetic-source | repo | fleet | yes" in _diff(
        "Sources", items, contract.sources
    )


def test_mutation_an_extra_mcp_tool_is_missing(root: Path, contract: ContractFacts) -> None:
    text = (root / _MCP_ASGI).read_text(encoding="utf-8") + '\nSYNTHETIC_SCAN_TOOL = "synthetic_scan"\n'
    assert "missing from contract.md § MCP tools: synthetic_scan | SYNTHETIC_SCAN_TOOL" in _diff(
        "MCP tools", _mcp_tool_items(text), contract.mcp_tools
    )


def test_mutation_an_extra_computed_site_is_missing(modules: dict[str, str], contract: ContractFacts) -> None:
    text = (
        "def gather_rows(rows):\n"
        "    return [Finding(source=Source.WRITER_LOCK, check=row['kind'], status=None) for row in rows]\n\n"
        "ROWS = [{'kind': 'synthetic-kind'}]\n"
    )
    facts = _code_facts(_with_synthetic(modules, text))
    assert f"missing from contract.md § Computed check sites: {_SYNTHETIC} | gather_rows | row['kind']" in _diff(
        "Computed check sites", facts.computed_check_sites, contract.computed_check_sites
    )
    assert f"missing from contract.md § Check codes: {_SYNTHETIC} | synthetic-kind" in _diff(
        "Check codes", facts.check_codes, contract.check_codes
    )


_KIND_GATHER = (
    "def gather_rows(rows):\n"
    "    return [Finding(source=Source.WRITER_LOCK, check=row['kind'], status=None) for row in rows]\n\n"
)
# In a module whose check= reads <row>['kind'], each form an item row's "kind" takes: a code it names, or a
# computed site (module, function, value) when no reading resolves the value.
_KIND_FORMS = {
    "dict-computed": ("def build(prefix):\n    return [{'kind': prefix + '-x'}]\n", "site", "build | prefix + '-x'"),
    "dict-call": ("def build():\n    return [dict(kind='silent-kind-dict')]\n", "code", "silent-kind-dict"),
    "dict-call-computed": ("def build(prefix):\n    return [dict(kind=prefix)]\n", "site", "build | prefix"),
    "assigned": (
        "def build():\n    row = {}\n    row['kind'] = 'silent-kind-assigned'\n    return [row]\n",
        "code",
        "silent-kind-assigned",
    ),
    "assigned-computed": (
        "def build(prefix):\n    row = {}\n    row['kind'] = prefix.upper()\n    return [row]\n",
        "site",
        "build | prefix.upper()",
    ),
    "updated": (
        "def build():\n    row = {}\n    row.update(kind='silent-kind-updated')\n    return [row]\n",
        "code",
        "silent-kind-updated",
    ),
    "updated-computed": (
        "def build(prefix):\n    row = {}\n    row.update(kind=prefix.lower())\n    return [row]\n",
        "site",
        "build | prefix.lower()",
    ),
    "setdefault": (
        "def build():\n    row = {}\n    row.setdefault('kind', 'silent-kind-default')\n    return [row]\n",
        "code",
        "silent-kind-default",
    ),
    "setdefault-computed": (
        "def build(prefix):\n    row = {}\n    row.setdefault('kind', prefix * 2)\n    return [row]\n",
        "site",
        "build | prefix * 2",
    ),
}


@pytest.mark.parametrize("case", sorted(_KIND_FORMS))
def test_mutation_an_item_row_kind_in_another_form_is_read(
    case: str, modules: dict[str, str], contract: ContractFacts
) -> None:
    body, family, item = _KIND_FORMS[case]
    facts = _code_facts(_with_synthetic(modules, _KIND_GATHER + body))
    if family == "site":
        assert f"missing from contract.md § Computed check sites: {_SYNTHETIC} | {item}" in _diff(
            "Computed check sites", facts.computed_check_sites, contract.computed_check_sites
        )
    else:
        assert f"missing from contract.md § Check codes: {_SYNTHETIC} | {item}" in _diff(
            "Check codes", facts.check_codes, contract.check_codes
        )


def test_mutation_an_extra_computed_environment_read_is_missing(
    modules: dict[str, str], contract: ContractFacts
) -> None:
    text = "import os\n\ndef token():\n    for key in ('SYNTHETIC_A', 'SYNTHETIC_B'):\n        os.getenv(key)\n"
    facts = _code_facts(_with_synthetic(modules, text))
    assert (
        f"missing from contract.md § Computed check sites: {_SYNTHETIC} | token | key | SYNTHETIC_A, SYNTHETIC_B"
        in _diff("Computed check sites", facts.computed_environment_reads, contract.computed_environment_reads)
    )


_STALE_CASES = {
    "cli-option": ("CLI", "| Verb | Option | Kind |\n|---|---|---|\n| `doctor check` | `--ghost-flag` | flag |"),
    "check-code": (
        "Check codes",
        "| Source | Module | Codes |\n|---|---|---|\n| `writer-lock` | `sources/writer_lock.py` | `ghost-code` |",
    ),
    "environment": (
        "Environment variables",
        "| Variable read | Module | Function |\n|---|---|---|\n| `GHOST_TOKEN` | `cli_bridge.py` | `run_git` |",
    ),
    "mcp-tool": (
        "MCP tools",
        "| Tool | Constant | Role |\n|---|---|---|\n| `ghost_scan` | `GHOST_SCAN_TOOL` | start |",
    ),
    "flag-key": (
        "Feature-flag keys",
        "| Key | Module | Reader |\n|---|---|---|\n| `pyforge.ghost` | `sources/writer_lock.py` | `read_boolean` |",
    ),
    "source": (
        "Sources",
        "| Source | Scope | Subject | Dispatcher | Governing capability | Modules |\n|---|---|---|---|---|---|\n"
        "| `ghost-source` | repo | fleet | no | CAP-1 | `sources/ghost.py` |",
    ),
    "computed-site": (
        "Computed check sites",
        "| Module | Function | Expression | Codes come from |\n|---|---|---|---|\n"
        "| `sources/board.py` | `_ghost_gather` | `item['kind']` | nothing |",
    ),
}


@pytest.mark.parametrize("case", sorted(_STALE_CASES))
def test_mutation_a_contract_line_with_no_code_is_stale(case: str, root: Path, code: CodeFacts) -> None:
    section, table = _STALE_CASES[case]
    synthetic = _contract_facts(f"## {section}\n\n{table}\n")
    _verbs, options = _cli_items(_parsers())
    pairs = {
        "cli-option": ("CLI (options)", options, synthetic.options, "doctor check | --ghost-flag"),
        "check-code": ("Check codes", code.check_codes, synthetic.check_codes, "sources/writer_lock.py | ghost-code"),
        "environment": (
            "Environment variables",
            code.environment_read,
            synthetic.environment_read,
            "GHOST_TOKEN | cli_bridge.py",
        ),
        "mcp-tool": (
            "MCP tools",
            _mcp_tool_items((root / _MCP_ASGI).read_text(encoding="utf-8")),
            synthetic.mcp_tools,
            "ghost_scan | GHOST_SCAN_TOOL",
        ),
        "flag-key": (
            "Feature-flag keys",
            code.flag_keys,
            synthetic.flag_keys,
            "pyforge.ghost | sources/writer_lock.py | read_boolean",
        ),
        "source": ("Sources", _real_sources(), synthetic.sources, "ghost-source | repo | fleet | no"),
        "computed-site": (
            "Computed check sites",
            code.computed_check_sites,
            synthetic.computed_check_sites,
            "sources/board.py | _ghost_gather | item['kind']",
        ),
    }
    label, code_items, contract_items, line = pairs[case]
    assert f"stale in contract.md § {label} (no code backs it): {line}" in _diff(label, code_items, contract_items)
