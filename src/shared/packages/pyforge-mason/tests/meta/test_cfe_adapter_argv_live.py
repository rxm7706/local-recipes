"""Story 38.3 (spec-pyforge-mason CAP-7, FR-62 <- CAP-7): Mason's adapters pass only what the
wrapped scripts declare.

`tests/integration/test_delegation_fidelity.py` runs one wrapped script for real; every other one
is exercised only against stubs this suite wrote, so a script renamed or an option dropped on the
conda-forge-expert side would leave the suite green. This module closes the part of that gap that
needs no CFE run. It reads source text and runs nothing, and it needs no network:

- The script names come from `pyforge.mason.cfe._CFE_SCRIPTS` (AD-3: they live in `cfe.py`
  alone), and where each one sits under the CFE root comes from the path expression `cfe.py`
  itself builds (`root / ... / _CFE_SCRIPTS[...]`), read by AST.
- The options an adapter can pass are the option-shaped string literals (`--name`) in the argument
  lists that reach it: the adapter function's own body in `cfe.py` and every `cfe.py` helper it
  calls, plus the first argument at each call site in `recipe.py`. `recipe.py` is walked branch by
  branch, so an option appended inside a branch that returns after calling one adapter is never
  credited to an adapter called after that branch.
- On the CFE side, a script with no argument parser of its own that builds one `Path(__file__)`
  anchored path to another `.py` file is a thin wrapper: the check follows it to the script it
  runs and reads that file's `add_argument` declarations. A script that is not Python has no parser
  to read and is checked for existence only.

Nothing here names a CFE script or a CFE option (CAP-7's knowledge-free rule). Every path is
anchored on `Path(__file__)`; no package code is handed the repository root. The module reads the
real conda-forge-expert tree, so it is in the live-tree half (Story 38.2). The two `planted` tests
copy the files the live check read into a temporary root, plant one violation each, and prove the
same check reports it.

A mismatch is never patched on the CFE side from here: conda-forge-expert changes need the skill
and a retro. The argv contract proper belongs to conda-forge-expert's own Spec (Story 39.2).
"""

from __future__ import annotations

import ast
import functools
import re
import shutil
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from pyforge.mason import cfe

pytestmark = pytest.mark.live_tree

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[6]
_MASON_SRC = _HERE.parents[2] / "src" / "pyforge" / "mason"
_ADAPTER_MODULE = _MASON_SRC / "cfe.py"
_USE_CASE_MODULE = _MASON_SRC / "recipe.py"

_OPTION = re.compile(r"--[A-Za-z0-9][A-Za-z0-9_-]*")
"""An option-shaped literal: `--name`, or `--name=value` (only the name counts). Prose that merely
contains a double dash (`"... -- got ..."`) does not match."""

_LIST_MUTATORS = frozenset({"append", "extend", "insert"})
_COMPOUND = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.TryStar,
    ast.Match,
)
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


# --- the Mason side: table, locations and passed options, all read from the package source ------


def _option_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str) and _OPTION.fullmatch(node.value.split("=")[0]):
        return node.value.split("=", 1)[0]
    return None


def _body_without_docstring(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.stmt]:
    body = func.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        return body[1:]
    return body


def _module_functions(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    return {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _table_key(node: ast.AST, table_name: str) -> str | None:
    """`_CFE_SCRIPTS["<key>"]` -> `<key>`; any other node -> None."""
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == table_name
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, str)
    ):
        return node.slice.value
    return None


