"""Story 26.1 (spec-pyforge-warden CAP-28, FR-45; decision D1): warden's public contract is one companion.

``contract.md``, beside ``SPEC.md``, lists every surface a caller of warden reaches. Sections 1 to 7 are
this test's (sections 8 to 12 are ``test_contract_surface.py``'s, Story 26.3). Each inventory is derived
from the code, never from a hand list, and compared both ways with its ``contract.md`` table: a code item
with no row is ``unlisted``, a row naming something the code no longer has is a ``stale row``.

Derivation rules, stated so the guard is not blind:

* CLI: the actions of ``cli._build_parser()``: the subcommand, the scan positional, every option string
  (argparse's own ``-h``/``--help`` aside) and the top-level ``--version``.
* Configuration keys: ``config._RECOGNIZED_KEYS``; each default from ``config.EffectiveConfig()``; the CLI
  column from the scan parser (a key has a flag when ``--<key>`` is a scan option).
* Exit codes, status rungs, error kinds, finding-id families: ``verdict.LATTICE`` and ``verdict.EXIT_SIGINT``,
  ``models.Status``, ``models.ErrorKind``, ``models._FINDING_ID_FAMILIES``; the report schema's ``$id`` from
  the bundled ``data/report-schema.json`` and its version from ``report.REPORT_SCHEMA_VERSION``.
* Feature flags: an AST scan for module-level string constants whose value starts ``pyforge.warden.``, in
  the kernel and in ``django-warden``, plus any such literal handed to a reader; compared both ways with the
  ``pyforge.warden.*`` rows of ``src/platform/config/flags.json`` and, per environment, of
  ``flag-overlays.json``. A flag's readers are the modules that hand its key to ``read_boolean``,
  ``require``, ``disabled_help``, ``evaluate_from_source`` or ``evaluate_boolean``.
* Environment variables, by AST over every module of a unit (the kernel; ``django-warden``): a read is an
  upper-case string (a literal or a module constant) passed to ``.get()``, ``.pop()``, ``.setdefault()`` or
  ``os.getenv()``, or used as a Load-context subscript, on ``os.environ`` or on a name bound to an
  environment mapping (``env``, ``environ``, ``source``), plus every ``ENV_*``, ``*_ENV`` and ``*_ENV_VAR``
  constant; a set is a Store-context subscript on such a mapping, or a string key of a dict literal passed
  as ``env=`` or ``extra_env=`` or to ``<mapping>.update()`` (so finding-id and licence dict literals are not
  variables); a pass-through is an element of a ``*_ENV_KEYS`` tuple; a Django setting is a ``*_SETTING``
  constant or the name handed to ``getattr(settings, ...)``.
* MCP tools: the ``@server.tool()`` functions of ``django-warden``'s ``mcp_asgi.py``, with their arguments.
* Management commands: ``django-warden``'s ``management/commands/*.py``, each with its arguments and the
  flag it ``require``s.

``contract.md`` is read only through the table rows under its exact headings (below), and only through the
backticked tokens and the plain cells this test names. Every outside path is a ``Path(__file__)``-anchored
constant, so steward's trigger-map scanner derives the reads. Negative tests use synthetic inventories and
synthetic source text, never a mutated tracked file.
"""

from __future__ import annotations

import argparse
import ast
import functools
import json
import re
from collections.abc import Callable, Iterable, Mapping
from enum import Enum
from pathlib import Path

import pytest
from pyforge.core.flags import ENVIRONMENTS

from pyforge.warden import cli, config, models, report, verdict

pytestmark = pytest.mark.live_tree

# tests/meta -> tests -> pyforge-warden -> packages -> shared -> src -> repo root
REPO_ROOT = Path(__file__).resolve().parents[6]
PACKAGE_SRC = Path(__file__).resolve().parents[2] / "src"
REPORT_SCHEMA = PACKAGE_SRC / "pyforge" / "warden" / "data" / "report-schema.json"
CONTRACT = REPO_ROOT / "_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/contract.md"
FLAGS_JSON = REPO_ROOT / "src/platform/config/flags.json"
FLAG_OVERLAYS_JSON = REPO_ROOT / "src/platform/config/flag-overlays.json"
DJANGO_WARDEN_SRC = REPO_ROOT / "src/shared/packages/django-warden/src"

KERNEL_PACKAGE = "pyforge/warden"
DJANGO_PACKAGE = "django_warden_fabric"
MCP_MODULE = f"{DJANGO_PACKAGE}/mcp_asgi.py"
COMMANDS_DIR = f"{DJANGO_PACKAGE}/management/commands/"

KERNEL = "kernel"
DJANGO = "django-warden"
READ = "read"
SET_FOR_ENGINE = "set for engine"
SET = "set"
PASS_THROUGH = "pass-through"
SETTING = "setting"

