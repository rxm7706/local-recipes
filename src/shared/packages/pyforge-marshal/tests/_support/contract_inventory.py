"""Marshal's public surface, derived from the code (Story 114.3, spec-pyforge-marshal:CAP-304).

``tests/meta/test_public_contract.py`` compares what this module derives with the tables of ``contract.md`` beside
``spec-pyforge-marshal``'s ``SPEC.md``, both ways. Nothing here is typed twice: every family is read from the code
that defines it, so a verb, a flag, a tool, a key, a variable, a code or an exit code the code gains is an item the
contract lacks until it says so.

The families, and where each is read:

* **verb paths and flags** -- ``cli.main._build_parser()``: every sub-parser choice, nested, gives a verb path (the
  bare ``marshal`` is the path ``""``); every option string of an action the path's parser owns gives a flag, except
  argparse's own ``-h``/``--help`` and an action whose help is ``argparse.SUPPRESS`` (not help-visible). Positional
  arguments are not flags.
* **MCP tools** -- the ``marshal-mcp`` stdio server: the keys of ``mcp.tools.TOOL_SPECS`` and the names
  ``mcp.server.build_server()`` registers (the union, so a registration with no spec is listed too), each with the
  CLI argv its spec runs. The station face (``POST /stations/marshal/mcp``): the tool names
  ``django_marshal_portal/mcp_asgi.py`` registers, read by AST, never imported -- each ``@<server>.tool(name=...)``
  decorator and each ``*_tool=`` keyword of the ``attach_supervised_start_get`` call, a name resolved through that
  module's constants or, for a name it imports from ``django_pyforge.supervisor``, through that module's AST.
* **feature-flag keys** -- every string constant in a marshal module shaped ``pyforge.<station>.<key>`` that is not
  a module path (it names no ``<key>.py`` file and no ``<key>/`` directory under the station's package), plus the
  seam: a module that imports ``root_of_record`` from ``pyforge.core.cutover_root`` contributes
  ``pyforge.core.cutover_root.CUTOVER_FLAG`` (``pyforge.cutover_root``), since no marshal module holds that string.
* **environment variables** -- the value of every module-level ``ENV_*`` or ``*_ENV`` string constant (a leading
  underscore allowed), and the key of every ``os.environ`` / ``os.getenv`` access: ``os.environ[K]``,
  ``os.environ.get/pop/setdefault(K)``, ``os.getenv(K)``, ``K in os.environ``, ``.get(K)`` on an expression holding
  ``os.environ``, a key of a dict literal that spreads ``**os.environ``, and a subscript or ``.get/.pop/.setdefault``
  key on a name the same function binds to an expression holding ``os.environ`` (a child environment) or takes as a
  parameter named ``environ``. ``K`` is a string literal or a name resolving to a module-level string constant (the
  module's own, or the marshal module it is imported from); a key computed at run time is not an item.
* **diagnostic codes** -- ``core.findings.REGISTERED_CODES``, each with its ``core.verdict.classify`` verdict, and
  the seed ``FindingType`` enum's wire values, each with its member name.
* **exit codes** -- ``core.verdict.GUARDED_EXIT_CODES``, each with the verdicts ``core.verdict.exit_code_for`` maps
  to it and the ``EXIT_*`` constants of ``core.verdict`` that equal it; and the seed group's taxonomy, the codes of
  ``seed.errors.SeedError``'s own leaves (``SEED_EXIT_CODES``), each with its leaf class.

Every derivation takes its input as an argument (the parser, the tool specs, the module sources, the codes), so the
meta-test can hand it a mutated input and prove the comparison fires. Paths outside the package are computed when a
function runs, never at import.
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import re
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

# Story 116.2 (spec-pyforge-marshal:CAP-305): only the live-tree tests/meta/test_public_contract.py uses this
# helper, and it reads sibling packages' sources, so it carries the live_tree mark for steward's trigger-map
# derivation, which routes a marked module's reads to the live half (pytest ignores the mark outside a test
# module, as in pyforge-steward's tests/integration/nkp_probes.py).
pytestmark = pytest.mark.live_tree

# Families, as the meta-test names them in its findings.
VERB_PATH = "verb path"
FLAG = "flag"
TOOL = "tool"
FLAG_KEY = "flag key"
ENV_VAR = "environment variable"
DIAGNOSTIC_CODE = "diagnostic code"
SEED_FINDING_TYPE = "seed finding type"
EXIT_CODE = "exit code"

FAMILIES: tuple[str, ...] = (VERB_PATH, FLAG, TOOL, FLAG_KEY, ENV_VAR, DIAGNOSTIC_CODE, SEED_FINDING_TYPE, EXIT_CODE)

# The two MCP surfaces and the two exit domains, as item prefixes.
MARSHAL_MCP = "marshal-mcp"
STATION_FACE = "station-face"
EVERY_VERB = "every-verb"
SEED_GROUP = "seed"

FLAG_KEY_SHAPE = re.compile(r"pyforge\.([a-z0-9_]+)\.([a-z0-9_]+)")
ENV_NAME_SHAPE = re.compile(r"[A-Z_][A-Z0-9_]*")
ENV_CONSTANT_NAME = re.compile(r"_?(?:ENV_[A-Z0-9_]+|[A-Z0-9_]+_ENV)")
_ENVIRON_KEY_METHODS = frozenset({"get", "pop", "setdefault"})
_ENVIRON_PARAMETER = "environ"
_CUTOVER_MODULE = "pyforge.core.cutover_root"
_CUTOVER_READER = "root_of_record"
_FACE_RELATIVE = Path("django-marshal/src/django_marshal_portal/mcp_asgi.py")
_FACE_SUPERVISOR_MODULE = "django_pyforge.supervisor"
_FACE_SUPERVISOR_RELATIVE = Path("django-pyforge/src/django_pyforge/supervisor.py")
_FACE_START_GET = "attach_supervised_start_get"

Item = tuple[str, str]
"""``(family, item)``: the item is the family's own key -- ``"factory dispatch"``, ``"factory dispatch --stories"``,
``"marshal-mcp marshal_status"``, ``"pyforge.marshal.watch"``, ``"BMAD_ACTIVE_PROJECT"``, ``"MRS-GATE-001"``,
``"artifact-missing"``, ``"every-verb 2"``."""


@dataclass(frozen=True)
class Inventory:
    """What the code has: each item mapped to its detail (``None`` when the family carries none)."""

    items: Mapping[Item, str | None]

    def family(self, family: str) -> dict[str, str | None]:
        return {item: detail for (kind, item), detail in self.items.items() if kind == family}


# -- where the code is ---------------------------------------------------------------------------------------------


def marshal_source_dir() -> Path:
    """The ``pyforge.marshal`` package directory the interpreter imports (the code the parser walk runs)."""
    import pyforge.marshal

    module_file = pyforge.marshal.__file__
    if module_file is None:
        raise RuntimeError("pyforge.marshal has no __file__")
    return Path(module_file).resolve().parent


def marshal_sources(source_dir: Path | None = None) -> dict[str, str]:
    """Every ``*.py`` under the marshal package, keyed by its path relative to the package (``cli/main.py``)."""
    root = source_dir if source_dir is not None else marshal_source_dir()
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*.py"))
        if "__pycache__" not in path.parts
    }


def packages_dir() -> Path:
    """``src/shared/packages``: the directory holding marshal's package and its siblings, found when called."""
    return marshal_source_dir().parents[3]


