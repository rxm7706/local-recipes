"""Story 122.2 (spec-pyforge-steward:CAP-179, FR-53): steward's public contract is one companion, and this holds it.

The contract is ``spec-pyforge-steward/contract.md`` beside ``SPEC.md``: hand-written tables, one per family, each
row naming the capability that carries it (decision D1 of 2026-11-10: no generator). This module derives the code
side and fails, naming the item and its family, for each item the code has and the contract lacks:

* **verb path** and **flag**: the argparse tree of ``pyforge.steward.cli.build_parser()``; every verb path that is a
  leaf or takes arguments of its own needs a row, and that row lists exactly the path's option strings and
  positionals (``<dest>``);
* **flag key**: string literals of the form ``pyforge.<station>.<name>`` in steward's source that are not a module
  path (a steward module or package on disk, or one of the other-station modules named in
  ``CROSS_STATION_MODULE_LITERALS``: another station's tree is never read), and every key of the flag tree
  ``src/platform/config/flags.json`` that steward owns (``pyforge.steward.*``, or ``metadata.owner`` ``steward``);
* **environment variable**: an AST scan of steward's source for ``os.environ`` / ``os.getenv`` reads, and reads
  through a local name bound to an expression over ``os.environ``, each name a literal, a module constant or a
  steward module's constant (a name built at run time is out of an AST scan's reach, and contract.md says so);
* **exit code**: every module-level ``EXIT_*`` constant in steward's source, by module and value;
* **MCP name**: the ``*_TOOL`` constants of django-steward's ``mcp_asgi.py``, and the ``STEWARD_DUTIES`` keys and the
  ``StationVerb("steward", ...)`` row of django-pyforge's ``station_cli.py``, both read by AST, never imported;

and the other way, it fails when ``contract.md`` or ``SPEC.md`` names a ``steward`` verb path in a code span that is
neither in the parser nor in the contract's *Retired verbs* table, or when a retired verb is in the parser again. The
``fires`` tests plant one extra item per family and prove the checker names it.

The contract is read by its ``##`` headings and the backticked tokens of its table rows (the columns the family
names); prose is not read. The module reads the Spec folder, django-steward, django-pyforge and the flag tree, so it
is a live-tree test; the repository root is found inside a function, never at import.
"""

from __future__ import annotations

import argparse
import ast
import functools
import json
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from pyforge.steward.cli import build_parser

pytestmark = pytest.mark.live_tree

PROGRAM = "steward"
STEWARD_SPEC_DIR = "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward"
FLAG_TREE = "src/platform/config/flags.json"
STEWARD_MCP_ASGI = "src/shared/packages/django-steward/src/django_steward_portal/mcp_asgi.py"
STATION_CLI = "src/shared/packages/django-pyforge/src/django_pyforge/station_cli.py"
STATION_PACKAGES = "src/shared/packages"

# The families, as a finding names them.
VERB_PATH = "verb path"
FLAG = "flag"
FLAG_KEY = "flag key"
ENV_VAR = "environment variable"
EXIT_CODE = "exit code"
MCP_NAME = "MCP name"
SPEC_VERB = "named verb path"

# The contract's headings. The test reads table rows under these and nothing else.
SECTION_VERBS = "CLI verbs and flags"
SECTION_RETIRED = "Retired verbs"
SECTION_MCP = "MCP face"
SECTION_FLAG_KEYS = "Feature-flag keys"
SECTION_ENV = "Environment variables"
SECTION_EXIT = "Exit codes"
SECTION_ENTRY = "Entry points"
#: Every heading whose table rows each name the capability that carries them.
CAPABILITY_SECTIONS: tuple[str, ...] = (
    SECTION_VERBS,
    SECTION_RETIRED,
    SECTION_MCP,
    SECTION_FLAG_KEYS,
    SECTION_ENV,
    SECTION_EXIT,
    SECTION_ENTRY,
    "Python names other packages import",
    "What steward needs from the tree",
    "Estate-bound constants",
)

_HEADING = re.compile(r"^## (.+?)\s*$")
_TICK = re.compile(r"`([^`]+)`")
_SEPARATOR_CELL = re.compile(r"^:?-+:?$")
_FLAG_KEY_SHAPE = re.compile(r"pyforge\.([a-z][a-z0-9_]*)\.([a-z][a-z0-9_]*)")
_EXIT_NAME = re.compile(r"EXIT_[A-Z0-9_]+")
#: A code span may wrap a line (SPEC.md wraps them at 120 columns); backticks pair left to right.
_CODE_SPAN = re.compile(r"`([^`]+)`")
_STEWARD_IN_SPAN = re.compile(r"(?:^|(?<=\s))steward(?=\s|$)")
_VERB_TOKEN = re.compile(r"[a-z][a-z0-9-]*(?:[|/][a-z][a-z0-9-]*)*")
_CAPABILITY = re.compile(r"(?:(spec-[a-z0-9-]+):)?CAP-(\d+)")
_SPEC_CAPABILITY = re.compile(r"^- \*\*CAP-(\d+) —", re.MULTILINE)
_ENVIRON_METHODS = frozenset({"get", "setdefault", "pop"})
#: Other stations' modules that steward's source names as literals of the flag-key shape (``estate_reconcile.py``
#: runs them with ``python -m``). The scan never reads another station's tree (steward's live job does not fire on
#: one), so a new literal in another station's namespace is reported as a flag key until it is added here.
CROSS_STATION_MODULE_LITERALS: frozenset[str] = frozenset({"pyforge.doctor.sources", "pyforge.scribe.cli"})
#: The contract paragraph that names each flag-key literal the scan drops for naming a module.
MODULE_COLLISION_MARKER = "dropped from the flag-key scan"


