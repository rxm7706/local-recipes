"""Story 31.1 / spec-pyforge-scribe CAP-4 (FR-54): scribe's public contract is written down, and this holds it.

The contract is the Spec companion ``spec-pyforge-scribe/contract.md``: one table per family. This test derives the
code side and fails, naming the item and its family, for each item present in the code and absent from the contract:

* **verb path** and **flag**: the click tree of ``pyforge.scribe.cli.app`` (leaf commands, every option string);
* **MCP tool**: the ``*_TOOL`` constants of django-scribe's ``mcp_asgi.py``, read as text (never imported);
* **flag key**: string literals of the form ``pyforge.<station>.<name>`` that name no module on disk (so
  ``"pyforge.scribe.cli"`` and the hook name ``"pyforge.scribe.graph_store"`` are not flag keys);
* **environment variable**: an AST scan of ``os.environ`` / ``os.getenv`` reads, each name a literal or a module
  constant;
* **exit code**: an AST scan of ``typer.Exit(code=)`` (a bare ``typer.Exit()`` is 0).

The three AST scans cover the package source and the surface scripts ``scripts/scribe_*.py`` and
``scripts/bmad_estate_check.py``. A read or exit whose name or code is not a literal is reported too, so nothing new
hides behind a variable. The contract is read by its ``##`` headings and the backticked tokens of its table rows'
first cell (and second, for a verb's flags and an exit code); prose is not read.

It reads outside the package (the Spec folder, django-scribe, ``scripts/``), so it is a live-tree test.
"""

from __future__ import annotations

import ast
import functools
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import typer

from pyforge.scribe.cli import app

pytestmark = pytest.mark.live_tree


@functools.cache
def _repo_root() -> Path:
    """The checkout this test reads, resolved inside the tests and never at import (Story 33.1's split rule)."""
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / "src" / "shared" / "packages").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + src/shared/packages)")


def _packages() -> Path:
    return _repo_root() / "src" / "shared" / "packages"


def _contract() -> Path:
    specs = _repo_root() / "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs"
    return specs / "spec-pyforge-scribe" / "contract.md"


def _mcp_asgi() -> Path:
    return _packages() / "django-scribe" / "src" / "django_scribe_portal" / "mcp_asgi.py"


PROGRAM = "scribe"

# The six families, as the failure message names them, and the contract heading each one's table sits under.
VERB_PATH = "verb path"
FLAG = "flag"
MCP_TOOL = "MCP tool"
FLAG_KEY = "flag key"
ENV_VAR = "environment variable"
EXIT_CODE = "exit code"
SECTION = {
    VERB_PATH: "CLI verbs and flags",
    FLAG: "CLI verbs and flags",
    MCP_TOOL: "MCP tools",
    FLAG_KEY: "Feature-flag keys",
    ENV_VAR: "Environment variables",
    EXIT_CODE: "Exit codes",
}

_HEADING = re.compile(r"^## (.+?)\s*$")
_TICK = re.compile(r"`([^`]+)`")
_TOOL_CONSTANT = re.compile(r"""^[A-Z][A-Z0-9_]*_TOOL\s*(?::[^=\n]+)?=\s*["']([^"']+)["']""", re.MULTILINE)
_FLAG_KEY = re.compile(r"pyforge\.([a-z][a-z0-9_]*)\.([a-z][a-z0-9_]*)")
_ENVIRON_METHODS = frozenset({"get", "setdefault", "pop"})


@dataclass
class Surface:
    """One side of the contract: what the code serves, or what ``contract.md`` records."""

    verb_paths: set[str] = field(default_factory=set)  # "capture", "graph compile"; "" is the root group
    flags: set[tuple[str, str]] = field(default_factory=set)  # (verb path, option string)
    mcp_tools: set[str] = field(default_factory=set)
    flag_keys: set[str] = field(default_factory=set)
    env_vars: set[str] = field(default_factory=set)
    exit_codes: set[tuple[str, int]] = field(default_factory=set)  # (program, code)
    unresolved: list[str] = field(default_factory=list)  # code side only: a name or code that is not a literal


# --------------------------------------------------------------------------- the code side


def _surface_scripts() -> list[Path]:
    scripts = _repo_root() / "scripts"
    return [*sorted(scripts.glob("scribe_*.py")), scripts / "bmad_estate_check.py"]