# Story 26.1's frozen equalities (the spec's own words: the derived kernel read set is exactly the seven,
# the set-for-engine set exactly the four).
KERNEL_READS = frozenset(
    {
        "GH_TOKEN",
        "GITHUB_API_URL",
        "GITHUB_REPOSITORY",
        "GITHUB_TOKEN",
        "OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY",
        "PYFORGE_WARDEN_FEED_CACHE_DIR",
        "WARDEN_OPTIONAL_SCANNERS",
    }
)
KERNEL_SETS_FOR_ENGINE = frozenset(
    {"NO_COLOR", "SEMGREP_SEND_METRICS", "OPENGREP_ENABLE_VERSION_CHECK", "OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY"}
)
SCHEMA_VERSION_FROZEN = "1.1.0"  # operator ruling 2026-11-10

H_CLI = "## 1. CLI"
H_KEYS = "## 2. Configuration keys"
H_EXIT = "### 3.1 Exit codes"
H_RUNGS = "### 3.2 Status rungs"
H_KINDS = "### 3.3 Error kinds"
H_FAMILIES = "### 3.4 Finding-id families"
H_SCHEMA = "### 3.5 Report schema"
H_FLAGS = "## 4. Feature flags"
H_ENV = "## 5. Environment variables"
H_MCP = "## 6. MCP tools"
H_COMMANDS = "## 7. Management commands"

_TOKEN = re.compile(r"`([^`]+)`")
_CAP = re.compile(r"\bCAP-\d+\b")
_HEADING = re.compile(r"(#+) ")
_SEPARATOR = re.compile(r"\|[-:| ]+\|")
_FLAG_PREFIX = "pyforge.warden."
_FLAG_READERS = frozenset({"read_boolean", "require", "disabled_help", "evaluate_from_source", "evaluate_boolean"})
_ENV_MAPPINGS = frozenset({"env", "environ", "source"})
_ENV_KEY = re.compile(r"[A-Z][A-Z0-9_]*\Z")
_ENV_CONSTANT = re.compile(r"\AENV_|_ENV\Z|_ENV_VAR\Z")
_PASS_THROUGH_CONSTANT = re.compile(r"_ENV_KEYS\Z")
_SETTING_CONSTANT = re.compile(r"_SETTING\Z")
_READ_METHODS = frozenset({"get", "pop", "setdefault"})
_SET_KEYWORDS = frozenset({"env", "extra_env"})

Problems = list[str]
EnvKey = tuple[str, str, str]  # (variable, unit, role)

# ---------------------------------------------------------------------------
# Reading contract.md
# ---------------------------------------------------------------------------


def _section(text: str, heading: str) -> str:
    """The body under ``heading``, up to the next heading of the same or a higher level."""
    level = len(heading) - len(heading.lstrip("#"))
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith(heading):
            body: list[str] = []
            for following in lines[index + 1 :]:
                match = _HEADING.match(following)
                if match and len(match.group(1)) <= level:
                    break
                body.append(following)
            return "\n".join(body)
    raise AssertionError(f"contract.md has no heading {heading!r}; keep the headings exact")


def _rows(block: str) -> list[list[str]]:
    """Every data row of every table in ``block`` (each table's header and separator skipped)."""
    rows: list[list[str]] = []
    in_table = False
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            in_table = False
            continue
        if not in_table:
            in_table = True  # the header row
            continue
        if _SEPARATOR.fullmatch(stripped):
            continue
        rows.append([cell.strip() for cell in stripped.strip("|").split("|")])
    return rows


def _tokens(cell: str) -> list[str]:
    return _TOKEN.findall(cell)


def _plain(cell: str) -> str:
    return cell.replace("`", "").strip()


def _keyed_rows(text: str, heading: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for cells in _rows(_section(text, heading)):
        for token in _tokens(cells[0]):
            out[token] = cells
    return out


def _both_ways(family: str, derived: Iterable[str], listed: Iterable[str]) -> Problems:
    have, rows = set(derived), set(listed)
    unlisted = [
        f"{family}: unlisted {item!r} (the code has it; contract.md has no row)" for item in sorted(have - rows)
    ]
    stale = [f"{family}: stale row {item!r} (contract.md lists it; the code does not)" for item in sorted(rows - have)]
    return unlisted + stale


def _missing_cap(family: str, rows: Mapping[str, list[str]]) -> Problems:
    return [f"{family}: row {key!r} names no CAP" for key, cells in sorted(rows.items()) if not _CAP.search(cells[-1])]


def _inject_row(text: str, heading: str, row: str) -> str:
    """``text`` with ``row`` added as the first data row of the first table under ``heading`` (in memory)."""
    lines = text.splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith(heading))
    separator = next(index for index in range(start + 1, len(lines)) if _SEPARATOR.fullmatch(lines[index].strip()))
    return "\n".join([*lines[: separator + 1], row, *lines[separator + 1 :]]) + "\n"


# ---------------------------------------------------------------------------
# Reading the code (AST helpers)
# ---------------------------------------------------------------------------


