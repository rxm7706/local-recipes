"""Story 98.1 (spec-pyforge-steward CAP-159): station tests run when what they read changes.

``.github/workflows/pyforge-station-tests.yml`` gates each of its ten suite jobs on a
literal list of paths (one array per job in the ``changes`` step, plus the identical
``on.pull_request.paths`` / ``on.push.paths`` lists). Before this story the lists named each
suite's own package and a short shared surface, while the suites read files far outside
both -- a change to one of those files ran no suite that reads it, and a break landed on
``main`` unseen (herald Story 38.1 changed ``scripts/lint_types.py`` and ``django-herald``;
steward's ``test_lint_types_django_tables.py`` went red on ``main`` with no job to catch it).

This meta-test makes the lists derived, not remembered:

* it reads the ten jobs from the workflow's ``jobs:`` and their pixi tasks from ``pixi.toml``
  (never a hand list), and derives what each job's tests read by static analysis of the
  tests themselves (``derive_reads``): ``Path(__file__)``-anchored expressions resolved
  to repository paths, and string literals that name a git-tracked path;
* a test that hands the bare repository root to the code under test reads whatever that code
  reads, which a scan of the test cannot see; those files are derived too and each one's
  inputs are declared in ``ROOT_HANDOFF_INPUTS`` (the derived set must equal the declared
  keys, so a new live-tree test fails until it is declared and a stale declaration fails too);
* for every read, a fixture repository changes one tracked representative path and the
  workflow's own ``changes`` script must set the job's output ``true``, and
  ``on.pull_request.paths`` must match the path under GitHub's glob rules.

No read is exempt (operator ruling 2026-10-12, "Trigger on planning too"): a read the filter
should not carry is removed from the test that makes it. The derivation is static, so a read
built from a value it cannot resolve is not derived; the non-vacuity rows below fail if the
derivation goes blind, and the mutation tests prove each half of the check fires.
"""

from __future__ import annotations

import ast
import fnmatch
import functools
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import tomllib
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import yaml

from pyforge.steward import preflight_ci

# tests/meta -> tests -> pyforge-steward -> packages -> shared -> src -> repo root
REPO_ROOT = Path(__file__).resolve().parents[6]
WORKFLOW_REL = ".github/workflows/pyforge-station-tests.yml"
WORKFLOW = REPO_ROOT / WORKFLOW_REL
THIS_FILE_REL = Path(__file__).resolve().relative_to(REPO_ROOT).as_posix()
PIXI_TOML = REPO_ROOT / "pixi.toml"
PACKAGES = "src/shared/packages"
BASE_REF = "refs/remotes/origin/main"
WILD = "*"

_GATE = re.compile(r"needs\.changes\.outputs\.(\w+)\s*==\s*'true'")
_PIXI_RUN = re.compile(r"pixi run --frozen -e (\S+) (\S+)")

# ---------------------------------------------------------------------------
# The tracked tree
# ---------------------------------------------------------------------------


@functools.cache
def tracked_files() -> tuple[str, ...]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=REPO_ROOT, check=True, capture_output=True, text=True).stdout
    return tuple(sorted(p for p in out.split("\0") if p and (REPO_ROOT / p).exists()))


@functools.cache
def _tracked_set() -> frozenset[str]:
    return frozenset(tracked_files())


@functools.cache
def _tracked_dirs() -> frozenset[str]:
    dirs: set[str] = set()
    for path in tracked_files():
        parts = path.split("/")
        for i in range(1, len(parts)):
            dirs.add("/".join(parts[:i]))
    return frozenset(dirs)


def _has_glob(segment: str) -> bool:
    return any(c in segment for c in "*?[")


def _segment_match(pattern: str, segment: str) -> bool:
    return pattern == WILD or fnmatch.fnmatchcase(segment, pattern)


def representative(parts: Sequence[str]) -> str | None:
    return _representative(tuple(parts))


@functools.cache
def _representative(parts: tuple[str, ...]) -> str | None:
    """The first tracked file at or under ``parts`` (a ``*`` segment matches any one segment)."""
    if not any(_has_glob(p) for p in parts):
        joined = "/".join(parts)
        if joined in _tracked_set():
            return joined
        if joined in _tracked_dirs():
            prefix = joined + "/"
            return next(p for p in tracked_files() if p.startswith(prefix))
        return None
    n = len(parts)
    for path in tracked_files():
        segs = path.split("/")
        if len(segs) >= n and all(_segment_match(p, s) for p, s in zip(parts, segs, strict=False)):
            return path
    return None


# ---------------------------------------------------------------------------
# What a test reads: a small static evaluator over the test's AST
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class V:
    """A path. ``rooted``: repo-relative, resolved from ``__file__``; else a relative literal."""

    parts: tuple[str, ...]
    rooted: bool = True


@dataclass(frozen=True)
class Modref:
    dotted: str


@functools.cache
def _module_index() -> Mapping[str, str]:
    """dotted module name -> repo-relative file, for every ``src/shared/packages/*/src`` module."""
    index: dict[str, str] = {}
    pattern = re.compile(rf"^{re.escape(PACKAGES)}/[^/]+/src/(.+)\.py$")
    for path in tracked_files():
        m = pattern.match(path)
        if not m:
            continue
        dotted = m.group(1).replace("/", ".")
        dotted = dotted.removesuffix(".__init__")
        index.setdefault(dotted, path)
    return index


@functools.cache
def _module_prefixes() -> frozenset[str]:
    prefixes: set[str] = set()
    for dotted in _module_index():
        parts = dotted.split(".")
        for i in range(1, len(parts) + 1):
            prefixes.add(".".join(parts[:i]))
    return frozenset(prefixes)


