"""Story 50.3 (spec-pyforge-herald CAP-62, FR-14.1): herald's public contract is one companion, and this test holds
the code to it.

``contract.md`` beside the Spec is written by hand from the code. This module derives each surface from the code and
compares it with that file in both directions: a surface the code has and the contract does not list fails, and so
does a contract row the code no longer has. The surfaces:

* the CLI verbs and their arguments, walked from ``pyforge.herald.cli._build_parser()``;
* the MCP tools of ``POST /stations/herald/mcp``, read from ``django_herald_portal/mcp_asgi.py`` by regex (no Django
  import);
* the feature-flag keys: herald's ``*_FLAG`` constants and the key that opens the doc comment of each flag reader
  ``docs-site/src/lib/flags.ts`` exports (``envFlagOn``, the generic reader, is exempt by name);
* the repository keys: ``roots.this`` once a herald module imports ``pyforge.core.cutover_root``;
* the environment variables the package and the docs-site build read, in every read form the tree uses;
* the ``HeraldError`` classes of ``pyforge.herald.errors`` with their exit codes, and the closed exit-code set.

``cli_cites`` holds ``cli.py``'s capability citations to the verb table: the ``CAP-n`` tokens in a verb's help, its
handler's docstring and its handler's body name only capabilities that verb's row names, and every token in the module
is named by some row. The ``planted`` cases run each comparison over in-memory fixtures and check that a difference is
named in the failure text.
"""

from __future__ import annotations

import argparse
import ast
import inspect
import re
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import pytest

from pyforge.herald import cli, errors

# Story 52.1 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package (the Spec folder,
# docs-site and django-herald), so it runs in the station's live-tree half and fires on what it reads.
pytestmark = pytest.mark.live_tree

# Every outside path is anchored on this file, so steward's trigger-map meta-test derives each read.
# tests/meta -> tests -> pyforge-herald -> packages -> shared -> src -> repo root
REPO_ROOT = Path(__file__).resolve().parents[6]
HERALD_SRC = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "herald"
CONTRACT = REPO_ROOT / "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/contract.md"
MCP_ASGI = REPO_ROOT / "src/shared/packages/django-herald/src/django_herald_portal/mcp_asgi.py"
FLAGS_TS = REPO_ROOT / "docs-site/src/lib/flags.ts"
SITE_DIRS = (REPO_ROOT / "docs-site/src", REPO_ROOT / "docs-site/scripts")
SITE_FILES = (REPO_ROOT / "docs-site/astro.config.mjs",)
SITE_SUFFIXES = frozenset({".ts", ".mts", ".cts", ".tsx", ".js", ".mjs", ".cjs", ".jsx", ".astro"})

TABLES = (
    "CLI verbs",
    "MCP tools",
    "Feature-flag keys",
    "Repository keys",
    "Environment variables",
    "Error classes",
    "Exit codes",
)

FLAG_HELPERS = frozenset({"envFlagOn"})
"""Exported ``flags.ts`` functions that read a flag by a name they are given, so they document no key."""

CUTOVER_MODULE = "pyforge.core.cutover_root"
CUTOVER_ROSTER_KEY = "roots.this"


# --- the contract file ------------------------------------------------------------------------------------------


def parse_contract(text: str) -> dict[str, list[list[str]]]:
    """Each ``## <table>`` section's table body rows (header and separator dropped), as lists of stripped cells."""
    tables: dict[str, list[list[str]]] = {}
    section: str | None = None
    for line in text.splitlines():
        heading = re.match(r"^## (.+?)\s*$", line)
        if heading:
            section = heading.group(1)
            tables[section] = []
            continue
        if section is None or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        tables[section].append(cells)
    return {name: rows[1:] for name, rows in tables.items()}


def ticked(cell: str) -> list[str]:
    return re.findall(r"`([^`]+)`", cell)


def row_key(row: list[str]) -> str:
    names = ticked(row[0])
    if not names:
        raise AssertionError(f"contract.md row has no backticked item in its first column: {row!r}")
    return names[0]


_CAP_RE = re.compile(r"(?:((?i:spec)-[a-z0-9-]+)[: ])?CAP-(\d+)(?:\.\.(?:CAP-)?(\d+))?")


def cap_tokens(text: str) -> set[str]:
    """Capability ids in ``text``: bare ``CAP-n`` is herald's, a ``spec-x:CAP-n`` keeps its Spec, ranges expand."""
    found: set[str] = set()
    for spec, first, last in _CAP_RE.findall(text):
        low = int(first)
        high = int(last) if last else low
        prefix = f"{spec.lower()}:" if spec and spec.lower() != "spec-pyforge-herald" else ""
        found.update(f"{prefix}CAP-{n}" for n in range(low, high + 1))
    return found


def set_problems(kind: str, code: Mapping[str, str], listed: Iterable[str]) -> list[str]:
    """Both directions for one kind: ``code`` maps each item to where the code has it."""
    listed_set = set(listed)
    problems = [
        f"{kind} `{item}` ({code[item]}) is missing from contract.md" for item in sorted(code.keys() - listed_set)
    ]
    problems += [
        f"contract.md lists {kind} `{item}`, which the code lacks" for item in sorted(listed_set - code.keys())
    ]
    return problems