def _div_chain(node: ast.AST) -> list[ast.AST]:
    """`a / b / c` -> [a, b, c]; any other node -> [node]."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return [*_div_chain(node.left), node.right]
    return [node]


@dataclass(frozen=True)
class _MasonSide:
    table: Mapping[str, str]
    """Adapter key -> script filename, `cfe._CFE_SCRIPTS` itself."""
    location: Mapping[str, tuple[str, ...]]
    """Adapter key -> the directory parts between the CFE root and the script, as `cfe.py` builds them."""
    passed: Mapping[str, frozenset[str]]
    """Adapter key -> every option a Mason adapter can pass to that script."""


def _adapter_functions(
    functions: Mapping[str, ast.FunctionDef | ast.AsyncFunctionDef], table_name: str, runner: str
) -> dict[str, str]:
    """Adapter function name -> its script key: the one function that names the key, either as
    `_CFE_SCRIPTS["<key>"]` or as the first argument of the CAPTURE runner."""
    adapters: dict[str, str] = {}
    for name, func in functions.items():
        keys: set[str] = set()
        for node in ast.walk(func):
            key = _table_key(node, table_name)
            if key is not None:
                keys.add(key)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == runner
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                keys.add(node.args[0].value)
        assert len(keys) <= 1, f"cfe.py function {name}() names more than one script key: {sorted(keys)}"
        if keys:
            adapters[name] = keys.pop()
    return adapters


def _locations(tree: ast.Module, table: Mapping[str, str], table_name: str, runner: str) -> dict[str, tuple[str, ...]]:
    """Read each script's directory under the CFE root from the `root / "a" / ... / _CFE_SCRIPTS[k]`
    expressions in `cfe.py`: a literal key gives that key's own location; a variable key (the CAPTURE
    runner's) gives the location of every key routed through the runner."""
    direct: dict[str, tuple[str, ...]] = {}
    generic: set[tuple[str, ...]] = set()
    for node in ast.walk(tree):
        chain = _div_chain(node)
        if len(chain) < 2 or not isinstance(chain[0], ast.Name):
            continue
        tail = chain[-1]
        if not (isinstance(tail, ast.Subscript) and isinstance(tail.value, ast.Name) and tail.value.id == table_name):
            continue
        parts = chain[1:-1]
        assert all(isinstance(p, ast.Constant) and isinstance(p.value, str) for p in parts), (
            f"cfe.py line {node.lineno}: a script path segment is not a string literal"
        )
        location = tuple(p.value for p in parts if isinstance(p, ast.Constant))
        key = _table_key(tail, table_name)
        if key is None:
            generic.add(location)
        else:
            direct[key] = location
    assert len(generic) <= 1, f"cfe.py builds the runner's script path more than one way: {sorted(generic)}"
    routed = {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == runner
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    }
    out: dict[str, tuple[str, ...]] = {}
    for key in table:
        if key in direct:
            out[key] = direct[key]
        elif key in routed and generic:
            out[key] = next(iter(generic))
    unlocated = sorted(set(table) - set(out))
    assert not unlocated, f"cfe.py builds no script path for table key(s) {unlocated}"
    return out