def _is_fixture(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for dec in node.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        name = target.attr if isinstance(target, ast.Attribute) else getattr(target, "id", "")
        if name == "fixture":
            return True
    return False


def _split_segments(text: str) -> list[str]:
    return [s for s in text.split("/") if s not in ("", ".")]


def _extend(base: V, segments: Iterable[str]) -> V | None:
    parts = list(base.parts)
    for seg in segments:
        if seg == "..":
            if not parts:
                return None
            parts.pop()
        else:
            parts.append(seg)
    return V(tuple(parts), base.rooted)


class Module:
    """One scanned Python file: its module-level environment, fixtures and zero-argument helpers."""

    def __init__(self, scanner: Scanner, rel: str, tree: ast.Module) -> None:
        self.scanner = scanner
        self.rel = rel
        self.parts = tuple(rel.split("/"))
        self.tree = tree
        self.env: dict[str, object] = {}
        self.funcs: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        self.path_names: set[str] = {"Path", "PurePath", "PosixPath"}
        self.fixtures: dict[str, object] = {}
        self._depth = 0


class Scanner:
    """Collects the reads of every Python file handed to ``scan``."""

    def __init__(self, package_dir: str | None) -> None:
        self.package_dir = package_dir
        self.modules: dict[str, Module] = {}
        self.reads: dict[tuple[str, ...], set[str]] = defaultdict(set)
        self.handoffs: set[str] = set()
        self._loading: set[str] = set()
        self._returns: dict[tuple, object] = {}
        self._inlined: set[tuple] = set()
        self._inline_depth = 0

    # -- module loading ---------------------------------------------------

    def module(self, rel: str) -> Module | None:
        if rel in self.modules:
            return self.modules[rel]
        if rel in self._loading or rel not in _tracked_set():
            return None
        try:
            tree = ast.parse((REPO_ROOT / rel).read_text(encoding="utf-8"))
        except SyntaxError, UnicodeDecodeError, ValueError:
            return None
        self._loading.add(rel)
        mod = Module(self, rel, tree)
        self.modules[rel] = mod
        self._prepare(mod)
        self._loading.discard(rel)
        return mod

    def _prepare(self, mod: Module) -> None:
        for stmt in mod.tree.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                mod.funcs[stmt.name] = stmt
        self._bind_statements(mod.tree.body, mod.env, mod, record=False)
        for name, func in list(mod.funcs.items()):
            if _is_fixture(func):
                value = self._call_function(func, mod, {})
                if value is not None:
                    mod.fixtures[name] = value

    def _local_module(self, mod: Module, name: str, level: int) -> Module | None:
        """A sibling test-support module (``from conftest import X``, ``from .helpers import X``)."""
        leaf = name.split(".")[-1] if name else ""
        directory = list(mod.parts[:-1])
        if level > 1:
            directory = directory[: len(directory) - (level - 1)]
        search = [directory] if level else [directory[:i] for i in range(len(directory), 0, -1)]
        for d in search:
            for candidate in (f"{leaf}.py", f"{leaf}/__init__.py"):
                rel = "/".join([*d, candidate])
                if rel in _tracked_set():
                    return self.module(rel)
        return None

    # -- statements -------------------------------------------------------

    def _bind_statements(self, body: Sequence[ast.stmt], env: dict[str, object], mod: Module, *, record: bool) -> None:
        for stmt in body:
            self._statement(stmt, env, mod, record=record)

    def _statement(self, stmt: ast.stmt, env: dict[str, object], mod: Module, *, record: bool) -> None:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                dotted = alias.name
                if alias.asname:
                    if dotted in _module_prefixes():
                        env[alias.asname] = Modref(dotted)
                else:
                    head = dotted.split(".")[0]
                    if head in _module_prefixes():
                        env[head] = Modref(head)
            return
        if isinstance(stmt, ast.ImportFrom):
            self._import_from(stmt, env, mod)
            return
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            mod.funcs.setdefault(stmt.name, stmt)
            if record:
                self._function(stmt, env, mod)
            return
        if isinstance(stmt, ast.ClassDef):
            class_env = dict(env)
            self._bind_statements(stmt.body, class_env, mod, record=record)
            return
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            value_node = stmt.value
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            if value_node is None:
                return
            value = self.ev(value_node, env, mod)
            if value is not None and len(targets) == 1 and isinstance(targets[0], ast.Name):
                env[targets[0].id] = value
                if record and isinstance(value, (list, tuple)):
                    self._record_container(value, mod)  # a table of paths is built to be read
                return
            if (
                isinstance(value_node, (ast.Tuple, ast.List))
                and len(targets) == 1
                and isinstance(targets[0], ast.Tuple)
                and len(targets[0].elts) == len(value_node.elts)
            ):
                for t, v in zip(targets[0].elts, value_node.elts, strict=True):
                    item = self.ev(v, env, mod)
                    if isinstance(t, ast.Name) and item is not None:
                        env[t.id] = item
                return
            keep = isinstance(value_node, ast.Constant) and value_node.value is None  # `except: ROOT = None`
            for t in targets:
                if isinstance(t, ast.Name) and not keep:
                    env.pop(t.id, None)
            self.visit(value_node, env, mod, stmt)
            return
        if isinstance(stmt, (ast.For, ast.AsyncFor)):
            if isinstance(stmt.target, ast.Name) and self._walks_up_to_root(stmt.iter, env, mod):
                # `for candidate in here.parents: if (candidate / "pixi.toml").is_file(): return candidate`
                env[stmt.target.id] = V(())
                self._bind_statements(stmt.body, env, mod, record=record)
                return
            self.visit(stmt.iter, env, mod, stmt)
            for bound in self._iterations(stmt.target, stmt.iter, env, mod):
                scope = {**env, **bound}
                self._bind_statements(stmt.body, scope, mod, record=record)
            self._bind_statements(stmt.orelse, dict(env), mod, record=record)
            return
        if isinstance(stmt, (ast.If, ast.While)):
            self.visit(stmt.test, env, mod, stmt)
            self._bind_statements(stmt.body, env, mod, record=record)
            self._bind_statements(stmt.orelse, env, mod, record=record)
            return
        if isinstance(stmt, (ast.With, ast.AsyncWith)):
            for item in stmt.items:
                self.visit(item.context_expr, env, mod, stmt)
            self._bind_statements(stmt.body, env, mod, record=record)
            return
        if isinstance(stmt, ast.Try):
            for part in (stmt.body, stmt.orelse, stmt.finalbody):
                self._bind_statements(part, env, mod, record=record)
            for handler in stmt.handlers:
                self._bind_statements(handler.body, env, mod, record=record)
            return
        if isinstance(stmt, ast.Return):
            if stmt.value is not None:
                self.visit(stmt.value, env, mod, stmt)
            return
        for child in ast.iter_child_nodes(stmt):
            if isinstance(child, ast.expr):
                self.visit(child, env, mod, stmt)

    def _walks_up_to_root(self, node: ast.expr, env: Mapping[str, object], mod: Module) -> bool:
        """A loop over ``<file path>.parents`` is the repo-root search idiom: its variable is the root."""
        for sub in ast.walk(node):
            if isinstance(sub, ast.Attribute) and sub.attr == "parents" and isinstance(self.ev(sub.value, env, mod), V):
                return True
        return False

    def _import_from(self, stmt: ast.ImportFrom, env: dict[str, object], mod: Module) -> None:
        module = stmt.module or ""
        if stmt.level == 0 and module == "pathlib":
            for alias in stmt.names:
                if alias.name in ("Path", "PurePath", "PosixPath"):
                    mod.path_names.add(alias.asname or alias.name)
            return
        for alias in stmt.names:
            bound = alias.asname or alias.name
            dotted = f"{module}.{alias.name}" if module else alias.name
            if stmt.level == 0 and dotted in _module_prefixes():
                env[bound] = Modref(dotted)
                continue
            if stmt.level == 0 and module in _module_prefixes():
                continue  # code under test, not a path
            other = self._local_module(mod, module, stmt.level)
            if other is None:
                continue
            if alias.name in other.env:
                env[bound] = other.env[alias.name]
            elif alias.name in other.fixtures:
                env[bound] = other.fixtures[alias.name]
            elif alias.name in other.funcs:
                env[bound] = (other, other.funcs[alias.name])

    # -- functions --------------------------------------------------------

    def _param_names(self, func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
        a = func.args
        return [x.arg for x in [*a.posonlyargs, *a.args, *a.kwonlyargs]]

    def _fixture_chain(self, mod: Module) -> list[Module]:
        chain = [mod]
        directory = list(mod.parts[:-1])
        while directory:
            rel = "/".join([*directory, "conftest.py"])
            if rel != mod.rel and rel in _tracked_set():
                other = self.module(rel)
                if other is not None:
                    chain.append(other)
            directory.pop()
        return chain

    def _function(self, func: ast.FunctionDef | ast.AsyncFunctionDef, env: dict[str, object], mod: Module) -> None:
        for dec in func.decorator_list:
            self.visit(dec, env, mod, func)
        scope = dict(env)
        params = self._param_names(func)
        bound: dict[str, list[object]] = {}
        for name in params:
            scope.pop(name, None)
            if name in ("self", "cls"):
                continue
            for owner in self._fixture_chain(mod):
                if name in owner.fixtures:
                    bound[name] = [owner.fixtures[name]]
                    break
        for name, values in self._parametrized(func, env, mod).items():
            if name in params:
                bound[name] = values
        names = list(bound)
        combos = [{}]
        for name in names:
            combos = [{**c, name: v} for c in combos for v in bound[name][:12]][:48]
        for combo in combos:
            local = {**scope, **combo}
            self._bind_statements(func.body, local, mod, record=True)

    def _parametrized(
        self, func: ast.FunctionDef | ast.AsyncFunctionDef, env: dict[str, object], mod: Module
    ) -> dict[str, list[object]]:
        out: dict[str, list[object]] = {}
        for dec in func.decorator_list:
            if not (
                isinstance(dec, ast.Call) and getattr(dec.func, "attr", "") == "parametrize" and len(dec.args) >= 2
            ):
                continue
            names_node = dec.args[0]
            if not (isinstance(names_node, ast.Constant) and isinstance(names_node.value, str)):
                continue
            names = [n.strip() for n in names_node.value.split(",")]
            values = self.ev(dec.args[1], env, mod)
            if not isinstance(values, (list, tuple)):
                continue
            if len(names) == 1:
                out[names[0]] = [v for v in values if isinstance(v, (str, V))]
            else:
                for i, name in enumerate(names):
                    column = [v[i] for v in values if isinstance(v, tuple) and len(v) == len(names)]
                    out[name] = [c for c in column if isinstance(c, (str, V))]
        return {k: v for k, v in out.items() if v}

    def _call_function(
        self,
        func: ast.FunctionDef | ast.AsyncFunctionDef,
        mod: Module,
        bound: Mapping[str, object],
    ) -> object | None:
        """The path or string a helper (or fixture) returns for these argument values, when it is one."""
        key = (mod.rel, func.lineno, tuple(sorted((k, repr(v)) for k, v in bound.items())))
        if key in self._returns:
            return self._returns[key]
        if mod._depth > 4:
            return None
        self._returns[key] = None
        mod._depth += 1
        try:
            scope = dict(mod.env)
            for name in self._param_names(func):
                scope.pop(name, None)
            scope.update(bound)
            self._bind_statements(func.body, scope, mod, record=False)
            result = None
            for node in ast.walk(func):
                if isinstance(node, ast.Return) and node.value is not None:
                    value = self.ev(node.value, scope, mod)
                    if value is not None:
                        result = value
                        break
            self._returns[key] = result
            return result
        finally:
            mod._depth -= 1

    def _resolve_function(
        self, func: ast.expr, env: Mapping[str, object], mod: Module
    ) -> tuple[Module, ast.FunctionDef | ast.AsyncFunctionDef] | None:
        if not isinstance(func, ast.Name):
            return None
        bound = env.get(func.id)
        if (
            isinstance(bound, tuple)
            and len(bound) == 2
            and isinstance(bound[1], (ast.FunctionDef, ast.AsyncFunctionDef))
        ):
            return bound[0], bound[1]
        if bound is None or bound is _UNBOUND:
            local = mod.funcs.get(func.id)
            if local is not None and not _is_fixture(local):
                return mod, local
        return None

    def _bind_arguments(
        self, func: ast.FunctionDef | ast.AsyncFunctionDef, call: ast.Call, env: Mapping[str, object], mod: Module
    ) -> dict[str, object]:
        params = self._param_names(func)
        out: dict[str, object] = {}
        for name, arg in zip(params, call.args, strict=False):
            value = self.ev(arg, env, mod)
            if value is not None:
                out[name] = value
        for kw in call.keywords:
            if kw.arg in params:
                value = self.ev(kw.value, env, mod)
                if value is not None and kw.arg is not None:
                    out[kw.arg] = value
        return out

    def _inline_call(self, node: ast.Call, env: dict[str, object], mod: Module) -> bool:
        """Follow a call into a helper the test module owns, so the reads inside it are seen."""
        target = self._resolve_function(node.func, env, mod)
        if target is None:
            return False
        owner, func = target
        bound = self._bind_arguments(func, node, env, mod)
        key = (owner.rel, func.lineno, tuple(sorted((k, repr(v)) for k, v in bound.items())))
        if key in self._inlined or self._inline_depth >= 3:
            return True
        self._inlined.add(key)
        self._inline_depth += 1
        try:
            scope = dict(owner.env)
            for name in self._param_names(func):
                scope.pop(name, None)
            scope.update(bound)
            self._bind_statements(func.body, scope, owner, record=True)
        finally:
            self._inline_depth -= 1
        return True

    # -- loops ------------------------------------------------------------

    def _iterations(
        self, target: ast.expr, iterable: ast.expr, env: dict[str, object], mod: Module
    ) -> list[dict[str, object]]:
        values = self.ev(iterable, env, mod)
        if not isinstance(values, (list, tuple)) or not values:
            return [{} if not isinstance(target, ast.Name) else {target.id: _UNBOUND}]
        out: list[dict[str, object]] = []
        for item in values[:40]:
            if isinstance(target, ast.Name):
                out.append({target.id: item})
            elif isinstance(target, ast.Tuple) and isinstance(item, tuple) and len(item) == len(target.elts):
                out.append({t.id: v for t, v in zip(target.elts, item, strict=True) if isinstance(t, ast.Name)})
            else:
                out.append({})
        return out or [{}]

    # -- evaluation -------------------------------------------------------

    def ev(self, node: ast.expr | None, env: Mapping[str, object], mod: Module) -> object | None:
        value = self._ev(node, env, mod)
        return None if value is _UNBOUND else value

    def _ev(self, node: ast.expr | None, env: Mapping[str, object], mod: Module) -> object | None:
        if node is None:
            return None
        if isinstance(node, ast.Constant):
            return node.value if isinstance(node.value, str) else None
        if isinstance(node, ast.Name):
            if node.id == "__file__":
                return V(mod.parts)
            return env.get(node.id)
        if isinstance(node, ast.JoinedStr):
            pieces: list[str] = []
            for part in node.values:
                if isinstance(part, ast.Constant):
                    pieces.append(str(part.value))
                elif isinstance(part, ast.FormattedValue):
                    inner = self.ev(part.value, env, mod)
                    if not isinstance(inner, str):
                        return None
                    pieces.append(inner)
            return "".join(pieces)
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            items = [self.ev(e, env, mod) for e in node.elts]
            if any(i is None for i in items):
                return None
            return tuple(items) if isinstance(node, ast.Tuple) else list(items)
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Div):
                left = self.ev(node.left, env, mod)
                if isinstance(left, V):
                    right = self._ev(node.right, env, mod)
                    if isinstance(right, str):
                        return _extend(left, _split_segments(right))
                    if isinstance(right, V) and not right.rooted:
                        return _extend(left, right.parts)
                    return V((*left.parts, WILD), left.rooted)
                return None
            if isinstance(node.op, ast.Add):
                a, b = self.ev(node.left, env, mod), self.ev(node.right, env, mod)
                if isinstance(a, str) and isinstance(b, str):
                    return a + b
                if isinstance(a, list) and isinstance(b, list):
                    return a + b
                return None
            return None
        if isinstance(node, ast.Attribute):
            return self._attribute(node, env, mod)
        if isinstance(node, ast.Subscript):
            base = node.value
            index = node.slice
            if (
                isinstance(base, ast.Attribute)
                and base.attr == "parents"
                and isinstance(index, ast.Constant)
                and isinstance(index.value, int)
                and index.value >= 0
            ):
                path = self.ev(base.value, env, mod)
                if isinstance(path, V) and index.value + 1 <= len(path.parts):
                    return V(path.parts[: len(path.parts) - index.value - 1], path.rooted)
                return None
            seq = self.ev(base, env, mod)
            if isinstance(seq, list) and isinstance(index, ast.Constant) and isinstance(index.value, int):
                try:
                    return seq[index.value]
                except IndexError:
                    return None
            return None
        if isinstance(node, ast.Call):
            return self._call(node, env, mod)
        return None

    def _attribute(self, node: ast.Attribute, env: Mapping[str, object], mod: Module) -> object | None:
        base = self.ev(node.value, env, mod)
        if isinstance(base, V):
            if node.attr == "parent":
                if base.parts:
                    return V(base.parts[:-1], base.rooted)
                return None
            if node.attr == "name" and base.parts and WILD not in base.parts[-1:]:
                return base.parts[-1]
            return None
        if isinstance(base, Modref):
            if node.attr == "__file__":
                file = _module_index().get(base.dotted)
                return V(tuple(file.split("/"))) if file else None
            dotted = f"{base.dotted}.{node.attr}"
            return Modref(dotted) if dotted in _module_prefixes() else None
        return None

    def _call(self, node: ast.Call, env: Mapping[str, object], mod: Module) -> object | None:
        func = node.func
        args = [self.ev(a, env, mod) for a in node.args]
        if isinstance(func, ast.Name):
            if func.id in mod.path_names:
                return self._path_ctor(node, args)
            if func.id in ("str", "fspath") and len(args) == 1 and isinstance(args[0], (V, str)):
                return args[0]
            target = self._resolve_function(func, env, mod)
            if target is not None:
                owner, helper = target
                return self._call_function(helper, owner, self._bind_arguments(helper, node, env, mod))
            return None
        if isinstance(func, ast.Attribute):
            owner_node = func.value
            attr = func.attr
            dotted = _dotted_name(func)
            if dotted in ("os.fspath", "os.path.abspath", "os.path.realpath", "os.path.normpath", "os.path.expanduser"):
                return args[0] if len(args) == 1 and isinstance(args[0], (V, str)) else None
            if dotted == "os.path.dirname" and len(args) == 1 and isinstance(args[0], V):
                a0 = args[0]
                return V(a0.parts[:-1], a0.rooted) if a0.parts else None
            if dotted == "os.path.join" and args and all(isinstance(a, (V, str)) for a in args):
                head = args[0]
                base = head if isinstance(head, V) else V(tuple(_split_segments(str(head))), False)
                return _extend(base, [s for a in args[1:] if isinstance(a, str) for s in _split_segments(a)])
            if dotted == "importlib.import_module" and node.args and isinstance(args[0], str):
                return Modref(args[0]) if args[0] in _module_prefixes() else None
            if dotted in ("pathlib.Path", "pathlib.PurePath"):
                return self._path_ctor(node, args)
            base = self.ev(owner_node, env, mod)
            if isinstance(base, V):
                if attr in ("resolve", "absolute", "expanduser", "as_posix"):
                    return base
                if attr == "joinpath":
                    out: V | None = base
                    for a in args:
                        if out is None:
                            return None
                        out = (
                            _extend(out, _split_segments(a))
                            if isinstance(a, str)
                            else V((*out.parts, WILD), out.rooted)
                        )
                    return out
            return None
        return None

    def _path_ctor(self, node: ast.Call, args: list[object]) -> V | None:
        if not args:
            return None
        head = args[0]
        if isinstance(head, V):
            out: V | None = head
        elif isinstance(head, str):
            if head.startswith("/") or head.startswith("~"):
                return None
            out = V(tuple(_split_segments(head)), False)
        else:
            return None
        for a in args[1:]:
            if out is None:
                return None
            out = _extend(out, _split_segments(a)) if isinstance(a, str) else V((*out.parts, WILD), out.rooted)
        return out

    # -- visiting ---------------------------------------------------------

    def visit(self, node: ast.AST, env: dict[str, object], mod: Module, parent: ast.AST | None) -> None:
        if isinstance(node, ast.expr) and not isinstance(node, (ast.Constant, ast.Lambda)):
            if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
                self._comprehension(node, env, mod)
                return
            value = self.ev(node, env, mod)
            if isinstance(value, V):
                self._record(value, mod, parent)
                return
            if isinstance(node, ast.Call) and self._record_glob(node, env, mod):
                return
            if isinstance(node, ast.Call) and self._inline_call(node, env, mod):
                for arg in node.args:
                    self.visit(arg, env, mod, None)  # the helper's own body decides what the argument reaches
                for kw in node.keywords:
                    self.visit(kw.value, env, mod, None)
                return
            if isinstance(value, (list, tuple)):
                self._record_container(value, mod)
        for child in ast.iter_child_nodes(node):
            self.visit(child, env, mod, node)

    def _record_glob(self, node: ast.Call, env: dict[str, object], mod: Module) -> bool:
        """``base.glob("a/*/b.md")`` reads ``base/a/*/b.md``; ``rglob`` and ``**`` read ``base`` itself."""
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr in ("glob", "rglob") and node.args):
            return False
        base = self.ev(func.value, env, mod)
        pattern = self.ev(node.args[0], env, mod)
        if not (isinstance(base, V) and base.rooted and isinstance(pattern, str)):
            return False
        segments: list[str] = []
        if func.attr == "glob":
            for seg in _split_segments(pattern):
                if seg == "**":
                    break
                segments.append(seg)
            segments = segments if segments and segments[-1] != "**" else segments
        extended = V((*base.parts, *segments), True)
        if not base.parts:
            self.handoffs.add(mod.rel)
        self._record(extended, mod, None)
        return True

    def _comprehension(self, node: ast.AST, env: dict[str, object], mod: Module) -> None:
        generators: list[ast.comprehension] = getattr(node, "generators", [])

        def walk(i: int, scope: dict[str, object]) -> None:
            if i == len(generators):
                elts = [node.key, node.value] if isinstance(node, ast.DictComp) else [getattr(node, "elt")]
                for e in elts:
                    self.visit(e, scope, mod, node)
                return
            gen = generators[i]
            self.visit(gen.iter, scope, mod, node)
            for bound in self._iterations(gen.target, gen.iter, scope, mod):
                inner = {**scope, **bound}
                for cond in gen.ifs:
                    self.visit(cond, inner, mod, node)
                walk(i + 1, inner)

        walk(0, dict(env))

    def _record_container(self, value: object, mod: Module) -> None:
        if isinstance(value, V):
            if value.parts:
                self._record(value, mod, None)
        elif isinstance(value, (list, tuple)):
            for item in value:
                self._record_container(item, mod)

    # -- recording --------------------------------------------------------

    def _record(self, value: V, mod: Module, parent: ast.AST | None) -> None:
        if not value.rooted or _is_plumbing(parent):
            return
        if isinstance(parent, ast.Attribute) and parent.attr == "is_dir":
            return  # a directory's existence is a root-finding probe, not a read of what is under it
        parts = list(value.parts)
        if not parts:
            if self._is_handoff(parent):
                self.handoffs.add(mod.rel)
            return
        while parts and parts[-1] == WILD:
            parts.pop()
        if not parts or parts[0] == WILD:
            return
        self._add_read(tuple(parts), mod.rel)

    @staticmethod
    def _is_handoff(parent: ast.AST | None) -> bool:
        if parent is None:
            return False
        if isinstance(parent, ast.Attribute):
            return parent.attr in ("glob", "rglob", "iterdir")
        return isinstance(parent, (ast.Call, ast.keyword, ast.List, ast.Tuple, ast.Dict, ast.Starred))

    def _add_read(self, parts: tuple[str, ...], source: str) -> None:
        joined = "/".join(parts)
        if self.package_dir and (joined == self.package_dir or joined.startswith(self.package_dir + "/")):
            return
        src_parts = tuple(source.split("/"))
        if self.package_dir and not _within(source, self.package_dir) and parts == src_parts[: len(parts)]:
            return  # an outside test's own directory chain: import-path plumbing, not a read
        if representative(parts) is None:
            return
        self.reads[parts].add(source)

    # -- strings ----------------------------------------------------------

    def scan_strings(self, mod: Module) -> None:
        docstrings: set[int] = set()
        for node in ast.walk(mod.tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                body = node.body
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                    docstrings.add(id(body[0].value))
            if (
                isinstance(node, ast.BinOp)
                and isinstance(node.op, ast.Div)
                and isinstance(node.right, ast.Constant)
                and not (isinstance(node.left, ast.Constant) and isinstance(node.left.value, str))
            ):
                # ``base / "a/b"`` joins onto some other root (a tmp_path, a fixture repo); the
                # evaluator already resolves the ones that join onto the repository root
                docstrings.add(id(node.right))
            if isinstance(node, ast.Call) and _dotted_name(node.func).endswith("parametrize"):
                # a parametrize table holds case labels handed to the code under test, not reads
                docstrings.update(id(n) for n in ast.walk(node))
        for node in ast.walk(mod.tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)) or id(node) in docstrings:
                continue
            text = node.value.strip()
            if not text or any(c in text for c in " \t\n*?[]{}$:\"'`<>|=,;") or text.startswith(("/", "~", "..")):
                continue
            segments = _split_segments(text)
            if len(segments) < 2 or ".." in segments:
                continue
            joined = "/".join(segments)
            if len(segments) < 3 and joined not in _tracked_set():
                continue  # a one- or two-segment directory name is a label (``docs/dreams``), not a read
            if representative(tuple(segments)) is not None:
                self._add_read(tuple(segments), mod.rel)

    def scan(self, rel: str) -> None:
        mod = self.module(rel)
        if mod is None:
            return
        for stmt in mod.tree.body:
            self._scan_top(stmt, mod)
        self.scan_strings(mod)

    def _scan_top(self, stmt: ast.stmt, mod: Module) -> None:
        env = dict(mod.env)
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._function(stmt, env, mod)
        elif isinstance(stmt, ast.ClassDef):
            class_env = dict(env)
            for inner in stmt.body:
                if isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self._function(inner, class_env, mod)
                elif isinstance(inner, (ast.Assign, ast.AnnAssign)):
                    self._statement(inner, class_env, mod, record=True)
        else:
            self._statement(stmt, env, mod, record=True)


