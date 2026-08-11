"""AD-14 -- credential blindness: Mason never reads a `JFROG_*` variable,
never makes an authenticated HTTP request on CFE's behalf, and never
overrides a CFE subprocess's own environment; credentials reach CFE only
through the inherited process environment (FR-6, NFR-2, R-8).

Three independent AST-based guards (never raw-text/regex -- matches every
sibling meta-test's documented rationale, e.g. `test_no_recipe_knowledge.py`'s
docstring), each scanning every `.py` file under `src/pyforge/mason/`. Unlike
`test_no_recipe_knowledge.py`'s four-category deny-list table, each guard
here enforces exactly one rule, so no `DenyListEntry`-style abstraction is
introduced -- a single compiled pattern / name set per guard is proportional
to the scope.

**Guard 1 -- env-var name.** No string constant (excluding a module/class/
function's own docstring, mirroring `test_no_recipe_knowledge.py`'s
exemption) matches `JFROG_[A-Z0-9_]*`, case-insensitively. Scoped to string
CONSTANT VALUES only, not identifier positions (unlike AD-1's guard): FR-6's
rule is "no module reads a JFROG_* variable," and an env-var read always
names the variable as a string (`os.environ.get("JFROG_API_KEY")`), never as
a Python identifier. `+`-concatenated chains of string constants are folded
before matching (follow-up review, both reviewers), since `"JFROG" +
"_API_KEY"` names the variable just as literally as one token does; the
parser already folds the adjacent-literal spelling (`"JFROG" "_API_KEY"`)
into a single constant. Known, accepted residual, disclosed rather than
chased: a name assembled by `%`/`.format()`/`str.join`, or read via
`getattr`, still evades a constant scan -- open-ended dataflow analysis is
out of proportion here, and no such shape exists in this codebase.

**Guard 2 -- HTTP-client import.** No `import`/`from ... import` of
`requests`, `httpx`, `urllib.request`, or `http.client` -- including the
"parent, then submodule" spelling (`from urllib import request`, `from http
import client`). Absolute imports only: a *relative* import (`from
.requests import helper`, `ImportFrom.level > 0`) names a local Mason module
that merely shares a banned name and is not the third-party client this
guard bans (follow-up review, both reviewers -- it was a false positive).
`_BANNED_HTTP_IMPORTS` is paired with an independently-spelled
`_REQUIRED_HTTP_IMPORTS` floor, mirroring
`test_adapter_sole_caller.py::_REQUIRED_SPAWN_CALL_NAMES`: the per-name
fixtures parametrize over the banned set itself, so without the floor,
deleting an entry deleted its own coverage and reopened the guard silently
(follow-up review, Edge Case Hunter, reproduced). Deliberately narrow (spec
Design Notes): Mason holds zero HTTP-client capability today, which
structurally forecloses CFE's own `_http.py` unconditional `JFROG_API_KEY`
header-injection pattern from reaching Mason's own surface. Not a general
network-access ban -- Epic 3 is expected to add scoped, non-CFE HTTP
capability later and must loosen this guard explicitly when that story lands.

**Guard 3 -- env inheritance.** Two scanners, one property: nothing changes
what a spawned CFE child inherits.

*3a -- `env=` at the call site.* Every `env=` keyword argument passed to a
call shaped like `subprocess.run`/`Popen`/`call`/`check_call`/
`check_output` or `asyncio.create_subprocess_exec`/`_shell` or
`run_streamed` (bare-name or attribute form, matched by name only -- no
receiver resolution, the same documented residual every sibling spawn-call
guard accepts) is either absent or the bare literal `None`. The recognized
set is pinned by an independently-spelled `_REQUIRED_ENV_OVERRIDE_CALL_NAMES`
floor and a per-name fixture, again mirroring `test_adapter_sole_caller.py`
-- the original three-name set let `subprocess.check_output(..., env=...)`
through untouched (follow-up review, Edge Case Hunter, reproduced).

Exactly one allowlist entry: `cfe.py`'s own `run_streamed`-internal
`Popen(..., env=dict(env) if env is not None else None)` call (Story 1.10's
sanctioned pass-through primitive -- `cfe.py`'s own docstring names it as
such). The allowlist is identified structurally -- by walking `run_streamed`'s
own function body in `cfe.py` and permitting only the `Popen` call found
there -- not by file alone, so an unrelated `env=` misuse elsewhere in
`cfe.py` still gets flagged (spec Design Notes: "targets call sites, not
function signatures... the property this guard protects is 'nobody currently
exercises the override,' which only a call-site scan can prove"). It
allowlists the `env=` EXPRESSION, not merely the call's identity: the value
must unparse to exactly `_SANCTIONED_PASS_THROUGH_ENV_EXPR`. Identity alone
was the guard's largest hole (follow-up review, both reviewers, reproduced
on the real `cfe.py`) -- rewriting that one call's `env=` to `{}`, or to a
targeted `JFROG_*`-stripping comprehension, defeated AD-14 at the single
site that can defeat it while every guard test stayed green.

*3b -- process-environment mutation.* No module mutates `os.environ`
(subscript assign/delete, or `update`/`setdefault`/`pop`/`popitem`/`clear`)
or calls `os.putenv`/`os.unsetenv`. Mutating the parent's environment before
a spawn overrides what the child inherits just as effectively as `env=`, and
is the more idiomatic way to do it -- 3a alone scanned clean through it
(follow-up review, both reviewers, reproduced).

Known, accepted residuals for Guard 3, not attempted here: `**kwargs`
unpacking, or `env` passed *positionally* rather than by keyword (which is
also the only way `os.execve`/`os.posix_spawn` accept it -- those are
positional-only in CPython, so a keyword-name scan cannot reach them, and
`test_adapter_sole_caller.py`'s AD-3 guard already bans them outside
`cfe.py`). Open-ended dataflow analysis is out of proportion for this guard,
and none of these shapes appears anywhere in this codebase's actual call
sites today.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "mason"


@dataclass(frozen=True)
class Violation:
    path: Path
    lineno: int
    category: str
    detail: str


CATEGORY_ENV_VAR_NAME = "jfrog-env-var-name"
CATEGORY_HTTP_IMPORT = "http-client-import"
CATEGORY_ENV_OVERRIDE = "env-override"


def _read_source(path: Path) -> str:
    try:
        # utf-8-sig, matching every sibling meta-test's choice: a plain
        # utf-8 read leaves a BOM in the text and ast.parse rejects it as a
        # syntax error, reporting a perfectly runnable module as unscannable.
        return path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise AssertionError(
            f"{path}: unreadable ({exc}); the AD-14 credential-isolation "
            "guard cannot AST-scan this file"
        ) from exc
    except UnicodeDecodeError as exc:
        raise AssertionError(
            f"{path}: not valid UTF-8; the AD-14 credential-isolation guard "
            "cannot AST-scan this file"
        ) from exc


def _parse_source(source: str, path: Path) -> ast.Module:
    try:
        return ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise AssertionError(
            f"{path}: invalid Python syntax; the AD-14 credential-isolation "
            "guard cannot AST-scan this file"
        ) from exc


def _parse_file(path: Path) -> ast.Module:
    return _parse_source(_read_source(path), path)


# --- Guard 1: no JFROG_* environment-variable name anywhere -----------------

_JFROG_ENV_VAR_PATTERN = re.compile(r"(?<![0-9A-Za-z])JFROG_[A-Z0-9_]*", re.IGNORECASE)
"""Explicit alphanumeric lookbehind (excluding `_`), NOT `\\b` (review pass,
Edge Case Hunter): `_` is a word character, so `\\b` never fires beside one
and a prefixed name like `STAGING_JFROG_API_KEY` sailed through the original
pattern -- the identical underscore-adjacency bug `test_no_recipe_knowledge.py`
already documents fixing for its own gotcha/v1-field entries (via the same
"exclude alnum, but not underscore" lookaround), reintroduced here despite
this file's own module docstring claiming to mirror that guard.
Case-insensitive (review pass, Blind Hunter): `jfrog_api_key` names the same
credential-shaped variable, lowercased."""


def _first_statement_docstring_ids(body: list[ast.stmt]) -> set[int]:
    """`id()` of `body`'s own docstring constant -- the first statement, if
    it is a bare string `Expr` (mirrors `test_no_recipe_knowledge.py`'s
    identically-named helper)."""
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return {id(body[0].value)}
    return set()


def _trailing_attribute_docstring_ids(body: list[ast.stmt]) -> set[int]:
    """`id()` of every bare string-`Expr` statement in `body` that
    immediately follows an assignment/annotated-assignment -- the PEP
    257-adjacent "attribute docstring" convention this very file now uses
    for `_JFROG_ENV_VAR_PATTERN` above (review pass, Blind Hunter: the
    original version only exempted a scope's first statement, narrower than
    `test_no_recipe_knowledge.py`'s own exemption despite this module's
    docstring claiming to mirror it -- so this file's own trailing-docstring
    rationale, once it names a JFROG_* term, would have false-positived on
    itself)."""
    ids: set[int] = set()
    for prev, curr in zip(body, body[1:]):
        if (
            isinstance(prev, (ast.Assign, ast.AnnAssign))
            and isinstance(curr, ast.Expr)
            and isinstance(curr.value, ast.Constant)
            and isinstance(curr.value.value, str)
        ):
            ids.add(id(curr.value))
    return ids


def _docstring_string_ids(tree: ast.Module) -> set[int]:
    """`id()` of every module/class/function/async-function docstring
    constant, plus every module/class-level trailing attribute docstring, in
    `tree` -- the exemption this guard grants, so a module narrating "Mason
    never reads JFROG_API_KEY" in prose is not itself flagged for saying
    so."""
    ids = _first_statement_docstring_ids(tree.body)
    ids |= _trailing_attribute_docstring_ids(tree.body)
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            ids |= _first_statement_docstring_ids(node.body)
        if isinstance(node, ast.ClassDef):
            ids |= _trailing_attribute_docstring_ids(node.body)
    return ids


def _constant_text_value(node: ast.expr) -> str | None:
    """Return the string form of a `Constant` node's value -- `str` values
    as-is, `bytes` values decoded (`errors="replace"`) -- or `None` for any
    other constant type or non-`Constant` node (review pass, Blind Hunter:
    mirrors `test_no_recipe_knowledge.py`'s identically-motivated helper --
    a bytes literal is a real, if unlikely, way to hide a JFROG_* reference
    from a str-only scan)."""
    if not isinstance(node, ast.Constant):
        return None
    if isinstance(node.value, str):
        return node.value
    if isinstance(node.value, bytes):
        return node.value.decode("utf-8", errors="replace")
    return None


def _add_chain_leaves(node: ast.BinOp) -> list[ast.expr] | None:
    """Every leaf of a `+`-joined chain, in source order, or `None` if any
    leaf is not a string-ish constant (which makes the chain unfoldable --
    `'a' + str(3)` has no compile-time text)."""
    if not isinstance(node.op, ast.Add):
        return None
    leaves: list[ast.expr] = []

    def collect(operand: ast.expr) -> bool:
        if isinstance(operand, ast.BinOp) and isinstance(operand.op, ast.Add):
            return collect(operand.left) and collect(operand.right)
        if _constant_text_value(operand) is None:
            return False
        leaves.append(operand)
        return True

    return leaves if collect(node) else None


def _folded_concatenations(tree: ast.Module) -> tuple[list[tuple[ast.BinOp, str]], set[int]]:
    """Every OUTERMOST foldable `+`-chain paired with the one text it
    evaluates to, plus the `id()`s of the constants those chains consumed
    (follow-up review, both reviewers: `os.environ.get("JFROG" + "_API_KEY")`
    scanned clean because `ast.walk` sees each half separately and neither
    matches alone).

    Both halves of the return value exist to keep one expression counted
    once. Inner chain nodes are skipped because the outermost node already
    carries the whole folded text; the consumed leaves are skipped by the
    caller's constant pass for the same reason -- otherwise `"JFROG_" +
    "API" + "_KEY"` reports twice, once folded and once for the leaf
    `"JFROG_"` that happens to match on its own."""
    nested_ids: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Add):
            continue
        for operand in (node.left, node.right):
            if isinstance(operand, ast.BinOp) and isinstance(operand.op, ast.Add):
                nested_ids.add(id(operand))

    folded: list[tuple[ast.BinOp, str]] = []
    consumed_ids: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp) or id(node) in nested_ids:
            continue
        leaves = _add_chain_leaves(node)
        if leaves is None:
            continue
        folded.append((node, "".join(_constant_text_value(leaf) or "" for leaf in leaves)))
        consumed_ids |= {id(leaf) for leaf in leaves}
    return folded, consumed_ids


def _find_jfrog_env_var_references(root: Path) -> list[Violation]:
    violations: list[Violation] = []
    for path in sorted(root.rglob("*.py")):
        tree = _parse_file(path)
        docstring_ids = _docstring_string_ids(tree)
        folded, consumed_ids = _folded_concatenations(tree)

        for node in ast.walk(tree):
            text = _constant_text_value(node)
            if text is None or id(node) in docstring_ids or id(node) in consumed_ids:
                continue
            match = _JFROG_ENV_VAR_PATTERN.search(text)
            if match is not None:
                violations.append(
                    Violation(path, node.lineno, CATEGORY_ENV_VAR_NAME, match.group())
                )

        for chain, text in folded:
            match = _JFROG_ENV_VAR_PATTERN.search(text)
            if match is not None:
                violations.append(
                    Violation(path, chain.lineno, CATEGORY_ENV_VAR_NAME, match.group())
                )
    return violations


# --- Guard 2: no HTTP-client import ------------------------------------------

_BANNED_HTTP_IMPORTS = frozenset({"requests", "httpx", "urllib.request", "http.client"})
"""The four libraries this guard bans -- deliberately narrow, not a general
network-access ban (module docstring)."""

_REQUIRED_HTTP_IMPORTS = frozenset({"requests", "httpx", "urllib.request", "http.client"})
"""Deliberately duplicated, NOT derived from `_BANNED_HTTP_IMPORTS` (follow-up
review, Edge Case Hunter, reproduced): the per-name fixtures below parametrize
over the banned set itself, so dropping `"requests"` from it also deleted the
only fixture proving `requests` is detected -- a real `import requests` in
`resolve.py` then scanned clean with the whole meta suite green. A derived
floor would delete itself the same way. Mirrors
`test_adapter_sole_caller.py::_REQUIRED_SPAWN_CALL_NAMES`, whose own deferred
entry (`DW-1-10`) already documents this exact duplication rationale."""


def _find_http_client_imports(root: Path) -> list[Violation]:
    violations: list[Violation] = []
    for path in sorted(root.rglob("*.py")):
        tree = _parse_file(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in _BANNED_HTTP_IMPORTS:
                        violations.append(
                            Violation(path, node.lineno, CATEGORY_HTTP_IMPORT, alias.name)
                        )
            # `node.level == 0` -- absolute imports only. A relative import
            # (`from .requests import helper`) names a LOCAL Mason module that
            # merely shares the name, not the banned third-party client
            # (follow-up review, both reviewers: it was a false positive, and
            # the cheapest repair under a red guard is to weaken the guard).
            elif (
                isinstance(node, ast.ImportFrom)
                and node.level == 0
                and node.module is not None
            ):
                if node.module in _BANNED_HTTP_IMPORTS:
                    violations.append(
                        Violation(path, node.lineno, CATEGORY_HTTP_IMPORT, node.module)
                    )
                # The "parent, then submodule" spelling of the two dotted
                # names -- `from urllib import request` / `from http import
                # client` reach the identical submodule as `import
                # urllib.request` / `import http.client`.
                for alias in node.names:
                    dotted = f"{node.module}.{alias.name}"
                    if dotted in _BANNED_HTTP_IMPORTS:
                        violations.append(
                            Violation(path, node.lineno, CATEGORY_HTTP_IMPORT, dotted)
                        )
    return violations