def station_package_dir(station: str) -> Path:
    """The ``pyforge/<station>`` directory of a sibling package (``pyforge-<station>/src/pyforge/<station>``)."""
    if station == "marshal":
        return marshal_source_dir()
    if station == "core":
        import pyforge.core

        core_file = pyforge.core.__file__
        if core_file is None:
            raise RuntimeError("pyforge.core has no __file__")
        return Path(core_file).resolve().parent
    return packages_dir() / f"pyforge-{station}" / "src" / "pyforge" / station


# -- verb paths and flags ------------------------------------------------------------------------------------------


def _subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction | None:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    return None


def _walk_parser(parser: argparse.ArgumentParser, path: str) -> Iterator[tuple[str, argparse.ArgumentParser]]:
    yield path, parser
    sub = _subparsers(parser)
    if sub is None:
        return
    for name, child in sub.choices.items():
        yield from _walk_parser(child, f"{path} {name}".strip())


def _help_visible_flags(parser: argparse.ArgumentParser) -> Iterator[str]:
    for action in parser._actions:
        if isinstance(action, (argparse._HelpAction, argparse._SubParsersAction)):
            continue
        if action.help == argparse.SUPPRESS:
            continue
        yield from action.option_strings


def cli_items(parser: argparse.ArgumentParser | None = None) -> dict[Item, str | None]:
    """Verb paths and ``(path, flag)`` pairs from the parser ``marshal`` runs (``cli.main._build_parser()``)."""
    if parser is None:
        from pyforge.marshal.cli.main import _build_parser

        parser = _build_parser()
    items: dict[Item, str | None] = {}
    for path, sub in _walk_parser(parser, ""):
        items[(VERB_PATH, path)] = None
        for flag in _help_visible_flags(sub):
            items[(FLAG, f"{path} {flag}".strip())] = None
    return items