_PATH_MATH = frozenset({"relative_to", "is_relative_to", "samefile"})
_IMPORT_PATH_CALLS = frozenset({"sys.path.insert", "sys.path.append", "sys.path.extend", "monkeypatch.syspath_prepend"})


def _is_plumbing(parent: ast.AST | None) -> bool:
    """A path used only to do path arithmetic or to extend the import path is no read of its content."""
    if isinstance(parent, ast.Call):
        func = parent.func
        if isinstance(func, ast.Attribute) and func.attr in _PATH_MATH:
            return True
        return _dotted_name(func) in _IMPORT_PATH_CALLS
    return False


class _Unbound:
    def __repr__(self) -> str:  # pragma: no cover
        return "<unbound>"


_UNBOUND = _Unbound()


def _dotted_name(node: ast.AST) -> str:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


# ---------------------------------------------------------------------------
# The jobs: read from the workflow's ``jobs:`` and ``pixi.toml``, never a hand list
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Job:
    output: str  # the ``changes`` output name that gates it (``atlas``, ``testing_kit``)
    key: str  # the job id (``atlas-test``)
    package: str  # ``src/shared/packages/pyforge-<x>``: the job's own package
    tasks: tuple[tuple[str, str], ...]  # (pixi environment, task) of its ``pixi run`` steps


