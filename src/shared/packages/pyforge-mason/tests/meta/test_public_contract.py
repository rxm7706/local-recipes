"""Story 38.1 (spec-pyforge-mason CAP-5, FR-60; decision D1): Mason's public
contract is the companion `contract.md`, and this module holds the code to it.

Seven families are judged: parser paths, options (with positionals), environment
variables, exit codes, error identifiers, MCP and portal names, and feature-flag
keys. For each, the code side is extracted here and compared with the backticked
first cell of every table row under that family's `##` heading in `contract.md`
(the second cell too, for an exit code's number). A family fails, naming each
item, when the code has an item `contract.md` lacks or `contract.md` names one
the code lacks. Prose outside those tables is not judged.

How the code side is extracted:

1. Parser paths and options: `build_parser()` walked through its subparsers.
   argparse's own `-h`/`--help` is skipped. The six global options are listed
   once in the contract and apply to every parser path.
2. Environment variables, by `ast` over the package source: every module-level
   name whose identifier contains `ENV` bound to an UPPER_SNAKE string literal,
   every string member of a module-level tuple whose identifier contains
   `CREDENTIAL`, and every UPPER_SNAKE literal passed as the first argument of
   `.get(` on `environ`/`env` (or `os.environ`), or used as an `environ[...]` key.
3. Exit codes: the module-level `EXIT_*` names of `exit_codes.py`, with their values.
4. Error identifiers: the literal first argument of each `super().__init__` in
   `errors.py`.
5. MCP and portal names: every module-level `*_TOOL` constant in django-mason's
   `mcp_asgi.py` and `LAST_DIAGNOSE_TOOL` in django-pyforge's
   `assertion/client.py`, read as text with `ast` -- neither package is imported.
6. Feature-flag keys: string literals passed to a `pyforge.core.flags` reader in
   the package source (none today).

The `planted` cases prove each family fires in both directions: an item planted
on the code side only, and a row planted in the contract only. No recipe
knowledge enters this module. It reads the planning tree and two other packages,
so it is in the live-tree half; it hands the repository root to no package code.
"""

from __future__ import annotations

import argparse
import ast
import re
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from pyforge.mason.cli import build_parser

pytestmark = pytest.mark.live_tree

PKG_ROOT = Path(__file__).resolve().parents[2]
PKG_SRC = PKG_ROOT / "src" / "pyforge" / "mason"
REPO_ROOT = PKG_ROOT.parents[3]
CONTRACT = (
    REPO_ROOT
    / "_bmad-output"
    / "projects"
    / "pyforge-mason"
    / "planning-artifacts"
    / "specs"
    / "spec-pyforge-mason"
    / "contract.md"
)
MCP_ASGI = REPO_ROOT / "src" / "shared" / "packages" / "django-mason" / "src" / "django_mason_portal" / "mcp_asgi.py"
ASSERTION_CLIENT = (
    REPO_ROOT / "src" / "shared" / "packages" / "django-pyforge" / "src" / "django_pyforge" / "assertion" / "client.py"
)

PARSER_PATH = "parser path"
OPTION = "option"
ENVIRONMENT_VARIABLE = "environment variable"
EXIT_CODE = "exit code"
ERROR_IDENTIFIER = "error identifier"
PORTAL_NAME = "MCP or portal name"
FLAG_KEY = "flag key"
FAMILIES = (PARSER_PATH, OPTION, ENVIRONMENT_VARIABLE, EXIT_CODE, ERROR_IDENTIFIER, PORTAL_NAME, FLAG_KEY)

HEADING_PATHS = "Parser paths"
HEADING_GLOBAL_OPTIONS = "Global options"
HEADING_OPTIONS = "Options and positionals"
HEADING_ENVIRONMENT = "Environment variables"
HEADING_EXIT_CODES = "Exit codes"
HEADING_ERRORS = "Error identifiers"
HEADING_NAMES = "MCP tool and portal-job names"
HEADING_FLAGS = "Feature-flag keys"
HEADINGS = (
    HEADING_PATHS,
    HEADING_GLOBAL_OPTIONS,
    HEADING_OPTIONS,
    HEADING_ENVIRONMENT,
    HEADING_EXIT_CODES,
    HEADING_ERRORS,
    HEADING_NAMES,
    HEADING_FLAGS,
)

_ROW = re.compile(r"^\| `([^`]+)` \|(.*)$")
_UPPER_SNAKE = re.compile(r"^[A-Z][A-Z0-9_]+$")
_FLAG_KEY_SHAPE = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)+$")
_FLAGS_MODULE = "pyforge.core.flags"
_FLAG_READERS = frozenset({"read_boolean", "kill_switch_on", "require", "disabled_help"})
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)