# -- MCP tools -----------------------------------------------------------------------------------------------------


def registered_tool_names(server: Any = None) -> frozenset[str]:
    """The names ``mcp.server.build_server()`` registers (the server ``marshal-mcp`` serves)."""
    if server is None:
        from pyforge.marshal.mcp.server import build_server

        server = build_server()
    tools = asyncio.run(server.list_tools())
    return frozenset(tool.name for tool in tools)


def _runs(spec: Mapping[str, Any] | None) -> str | None:
    cli = None if spec is None else spec.get("cli")
    if not cli:
        return None
    return "marshal " + " ".join(str(token) for token in cli)


def marshal_mcp_items(
    tool_specs: Mapping[str, Mapping[str, object]] | None = None,
    registered: Iterable[str] | None = None,
) -> dict[Item, str | None]:
    """``marshal-mcp``'s tools: ``TOOL_SPECS`` and the registered names, each with the CLI argv it runs."""
    if tool_specs is None:
        from pyforge.marshal.mcp.tools import TOOL_SPECS

        tool_specs = TOOL_SPECS
    names = set(tool_specs) | set(registered_tool_names() if registered is None else registered)
    return {(TOOL, f"{MARSHAL_MCP} {name}"): _runs(tool_specs.get(name)) for name in names}


def _string_constants(tree: ast.Module) -> dict[str, str]:
    """Module-level ``NAME = "<str>"`` (or annotated) bindings."""
    found: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            for target in targets:
                if isinstance(target, ast.Name):
                    found[target.id] = value.value
    return found


def _face_name(node: ast.expr, local: Mapping[str, str], imported: Mapping[str, str]) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and node.id in local:
        return local[node.id]
    if isinstance(node, ast.Name) and node.id in imported:
        return imported[node.id]
    raise ValueError(f"the station face names a tool through {ast.unparse(node)!r}, which no constant resolves")