def _own_options(func: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    return frozenset(
        name for stmt in _body_without_docstring(func) for node in ast.walk(stmt) if (name := _option_name(node))
    )


def _adapter_module_options(
    functions: Mapping[str, ast.FunctionDef | ast.AsyncFunctionDef], adapters: Mapping[str, str]
) -> dict[str, frozenset[str]]:
    """Options a `cfe.py` adapter function writes into the argv itself, or through any `cfe.py`
    function it calls (the CAPTURE runner, the STREAM primitive), transitively."""
    calls: dict[str, set[str]] = {
        name: {
            node.func.id
            for node in ast.walk(func)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in functions
        }
        for name, func in functions.items()
    }
    out: dict[str, frozenset[str]] = {}
    for name, key in adapters.items():
        seen: set[str] = set()
        stack = [name]
        options: set[str] = set()
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            options |= _own_options(functions[current])
            stack.extend(calls[current])
        out[key] = out.get(key, frozenset()) | frozenset(options)
    return out


_State = dict[str, frozenset[str]]


def _options_in(node: ast.AST, state: Mapping[str, frozenset[str]]) -> frozenset[str]:
    """Every option literal in `node`, plus every option already carried by a name it reads."""
    found: set[str] = set()
    for sub in ast.walk(node):
        name = _option_name(sub)
        if name:
            found.add(name)
        elif isinstance(sub, ast.Name) and sub.id in state:
            found |= state[sub.id]
    return frozenset(found)


def _merge(states: Sequence[_State]) -> _State:
    merged: _State = {}
    for state in states:
        for name, options in state.items():
            merged[name] = merged.get(name, frozenset()) | options
    return merged


def _child_blocks(stmt: ast.stmt) -> Iterator[list[ast.stmt]]:
    for field in ("body", "orelse", "finalbody"):
        block = getattr(stmt, field, None)
        if block:
            yield block
    for handler in getattr(stmt, "handlers", ()):
        yield handler.body
    for case in getattr(stmt, "cases", ()):
        yield case.body


def _own_expressions(stmt: ast.stmt) -> Iterator[ast.AST]:
    """The expressions a compound statement evaluates itself (its test, iterable, context
    managers), never the statements nested in its blocks."""
    for field, value in ast.iter_fields(stmt):
        if field in {"body", "orelse", "finalbody", "handlers", "cases"}:
            continue
        values = value if isinstance(value, list) else [value]
        yield from (v for v in values if isinstance(v, ast.AST))


class _CallSites:
    """Walks `recipe.py` and records, per adapter key, the options at each adapter call site."""

    def __init__(self, adapters: Mapping[str, str]) -> None:
        self.adapters = adapters
        self.passed: dict[str, frozenset[str]] = {}
        self.sites = 0

    def _scan(self, node: ast.AST, state: Mapping[str, frozenset[str]]) -> None:
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Call):
                continue
            func = sub.func
            name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else None
            if name not in self.adapters:
                continue
            self.sites += 1
            key = self.adapters[name]
            first = sub.args[0] if sub.args else next((kw.value for kw in sub.keywords if kw.arg == "args"), None)
            options = _options_in(first, state) if first is not None else frozenset()
            self.passed[key] = self.passed.get(key, frozenset()) | options

    @staticmethod
    def _mutate(stmt: ast.stmt, state: _State) -> None:
        if isinstance(stmt, ast.Assign):
            options = _options_in(stmt.value, state)
            for target in stmt.targets:
                for sub in ast.walk(target):
                    if isinstance(sub, ast.Name):
                        state[sub.id] = options
        elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None and isinstance(stmt.target, ast.Name):
            state[stmt.target.id] = _options_in(stmt.value, state)
        elif isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
            state[stmt.target.id] = state.get(stmt.target.id, frozenset()) | _options_in(stmt.value, state)
        elif (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Call)
            and isinstance(stmt.value.func, ast.Attribute)
            and stmt.value.func.attr in _LIST_MUTATORS
            and isinstance(stmt.value.func.value, ast.Name)
        ):
            target = stmt.value.func.value.id
            added = frozenset().union(*(_options_in(arg, state) for arg in stmt.value.args))
            state[target] = state.get(target, frozenset()) | added

    def walk(self, stmts: Sequence[ast.stmt], state: Mapping[str, frozenset[str]]) -> _State | None:
        """Return the state after `stmts`, or None when every path through them returns or raises.
        A compound statement may run any one of its blocks or none of them, so the state after it
        is the merge of the state before it with every block that falls through."""
        current: _State = dict(state)
        for stmt in stmts:
            if isinstance(stmt, _SCOPES):
                self.walk(stmt.body, current)
                continue
            if isinstance(stmt, _COMPOUND):
                for expr in _own_expressions(stmt):
                    self._scan(expr, current)
                outcomes = [self.walk(block, current) for block in _child_blocks(stmt)]
                current = _merge([current, *(o for o in outcomes if o is not None)])
                continue
            self._scan(stmt, current)
            self._mutate(stmt, current)
            if isinstance(stmt, (ast.Return, ast.Raise)):
                return None
        return current