def _sources(root: Path, package: str) -> dict[str, str]:
    base = root / package
    return {path.relative_to(root).as_posix(): path.read_text(encoding="utf-8") for path in sorted(base.rglob("*.py"))}


@functools.cache
def _kernel_sources() -> Mapping[str, str]:
    return _sources(PACKAGE_SRC, KERNEL_PACKAGE)


@functools.cache
def _django_sources() -> Mapping[str, str]:
    return _sources(DJANGO_WARDEN_SRC, DJANGO_PACKAGE)


def _string_constants(tree: ast.Module) -> dict[str, str]:
    out: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            out.update({target.id: node.value.value for target in node.targets if isinstance(target, ast.Name)})
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            out[node.target.id] = node.value.value
    return out


def _all_constants(trees: Mapping[str, ast.Module]) -> dict[str, str]:
    out: dict[str, str] = {}
    for tree in trees.values():
        out.update(_string_constants(tree))
    return out


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _parse(sources: Mapping[str, str]) -> dict[str, ast.Module]:
    return {path: ast.parse(text, filename=path) for path, text in sources.items()}


# ---------------------------------------------------------------------------
# Section 1: CLI
# ---------------------------------------------------------------------------


def _cli_derived(parser: argparse.ArgumentParser, scan: argparse.ArgumentParser) -> set[str]:
    out: set[str] = set()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            out.update(action.choices)
        elif not isinstance(action, argparse._HelpAction):
            out.update(action.option_strings)
    for action in scan._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        if action.option_strings:
            out.update(action.option_strings)
        else:
            out.add(f"<{action.dest}>")
    return out


@functools.cache
def _live_cli() -> frozenset[str]:
    return frozenset(_cli_derived(*cli._build_parser()))


def _scan_options() -> set[str]:
    return {item for item in _live_cli() if item.startswith("-")}


def _cli_problems(derived: Iterable[str], text: str) -> Problems:
    rows = _keyed_rows(text, H_CLI)
    return _both_ways("cli", derived, rows) + _missing_cap("cli", rows)


# ---------------------------------------------------------------------------
# Section 2: configuration keys
# ---------------------------------------------------------------------------


def _render_default(value: object) -> list[str]:
    """A default as the backticked tokens of its contract cell (None and an empty list have none)."""
    if value is None:
        return []
    if isinstance(value, bool):
        return ["true" if value else "false"]
    if isinstance(value, Enum):
        return [str(value.value)]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    return [str(value)]


def _keys_derived(keys: Iterable[str], scan_options: Iterable[str]) -> dict[str, tuple[list[str], list[str]]]:
    effective = config.EffectiveConfig()
    options = set(scan_options)
    out: dict[str, tuple[list[str], list[str]]] = {}
    for key in keys:
        field = key.replace("-", "_")
        default = _render_default(getattr(effective, field)) if hasattr(effective, field) else ["<no field>"]
        flag = f"--{key}"
        out[key] = (default, [flag] if flag in options else [])
    return out


def _keys_problems(derived: Mapping[str, tuple[list[str], list[str]]], text: str) -> Problems:
    rows = _keyed_rows(text, H_KEYS)
    problems = _both_ways("config key", derived, rows) + _missing_cap("config key", rows)
    for key in sorted(set(derived) & set(rows)):
        default, flag = derived[key]
        cells = rows[key]
        if _tokens(cells[1]) != default:
            problems.append(f"config key {key!r}: default row {_tokens(cells[1])} != code {default}")
        if _tokens(cells[2]) != flag:
            problems.append(f"config key {key!r}: CLI flag row {_tokens(cells[2])} != code {flag}")
    return problems


# ---------------------------------------------------------------------------
# Section 3: exit codes, status rungs, error kinds, finding-id families, the report schema
# ---------------------------------------------------------------------------


def _exit_derived() -> set[str]:
    return {str(code) for code in verdict.LATTICE.exit_codes} | {str(verdict.EXIT_SIGINT)}


def _exit_problems(derived: Iterable[str], text: str) -> Problems:
    return _both_ways("exit code", derived, _keyed_rows(text, H_EXIT))


def _rungs_derived() -> dict[str, tuple[int, int]]:
    return {
        status.value: (verdict.LATTICE.rank(status) + 1, verdict.LATTICE.exit_by_member[status])
        for status in models.Status
    }


def _rungs_problems(derived: Mapping[str, tuple[int, int]], text: str) -> Problems:
    rows = _keyed_rows(text, H_RUNGS)
    problems = _both_ways("status rung", derived, rows)
    for rung in sorted(set(derived) & set(rows)):
        listed = (_plain(rows[rung][1]), _plain(rows[rung][2]))
        expected = tuple(str(value) for value in derived[rung])
        if listed != expected:
            problems.append(f"status rung {rung!r}: row (order, exit) {listed} != code {expected}")
    return problems


def _kinds_problems(derived: Iterable[str], text: str) -> Problems:
    return _both_ways("error kind", derived, _keyed_rows(text, H_KINDS))