# --- Guard 3: env inheritance on subprocess.run / subprocess.Popen / --------
# ------------------------------------------- run_streamed call sites -------

_ENV_OVERRIDE_CALL_NAMES = frozenset(
    {
        "run",
        "Popen",
        "call",
        "check_call",
        "check_output",
        "create_subprocess_exec",
        "create_subprocess_shell",
        "run_streamed",
    }
)
"""Matched on bare attribute/function name only, no receiver resolution --
the same documented residual `test_adapter_sole_caller.py`'s spawn-call
guard accepts. Every spawn API in this project's reach that takes `env` as a
KEYWORD. The original set held only `run`/`Popen`/`run_streamed` (the three
the spec's I/O matrix names by example), so `subprocess.check_output(...,
env={...})` -- a plain, unexotic override -- scanned clean (follow-up review,
Edge Case Hunter, reproduced). `os.execve`/`os.posix_spawn` are deliberately
absent: they take env positionally-only, so no keyword scan can reach them
(module docstring residuals)."""

_REQUIRED_ENV_OVERRIDE_CALL_NAMES = frozenset(
    {
        "run",
        "Popen",
        "call",
        "check_call",
        "check_output",
        "create_subprocess_exec",
        "create_subprocess_shell",
        "run_streamed",
    }
)
"""Independently spelled floor, same rationale as `_REQUIRED_HTTP_IMPORTS`
and `test_adapter_sole_caller.py::_REQUIRED_SPAWN_CALL_NAMES`: narrowing the
recognized set must also delete the name here, with the rationale in that
diff."""