def _scanned_files() -> list[tuple[str, Path]]:
    """(program, path) for every file the AST scans read: the package source, then the surface scripts."""
    package = [(PROGRAM, path) for path in sorted((_packages() / "pyforge-scribe" / "src").rglob("*.py"))]
    return [*package, *((f"scripts/{path.name}", path) for path in _surface_scripts())]


def _module_constants(tree: ast.Module) -> dict[str, str]:
    """Module-level ``NAME = "text"`` assignments: the constants an environment read may name."""
    constants: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target, value = node.target, node.value
        else:
            continue
        if isinstance(target, ast.Name) and isinstance(value, ast.Constant) and isinstance(value.value, str):
            constants[target.id] = value.value
    return constants


def _is_environ(node: ast.expr) -> bool:
    if isinstance(node, ast.Attribute):
        return node.attr == "environ" and isinstance(node.value, ast.Name) and node.value.id == "os"
    return isinstance(node, ast.Name) and node.id == "environ"


def _environ_read(node: ast.AST) -> ast.expr | None:
    """The name expression of an environment read, or None when ``node`` is not one."""
    if isinstance(node, ast.Call) and node.args:
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in _ENVIRON_METHODS and _is_environ(func.value):
            return node.args[0]
        if isinstance(func, ast.Attribute) and func.attr == "getenv":
            return node.args[0] if isinstance(func.value, ast.Name) and func.value.id == "os" else None
        if isinstance(func, ast.Name) and func.id == "getenv":
            return node.args[0]
    if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load) and _is_environ(node.value):
        return node.slice
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], (ast.In, ast.NotIn)):
        return node.left if _is_environ(node.comparators[0]) else None
    return None


def _is_typer_exit(func: ast.expr) -> bool:
    if isinstance(func, ast.Attribute):
        return func.attr == "Exit" and isinstance(func.value, ast.Name) and func.value.id == "typer"
    return isinstance(func, ast.Name) and func.id == "Exit"


def _names_a_module(station: str, name: str) -> bool:
    """``pyforge.<station>.<name>`` is a module or package path, not a flag key."""
    base = _packages() / f"pyforge-{station.replace('_', '-')}" / "src" / "pyforge" / station / name
    return base.with_suffix(".py").is_file() or base.is_dir()


def _scan_source(program: str, path: Path, tree: ast.Module, constants: dict[str, str], into: Surface) -> None:
    local = {**constants, **_module_constants(tree)}
    where = path.relative_to(_repo_root()).as_posix()
    for node in ast.walk(tree):
        name_expr = _environ_read(node)
        if name_expr is not None:
            if isinstance(name_expr, ast.Constant) and isinstance(name_expr.value, str):
                into.env_vars.add(name_expr.value)
            elif isinstance(name_expr, ast.Name) and name_expr.id in local:
                into.env_vars.add(local[name_expr.id])
            else:
                into.unresolved.append(
                    f"{ENV_VAR}: the read at {where}:{getattr(node, 'lineno', '?')} names no literal or module "
                    "constant, so contract.md cannot be checked for it"
                )
        if isinstance(node, ast.Call) and _is_typer_exit(node.func):
            code = next((kw.value for kw in node.keywords if kw.arg == "code"), node.args[0] if node.args else None)
            if code is None:
                into.exit_codes.add((program, 0))
            elif isinstance(code, ast.Constant) and type(code.value) is int:
                into.exit_codes.add((program, code.value))
            else:
                into.unresolved.append(
                    f"{EXIT_CODE}: typer.Exit at {where}:{node.lineno} has no literal code, so contract.md cannot "
                    "be checked for it"
                )
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            match = _FLAG_KEY.fullmatch(node.value)
            if match is not None and not _names_a_module(match.group(1), match.group(2)):
                into.flag_keys.add(node.value)


def _walk_click_tree(command: object, path: str, into: Surface) -> None:
    for param in getattr(command, "params", ()):
        if param.param_type_name == "option":
            for option in (*param.opts, *param.secondary_opts):
                into.flags.add((path, option))
    subcommands = getattr(command, "commands", None) or {}
    for name, sub in subcommands.items():
        _walk_click_tree(sub, f"{path} {name}".strip(), into)
    if not subcommands and path:
        into.verb_paths.add(path)