def _families_derived() -> set[str]:
    return {pattern.pattern.split(":", 1)[0] for pattern in models._FINDING_ID_FAMILIES}


def _families_problems(derived: Iterable[str], text: str) -> Problems:
    return _both_ways("finding-id family", derived, _keyed_rows(text, H_FAMILIES))


def _schema_derived() -> tuple[str, str]:
    schema = json.loads(REPORT_SCHEMA.read_text(encoding="utf-8"))
    return str(schema["$id"]), report.REPORT_SCHEMA_VERSION


def _schema_problems(derived: tuple[str, str], text: str) -> Problems:
    listed = {tuple(_tokens(cells[0]) + _tokens(cells[1])[:1]) for cells in _rows(_section(text, H_SCHEMA))}
    return _both_ways("report schema ($id, version)", [str(derived)], [str(item) for item in listed])


# ---------------------------------------------------------------------------
# Section 4: feature flags
# ---------------------------------------------------------------------------


def _flags_derived(sources: Mapping[str, str]) -> dict[str, set[str]]:
    """Each ``pyforge.warden.*`` flag key the code defines or reads, with the modules that read it."""
    trees = _parse(sources)
    by_name: dict[str, str] = {}
    flags: dict[str, set[str]] = {}
    for tree in trees.values():
        for name, value in _string_constants(tree).items():
            if value.startswith(_FLAG_PREFIX):
                by_name[name] = value
                flags.setdefault(value, set())
    for path, tree in trees.items():
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and _call_name(node) in _FLAG_READERS):
                continue
            for arg in [*node.args, *(keyword.value for keyword in node.keywords)]:
                if isinstance(arg, ast.Name) and arg.id in by_name:
                    flags[by_name[arg.id]].add(path)
                elif (
                    isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.startswith(_FLAG_PREFIX)
                ):
                    flags.setdefault(arg.value, set()).add(path)
    return flags


def _live_flag_sources() -> dict[str, str]:
    return {**_kernel_sources(), **_django_sources()}


def _flag_tree() -> dict[str, dict]:
    data = json.loads(FLAGS_JSON.read_text(encoding="utf-8"))
    return dict(data.get("flags", data))


def _flag_overlays() -> dict[str, dict[str, str]]:
    return json.loads(FLAG_OVERLAYS_JSON.read_text(encoding="utf-8"))


def _flag_problems(
    code: Mapping[str, set[str]],
    tree: Mapping[str, Mapping],
    overlays: Mapping[str, Mapping[str, str]],
    text: str,
) -> Problems:
    rows = _keyed_rows(text, H_FLAGS)
    tree_keys = {key for key in tree if key.startswith(_FLAG_PREFIX)}
    problems = _both_ways("feature flag (code vs contract.md)", code, rows)
    problems += _both_ways("feature flag (code vs flags.json)", code, tree_keys)
    for environment in ENVIRONMENTS:
        orphans = {key for key in overlays.get(environment, {}) if key.startswith(_FLAG_PREFIX)} - tree_keys
        problems += [
            f"feature flag: flag-overlays.json {environment} names {key!r}, absent from flags.json"
            for key in sorted(orphans)
        ]
    for key, cells in sorted(rows.items()):
        if key in tree:
            default = str(tree[key]["defaultVariant"])
            expected = [default, *(str(overlays.get(env, {}).get(key, default)) for env in ENVIRONMENTS)]
            listed = [_plain(cell) for cell in cells[1:5]]
            if listed != expected:
                problems.append(
                    f"feature flag {key!r}: row (flags.json, {', '.join(ENVIRONMENTS)}) {listed} != {expected}"
                )
        if key in code and set(_tokens(cells[5])) != code[key]:
            problems.append(f"feature flag {key!r}: reader row {sorted(_tokens(cells[5]))} != code {sorted(code[key])}")
        if not _plain(cells[6]):
            problems.append(f"feature flag {key!r}: no flag-off behaviour")
    return problems


def _live_flag_problems(text: str) -> Problems:
    return _flag_problems(_flags_derived(_live_flag_sources()), _flag_tree(), _flag_overlays(), text)


# ---------------------------------------------------------------------------
# Section 5: environment variables
# ---------------------------------------------------------------------------


def _is_env_mapping(node: ast.AST) -> bool:
    if isinstance(node, ast.Attribute):
        return node.attr == "environ" and isinstance(node.value, ast.Name) and node.value.id == "os"
    return isinstance(node, ast.Name) and node.id in _ENV_MAPPINGS