_SANCTIONED_PASS_THROUGH_ENV_EXPR = "dict(env) if env is not None else None"
"""The one `env=` expression the Guard-3 allowlist accepts, compared as
`ast.unparse` text. Story 1.10's sanctioned pass-through: it forwards the
caller's own `env` argument and otherwise hands `Popen` a bare `None`, which
is exactly "inherit the parent environment". Pinning the EXPRESSION, not
just the call's identity, is the fix for this guard's largest hole
(follow-up review, both reviewers, reproduced against the real `cfe.py`):
allowlisting by identity meant the sanctioned call could be rewritten to
`env={}` or to a `JFROG_*`-stripping comprehension -- defeating AD-14 at the
one site that can defeat it -- with all 34 guard tests still green."""


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _is_call_of_interest(node: ast.Call) -> bool:
    return _call_name(node) in _ENV_OVERRIDE_CALL_NAMES


def _env_kwarg_value(node: ast.Call) -> ast.expr | None:
    for kw in node.keywords:
        if kw.arg == "env":
            return kw.value
    return None


def _is_bare_none_literal(value: ast.expr) -> bool:
    return isinstance(value, ast.Constant) and value.value is None


def _run_streamed_function_def(tree: ast.Module) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "run_streamed":
            return node
    return None


def _allowlisted_popen_call_ids(tree: ast.Module) -> set[int]:
    """The one AD-14 allowlist entry: `id()` of `run_streamed`'s own
    `Popen(...)` call -- structural, not file-wide (module docstring), so a
    second, unrelated `env=` misuse elsewhere in the same file is still
    caught by the caller below.

    Fails CLOSED, not open (review pass, Blind Hunter): if `run_streamed`'s
    body contains more than one `Popen` call, NONE is allowlisted. The
    original version allowlisted every `Popen` call found by location alone,
    regardless of count -- so a second, hostile `Popen(..., env={...})`
    planted inside the same function body was silently allowlisted alongside
    the one legitimate call, the exact regression this guard exists to
    catch. The allowlist's whole premise is "exactly one sanctioned
    pass-through call"; a second call (however it got there) invalidates
    that premise, so both fall back to being flagged like any other
    unallowlisted site.

    Allowlists the `env=` EXPRESSION, not the call's identity (follow-up
    review, both reviewers): the value must unparse to exactly
    `_SANCTIONED_PASS_THROUGH_ENV_EXPR`. Identity alone meant that editing
    the one sanctioned call's `env=` -- to `{}`, or to a targeted
    `JFROG_*`-stripping comprehension -- passed every guard test, at the
    single call site where AD-14 can actually be broken."""
    func = _run_streamed_function_def(tree)
    if func is None:
        return set()
    popen_calls = [
        node
        for node in ast.walk(func)
        if node is not func and isinstance(node, ast.Call) and _call_name(node) == "Popen"
    ]
    if len(popen_calls) != 1:
        return set()
    env_value = _env_kwarg_value(popen_calls[0])
    if env_value is None or _is_bare_none_literal(env_value):
        # Not flagged by the caller anyway -- nothing to allowlist.
        return set()
    if ast.unparse(env_value) != _SANCTIONED_PASS_THROUGH_ENV_EXPR:
        return set()
    return {id(popen_calls[0])}