def derive_code_side() -> Surface:
    """Everything scribe serves to a caller, read from the code."""
    code = Surface()
    _walk_click_tree(typer.main.get_command(app), "", code)
    code.mcp_tools.update(_TOOL_CONSTANT.findall(_mcp_asgi().read_text(encoding="utf-8")))
    files = _scanned_files()
    trees = {path: ast.parse(path.read_text(encoding="utf-8"), filename=str(path)) for _, path in files}
    shared: dict[str, str] = {}
    for tree in trees.values():
        for name, value in _module_constants(tree).items():
            shared.setdefault(name, value)
    for program, path in files:
        _scan_source(program, path, trees[path], shared, code)
    return code


# --------------------------------------------------------------------------- the contract side


def _table_rows(text: str) -> dict[str, list[list[str]]]:
    """Table rows (as cell lists) under each ``##`` heading."""
    rows: dict[str, list[list[str]]] = {}
    heading: str | None = None
    for line in text.splitlines():
        match = _HEADING.match(line)
        if match is not None:
            heading = match.group(1)
            rows.setdefault(heading, [])
        elif heading is not None and line.startswith("|"):
            rows[heading].append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return rows


def _ticks(row: list[str], index: int) -> list[str]:
    return _TICK.findall(row[index]) if len(row) > index else []


def read_contract(text: str) -> Surface:
    """What ``contract.md`` records, by family."""
    rows = _table_rows(text)
    recorded = Surface()
    for row in rows.get(SECTION[VERB_PATH], []):
        first = _ticks(row, 0)
        if not first or (first[0] != PROGRAM and not first[0].startswith(f"{PROGRAM} ")):
            continue
        path = first[0][len(PROGRAM) :].strip()
        recorded.verb_paths.add(path)
        recorded.flags.update((path, token) for token in _ticks(row, 1) if token.startswith("-"))
    for row in rows.get(SECTION[MCP_TOOL], []):
        recorded.mcp_tools.update(_ticks(row, 0))
    for row in rows.get(SECTION[FLAG_KEY], []):
        recorded.flag_keys.update(_ticks(row, 0))
    for row in rows.get(SECTION[ENV_VAR], []):
        recorded.env_vars.update(_ticks(row, 0))
    for row in rows.get(SECTION[EXIT_CODE], []):
        codes = [int(token) for token in _ticks(row, 1) if token.isdigit()]
        recorded.exit_codes.update((program, code) for program in _ticks(row, 0) for code in codes)
    return recorded


def _verb(path: str) -> str:
    return f"`{PROGRAM} {path}`" if path else f"`{PROGRAM}`"


def missing_from_contract(code: Surface, recorded: Surface) -> list[str]:
    """One finding per item the code serves and the contract lacks, naming the item and its family."""
    items: list[tuple[str, str]] = []
    items += [(VERB_PATH, _verb(path)) for path in sorted(code.verb_paths - recorded.verb_paths)]
    items += [(FLAG, f"`{flag}` of {_verb(path)}") for path, flag in sorted(code.flags - recorded.flags)]
    items += [(MCP_TOOL, f"`{tool}`") for tool in sorted(code.mcp_tools - recorded.mcp_tools)]
    items += [(FLAG_KEY, f"`{key}`") for key in sorted(code.flag_keys - recorded.flag_keys)]
    items += [(ENV_VAR, f"`{name}`") for name in sorted(code.env_vars - recorded.env_vars)]
    items += [(EXIT_CODE, f"`{c}` of `{prog}`") for prog, c in sorted(code.exit_codes - recorded.exit_codes)]
    findings = [
        f"{family}: {item} is in the code and absent from contract.md § {SECTION[family]}" for family, item in items
    ]
    return [*findings, *code.unresolved]


# --------------------------------------------------------------------------- the tests


@pytest.fixture(scope="module")
def code_side() -> Surface:
    return derive_code_side()


@pytest.fixture(scope="module")
def contract_text() -> str:
    contract = _contract()
    assert contract.is_file(), f"the contract companion is missing: {contract.relative_to(_repo_root())}"
    return contract.read_text(encoding="utf-8")