def _env_derived(sources: Mapping[str, str], unit: str, set_role: str) -> dict[EnvKey, set[str]]:
    """``(variable, unit, role) -> modules`` under the module docstring's rules."""
    trees = _parse(sources)
    constants = _all_constants(trees)
    out: dict[EnvKey, set[str]] = {}

    def names(node: ast.AST | None) -> list[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
        elif isinstance(node, ast.Name) and node.id in constants:
            value = constants[node.id]
        else:
            return []
        return [value] if _ENV_KEY.match(value) else []

    def add(nodes: Iterable[ast.AST | None], role: str, path: str) -> None:
        for node in nodes:
            for variable in names(node):
                out.setdefault((variable, unit, role), set()).add(path)

    for path, tree in trees.items():
        for statement in tree.body:
            if not isinstance(statement, ast.Assign):
                continue
            for target in statement.targets:
                if not isinstance(target, ast.Name):
                    continue
                if _ENV_CONSTANT.search(target.id):
                    add([statement.value], READ, path)
                elif _SETTING_CONSTANT.search(target.id):
                    add([statement.value], SETTING, path)
                elif _PASS_THROUGH_CONSTANT.search(target.id) and isinstance(statement.value, (ast.Tuple, ast.List)):
                    add(statement.value.elts, PASS_THROUGH, path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and _is_env_mapping(node.value):
                add([node.slice], set_role if isinstance(node.ctx, ast.Store) else READ, path)
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute) and _is_env_mapping(func.value) and node.args:
                if func.attr in _READ_METHODS:
                    add(node.args[:1], READ, path)
                elif func.attr == "update":
                    add([key for arg in node.args if isinstance(arg, ast.Dict) for key in arg.keys], set_role, path)
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "getenv"
                and isinstance(func.value, ast.Name)
                and func.value.id == "os"
            ):
                add(node.args[:1], READ, path)
            if (
                isinstance(func, ast.Name)
                and func.id == "getattr"
                and len(node.args) >= 2
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "settings"
            ):
                add(node.args[1:2], SETTING, path)
            for keyword in node.keywords:
                if keyword.arg in _SET_KEYWORDS and isinstance(keyword.value, ast.Dict):
                    add(keyword.value.keys, set_role, path)
    return out


def _kernel_env(sources: Mapping[str, str] | None = None) -> dict[EnvKey, set[str]]:
    return _env_derived(_kernel_sources() if sources is None else sources, KERNEL, SET_FOR_ENGINE)


def _django_env(sources: Mapping[str, str] | None = None) -> dict[EnvKey, set[str]]:
    return _env_derived(_django_sources() if sources is None else sources, DJANGO, SET)


def _role(derived: Mapping[EnvKey, set[str]], role: str) -> set[str]:
    return {variable for variable, _unit, row_role in derived if row_role == role}


def _env_problems(derived: Mapping[EnvKey, set[str]], text: str) -> Problems:
    rows: dict[EnvKey, list[str]] = {}
    for cells in _rows(_section(text, H_ENV)):
        for variable in _tokens(cells[0]):
            rows[(variable, _plain(cells[1]), _plain(cells[2]))] = cells
    problems = _both_ways("environment variable (variable, unit, role)", map(str, derived), map(str, rows))
    for key in sorted(set(derived) & set(rows)):
        where = set(_tokens(rows[key][3]))
        if where != derived[key]:
            problems.append(f"environment variable {key}: where row {sorted(where)} != code {sorted(derived[key])}")
    problems += _missing_cap("environment variable", {str(key): cells for key, cells in rows.items()})
    return problems


def _live_env() -> dict[EnvKey, set[str]]:
    return {**_kernel_env(), **_django_env()}


# ---------------------------------------------------------------------------
# Sections 6 and 7: MCP tools and management commands
# ---------------------------------------------------------------------------


def _is_server_tool(decorator: ast.expr) -> bool:
    return (
        isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Attribute)
        and decorator.func.attr == "tool"
        and isinstance(decorator.func.value, ast.Name)
        and decorator.func.value.id == "server"
    )


def _mcp_derived(source: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(map(_is_server_tool, node.decorator_list)):
            out[node.name] = [arg.arg for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]]
    return out


def _mcp_problems(derived: Mapping[str, list[str]], text: str) -> Problems:
    rows = _keyed_rows(text, H_MCP)
    problems = _both_ways("MCP tool", derived, rows) + _missing_cap("MCP tool", rows)
    for tool in sorted(set(derived) & set(rows)):
        if _tokens(rows[tool][1]) != derived[tool]:
            problems.append(f"MCP tool {tool!r}: arguments row {_tokens(rows[tool][1])} != code {derived[tool]}")
    return problems


def _command_sources() -> dict[str, str]:
    return {
        Path(path).stem: text
        for path, text in _django_sources().items()
        if path.startswith(COMMANDS_DIR) and Path(path).name != "__init__.py"
    }


def _commands_derived(
    commands: Mapping[str, str], constants: Mapping[str, str]
) -> dict[str, tuple[list[str], list[str]]]:
    out: dict[str, tuple[list[str], list[str]]] = {}
    for name, text in commands.items():
        calls = sorted(
            (node for node in ast.walk(ast.parse(text)) if isinstance(node, ast.Call)),
            key=lambda node: (node.lineno, node.col_offset),
        )
        arguments = [
            str(call.args[0].value)
            for call in calls
            if _call_name(call) == "add_argument" and call.args and isinstance(call.args[0], ast.Constant)
        ]
        flags = [
            constants.get(arg.id, arg.id)
            for call in calls
            if _call_name(call) == "require"
            for arg in call.args[:1]
            if isinstance(arg, ast.Name)
        ]
        out[name] = (arguments, flags)
    return out