def workflow_document(workflow_text: str) -> dict:
    return yaml.safe_load(workflow_text)


def load_jobs(workflow_text: str) -> list[Job]:
    jobs: list[Job] = []
    for key, body in workflow_document(workflow_text)["jobs"].items():
        gate = _GATE.search(str(body.get("if", "")))
        if gate is None:
            continue
        tasks: list[tuple[str, str]] = []
        for step in body.get("steps", []):
            m = _PIXI_RUN.search(str(step.get("run", "")))
            if m and m.group(2) != "python":
                tasks.append((m.group(1), m.group(2)))
        envs = {env for env, _ in tasks}
        assert len(envs) == 1, f"{key} runs tasks in {envs}; expected exactly one pixi environment"
        jobs.append(Job(gate.group(1), key, f"{PACKAGES}/{next(iter(envs))}", tuple(tasks)))
    return jobs


def _task_definition(pixi: Mapping, env: str, task: str) -> Mapping | None:
    features = pixi.get("feature", {})
    if task in features.get(env, {}).get("tasks", {}):
        return features[env]["tasks"][task]
    for feature in features.values():
        if task in feature.get("tasks", {}):
            return feature["tasks"][task]
    return pixi.get("tasks", {}).get(task)


def task_commands(pixi: Mapping, env: str, task: str, _seen: frozenset[str] = frozenset()) -> list[str]:
    """The ``cmd`` text of a task and of everything it ``depends-on``."""
    if task in _seen:
        return []
    definition = _task_definition(pixi, env, task) or {}
    cmd = definition.get("cmd", "")
    commands = [" ".join(cmd) if isinstance(cmd, list) else str(cmd)]
    for dep in definition.get("depends-on", []):
        name, dep_env = (dep, env) if isinstance(dep, str) else (dep["task"], dep.get("environment", env))
        commands.extend(task_commands(pixi, dep_env, name, _seen | {task}))
    return commands


def task_paths(pixi: Mapping, job: Job) -> list[str]:
    """Every tracked path named on a job's task command lines (pytest targets, the recipe a smoke builds)."""
    found: list[str] = []
    for env, task in job.tasks:
        for command in task_commands(pixi, env, task):
            for segment in re.split(r"&&|\|\||;", command):
                try:
                    tokens = shlex.split(segment)
                except ValueError:
                    continue
                for token in tokens:
                    if token.startswith("-") or "/" not in token:
                        continue
                    token = token.rstrip("/")
                    if token in _tracked_set() or token in _tracked_dirs():
                        found.append(token)
    return sorted(set(found))


def job_test_files(job: Job, paths: Iterable[str]) -> list[str]:
    files: set[str] = set()
    for path in [f"{job.package}/tests", *paths]:
        if path.endswith(".py") and path in _tracked_set():
            files.add(path)
        else:
            prefix = path.rstrip("/") + "/"
            files.update(p for p in tracked_files() if p.startswith(prefix) and p.endswith(".py"))
    return sorted(files)


@dataclass
class JobReads:
    reads: dict[tuple[str, ...], set[str]] = field(default_factory=dict)  # path pattern -> reading files
    handoffs: set[str] = field(default_factory=set)  # test files handing the bare repo root to code


def _within(path: str, package: str) -> bool:
    return path == package or path.startswith(package + "/")


def derive_reads(job: Job, pixi: Mapping) -> JobReads:
    """What the job's tests (and its pixi task lines) read: the static derivation."""
    paths = task_paths(pixi, job)
    scanner = Scanner(job.package)
    for rel in job_test_files(job, paths):
        if rel != THIS_FILE_REL:  # its own literals are declarations and mutations, not reads
            scanner.scan(rel)
    reads: dict[tuple[str, ...], set[str]] = {k: set(v) for k, v in scanner.reads.items()}
    for path in paths:
        if not _within(path, job.package):
            reads.setdefault(tuple(path.split("/")), set()).add(f"pixi task of {job.key}")
    return JobReads(reads, set(scanner.handoffs))


STEWARD_OWN = "steward-test (this meta-test reads every suite's tests)"


@functools.cache
def real_derivation() -> dict[str, JobReads]:
    pixi = tomllib.loads(PIXI_TOML.read_text(encoding="utf-8"))
    jobs = load_jobs(WORKFLOW.read_text(encoding="utf-8"))
    derived = {job.output: derive_reads(job, pixi) for job in jobs}
    # Its own reads: this meta-test reads every suite's tests, so steward's list carries them -- a
    # station PR that adds an outside read runs steward-test and is caught in that PR.
    own = derived["steward"].reads
    own.setdefault((*PACKAGES.split("/"), "pyforge-*", "tests"), set()).add(STEWARD_OWN)
    for job in jobs:
        for path in task_paths(pixi, job):
            if not _within(path, job.package):
                own.setdefault(tuple(path.split("/")), set()).add(STEWARD_OWN)
    for rel in (WORKFLOW_REL, "pixi.toml"):
        own.setdefault(tuple(rel.split("/")), set()).add(STEWARD_OWN)
    return derived


# ---------------------------------------------------------------------------
# Root handoffs: tests that give the bare repository root to the code under test
# ---------------------------------------------------------------------------
# A test that passes the repo root to a gatherer, a generator, ``subprocess.run`` or
# ``monkeypatch.chdir`` reads whatever that code reads, and a scan of the test cannot see it.
# Each such file is declared per job with the globs the code reads from the root and why. The
# derived set of handoff files must equal the declared keys (so a new live-tree test fails until
# it is declared, and a stale declaration fails too); every declared glob goes through the same
# fire check as a derived read. A declaration only adds inputs.

_PLAN = ("_bmad-output/projects/*/planning-artifacts/**", "_bmad-output/projects/*/README.md")
_PYTHON_TREES = ("src/**", "scripts/**", ".claude/scripts/**")