# --- CLI verbs --------------------------------------------------------------------------------------------------


def _subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction | None:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    return None


def _arg_token(action: argparse.Action) -> str:
    if action.option_strings:
        return "/".join(action.option_strings)
    name = action.metavar if isinstance(action.metavar, str) else action.dest
    if action.nargs == "?":
        return f"[{name}]"
    if action.nargs == "+":
        return f"<{name}>..."
    if action.nargs == "*":
        return f"[{name}]..."
    return f"<{name}>"


def walk_parser(parser: argparse.ArgumentParser) -> Iterator[tuple[str, argparse.ArgumentParser, str | None]]:
    """Every verb path with its parser and the help its parent lists it under, root first."""

    def walk(
        node: argparse.ArgumentParser, path: str, listed_help: str | None
    ) -> Iterator[tuple[str, argparse.ArgumentParser, str | None]]:
        yield path, node, listed_help
        subs = _subparsers(node)
        if subs is None:
            return
        helps = {choice.dest: choice.help for choice in subs._choices_actions}
        for name, child in subs.choices.items():
            yield from walk(child, f"{path} {name}", helps.get(name))

    yield from walk(parser, parser.prog, None)


def cli_verbs(parser: argparse.ArgumentParser) -> dict[str, frozenset[str]]:
    """Each verb path's own arguments (``-h/--help`` and the verb choice itself left out)."""
    return {
        path: frozenset(
            _arg_token(action)
            for action in node._actions
            if not isinstance(action, (argparse._HelpAction, argparse._SubParsersAction))
        )
        for path, node, _ in walk_parser(parser)
    }


def contract_verbs(rows: list[list[str]]) -> tuple[dict[str, frozenset[str]], dict[str, frozenset[str]]]:
    """The verb table: each path's listed arguments, and each path's capabilities."""
    arguments: dict[str, frozenset[str]] = {}
    capabilities: dict[str, frozenset[str]] = {}
    for row in rows:
        path = row_key(row)
        arguments[path] = frozenset(ticked(row[1]))
        capabilities[path] = frozenset(cap_tokens(row[2]))
    return arguments, capabilities


def verb_problems(code: Mapping[str, frozenset[str]], listed: Mapping[str, frozenset[str]]) -> list[str]:
    problems = set_problems("verb", {path: "the parser" for path in code}, listed)
    for path in sorted(code.keys() & listed.keys()):
        for token in sorted(code[path] - listed[path]):
            problems.append(f"`{path}` takes `{token}`, which contract.md does not list")
        for token in sorted(listed[path] - code[path]):
            problems.append(f"contract.md lists `{token}` on `{path}`, which the parser lacks")
    return problems


# --- cli_cites --------------------------------------------------------------------------------------------------


def verb_help_texts(parser: argparse.ArgumentParser) -> dict[str, str]:
    """Each verb path's help as the parent lists it, its description and epilog, and its own arguments' help."""
    texts: dict[str, str] = {}
    for path, node, listed_help in walk_parser(parser):
        parts = [listed_help or "", node.description or "", node.epilog or ""]
        parts += [action.help or "" for action in node._actions if not isinstance(action, argparse._SubParsersAction)]
        texts[path] = "\n".join(parts)
    return texts


def _filled(action: argparse.Action) -> list[str]:
    if action.choices:
        value = str(next(iter(action.choices)))
    elif action.type in (int, float):
        value = "1"
    else:
        value = "x"
    if isinstance(action.nargs, int):
        values = [value] * action.nargs
    elif action.nargs in (None, "+"):
        values = [value]
    else:
        values = []
    return [action.option_strings[0], *values] if action.option_strings else values


def _required(action: argparse.Action) -> bool:
    if isinstance(action, (argparse._HelpAction, argparse._SubParsersAction)):
        return False
    if action.option_strings:
        return bool(action.required)
    return action.nargs not in ("?", "*")


def verb_argvs(parser: argparse.ArgumentParser) -> dict[str, list[str]]:
    """The smallest argv that reaches each verb path: its words plus a value for each required argument."""
    argvs: dict[str, list[str]] = {}

    def walk(node: argparse.ArgumentParser, path: str, argv: list[str]) -> None:
        here = [*argv]
        for action in node._actions:
            if _required(action):
                here += _filled(action)
        argvs[path] = here
        subs = _subparsers(node)
        if subs is not None:
            for name, child in subs.choices.items():
                walk(child, f"{path} {name}", [*here, name])

    walk(parser, parser.prog, [])
    return argvs


def route_handlers(monkeypatch: pytest.MonkeyPatch) -> tuple[dict[str, Callable[..., object]], dict[str, str]]:
    """Which ``_run_*`` handler ``cli._route`` reaches for each verb path, found by routing a parsed argv with every
    handler swapped for a recorder. Returns the original handlers by name, and each reachable path's handler name."""
    originals = {
        name: value for name, value in vars(cli).items() if name.startswith("_run_") and inspect.isfunction(value)
    }
    called: list[str] = []

    def recorder(name: str) -> Callable[[argparse.Namespace], int]:
        def record(_args: argparse.Namespace) -> int:
            called.append(name)
            return 0

        return record

    for name in originals:
        monkeypatch.setattr(cli, name, recorder(name))
    parser = cli._build_parser()
    reached: dict[str, str] = {}
    for path, argv in verb_argvs(parser).items():
        try:
            args = parser.parse_args(argv)
        except SystemExit:
            continue  # a group whose verb is required runs nothing alone
        if getattr(args, "command", None) is None:
            continue
        called.clear()
        cli._route(args)
        if called:
            reached[path] = called[0]
    return originals, reached


