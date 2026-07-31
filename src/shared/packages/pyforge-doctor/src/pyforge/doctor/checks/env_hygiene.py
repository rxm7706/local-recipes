"""Env-var credential-injection hygiene scanner (Story 1.4, FR-3).

Doctor's first HAND-WRITTEN detector -- unlike ``sources.warden`` (Story
1.2) and ``checks.registry`` (Story 1.3), no existing instrument wraps this
signal. It exists to catch the exact class of bug found in this repo's own
``.claude/skills/conda-forge-expert/scripts/_http.py::auth_headers_for``
(the golden fixture this module is tested against, read-only): an env-var
credential attached to a request's headers with no destination-host gate,
so a key/token scoped (in the operator's head) to one internal service can
leak to every host the caller ever requests.

``ast.parse`` ONLY -- this module never ``exec``/``eval``s, dynamically
``import``s, or otherwise RUNS any scanned source (mirrors
``sources.warden``'s own extraction discipline); see
``tests/meta/test_env_hygiene_no_execution.py``.

Detection is a settled v1 scope boundary, not an open question (see the
story spec's Design Notes -- do not re-litigate here):

* DIRECT-EXPRESSION ONLY -- the env-var read (``os.environ.get``/
  ``os.getenv``/``os.environ[...]``, including via ``from os import
  environ``/``getenv`` or an aliased ``import os as ...``) must appear
  textually within the assigned value's own expression subtree, and only
  in a VALUE-CARRYING position -- an env-read used solely as a ternary's
  ``test`` (e.g. ``"a" if os.environ.get("X") else "b"``, deciding BETWEEN
  two unrelated values) does not count (review finding: that shape is not
  actually feeding the header, so flagging it produced a false positive
  with a misleading message). No intermediate-variable tracking (``token =
  os.environ.get(...); headers["X"] = token`` is invisible to this
  scanner) and no dict-literal-construction tracking (``headers = {"X":
  os.environ.get(...)}`` likewise). Both gaps are logged in
  ``deferred-work.md``, not chased here.
* The assignment target must be an ``ast.Subscript`` on a bare
  ``ast.Name`` whose ``.id`` (case-insensitive) contains ``"header"`` --
  ``headers[...]``, ``request_headers[...]``, etc. An attribute-based
  target (``self.headers[...]``) does not match (out of v1 scope). A
  chained assignment (``headers["X"] = other["Y"] = value``) matches if
  ANY target is header-shaped (review finding).
* Guard recognition is ``if``/``elif`` STATEMENTS ONLY -- a host check
  expressed as a ternary (``ast.IfExp``) condition, a ``match``/``case``
  dispatch, or any other expression-level conditional is not recognized as
  suppressing a finding (review finding, scoped out rather than chased: a
  narrower edge case than the false-positive/false-negative gaps above).
* A finding is suppressed only when SOME enclosing ``if``/``elif`` test,
  anywhere up the assignment's ancestor chain WITHIN ITS OWN ENCLOSING
  FUNCTION, references a host-like name (``host``/``netloc``/``hostname``/
  ``domain``, matched as a whole ``_``-separated token, case-insensitive,
  against any ``ast.Name.id`` or ``ast.Attribute.attr`` in the test
  subtree -- substring containment was rejected: it let an unrelated name
  like ``ghost_mode`` accidentally suppress a real finding, review
  finding). Suppression applies ONLY to the guarded ``if``/``elif``'s TRUE
  branch (``node.body``) -- an assignment in the ``else``/failed-``elif``
  branch (``node.orelse``) does NOT inherit that same test as a guard,
  since the test being FALSE there is exactly the "not this host" case
  this check exists to catch (review finding: `if host==safe: ... else:
  headers[...] = os.environ.get(...)` was silently invisible before this
  fix). A guard belonging to an outer function that merely contains a
  nested ``def`` does not count either -- see
  ``_CredentialInjectionVisitor``.

Every emitted ``Finding`` carries ``status=DoctorStatus.WARN`` (Design
Decision, story spec): a hand-written pattern-match with no wrap-a-proven-
instrument precedent has an unproven false-positive rate on arbitrary
scanned trees, so it reports without gating ``doctor check``'s exit code by
itself in v1.

This module parses source as DATA: no subprocess, no network, no exec.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Iterator

from ..models import DoctorStatus, Finding, Source

# The one check this module produces -- registered in checks.registry's
# _CATALOG under category "env" and dispatched by gather_one.
CHECK_NAME = "unconditional-credential-injection"

# Directory names pruned from the discovery walk -- never a project's own
# scannable source (extends pyforge.warden.hygiene.has_adjacent_python_
# source's .git-pruning idiom to the other VCS-adjacent/vendored dirs a
# Python project commonly carries).
_PRUNED_DIR_NAMES = frozenset(
    {".git", "__pycache__", ".venv", "venv", "node_modules", ".pixi"}
)

# NFR bound mirroring pyforge.warden.hygiene._ADJACENT_PYTHON_SOURCE_ENTRY_CAP:
# the max number of directory ENTRIES (files + subdirs, summed across the
# whole walk) examined before the discovery walk stops collecting more --
# a pathological/huge tree can never turn this into an unbounded walk.
_DISCOVERY_ENTRY_CAP = 50_000

_HOST_LIKE_TOKENS = frozenset({"host", "netloc", "hostname", "domain"})


def _discover_python_files(target: Path) -> tuple[list[Path], bool]:
    """A bounded, ``.git``-etc-pruning ``os.walk`` collecting every ``*.py``
    file under ``target``, sorted (both dir traversal and file collection)
    for a deterministic scan order.

    Returns ``(files, incomplete)`` -- ``incomplete`` is ``True`` when the
    walk hit the entry cap or ``os.walk`` could not descend into some
    subdirectory (permission-denied, vanished mid-walk); mirrors
    ``pyforge.warden.hygiene.has_adjacent_python_source``'s ``onerror``
    idiom, which this module's discovery walk previously omitted (review
    finding) -- a silently-pruned subtree could otherwise hide the exact
    leak this scanner exists to find with zero signal in the result."""
    discovered: list[Path] = []
    entries_visited = 0
    incomplete = False

    def _on_error(_exc: OSError) -> None:
        nonlocal incomplete
        incomplete = True

    for dirpath, dirnames, filenames in os.walk(target, onerror=_on_error):
        dirnames[:] = sorted(
            name for name in dirnames if name not in _PRUNED_DIR_NAMES
        )
        entries_visited += len(dirnames)
        if entries_visited >= _DISCOVERY_ENTRY_CAP:
            incomplete = True
            break
        for name in sorted(filenames):
            entries_visited += 1
            if name.endswith(".py"):
                discovered.append(Path(dirpath) / name)
            if entries_visited >= _DISCOVERY_ENTRY_CAP:
                incomplete = True
                break
        if entries_visited >= _DISCOVERY_ENTRY_CAP:
            break
    return discovered, incomplete


def _resolve_os_aliases(
    tree: ast.Module,
) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """Returns ``(os_names, environ_names, getenv_names)`` -- the bound
    names that refer to the ``os`` module, ``os.environ``, and
    ``os.getenv`` respectively in THIS file, resolving ``import os as
    X``/``from os import environ [as X]``/``from os import getenv [as
    X]`` aliasing (mirrors ``test_sources_warden_no_subprocess.py``'s
    ``os_aliases`` idiom) -- previously hard-coded to the literal names
    ``"os"``/``"environ"``/``"getenv"``, which an aliased or ``from``-style
    import silently evaded (review finding)."""
    os_names = {"os"}
    environ_names: set[str] = set()
    getenv_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "os" and alias.asname:
                    os_names.add(alias.asname)
        elif isinstance(node, ast.ImportFrom) and node.module == "os":
            for alias in node.names:
                bound = alias.asname or alias.name
                if alias.name == "environ":
                    environ_names.add(bound)
                elif alias.name == "getenv":
                    getenv_names.add(bound)
    return frozenset(os_names), frozenset(environ_names), frozenset(getenv_names)


def _is_os_environ_attribute(node: ast.expr, os_names: frozenset[str]) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "environ"
        and isinstance(node.value, ast.Name)
        and node.value.id in os_names
    )


def _is_os_getenv_name(node: ast.expr, os_names: frozenset[str]) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "getenv"
        and isinstance(node.value, ast.Name)
        and node.value.id in os_names
    )


def _literal_str(node: ast.expr | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _env_read_match(
    node: ast.AST,
    os_names: frozenset[str],
    environ_names: frozenset[str],
    getenv_names: frozenset[str],
) -> tuple[str | None, bool]:
    """Whether ``node`` itself is an ``os.environ.get(...)``/
    ``os.getenv(...)``/``os.environ[...]`` read (or the ``from``-imported/
    aliased equivalent). Returns ``(name, True)`` when it is -- ``name`` is
    the literal string key/arg if present, else ``None`` -- or ``(None,
    False)`` when it is not."""
    if isinstance(node, ast.Call):
        func = node.func
        is_environ_get = isinstance(func, ast.Attribute) and func.attr == "get" and (
            _is_os_environ_attribute(func.value, os_names)
            or (isinstance(func.value, ast.Name) and func.value.id in environ_names)
        )
        is_getenv_call = _is_os_getenv_name(func, os_names) or (
            isinstance(func, ast.Name) and func.id in getenv_names
        )
        if is_environ_get or is_getenv_call:
            arg = node.args[0] if node.args else None
            return _literal_str(arg), True
    elif isinstance(node, ast.Subscript):
        base = node.value
        if _is_os_environ_attribute(base, os_names) or (
            isinstance(base, ast.Name) and base.id in environ_names
        ):
            return _literal_str(node.slice), True
    return None, False


def _walk_value_positions(node: ast.AST) -> Iterator[ast.AST]:
    """Like ``ast.walk`` but never descends into ``ast.IfExp.test`` -- a
    ternary's condition decides BETWEEN two other values and contributes
    no value of its own to the assignment, so an env-read used only there
    is not "fed" into the header (review finding: this previously produced
    a false positive on e.g. ``"a" if os.environ.get("X") else "b"``, with
    a message asserting the env-var fed the header when it did not)."""
    yield node
    if isinstance(node, ast.IfExp):
        for child in (node.body, node.orelse):
            yield from _walk_value_positions(child)
        return
    for child in ast.iter_child_nodes(node):
        yield from _walk_value_positions(child)


def _direct_env_read(
    value: ast.expr,
    os_names: frozenset[str],
    environ_names: frozenset[str],
    getenv_names: frozenset[str],
) -> tuple[str | None, bool]:
    """Whether ``value``'s own expression subtree directly contains an
    env-var read in a value-carrying position -- never following a
    ``Name`` reference to its assignment elsewhere (the direct-expression-
    only v1 boundary), and never counting a ternary's ``test`` (see
    ``_walk_value_positions``)."""
    for node in _walk_value_positions(value):
        name, found = _env_read_match(node, os_names, environ_names, getenv_names)
        if found:
            return name, True
    return None, False


def _header_subscript_name(target: ast.expr) -> str | None:
    if not isinstance(target, ast.Subscript):
        return None
    base = target.value
    if not isinstance(base, ast.Name) or "header" not in base.id.lower():
        return None
    return base.id


def _header_subscript_target(assign: ast.Assign) -> str | None:
    """The header-dict variable name when ANY of ``assign``'s targets is
    an ``ast.Subscript`` on a bare ``ast.Name`` whose ``.id`` (case-
    insensitive) contains ``"header"`` -- handles a chained assignment
    (``headers["X"] = other["Y"] = value``, review finding); ``None`` when
    no target matches."""
    for target in assign.targets:
        name = _header_subscript_name(target)
        if name is not None:
            return name
    return None


def _references_host_like(test: ast.expr) -> bool:
    """Whether ``test`` references a host-like name, matched as a WHOLE
    ``_``-separated token (case-insensitive) -- substring containment was
    rejected: it let an unrelated name like ``ghost_mode`` accidentally
    suppress a real finding (review finding)."""
    for node in ast.walk(test):
        if isinstance(node, ast.Name):
            candidate = node.id
        elif isinstance(node, ast.Attribute):
            candidate = node.attr
        else:
            continue
        tokens = candidate.lower().split("_")
        if any(token in _HOST_LIKE_TOKENS for token in tokens):
            return True
    return False


class _CredentialInjectionVisitor(ast.NodeVisitor):
    """Walks one module's AST tracking a stack of enclosing ``ast.If.test``
    nodes (TRUE-branch only, see ``visit_If``), collecting ``(lineno,
    header_var, env_var_name)`` for every unconditional credential-
    injection assignment found.

    The guard stack is RESET (not merely appended to) at each function
    boundary: only a host-referencing test "anywhere up the ancestor chain
    WITHIN THE FUNCTION" suppresses a finding (the story spec's Design
    Decision) -- a guard belonging to an outer function that merely
    contains a nested ``def`` must not leak in and suppress a finding
    inside that nested function. ``elif`` branches are ordinary nested
    ``ast.If`` nodes in Python's own AST (living in the outer ``If``'s
    ``orelse``), so an assignment guarded by an ``elif`` naturally
    accumulates both that ``elif``'s own test and every enclosing ``if``'s
    test on the stack -- exactly "anywhere up the ancestor chain"."""

    def __init__(
        self,
        os_names: frozenset[str],
        environ_names: frozenset[str],
        getenv_names: frozenset[str],
    ) -> None:
        self._os_names = os_names
        self._environ_names = environ_names
        self._getenv_names = getenv_names
        self._guards: list[ast.expr] = []
        self.matches: list[tuple[int, str, str | None]] = []

    def visit_If(self, node: ast.If) -> None:
        # node.test is evaluated under the CURRENT (not-yet-extended) guard
        # stack; only node.body runs "gated on node.test passing" -- node.
        # orelse (else/failed-elif) runs precisely when the test did NOT
        # match, so inheriting the same guard there would suppress the
        # exact inverse-condition leak this check exists to catch (review
        # finding: `if host==safe: ... else: headers[...] =
        # os.environ.get(...)` was silently invisible before this fix).
        self.visit(node.test)
        self._guards.append(node.test)
        for stmt in node.body:
            self.visit(stmt)
        self._guards.pop()
        for stmt in node.orelse:
            self.visit(stmt)

    def _visit_function_scope(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        saved_guards, self._guards = self._guards, []
        self.generic_visit(node)
        self._guards = saved_guards

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function_scope(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function_scope(node)

    def _check(self, header_var: str | None, value: ast.expr, lineno: int) -> None:
        if header_var is None:
            return
        env_var_name, found = _direct_env_read(
            value, self._os_names, self._environ_names, self._getenv_names
        )
        if found and not any(
            _references_host_like(guard) for guard in self._guards
        ):
            self.matches.append((lineno, header_var, env_var_name))

    def visit_Assign(self, node: ast.Assign) -> None:
        self._check(_header_subscript_target(node), node.value, node.lineno)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._check(
            _header_subscript_name(node.target), node.value, node.lineno
        )
        self.generic_visit(node)


def _scan_file(file_path: Path) -> list[Finding]:
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError, OSError):
        # A file that fails to parse -- a syntax error, an undecodable
        # encoding, or a filesystem race -- is skipped, never crashes the
        # scan (pyforge.doctor's degrade-never-crash discipline; mirrors
        # sources/warden.py's own "no Exception escapes gather()" rule).
        return []
    os_names, environ_names, getenv_names = _resolve_os_aliases(tree)
    visitor = _CredentialInjectionVisitor(os_names, environ_names, getenv_names)
    visitor.visit(tree)
    findings: list[Finding] = []
    for lineno, header_var, env_var_name in visitor.matches:
        env_label = env_var_name or "an env-var"
        findings.append(
            Finding(
                source=Source.ENV_HYGIENE,
                check=CHECK_NAME,
                status=DoctorStatus.WARN,
                message=(
                    f"{file_path}:{lineno}: {env_label} is read directly "
                    f"into {header_var}[...] with no enclosing host-scope "
                    "if/elif guard -- looks like an unconditional "
                    "credential injection"
                ),
                evidence={
                    "file": str(file_path),
                    "line": lineno,
                    "var_name": env_var_name,
                },
            )
        )
    return findings


def gather(target: Path) -> tuple[Finding, ...]:
    """Scan every ``*.py`` file under ``target`` for an unconditional
    env-var-credential-into-header-assignment shape (see the module
    docstring for the exact detection boundary) and return one
    ``Finding(status=DoctorStatus.WARN)`` per match, plus one additional
    ``Finding`` if the discovery walk was incomplete (entry cap hit, or a
    subdirectory could not be read) -- an incomplete scan could otherwise
    report a false "all clear" with zero signal that part of the tree was
    never examined (review finding).

    Pure ``ast.parse`` static analysis -- never executes, imports, or
    otherwise runs any scanned source."""
    findings: list[Finding] = []
    files, incomplete = _discover_python_files(target)
    for file_path in files:
        findings.extend(_scan_file(file_path))
    if incomplete:
        findings.append(
            Finding(
                source=Source.ENV_HYGIENE,
                check=CHECK_NAME,
                status=DoctorStatus.WARN,
                message=(
                    f"scan of {target} was INCOMPLETE -- the discovery "
                    "walk hit its entry cap or could not read some "
                    "subdirectory; results above may be missing real "
                    "findings"
                ),
                evidence={"file": str(target), "line": None, "var_name": None},
            )
        )
    return tuple(findings)