# --- Guard 3b: no mutation of the parent's own process environment ----------

CATEGORY_ENV_MUTATION = "env-mutation"

_ENV_MUTATING_METHODS = frozenset(
    {"update", "setdefault", "pop", "popitem", "clear", "__setitem__", "__delitem__"}
)
_ENV_MUTATING_FUNCTIONS = frozenset({"putenv", "unsetenv"})


def _is_os_environ(node: ast.expr) -> bool:
    """`os.environ` (attribute form) or a bare `environ` name imported from
    `os` -- matched by name only, the same receiver-resolution residual the
    rest of this file accepts."""
    if isinstance(node, ast.Attribute):
        return node.attr == "environ"
    return isinstance(node, ast.Name) and node.id == "environ"


def _is_os_environ_subscript(node: ast.expr) -> bool:
    return isinstance(node, ast.Subscript) and _is_os_environ(node.value)


def _find_env_mutation_violations(root: Path) -> list[Violation]:
    """Mutating `os.environ` (or calling `os.putenv`) before a spawn changes
    what the child inherits exactly as `env=` does, and is the more
    idiomatic way to do it -- Guard 3a alone scanned clean straight through
    `os.environ['X'] = token; subprocess.run(argv)` (follow-up review, both
    reviewers, reproduced)."""
    violations: list[Violation] = []
    for path in sorted(root.rglob("*.py")):
        tree = _parse_file(path)
        for node in ast.walk(tree):
            targets: list[ast.expr] = []
            if isinstance(node, (ast.Assign, ast.Delete)):
                targets = list(node.targets)
            elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
                targets = [node.target]
            if any(_is_os_environ_subscript(target) for target in targets):
                violations.append(
                    Violation(path, node.lineno, CATEGORY_ENV_MUTATION, "os.environ[...]")
                )
                continue
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr in _ENV_MUTATING_METHODS
                and _is_os_environ(func.value)
            ):
                violations.append(
                    Violation(
                        path, node.lineno, CATEGORY_ENV_MUTATION, f"os.environ.{func.attr}()"
                    )
                )
            elif _call_name(node) in _ENV_MUTATING_FUNCTIONS:
                violations.append(
                    Violation(
                        path, node.lineno, CATEGORY_ENV_MUTATION, f"os.{_call_name(node)}()"
                    )
                )
    return violations