# --------------------------------------------------------------------------- where things are


@functools.cache
def _repo_root() -> Path:
    """The checkout this test reads, resolved inside a function and never at import (the live-tree split rule)."""
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pixi.toml").is_file() and (candidate / STATION_PACKAGES).is_dir():
            return candidate
    raise AssertionError("could not locate the repository root (pixi.toml beside src/shared/packages)")


def _steward_source_dir() -> Path:
    """The imported ``pyforge.steward`` package's directory: the source this test holds to the contract."""
    import pyforge.steward

    return Path(pyforge.steward.__file__).resolve().parent


def _contract_path() -> Path:
    return _repo_root() / STEWARD_SPEC_DIR / "contract.md"


def _spec_path() -> Path:
    return _repo_root() / STEWARD_SPEC_DIR / "SPEC.md"


# --------------------------------------------------------------------------- the code side


@dataclass(frozen=True)
class Node:
    """One verb path of the parser: its own option strings and positionals, and the verbs under it."""

    params: frozenset[str]
    children: frozenset[str]

    @property
    def needs_row(self) -> bool:
        """A leaf, or a group that takes arguments of its own, is a row of the contract."""
        return not self.children or bool(self.params)


def parser_tree(parser: argparse.ArgumentParser) -> dict[str, Node]:
    """Every verb path (``""`` is the program itself) mapped to its node."""
    tree: dict[str, Node] = {}

    def walk(current: argparse.ArgumentParser, path: str) -> None:
        params: set[str] = set()
        children: dict[str, argparse.ArgumentParser] = {}
        for action in current._actions:
            if isinstance(action, argparse._SubParsersAction):
                children.update(action.choices)
            elif isinstance(action, argparse._HelpAction):
                continue
            elif action.option_strings:
                params.update(action.option_strings)
            else:
                params.add(f"<{action.dest}>")
        tree[path] = Node(frozenset(params), frozenset(children))
        for name, child in children.items():
            walk(child, f"{path} {name}".strip())

    walk(parser, "")
    return tree


def _modules(package_dir: Path) -> list[Path]:
    return sorted(path for path in package_dir.rglob("*.py") if "__pycache__" not in path.parts)


def _module_name(path: Path, package_dir: Path) -> str:
    """``estate.py`` -> ``estate``; ``dashboard/audit.py`` -> ``dashboard.audit``."""
    return ".".join(path.relative_to(package_dir).with_suffix("").parts)


def _assignments(statement: ast.stmt) -> Iterator[tuple[str, ast.expr]]:
    """``(name, value)`` for each name a module-level assignment binds, tuple unpacking element by element."""
    if isinstance(statement, ast.Assign):
        targets, value = statement.targets, statement.value
    elif isinstance(statement, ast.AnnAssign) and statement.value is not None:
        targets, value = [statement.target], statement.value
    else:
        return
    for target in targets:
        if isinstance(target, ast.Name):
            yield target.id, value
        elif isinstance(target, ast.Tuple) and isinstance(value, ast.Tuple) and len(target.elts) == len(value.elts):
            for element, element_value in zip(target.elts, value.elts, strict=True):
                if isinstance(element, ast.Name):
                    yield element.id, element_value


def _string_constants(tree: ast.Module) -> dict[str, str]:
    return {
        name: value.value
        for statement in tree.body
        for name, value in _assignments(statement)
        if isinstance(value, ast.Constant) and isinstance(value.value, str)
    }


def _is_os_environ(node: ast.AST) -> bool:
    if isinstance(node, ast.Attribute):
        return node.attr == "environ" and isinstance(node.value, ast.Name) and node.value.id == "os"
    return isinstance(node, ast.Name) and node.id == "environ"


def _environ_aliases(scope: ast.AST) -> set[str]:
    """Names a scope binds to an expression over ``os.environ`` (``env = dict(os.environ)``, ``env = os.environ if
    environ is None else environ``): a read through one of them is a read of the inherited environment."""
    aliases: set[str] = set()
    for node in ast.walk(scope):
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        if any(_is_os_environ(inner) for inner in ast.walk(value)):
            aliases.update(target.id for target in targets if isinstance(target, ast.Name))
    return aliases


def _environ_read(node: ast.AST, aliases: set[str]) -> ast.expr | None:
    """The name expression of an environment read, or None when ``node`` is not one."""

    def is_environment(receiver: ast.AST) -> bool:
        return _is_os_environ(receiver) or (isinstance(receiver, ast.Name) and receiver.id in aliases)

    if isinstance(node, ast.Call) and node.args:
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in _ENVIRON_METHODS and is_environment(func.value):
            return node.args[0]
        if isinstance(func, ast.Attribute) and func.attr == "getenv":
            return node.args[0] if isinstance(func.value, ast.Name) and func.value.id == "os" else None
        if isinstance(func, ast.Name) and func.id == "getenv":
            return node.args[0]
    if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load) and is_environment(node.value):
        return node.slice
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], (ast.In, ast.NotIn)):
        return node.left if is_environment(node.comparators[0]) else None
    return None