@functools.cache
def _mason_side() -> _MasonSide:
    table = dict(cfe._CFE_SCRIPTS)
    assert table, "cfe._CFE_SCRIPTS is empty"
    adapter_tree = ast.parse(_ADAPTER_MODULE.read_text(encoding="utf-8"))
    functions = _module_functions(adapter_tree)
    table_name, runner = "_CFE_SCRIPTS", "_invoke_captured"
    assert runner in functions, f"cfe.py has no {runner}() -- re-point this check at the CAPTURE runner"
    adapters = _adapter_functions(functions, table_name, runner)
    unadapted = sorted(set(table) - set(adapters.values()))
    assert not unadapted, f"no cfe.py function names the table key(s) {unadapted}"
    location = _locations(adapter_tree, table, table_name, runner)

    passed = _adapter_module_options(functions, adapters)
    sites = _CallSites(adapters)
    use_case_tree = ast.parse(_USE_CASE_MODULE.read_text(encoding="utf-8"))
    sites.walk(use_case_tree.body, {})
    assert sites.sites, "recipe.py calls no cfe.py adapter -- the option scan would be vacuous"
    for key, options in sites.passed.items():
        passed[key] = passed.get(key, frozenset()) | options
    assert any(passed.values()), "no adapter passes any option -- the option scan would be vacuous"
    return _MasonSide(table=table, location=location, passed=passed)


# --- the CFE side: files and declared options, read as source text ------------------------------


def _add_argument_calls(tree: ast.Module) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument"
    ]


def _declared_options(calls: Sequence[ast.Call]) -> frozenset[str]:
    """Every option string the given `add_argument(...)` calls declare."""
    return frozenset(
        arg.value
        for call in calls
        for arg in call.args
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.startswith("-")
    )


def _file_anchored(node: ast.AST, here: Path) -> Path | None:
    """Evaluate a `Path(__file__)`-anchored expression (`.parent`, `.parents[n]`, `.resolve()`,
    `/ "segment"`) lexically against `here`; any other expression -> None."""
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Path"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "__file__"
    ):
        return here
    if isinstance(node, ast.Attribute) and node.attr == "parent":
        base = _file_anchored(node.value, here)
        return base.parent if base is not None else None
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "parents"
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, int)
    ):
        base = _file_anchored(node.value.value, here)
        return base.parents[node.slice.value] if base is not None else None
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"resolve", "absolute"}
    ):
        return _file_anchored(node.func.value, here)
    if (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Div)
        and isinstance(node.right, ast.Constant)
        and isinstance(node.right.value, str)
    ):
        base = _file_anchored(node.left, here)
        return base / node.right.value if base is not None else None
    return None


def _wrapped_targets(tree: ast.Module, here: Path) -> list[Path]:
    targets: list[Path] = []
    for node in ast.walk(tree):
        path = _file_anchored(node, here)
        if path is not None and path.suffix == ".py" and path != here and path not in targets:
            targets.append(path)
    return targets


@dataclass(frozen=True)
class _Verdict:
    missing: tuple[str, ...]
    """Adapter keys whose script, or the script a thin wrapper runs, has no file."""
    undeclared: tuple[tuple[str, str], ...]
    """(adapter key, option) pairs an adapter can pass that the wrapped script never declares."""
    read: tuple[Path, ...]
    """Every CFE file the check read."""
    parsers: Mapping[str, tuple[Path, ...]]
    """Adapter key -> the file(s) whose `add_argument` calls were read for it."""