def _find_env_override_violations(root: Path) -> list[Violation]:
    cfe_path = (root / "cfe.py").resolve()
    violations: list[Violation] = []
    for path in sorted(root.rglob("*.py")):
        tree = _parse_file(path)
        allowlisted_ids = (
            _allowlisted_popen_call_ids(tree) if path.resolve() == cfe_path else set()
        )
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not _is_call_of_interest(node):
                continue
            if id(node) in allowlisted_ids:
                continue
            env_value = _env_kwarg_value(node)
            if env_value is None or _is_bare_none_literal(env_value):
                continue
            violations.append(
                Violation(path, node.lineno, CATEGORY_ENV_OVERRIDE, ast.dump(env_value))
            )
    return violations


# --- The three real-tree assertions (FR-6, NFR-2, AD-14) --------------------


def _assert_scanning_something(root: Path) -> None:
    # Guard the guard: a stale PKG_ROOT would make every real-tree assertion
    # below pass vacuously (mirrors every sibling meta-test's own check).
    assert root.is_dir(), (
        f"AD-14 credential-isolation guard is scanning nothing -- package "
        f"root moved? {root}"
    )
    assert list(root.rglob("*.py")), (
        f"AD-14 credential-isolation guard found zero modules under {root} "
        "-- it would pass vacuously; has the package moved or been renamed?"
    )


def test_no_jfrog_env_var_reference_in_the_real_tree():
    _assert_scanning_something(PKG_ROOT)
    violations = _find_jfrog_env_var_references(PKG_ROOT)
    assert not violations, (
        "AD-14: no module may read a JFROG_* environment variable; found:\n"
        + "\n".join(f"  {v.path}:{v.lineno} matched {v.detail!r}" for v in violations)
    )


def test_no_http_client_import_in_the_real_tree():
    _assert_scanning_something(PKG_ROOT)
    violations = _find_http_client_imports(PKG_ROOT)
    assert not violations, (
        "AD-14: no module may import requests/httpx/urllib.request/http.client; "
        "found:\n" + "\n".join(f"  {v.path}:{v.lineno} imported {v.detail!r}" for v in violations)
    )


def test_no_unallowlisted_env_override_in_the_real_tree():
    _assert_scanning_something(PKG_ROOT)
    violations = _find_env_override_violations(PKG_ROOT)
    assert not violations, (
        "AD-14: env= on subprocess.run/Popen/run_streamed must be absent or "
        "the bare literal None, except cfe.py's own run_streamed-internal "
        "Popen call; found:\n"
        + "\n".join(f"  {v.path}:{v.lineno} env={v.detail}" for v in violations)
    )


def test_no_process_environment_mutation_in_the_real_tree():
    _assert_scanning_something(PKG_ROOT)
    violations = _find_env_mutation_violations(PKG_ROOT)
    assert not violations, (
        "AD-14: no module may mutate os.environ or call os.putenv/unsetenv -- "
        "a spawned CFE child must inherit the environment unchanged; found:\n"
        + "\n".join(f"  {v.path}:{v.lineno} {v.detail}" for v in violations)
    )


# --- Anti-shrink floors (both mirror test_adapter_sole_caller.py) -----------


def test_banned_http_imports_covers_the_required_floor():
    missing = _REQUIRED_HTTP_IMPORTS - _BANNED_HTTP_IMPORTS
    assert not missing, (
        "the HTTP-import guard no longer bans every client library it was "
        f"specified with; missing: {sorted(missing)}. Widening the set is "
        "free; narrowing it must also delete the name from "
        "_REQUIRED_HTTP_IMPORTS, with the rationale in that diff."
    )


def test_env_override_call_names_covers_the_required_floor():
    missing = _REQUIRED_ENV_OVERRIDE_CALL_NAMES - _ENV_OVERRIDE_CALL_NAMES
    assert not missing, (
        "the env-override guard no longer recognizes every spawn call name it "
        f"was specified with; missing: {sorted(missing)}. Widening the set is "
        "free; narrowing it must also delete the name from "
        "_REQUIRED_ENV_OVERRIDE_CALL_NAMES, with the rationale in that diff."
    )


# --- Guard 1 regression fixtures --------------------------------------------


def test_detector_fires_on_a_planted_jfrog_env_var_reference(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'import os\nKEY = os.environ.get("JFROG_API_KEY")\n', encoding="utf-8",
    )

    violations = _find_jfrog_env_var_references(root)

    assert any(v.category == CATEGORY_ENV_VAR_NAME for v in violations)


def test_detector_fires_on_a_differently_suffixed_jfrog_variable(tmp_path):
    """The pattern's `[A-Z0-9_]*` suffix must not be hardcoded to
    `JFROG_API_KEY` alone -- any `JFROG_*` name is a credential-shaped
    variable CFE itself reads (spec Intent)."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text('URL = "JFROG_URL"\n', encoding="utf-8")

    violations = _find_jfrog_env_var_references(root)

    assert any(v.category == CATEGORY_ENV_VAR_NAME for v in violations)


def test_clean_module_produces_zero_jfrog_matches(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        'VALUE = os.environ.get("MASON_CFE_ROOT")\n', encoding="utf-8",
    )

    assert _find_jfrog_env_var_references(root) == []


def test_docstring_mentioning_jfrog_is_not_flagged(tmp_path):
    """`cfe.py`-style prose ("Mason never reads JFROG_API_KEY") must not
    trip the very guard describing that guarantee."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "narrator.py").write_text(
        '"""Module docstring: Mason never reads JFROG_API_KEY (AD-14)."""\n'
        "\n"
        "class Foo:\n"
        '    """Class docstring mentioning JFROG_API_KEY too."""\n'
        "\n"
        "    def bar(self):\n"
        '        """Function docstring mentioning JFROG_API_KEY too."""\n'
        "        return 1\n",
        encoding="utf-8",
    )

    assert _find_jfrog_env_var_references(root) == []