def cite_problems(
    capabilities: Mapping[str, frozenset[str]], verb_texts: Mapping[str, str], module_text: str
) -> list[str]:
    """A verb's citations are a subset of its row's capabilities; the module's are a subset of their union."""
    problems: list[str] = []
    for path, text in sorted(verb_texts.items()):
        listed = capabilities.get(path, frozenset())
        for cap in sorted(cap_tokens(text) - listed):
            problems.append(f"`{path}` cites {cap}, which its contract row does not name")
    union: frozenset[str] = frozenset().union(*capabilities.values())
    for cap in sorted(cap_tokens(module_text) - union):
        problems.append(f"cli.py cites {cap}, which no contract row names")
    return problems


# --- MCP tools --------------------------------------------------------------------------------------------------

_CONSTANT_RE = re.compile(r"^([A-Z][A-Z0-9_]*)\s*(?::[^=\n]*)?=\s*[\"']([^\"']+)[\"']", re.MULTILINE)
_TOOL_KEYWORD_RE = re.compile(r"(?<![\w])([a-z]+)_tool\s*=(?!=)\s*([A-Z][A-Z0-9_]*|\"[^\"]+\"|'[^']+')")
_TOOL_DECORATOR_RE = re.compile(r"\.tool\(\s*name\s*=\s*([A-Z][A-Z0-9_]*|\"[^\"]+\"|'[^']+')")


def mcp_tools(source: str) -> set[str]:
    """Tool names the face registers: each ``<kind>_tool=`` argument but ``run_tool`` (the supervisor's runner key,
    not an MCP tool), and each ``.tool(name=…)``; constants resolve through their module-level assignment."""
    constants = dict(_CONSTANT_RE.findall(source))

    def resolve(token: str) -> str:
        return token[1:-1] if token[0] in "\"'" else constants.get(token, token)

    tools = {resolve(token) for kind, token in _TOOL_KEYWORD_RE.findall(source) if kind != "run"}
    tools |= {resolve(token) for token in _TOOL_DECORATOR_RE.findall(source)}
    return tools


# --- Python sources: flags, repository keys, environment --------------------------------------------------------