def _resolve_name(
    expression: ast.expr, local: Mapping[str, str], modules: Mapping[str, Mapping[str, str]]
) -> str | None:
    """A literal, a module constant, or ``<steward module>.<CONSTANT>``; None when the name is built at run time."""
    if isinstance(expression, ast.Constant) and isinstance(expression.value, str):
        return expression.value
    if isinstance(expression, ast.Name):
        return local.get(expression.id)
    if isinstance(expression, ast.Attribute) and isinstance(expression.value, ast.Name):
        return modules.get(expression.value.id, {}).get(expression.attr)
    return None


def _scopes(tree: ast.Module) -> Iterator[ast.AST]:
    """The module itself and every function in it: an alias is bound and read within one scope."""
    yield tree
    yield from (node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))


def _names_a_module(literal: str, station: str, name: str, package_dir: Path) -> bool:
    """``pyforge.<station>.<name>`` is a module or package path (``pyforge.steward.cli``), not a flag key.

    Steward's own namespace is checked against ``package_dir``; another station's only against the fixed
    ``CROSS_STATION_MODULE_LITERALS``, never against that station's tree (a read steward's live job cannot see).
    """
    if station != PROGRAM:
        return literal in CROSS_STATION_MODULE_LITERALS
    base = package_dir / name
    return base.with_suffix(".py").is_file() or base.is_dir()


@dataclass
class SourceScan:
    """What an AST scan of a steward source tree finds."""

    flag_keys: set[str] = field(default_factory=set)
    module_literals: set[str] = field(default_factory=set)  # of the key shape, dropped for naming a module
    env_vars: set[str] = field(default_factory=set)
    exit_codes: set[tuple[str, int]] = field(default_factory=set)  # ("estate.EXIT_ESTATE_REFUSAL", 3)
    unresolved_env_reads: list[str] = field(default_factory=list)  # out of reach: recorded, never a finding


def scan_source(package_dir: Path) -> SourceScan:
    """Flag keys, environment reads and ``EXIT_*`` constants of every module under ``package_dir``."""
    trees = {path: ast.parse(path.read_text(encoding="utf-8"), filename=str(path)) for path in _modules(package_dir)}
    by_path = {path: _string_constants(tree) for path, tree in trees.items()}
    # ``preflight.SCOPE_ENV`` from another module: a steward module's constants, by the name it is imported as.
    constants: dict[str, dict[str, str]] = {}
    for path, values in by_path.items():
        constants.setdefault(path.stem, values)
    scan = SourceScan()
    for path, tree in trees.items():
        module = _module_name(path, package_dir)
        local = by_path[path]
        for statement in tree.body:
            for name, value in _assignments(statement):
                if _EXIT_NAME.fullmatch(name) and isinstance(value, ast.Constant) and type(value.value) is int:
                    scan.exit_codes.add((f"{module}.{name}", value.value))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                match = _FLAG_KEY_SHAPE.fullmatch(node.value)
                if match is None:
                    continue
                if _names_a_module(node.value, match.group(1), match.group(2), package_dir):
                    scan.module_literals.add(node.value)
                else:
                    scan.flag_keys.add(node.value)
        for scope in _scopes(tree):
            aliases = _environ_aliases(scope) if not isinstance(scope, ast.Module) else set()
            nodes = ast.walk(scope) if not isinstance(scope, ast.Module) else _module_level_nodes(scope)
            for node in nodes:
                expression = _environ_read(node, aliases)
                if expression is None:
                    continue
                resolved = _resolve_name(expression, local, constants)
                if resolved is None:
                    scan.unresolved_env_reads.append(f"{module}:{getattr(node, 'lineno', '?')}")
                else:
                    scan.env_vars.add(resolved)
    return scan


def _module_level_nodes(tree: ast.Module) -> Iterator[ast.AST]:
    """Every node outside a function (a function's reads are scanned with its own aliases)."""
    stack: list[ast.AST] = list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        yield node
        stack.extend(ast.iter_child_nodes(node))


def owned_flag_keys(flag_tree: Mapping[str, object]) -> set[str]:
    """Keys of the flag tree steward owns: its namespace, and any key whose metadata names steward its owner."""
    flags = flag_tree.get("flags")
    assert isinstance(flags, dict), "the flag tree has no 'flags' object"
    owned: set[str] = set()
    for key, entry in flags.items():
        metadata = entry.get("metadata") if isinstance(entry, dict) else None
        if key.startswith(f"pyforge.{PROGRAM}.") or (isinstance(metadata, dict) and metadata.get("owner") == PROGRAM):
            owned.add(key)
    return owned


def mcp_names(mcp_asgi_source: str, station_cli_source: str) -> set[str]:
    """The steward face's tool names and targets, read by AST from the two host modules (never imported)."""
    names: set[str] = set()
    for statement in ast.parse(mcp_asgi_source).body:
        for name, value in _assignments(statement):
            if name.endswith("_TOOL") and isinstance(value, ast.Constant) and isinstance(value.value, str):
                names.add(value.value)
    station_cli = ast.parse(station_cli_source)
    for statement in station_cli.body:
        for name, value in _assignments(statement):
            if name == "STEWARD_DUTIES" and isinstance(value, ast.Dict):
                names.update(k.value for k in value.keys if isinstance(k, ast.Constant) and isinstance(k.value, str))
    for node in ast.walk(station_cli):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        args = node.args
        if called == "StationVerb" and args and isinstance(args[0], ast.Constant) and args[0].value == PROGRAM:
            names.update(a.value for a in args[1:3] if isinstance(a, ast.Constant) and isinstance(a.value, str))
    return names