def test_the_same_jfrog_text_outside_a_docstring_is_still_flagged(tmp_path):
    """Proves the docstring exemption is targeted, not a blanket
    suppression that would make the whole detector vacuous."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "leaky.py").write_text('MSG = "JFROG_API_KEY"\n', encoding="utf-8")

    assert _find_jfrog_env_var_references(root) != []


def test_detector_fires_on_an_underscore_prefixed_jfrog_variable(tmp_path):
    """Review pass (Edge Case Hunter): `_` is a word character, so the
    original `\\bJFROG_...` never fired beside one -- `STAGING_JFROG_API_KEY`
    is exactly the prefixed, still credential-shaped name this scan exists
    to catch."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'KEY = os.environ.get("STAGING_JFROG_API_KEY")\n', encoding="utf-8",
    )

    violations = _find_jfrog_env_var_references(root)

    assert any(v.category == CATEGORY_ENV_VAR_NAME for v in violations)


def test_detector_fires_on_a_lowercase_jfrog_variable(tmp_path):
    """Review pass (Blind Hunter): `jfrog_api_key` names the identical
    credential-shaped variable as `JFROG_API_KEY`, lowercased."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text('KEY = "jfrog_api_key"\n', encoding="utf-8")

    violations = _find_jfrog_env_var_references(root)

    assert any(v.category == CATEGORY_ENV_VAR_NAME for v in violations)


def test_detector_fires_on_a_bytes_literal_jfrog_reference(tmp_path):
    """Review pass (Blind Hunter): a `bytes` literal (`b"..."`) is a real,
    if unlikely, way to spell a JFROG_* reference past a `str`-only scan."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text('KEY = b"JFROG_API_KEY"\n', encoding="utf-8")

    violations = _find_jfrog_env_var_references(root)

    assert any(v.category == CATEGORY_ENV_VAR_NAME for v in violations)


def test_trailing_attribute_docstring_mentioning_jfrog_is_not_flagged(tmp_path):
    """Review pass (Blind Hunter): this file's own style for
    `_JFROG_ENV_VAR_PATTERN` above (a bare string statement right after a
    module-level assignment) must not false-positive on itself -- the
    original exemption only covered a scope's FIRST statement, narrower
    than `test_no_recipe_knowledge.py`'s own exemption despite this file's
    module docstring claiming to mirror it."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "narrator.py").write_text(
        "_SOME_PATTERN = 'x'\n"
        '"""Mentions JFROG_API_KEY in prose, mirroring this file\'s own '
        'trailing-docstring style."""\n',
        encoding="utf-8",
    )

    assert _find_jfrog_env_var_references(root) == []


def test_a_bare_string_not_preceded_by_an_assignment_is_still_flagged(tmp_path):
    """Proves the trailing-attribute-docstring exemption requires the
    adjacency (assignment immediately before the string) -- a bare string
    statement with no preceding assignment is not a docstring of anything
    and must still be flagged."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "leaky.py").write_text(
        "print('unrelated')\n'JFROG_API_KEY'\n", encoding="utf-8",
    )

    assert _find_jfrog_env_var_references(root) != []


def test_detector_fires_on_a_concatenated_jfrog_variable_name(tmp_path):
    """Follow-up review (both reviewers): `"JFROG" + "_API_KEY"` names the
    variable just as literally as one token does, but `ast.walk` sees each
    half separately and neither half matches alone -- it scanned clean."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'import os\nKEY = os.environ.get("JFROG" + "_API_KEY")\n', encoding="utf-8",
    )

    violations = _find_jfrog_env_var_references(root)

    assert any(v.category == CATEGORY_ENV_VAR_NAME for v in violations)


def test_a_multi_part_concatenation_is_reported_once_not_once_per_operand(tmp_path):
    """The outermost `+`-node already carries the fully folded text, so its
    inner nodes must not be counted again."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text('KEY = "JFROG_" + "API" + "_KEY"\n', encoding="utf-8")

    violations = _find_jfrog_env_var_references(root)

    assert len(violations) == 1


def test_a_non_string_concatenation_is_not_folded(tmp_path):
    """`1 + 2` (or any chain with a non-string-ish leaf) has no text to
    match -- folding must not crash or invent one."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text("TOTAL = 1 + 2\nJOINED = 'a' + str(3)\n", encoding="utf-8")

    assert _find_jfrog_env_var_references(root) == []


# --- Guard 2 regression fixtures --------------------------------------------


@pytest.mark.parametrize("name", sorted(_BANNED_HTTP_IMPORTS))
def test_detector_fires_on_a_plain_import_of_each_banned_http_client(tmp_path, name):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(f"import {name}\n", encoding="utf-8")

    violations = _find_http_client_imports(root)

    assert any(v.category == CATEGORY_HTTP_IMPORT and v.detail == name for v in violations)


@pytest.mark.parametrize("name", sorted(_BANNED_HTTP_IMPORTS))
def test_detector_fires_on_a_from_import_of_each_banned_http_client(tmp_path, name):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(f"from {name} import Something\n", encoding="utf-8")

    violations = _find_http_client_imports(root)

    assert any(v.category == CATEGORY_HTTP_IMPORT and v.detail == name for v in violations)


def test_detector_fires_on_the_parent_plus_submodule_import_form(tmp_path):
    """`from urllib import request` / `from http import client` reach the
    identical banned submodule as `import urllib.request` / `import
    http.client`, one node deeper."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "from urllib import request\nfrom http import client\n", encoding="utf-8",
    )

    violations = {v.detail for v in _find_http_client_imports(root)}

    assert violations == {"urllib.request", "http.client"}


def test_clean_module_produces_zero_http_import_matches(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        "import subprocess\nfrom pathlib import Path\n", encoding="utf-8",
    )

    assert _find_http_client_imports(root) == []


def test_a_relative_import_of_a_local_module_is_not_flagged(tmp_path):
    """Follow-up review (both reviewers): `from .requests import helper`
    parses to `ImportFrom(module='requests', level=1)` and was reported as
    the third-party `requests` -- a false positive on a purely local module,
    the failure mode whose cheapest repair is to weaken the guard."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        "from .requests import helper\nfrom .http import client\n", encoding="utf-8",
    )

    assert _find_http_client_imports(root) == []