def test_the_code_side_is_derived_not_empty(code_side: Surface) -> None:
    """A scan that finds nothing would pass vacuously: every family reads something, and a module constant resolves."""
    mcp_asgi = _mcp_asgi()
    assert mcp_asgi.is_file(), f"django-scribe's MCP face is missing: {mcp_asgi.relative_to(_repo_root())}"
    for family, items in (
        (VERB_PATH, code_side.verb_paths),
        (FLAG, code_side.flags),
        (MCP_TOOL, code_side.mcp_tools),
        (FLAG_KEY, code_side.flag_keys),
        (ENV_VAR, code_side.env_vars),
        (EXIT_CODE, code_side.exit_codes),
    ):
        assert items, f"the {family} scan found nothing; the derivation is broken, not the contract"
    # Read only through `_BACKEND_ENV` in scripts/scribe_install_nightly_trigger.py: proves constant resolution.
    assert "PYFORGE_SCRIBE_TRIGGER_BACKEND" in code_side.env_vars
    # A hook name and a module path are literals of the flag-key shape, and neither is a flag key.
    assert not code_side.flag_keys & {"pyforge.scribe.graph_store", "pyforge.scribe.cli"}


def test_contract_records_every_item_the_code_serves(code_side: Surface, contract_text: str) -> None:
    findings = missing_from_contract(code_side, read_contract(contract_text))
    assert not findings, "contract.md falls behind the code:\n" + "\n".join(findings)


def _drop_row(row_start: str) -> Callable[[str], str]:
    def mutate(text: str) -> str:
        return "\n".join(line for line in text.splitlines() if not line.startswith(row_start)) + "\n"

    return mutate


def _drop_token(row_start: str, token: str) -> Callable[[str], str]:
    def mutate(text: str) -> str:
        lines = [line.replace(token, "") if line.startswith(row_start) else line for line in text.splitlines()]
        return "\n".join(lines) + "\n"

    return mutate


# One planted gap per family: (family, the item as the finding names it, the mutation, the item on the code side).
PLANTED = [
    pytest.param(
        VERB_PATH,
        "`scribe index refresh`",
        _drop_row("| `scribe index refresh` |"),
        lambda code: "index refresh" in code.verb_paths,
        id="verb-path",
    ),
    pytest.param(
        FLAG,
        "`--pipeline-truth` of `scribe catalog bmad-estate`",
        _drop_token("| `scribe catalog bmad-estate` |", "`--pipeline-truth`"),
        lambda code: ("catalog bmad-estate", "--pipeline-truth") in code.flags,
        id="flag",
    ),
    pytest.param(
        MCP_TOOL,
        "`start_recall`",
        _drop_row("| `start_recall` |"),
        lambda code: "start_recall" in code.mcp_tools,
        id="mcp-tool",
    ),
    pytest.param(
        FLAG_KEY,
        "`pyforge.scribe.bmad_estate_catalog`",
        _drop_row("| `pyforge.scribe.bmad_estate_catalog` |"),
        lambda code: "pyforge.scribe.bmad_estate_catalog" in code.flag_keys,
        id="flag-key",
    ),
    pytest.param(
        ENV_VAR,
        "`SCRIBE_PG_SOCKET_DIR`",
        _drop_row("| `SCRIBE_PG_SOCKET_DIR` |"),
        lambda code: "SCRIBE_PG_SOCKET_DIR" in code.env_vars,
        id="environment-variable",
    ),
    pytest.param(
        EXIT_CODE,
        "`1` of `scribe`",
        _drop_row("| `scribe` | `1` |"),
        lambda code: (PROGRAM, 1) in code.exit_codes,
        id="exit-code",
    ),
]


@pytest.mark.parametrize(("family", "item", "mutate", "in_code"), PLANTED)
def test_checker_names_a_missing_item(
    code_side: Surface,
    contract_text: str,
    family: str,
    item: str,
    mutate: Callable[[str], str],
    in_code: Callable[[Surface], bool],
) -> None:
    assert in_code(code_side), f"the planted {family} {item} is not served by the code; pick one that is"
    expected = f"{family}: {item} is in the code and absent from contract.md § {SECTION[family]}"
    assert expected not in missing_from_contract(code_side, read_contract(contract_text))
    planted = mutate(contract_text)
    assert planted != contract_text, f"the mutation for {family} {item} matched nothing in contract.md"
    findings = missing_from_contract(code_side, read_contract(planted))
    assert expected in findings, f"a contract without {family} {item} was not reported by name:\n" + "\n".join(findings)