@dataclass
class CodeSide:
    """Everything steward serves to a caller, read from the code."""

    tree: dict[str, Node]
    flag_keys: set[str]
    env_vars: set[str]
    exit_codes: set[tuple[str, int]]
    mcp_names: set[str]


def derive_code_side(
    parser: argparse.ArgumentParser | None = None,
    package_dir: Path | None = None,
    mcp_sources: tuple[str, str] | None = None,
) -> CodeSide:
    """The live code side; a test passes a planted parser, source tree or host module text instead."""
    root = _repo_root()
    scan = scan_source(package_dir or _steward_source_dir())
    flag_tree = json.loads((root / FLAG_TREE).read_text(encoding="utf-8"))
    if mcp_sources is None:
        mcp_sources = (
            (root / STEWARD_MCP_ASGI).read_text(encoding="utf-8"),
            (root / STATION_CLI).read_text(encoding="utf-8"),
        )
    return CodeSide(
        tree=parser_tree(parser or build_parser()),
        flag_keys=scan.flag_keys | owned_flag_keys(flag_tree),
        env_vars=scan.env_vars,
        exit_codes=scan.exit_codes,
        mcp_names=mcp_names(*mcp_sources),
    )


# --------------------------------------------------------------------------- the contract side


@dataclass
class Table:
    header: list[str]
    rows: list[list[str]]

    def column(self, name: str) -> int | None:
        return self.header.index(name) if name in self.header else None


def tables(text: str) -> dict[str, list[Table]]:
    """The tables under each ``##`` heading: header cells, then body rows as cell lists."""
    found: dict[str, list[Table]] = {}
    heading: str | None = None
    current: Table | None = None
    for line in text.splitlines():
        match = _HEADING.match(line)
        if match is not None:
            heading, current = match.group(1), None
            found.setdefault(heading, [])
            continue
        if heading is None or not line.startswith("|"):
            current = None
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if current is None:
            current = Table(header=cells, rows=[])
            found[heading].append(current)
        elif not all(_SEPARATOR_CELL.match(cell) for cell in cells):
            current.rows.append(cells)
    return found


def _ticks(row: list[str], index: int | None) -> list[str]:
    return _TICK.findall(row[index]) if index is not None and index < len(row) else []


def _verb_path(token: str) -> str | None:
    """``steward keys list`` -> ``keys list``; ``steward`` -> ``""``; anything else -> None."""
    if token == PROGRAM:
        return ""
    if token.startswith(f"{PROGRAM} "):
        return token[len(PROGRAM) :].strip()
    return None


@dataclass
class Contract:
    """What ``contract.md`` records, by family."""

    rows: dict[str, set[str]] = field(default_factory=dict)  # verb path -> its flags and positionals
    retired: set[str] = field(default_factory=set)
    mcp_names: set[str] = field(default_factory=set)
    flag_keys: set[str] = field(default_factory=set)
    entry_names: set[str] = field(default_factory=set)
    env_vars: set[str] = field(default_factory=set)
    exit_codes: dict[str, set[int]] = field(default_factory=dict)  # "estate.EXIT_ESTATE_REFUSAL" -> {3}


def read_contract(text: str) -> Contract:
    found = tables(text)
    contract = Contract()
    for table in found.get(SECTION_VERBS, []):
        flags, arguments = table.column("Flags"), table.column("Arguments")
        for row in table.rows:
            path = next((p for p in map(_verb_path, _ticks(row, 0)) if p is not None), None)
            if path is not None:
                params = contract.rows.setdefault(path, set())
                params.update(_ticks(row, flags))
                params.update(_ticks(row, arguments))
    for table in found.get(SECTION_RETIRED, []):
        for row in table.rows:
            contract.retired.update(p for p in map(_verb_path, _ticks(row, 0)) if p is not None)
    for table in found.get(SECTION_MCP, []):
        contract.mcp_names.update(token for row in table.rows for token in _ticks(row, 0))
    for table in found.get(SECTION_FLAG_KEYS, []):
        contract.flag_keys.update(token for row in table.rows for token in _ticks(row, 0))
    for table in found.get(SECTION_ENTRY, []):
        contract.entry_names.update(token for row in table.rows for token in _ticks(row, 0))
    for table in found.get(SECTION_ENV, []):
        contract.env_vars.update(token for row in table.rows for token in _ticks(row, 0))
    for table in found.get(SECTION_EXIT, []):
        for row in table.rows:
            codes = {int(token) for token in _ticks(row, 0) if token.isdigit()}
            for constant in _ticks(row, 1):
                contract.exit_codes.setdefault(constant, set()).update(codes)
    return contract


def named_verb_paths(text: str, tree: Mapping[str, Node]) -> set[str]:
    """Every ``steward`` verb path a document names in a code span (``steward ci pause|resume <surface>`` names two).

    A word after a group descends into it (``|`` and ``/`` separate alternatives); the walk stops at a leaf (what
    follows is an argument), at a flag or placeholder, and at a word the group lacks, which is then the path named.
    """
    named: set[str] = set()
    for span in _CODE_SPAN.findall(text):
        for start in _STEWARD_IN_SPAN.finditer(span):
            tokens = span[start.end() :].split()

            def walk(path: str, index: int, tokens: list[str] = tokens) -> None:
                node = tree.get(path)
                if node is None or not node.children or index >= len(tokens):
                    named.add(path)
                    return
                if not _VERB_TOKEN.fullmatch(tokens[index]):
                    named.add(path)
                    return
                for word in re.split(r"[|/]", tokens[index]):
                    walk(f"{path} {word}".strip(), index + 1)

            walk("", 0)
    return named