def _live_commands() -> dict[str, tuple[list[str], list[str]]]:
    return _commands_derived(_command_sources(), _all_constants(_parse(_django_sources())))


def _commands_problems(derived: Mapping[str, tuple[list[str], list[str]]], text: str) -> Problems:
    rows = _keyed_rows(text, H_COMMANDS)
    problems = _both_ways("management command", derived, rows) + _missing_cap("management command", rows)
    for command in sorted(set(derived) & set(rows)):
        arguments, flags = derived[command]
        if _tokens(rows[command][1]) != arguments:
            problems.append(f"management command {command!r}: arguments row {_tokens(rows[command][1])} != {arguments}")
        if _tokens(rows[command][2]) != flags:
            problems.append(f"management command {command!r}: flag row {_tokens(rows[command][2])} != {flags}")
    return problems


# ---------------------------------------------------------------------------
# The live checks
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def contract_text() -> str:
    assert CONTRACT.is_file(), f"{CONTRACT} is missing: warden's public contract is one companion (CAP-28)"
    return CONTRACT.read_text(encoding="utf-8")


def test_derivations_are_not_blind() -> None:
    """Each inventory derives something, so a green below is never a scan that found nothing."""
    assert {"scan", "<path>", "--version", "--format", "--doctor"} <= _live_cli()
    assert len(_scan_options()) >= 24
    assert len(config._RECOGNIZED_KEYS) >= 13
    assert len(_flags_derived(_live_flag_sources())) >= 9
    assert len(_role(_django_env(), READ)) >= 3
    assert _role(_django_env(), PASS_THROUGH) and _role(_django_env(), SETTING) and _role(_django_env(), SET)
    assert len(_mcp_derived(_django_sources()[MCP_MODULE])) >= 2
    assert len(_live_commands()) >= 4
    assert all(flags for _arguments, flags in _live_commands().values())


def test_cli_matches_contract(contract_text: str) -> None:
    assert _cli_problems(_live_cli(), contract_text) == []


def test_config_keys_match_contract(contract_text: str) -> None:
    assert _keys_problems(_keys_derived(config._RECOGNIZED_KEYS, _scan_options()), contract_text) == []


def test_fail_on_kev_and_the_estate_repos_defaults(contract_text: str) -> None:
    rows = _keyed_rows(contract_text, H_KEYS)
    assert _tokens(rows["fail-on-kev"][1]) == ["true"]
    assert _tokens(rows["fix-pr-estate-repos"][1]) == ["rxm7706/local-recipes", "rxm7706/python-foundry"]


def test_exit_codes_match_contract(contract_text: str) -> None:
    assert _exit_derived() == {"0", "1", "2", "130"}
    assert _exit_problems(_exit_derived(), contract_text) == []


def test_status_rungs_match_contract(contract_text: str) -> None:
    assert _rungs_problems(_rungs_derived(), contract_text) == []


def test_error_kinds_match_contract(contract_text: str) -> None:
    assert _kinds_problems({kind.value for kind in models.ErrorKind}, contract_text) == []


def test_finding_id_families_match_contract(contract_text: str) -> None:
    assert _families_problems(_families_derived(), contract_text) == []


def test_report_schema_is_frozen_at_1_1_0(contract_text: str) -> None:
    schema_id, version = _schema_derived()
    assert schema_id == "urn:local-recipes:pyforge-warden:report-schema"
    assert version == SCHEMA_VERSION_FROZEN
    assert _schema_problems((schema_id, version), contract_text) == []


def test_flags_match_code_tree_and_overlays(contract_text: str) -> None:
    assert _live_flag_problems(contract_text) == []


def test_kernel_env_reads_are_exactly_the_seven() -> None:
    assert _role(_kernel_env(), READ) == KERNEL_READS


def test_kernel_env_sets_are_exactly_the_four() -> None:
    derived = _kernel_env()
    assert _role(derived, SET_FOR_ENGINE) == KERNEL_SETS_FOR_ENGINE
    assert _role(derived, PASS_THROUGH) == set() and _role(derived, SETTING) == set()


def test_environment_variables_match_contract(contract_text: str) -> None:
    assert _env_problems(_live_env(), contract_text) == []


def test_mcp_tools_match_contract(contract_text: str) -> None:
    assert _mcp_problems(_mcp_derived(_django_sources()[MCP_MODULE]), contract_text) == []


def test_management_commands_match_contract(contract_text: str) -> None:
    assert _commands_problems(_live_commands(), contract_text) == []


# ---------------------------------------------------------------------------
# The derivation sees what it should, and nothing else
# ---------------------------------------------------------------------------

_SYNTHETIC_GET = "def resolve(source):\n    return source.get('NEW_VAR')\n"