# group -> (globs the code under test reads from the root, why)
_H: dict[str, tuple[tuple[str, ...], str]] = {
    "GIT_PLATFORM_DIFF": (
        ("src/platform/**",),
        "changed_paths_since + pyforge_import_offenders diff src/platform against origin/main and read the changed files",
    ),
    "SKF_SKILL_TREE": (
        ("src/platform/**", ".claude/skills/**", "_bmad/skf/**"),
        "the required-skill-file check, unsanctioned_commits history and the platform import diff",
    ),
    "ATLAS_PACKAGING_DOCS": (
        ("docs/reference/**",),
        "the metrics CLI run from the root resolved its retired default output to the tracked prompt doc",
    ),
    "GITIGNORE_STATE": (
        (".gitignore",),
        "`git check-ignore` answers from the root's ignore rules",
    ),
    "GITIGNORE_SKILLS": (
        (".gitignore", ".claude/skills/**"),
        "`git check-ignore` / `git ls-files` over the skill tree answer from the root's ignore rules",
    ),
    "ATLAS_GIST_RECIPES": (
        ("recipes/**",),
        "the identity gist export classifies every recipe directory under repo_root/recipes",
    ),
    "DOCTOR_WHOLE_CHECK": (
        ("docs/dreams/**", "docs/governance/**", "archive/**", "pixi.toml", ".claude/skills/**", *_PLAN),
        "`doctor check <root>` runs every registered source over the live tree",
    ),
    "PYTHON_SOURCES": (_PYTHON_TREES, "env_hygiene discovers every python file under the root"),
    "BMAD_SUITE_PINS": (
        ("recipes/bmad-suite/suite-members.yaml", "pixi.toml", "_bmad/**"),
        "the bmad-method source reads the suite roster and the pixi floor from the root",
    ),
    "DOCTOR_BOARD": (
        (*_PLAN, "docs/dreams/**", "docs/governance/**", "docs/dashboard/**"),
        "the board gatherers read every spec, PRD and dream and the dashboard generator under the root",
    ),
    "DOCTOR_CALLER_REACH": (
        (*_PLAN, ".claude/skills/**", "docs/dreams/**"),
        "gather_caller_reach walks the planning artifacts and skills for capability callers",
    ),
    "DOCS_DIATAXIS": (
        ("docs/explanation/**", "docs/how-to/**"),
        "docs_shelf checks the named explanation and how-to pages under the root",
    ),
    "DOCTOR_FACTORY": (
        (*_PLAN, "pixi.toml"),
        "the factory source reads the marshal planning files and counts environments in pixi.toml",
    ),
    "DOCS_ALL": (
        ("docs/dreams/**", "docs/governance/**", "docs/how-to/**", "docs/reference/**", "docs/explanation/**"),
        "general_docs_consistency reads the documentation tree under the root",
    ),
    "DOCTOR_PLANNING_AND_DOCS": (
        (*_PLAN, "docs/dreams/**", "docs/governance/**", "archive/**", "recipes/*/recipe.yaml"),
        "the hygiene gatherer reads the sprint ledgers, dreams and recipes under the root",
    ),
    "DOCTOR_CHAIN": (
        (*_PLAN, "docs/dreams/**", "docs/governance/**", "archive/**", "recipes/*/recipe.yaml"),
        "the chain, one-chain and status-body gatherers read every dream, spec, ledger and recipe under the root",
    ),
    "PLANNING": (_PLAN, "the gatherer reads the planning artifacts of every project under the root"),
    "PRESENTATIONS": (
        ("presentations/**",),
        "the deck helpers read presentations/ (exports, Marp sources, the Modernist design system)",
    ),
    "DOCS_SITE": (
        ("docs-site/**", "docsite/**"),
        "the docs-site and docsite checks list and read their trees from the root",
    ),
    "MARSHAL_CODE_LINKAGE": (
        (*_PLAN, "docs/dreams/**", "src/shared/packages/pyforge-marshal/**"),
        "verify_code_linkage reads marshal's epics, spec and code",
    ),
    "PLANNING_SPECS_TRACKED": (
        ("_bmad-output/projects/*/planning-artifacts/specs/**",),
        "`git ls-files` at the root, then the tracked story specs' frontmatter",
    ),
    "HARNESS_PROFILES": (
        ("_bmad-output/harness-profiles/*.toml",),
        "load_profiles overlays <root>/_bmad-output/harness-profiles/*.toml",
    ),
    "ADOPT_MANIFEST_TREE": (
        ("AGENTS.md", "CLAUDE.md", ".claude/**", ".cursor/**", ".gemini/**", ".github/copilot-instructions.md"),
        "run_adopt plans the instruction-surface files it would write into the root",
    ),
    "LIVE_KEYCLOAK": (
        ("src/platform/**",),
        "the live Keycloak login proof runs the platform stack from the root (skipped without the server)",
    ),
    "TEA_GENERATOR": (
        (*_PLAN, "src/shared/packages/pyforge-*/tests/**", "_bmad/**"),
        "the test-architecture generator's live-tree smoke reads every station's epics.md and tests",
    ),
    "ADOPTION_PIPELINE": (
        (*_PLAN, "recipes/bmad-suite/**", ".claude/skills/**", "_bmad/**", "pixi.toml"),
        "build_pipeline_truth_report walks the suite roster, installed skills and planning records",
    ),
    "BOOTSTRAP_INPUTS": (
        ("pixi.toml", ".pre-commit-config.yaml", ".github/workflows/*.yml"),
        "the bootstrap prerequisites and setup steps read the pixi floor, hooks and workflows from the root",
    ),
    "FIVE_TIER": (
        ("docs/dreams/**", "docs/governance/**", "AGENTS.md", *_PLAN),
        "the five-tier check reads dreams, governance and the planning tiers",
    ),
    "FRAMES": (
        ("docs/foundry/**", "docs/dreams/**", *_PLAN),
        "preflight_frames reads the foundry frames, dreams and specs",
    ),
    "CLASS_PATH": (
        ("pixi.toml", ".claude/skills/**", "_bmad/**", "recipes/bmad-suite/**", ".claude/settings.json"),
        "probe_wired inspects the suite members' install class on the root",
    ),
    "PIXI_AND_WORKFLOWS": (
        ("pixi.toml", ".github/workflows/*.yml", ".pre-commit-config.yaml"),
        "the preflight scratch and suite-reduction code read pixi tasks and workflows from the root",
    ),
    "STEWARD_SESSION": (
        ("pixi.toml", "_bmad/**", ".claude/skills/**", "recipes/bmad-suite/**", ".pre-commit-config.yaml"),
        "the session start gatherers read the bmad estate and hooks from the root",
    ),
}