# --------------------------------------------------------------------------- the check


def _verb(path: str) -> str:
    return f"`{PROGRAM} {path}`" if path else f"`{PROGRAM}`"


def check(code: CodeSide, contract: Contract, documents: Mapping[str, str]) -> list[str]:
    """One finding per item the code has and the contract lacks, and per verb path a document names that is neither
    live nor retired; each finding names its family and the item."""
    findings: list[str] = []

    def missing(family: str, item: str, section: str) -> None:
        findings.append(f"{family}: {item} is in the code and absent from contract.md § {section}")

    for path, node in sorted(code.tree.items()):
        if not node.needs_row:
            continue
        if path not in contract.rows:
            missing(VERB_PATH, _verb(path), SECTION_VERBS)
            continue
        recorded = contract.rows[path]
        for param in sorted(node.params - recorded):
            missing(FLAG, f"`{param}` of {_verb(path)}", SECTION_VERBS)
        for param in sorted(recorded - node.params):
            findings.append(f"{FLAG}: contract.md records `{param}` of {_verb(path)}, which the parser does not have")
    for key in sorted(code.flag_keys - contract.flag_keys - contract.entry_names):
        missing(FLAG_KEY, f"`{key}`", SECTION_FLAG_KEYS)
    for name in sorted(code.env_vars - contract.env_vars):
        missing(ENV_VAR, f"`{name}`", SECTION_ENV)
    for constant, value in sorted(code.exit_codes):
        if constant not in contract.exit_codes:
            missing(EXIT_CODE, f"`{constant}` ({value})", SECTION_EXIT)
        elif value not in contract.exit_codes[constant]:
            findings.append(
                f"{EXIT_CODE}: `{constant}` is {value} in the code and contract.md § {SECTION_EXIT} gives it "
                f"{sorted(contract.exit_codes[constant])}"
            )
    for name in sorted(code.mcp_names - contract.mcp_names):
        missing(MCP_NAME, f"`{name}`", SECTION_MCP)
    for label, text in documents.items():
        for path in sorted(named_verb_paths(text, code.tree)):
            if path not in code.tree and path not in contract.retired:
                findings.append(
                    f"{SPEC_VERB}: {label} names {_verb(path)}, which is neither in the parser nor in "
                    f"contract.md § {SECTION_RETIRED}"
                )
    for path in sorted(contract.retired & code.tree.keys()):
        findings.append(f"{SPEC_VERB}: {_verb(path)} is under contract.md § {SECTION_RETIRED} and in the parser")
    return findings


def capability_findings(text: str, spec_capabilities: set[str]) -> list[str]:
    """A row under a contract table that names no capability, or a bare ``CAP-n`` the steward Spec does not define."""
    findings: list[str] = []
    found = tables(text)
    for section in CAPABILITY_SECTIONS:
        if not found.get(section):
            findings.append(f"contract.md has no table under § {section}")
        for table in found.get(section, []):
            column = table.column("Capability")
            if column is None:
                findings.append(f"a table under § {section} has no Capability column")
                continue
            for row in table.rows:
                cell = row[column] if column < len(row) else ""
                cited = _CAPABILITY.findall(cell)
                if not cited:
                    findings.append(f"§ {section}: the row {row[0]} names no capability")
                findings += [
                    f"§ {section}: the row {row[0]} cites CAP-{number}, which SPEC.md does not define"
                    for spec, number in cited
                    if not spec and number not in spec_capabilities
                ]
    return findings


def collision_findings(text: str, dropped_keys: set[str]) -> list[str]:
    """A flag-tree key the scan drops for naming a module that contract.md's paragraph on such literals omits.

    The flag-key scan cannot tell a module path from a flag key of the same string, so contract.md names each one in
    the paragraph that says which literals are dropped; this keeps that written blind spot current.
    """
    paragraphs = [" ".join(paragraph.split()) for paragraph in re.split(r"\n\s*\n", text)]
    marked = [paragraph for paragraph in paragraphs if MODULE_COLLISION_MARKER in paragraph]
    if not marked:
        return [f"contract.md has no paragraph saying which literals are {MODULE_COLLISION_MARKER}"]
    return [
        f"{FLAG_KEY}: `{key}` names a module and is a flag-tree key, and contract.md's paragraph on literals "
        f"{MODULE_COLLISION_MARKER} does not name it"
        for key in sorted(dropped_keys)
        if not any(f"`{key}`" in paragraph for paragraph in marked)
    ]


# --------------------------------------------------------------------------- the live contract


@pytest.fixture(scope="module")
def code_side() -> CodeSide:
    return derive_code_side()


@pytest.fixture(scope="module")
def contract_text() -> str:
    path = _contract_path()
    assert path.is_file(), f"the contract companion is missing: {path.relative_to(_repo_root())}"
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def spec_text() -> str:
    return _spec_path().read_text(encoding="utf-8")