def test_kernel_env_derivation_catches_a_synthetic_source_get(contract_text: str) -> None:
    alone = _kernel_env({"pyforge/warden/synthetic.py": _SYNTHETIC_GET})
    assert ("NEW_VAR", KERNEL, READ) in alone
    sources = {**_kernel_sources(), "pyforge/warden/synthetic.py": _SYNTHETIC_GET}
    problems = _env_problems({**_kernel_env(sources), **_django_env()}, contract_text)
    assert any("unlisted" in problem and "NEW_VAR" in problem for problem in problems), problems


def test_kernel_env_ignores_dict_literals_outside_env_arguments() -> None:
    source = (
        "import os, subprocess\n"
        "CODES = {'DEP001': 'missing', 'MIT': 'licence'}\n"
        "def run(env):\n"
        "    env['SYNTHETIC_STORE'] = '1'\n"
        "    subprocess.run(['x'], env={'SYNTHETIC_SET': '1'})\n"
        "    lookup = {'SYNTHETIC_LITERAL': 1}\n"
        "    return os.environ['SYNTHETIC_LOAD'], CODES.get('DEP001'), lookup\n"
    )
    derived = _kernel_env({"pyforge/warden/synthetic.py": source})
    assert _role(derived, READ) == {"SYNTHETIC_LOAD"}
    assert _role(derived, SET_FOR_ENGINE) == {"SYNTHETIC_STORE", "SYNTHETIC_SET"}


# ---------------------------------------------------------------------------
# Synthetic drift, both directions: each inventory names an unlisted item and a stale row
# ---------------------------------------------------------------------------


def _cli_with_synthetic_option() -> set[str]:
    parser, scan = cli._build_parser()
    scan.add_argument("--synthetic-option", action="store_true")
    return _cli_derived(parser, scan)


def _mcp_with_synthetic_tool() -> dict[str, list[str]]:
    source = _django_sources()[MCP_MODULE] + "\n\n@server.tool()\ndef synthetic_tool(target):\n    return target\n"
    return _mcp_derived(source)


def _commands_with_synthetic_command() -> dict[str, tuple[list[str], list[str]]]:
    synthetic = "from pyforge.core.flags import require\n\ndef handle():\n    require(FLEET_SCAN_FLAG)\n"
    commands = {**_command_sources(), "warden_fleet_synthetic": synthetic}
    return _commands_derived(commands, _all_constants(_parse(_django_sources())))


def _flag_source_with_synthetic_key() -> dict[str, str]:
    return {**_live_flag_sources(), "pyforge/warden/synthetic.py": 'SYNTHETIC_FLAG = "pyforge.warden.synthetic"\n'}


Case = tuple[Callable[[str], Problems], str]

UNLISTED: dict[str, Case] = {
    "cli": (lambda text: _cli_problems(_cli_with_synthetic_option(), text), "--synthetic-option"),
    "config_key": (
        lambda text: _keys_problems(_keys_derived({*config._RECOGNIZED_KEYS, "synthetic-key"}, _scan_options()), text),
        "synthetic-key",
    ),
    "exit_code": (lambda text: _exit_problems(_exit_derived() | {"3"}, text), "'3'"),
    "status_rung": (
        lambda text: _rungs_problems({**_rungs_derived(), "synthetic-rung": (8, 0)}, text),
        "synthetic-rung",
    ),
    "error_kind": (
        lambda text: _kinds_problems({kind.value for kind in models.ErrorKind} | {"synthetic-kind"}, text),
        "synthetic-kind",
    ),
    "finding_family": (lambda text: _families_problems(_families_derived() | {"synthetic"}, text), "'synthetic'"),
    "report_schema": (lambda text: _schema_problems(("urn:synthetic", "9.9.9"), text), "urn:synthetic"),
    "feature_flag": (
        lambda text: _flag_problems(
            _flags_derived(_flag_source_with_synthetic_key()), _flag_tree(), _flag_overlays(), text
        ),
        "pyforge.warden.synthetic",
    ),
    "kernel_env": (
        lambda text: _env_problems(
            {**_kernel_env({**_kernel_sources(), "pyforge/warden/synthetic.py": _SYNTHETIC_GET}), **_django_env()}, text
        ),
        "NEW_VAR",
    ),
    "django_env": (
        lambda text: _env_problems(
            {
                **_kernel_env(),
                **_django_env(
                    {
                        **_django_sources(),
                        "django_warden_fabric/synthetic.py": "import os\nX = os.environ.get('WARDEN_SYNTHETIC')\n",
                    }
                ),
            },
            text,
        ),
        "WARDEN_SYNTHETIC",
    ),
    "mcp_tool": (lambda text: _mcp_problems(_mcp_with_synthetic_tool(), text), "synthetic_tool"),
    "management_command": (
        lambda text: _commands_problems(_commands_with_synthetic_command(), text),
        "warden_fleet_synthetic",
    ),
}