ROOT_HANDOFF_INPUTS: dict[str, dict[str, tuple[tuple[str, ...], str]]] = {
    "atlas": {
        "scripts/tests/test_conda_forge_packaging_inventory_operations_metrics.py": _H["ATLAS_PACKAGING_DOCS"],
        "src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_identity_gist_markdown.py": _H[
            "ATLAS_GIST_RECIPES"
        ],
        "src/shared/packages/pyforge-atlas/tests/meta/test_skf_skill_and_persona.py": _H["SKF_SKILL_TREE"],
        "src/shared/packages/pyforge-atlas/tests/unit/catalog/test_credential_scoping.py": _H["GITIGNORE_STATE"],
    },
    "doctor": {
        "src/shared/packages/pyforge-doctor/tests/meta/test_portal_fleet_pulse.py": _H["GIT_PLATFORM_DIFF"],
        "src/shared/packages/pyforge-doctor/tests/meta/test_skf_domain_skill.py": _H["SKF_SKILL_TREE"],
        "src/shared/packages/pyforge-doctor/tests/meta/test_station_persona.py": _H["GIT_PLATFORM_DIFF"],
        "src/shared/packages/pyforge-doctor/tests/unit/test_check_speed_budget.py": _H["DOCTOR_WHOLE_CHECK"],
        "src/shared/packages/pyforge-doctor/tests/unit/test_checks_env_hygiene.py": _H["PYTHON_SOURCES"],
        "src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py": _H["BMAD_SUITE_PINS"],
        "src/shared/packages/pyforge-doctor/tests/unit/test_sources_board.py": _H["DOCTOR_BOARD"],
        "src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_chain_layers_audit.py": _H["DOCTOR_BOARD"],
        "src/shared/packages/pyforge-doctor/tests/unit/test_sources_capability_effect_caller_reach.py": _H[
            "DOCTOR_CALLER_REACH"
        ],
        "src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py": _H["DOCTOR_CHAIN"],
        "src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dreams_hygiene.py": _H["DOCTOR_CHAIN"],
        "src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py": _H["DOCTOR_CHAIN"],
        "src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_source_spec_resolution.py": _H[
            "DOCTOR_CHAIN"
        ],
        "src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_shelf.py": _H["DOCS_DIATAXIS"],
        "src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py": _H["DOCTOR_FACTORY"],
        "src/shared/packages/pyforge-doctor/tests/unit/test_sources_general_docs_consistency.py": _H["DOCS_ALL"],
        "src/shared/packages/pyforge-doctor/tests/unit/test_sources_hygiene.py": _H["DOCTOR_PLANNING_AND_DOCS"],
        "src/shared/packages/pyforge-doctor/tests/unit/test_sources_live_proof_surfaces.py": _H["PLANNING"],
        "src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain.py": _H["DOCTOR_CHAIN"],
        "src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fold_complete.py": _H["DOCTOR_CHAIN"],
        "src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_consistency.py": _H["DOCTOR_CHAIN"],
        "src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_open_questions.py": _H["DOCTOR_CHAIN"],
        "src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_promissory.py": _H["DOCTOR_CHAIN"],
        "src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_status_comment.py": _H["DOCTOR_CHAIN"],
    },
    "herald": {
        "src/shared/packages/pyforge-herald/tests/meta/test_deck_working_set.py": _H["PRESENTATIONS"],
        "src/shared/packages/pyforge-herald/tests/meta/test_docs_site_imports_tracked.py": _H["DOCS_SITE"],
        "src/shared/packages/pyforge-herald/tests/meta/test_docsite_zero_origin.py": _H["DOCS_SITE"],
        "src/shared/packages/pyforge-herald/tests/meta/test_pptx_native_live_decks.py": _H["PRESENTATIONS"],
        "src/shared/packages/pyforge-herald/tests/meta/test_skf_skill_and_persona.py": _H["SKF_SKILL_TREE"],
        "src/shared/packages/pyforge-herald/tests/meta/test_twins_zero_origin.py": _H["PRESENTATIONS"],
        "src/shared/packages/pyforge-herald/tests/unit/test_pptx_native.py": _H["PRESENTATIONS"],
    },
    "marshal": {
        "src/shared/packages/pyforge-marshal/tests/integration/test_local_recipes_empty_plan.py": _H[
            "ADOPT_MANIFEST_TREE"
        ],
        "src/shared/packages/pyforge-marshal/tests/integration/test_login_pkce_live_keycloak.py": _H["LIVE_KEYCLOAK"],
        "src/shared/packages/pyforge-marshal/tests/meta/test_27_2_portal_loop_homes.py": _H["GIT_PLATFORM_DIFF"],
        "src/shared/packages/pyforge-marshal/tests/meta/test_kit_artifacts_ignored_not_the_tracked_skills.py": _H[
            "GITIGNORE_SKILLS"
        ],
        "src/shared/packages/pyforge-marshal/tests/meta/test_rendered_policy_untracked.py": _H["GITIGNORE_STATE"],
        "src/shared/packages/pyforge-marshal/tests/meta/test_skf_domain_skill.py": _H["SKF_SKILL_TREE"],
        "src/shared/packages/pyforge-marshal/tests/meta/test_skill_projection_manifest_untracked.py": _H[
            "GITIGNORE_SKILLS"
        ],
        "src/shared/packages/pyforge-marshal/tests/meta/test_station_persona.py": _H["GIT_PLATFORM_DIFF"],
        "src/shared/packages/pyforge-marshal/tests/meta/test_tea_architecture_drift.py": _H["TEA_GENERATOR"],
        "src/shared/packages/pyforge-marshal/tests/meta/test_tea_architecture_generator.py": _H["TEA_GENERATOR"],
        "src/shared/packages/pyforge-marshal/tests/meta/test_wire_store_ignored_not_the_seed_namespace.py": _H[
            "GITIGNORE_STATE"
        ],
        "src/shared/packages/pyforge-marshal/tests/unit/test_chain_regen.py": _H["MARSHAL_CODE_LINKAGE"],
        "src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_spec_frontmatter.py": _H[
            "PLANNING_SPECS_TRACKED"
        ],
        "src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification.py": _H["HARNESS_PROFILES"],
        "src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verify_fix.py": _H["HARNESS_PROFILES"],
    },
    "mason": {
        "src/shared/packages/pyforge-mason/tests/meta/test_persona_consults_cfe.py": _H["GIT_PLATFORM_DIFF"],
        "src/shared/packages/pyforge-mason/tests/meta/test_portal_last_diagnose.py": _H["GIT_PLATFORM_DIFF"],
        "src/shared/packages/pyforge-mason/tests/meta/test_skf_mason_skill.py": _H["SKF_SKILL_TREE"],
    },
    "scribe": {
        "src/shared/packages/pyforge-scribe/tests/meta/test_first_portal_slice.py": _H["GIT_PLATFORM_DIFF"],
        "src/shared/packages/pyforge-scribe/tests/meta/test_skf_skill_ownership.py": _H["GIT_PLATFORM_DIFF"],
        "src/shared/packages/pyforge-scribe/tests/meta/test_station_persona.py": _H["GIT_PLATFORM_DIFF"],
    },
    "steward": {
        "src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py": _H["ADOPTION_PIPELINE"],
        "src/shared/packages/pyforge-steward/tests/meta/test_first_portal_slice_provision_list.py": _H[
            "GIT_PLATFORM_DIFF"
        ],
        "src/shared/packages/pyforge-steward/tests/meta/test_five_tier_check.py": _H["FIVE_TIER"],
        "src/shared/packages/pyforge-steward/tests/meta/test_skf_domain_skills.py": _H["SKF_SKILL_TREE"],
        "src/shared/packages/pyforge-steward/tests/meta/test_skf_steward_skill.py": _H["GIT_PLATFORM_DIFF"],
        "src/shared/packages/pyforge-steward/tests/meta/test_station_persona.py": _H["GIT_PLATFORM_DIFF"],
        "src/shared/packages/pyforge-steward/tests/meta/test_steward_persona.py": _H["GIT_PLATFORM_DIFF"],
        "src/shared/packages/pyforge-steward/tests/unit/test_bootstrap.py": _H["BOOTSTRAP_INPUTS"],
        "src/shared/packages/pyforge-steward/tests/unit/test_bootstrap_setup.py": _H["BOOTSTRAP_INPUTS"],
        "src/shared/packages/pyforge-steward/tests/unit/test_bootstrap_setup_flow.py": _H["BOOTSTRAP_INPUTS"],
        "src/shared/packages/pyforge-steward/tests/unit/test_frame_preflight.py": _H["FRAMES"],
        "src/shared/packages/pyforge-steward/tests/unit/test_fresh_clone_class_path.py": _H["CLASS_PATH"],
        "src/shared/packages/pyforge-steward/tests/unit/test_preflight_scratch.py": _H["PIXI_AND_WORKFLOWS"],
        "src/shared/packages/pyforge-steward/tests/unit/test_preflight_suite_reduction.py": _H["PIXI_AND_WORKFLOWS"],
        "src/shared/packages/pyforge-steward/tests/unit/test_session.py": _H["STEWARD_SESSION"],
        "src/shared/packages/pyforge-steward/tests/unit/test_estate.py": (
            ("docs/governance/guild-roster.json", ".claude/hooks/pre-shell.py"),
            "Story 100.2 AC4: estate transitive denial row and hook matcher parity",
        ),
        "src/shared/packages/pyforge-steward/tests/unit/test_estate_realize.py": (
            (
                "docs/governance/guild-roster.json",
                ".claude/hooks/pre-shell.py",
                "docs/governance/realization-register.yaml",
            ),
            "Story 100.5: estate realize and realization register",
        ),
        "src/shared/packages/pyforge-steward/tests/unit/test_sprint_ledger_query.py": _H["PLANNING"],
        "src/shared/packages/pyforge-steward/tests/unit/test_suite_wired_class_predicates.py": _H["CLASS_PATH"],
    },
    "warden": {
        "src/shared/packages/pyforge-warden/tests/meta/test_portal_audit_start_get.py": _H["GIT_PLATFORM_DIFF"],
        "src/shared/packages/pyforge-warden/tests/meta/test_skf_domain_skill.py": _H["SKF_SKILL_TREE"],
        "src/shared/packages/pyforge-warden/tests/meta/test_station_persona.py": _H["GIT_PLATFORM_DIFF"],
    },
}


# ---------------------------------------------------------------------------
# Reads -> workflow entries, and the workflow's own arrays
# ---------------------------------------------------------------------------

# The shared surface fires every job; it is not in any job's array.
SHARED_ENTRIES = (
    "src/shared/packages/pyforge-core",
    "src/shared/packages/pyforge-testing-kit",
    "pixi.toml",
    "pixi.lock",
    WORKFLOW_REL,
)

HANDOFF_SOURCE = "ROOT_HANDOFF_INPUTS"


def glob_parts(glob: str) -> tuple[str, ...]:
    """``a/*/b/**`` -> ``('a', '*', 'b')``: a trailing ``**`` names the directory itself."""
    parts = glob.split("/")
    if parts[-1] == "**":
        parts = parts[:-1]
    return tuple(parts)


def is_file_pattern(parts: Sequence[str]) -> bool:
    """The pattern names tracked files (not directories)."""
    if not any(_has_glob(p) for p in parts):
        return "/".join(parts) in _tracked_set()
    n = len(parts)
    return any(
        len(segs := path.split("/")) == n and all(_segment_match(p, s) for p, s in zip(parts, segs, strict=True))
        for path in tracked_files()
    )


def to_pathspec(parts: Sequence[str]) -> str:
    """The git pathspec the ``changes`` script carries for a read: a wildcard directory needs ``/*``."""
    path = "/".join(parts)
    if any(_has_glob(p) for p in parts) and not is_file_pattern(parts):
        return path + "/*"
    return path


def to_trigger_glob(entry: str) -> str:
    """The ``on.pull_request.paths`` glob for an array entry (GitHub's ``*`` stops at ``/``)."""
    if entry.endswith("/*"):
        return entry[:-1] + "**"
    parts = tuple(entry.split("/"))
    if is_file_pattern(parts):
        return entry
    return entry + "/**"


def job_reads_with_handoffs(output: str) -> dict[tuple[str, ...], set[str]]:
    """Derived reads plus the declared root-handoff globs, minus the job's own package."""
    derivation = real_derivation()[output]
    reads = {k: set(v) for k, v in derivation.reads.items()}
    package = next(j.package for j in load_jobs(WORKFLOW.read_text(encoding="utf-8")) if j.output == output)
    for file, (globs, _reason) in ROOT_HANDOFF_INPUTS.get(output, {}).items():
        for glob in globs:
            parts = glob_parts(glob)
            if not _within("/".join(parts), package):
                reads.setdefault(parts, set()).add(f"{HANDOFF_SOURCE}[{file}]")
    return reads


def _covers(broad: Sequence[str], narrow: Sequence[str]) -> bool:
    return len(broad) <= len(narrow) and all(_segment_match(b, n) for b, n in zip(broad, narrow, strict=False))


def minimal_entries(reads: Iterable[Sequence[str]], pinned: Iterable[Sequence[str]] = ()) -> list[tuple[str, ...]]:
    """Drop a read another read already covers as a directory; keep every pinned read."""
    items = sorted({tuple(r) for r in reads} | {tuple(p) for p in pinned}, key=lambda t: (len(t), t))
    keep: list[tuple[str, ...]] = []
    for item in items:
        if any(_covers(k, item) and not is_file_pattern(k) for k in keep):
            continue
        keep.append(item)
    return keep


_ARRAY = re.compile(r"^[ \t]*(\w+)_paths=\(\n(.*?)^[ \t]*\)[ \t]*$", re.MULTILINE | re.DOTALL)
_SHARED_BLOCK = re.compile(r'git diff --quiet "\$BASE"\.\.\.HEAD -- \\\n(.*?)2>/dev/null; then', re.DOTALL)