def station_face_items(face_source: str | None = None, supervisor_source: str | None = None) -> dict[Item, str | None]:
    """The tool names the station face registers, read by AST from ``mcp_asgi.py`` (never imported)."""
    if face_source is None:
        face_source = (packages_dir() / _FACE_RELATIVE).read_text(encoding="utf-8")
    if supervisor_source is None:
        supervisor_source = (packages_dir() / _FACE_SUPERVISOR_RELATIVE).read_text(encoding="utf-8")
    face = ast.parse(face_source)
    local = _string_constants(face)
    supervisor_constants = _string_constants(ast.parse(supervisor_source))
    imported = {
        alias.asname or alias.name: supervisor_constants[alias.name]
        for node in ast.walk(face)
        if isinstance(node, ast.ImportFrom) and node.module == _FACE_SUPERVISOR_MODULE
        for alias in node.names
        if alias.name in supervisor_constants
    }
    names: set[str] = set()
    for node in ast.walk(face):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "tool":
            names.update(_face_name(kw.value, local, imported) for kw in node.keywords if kw.arg == "name")
        elif isinstance(func, ast.Name) and func.id == _FACE_START_GET:
            names.update(
                _face_name(kw.value, local, imported)
                for kw in node.keywords
                if kw.arg is not None and kw.arg.endswith("_tool")
            )
    return {(TOOL, f"{STATION_FACE} {name}"): None for name in names}


# -- module sources: flag keys and environment variables -----------------------------------------------------------


@dataclass(frozen=True)
class _Module:
    relpath: str
    dotted: str
    tree: ast.Module
    constants: Mapping[str, str]


def _parse(sources: Mapping[str, str]) -> dict[str, _Module]:
    modules: dict[str, _Module] = {}
    for relpath, text in sources.items():
        parts = relpath.removesuffix(".py").split("/")
        if parts[-1] == "__init__":
            parts = parts[:-1]
        dotted = ".".join(["pyforge", "marshal", *parts])
        tree = ast.parse(text, filename=relpath)
        modules[dotted] = _Module(relpath, dotted, tree, _string_constants(tree))
    return modules


def _is_package(module: _Module) -> bool:
    return module.relpath.endswith("__init__.py")


def _import_target(module: _Module, node: ast.ImportFrom) -> str:
    if not node.level:
        return node.module or ""
    package = module.dotted if _is_package(module) else module.dotted.rpartition(".")[0]
    for _ in range(node.level - 1):
        package = package.rpartition(".")[0]
    return f"{package}.{node.module}" if node.module else package