@dataclass(frozen=True)
class CodeInputs:
    """Everything the code side is extracted from."""

    parser: argparse.ArgumentParser
    sources: Mapping[str, str]  # package source, path relative to PKG_SRC -> text
    portal: Mapping[str, str]  # "mcp_asgi.py" / "client.py" -> text


# --- the code side -----------------------------------------------------------


def _package_sources() -> dict[str, str]:
    return {path.relative_to(PKG_SRC).as_posix(): path.read_text(encoding="utf-8") for path in PKG_SRC.rglob("*.py")}


def _real_inputs() -> CodeInputs:
    return CodeInputs(
        parser=build_parser(),
        sources=_package_sources(),
        portal={
            "mcp_asgi.py": MCP_ASGI.read_text(encoding="utf-8"),
            "client.py": ASSERTION_CLIENT.read_text(encoding="utf-8"),
        },
    )


def _subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    return next(action for action in parser._actions if isinstance(action, argparse._SubParsersAction))


def _parser_items(parser: argparse.ArgumentParser) -> tuple[set[str], set[str]]:
    """Every parser path, and every `<path> <option>` / `<path> <positional>`."""
    paths: set[str] = set()
    options: set[str] = set()

    def walk(node: argparse.ArgumentParser, path: str) -> None:
        paths.add(path)
        for action in node._actions:
            if isinstance(action, argparse._HelpAction):
                continue
            if isinstance(action, argparse._SubParsersAction):
                for name, child in action.choices.items():
                    walk(child, f"{path} {name}")
                continue
            argument = "/".join(action.option_strings) if action.option_strings else str(action.metavar or action.dest)
            options.add(f"{path} {argument}")

    walk(parser, parser.prog)
    return paths, options


def _module_level_bindings(tree: ast.Module) -> Iterator[tuple[str, ast.expr]]:
    """`(name, value)` for every module-scope assignment to a plain name."""
    stack: list[ast.AST] = [tree]
    while stack:
        node = stack.pop()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, _SCOPES):
                continue
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        yield target.id, child.value
            elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name) and child.value is not None:
                yield child.target.id, child.value
            stack.append(child)


def _string(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _upper_snake(node: ast.AST) -> str | None:
    value = _string(node)
    return value if value is not None and _UPPER_SNAKE.match(value) else None


def _is_environ(node: ast.AST) -> bool:
    return (isinstance(node, ast.Name) and node.id in {"environ", "env"}) or (
        isinstance(node, ast.Attribute) and node.attr == "environ"
    )


def _environment_variables(sources: Mapping[str, str]) -> set[str]:
    found: set[str] = set()
    for text in sources.values():
        tree = ast.parse(text)
        for name, value in _module_level_bindings(tree):
            variable = _upper_snake(value)
            if "ENV" in name and variable is not None:
                found.add(variable)
            if "CREDENTIAL" in name and isinstance(value, ast.Tuple):
                found.update(item for item in map(_string, value.elts) if item is not None)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and _is_environ(node.func.value)
                and node.args
            ):
                variable = _upper_snake(node.args[0])
            elif isinstance(node, ast.Subscript) and _is_environ(node.value):
                variable = _upper_snake(node.slice)
            else:
                continue
            if variable is not None:
                found.add(variable)
    return found


def _exit_codes(sources: Mapping[str, str]) -> set[str]:
    tree = ast.parse(sources["exit_codes.py"])
    return {
        f"{name} = {ast.unparse(value)}" for name, value in _module_level_bindings(tree) if name.startswith("EXIT_")
    }


def _error_identifiers(sources: Mapping[str, str]) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(sources["errors.py"])):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "__init__"
            and isinstance(node.func.value, ast.Call)
            and isinstance(node.func.value.func, ast.Name)
            and node.func.value.func.id == "super"
            and node.args
        ):
            identifier = _string(node.args[0])
            if identifier is not None:
                found.add(identifier)
    return found


def _portal_names(portal: Mapping[str, str]) -> set[str]:
    found = {
        value
        for name, node in _module_level_bindings(ast.parse(portal["mcp_asgi.py"]))
        if name.endswith("_TOOL") and (value := _string(node)) is not None
    }
    found.update(
        value
        for name, node in _module_level_bindings(ast.parse(portal["client.py"]))
        if name == "LAST_DIAGNOSE_TOOL" and (value := _string(node)) is not None
    )
    return found