def workflow_arrays(workflow_text: str) -> dict[str, list[str]]:
    """The per-job pathspec arrays in the ``changes`` script, by job output name."""
    return {m.group(1): shlex.split(m.group(2), comments=True) for m in _ARRAY.finditer(workflow_text)}


def trigger_paths(workflow_text: str, event: str = "pull_request") -> list[str]:
    triggers = workflow_document(workflow_text)[True]
    return list(triggers[event]["paths"])


def without_array_entry(workflow_text: str, output: str, entry: str) -> str:
    """A copy of the workflow with one entry removed from one job's array."""
    match = next(m for m in _ARRAY.finditer(workflow_text) if m.group(1) == output)
    kept: list[str] = []
    removed = 0
    for line in match.group(2).splitlines(keepends=True):
        if shlex.split(line, comments=True) == [entry]:
            removed += 1
        else:
            kept.append(line)
    assert removed == 1, f"mutation premise: {entry!r} is one line of the {output} array (found {removed})"
    return workflow_text[: match.start(2)] + "".join(kept) + workflow_text[match.end(2) :]


def without_trigger(workflow_text: str, glob: str) -> str:
    """A copy of the workflow with one glob removed from ``on.pull_request.paths`` only."""
    head, sep, tail = workflow_text.partition("  push:\n")
    needle = f"      - '{glob}'\n"
    assert needle in head, f"mutation premise: {glob!r} is a pull_request path"
    return head.replace(needle, "", 1) + sep + tail


# ---------------------------------------------------------------------------
# Does the workflow fire? A fixture repository per representative path
# ---------------------------------------------------------------------------

OUTPUTS = ("core", "testing_kit", "atlas", "doctor", "herald", "marshal", "mason", "scribe", "steward", "warden")
STATIONS = OUTPUTS[2:]
_WORKERS = 8


def expand_roots(parts: tuple[str, ...]) -> list[tuple[str, ...]]:
    """``src`` and ``src/shared/packages`` are enumerated, never one glob: each package is a trigger."""
    if parts not in {("src",), ("src", "shared", "packages")}:
        return [parts]
    depth = len(parts) + 1
    prefixes = sorted(
        {
            tuple(segs[:depth])
            for path in tracked_files()
            if (segs := path.split("/"))[: len(parts)] == list(parts) and len(segs) > depth
        }
    )
    out: list[tuple[str, ...]] = []
    for prefix in prefixes:
        out.extend(expand_roots(("src", "shared", "packages")) if prefix == ("src", "shared") else [prefix])
    return out


@dataclass(frozen=True)
class Target:
    job: str
    parts: tuple[str, ...]
    sources: tuple[str, ...]
    rep: str

    @property
    def read(self) -> str:
        return "/".join(self.parts)


@functools.cache
def real_targets() -> tuple[Target, ...]:
    out: list[Target] = []
    for output in OUTPUTS:
        for parts, sources in sorted(job_reads_with_handoffs(output).items()):
            for expanded in expand_roots(parts):
                rep = representative(expanded)
                if rep is not None:
                    out.append(Target(output, expanded, tuple(sorted(sources))[:2], rep))
    return tuple(out)


def _changes_script(workflow_text: str) -> str:
    steps = workflow_document(workflow_text)["jobs"]["changes"]["steps"]
    script = next(s["run"] for s in steps if "run" in s)
    return script.replace("${{ github.event_name }}", "pull_request")


def _git(cwd: Path, *args: str, stdin: bytes | None = None) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd,
        input=stdin,
        check=True,
        capture_output=True,
    )
    return done.stdout.decode().strip()


def _quote(path: str) -> str:
    return '"' + path.replace("\\", "\\\\").replace('"', '\\"') + '"'


def run_changes(workflow_text: str, paths: Iterable[str]) -> dict[str, dict[str, str]]:
    """The ``changes`` step's own shell, run against one fixture diff per path.

    The base is ``refs/remotes/origin/main`` (an empty commit); each path is a one-file commit on
    top of it, selected by pointing ``HEAD`` at it, so a thousand diffs cost a thousand diffs and
    not a thousand clones."""
    ordered = sorted(set(paths))
    script = _changes_script(workflow_text)
    results: dict[str, dict[str, str]] = {}
    with tempfile.TemporaryDirectory(prefix="station-trigger-map-") as tmp:
        template = Path(tmp) / "template"
        template.mkdir()
        _git(template, "init", "-q")
        base = _git(template, "commit-tree", _git(template, "hash-object", "-t", "tree", "/dev/null"), "-m", "base")
        _git(template, "update-ref", BASE_REF, base)
        stream = ["blob", "mark :1", "data 2", "x", ""]
        for i, path in enumerate(ordered):
            stream += [f"commit refs/heads/p{i}", "committer t <t@t> 0 +0000", "data 2", "c", f"from {base}"]
            stream += [f"M 100644 :1 {_quote(path)}", ""]
        _git(template, "fast-import", "--quiet", stdin=("\n".join(stream) + "\n").encode())
        chunks = [list(enumerate(ordered))[k::_WORKERS] for k in range(_WORKERS)]

        def work(k: int) -> dict[str, dict[str, str]]:
            repo = Path(tmp) / f"w{k}"
            shutil.copytree(template, repo)
            out_file = repo / "gh-output"
            env = {**os.environ, "GITHUB_BASE_REF": "main", "GITHUB_OUTPUT": str(out_file)}
            done: dict[str, dict[str, str]] = {}
            for i, path in chunks[k]:
                _git(repo, "symbolic-ref", "HEAD", f"refs/heads/p{i}")
                out_file.write_text("", encoding="utf-8")
                subprocess.run(["bash", "-e", "-c", script], cwd=repo, env=env, check=True, capture_output=True)
                lines = out_file.read_text(encoding="utf-8").splitlines()
                done[path] = dict(line.split("=", 1) for line in lines if "=" in line)
            return done

        with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
            for part in pool.map(work, range(_WORKERS)):
                results.update(part)
    return results


def fire_failures(workflow_text: str, targets: Sequence[Target]) -> list[str]:
    """One message per (job, read) whose representative path does not fire the job, naming the half."""
    outputs = run_changes(workflow_text, {t.rep for t in targets})
    patterns = trigger_paths(workflow_text)
    failures: list[str] = []
    for t in targets:
        who = f"{t.job}: read `{t.read}` (from {', '.join(t.sources)}); representative path `{t.rep}`"
        if outputs[t.rep].get(t.job) != "true":
            failures.append(f"{who}: the `changes` step left output `{t.job}` false")
        if not preflight_ci.filter_matches(patterns, t.rep):
            failures.append(f"{who}: on.pull_request.paths does not match it")
    return failures


def handoff_problems(
    derived: Mapping[str, set[str]], declared: Mapping[str, Mapping[str, tuple[tuple[str, ...], str]]]
) -> list[str]:
    problems: list[str] = []
    for job in sorted(set(derived) | set(declared)):
        have, want = derived.get(job, set()), set(declared.get(job, {}))
        problems.extend(
            f"{job}: `{f}` hands the repo root to the code under test and is not in ROOT_HANDOFF_INPUTS"
            for f in sorted(have - want)
        )
        problems.extend(
            f"{job}: ROOT_HANDOFF_INPUTS names `{f}`, which hands no repo root to anything" for f in sorted(want - have)
        )
        for f, (globs, reason) in sorted(declared.get(job, {}).items()):
            if not globs or not reason.strip():
                problems.append(f"{job}: ROOT_HANDOFF_INPUTS[`{f}`] needs at least one glob and a reason")
    return problems


def derived_handoffs() -> dict[str, set[str]]:
    return {output: set(r.handoffs) for output, r in real_derivation().items()}


# ---------------------------------------------------------------------------
# The tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_the_ten_jobs_are_read_from_the_workflow_not_listed(workflow_text: str) -> None:
    jobs = load_jobs(workflow_text)
    assert sorted(j.output for j in jobs) == sorted(OUTPUTS)
    pixi = tomllib.loads(PIXI_TOML.read_text(encoding="utf-8"))
    by_output = {j.output: j for j in jobs}
    assert any(p.endswith("test_openteams_handoffs.py") for p in task_paths(pixi, by_output["atlas"]))
    assert any(p.endswith("test_cli_tool_parity.py") for p in task_paths(pixi, by_output["mason"]))
    assert "scripts/tests" in task_paths(pixi, by_output["atlas"])


def test_every_job_but_the_kit_has_a_path_array(workflow_text: str) -> None:
    assert sorted(workflow_arrays(workflow_text)) == sorted(set(OUTPUTS) - {"testing_kit"})
    for output, entries in workflow_arrays(workflow_text).items():
        assert entries, f"{output}_paths is empty"
        assert len(entries) == len(set(entries)), f"{output}_paths repeats an entry"


def test_the_pull_request_and_push_path_lists_are_identical(workflow_text: str) -> None:
    assert trigger_paths(workflow_text, "pull_request") == trigger_paths(workflow_text, "push")


def test_the_changes_script_is_valid_bash_and_the_workflow_is_valid_yaml(workflow_text: str, tmp_path: Path) -> None:
    assert isinstance(workflow_document(workflow_text), dict)
    script = tmp_path / "changes.sh"
    script.write_text(_changes_script(workflow_text), encoding="utf-8")
    done = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr


# --- AC2: the derivation is not blind ---------------------------------------

DERIVED_ROWS = {
    "steward": [
        "scripts/lint_types.py",
        ".github/workflows/lint-types.yml",
        "src/shared/packages/django-herald/pyproject.toml",
        "src/shared/packages/django-steward",
    ],
    "herald": ["src/shared/packages/django-herald", "src/shared/packages/pyforge-steward/src"],
    "atlas": ["src/platform/config/flags.json", "src/shared/packages/pyforge-scribe/src"],
    "doctor": ["scripts/fleet_scan.py", "src/shared/packages/django-pyforge/src"],
    "marshal": ["scripts/fleet_picture.py"],
    "mason": ["scripts/cfe_rebuild_guard_check.py"],
    "scribe": ["src/platform/db/changelog/changes"],
    "warden": ["src/shared/packages/django-warden"],
    "testing_kit": ["src/platform/config/flags.json"],
}
PLANNING_ROWS = {
    "doctor": [
        "_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md",
        "_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md",
    ],
    "marshal": [
        "_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml",
        ".claude/memory/MEMORY.md",
    ],
    "herald": [
        "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/case-list.md"
    ],
    "atlas": ["recipes"],
}