STALE_ROWS: dict[str, Case] = {
    "cli": (
        lambda text: _cli_problems(_live_cli(), _inject_row(text, H_CLI, "| `--synthetic-option` | switch | CAP-1 |")),
        "--synthetic-option",
    ),
    "config_key": (
        lambda text: _keys_problems(
            _keys_derived(config._RECOGNIZED_KEYS, _scan_options()),
            _inject_row(text, H_KEYS, "| `synthetic-key` | `x` | none | CAP-5 |"),
        ),
        "synthetic-key",
    ),
    "exit_code": (
        lambda text: _exit_problems(_exit_derived(), _inject_row(text, H_EXIT, "| `3` | synthetic |")),
        "'3'",
    ),
    "status_rung": (
        lambda text: _rungs_problems(_rungs_derived(), _inject_row(text, H_RUNGS, "| `synthetic-rung` | 8 | 0 |")),
        "synthetic-rung",
    ),
    "error_kind": (
        lambda text: _kinds_problems(
            {kind.value for kind in models.ErrorKind}, _inject_row(text, H_KINDS, "| `synthetic-kind` | nobody |")
        ),
        "synthetic-kind",
    ),
    "finding_family": (
        lambda text: _families_problems(
            _families_derived(), _inject_row(text, H_FAMILIES, "| `synthetic` | `synthetic:<x>` |")
        ),
        "'synthetic'",
    ),
    "report_schema": (
        lambda text: _schema_problems(
            _schema_derived(), _inject_row(text, H_SCHEMA, "| `urn:synthetic` | `9.9.9` | none |")
        ),
        "urn:synthetic",
    ),
    "feature_flag": (
        lambda text: _live_flag_problems(
            _inject_row(
                text,
                H_FLAGS,
                "| `pyforge.warden.synthetic` | off | on | on | off | `pyforge/warden/cli.py` | nothing |",
            )
        ),
        "pyforge.warden.synthetic",
    ),
    "flag_tree": (
        lambda text: _flag_problems(
            _flags_derived(_live_flag_sources()),
            {**_flag_tree(), "pyforge.warden.synthetic_tree": {"defaultVariant": "off"}},
            _flag_overlays(),
            text,
        ),
        "pyforge.warden.synthetic_tree",
    ),
    "kernel_env": (
        lambda text: _env_problems(
            _live_env(),
            _inject_row(text, H_ENV, "| `SYNTHETIC_VAR` | kernel | read | `pyforge/warden/cli.py` | CAP-11 |"),
        ),
        "SYNTHETIC_VAR",
    ),
    "django_env": (
        lambda text: _env_problems(
            _live_env(),
            _inject_row(
                text,
                H_ENV,
                "| `SYNTHETIC_SETTING` | django-warden | setting | `django_warden_fabric/tasks.py` | CAP-29 |",
            ),
        ),
        "SYNTHETIC_SETTING",
    ),
    "mcp_tool": (
        lambda text: _mcp_problems(
            _mcp_derived(_django_sources()[MCP_MODULE]),
            _inject_row(text, H_MCP, "| `synthetic_tool` | `target` | nothing | CAP-4 |"),
        ),
        "synthetic_tool",
    ),
    "management_command": (
        lambda text: _commands_problems(
            _live_commands(),
            _inject_row(
                text, H_COMMANDS, "| `warden_fleet_synthetic` | none | `pyforge.warden.fleet_scan` | nothing | CAP-29 |"
            ),
        ),
        "warden_fleet_synthetic",
    ),
}


@pytest.mark.parametrize("inventory", sorted(UNLISTED))
def test_unlisted_item_is_caught(inventory: str, contract_text: str) -> None:
    run, item = UNLISTED[inventory]
    problems = run(contract_text)
    assert any("unlisted" in problem and item in problem for problem in problems), problems


@pytest.mark.parametrize("inventory", sorted(STALE_ROWS))
def test_stale_row_is_caught(inventory: str, contract_text: str) -> None:
    run, item = STALE_ROWS[inventory]
    problems = run(contract_text)
    assert any("stale row" in problem and item in problem for problem in problems), problems


def test_flag_row_value_drift_is_caught(contract_text: str) -> None:
    overlays = {env: dict(values) for env, values in _flag_overlays().items()}
    overlays["production"]["pyforge.warden.fleet_scan"] = "on"
    problems = _flag_problems(_flags_derived(_live_flag_sources()), _flag_tree(), overlays, contract_text)
    assert any("pyforge.warden.fleet_scan" in problem and "row (flags.json" in problem for problem in problems), (
        problems
    )


def test_flag_reader_drift_is_caught(contract_text: str) -> None:
    code = {key: set(readers) for key, readers in _flags_derived(_live_flag_sources()).items()}
    code["pyforge.warden.sast_opengrep"].add("pyforge/warden/synthetic.py")
    problems = _flag_problems(code, _flag_tree(), _flag_overlays(), contract_text)
    assert any("pyforge.warden.sast_opengrep" in problem and "reader row" in problem for problem in problems), problems