def _string_constants(tree: ast.AST) -> Iterator[tuple[str, str]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            for target in targets:
                if isinstance(target, ast.Name):
                    yield target.id, value.value


def flag_constants(sources: Mapping[str, str]) -> dict[str, str]:
    """Each ``*_FLAG = "<key>"`` constant's key, whatever its prefix, with the module and name that hold it."""
    keys: dict[str, str] = {}
    for module, text in sorted(sources.items()):
        for name, value in _string_constants(ast.parse(text)):
            if name.endswith("_FLAG"):
                keys.setdefault(value, f"{module} {name}")
    return keys


def cutover_importers(sources: Mapping[str, str]) -> list[str]:
    """Modules that import ``pyforge.core.cutover_root``, in any import form."""
    importers: list[str] = []
    for module, text in sorted(sources.items()):
        for node in ast.walk(ast.parse(text)):
            hit = False
            if isinstance(node, ast.Import):
                hit = any(alias.name == CUTOVER_MODULE for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                hit = node.module == CUTOVER_MODULE or (
                    node.module == "pyforge.core" and any(alias.name == "cutover_root" for alias in node.names)
                )
            elif isinstance(node, ast.Call) and node.args:
                first = node.args[0]
                hit = isinstance(first, ast.Constant) and first.value == CUTOVER_MODULE
            if hit:
                importers.append(module)
                break
    return importers


def repository_key_problems(sources: Mapping[str, str], rows: list[list[str]]) -> list[str]:
    listed = {row_key(row) for row in rows}
    importers = cutover_importers(sources)
    problems = [
        f"{module} imports {CUTOVER_MODULE}, but contract.md has no repository-key row naming {CUTOVER_ROSTER_KEY}"
        for module in importers
        if CUTOVER_ROSTER_KEY not in listed
    ]
    required = {CUTOVER_ROSTER_KEY} if importers else set()
    problems += [
        f"contract.md lists repository key `{key}`, which no herald source reads" for key in sorted(listed - required)
    ]
    return problems


_ENV_CONSTANT_RE = re.compile(r"_ENV(?:_VAR)?$")


def _is_os_environ(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "environ"
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
    )


def _binds_environ(value: ast.AST) -> bool:
    """``os.environ``, ``os.environ.copy()``, ``dict(os.environ)``, or a conditional that yields one of them."""
    if _is_os_environ(value):
        return True
    if isinstance(value, ast.Call):
        func = value.func
        if isinstance(func, ast.Attribute) and func.attr == "copy" and _is_os_environ(func.value):
            return True
        if isinstance(func, ast.Name) and func.id == "dict" and value.args and _is_os_environ(value.args[0]):
            return True
    if isinstance(value, ast.IfExp):
        return _binds_environ(value.body) or _binds_environ(value.orelse)
    return False


def _literal(node: ast.AST | None) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _literal_read(node: ast.AST, is_environ: Callable[[ast.AST], bool]) -> str | None:
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.args:
        func = node.func
        if func.attr == "get" and is_environ(func.value):
            return _literal(node.args[0])
        if func.attr == "getenv" and isinstance(func.value, ast.Name) and func.value.id == "os":
            return _literal(node.args[0])
    if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load) and is_environ(node.value):
        return _literal(node.slice)
    return None


def package_env(sources: Mapping[str, str]) -> dict[str, str]:
    """Environment variables the package reads: literals through ``os.environ``/``os.getenv`` or a local bound to
    ``os.environ`` (or a copy), and every string constant named ``*_ENV`` or ``*_ENV_VAR``."""
    names: dict[str, str] = {}
    for module, text in sorted(sources.items()):
        tree = ast.parse(text)
        for name, value in _string_constants(tree):
            if _ENV_CONSTANT_RE.search(name):
                names.setdefault(value, f"{module} {name}")
        for node in ast.walk(tree):
            key = _literal_read(node, _is_os_environ)
            if key is not None:
                names.setdefault(key, module)
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            bound = {
                target.id
                for node in ast.walk(function)
                if isinstance(node, ast.Assign) and _binds_environ(node.value)
                for target in node.targets
                if isinstance(target, ast.Name)
            }
            if not bound:
                continue
            for node in ast.walk(function):
                key = _literal_read(node, lambda value: isinstance(value, ast.Name) and value.id in bound)
                if key is not None:
                    names.setdefault(key, module)
    return names


# --- docs-site sources: flags.ts and the build's environment ----------------------------------------------------

_EXPORTED_FUNCTION_RE = re.compile(r"export\s+(?:async\s+)?function\s+(\w+)")
_DOC_KEY_RE = re.compile(r"`(pyforge\.[a-z_]+\.[a-z_]+)`")


def _doc_comment_before(text: str, position: int) -> str | None:
    head = text[:position].rstrip()
    if not head.endswith("*/"):
        return None
    start = head.rfind("/**")
    if start < 0:
        return None
    lines = (re.sub(r"^\s*\*?\s?", "", line).strip() for line in head[start + 3 : -2].splitlines())
    return " ".join(line for line in lines if line)


def flags_ts_keys(text: str) -> tuple[dict[str, str], list[str]]:
    """Each exported flag reader's key (the backticked ``pyforge.<station>.<name>`` that opens its doc comment), and
    a problem for each exported function other than the generic helpers that documents none."""
    keys: dict[str, str] = {}
    problems: list[str] = []
    for match in _EXPORTED_FUNCTION_RE.finditer(text):
        name = match.group(1)
        if name in FLAG_HELPERS:
            continue
        doc = _doc_comment_before(text, match.start())
        key = _DOC_KEY_RE.match(doc) if doc else None
        if key is None:
            problems.append(
                f"flags.ts exports {name}() with no documented pyforge.<station>.<name> key opening its doc comment"
            )
        else:
            keys.setdefault(key.group(1), f"flags.ts {name}()")
    return keys, problems


_PROCESS_ENV_DOT_RE = re.compile(r"\bprocess\.env\.([A-Z][A-Z0-9_]*)\b")
_PROCESS_ENV_INDEX_RE = re.compile(r"\bprocess\.env\[\s*(?:([A-Z][A-Z0-9_]*)|[\"']([A-Z][A-Z0-9_]*)[\"'])\s*\]")
_EXPORT_CONST_RE = re.compile(r"export\s+const\s+([A-Z][A-Z0-9_]*)\s*(?::[^=]*)?=\s*[\"']([^\"']+)[\"']")
_INJECTED_ENV_RE = re.compile(r"(?<![\w.$])env\??\s*(?::[^=;]*?)?=\s*(?:[^;\n]*\?\?\s*)?process\.env\b")
_ENV_DOT_RE = re.compile(r"(?<![\w.$])env\.([A-Z][A-Z0-9_]*)\b")
_ENV_FLAG_ON_RE = re.compile(r"\benvFlagOn\(\s*[\"']([A-Z][A-Z0-9_]*)[\"']")


def site_env(sources: Mapping[str, str]) -> dict[str, str]:
    """Environment variables the docs-site build reads: ``process.env.X``; ``process.env[CONST]`` through the
    constant's ``export const``; ``env.X`` in a file whose ``env`` record defaults to ``process.env``; and the
    argument of ``envFlagOn('X', …)``. ``import.meta.env`` is Astro's build constant and is never matched."""
    constants: dict[str, str] = {}
    for text in sources.values():
        constants.update(_EXPORT_CONST_RE.findall(text))
    names: dict[str, str] = {}
    for path, text in sorted(sources.items()):
        for name in _PROCESS_ENV_DOT_RE.findall(text):
            names.setdefault(name, f"{path} process.env.{name}")
        for constant, literal in _PROCESS_ENV_INDEX_RE.findall(text):
            name = literal or constants.get(constant, constant)
            names.setdefault(name, f"{path} process.env[{constant or literal}]")
        if _INJECTED_ENV_RE.search(text):
            for name in _ENV_DOT_RE.findall(text):
                names.setdefault(name, f"{path} env.{name}")
        for name in _ENV_FLAG_ON_RE.findall(text):
            names.setdefault(name, f"{path} envFlagOn('{name}')")
    return names


# --- errors and exit codes --------------------------------------------------------------------------------------


def error_surface(classes: Iterable[type[errors.HeraldError]], exit_code_for: Callable[..., int]) -> dict[str, str]:
    """Each class as ``"<parent> <exit code>"``."""
    return {cls.__name__: f"{cls.__mro__[1].__name__} {exit_code_for(cls('probe'))}" for cls in classes}


def herald_error_classes(module: ModuleType) -> list[type[errors.HeraldError]]:
    return [
        value
        for value in vars(module).values()
        if isinstance(value, type) and issubclass(value, module.HeraldError) and value.__module__ == module.__name__
    ]


def contract_errors(rows: list[list[str]]) -> dict[str, str]:
    return {row_key(row): f"{ticked(row[1])[0] if ticked(row[1]) else row[1]} {row[2]}" for row in rows}


def error_problems(code: Mapping[str, str], listed: Mapping[str, str]) -> list[str]:
    problems = set_problems("error class", {name: "pyforge.herald.errors" for name in code}, listed)
    for name in sorted(code.keys() & listed.keys()):
        if code[name] != listed[name]:
            problems.append(
                f"error class `{name}` is `{code[name]}` (parent, exit code) in the code, `{listed[name]}` in contract.md"
            )
    return problems


# --- the live tree ----------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Tree:
    tables: dict[str, list[list[str]]]
    herald: dict[str, str]
    site: dict[str, str]
    mcp_asgi: str
    flags_ts: str


@pytest.fixture(scope="module")
def tree() -> Tree:
    herald = {
        path.relative_to(HERALD_SRC).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(HERALD_SRC.rglob("*.py"))
        if "__pycache__" not in path.parts
    }
    site_paths = [
        path
        for directory in SITE_DIRS
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path.suffix in SITE_SUFFIXES and "node_modules" not in path.parts
    ]
    site_paths += list(SITE_FILES)
    return Tree(
        tables=parse_contract(CONTRACT.read_text(encoding="utf-8")),
        herald=herald,
        site={path.relative_to(REPO_ROOT).as_posix(): path.read_text(encoding="utf-8") for path in site_paths},
        mcp_asgi=MCP_ASGI.read_text(encoding="utf-8"),
        flags_ts=FLAGS_TS.read_text(encoding="utf-8"),
    )


def test_contract_has_one_table_per_kind(tree: Tree) -> None:
    missing = [name for name in TABLES if name not in tree.tables]
    assert not missing, f"contract.md has no `## {'`, `## '.join(missing)}` table"


def test_verbs_and_their_arguments_match_the_parser(tree: Tree) -> None:
    listed, _ = contract_verbs(tree.tables["CLI verbs"])
    problems = verb_problems(cli_verbs(cli._build_parser()), listed)
    assert not problems, "\n".join(problems)


def test_deck_help_lists_its_verbs_from_the_parser() -> None:
    parser = cli._build_parser()
    helps = {path: listed for path, _, listed in walk_parser(parser)}
    deck_verbs = [path.split()[-1] for path in helps if path.startswith("herald deck ")]
    assert len(deck_verbs) == 12
    assert helps["herald deck"] == f"manage Claude Design decks ({'/'.join(deck_verbs)})"


def test_mcp_tools_match_the_face(tree: Tree) -> None:
    code = {name: "django_herald_portal/mcp_asgi.py" for name in mcp_tools(tree.mcp_asgi)}
    problems = set_problems("MCP tool", code, (row_key(row) for row in tree.tables["MCP tools"]))
    assert not problems, "\n".join(problems)


def test_flag_keys_match_the_constants_and_flags_ts(tree: Tree) -> None:
    ts_keys, problems = flags_ts_keys(tree.flags_ts)
    code = {**ts_keys, **flag_constants(tree.herald)}
    problems += set_problems("flag key", code, (row_key(row) for row in tree.tables["Feature-flag keys"]))
    assert not problems, "\n".join(problems)


def test_repository_keys_match_the_core_imports(tree: Tree) -> None:
    problems = repository_key_problems(tree.herald, tree.tables["Repository keys"])
    assert not problems, "\n".join(problems)


def test_environment_variables_match_every_reader(tree: Tree) -> None:
    code = {**site_env(tree.site), **package_env(tree.herald)}
    problems = set_problems(
        "environment variable", code, (row_key(row) for row in tree.tables["Environment variables"])
    )
    assert not problems, "\n".join(problems)


def test_error_classes_and_exit_codes_match_errors_py(tree: Tree) -> None:
    code = error_surface(herald_error_classes(errors), errors.exit_code_for)
    problems = error_problems(code, contract_errors(tree.tables["Error classes"]))
    assert not problems, "\n".join(problems)


def test_exit_codes_are_the_closed_set(tree: Tree, capsys: pytest.CaptureFixture[str]) -> None:
    observed = {
        int(code.split()[-1]) for code in error_surface(herald_error_classes(errors), errors.exit_code_for).values()
    }
    observed |= {cli.main(["--version"]), cli.main([]), cli.main(["no-such-command"])}
    capsys.readouterr()
    listed = {int(row_key(row)) for row in tree.tables["Exit codes"]}
    problems = set_problems("exit code", {str(code): "herald" for code in observed}, (str(code) for code in listed))
    assert not problems, "\n".join(problems)


def test_cli_cites_only_the_capabilities_of_its_contract_rows(tree: Tree, monkeypatch: pytest.MonkeyPatch) -> None:
    _, capabilities = contract_verbs(tree.tables["CLI verbs"])
    originals, reached = route_handlers(monkeypatch)
    parser = cli._build_parser()
    texts = verb_help_texts(parser)
    leaves = [path for path, node, _ in walk_parser(parser) if _subparsers(node) is None]
    unreached = [path for path in leaves if path not in reached]
    assert not unreached, f"no handler reached for {unreached}"
    for path, handler in reached.items():
        texts[path] += "\n" + inspect.getsource(originals[handler])
    module_text = Path(inspect.getfile(cli)).read_text(encoding="utf-8")
    problems = cite_problems(capabilities, texts, module_text)
    assert not problems, "\n".join(problems)


# --- planted differences, over in-memory fixtures ---------------------------------------------------------------

_PLANTED_CONTRACT = """\
## CLI verbs
| Verb path | Arguments | CAP |
|---|---|---|
| `herald` | — | — |
| `herald deck` | — | — |
| `herald deck seed` | `<slug>` `--repo-root` | CAP-1, CAP-4 |
| `herald deck qa` | `<slug>` | CAP-26..CAP-28 |

## MCP tools
| Tool | What it does | CAP |
|---|---|---|
| `start_notice` | starts | spec-pyforge-unifying-strategy:CAP-20 |
| `get_notice` | gets | spec-pyforge-unifying-strategy:CAP-20 |

## Feature-flag keys
| Key | Read by |
|---|---|
| `pyforge.herald.deck_publish` | constant |
| `pyforge.herald.status_pages` | flags.ts |

## Repository keys
| Key | File | Read through |
|---|---|---|

## Environment variables
| Variable | Reader | Read as |
|---|---|---|
| `HERALD_TOKEN` | package | constant |
| `SITE_URL` | docs-site | process.env.X |

## Error classes
| Class | Parent | Exit code |
|---|---|---|
| `HeraldError` | `PyforgeError` | 1 |
| `TransportError` | `HeraldError` | 4 |
"""

_PLANTED_MCP = """\
START_NOTICE_TOOL = "start_notice"
GET_NOTICE_TOOL = "get_notice"
RUN_NOTICE_TOOL = "run_notice"
build(start_tool=START_NOTICE_TOOL, get_tool=GET_NOTICE_TOOL, run_tool=RUN_NOTICE_TOOL)
"""

_PLANTED_FLAGS_TS = """\
/** `name` in `env` reads on. */
export function envFlagOn(name: string, env: Record<string, string | undefined> = process.env): boolean {
  return ['1'].includes(env[name] ?? '');
}

/** `pyforge.herald.status_pages` (Story 42.1): the status pages. */
export function statusPages(): boolean {
  return envFlagOn('PYFORGE_STATUS_PAGES');
}
"""


def _planted_tables() -> dict[str, list[list[str]]]:
    return parse_contract(_PLANTED_CONTRACT)


def _planted_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="herald")
    commands = parser.add_subparsers(dest="command")
    deck = commands.add_parser("deck", help="decks")
    verbs = deck.add_subparsers(dest="deck_command", required=True)
    seed = verbs.add_parser("seed", help="seed a deck (CAP-1, CAP-4)")
    seed.add_argument("slug")
    seed.add_argument("--repo-root")
    qa = verbs.add_parser("qa", help="visual QA (CAP-27)")
    qa.add_argument("slug")
    return parser