def test_the_absolute_form_of_that_same_import_is_still_flagged(tmp_path):
    """Proves the `level == 0` narrowing is targeted at relative imports
    only, not a blanket suppression of the name."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "leaky.py").write_text("from requests import Session\n", encoding="utf-8")

    assert _find_http_client_imports(root) != []


# --- Guard 3 regression fixtures --------------------------------------------


def test_detector_fires_on_a_planted_subprocess_run_env_override(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "import subprocess\n"
        'subprocess.run(["x"], env={"FOO": "bar"})\n',
        encoding="utf-8",
    )

    violations = _find_env_override_violations(root)

    assert any(v.category == CATEGORY_ENV_OVERRIDE for v in violations)


def test_detector_fires_on_a_planted_run_streamed_caller_env_override(tmp_path):
    """The exact synthetic-caller shape the spec's I/O matrix names."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "from .cfe import run_streamed\n"
        'run_streamed(["x"], timeout=5, env={"FOO": "bar"})\n',
        encoding="utf-8",
    )

    violations = _find_env_override_violations(root)

    assert any(v.category == CATEGORY_ENV_OVERRIDE for v in violations)


def test_detector_permits_an_explicit_bare_none_env_literal(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        "import subprocess\nsubprocess.run(['x'], env=None)\n", encoding="utf-8",
    )

    assert _find_env_override_violations(root) == []


def test_detector_permits_a_call_with_no_env_kwarg_at_all(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        "import subprocess\nsubprocess.run(['x'], timeout=5)\n", encoding="utf-8",
    )

    assert _find_env_override_violations(root) == []


def test_allowlist_permits_a_synthetic_cfe_py_run_streamed_shaped_like_the_real_one(tmp_path):
    """Mirrors `cfe.py`'s real shape structurally: a `run_streamed` function
    whose own body builds `Popen(..., env=dict(env) if env is not None else
    None)` -- the sanctioned pass-through primitive itself -- must not be
    flagged when the file is literally named `cfe.py`."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "cfe.py").write_text(
        "import subprocess\n"
        "\n"
        "\n"
        "def run_streamed(argv, *, timeout, env=None):\n"
        "    proc = subprocess.Popen(\n"
        "        argv, env=dict(env) if env is not None else None,\n"
        "    )\n"
        "    return proc.wait(timeout=timeout)\n",
        encoding="utf-8",
    )

    assert _find_env_override_violations(root) == []


def test_allowlist_is_scoped_to_a_file_literally_named_cfe_py(tmp_path):
    """The identical `run_streamed`-shaped `Popen` call in a file NOT named
    `cfe.py` must still be flagged -- the allowlist is not "any file that
    defines a function called run_streamed", it is `cfe.py` specifically."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "other.py").write_text(
        "import subprocess\n"
        "\n"
        "\n"
        "def run_streamed(argv, *, timeout, env=None):\n"
        "    return subprocess.Popen(\n"
        "        argv, env=dict(env) if env is not None else None,\n"
        "    )\n",
        encoding="utf-8",
    )

    violations = _find_env_override_violations(root)

    assert any(v.category == CATEGORY_ENV_OVERRIDE for v in violations)


def test_allowlist_does_not_cover_an_unrelated_env_override_elsewhere_in_cfe_py(tmp_path):
    """The allowlist is scoped to the one `Popen` call inside
    `run_streamed`'s own body, not the whole file -- a second, unrelated
    `env=` misuse elsewhere in `cfe.py` must still be caught."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "cfe.py").write_text(
        "import subprocess\n"
        "\n"
        "\n"
        "def run_streamed(argv, *, timeout, env=None):\n"
        "    return subprocess.Popen(\n"
        "        argv, env=dict(env) if env is not None else None,\n"
        "    )\n"
        "\n"
        "\n"
        "def other_invocation(argv):\n"
        '    return subprocess.run(argv, env={"BAD": "1"})\n',
        encoding="utf-8",
    )

    violations = _find_env_override_violations(root)

    assert len(violations) == 1
    assert violations[0].path.name == "cfe.py"
    assert "BAD" in violations[0].detail


def test_allowlist_is_revoked_when_run_streamed_gains_a_second_popen_call(tmp_path):
    """Review pass (Blind Hunter): the allowlist previously permitted EVERY
    `Popen` call found inside `run_streamed`'s body, not just the one
    sanctioned call -- a second, hostile `Popen(..., env={...})` planted in
    the same function body was silently allowlisted alongside the real one,
    the exact regression this guard exists to catch. With the fix, more than
    one `Popen` call in `run_streamed`'s body revokes the allowlist
    entirely: both calls must be flagged, not just the newly-planted one."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "cfe.py").write_text(
        "import subprocess\n"
        "\n"
        "\n"
        "def run_streamed(argv, *, timeout, env=None):\n"
        "    leaked = subprocess.Popen(argv, env={'JFROG_API_KEY': 'x'})\n"
        "    proc = subprocess.Popen(\n"
        "        argv, env=dict(env) if env is not None else None,\n"
        "    )\n"
        "    return proc.wait(timeout=timeout)\n",
        encoding="utf-8",
    )

    violations = _find_env_override_violations(root)

    assert len(violations) == 2