def _flag_keys(sources: Mapping[str, str]) -> set[str]:
    """Flag-key literals (or module-level string constants) passed to a reader
    imported from `pyforge.core.flags`, called bare or through the module."""
    found: set[str] = set()
    for text in sources.values():
        tree = ast.parse(text)
        readers: set[str] = set()
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == _FLAGS_MODULE:
                readers.update(alias.asname or alias.name for alias in node.names if alias.name in _FLAG_READERS)
            elif isinstance(node, ast.ImportFrom) and node.module == "pyforge.core":
                modules.update(alias.asname or alias.name for alias in node.names if alias.name == "flags")
            elif isinstance(node, ast.Import):
                modules.update(alias.asname or alias.name for alias in node.names if alias.name == _FLAGS_MODULE)
        constants = {name: value for name, node in _module_level_bindings(tree) if (value := _string(node)) is not None}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                (isinstance(func, ast.Name) and func.id in readers)
                or (
                    isinstance(func, ast.Attribute)
                    and func.attr in _FLAG_READERS
                    and ast.unparse(func.value) in modules
                )
            ):
                continue
            for argument in [*node.args, *(keyword.value for keyword in node.keywords)]:
                value = constants.get(argument.id) if isinstance(argument, ast.Name) else _string(argument)
                if value is not None and _FLAG_KEY_SHAPE.match(value):
                    found.add(value)
    return found


def code_side(inputs: CodeInputs) -> dict[str, set[str]]:
    paths, options = _parser_items(inputs.parser)
    return {
        PARSER_PATH: paths,
        OPTION: options,
        ENVIRONMENT_VARIABLE: _environment_variables(inputs.sources),
        EXIT_CODE: _exit_codes(inputs.sources),
        ERROR_IDENTIFIER: _error_identifiers(inputs.sources),
        PORTAL_NAME: _portal_names(inputs.portal),
        FLAG_KEY: _flag_keys(inputs.sources),
    }


# --- the contract side -------------------------------------------------------


def _sections(text: str) -> dict[str, list[str]]:
    """The lines under each `## ` heading (a `###` subsection stays in its section)."""
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
            assert title not in sections, f"contract.md: heading `## {title}` appears twice"
            current = sections[title] = []
        elif current is not None:
            current.append(line)
    missing = [heading for heading in HEADINGS if heading not in sections]
    assert not missing, f"contract.md: missing heading(s) {missing} -- keep the `##` headings exact"
    return sections


def _rows(lines: list[str]) -> list[tuple[str, str]]:
    """`(first cell, second cell)` of every table row whose first cell is backticked."""
    rows: list[tuple[str, str]] = []
    for line in lines:
        match = _ROW.match(line)
        if match is not None:
            rows.append((match.group(1), match.group(2).split("|")[0].strip().strip("`")))
    return rows


def contract_side(text: str) -> dict[str, list[str]]:
    sections = _sections(text)

    def first_cells(heading: str) -> list[str]:
        return [first for first, _ in _rows(sections[heading])]

    paths = first_cells(HEADING_PATHS)
    global_options = first_cells(HEADING_GLOBAL_OPTIONS)
    return {
        PARSER_PATH: paths,
        OPTION: [f"{path} {option}" for path in paths for option in global_options] + first_cells(HEADING_OPTIONS),
        ENVIRONMENT_VARIABLE: first_cells(HEADING_ENVIRONMENT),
        EXIT_CODE: [f"{name} = {value}" for name, value in _rows(sections[HEADING_EXIT_CODES])],
        ERROR_IDENTIFIER: first_cells(HEADING_ERRORS),
        PORTAL_NAME: first_cells(HEADING_NAMES),
        FLAG_KEY: first_cells(HEADING_FLAGS),
    }


def family_drift(family: str, code: Mapping[str, set[str]], contract: Mapping[str, list[str]]) -> list[str]:
    listed: set[str] = set()
    problems: list[str] = []
    for item in contract[family]:
        if item in listed:
            problems.append(f"{family}: listed twice in contract.md: {item}")
        listed.add(item)
    problems += [f"{family}: in the code, not in contract.md: {item}" for item in sorted(code[family] - listed)]
    problems += [f"{family}: in contract.md, not in the code: {item}" for item in sorted(listed - code[family])]
    return problems


# --- the tree ------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_inputs() -> CodeInputs:
    return _real_inputs()


@pytest.fixture(scope="module")
def contract_text() -> str:
    return CONTRACT.read_text(encoding="utf-8")


@pytest.mark.parametrize("family", FAMILIES)
def test_contract_matches_the_code(family: str, real_inputs: CodeInputs, contract_text: str) -> None:
    code = code_side(real_inputs)
    if family != FLAG_KEY:
        # Guard the guard: an extractor that finds nothing would pass against an empty table.
        assert code[family], f"{family}: the code-side extractor found nothing -- did a source move?"
    problems = family_drift(family, code, contract_side(contract_text))
    assert not problems, "contract.md and the code differ:\n" + "\n".join(problems)