def _deck_verbs(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    for path, node, _ in walk_parser(parser):
        if path == "herald deck":
            subs = _subparsers(node)
            assert subs is not None
            return subs
    raise AssertionError("no deck group")


def _planted_verb_problems(parser: argparse.ArgumentParser) -> list[str]:
    listed, _ = contract_verbs(_planted_tables()["CLI verbs"])
    return verb_problems(cli_verbs(parser), listed)


def _named(problems: list[str], *items: str) -> bool:
    return any(all(item in problem for item in items) for problem in problems)


def test_planted_baseline_fixture_agrees_with_itself() -> None:
    assert _planted_verb_problems(_planted_parser()) == []
    assert (
        set_problems(
            "MCP tool",
            dict.fromkeys(mcp_tools(_PLANTED_MCP), "x"),
            (row_key(r) for r in _planted_tables()["MCP tools"]),
        )
        == []
    )


def test_planted_extra_verb_is_named() -> None:
    parser = _planted_parser()
    _deck_verbs(parser).add_parser("frobnicate", help="new")
    assert _named(_planted_verb_problems(parser), "herald deck frobnicate", "missing from contract.md")


def test_planted_extra_option_is_named() -> None:
    parser = _planted_parser()
    _deck_verbs(parser).choices["seed"].add_argument("--frobnicate", action="store_true")
    assert _named(_planted_verb_problems(parser), "herald deck seed", "--frobnicate")


def test_planted_extra_mcp_tool_is_named() -> None:
    source = _PLANTED_MCP + '@server.tool(name="list_notice")\ndef _list(): ...\n'
    problems = set_problems(
        "MCP tool", dict.fromkeys(mcp_tools(source), "x"), (row_key(r) for r in _planted_tables()["MCP tools"])
    )
    assert _named(problems, "list_notice", "missing from contract.md")
    assert not _named(problems, "run_notice")


def test_planted_extra_flag_constant_is_named() -> None:
    sources = {
        "deck_publish.py": 'DECK_PUBLISH_FLAG = "pyforge.herald.deck_publish"\n',
        "new_thing.py": 'NEW_THING_FLAG: str = "pyforge.herald.new_thing"\n',
    }
    ts_keys, ts_problems = flags_ts_keys(_PLANTED_FLAGS_TS)
    assert ts_problems == []
    code = {**ts_keys, **flag_constants(sources)}
    problems = set_problems("flag key", code, (row_key(r) for r in _planted_tables()["Feature-flag keys"]))
    assert _named(problems, "pyforge.herald.new_thing", "new_thing.py NEW_THING_FLAG")


def test_planted_flags_ts_function_without_a_key_is_named() -> None:
    text = (
        _PLANTED_FLAGS_TS
        + "\n/** Whether the banner shows. */\nexport function bannerShown(): boolean {\n  return true;\n}\n"
    )
    _, problems = flags_ts_keys(text)
    assert _named(problems, "bannerShown()", "no documented pyforge.<station>.<name> key")
    assert not _named(problems, "envFlagOn")


def test_planted_env_flag_on_is_exempt_only_by_name() -> None:
    renamed = _PLANTED_FLAGS_TS.replace("export function envFlagOn", "export function envFlagRead")
    _, problems = flags_ts_keys(renamed)
    assert _named(problems, "envFlagRead()")


def test_planted_process_env_read_is_named() -> None:
    sources = {
        "docs-site/src/lib/site-url.mjs": "const u = process.env.SITE_URL;\nconst n = process.env.NEW_SITE_VAR;\n"
    }
    problems = set_problems(
        "environment variable", site_env(sources), (row_key(r) for r in _planted_tables()["Environment variables"])
    )
    assert _named(problems, "NEW_SITE_VAR", "process.env.NEW_SITE_VAR")


def test_planted_injected_env_read_is_named() -> None:
    sources = {
        "docs-site/src/lib/built.ts": (
            "export function built(env: Record<string, string | undefined> = process.env): string {\n"
            "  return (env.GITHUB_RUN_ATTEMPT ?? '').trim();\n}\n"
        ),
        "docs-site/scripts/build.mts": "const env = options.env ?? process.env;\nconst p = env.HERALD_NEW_KNOB;\n",
    }
    found = site_env(sources)
    problems = set_problems(
        "environment variable", found, (row_key(r) for r in _planted_tables()["Environment variables"])
    )
    assert _named(problems, "GITHUB_RUN_ATTEMPT", "env.GITHUB_RUN_ATTEMPT")
    assert _named(problems, "HERALD_NEW_KNOB", "env.HERALD_NEW_KNOB")


def test_planted_env_record_without_a_process_env_default_is_not_read() -> None:
    sources = {"docs-site/src/lib/config.ts": "const env = loadConfig();\nconst x = env.NOT_AN_ENV_READ;\n"}
    assert site_env(sources) == {}


def test_planted_process_env_index_resolves_its_constant() -> None:
    sources = {
        "docs-site/src/lib/agent-surface.ts": (
            "export const INPUTS_DIR_ENV = 'PAGES_BUILD_INPUTS_DIR';\nconst o = process.env[INPUTS_DIR_ENV];\n"
        )
    }
    assert set(site_env(sources)) == {"PAGES_BUILD_INPUTS_DIR"}


def test_planted_env_flag_on_argument_is_named() -> None:
    sources = {"docs-site/scripts/pages.mts": "const on = envFlagOn('PYFORGE_NEW_PAGES', env);\n"}
    assert set(site_env(sources)) == {"PYFORGE_NEW_PAGES"}


def test_planted_import_meta_env_is_not_an_environment_read() -> None:
    sources = {
        "docs-site/src/components/Title.astro": (
            "const base = import.meta.env.BASE_URL;\n"
            "export function f(env: Env = process.env) { return env.SITE_URL; }\n"
        )
    }
    assert set(site_env(sources)) == {"SITE_URL"}


def test_planted_package_env_reads_are_named() -> None:
    sources = {
        "auth.py": 'TOKEN_ENV_VAR = "HERALD_TOKEN"\n',
        "store.py": 'BUCKET_ENV: Final[str] = "OBJECT_STORAGE_NEW_BUCKET"\n',
        "proof.py": 'import os\nif os.environ.get("HERALD_NEW_PROOF") == "1":\n    pass\nos.getenv("HERALD_GETENV")\n',
        "node.py": (
            "import os\ndef node_env():\n    env = os.environ.copy()\n"
            '    path = env.get("NODE_NEW_PATH", "")\n    env["NOT_A_READ"] = path\n    return env\n'
        ),
        "doc.py": '"""Reads ``os.environ["IN_A_DOCSTRING"]``."""\n',
    }
    found = package_env(sources)
    assert set(found) == {
        "HERALD_TOKEN",
        "OBJECT_STORAGE_NEW_BUCKET",
        "HERALD_NEW_PROOF",
        "HERALD_GETENV",
        "NODE_NEW_PATH",
    }
    problems = set_problems(
        "environment variable", found, (row_key(r) for r in _planted_tables()["Environment variables"])
    )
    assert _named(problems, "OBJECT_STORAGE_NEW_BUCKET", "store.py BUCKET_ENV")


def test_planted_extra_error_class_is_named() -> None:
    class PlantedError(errors.HeraldError):
        """An error class the contract does not list."""

    classes = [errors.HeraldError, errors.TransportError, PlantedError]
    code = error_surface(classes, errors.exit_code_for)
    problems = error_problems(code, contract_errors(_planted_tables()["Error classes"]))
    assert _named(problems, "PlantedError", "missing from contract.md")


def test_planted_changed_exit_code_is_named() -> None:
    code = error_surface([errors.HeraldError, errors.TransportError], lambda error: 7)
    problems = error_problems(code, contract_errors(_planted_tables()["Error classes"]))
    assert _named(problems, "TransportError", "HeraldError 7")


@pytest.mark.parametrize(
    ("table", "kind", "code"),
    [
        ("MCP tools", "MCP tool", {"start_notice": "x"}),
        ("Feature-flag keys", "flag key", {"pyforge.herald.deck_publish": "x"}),
        ("Environment variables", "environment variable", {"HERALD_TOKEN": "x"}),
    ],
)
def test_planted_contract_row_the_code_lacks_is_named(table: str, kind: str, code: dict[str, str]) -> None:
    rows = _planted_tables()[table]
    problems = set_problems(kind, code, (row_key(r) for r in rows))
    lacking = sorted({row_key(r) for r in rows} - code.keys())
    assert lacking
    assert all(_named(problems, f"contract.md lists {kind} `{item}`", "the code lacks") for item in lacking)


def test_planted_contract_verb_row_the_parser_lacks_is_named() -> None:
    parser = argparse.ArgumentParser(prog="herald")
    commands = parser.add_subparsers(dest="command")
    deck = commands.add_parser("deck")
    seed = deck.add_subparsers(dest="deck_command").add_parser("seed")
    seed.add_argument("slug")
    problems = _planted_verb_problems(parser)
    assert _named(problems, "contract.md lists verb `herald deck qa`", "the code lacks")
    assert _named(problems, "contract.md lists `--repo-root` on `herald deck seed`", "the parser lacks")


def test_planted_contract_error_row_the_code_lacks_is_named() -> None:
    code = error_surface([errors.HeraldError], errors.exit_code_for)
    problems = error_problems(code, contract_errors(_planted_tables()["Error classes"]))
    assert _named(problems, "contract.md lists error class `TransportError`", "the code lacks")


def test_planted_cutover_import_without_a_roots_this_row_is_named() -> None:
    sources = {
        "local_ship.py": "from pyforge.core.cutover_root import forge_slug_for\n",
        "deck_store.py": "import os\n",
    }
    problems = repository_key_problems(sources, _planted_tables()["Repository keys"])
    assert _named(problems, "local_ship.py", "pyforge.core.cutover_root", "roots.this")
    assert not _named(problems, "deck_store.py")
    for form in ("from pyforge.core import cutover_root\n", "import pyforge.core.cutover_root\n"):
        assert _named(repository_key_problems({"other.py": form}, []), "other.py", "roots.this")
    with_row = [["`roots.this`", "`docs/governance/guild-roster.json`", "`forge_slug_for`"]]
    assert repository_key_problems(sources, with_row) == []


def test_planted_roots_this_row_without_an_import_is_named() -> None:
    rows = [["`roots.this`", "`docs/governance/guild-roster.json`", "`forge_slug_for`"]]
    problems = repository_key_problems({"deck_store.py": "import os\n"}, rows)
    assert _named(problems, "contract.md lists repository key `roots.this`", "no herald source reads")


def test_planted_cli_cites_a_capability_its_row_lacks() -> None:
    _, capabilities = contract_verbs(_planted_tables()["CLI verbs"])
    texts = verb_help_texts(_planted_parser())
    assert cite_problems(capabilities, texts, "CAP-1 CAP-4 CAP-27") == []
    texts["herald deck seed"] += '\n    """``herald deck seed`` (Story 1.6, CAP-2)."""'
    problems = cite_problems(capabilities, texts, "CAP-1 CAP-4 CAP-27 CAP-99")
    assert _named(problems, "`herald deck seed` cites CAP-2", "does not name")
    assert _named(problems, "cli.py cites CAP-99", "no contract row names")


def test_planted_cap_tokens_read_ranges_and_qualified_ids() -> None:
    assert cap_tokens("CAP-26..CAP-28") == {"CAP-26", "CAP-27", "CAP-28"}
    assert cap_tokens("(Story 23.6, CAP-36 + CAP-31's sweep half)") == {"CAP-36", "CAP-31"}
    assert cap_tokens("spec-pyforge-unifying-strategy:CAP-20") == {"spec-pyforge-unifying-strategy:CAP-20"}
    assert cap_tokens("spec-pyforge-herald CAP-62") == {"CAP-62"}
    assert cap_tokens("—") == set()