def test_the_code_side_is_derived_not_empty(code_side: CodeSide, spec_text: str) -> None:
    """A derivation that went blind would pass vacuously: each family reads what it must."""
    assert {"estate plan", "deploy nic up", "cutover flip", "preflight verify-deferred"} <= code_side.tree.keys()
    assert "--due" in code_side.tree["estate plan"].params and "<argv>" in code_side.tree["keys exec"].params
    # A literal key, a key only the host reads (flags.json) and the root key steward's metadata owns.
    assert {"pyforge.steward.estate_refresh", "pyforge.steward.start_tool_cli", "pyforge.cutover_root"} <= (
        code_side.flag_keys
    )
    # A module path and a sibling station's module are literals of the key shape and are not flag keys.
    assert not code_side.flag_keys & {"pyforge.steward.cli", "pyforge.doctor.sources"}
    # A literal read, a module-constant read and a read through a local alias of os.environ (preflight.py's scope).
    assert {"SOPS_AGE_KEY_FILE", "PYFORGE_STUDIO_ROOT", "PYFORGE_PREFLIGHT_SCOPE"} <= code_side.env_vars
    assert {("cli.EXIT_INTERNAL", 70), ("estate.EXIT_ESTATE_REFUSAL", 3), ("frames.EXIT_FAIL", 1)} <= (
        code_side.exit_codes
    )
    assert {"start_duty", "get_duty", "run_duty", "ci-status", "estate-plan", "estate-status"} <= code_side.mcp_names
    assert len(named_verb_paths(spec_text, code_side.tree)) >= 20


def test_contract_records_every_item_the_code_has(code_side: CodeSide, contract_text: str, spec_text: str) -> None:
    documents = {"contract.md": contract_text, "SPEC.md": spec_text}
    findings = check(code_side, read_contract(contract_text), documents)
    assert not findings, "contract.md and the code disagree:\n" + "\n".join(findings)


def test_every_contract_row_names_its_capability(contract_text: str, spec_text: str) -> None:
    """Each row names the capability that carries it, qualified when another Spec owns it."""
    findings = capability_findings(contract_text, set(_SPEC_CAPABILITY.findall(spec_text)))
    assert not findings, "\n".join(findings)


def test_the_contract_says_what_an_ast_scan_cannot_reach(contract_text: str) -> None:
    """Environment reads and flag keys built by concatenation are out of reach, and the contract says so."""
    prose = " ".join(contract_text.split())  # the sentence may wrap a line
    assert "built by concatenation" in prose and "out of an AST scan's reach" in prose


def test_the_contract_names_each_module_literal_that_is_also_a_flag_key(contract_text: str) -> None:
    """The scan drops a literal that names a module even when the flag tree holds the same key; the contract says
    which, so that blind spot is written down beside the concatenation one."""
    flags = json.loads((_repo_root() / FLAG_TREE).read_text(encoding="utf-8"))["flags"]
    dropped = scan_source(_steward_source_dir()).module_literals & flags.keys()
    assert dropped, "no module literal of steward's source is also a flag-tree key: re-check the collision scan"
    findings = collision_findings(contract_text, dropped)
    assert not findings, "\n".join(findings)


# --------------------------------------------------------------------------- each family fires


def _live(code: CodeSide, contract_text: str, spec_text: str) -> list[str]:
    return check(code, read_contract(contract_text), {"contract.md": contract_text, "SPEC.md": spec_text})


def _subparsers(parser: argparse.ArgumentParser, *path: str) -> argparse.ArgumentParser:
    for word in path:
        action = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
        parser = action.choices[word]
    return parser


def test_fires_on_a_planted_verb_path(code_side: CodeSide, contract_text: str, spec_text: str) -> None:
    parser = build_parser()
    keys = _subparsers(parser, "keys")
    action = next(a for a in keys._actions if isinstance(a, argparse._SubParsersAction))
    action.add_parser("planted")
    planted = CodeSide(**{**code_side.__dict__, "tree": parser_tree(parser)})
    expected = f"{VERB_PATH}: `steward keys planted` is in the code and absent from contract.md § {SECTION_VERBS}"
    assert expected not in _live(code_side, contract_text, spec_text)
    assert expected in _live(planted, contract_text, spec_text)


def test_fires_on_a_planted_flag(code_side: CodeSide, contract_text: str, spec_text: str) -> None:
    parser = build_parser()
    _subparsers(parser, "budget", "show").add_argument("--planted", action="store_true")
    planted = CodeSide(**{**code_side.__dict__, "tree": parser_tree(parser)})
    expected = (
        f"{FLAG}: `--planted` of `steward budget show` is in the code and absent from contract.md § {SECTION_VERBS}"
    )
    assert expected in _live(planted, contract_text, spec_text)


def test_fires_on_a_contract_flag_the_parser_lacks(code_side: CodeSide, contract_text: str, spec_text: str) -> None:
    planted = contract_text.replace(
        "| `steward budget show` | `--json` |", "| `steward budget show` | `--json`, `--gone` |"
    )
    assert planted != contract_text, "the budget show row moved; re-point the plant"
    findings = _live(code_side, planted, spec_text)
    assert f"{FLAG}: contract.md records `--gone` of `steward budget show`, which the parser does not have" in findings


def _plant_source(tmp_path: Path, text: str) -> Path:
    package_dir = tmp_path / "steward"
    package_dir.mkdir()
    (package_dir / "planted.py").write_text(text, encoding="utf-8")
    return package_dir