# --- planted violations, both directions per family ----------------------------


def _plant_parser_path(inputs: CodeInputs) -> CodeInputs:
    parser = build_parser()
    recipe = _subparsers(parser).choices["recipe"]
    _subparsers(recipe).add_parser("planted")
    return replace(inputs, parser=parser)


def _plant_option(inputs: CodeInputs) -> CodeInputs:
    parser = build_parser()
    new = _subparsers(_subparsers(parser).choices["recipe"]).choices["new"]
    new.add_argument("--planted-option")
    return replace(inputs, parser=parser)


def _plant_source(path: str, text: str) -> Callable[[CodeInputs], CodeInputs]:
    def plant(inputs: CodeInputs) -> CodeInputs:
        sources = dict(inputs.sources)
        sources[path] = sources.get(path, "") + text
        return replace(inputs, sources=sources)

    return plant


def _plant_portal(inputs: CodeInputs) -> CodeInputs:
    portal = dict(inputs.portal)
    portal["mcp_asgi.py"] += '\nPLANTED_TOOL = "planted_tool"\n'
    return replace(inputs, portal=portal)


_PLANTED_ERROR = """

class PlantedError(MasonError):
    def __init__(self) -> None:
        super().__init__("planted:identifier", "planted for the contract test")
"""

_PLANTED_FLAG_READ = """
from pyforge.core.flags import read_boolean

if read_boolean("pyforge.mason.planted_flag"):
    pass
"""

# family -> (the item, how to plant it in the code, the contract heading, the contract row)
PLANTS: dict[str, tuple[str, Callable[[CodeInputs], CodeInputs], str, str]] = {
    PARSER_PATH: (
        "mason recipe planted",
        _plant_parser_path,
        HEADING_PATHS,
        "| `mason recipe planted` | — | planted |",
    ),
    OPTION: (
        "mason recipe new --planted-option",
        _plant_option,
        HEADING_OPTIONS,
        "| `mason recipe new --planted-option` | option | planted |",
    ),
    ENVIRONMENT_VARIABLE: (
        "MASON_PLANTED",
        _plant_source("planted.py", '_ENV_PLANTED = "MASON_PLANTED"\n'),
        HEADING_ENVIRONMENT,
        "| `MASON_PLANTED` | read | planted |",
    ),
    EXIT_CODE: (
        "EXIT_PLANTED = 99",
        _plant_source("exit_codes.py", "\nEXIT_PLANTED = 99\n"),
        HEADING_EXIT_CODES,
        "| `EXIT_PLANTED` | 99 | planted |",
    ),
    ERROR_IDENTIFIER: (
        "planted:identifier",
        _plant_source("errors.py", _PLANTED_ERROR),
        HEADING_ERRORS,
        "| `planted:identifier` | `PlantedError` | planted |",
    ),
    PORTAL_NAME: (
        "planted_tool",
        _plant_portal,
        HEADING_NAMES,
        "| `planted_tool` | MCP tool | planted |",
    ),
    FLAG_KEY: (
        "pyforge.mason.planted_flag",
        _plant_source("planted.py", _PLANTED_FLAG_READ),
        HEADING_FLAGS,
        "| `pyforge.mason.planted_flag` | off | planted |",
    ),
}


def _plant_row(text: str, heading: str, row: str) -> str:
    """Insert `row` after the last table line under `## heading`."""
    lines = text.splitlines()
    start = lines.index(f"## {heading}")
    end = next((index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")), len(lines))
    last = max(index for index in range(start, end) if lines[index].startswith("|"))
    lines.insert(last + 1, row)
    return "\n".join(lines) + "\n"


@pytest.mark.parametrize(
    ("family", "side"),
    [(family, side) for family in FAMILIES for side in ("code", "contract")],
    ids=[f"{family.replace(' ', '-')}-only-in-the-{side}" for family in FAMILIES for side in ("code", "contract")],
)
def test_planted_item_fails_its_family(family: str, side: str, real_inputs: CodeInputs, contract_text: str) -> None:
    item, plant_code, heading, row = PLANTS[family]
    if side == "code":
        expected = f"{family}: in the code, not in contract.md: {item}"
        code, text = code_side(plant_code(real_inputs)), contract_text
    else:
        expected = f"{family}: in contract.md, not in the code: {item}"
        code, text = code_side(real_inputs), _plant_row(contract_text, heading, row)
    baseline = family_drift(family, code_side(real_inputs), contract_side(contract_text))
    assert expected not in baseline, f"the planted item is already drift on the tree: {expected}"
    assert expected in family_drift(family, code, contract_side(text))