def _module_aliases(module: _Module) -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
    """``(alias -> module dotted path, name -> (module dotted path, imported name))`` for one module."""
    module_alias: dict[str, str] = {}
    name_alias: dict[str, tuple[str, str]] = {}
    for node in ast.walk(module.tree):
        if isinstance(node, ast.ImportFrom):
            target = _import_target(module, node)
            for alias in node.names:
                bound = alias.asname or alias.name
                module_alias[bound] = f"{target}.{alias.name}"
                name_alias[bound] = (target, alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    module_alias[alias.asname] = alias.name
    return module_alias, name_alias


class _Resolver:
    """Resolves a key expression to a string: a literal, or a module-level constant of a marshal module."""

    def __init__(self, module: _Module, modules: Mapping[str, _Module]) -> None:
        self._module = module
        self._modules = modules
        self._module_alias, self._name_alias = _module_aliases(module)

    def __call__(self, node: ast.expr) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in self._module.constants:
                return self._module.constants[node.id]
            if node.id in self._name_alias:
                target, name = self._name_alias[node.id]
                source = self._modules.get(target)
                return None if source is None else source.constants.get(name)
            return None
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            source = self._modules.get(self._module_alias.get(node.value.id, ""))
            return None if source is None else source.constants.get(node.attr)
        return None


def _is_module_path(key: str) -> bool:
    match = FLAG_KEY_SHAPE.fullmatch(key)
    if match is None:
        return False
    station, name = match.groups()
    base = station_package_dir(station)
    return (base / f"{name}.py").is_file() or (base / name).is_dir()


def flag_key_items(sources: Mapping[str, str] | None = None) -> dict[Item, str | None]:
    """Every ``pyforge.<station>.<key>`` string constant that is not a module path, plus the root-of-record seam."""
    from pyforge.core.cutover_root import CUTOVER_FLAG

    modules = _parse(marshal_sources() if sources is None else sources)
    keys: set[str] = set()
    for module in modules.values():
        for node in ast.walk(module.tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and FLAG_KEY_SHAPE.fullmatch(node.value):
                keys.add(node.value)
            elif (
                isinstance(node, ast.ImportFrom)
                and _import_target(module, node) == _CUTOVER_MODULE
                and any(alias.name == _CUTOVER_READER for alias in node.names)
            ):
                keys.add(CUTOVER_FLAG)
    return {(FLAG_KEY, key): None for key in keys if not _is_module_path(key)}


def _is_os_environ(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "environ"
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
    )


def _holds_environ(node: ast.AST) -> bool:
    return any(_is_os_environ(inner) for inner in ast.walk(node))


def _scope_nodes(body: Iterable[ast.AST]) -> Iterator[ast.AST]:
    """Every node of a scope's body, not descending into a nested function or class (each is its own scope)."""
    stack = list(body)
    while stack:
        node = stack.pop()
        yield node
        for child in ast.iter_child_nodes(node):
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                stack.append(child)


def _scopes(tree: ast.Module) -> Iterator[tuple[list[ast.AST], set[str]]]:
    """Each scope's body nodes with the names its parameters bind to an environment (``environ``)."""
    yield list(tree.body), set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            arguments = node.args
            parameters = [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]
            yield list(node.body), {arg.arg for arg in parameters if arg.arg == _ENVIRON_PARAMETER}


def _environment_keys(module: _Module) -> Iterator[ast.expr]:
    """Each key expression a module reads from or sets in an environment (see the module docstring)."""
    for body, environ_names in _scopes(module.tree):
        nodes = list(_scope_nodes(body))
        names = set(environ_names)
        for node in nodes:
            if isinstance(node, ast.Assign) and _holds_environ(node.value):
                names.update(target.id for target in node.targets if isinstance(target, ast.Name))

        def is_environment(expr: ast.AST, names: set[str] = names) -> bool:
            return _is_os_environ(expr) or (isinstance(expr, ast.Name) and expr.id in names)

        for node in nodes:
            if isinstance(node, ast.Subscript) and is_environment(node.value):
                yield node.slice
            elif isinstance(node, ast.Call) and node.args:
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "getenv" and isinstance(func.value, ast.Name):
                    if func.value.id == "os":
                        yield node.args[0]
                elif isinstance(func, ast.Attribute) and func.attr in _ENVIRON_KEY_METHODS:
                    if is_environment(func.value) or (func.attr == "get" and _holds_environ(func.value)):
                        yield node.args[0]
            elif isinstance(node, ast.Compare) and any(_is_os_environ(c) for c in node.comparators):
                if any(isinstance(op, (ast.In, ast.NotIn)) for op in node.ops):
                    yield node.left
            elif isinstance(node, ast.Dict) and any(
                key is None and _is_os_environ(value) for key, value in zip(node.keys, node.values, strict=True)
            ):
                yield from (key for key in node.keys if key is not None)


def env_items(sources: Mapping[str, str] | None = None) -> dict[Item, str | None]:
    """Every ``ENV_*`` / ``*_ENV`` constant's value and every resolvable ``os.environ`` / ``os.getenv`` key."""
    modules = _parse(marshal_sources() if sources is None else sources)
    names: set[str] = set()
    for module in modules.values():
        for constant, value in module.constants.items():
            if ENV_CONSTANT_NAME.fullmatch(constant) and ENV_NAME_SHAPE.fullmatch(value):
                names.add(value)
        resolve = _Resolver(module, modules)
        for key in _environment_keys(module):
            value = resolve(key)
            if value is not None and ENV_NAME_SHAPE.fullmatch(value):
                names.add(value)
    return {(ENV_VAR, name): None for name in names}


# -- diagnostic codes and exit codes -------------------------------------------------------------------------------


def _verdict(classify: Callable[[str], object], code: str) -> str:
    try:
        verdict = classify(code)
    except Exception:  # noqa: BLE001 -- a code with no classification is reported, never raised
        return "unclassified"
    return str(getattr(verdict, "value", verdict))


def diagnostic_items(
    codes: Iterable[str] | None = None,
    classify: Callable[[str], object] | None = None,
) -> dict[Item, str | None]:
    """``REGISTERED_CODES``, each with the verdict ``core.verdict.classify`` gives it."""
    if codes is None:
        from pyforge.marshal.core.findings import REGISTERED_CODES

        codes = REGISTERED_CODES
    if classify is None:
        from pyforge.marshal.core.verdict import classify as classify_code

        classify = classify_code
    return {(DIAGNOSTIC_CODE, code): _verdict(classify, code) for code in codes}


def seed_finding_type_items(finding_types: Mapping[str, str] | None = None) -> dict[Item, str | None]:
    """The seed ``FindingType`` wire values, each with its member name (``{value: member}`` when given)."""
    if finding_types is None:
        from pyforge.marshal.seed.detect.findings import FindingType

        finding_types = {member.value: member.name for member in FindingType}
    return {(SEED_FINDING_TYPE, value): name for value, name in finding_types.items()}


def _every_verb_meanings() -> dict[int, list[str]]:
    from pyforge.marshal.core import verdict as verdict_module

    meanings: dict[int, list[str]] = {}
    for member in verdict_module.LATTICE_ORDER:
        meanings.setdefault(verdict_module.exit_code_for(member), []).append(member.value)
    for name, value in vars(verdict_module).items():
        if name.startswith("EXIT_") and isinstance(value, int) and not isinstance(value, bool):
            meanings.setdefault(value, []).append(name)
    return meanings


def _seed_leaves() -> dict[int, str]:
    from pyforge.marshal.seed import errors

    return {
        leaf.exit_code: leaf.__name__
        for leaf in errors.SeedError.__subclasses__()
        if leaf.__module__ == errors.__name__ and leaf.exit_code in errors.SEED_EXIT_CODES
    }


def exit_code_items(
    guarded: Mapping[int, Iterable[str]] | None = None,
    seed: Mapping[int, str] | None = None,
) -> dict[Item, str | None]:
    """Both exit domains: ``GUARDED_EXIT_CODES`` with each code's meanings, and the seed leaves' codes."""
    if guarded is None:
        from pyforge.marshal.core.verdict import GUARDED_EXIT_CODES

        meanings = _every_verb_meanings()
        guarded = {code: meanings.get(code, []) for code in GUARDED_EXIT_CODES}
    if seed is None:
        seed = _seed_leaves()
    items: dict[Item, str | None] = {
        (EXIT_CODE, f"{EVERY_VERB} {code}"): ", ".join(sorted(names)) for code, names in guarded.items()
    }
    items.update({(EXIT_CODE, f"{SEED_GROUP} {code}"): leaf for code, leaf in seed.items()})
    return items


# -- everything ----------------------------------------------------------------------------------------------------


def inventory(
    *,
    parser: argparse.ArgumentParser | None = None,
    tool_specs: Mapping[str, Mapping[str, object]] | None = None,
    registered: Iterable[str] | None = None,
    face_source: str | None = None,
    sources: Mapping[str, str] | None = None,
    codes: Iterable[str] | None = None,
    classify: Callable[[str], object] | None = None,
    finding_types: Mapping[str, str] | None = None,
    guarded: Mapping[int, Iterable[str]] | None = None,
    seed: Mapping[int, str] | None = None,
) -> Inventory:
    """Every family, each from its own source; an argument replaces that source (the meta-test's mutations)."""
    module_sources = marshal_sources() if sources is None else sources
    items: dict[Item, str | None] = {}
    items.update(cli_items(parser))
    items.update(marshal_mcp_items(tool_specs, registered))
    items.update(station_face_items(face_source))
    items.update(flag_key_items(module_sources))
    items.update(env_items(module_sources))
    items.update(diagnostic_items(codes, classify))
    items.update(seed_finding_type_items(finding_types))
    items.update(exit_code_items(guarded, seed))
    return Inventory(items)