def test_fires_on_a_planted_flag_key(code_side: CodeSide, contract_text: str, spec_text: str, tmp_path: Path) -> None:
    package_dir = _plant_source(
        tmp_path, 'FLAG = "pyforge.steward.planted_switch"\nMODULE = "pyforge.steward.planted"\n'
    )
    scan = scan_source(package_dir)
    assert scan.flag_keys == {"pyforge.steward.planted_switch"}  # planted.py is a module, so its own path is no key
    assert scan.module_literals == {"pyforge.steward.planted"}
    planted = CodeSide(**{**code_side.__dict__, "flag_keys": code_side.flag_keys | scan.flag_keys})
    expected = (
        f"{FLAG_KEY}: `pyforge.steward.planted_switch` is in the code and absent from contract.md § {SECTION_FLAG_KEYS}"
    )
    assert expected in _live(planted, contract_text, spec_text)


def test_fires_on_an_unlisted_other_station_literal(
    code_side: CodeSide, contract_text: str, spec_text: str, tmp_path: Path
) -> None:
    """Another station's tree is never read: a literal in its namespace is a key unless the fixed set lists it."""
    package_dir = _plant_source(tmp_path, 'RUN = "pyforge.doctor.planted"\nLISTED = "pyforge.doctor.sources"\n')
    scan = scan_source(package_dir)
    assert scan.flag_keys == {"pyforge.doctor.planted"}
    assert scan.module_literals == {"pyforge.doctor.sources"}
    planted = CodeSide(**{**code_side.__dict__, "flag_keys": code_side.flag_keys | scan.flag_keys})
    expected = f"{FLAG_KEY}: `pyforge.doctor.planted` is in the code and absent from contract.md § {SECTION_FLAG_KEYS}"
    assert expected in _live(planted, contract_text, spec_text)


def test_fires_on_a_module_literal_the_contract_does_not_name(contract_text: str) -> None:
    planted = "pyforge.steward.planted_module_key"
    expected = (
        f"{FLAG_KEY}: `{planted}` names a module and is a flag-tree key, and contract.md's paragraph on literals "
        f"{MODULE_COLLISION_MARKER} does not name it"
    )
    assert expected in collision_findings(contract_text, {planted, "pyforge.steward.budget"})
    assert not collision_findings(contract_text, {"pyforge.steward.budget"})
    unmarked = contract_text.replace(MODULE_COLLISION_MARKER, "left out of the scan")
    assert collision_findings(unmarked, set()) == [
        f"contract.md has no paragraph saying which literals are {MODULE_COLLISION_MARKER}"
    ]


def test_fires_on_a_planted_flag_tree_key(code_side: CodeSide, contract_text: str, spec_text: str) -> None:
    tree = {"flags": {"pyforge.steward.planted_host_switch": {}, "pyforge.other": {"metadata": {"owner": "steward"}}}}
    planted = CodeSide(**{**code_side.__dict__, "flag_keys": code_side.flag_keys | owned_flag_keys(tree)})
    findings = _live(planted, contract_text, spec_text)
    for key in ("pyforge.steward.planted_host_switch", "pyforge.other"):
        assert f"{FLAG_KEY}: `{key}` is in the code and absent from contract.md § {SECTION_FLAG_KEYS}" in findings


@pytest.mark.parametrize(
    "source",
    [
        'import os\nV = os.environ.get("STEWARD_PLANTED")\n',
        'import os\nV = os.getenv("STEWARD_PLANTED", "")\n',
        'import os\nNAME = "STEWARD_PLANTED"\nV = os.environ[NAME]\n',
        'import os\nV = "STEWARD_PLANTED" in os.environ\n',
        "import os\ndef f(environ=None):\n    env = os.environ if environ is None else environ\n"
        '    return env.get("STEWARD_PLANTED")\n',
        'import os\ndef f():\n    env = dict(os.environ)\n    return env["STEWARD_PLANTED"]\n',
    ],
    ids=["environ-get", "getenv", "module-constant", "in-environ", "alias-conditional", "alias-copy"],
)
def test_fires_on_a_planted_environment_read(
    code_side: CodeSide, contract_text: str, spec_text: str, tmp_path: Path, source: str
) -> None:
    scan = scan_source(_plant_source(tmp_path, source))
    assert scan.env_vars == {"STEWARD_PLANTED"}
    planted = CodeSide(**{**code_side.__dict__, "env_vars": code_side.env_vars | scan.env_vars})
    expected = f"{ENV_VAR}: `STEWARD_PLANTED` is in the code and absent from contract.md § {SECTION_ENV}"
    assert expected in _live(planted, contract_text, spec_text)


def test_a_name_built_at_run_time_is_out_of_reach(tmp_path: Path) -> None:
    """The scan does not guess: a read whose name is computed is recorded as out of reach, never as a variable."""
    scan = scan_source(_plant_source(tmp_path, 'import os\ndef f(n):\n    return os.environ.get("STEWARD_" + n)\n'))
    assert scan.env_vars == set() and scan.unresolved_env_reads == ["planted:3"]


@pytest.mark.parametrize(
    "source",
    ["EXIT_PLANTED = 9\n", "EXIT_OK, EXIT_PLANTED = 0, 9\n", "EXIT_PLANTED: int = 9\n"],
    ids=["assign", "tuple", "annotated"],
)
def test_fires_on_a_planted_exit_code(
    code_side: CodeSide, contract_text: str, spec_text: str, tmp_path: Path, source: str
) -> None:
    scan = scan_source(_plant_source(tmp_path, source))
    assert ("planted.EXIT_PLANTED", 9) in scan.exit_codes
    planted = CodeSide(**{**code_side.__dict__, "exit_codes": code_side.exit_codes | scan.exit_codes})
    expected = f"{EXIT_CODE}: `planted.EXIT_PLANTED` (9) is in the code and absent from contract.md § {SECTION_EXIT}"
    assert expected in _live(planted, contract_text, spec_text)