def _check(root: Path, mason: _MasonSide) -> _Verdict:
    missing: list[str] = []
    undeclared: list[tuple[str, str]] = []
    read: list[Path] = []
    parsers: dict[str, tuple[Path, ...]] = {}
    for key, filename in mason.table.items():
        script = root.joinpath(*mason.location[key], filename)
        if not script.is_file():
            missing.append(key)
            continue
        read.append(script)
        if script.suffix != ".py":
            continue  # no argument parser to read: existence only
        frontier: list[Path] = [script]
        seen: set[Path] = set()
        declared: set[str] = set()
        absent = False
        while frontier:
            current = frontier.pop()
            if current in seen:
                continue
            seen.add(current)
            if not current.is_file():
                absent = True
                continue
            if current not in read:
                read.append(current)
            tree = ast.parse(current.read_text(encoding="utf-8"))
            calls = _add_argument_calls(tree)
            targets = [] if calls else _wrapped_targets(tree, current)
            if targets:
                frontier.extend(targets)  # a thin wrapper: read the script it runs instead
            else:
                declared |= _declared_options(calls)
                parsers[key] = (*parsers.get(key, ()), current)
        if absent:
            missing.append(key)
            continue
        undeclared.extend((key, option) for option in sorted(mason.passed.get(key, ())) if option not in declared)
    return _Verdict(tuple(missing), tuple(undeclared), tuple(read), parsers)


def _copy_read_files(verdict: _Verdict, source_root: Path, dest_root: Path, *, skip: Path | None = None) -> None:
    for path in verdict.read:
        if path == skip:
            continue
        target = dest_root / path.relative_to(source_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


# --- the live tree --------------------------------------------------------------------------------


def test_every_script_the_adapter_table_names_exists_at_the_real_cfe_root() -> None:
    verdict = _check(_REPO_ROOT, _mason_side())
    assert not verdict.missing, (
        f"adapter table key(s) with no script file under {_REPO_ROOT}: {list(verdict.missing)} -- "
        "a renamed or removed conda-forge-expert script; record it as a deferral, never patch CFE from here"
    )


def test_every_option_an_adapter_can_pass_is_declared_by_the_wrapped_script() -> None:
    verdict = _check(_REPO_ROOT, _mason_side())
    assert verdict.parsers, "no wrapped script's argument parser was read -- the option check would be vacuous"
    assert not verdict.undeclared, (
        f"options a Mason adapter can pass that the wrapped script never declares: {list(verdict.undeclared)} -- "
        "a one-line adapter fix if Mason's, otherwise a deferral; never a CFE edit from here"
    )


# --- planted violations: the same check, on a copy of what it read ------------------------------


def test_planted_script_table_entry_with_no_file_is_reported(tmp_path: Path) -> None:
    mason = _mason_side()
    live = _check(_REPO_ROOT, mason)
    key = next(iter(mason.table))
    script = _REPO_ROOT.joinpath(*mason.location[key], mason.table[key])
    _copy_read_files(live, _REPO_ROOT, tmp_path, skip=script)

    planted = _check(tmp_path, mason)

    assert planted.missing == (key,)
    assert planted.undeclared == ()


def test_planted_script_source_lacking_a_passed_option_is_reported(tmp_path: Path) -> None:
    mason = _mason_side()
    live = _check(_REPO_ROOT, mason)
    key, option = next(
        (k, sorted(mason.passed[k])[0]) for k in mason.table if mason.passed.get(k) and k in live.parsers
    )
    _copy_read_files(live, _REPO_ROOT, tmp_path)
    changed = 0
    for parser in live.parsers[key]:
        copy = tmp_path / parser.relative_to(_REPO_ROOT)
        text = copy.read_text(encoding="utf-8")
        planted_text = text.replace(f'"{option}"', '"--planted-undeclared"').replace(
            f"'{option}'", "'--planted-undeclared'"
        )
        changed += planted_text != text
        copy.write_text(planted_text, encoding="utf-8")
    assert changed, f"no parser read for {key} spells {option} as a literal -- nothing was planted"

    planted = _check(tmp_path, mason)

    assert planted.missing == ()
    assert (key, option) in planted.undeclared
    assert {o for _, o in planted.undeclared} == {option}