@pytest.mark.parametrize("call_name", sorted(_REQUIRED_ENV_OVERRIDE_CALL_NAMES))
def test_every_required_env_override_call_name_is_actually_detected(tmp_path, call_name):
    """Membership in the frozenset is not detection -- only three of the
    names were ever exercised, and `subprocess.check_output(..., env={...})`
    was not one of them (follow-up review, Edge Case Hunter, reproduced)."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        f'import subprocess\n\nsubprocess.{call_name}(["x"], env={{"A": "b"}})\n',
        encoding="utf-8",
    )

    violations = _find_env_override_violations(root)

    assert any(v.category == CATEGORY_ENV_OVERRIDE for v in violations)


@pytest.mark.parametrize(
    "env_expr",
    ["{}", '{"HTTPS_PROXY": "http://evil"}', "{k: v for k, v in os.environ.items()}"],
    ids=["empty-dict", "hostile-dict", "stripping-comprehension"],
)
def test_allowlist_rejects_a_rewritten_env_expression_in_the_sanctioned_call(
    tmp_path, env_expr
):
    """THE high-severity hole (follow-up review, both reviewers, reproduced
    against the real `cfe.py`): the allowlist keyed on the `Popen` call's
    identity and never looked at its `env=` value, so rewriting the one
    sanctioned call -- to `{}`, to a hostile dict, or to a targeted
    `JFROG_*`-stripping comprehension -- defeated AD-14 at the single site
    that can defeat it, with every guard test green."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "cfe.py").write_text(
        "import os\nimport subprocess\n"
        "\n"
        "\n"
        "def run_streamed(argv, *, timeout, env=None):\n"
        f"    return subprocess.Popen(argv, env={env_expr})\n",
        encoding="utf-8",
    )

    violations = _find_env_override_violations(root)

    assert any(v.category == CATEGORY_ENV_OVERRIDE for v in violations)


def test_allowlist_is_matched_by_path_not_bare_filename(tmp_path):
    """The allowlist resolves `root/"cfe.py"`, not any file *named*
    `cfe.py`: a same-named module nested elsewhere in the tree must still be
    scanned. Mirrors `test_adapter_sole_caller.py`'s identically-named
    fixture and `test_dependency_direction.py`'s `nested/cli.py` case --
    without it, a regression to `path.name == "cfe.py"` ships green."""
    root = tmp_path / "mason"
    (root / "nested").mkdir(parents=True)
    (root / "nested" / "cfe.py").write_text(
        "import subprocess\n"
        "\n"
        "\n"
        "def run_streamed(argv, *, timeout, env=None):\n"
        "    return subprocess.Popen(\n"
        "        argv, env=dict(env) if env is not None else None,\n"
        "    )\n",
        encoding="utf-8",
    )

    violations = _find_env_override_violations(root)

    assert any(v.category == CATEGORY_ENV_OVERRIDE for v in violations)


# --- Guard 3b regression fixtures -------------------------------------------


@pytest.mark.parametrize(
    "mutation",
    [
        "os.environ['ARTIFACTORY_TOKEN'] = 't'",
        "del os.environ['PATH']",
        "os.environ.update({'A': 'b'})",
        "os.environ.setdefault('A', 'b')",
        "os.environ.pop('A', None)",
        "os.environ.clear()",
        "os.putenv('A', 'b')",
        "os.unsetenv('A')",
    ],
)
def test_detector_fires_on_each_process_environment_mutation(tmp_path, mutation):
    """Follow-up review (both reviewers, reproduced): mutating the parent's
    environment before a spawn overrides what the child inherits exactly as
    `env=` does, and Guard 3a scanned straight through every one of these."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        f"import os\nimport subprocess\n{mutation}\nsubprocess.run(['x'])\n",
        encoding="utf-8",
    )

    violations = _find_env_mutation_violations(root)

    assert any(v.category == CATEGORY_ENV_MUTATION for v in violations)


def test_reading_os_environ_is_not_a_mutation(tmp_path):
    """The guard bans WRITES, not reads -- `resolve.py` legitimately reads
    two `MASON_*` keys, and a read-flagging guard would red the real tree."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        "import os\n"
        "ROOT = os.environ.get('MASON_CFE_ROOT')\n"
        "PY = os.environ['MASON_CFE_PYTHON']\n"
        "KEYS = list(os.environ)\n",
        encoding="utf-8",
    )

    assert _find_env_mutation_violations(root) == []


def test_mutating_an_unrelated_mapping_is_not_flagged(tmp_path):
    """Scoped to `os.environ`, not every dict named anything."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        "settings = {}\nsettings['A'] = 'b'\nsettings.update({'C': 'd'})\n",
        encoding="utf-8",
    )

    assert _find_env_mutation_violations(root) == []


# --- Shared file-reading robustness (covers all three guards, since they --
# --- share the same _read_source/_parse_source helpers) --------------------


def test_unreadable_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    """Follow-up review (Blind Hunter): `_read_source`'s `except OSError`
    branch shipped untested, and this was the only AST-scanning meta-test in
    the suite without the fixture its six siblings all carry (a dangling
    symlink is the sibling files' own chosen trigger)."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").symlink_to(root / "does-not-exist.py")

    with pytest.raises(AssertionError, match="unreadable"):
        _find_jfrog_env_var_references(root)


def test_non_utf8_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").write_bytes(b"\xff\xfe not valid utf-8 \x80\x81")

    with pytest.raises(AssertionError, match="not valid UTF-8"):
        _find_jfrog_env_var_references(root)


def test_invalid_syntax_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").write_text("def(:\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="invalid Python syntax"):
        _find_http_client_imports(root)


def test_a_utf8_bom_file_is_scanned_not_reported_as_unparseable(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_bytes(b'\xef\xbb\xbfMSG = "JFROG_API_KEY"\n')

    violations = _find_jfrog_env_var_references(root)

    assert any(v.category == CATEGORY_ENV_VAR_NAME for v in violations)