def test_fires_on_an_exit_code_whose_value_moved(code_side: CodeSide, contract_text: str, spec_text: str) -> None:
    moved = {(c, 4) if c == "estate.EXIT_ESTATE_REFUSAL" else (c, v) for c, v in code_side.exit_codes}
    planted = CodeSide(**{**code_side.__dict__, "exit_codes": moved})
    findings = _live(planted, contract_text, spec_text)
    assert any(f.startswith(f"{EXIT_CODE}: `estate.EXIT_ESTATE_REFUSAL` is 4 in the code") for f in findings)


@pytest.mark.parametrize(
    ("asgi_line", "cli_line", "name"),
    [
        ('PLANTED_TOOL = "planted_duty"\n', "", "planted_duty"),
        ("", 'STEWARD_DUTIES = {"ci-status": (), "planted-target": ()}\n', "planted-target"),
        ("", 'ROWS = (StationVerb("steward", "run_planted", "start_planted"),)\n', "start_planted"),
    ],
    ids=["tool-constant", "target", "verb-row"],
)
def test_fires_on_a_planted_mcp_name(
    code_side: CodeSide, contract_text: str, spec_text: str, asgi_line: str, cli_line: str, name: str
) -> None:
    root = _repo_root()
    asgi = (root / STEWARD_MCP_ASGI).read_text(encoding="utf-8") + asgi_line
    cli = (root / STATION_CLI).read_text(encoding="utf-8") + cli_line
    planted = CodeSide(**{**code_side.__dict__, "mcp_names": mcp_names(asgi, cli)})
    expected = f"{MCP_NAME}: `{name}` is in the code and absent from contract.md § {SECTION_MCP}"
    assert expected not in _live(code_side, contract_text, spec_text)
    assert expected in _live(planted, contract_text, spec_text)


def test_fires_on_a_spec_verb_that_is_neither_live_nor_retired(
    code_side: CodeSide, contract_text: str, spec_text: str
) -> None:
    planted_spec = spec_text + "\n- `steward keys frobnicate --now` and `pyforge steward frobnicate`\n"
    findings = _live(code_side, contract_text, planted_spec)
    assert f"{SPEC_VERB}: SPEC.md names `steward keys frobnicate`, which is neither in the parser nor in " in "\n".join(
        findings
    )
    assert any("SPEC.md names `steward frobnicate`," in finding for finding in findings)


def test_fires_on_a_contract_verb_that_is_neither_live_nor_retired(
    code_side: CodeSide, contract_text: str, spec_text: str
) -> None:
    planted = contract_text + "\nProse naming `steward deploy frobnicate` is read too.\n"
    findings = _live(code_side, planted, spec_text)
    assert any(f.startswith(f"{SPEC_VERB}: contract.md names `steward deploy frobnicate`,") for f in findings)


def test_fires_on_a_retired_verb_that_is_live_again(code_side: CodeSide, contract_text: str, spec_text: str) -> None:
    parser = build_parser()
    deploy = _subparsers(parser, "deploy")
    next(a for a in deploy._actions if isinstance(a, argparse._SubParsersAction)).add_parser("dashboard")
    planted = CodeSide(**{**code_side.__dict__, "tree": parser_tree(parser)})
    findings = _live(planted, contract_text, spec_text)
    assert f"{SPEC_VERB}: `steward deploy dashboard` is under contract.md § {SECTION_RETIRED} and in the parser" in (
        findings
    )


def test_fires_on_a_row_without_a_capability(contract_text: str, spec_text: str) -> None:
    spec_capabilities = set(_SPEC_CAPABILITY.findall(spec_text))
    planted = contract_text.replace(
        "| `steward budget show` | `--json` | — | CAP-4 |", "| `steward budget show` | `--json` | — | — |"
    )
    assert planted != contract_text, "the budget show row moved; re-point the plant"
    assert "§ CLI verbs and flags: the row `steward budget show` names no capability" in capability_findings(
        planted, spec_capabilities
    )
    unknown = contract_text.replace(
        "| `steward budget show` | `--json` | — | CAP-4 |", "| `steward budget show` | `--json` | — | CAP-999 |"
    )
    assert "§ CLI verbs and flags: the row `steward budget show` cites CAP-999, which SPEC.md does not define" in (
        capability_findings(unknown, spec_capabilities)
    )


def test_named_verb_paths_reads_alternatives_and_stops_at_arguments(code_side: CodeSide) -> None:
    text = (
        "`steward ci pause|resume <surface> --reason`, `steward keys encrypt/decrypt`, `steward provision --env x`, "
        "`pixi run -e pyforge-guild pyforge steward estate plan --due`, `pyforge-steward-test`, `.steward/x`, "
        "`steward:121.5`, `steward deploy dashboard`"
    )
    assert named_verb_paths(text, code_side.tree) == {
        "ci pause",
        "ci resume",
        "keys encrypt",
        "keys decrypt",
        "provision",
        "estate plan",
        "deploy dashboard",
    }