def _derived_covers(output: str, row: str, *, declared: bool) -> bool:
    reads = job_reads_with_handoffs(output) if declared else real_derivation()[output].reads
    want = tuple(row.split("/"))
    return any(_covers(read, want) or _covers(want, read) for read in reads)


@pytest.mark.parametrize(("output", "row"), [(o, r) for o, rows in DERIVED_ROWS.items() for r in rows])
def test_the_derivation_finds_each_known_read(output: str, row: str) -> None:
    assert _derived_covers(output, row, declared=False), f"{output}: the derivation lost the read of `{row}`"


def test_the_derivation_finds_a_core_read_under_scripts() -> None:
    assert any(read[0] == "scripts" for read in real_derivation()["core"].reads)


@pytest.mark.parametrize(("output", "row"), [(o, r) for o, rows in PLANNING_ROWS.items() for r in rows])
def test_planning_reads_are_derived_or_declared(output: str, row: str) -> None:
    assert _derived_covers(output, row, declared=True), f"{output}: nothing reads or declares `{row}`"


def test_the_steward_job_reads_every_suites_tests() -> None:
    assert any(read[-2:] == ("pyforge-*", "tests") for read in real_derivation()["steward"].reads), (
        "steward's own reads lost src/shared/packages/pyforge-*/tests"
    )


# --- AC3: every read fires its job ------------------------------------------


def test_every_read_and_declared_glob_fires_its_job(workflow_text: str) -> None:
    targets = real_targets()
    assert len(targets) > 300, f"only {len(targets)} targets: the derivation went blind"
    failures = fire_failures(workflow_text, targets)
    assert not failures, f"{len(failures)} reads do not fire their job:\n" + "\n".join(failures)


# --- AC1: the portal packages -----------------------------------------------


def test_every_django_package_fires_steward_and_its_own_station(workflow_text: str) -> None:
    packages = sorted({p.split("/")[3] for p in tracked_files() if p.startswith(f"{PACKAGES}/django-")})
    assert {f"django-{s}" for s in STATIONS} <= set(packages)
    reps = {pkg: next(p for p in tracked_files() if p.startswith(f"{PACKAGES}/{pkg}/")) for pkg in packages}
    outputs = run_changes(workflow_text, reps.values())
    patterns = trigger_paths(workflow_text)
    for pkg, rep in reps.items():
        assert outputs[rep]["steward"] == "true", f"{rep} does not fire steward"
        assert preflight_ci.filter_matches(patterns, rep), f"on.pull_request.paths does not match {rep}"
        station = pkg.removeprefix("django-")
        if station in STATIONS:
            assert outputs[rep][station] == "true", f"{rep} does not fire {station}"


# --- AC4: root handoffs are declared -----------------------------------------


def test_root_handoffs_are_declared_exactly() -> None:
    assert handoff_problems(derived_handoffs(), ROOT_HANDOFF_INPUTS) == []


def test_the_handoff_floor() -> None:
    derived = derived_handoffs()
    pkg = f"{PACKAGES}/pyforge-doctor/tests/unit"
    assert {f"{pkg}/test_sources_chain_dreams_hygiene.py", f"{pkg}/test_sources_board.py"} <= derived["doctor"]
    assert f"{PACKAGES}/pyforge-marshal/tests/meta/test_tea_architecture_generator.py" in derived["marshal"]


def _declared_globs(job: str) -> list[str]:
    return [g for globs, _ in ROOT_HANDOFF_INPUTS[job].values() for g in globs]


@pytest.mark.parametrize(
    ("job", "sample"),
    [
        ("doctor", "docs/dreams/a-dream.md"),
        ("doctor", "_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md"),
        ("doctor", "archive/_bmad-output/x.md"),
        ("marshal", "_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md"),
        ("marshal", f"{PACKAGES}/pyforge-atlas/tests/unit/test_x.py"),
    ],
)
def test_the_minimum_declarations_are_present(job: str, sample: str) -> None:
    assert preflight_ci.filter_matches(_declared_globs(job), sample), f"{job} declares nothing that matches {sample}"


def test_every_declared_glob_has_a_tracked_representative() -> None:
    for job, files in ROOT_HANDOFF_INPUTS.items():
        for file, (globs, _reason) in files.items():
            for glob in globs:
                assert representative(glob_parts(glob)) is not None, (
                    f"{job}: `{file}` declares `{glob}`, which matches nothing tracked"
                )


# --- AC5: mutations, each on a scratch copy ----------------------------------


def _targets(job: str, read: str) -> list[Target]:
    found = [t for t in real_targets() if t.job == job and t.read == read]
    assert found, f"mutation premise: {job} reads `{read}`"
    return found


def test_dropping_lint_types_from_steward_fails_the_meta_test(workflow_text: str) -> None:
    mutant = without_array_entry(workflow_text, "steward", "scripts/lint_types.py")
    failures = fire_failures(mutant, _targets("steward", "scripts/lint_types.py"))
    assert failures and all(f.startswith("steward: read `scripts/lint_types.py`") for f in failures)
    assert "left output `steward` false" in failures[0]


def test_dropping_django_herald_from_heralds_list_fails_the_meta_test(workflow_text: str) -> None:
    mutant = without_array_entry(workflow_text, "herald", "src/shared/packages/django-herald")
    failures = fire_failures(mutant, _targets("herald", "src/shared/packages/django-herald"))
    assert failures and all(f.startswith("herald: read `src/shared/packages/django-herald`") for f in failures)


def test_dropping_the_django_glob_from_the_trigger_paths_fails_the_paths_half(workflow_text: str) -> None:
    mutant = without_trigger(workflow_text, "src/shared/packages/django-*/**")
    failures = fire_failures(mutant, _targets("steward", "src/shared/packages/django-*"))
    assert failures and all("on.pull_request.paths does not match it" in f for f in failures)
    assert failures[0].startswith("steward: read `src/shared/packages/django-*`")


def test_dropping_docs_dreams_from_doctors_list_fails_the_meta_test(workflow_text: str) -> None:
    mutant = without_array_entry(workflow_text, "doctor", "docs/dreams")
    failures = fire_failures(mutant, _targets("doctor", "docs/dreams"))
    assert failures and all(f.startswith("doctor: read `docs/dreams`") for f in failures)


def test_dropping_the_planning_glob_from_marshals_list_fails_the_meta_test(workflow_text: str) -> None:
    glob = "_bmad-output/projects/*/planning-artifacts/**"
    mutant = without_array_entry(workflow_text, "marshal", to_pathspec(glob_parts(glob)))
    failures = fire_failures(mutant, _targets("marshal", "_bmad-output/projects/*/planning-artifacts"))
    assert failures and all(
        f.startswith("marshal: read `_bmad-output/projects/*/planning-artifacts`") for f in failures
    )


def test_removing_a_handoff_file_from_its_declaration_fails_the_meta_test() -> None:
    victim = f"{PACKAGES}/pyforge-marshal/tests/meta/test_tea_architecture_generator.py"
    declared = {job: dict(files) for job, files in ROOT_HANDOFF_INPUTS.items()}
    del declared["marshal"][victim]
    assert handoff_problems(derived_handoffs(), declared) == [
        f"marshal: `{victim}` hands the repo root to the code under test and is not in ROOT_HANDOFF_INPUTS"
    ]


def test_a_stale_handoff_declaration_fails_the_meta_test() -> None:
    declared = {job: dict(files) for job, files in ROOT_HANDOFF_INPUTS.items()}
    declared["warden"]["src/shared/packages/pyforge-warden/tests/unit/test_gone.py"] = (("docs/**",), "stale")
    problems = handoff_problems(derived_handoffs(), declared)
    assert problems == [
        "warden: ROOT_HANDOFF_INPUTS names `src/shared/packages/pyforge-warden/tests/unit/test_gone.py`, "
        "which hands no repo root to anything"
    ]


# --- AC6: no job loses a path -------------------------------------------------

ALL_JOBS = set(OUTPUTS)
PRESERVED: dict[str, set[str]] = {
    "src/shared/packages/pyforge-core/src/x.py": ALL_JOBS,
    "src/shared/packages/pyforge-testing-kit/src/x.py": ALL_JOBS,
    "pixi.toml": ALL_JOBS,
    "pixi.lock": ALL_JOBS,
    WORKFLOW_REL: ALL_JOBS,
    "presentations/deck/x.md": {"herald"},
    "docs-site/x.md": {"herald"},
    "scripts/tests/test_x.py": {"atlas", "core"},
    "tests/packaging/test_openteams_handoffs.py": {"atlas", "core"},
    "scripts/openteams_identity_dashboards.py": {"atlas", "core"},
    "scripts/conda-forge-packaging-inventory-operations_x.py": {"atlas", "core"},
    "src/shared/packages/django-pyforge/src/x.py": {"testing_kit"},
    "src/platform/config/flags.json": {"testing_kit"},
    **{f"src/shared/packages/pyforge-{s}/src/x.py": {s, "core"} for s in STATIONS},
}


def test_no_trigger_the_workflow_had_before_is_lost(workflow_text: str) -> None:
    outputs = run_changes(workflow_text, PRESERVED)
    patterns = trigger_paths(workflow_text)
    lost = [
        f"{path}: lost output `{job}`"
        for path, jobs in PRESERVED.items()
        for job in sorted(jobs)
        if outputs[path].get(job) != "true"
    ]
    lost += [
        f"{path}: no longer matches on.pull_request.paths"
        for path in PRESERVED
        if not preflight_ci.filter_matches(patterns, path)
    ]
    assert not lost, "\n".join(lost)
