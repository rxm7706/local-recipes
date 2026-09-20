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
a Python identifier. The trailing `_...` is OPTIONAL: a bare `JFROG` prefix
is how a whole credential family is read at once
(`{k: v for k, v in os.environ.items() if k.startswith("JFROG")}`), which
reads every `JFROG_*` variable while naming none of them (third review pass,
Edge Case Hunter, reproduced). `+`-concatenated chains of string constants
are folded before matching (follow-up review, both reviewers), since
`"JFROG" + "_API_KEY"` names the variable just as literally as one token
does; the parser already folds the adjacent-literal spelling (`"JFROG"
"_API_KEY"`) into a single constant. Folding applies to the outermost
*foldable* chain, not the outermost chain: `"JFROG" + "_API_KEY" + suffix`
has an unfoldable outer node whose left operand folds perfectly well, and
the first cut skipped that inner chain as "nested" and missed the read
entirely (third review pass, both reviewers, reproduced). A leaf that
matches on its own is still reported when the fold it belongs to does not
match, so folding can only ever ADD detections -- `"staging" +
"JFROG_API_KEY"` folds to text the alnum lookbehind rejects while the leaf
alone is a plain violation (third review pass, Blind Hunter, reproduced).
Known, accepted residual, disclosed rather than chased: a name that never
appears as a compile-time constant at all -- assembled character by
character, or reached via `getattr` -- evades a constant scan. Open-ended
dataflow analysis is out of proportion here, and no such shape exists in
this codebase.

This corrects an earlier residual that named `%`/`.format()`/`str.join`/
f-strings as evasions too (fourth review pass, Blind Hunter, each
reproduced against the real detector). All four are in fact FLAGGED, and
have been since the third pass made the `_...` suffix optional: every one of
them leaves a literal `"JFROG..."` fragment somewhere in the expression
(`f"JFROG_API_{suffix}"` -> `'JFROG_API_'`, `"{}_API_KEY".format("JFROG")`
-> `'JFROG'`), and the bare-prefix form matches it. This is the same
stale-disclosure defect class the third pass corrected for `os.execve`
below, and the same one `test_adapter_sole_caller.py` corrected for its own
f-string note -- with the reason spelled out there: a maintainer who trusts
a stale "this evades" note reads a true red as a false positive and exempts
it.

**Guard 2 -- HTTP-client import.** No `import`/`from ... import` of
`requests`, `httpx`, `urllib.request`, or `http.client` -- including the
"parent, then submodule" spelling (`from urllib import request`, `from http
import client`) and any SUBMODULE of a banned name (`import
requests.sessions`, `from requests.sessions import Session`, `import
httpx._client`). Submodule matching is the difference between a guard and a
speed bump: `import requests.sessions` binds the name `requests` with
`requests.get` fully callable, and an exact-set membership test scanned it
clean -- one dotted suffix defeated the whole guard (third review pass, both
reviewers, reproduced). Absolute imports only: a *relative* import (`from
.requests import helper`, `ImportFrom.level > 0`) names a local Mason module
that merely shares a banned name and is not the third-party client this
guard bans (follow-up review, both reviewers -- it was a false positive).
`_BANNED_HTTP_IMPORTS` is paired with an independently-spelled
`_REQUIRED_HTTP_IMPORTS` floor, mirroring
`test_adapter_sole_caller.py::_REQUIRED_SPAWN_CALL_NAMES`: the per-name
fixtures parametrize over the banned set itself, so without the floor,
deleting an entry deleted its own coverage and reopened the guard silently
(follow-up review, Edge Case Hunter, reproduced).

An `import` statement is not the only way to reach a module, so this guard
also flags a banned name spelled as a string constant passed as a call
ARGUMENT (fourth review pass, Blind Hunter, reproduced): `_dyn =
importlib.import_module` followed by `_dyn("requests")` gave `resolve.py` a
live HTTP client posting a bearer token with the entire suite green. Two
earlier passes rejected this family on the premise that
`test_dependency_direction.py`'s AD-4 guard bans dynamic imports
unconditionally -- true of the direct spellings those passes actually
tested, but that guard's own docstring declares the exception verbatim: "It
does not trace indirect rebinding". Every dynamic route must still name its
target as a string, so scanning arguments closes the family without tracing
any callable. ARGUMENTS specifically, not every constant: `cfe.py`'s
`CFE_IMPORT_FLOOR` legitimately names `"requests"` as CFE's own dependency,
probed inside the CFE interpreter and never imported by Mason, and a
blanket constant scan red the real tree on it.

Deliberately narrow (spec Design Notes): Mason holds zero HTTP-client
capability today, which structurally forecloses CFE's own `_http.py`
unconditional `JFROG_API_KEY` header-injection pattern from reaching Mason's
own surface. Not a general network-access ban -- Epic 3 is expected to add
scoped, non-CFE HTTP capability later and must loosen this guard explicitly
when that story lands. **Story 3.7 is that story.** It adds a narrow,
STRUCTURAL per-(file, module-name) allowlist, `_GUARD_2_HTTP_IMPORT_
ALLOWLIST` below: `urllib.request` is now permitted, but ONLY inside
`pypi_index.py` (the one module `package.py::ship_pypi`'s new PyPI-index
idempotence interrogation, AD-10, needs it in). `requests`/`httpx`/
`http.client` are NOT in that file's exempted set -- they stay banned even
inside `pypi_index.py`, and `urllib.request` stays banned in every OTHER
file exactly as before. This is a widening of WHO may import ONE already-
named client for ONE already-scoped reason, not a widening of the banned
set itself or of the deny-list's own narrow scope.

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

Exactly two allowlist entries (Story 2.9 widens this from one): `cfe.py`'s
own `run_streamed`-internal `Popen(..., env=dict(env) if env is not None
else None)` call (Story 1.10's sanctioned pass-through primitive --
`cfe.py`'s own docstring names it as such), and `cfe.py`'s own
`_invoke_captured`-internal `subprocess.run(..., env=dict(env) if env is
not None else None)` call (Story 2.9's second sanctioned pass-through site,
added so `recipe.py::submit()` can inject `CFE_RECIPES_ROOT` into the
child's environment for an out-of-tree recipe -- epic-2-context.md
Technical Decisions, correct-course 2026-08-10). Each is identified
structurally -- by walking its OWN named function's body in `cfe.py` and
permitting only the one call of its own kind found there -- not by file
alone, so an unrelated `env=` misuse elsewhere in `cfe.py` still gets
flagged (spec Design Notes: "targets call sites, not function signatures...
the property this guard protects is 'nobody currently exercises the
override,' which only a call-site scan can prove"), and each is checked
INDEPENDENTLY of the other: a regression at one site does not affect the
other's own coverage, and a synthetic test fixture defining only one of the
two named functions still gets that one site's protection in full (the
generalized lookup returns the empty set, not an error, for a function that
is absent or that contains zero matching calls). Both allowlist the `env=`
EXPRESSION, not merely the call's identity: the value must unparse to
exactly `_SANCTIONED_PASS_THROUGH_ENV_EXPR`. Identity alone was the guard's
largest hole (follow-up review, both reviewers, reproduced on the real
`cfe.py`) -- rewriting either sanctioned call's `env=` to `{}`, or to a
targeted `JFROG_*`-stripping comprehension, defeats AD-14 at the one site
that can defeat it while every OTHER guard test stays green -- proven
independently for each site by its own fixtures below.

*3b -- process-environment mutation.* No module mutates `os.environ` (or
`os.environb`, the bytes view of the identical POSIX environment) by
subscript assign/delete, by `|=`, by
`update`/`setdefault`/`pop`/`popitem`/`clear`, or by
`os.putenv`/`os.unsetenv`. Mutating the parent's environment before a spawn
overrides what the child inherits just as effectively as `env=`, and is the
more idiomatic way to do it -- 3a alone scanned clean through it (follow-up
review, both reviewers, reproduced). Binding targets are walked
recursively (tuple/list/starred unpacking, `for` targets, `with ... as`
targets, and a COMPREHENSION's own `for` target), mirroring
`test_no_recipe_knowledge.py::_bound_names_in_target`: the first cut
inspected only top-level targets, so `os.environ['JFROG_API_KEY'], ok =
token, True` scanned clean (third review pass, both reviewers, reproduced),
and the cut after that missed `[None for os.environ['TOKEN'] in [...]]`
because a comprehension carries its target on its own node type rather than
on `ast.For` (fourth review pass, both reviewers, reproduced).

The mapping is recognized through an ALIAS, not only as the two literal
spellings (fourth review pass, both reviewers, reproduced against the real
`cfe.py`): `_env = os.environ` followed by a targeted `del` of the
enterprise credential family is a complete AD-14 break in two lines, and it
scanned clean, as did `from os import environ as e`. `_env_alias_names`
resolves `as`-aliases and direct assignment chains to a fixed point, flow-
insensitively so it fails closed.

*3c -- explicit-environment process replacement.* No module calls the
`os.exec*e`/`os.spawn*e`/`os.posix_spawn[p]` family AT ALL. These are the
stdlib calls that take an explicit environment rather than inheriting one,
and Mason has no legitimate use for any of them -- `cfe.py`'s `run_streamed`
is the sanctioned spawn primitive (AD-3). They are banned unconditionally
rather than scanned for an `env=` keyword because the environment argument
is positional for all of them and positional-ONLY for
`os.posix_spawn`/`posix_spawnp`, so no keyword scan can reach it.

This replaces an earlier, FACTUALLY WRONG disclosure (third review pass,
both reviewers, reproduced): that residual claimed `env` is
"positional-only" for `os.execve` and that
`test_adapter_sole_caller.py`'s AD-3 guard "already bans them outside
`cfe.py`". Both halves are false. `inspect.signature(os.execve)` is
`(path, argv, env)` -- positional-OR-keyword, so `os.execve(p, argv,
env={...})` is accepted -- and AD-3 flags a spawn call only when one of its
arguments names a CFE path or a `_CFE_SCRIPTS` filename, so a spawn carrying
a credential dict but no CFE path is invisible to it. A residual accepted on
the strength of protection that was not there is worse than no disclosure.

Known, accepted residuals for Guard 3, not attempted here: `**kwargs`
unpacking, and `env` passed positionally to a `subprocess` API. Open-ended
dataflow analysis is out of proportion for this guard, and neither shape
appears anywhere in this codebase's actual call sites today.
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
CATEGORY_HTTP_MODULE_NAME = "http-client-module-name"
CATEGORY_ENV_OVERRIDE = "env-override"


def _read_source(path: Path) -> str:
    try:
        # utf-8-sig, matching every sibling meta-test's choice: a plain
        # utf-8 read leaves a BOM in the text and ast.parse rejects it as a
        # syntax error, reporting a perfectly runnable module as unscannable.
        return path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise AssertionError(
            f"{path}: unreadable ({exc}); the AD-14 credential-isolation guard cannot AST-scan this file"
        ) from exc
    except UnicodeDecodeError as exc:
        raise AssertionError(
            f"{path}: not valid UTF-8; the AD-14 credential-isolation guard cannot AST-scan this file"
        ) from exc


def _parse_source(source: str, path: Path) -> ast.Module:
    try:
        return ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise AssertionError(
            f"{path}: invalid Python syntax; the AD-14 credential-isolation guard cannot AST-scan this file"
        ) from exc


def _parse_file(path: Path) -> ast.Module:
    return _parse_source(_read_source(path), path)


# --- Guard 1: no JFROG_* environment-variable name anywhere -----------------

_JFROG_ENV_VAR_PATTERN = re.compile(r"(?<![0-9A-Za-z])JFROG(?:_[A-Z0-9_]*)?(?![0-9A-Za-z])", re.IGNORECASE)
"""Explicit alphanumeric lookbehind (excluding `_`), NOT `\\b` (review pass,
Edge Case Hunter): `_` is a word character, so `\\b` never fires beside one
and a prefixed name like `STAGING_JFROG_API_KEY` sailed through the original
pattern -- the identical underscore-adjacency bug `test_no_recipe_knowledge.py`
already documents fixing for its own gotcha/v1-field entries (via the same
"exclude alnum, but not underscore" lookaround), reintroduced here despite
this file's own module docstring claiming to mirror that guard.
Case-insensitive (review pass, Blind Hunter): `jfrog_api_key` names the same
credential-shaped variable, lowercased.
The `_...` suffix is OPTIONAL, with a matching alnum lookahead (third review
pass, Edge Case Hunter): requiring the trailing underscore meant
`os.environ.items() ... if k.startswith("JFROG")` -- the idiomatic way to
read a whole credential FAMILY at once -- scanned clean while naming no
single variable. The lookahead keeps the bare form from matching inside an
unrelated alphanumeric word."""


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


def _folded_concatenations(
    tree: ast.Module,
) -> tuple[list[tuple[ast.BinOp, str, list[ast.expr]]], set[int]]:
    """Every outermost FOLDABLE `+`-chain paired with the one text it
    evaluates to and its own leaves, plus the `id()`s of the constants those
    chains consumed (follow-up review, both reviewers:
    `os.environ.get("JFROG" + "_API_KEY")` scanned clean because `ast.walk`
    sees each half separately and neither matches alone).

    "Outermost foldable", not "outermost" (third review pass, both
    reviewers, reproduced): the first cut marked every `+`-operand that was
    itself a `+`-chain as nested BEFORE knowing whether its parent folded,
    so `"JFROG" + "_API_KEY" + suffix` -- an unfoldable outer node over a
    perfectly foldable inner one -- skipped the inner chain as nested,
    folded nothing, and scanned clean. One extra operand defeated the whole
    fix. Nesting is now derived only from chains that actually fold.

    `consumed_ids` exists to keep one expression counted once: the caller
    skips these leaves in its plain constant pass, so `"JFROG_" + "API" +
    "_KEY"` reports once (folded) rather than twice (folded, plus the leaf
    `"JFROG_"` that happens to match alone). The caller re-scans the leaves
    itself when the FOLD does not match, so this can only ever add
    detections -- see `_find_jfrog_env_var_references`."""
    foldable: dict[int, tuple[ast.BinOp, list[ast.expr]]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp):
            continue
        leaves = _add_chain_leaves(node)
        if leaves is not None:
            foldable[id(node)] = (node, leaves)

    nested_ids: set[int] = set()
    for node, _leaves in foldable.values():
        for operand in (node.left, node.right):
            if id(operand) in foldable:
                nested_ids.add(id(operand))

    folded: list[tuple[ast.BinOp, str, list[ast.expr]]] = []
    consumed_ids: set[int] = set()
    for node_id, (node, leaves) in foldable.items():
        if node_id in nested_ids:
            continue
        folded.append((node, "".join(_constant_text_value(leaf) or "" for leaf in leaves), leaves))
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
                violations.append(Violation(path, node.lineno, CATEGORY_ENV_VAR_NAME, match.group()))

        for chain, text, leaves in folded:
            match = _JFROG_ENV_VAR_PATTERN.search(text)
            if match is None:
                # The fold did not match, but a LEAF still can: `"staging" +
                # "JFROG_API_KEY"` folds to `stagingJFROG_API_KEY`, which the
                # alnum lookbehind correctly rejects, while the leaf alone is
                # a plain violation the constant pass would have caught if
                # folding had not consumed it (third review pass, Blind
                # Hunter, reproduced -- folding was a NET WEAKENING for this
                # shape). Reported once per chain, so the "one expression,
                # one violation" property the fixtures pin still holds.
                match = next(
                    (
                        m
                        for m in (_JFROG_ENV_VAR_PATTERN.search(_constant_text_value(leaf) or "") for leaf in leaves)
                        if m is not None
                    ),
                    None,
                )
            if match is not None:
                violations.append(Violation(path, chain.lineno, CATEGORY_ENV_VAR_NAME, match.group()))
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
`test_adapter_sole_caller.py::_REQUIRED_SPAWN_CALL_NAMES`, which carries this
same duplication rationale inline at its own definition (third review pass,
Edge Case Hunter: the first cut cited ledger entry `DW-1-10` for it, which is
actually about an owed follow-up review of Story 1.10 and says nothing about
set duplication -- verified against the ledger)."""


_GUARD_2_HTTP_IMPORT_ALLOWLIST: dict[str, frozenset[str]] = {
    "pypi_index.py": frozenset({"urllib.request"}),
}
"""Per-(file, module-name) exemptions from Guard 2's import ban (Story 3.7):
`urllib.request` is permitted ONLY inside `pypi_index.py` -- the one module
Guard 2's own docstring above pre-authorizes ("Epic 3 is expected to add
scoped, non-CFE HTTP capability later and must loosen this guard explicitly
when that story lands"). `requests`/`httpx`/`http.client` are deliberately
NOT in this file's exempted set -- they stay banned even inside
`pypi_index.py` (spec Always boundary): PyPI's own public JSON index needs
nothing beyond stdlib `urllib.request.urlopen`, so there is no legitimate
reason for a third-party HTTP client to appear there either.

Keyed by bare FILENAME, not a resolved full path (mirrors `_find_env_
override_violations`'s own `cfe.py` special-case just above, which also
special-cases by name against `root` rather than an absolute path):
`pypi_index.py` is a single well-known module name, so a collision with an
unrelated same-named file elsewhere in the tree is not a realistic risk the
extra path-resolution machinery would be worth here.

`test_guard_2_allowlist_has_not_widened_past_its_pinned_ceiling` below is
this allowlist's own anti-shrink -- more precisely anti-WIDEN -- floor,
mirroring `_REQUIRED_HTTP_IMPORTS`/`_REQUIRED_ENV_OVERRIDE_CALL_NAMES`'s
independently-spelled-floor pattern used throughout this file: a live set
that is free to widen on its own, with nothing else in the file noticing,
is exactly the failure mode those floors exist to catch -- inverted here,
since THIS set narrows the guard rather than widening it, so what must be
pinned is a CEILING it may never silently exceed."""

_GUARD_2_ALLOWLIST_CEILING: dict[str, frozenset[str]] = {
    "pypi_index.py": frozenset({"urllib.request"}),
}
"""Independently-spelled ceiling mirroring `_GUARD_2_HTTP_IMPORT_ALLOWLIST`
exactly (own docstring above): a widening edit to the live allowlist --
adding a new file key, or adding `requests`/`httpx`/`http.client` to
`pypi_index.py`'s own exempted set -- must also touch this independently-
spelled copy, with the rationale for the widening spelled out in that diff.
Deriving one dict from the other would let a single edit widen both at
once, the same self-deleting-fixture failure mode `_REQUIRED_HTTP_IMPORTS`'s
own docstring documents at length for the banned set."""


def _is_http_import_allowlisted(path: Path, module_name: str) -> bool:
    """True when `module_name` (a name Guard 2 would otherwise flag) is
    exempted for `path` by `_GUARD_2_HTTP_IMPORT_ALLOWLIST` (module
    docstring). `module_name` matches an allowlisted entry OR any of ITS
    submodules -- the same dotted-boundary rule `_is_banned_http_module`
    itself applies to the ban -- so `urllib.request.foo` is exactly as
    exempt as the bare `urllib.request` inside `pypi_index.py`."""
    allowed = _GUARD_2_HTTP_IMPORT_ALLOWLIST.get(path.name, frozenset())
    return any(module_name == allowed_name or module_name.startswith(f"{allowed_name}.") for allowed_name in allowed)


def _is_banned_http_module(name: str) -> bool:
    """True for a banned client itself or ANY submodule of one (third review
    pass, both reviewers, reproduced): `import requests.sessions` binds the
    name `requests` with `requests.get` fully callable, and `from
    requests.sessions import Session` hands back a complete session object --
    both scanned clean under exact set membership, which made one dotted
    suffix the cheapest possible defeat of this guard."""
    return any(name == banned or name.startswith(f"{banned}.") for banned in _BANNED_HTTP_IMPORTS)


def _banned_module_name_arguments(tree: ast.Module) -> list[tuple[ast.expr, str]]:
    """Every string constant naming a banned client that is passed as an
    ARGUMENT to some call, paired with the name it spells.

    Fourth review pass (Blind Hunter, reproduced): a rebound handle on
    `importlib.import_module` reaches any module with no `import` statement
    at all, and `test_dependency_direction.py`'s AD-4 guard -- cited twice
    by earlier passes as the backstop -- declares in its own docstring that
    it "does not trace indirect rebinding". Every dynamic route
    (`import_module`, `__import__`, `globals()["__import__"]`, or any
    rebinding of any of them) must still hand the target's name to a
    callable, so scanning call ARGUMENTS closes the family without tracing a
    single callable.

    Arguments, not every constant in the file: `cfe.py`'s `CFE_IMPORT_FLOOR`
    legitimately names `"requests"` as a data-table entry -- CFE's own
    dependency floor, probed inside the CFE interpreter, never imported by
    Mason -- and a blanket constant scan red the real tree on it (caught by
    this file's own real-tree assertion when the first cut of this patch
    landed). A guard whose first red is a false positive is one a maintainer
    weakens.

    Residuals, disclosed not chased: a name assembled at runtime, or read
    out of a data structure and passed indirectly, is open-ended dataflow --
    the same boundary Guard 1 draws."""
    found: dict[int, tuple[ast.expr, str]] = {}
    for call in ast.walk(tree):
        if not isinstance(call, ast.Call):
            continue
        for argument in [*call.args, *(kw.value for kw in call.keywords)]:
            for node in ast.walk(argument):
                text = _constant_text_value(node)
                if text is not None and _is_banned_http_module(text):
                    # Keyed by node identity: a nested call's own arguments
                    # are walked by both calls, and one string is one
                    # violation.
                    found[id(node)] = (node, text)
    return list(found.values())


def _find_http_client_imports(root: Path) -> list[Violation]:
    violations: list[Violation] = []
    for path in sorted(root.rglob("*.py")):
        tree = _parse_file(path)
        for node, text in _banned_module_name_arguments(tree):
            if _is_http_import_allowlisted(path, text):
                continue
            violations.append(Violation(path, node.lineno, CATEGORY_HTTP_MODULE_NAME, text))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_banned_http_module(alias.name) and not _is_http_import_allowlisted(
                        path,
                        alias.name,
                    ):
                        violations.append(Violation(path, node.lineno, CATEGORY_HTTP_IMPORT, alias.name))
            # `node.level == 0` -- absolute imports only. A relative import
            # (`from .requests import helper`) names a LOCAL Mason module that
            # merely shares the name, not the banned third-party client
            # (follow-up review, both reviewers: it was a false positive, and
            # the cheapest repair under a red guard is to weaken the guard).
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module is not None:
                if _is_banned_http_module(node.module):
                    if not _is_http_import_allowlisted(path, node.module):
                        violations.append(Violation(path, node.lineno, CATEGORY_HTTP_IMPORT, node.module))
                    continue
                # The "parent, then submodule" spelling of the two dotted
                # names -- `from urllib import request` / `from http import
                # client` reach the identical submodule as `import
                # urllib.request` / `import http.client`. Only reached when
                # the module itself is clean, so one import is never counted
                # twice.
                for alias in node.names:
                    dotted = f"{node.module}.{alias.name}"
                    if _is_banned_http_module(dotted) and not _is_http_import_allowlisted(
                        path,
                        dotted,
                    ):
                        violations.append(Violation(path, node.lineno, CATEGORY_HTTP_IMPORT, dotted))
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
        "subprocess_exec",
        "subprocess_shell",
        "run_streamed",
    }
)
"""Matched on bare attribute/function name only, no receiver resolution --
the same documented residual `test_adapter_sole_caller.py`'s spawn-call
guard accepts. Every spawn API in this project's reach that takes `env` as a
KEYWORD. The original set held only `run`/`Popen`/`run_streamed` (the three
the spec's I/O matrix names by example), so `subprocess.check_output(...,
env={...})` -- a plain, unexotic override -- scanned clean (follow-up review,
Edge Case Hunter, reproduced). `asyncio`'s low-level
`loop.subprocess_exec`/`subprocess_shell` forward `**kwargs` straight to
`subprocess.Popen`, so `env=` is a genuine keyword there; both names are
already in `test_adapter_sole_caller.py::_REQUIRED_SPAWN_CALL_NAMES` and
were missing here (third review pass, Blind Hunter, reproduced). The
`os.exec*`/`os.spawn*` family is deliberately absent from THIS set and
banned outright by `_BANNED_EXPLICIT_ENV_SPAWN_FUNCTIONS` below instead."""

_REQUIRED_ENV_OVERRIDE_CALL_NAMES = frozenset(
    {
        "run",
        "Popen",
        "call",
        "check_call",
        "check_output",
        "create_subprocess_exec",
        "create_subprocess_shell",
        "subprocess_exec",
        "subprocess_shell",
        "run_streamed",
    }
)
"""Independently spelled floor, same rationale as `_REQUIRED_HTTP_IMPORTS`
and `test_adapter_sole_caller.py::_REQUIRED_SPAWN_CALL_NAMES`: narrowing the
recognized set must also delete the name here, with the rationale in that
diff."""

CATEGORY_EXPLICIT_ENV_SPAWN = "explicit-env-spawn"

_BANNED_EXPLICIT_ENV_SPAWN_FUNCTIONS = frozenset(
    {
        "execle",
        "execlpe",
        "execve",
        "execvpe",
        "spawnle",
        "spawnlpe",
        "spawnve",
        "spawnvpe",
        "posix_spawn",
        "posix_spawnp",
    }
)
"""The `os` spawn/exec calls that take an EXPLICIT environment rather than
inheriting one -- banned outright, not scanned for an `env=` keyword (third
review pass, both reviewers, reproduced). The environment argument is
positional for all of them and positional-ONLY for
`os.posix_spawn`/`posix_spawnp`, so no keyword-name scan can reach it, and
`os.posix_spawn(path, argv, {"JFROG_API_KEY": tok})` was a complete,
one-line AD-14 break that every guard in this file reported clean. An
outright ban needs no arity analysis and costs nothing: `cfe.py`'s
`run_streamed` is Mason's sanctioned spawn primitive (AD-3), so no module
has any legitimate use for these. The non-`e` variants (`execv`, `spawnl`,
...) are absent because they cannot carry an explicit environment at all:
they inherit, which is precisely what AD-14 requires, so they are outside
this guard's rule rather than delegated to another one. (Fourth review
pass, Edge Case Hunter: the original wording said "AD-3's own guard owns
them", which is the same false-backstop claim the paragraph directly above
had just corrected for `os.execve` -- AD-3 fires only when a spawn's
arguments name a CFE path or script, so it does not flag a bare
`os.execv("/bin/sh", ...)` either. Nothing needs it to: an inheriting spawn
cannot break credential isolation.)"""

_REQUIRED_EXPLICIT_ENV_SPAWN_FUNCTIONS = frozenset(
    {
        "execle",
        "execlpe",
        "execve",
        "execvpe",
        "spawnle",
        "spawnlpe",
        "spawnve",
        "spawnvpe",
        "posix_spawn",
        "posix_spawnp",
    }
)
"""Independently spelled floor, same rationale as `_REQUIRED_HTTP_IMPORTS`."""

_SANCTIONED_PASS_THROUGH_ENV_EXPR = "dict(env) if env is not None else None"
"""The one `env=` expression every Guard-3a allowlist entry accepts (Story
2.9 widened this docstring from "the allowlist" (singular) to "both
entries"; PR #1354 widens it again to four -- the expression text itself is
unchanged and shared verbatim across every site), compared as `ast.unparse`
text. Story 1.10's sanctioned pass-through, mirrored exactly by each later
site: it forwards the caller's own `env` argument and otherwise hands the
call a bare `None`, which is exactly "inherit the parent environment".
Pinning the EXPRESSION, not just the call's identity, is the fix for this
guard's largest hole (follow-up review, both reviewers, reproduced against
the real `cfe.py`): allowlisting by identity meant a sanctioned call could
be rewritten to `env={}` or to a `JFROG_*`-stripping comprehension --
defeating AD-14 at the one site that can defeat it -- with all 34 guard
tests still green."""


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


def _named_function_def(
    tree: ast.Module,
    name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """The (sync or async) function definition named `name`, anywhere in
    `tree` -- generalized (Story 2.9) from the original
    `_run_streamed_function_def`, which hardcoded the name `"run_streamed"`,
    so the identical structural lookup serves every one of Guard 3a's
    sanctioned sites: `run_streamed`, `_invoke_captured`, `build_native`,
    and `build_docker` (the latter two added by PR #1354).

    `AsyncFunctionDef` too (third review pass, Edge Case Hunter,
    reproduced): matching only `ast.FunctionDef` fails CLOSED -- an `async
    def run_streamed` reds the guard on the sanctioned call itself rather
    than opening a hole -- but a false positive whose cheapest repair is to
    weaken the guard is exactly the failure mode this file designs against,
    and `_docstring_string_ids` above already handles both node types."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _allowlisted_call_ids_in_named_function(
    tree: ast.Module,
    function_name: str,
    call_name: str,
) -> set[int]:
    """One Guard-3a allowlist entry: `id()` of the one sanctioned
    `call_name` call inside `function_name`'s own body -- structural, not
    file-wide (module docstring), so a second, unrelated `env=` misuse
    elsewhere in the same file is still caught by the caller below.
    Generalized (Story 2.9) from the original `_allowlisted_popen_call_ids`,
    which hardcoded `"run_streamed"`/`"Popen"`: this same per-function check
    now backs all four sanctioned sites (`run_streamed`/`Popen`,
    `_invoke_captured`/`run`, `build_native`/`run_streamed`, and
    `build_docker`/`run_streamed` -- the latter two added by PR #1354), each
    called independently by `_allowlisted_env_override_ids` below.

    Returns the empty set -- gracefully, not an error -- both when
    `function_name` is not defined anywhere in `tree` at all (the original
    behavior, e.g. for any file that isn't `cfe.py`) AND when it IS defined
    but contains zero calls named `call_name` (the new case this
    generalization must also handle gracefully: before Story 2.9 gives
    `_invoke_captured` its own `env=`-passing call, `cfe.py` has a live
    `run_streamed` entry and a `_invoke_captured` with no matching call at
    all -- the caller below must not error or misbehave over that).

    Fails CLOSED, not open (review pass, Blind Hunter): if
    `function_name`'s body contains more than one call named `call_name`,
    NONE is allowlisted. The original version allowlisted every such call
    found by location alone, regardless of count -- so a second, hostile
    call planted inside the same function body was silently allowlisted
    alongside the one legitimate call, the exact regression this guard
    exists to catch. The allowlist's whole premise is "exactly one
    sanctioned pass-through call in THIS function"; a second call (however
    it got there) invalidates that premise for this function alone -- the
    OTHER sanctioned site, if any, is checked independently and is
    unaffected.

    Allowlists the `env=` EXPRESSION, not the call's identity (follow-up
    review, both reviewers): the value must unparse to exactly
    `_SANCTIONED_PASS_THROUGH_ENV_EXPR`. Identity alone meant that editing
    the one sanctioned call's `env=` -- to `{}`, or to a targeted
    `JFROG_*`-stripping comprehension -- passed every guard test, at the
    single call site where AD-14 can actually be broken."""
    func = _named_function_def(tree, function_name)
    if func is None:
        return set()
    matching_calls = [
        node
        for node in ast.walk(func)
        if node is not func and isinstance(node, ast.Call) and _call_name(node) == call_name
    ]
    if len(matching_calls) != 1:
        return set()
    env_value = _env_kwarg_value(matching_calls[0])
    if env_value is None or _is_bare_none_literal(env_value):
        # Not flagged by the caller anyway -- nothing to allowlist.
        return set()
    if ast.unparse(env_value) != _SANCTIONED_PASS_THROUGH_ENV_EXPR:
        return set()
    return {id(matching_calls[0])}


def _allowlisted_env_override_ids(tree: ast.Module) -> set[int]:
    """The union of all four Guard-3a allowlist entries (Story 2.9 renamed
    this from `_allowlisted_popen_call_ids`, which covered only
    `run_streamed`'s `Popen` call): `run_streamed`'s own `Popen(...)` call,
    `_invoke_captured`'s own `run(...)` (`subprocess.run`) call, and
    `build_native`'s/`build_docker`'s own `run_streamed(...)` calls. Each is
    checked independently by `_allowlisted_call_ids_in_named_function`
    above, so a regression at one site (a second call planted in its body,
    a rewritten `env=` expression) does not affect any other site's own
    coverage.

    The `build_native`/`build_docker` entries were added during local-recipes
    PR #1354's CI-failure remediation (2026-09-14): Story 44.7's
    factory-island wiring had both functions forwarding their own `env`
    parameter into `run_streamed` since the story landed, but the CI job
    that runs this guard hadn't executed on any push to `main` for five days
    (a GitHub Actions billing outage), so the violation went undetected
    through ~260 merged PRs. `cfe.py`'s call sites were changed to the exact
    `_SANCTIONED_PASS_THROUGH_ENV_EXPR` shape (previously a bare `env=env`)
    so this extension reuses the identical, already-reviewed expression
    check -- it does not loosen it -- and each entry still requires exactly
    one matching call in its named function's body."""
    return (
        _allowlisted_call_ids_in_named_function(tree, "run_streamed", "Popen")
        | _allowlisted_call_ids_in_named_function(tree, "_invoke_captured", "run")
        | _allowlisted_call_ids_in_named_function(tree, "build_native", "run_streamed")
        | _allowlisted_call_ids_in_named_function(tree, "build_docker", "run_streamed")
    )


# --- Guard 3b: no mutation of the parent's own process environment ----------

CATEGORY_ENV_MUTATION = "env-mutation"

_ENV_MUTATING_METHODS = frozenset(
    {
        "update",
        "setdefault",
        "pop",
        "popitem",
        "clear",
        "__setitem__",
        "__delitem__",
        "__ior__",
    }
)
_ENV_MUTATING_FUNCTIONS = frozenset({"putenv", "unsetenv"})

_REQUIRED_ENV_MUTATING_METHODS = frozenset(
    {
        "update",
        "setdefault",
        "pop",
        "popitem",
        "clear",
        "__setitem__",
        "__delitem__",
        "__ior__",
    }
)
_REQUIRED_ENV_MUTATING_FUNCTIONS = frozenset({"putenv", "unsetenv"})
"""Independently-spelled floors for Guard 3b, mirroring
`_REQUIRED_HTTP_IMPORTS`/`_REQUIRED_ENV_OVERRIDE_CALL_NAMES` (third review
pass, Blind Hunter): 3b was the only guard in this file without one. It is
protected today only incidentally, because
`test_detector_fires_on_each_process_environment_mutation` hardcodes its
mutation strings instead of deriving them -- a future tidy-up to
`@parametrize(sorted(_ENV_MUTATING_METHODS))` would reintroduce exactly the
self-deleting-fixture bug this file already documents twice. The per-name
fixture below therefore parametrizes over THIS floor, never over the live
set (fourth review pass, Blind Hunter: three of the seven names --
`popitem`, `__setitem__`, `__delitem__` -- had no detection fixture at all,
and "membership in the frozenset is not detection" is this file's own
repeatedly-stated standard).

`__ior__` is the explicit-dunder spelling of the `|=` operator the third
pass fixed as a HIGH (fourth review pass, both reviewers, reproduced): the
operator form was caught while `os.environ.__ior__({...})` -- the identical
call, spelled out -- scanned clean, even though `__setitem__`/`__delitem__`
were already listed here for exactly that reason."""

_ENV_MAPPING_NAMES = frozenset({"environ", "environb"})
"""`os.environb` is the BYTES view of the identical POSIX environment and
`putenv`s through it, so `os.environb[b"JFROG_API_KEY"] = tok` overrides
what a spawned child inherits exactly as `os.environ[...]` does -- and an
exact `== "environ"` match scanned it clean (third review pass, both
reviewers, reproduced against a real child process)."""


def _is_os_environ(node: ast.expr, alias_names: frozenset[str]) -> bool:
    """`os.environ`/`os.environb` (attribute form) or any bare NAME bound to
    one (`alias_names`, which always contains the two unaliased spellings).

    Attribute matching stays pinned to `_ENV_MAPPING_NAMES` rather than the
    alias set: a local alias is a bare name by construction, and matching
    `anything.<alias>` too would turn one `data = os.environ` line into a
    false positive on every unrelated `foo.data[...] = x` in the file. The
    receiver of the attribute form itself is still unresolved -- the same
    residual the rest of this file accepts."""
    if isinstance(node, ast.Attribute):
        return node.attr in _ENV_MAPPING_NAMES
    return isinstance(node, ast.Name) and node.id in alias_names


def _plain_names_in_target(node: ast.expr) -> list[str]:
    """Every bare `Name` bound by a binding target, recursing through
    tuple/list/starred unpacking (`a, (b, *c) = ...`)."""
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        return [found for elt in node.elts for found in _plain_names_in_target(elt)]
    if isinstance(node, ast.Starred):
        return _plain_names_in_target(node.value)
    return []


def _env_alias_names(tree: ast.Module) -> frozenset[str]:
    """Every name in `tree` that refers to the process environment mapping:
    `environ`/`environb` themselves, any `from os import environ as X`
    alias, and any name assigned directly from one of those (transitively,
    to a fixed point, so `a = os.environ; b = a` reaches `b`).

    Fourth review pass, both reviewers, reproduced against the real
    `cfe.py`: matching only the two literal spellings meant ONE binding line
    defeated the whole of Guard 3b --

        _env = os.environ
        for _k in [k for k in _env if k.startswith("ARTIFACTORY")]:
            del _env[_k]

    is Mason stripping a credential family out of the environment the CFE
    child inherits, a complete AD-14 break at the seam this story exists to
    protect, and the entire suite stayed green. `from os import environ as
    e` was the same hole one keyword shorter (the unaliased `from os import
    environ` was already caught, which is what made the gap specific to
    rebinding).

    Deliberately flow-INSENSITIVE, so it fails closed: a name is treated as
    the environment from the moment any assignment binds it to one, even if
    a later line rebinds it to something else. That direction costs a
    hypothetical false positive on `e = os.environ; e = {}; e['x'] = 1`; the
    other direction costs the guard. Residual, disclosed not chased: binding
    through a container, a call, or an instance attribute
    (`self._env = os.environ`) is open-ended dataflow and is not tracked."""
    names = set(_ENV_MAPPING_NAMES)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "os" and node.level == 0:
            for alias in node.names:
                if alias.name in _ENV_MAPPING_NAMES:
                    names.add(alias.asname or alias.name)

    while True:
        added = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                value, targets = node.value, node.targets
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                value, targets = node.value, [node.target]
            else:
                continue
            if not _is_os_environ(value, frozenset(names)):
                continue
            for target in targets:
                for name in _plain_names_in_target(target):
                    if name not in names:
                        names.add(name)
                        added = True
        if not added:
            return frozenset(names)


def _is_os_environ_subscript(node: ast.expr, alias_names: frozenset[str]) -> bool:
    return isinstance(node, ast.Subscript) and _is_os_environ(node.value, alias_names)


def _mutated_env_targets(node: ast.expr | None, alias_names: frozenset[str]) -> list[ast.expr]:
    """Every `os.environ[...]` subscript reachable from a binding target,
    recursing through tuple/list/starred unpacking -- mirroring
    `test_no_recipe_knowledge.py::_bound_names_in_target`, which already
    recurses for exactly this reason (third review pass, both reviewers,
    reproduced): the first cut inspected only top-level targets, so
    `os.environ['JFROG_API_KEY'], ok = token, True` scanned clean."""
    if node is None:
        return []
    if _is_os_environ_subscript(node, alias_names):
        return [node]
    if isinstance(node, (ast.Tuple, ast.List)):
        return [found for elt in node.elts for found in _mutated_env_targets(elt, alias_names)]
    if isinstance(node, ast.Starred):
        return _mutated_env_targets(node.value, alias_names)
    return []


def _find_env_mutation_violations(root: Path) -> list[Violation]:
    """Mutating `os.environ` (or calling `os.putenv`) before a spawn changes
    what the child inherits exactly as `env=` does, and is the more
    idiomatic way to do it -- Guard 3a alone scanned clean straight through
    `os.environ['X'] = token; subprocess.run(argv)` (follow-up review, both
    reviewers, reproduced)."""
    violations: list[Violation] = []
    for path in sorted(root.rglob("*.py")):
        tree = _parse_file(path)
        alias_names = _env_alias_names(tree)
        for node in ast.walk(tree):
            targets: list[ast.expr] = []
            if isinstance(node, (ast.Assign, ast.Delete)):
                targets = list(node.targets)
            elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
                targets = [node.target]
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                targets = [node.target]
            elif isinstance(node, ast.withitem):
                targets = [node.optional_vars] if node.optional_vars else []
            elif isinstance(node, ast.comprehension):
                # `[None for os.environ['TOKEN'] in ['scrubbed']]` binds the
                # subscript exactly as the statement `for` does, and mutates
                # the real environment -- but `ast.comprehension` is its own
                # node type, so it fell through the `For`/`AsyncFor` branch
                # the third pass added for precisely this shape (fourth
                # review pass, both reviewers, reproduced against a real
                # child process). Covers list/set/dict comprehensions and
                # generator expressions alike, which all carry this node.
                targets = [node.target]
            matched = [t for target in targets for t in _mutated_env_targets(target, alias_names)]
            if matched:
                # The matched TARGET's lineno, not the statement's:
                # `ast.withitem` carries no `lineno` at all, so anchoring on
                # the statement raised `AttributeError` out of the scanner
                # instead of reporting the violation. Every `expr` node has
                # one, and the target is the more precise anchor anyway.
                violations.append(
                    Violation(
                        path,
                        matched[0].lineno,
                        CATEGORY_ENV_MUTATION,
                        f"{ast.unparse(matched[0])} (assignment target)",
                    )
                )
                continue
            # `os.environ |= {...}` -- the operator that IS `update`
            # (`MutableMapping.__ior__` calls `self.update`, which reaches
            # `os._Environ.__setitem__` and `putenv`). Its target is the bare
            # `os.environ` attribute, not a subscript, so it fell through
            # both branches and scanned clean (third review pass, both
            # reviewers, reproduced).
            if isinstance(node, ast.AugAssign) and _is_os_environ(node.target, alias_names):
                violations.append(
                    Violation(
                        path,
                        node.lineno,
                        CATEGORY_ENV_MUTATION,
                        f"os.environ {type(node.op).__name__}=",
                    )
                )
                continue
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr in _ENV_MUTATING_METHODS
                and _is_os_environ(func.value, alias_names)
            ):
                violations.append(Violation(path, node.lineno, CATEGORY_ENV_MUTATION, f"{ast.unparse(func)}()"))
            elif _call_name(node) in _ENV_MUTATING_FUNCTIONS:
                # Reported as its own source text, not as `os.<name>()`
                # (third review pass, Blind Hunter): this branch matches a
                # bare call NAME with no receiver check -- deliberately
                # conservative, but it must not name a module it never
                # confirmed was involved.
                violations.append(Violation(path, node.lineno, CATEGORY_ENV_MUTATION, f"{ast.unparse(func)}()"))
    return violations


def _find_env_override_violations(root: Path) -> list[Violation]:
    cfe_path = (root / "cfe.py").resolve()
    violations: list[Violation] = []
    for path in sorted(root.rglob("*.py")):
        tree = _parse_file(path)
        allowlisted_ids = _allowlisted_env_override_ids(tree) if path.resolve() == cfe_path else set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _call_name(node) in _BANNED_EXPLICIT_ENV_SPAWN_FUNCTIONS:
                violations.append(
                    Violation(
                        path,
                        node.lineno,
                        CATEGORY_EXPLICIT_ENV_SPAWN,
                        f"{ast.unparse(node.func)}()",
                    )
                )
                continue
            if not _is_call_of_interest(node):
                continue
            if id(node) in allowlisted_ids:
                continue
            env_value = _env_kwarg_value(node)
            if env_value is None or _is_bare_none_literal(env_value):
                continue
            # `ast.unparse`, not `ast.dump` (third review pass, Blind Hunter,
            # reproduced): this guard's most likely real-world red is a
            # benign reformat of `cfe.py`'s sanctioned pass-through, and a
            # raw `IfExp(test=Name(id='env', ...))` dump gave a maintainer no
            # signal distinguishing "you broke AD-14" from "you reformatted a
            # line" -- the message must name the expected expression, since
            # "the cheapest repair under a red guard is to weaken the guard".
            violations.append(Violation(path, node.lineno, CATEGORY_ENV_OVERRIDE, ast.unparse(env_value)))
    return violations


# --- The three real-tree assertions (FR-6, NFR-2, AD-14) --------------------


def _assert_scanning_something(root: Path) -> None:
    # Guard the guard: a stale PKG_ROOT would make every real-tree assertion
    # below pass vacuously (mirrors every sibling meta-test's own check).
    assert root.is_dir(), f"AD-14 credential-isolation guard is scanning nothing -- package root moved? {root}"
    assert list(root.rglob("*.py")), (
        f"AD-14 credential-isolation guard found zero modules under {root} "
        "-- it would pass vacuously; has the package moved or been renamed?"
    )


def test_no_jfrog_env_var_reference_in_the_real_tree():
    _assert_scanning_something(PKG_ROOT)
    violations = _find_jfrog_env_var_references(PKG_ROOT)
    assert not violations, "AD-14: no module may read a JFROG_* environment variable; found:\n" + "\n".join(
        f"  {v.path}:{v.lineno} matched {v.detail!r}" for v in violations
    )


def test_no_http_client_import_in_the_real_tree():
    _assert_scanning_something(PKG_ROOT)
    violations = _find_http_client_imports(PKG_ROOT)
    assert not violations, (
        "AD-14: no module may import requests/httpx/urllib.request/http.client, "
        "nor name one as a string (which is how every dynamic import reaches "
        "it); found:\n" + "\n".join(f"  {v.path}:{v.lineno} [{v.category}] {v.detail!r}" for v in violations)
    )


def test_no_unallowlisted_env_override_in_the_real_tree():
    _assert_scanning_something(PKG_ROOT)
    violations = _find_env_override_violations(PKG_ROOT)
    assert not violations, (
        "AD-14: env= on a spawn call must be absent or the bare literal "
        "None, and no module may call the os.exec*e/spawn*e/posix_spawn "
        "family at all. The TWO allowlisted sites are cfe.py's own "
        "run_streamed-internal Popen call and its own _invoke_captured-"
        "internal subprocess.run call, each of whose env= must unparse to "
        f"exactly {_SANCTIONED_PASS_THROUGH_ENV_EXPR!r}. Found:\n"
        + "\n".join(f"  {v.path}:{v.lineno} [{v.category}] {v.detail}" for v in violations)
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


def test_guard_2_allowlist_has_not_widened_past_its_pinned_ceiling():
    """Story 3.7's own anti-shrink floor for the Guard 2 allowlist, inverted
    (`_GUARD_2_HTTP_IMPORT_ALLOWLIST`'s own docstring): the LIVE allowlist
    is the thing under test here, and `_GUARD_2_ALLOWLIST_CEILING` is the
    independently-spelled pin it must never silently exceed. A widening
    edit -- a new file key, or a new exempted module name added to an
    existing file's set -- must also touch the ceiling, with the rationale
    for the widening spelled out in that diff, mirroring every other
    `_REQUIRED_*`-floor test in this file."""
    for file_name, modules in _GUARD_2_HTTP_IMPORT_ALLOWLIST.items():
        ceiling_modules = _GUARD_2_ALLOWLIST_CEILING.get(file_name, frozenset())
        widened = modules - ceiling_modules
        assert not widened, (
            f"{file_name}'s Guard 2 allowlist has widened beyond its pinned "
            f"ceiling; new entries: {sorted(widened)}. Widening the "
            "allowlist must also update _GUARD_2_ALLOWLIST_CEILING, with the "
            "rationale in that diff."
        )
    extra_files = set(_GUARD_2_HTTP_IMPORT_ALLOWLIST) - set(_GUARD_2_ALLOWLIST_CEILING)
    assert not extra_files, (
        f"Guard 2's allowlist gained new file key(s) not present in its pinned ceiling: {sorted(extra_files)}."
    )


def test_env_override_call_names_covers_the_required_floor():
    missing = _REQUIRED_ENV_OVERRIDE_CALL_NAMES - _ENV_OVERRIDE_CALL_NAMES
    assert not missing, (
        "the env-override guard no longer recognizes every spawn call name it "
        f"was specified with; missing: {sorted(missing)}. Widening the set is "
        "free; narrowing it must also delete the name from "
        "_REQUIRED_ENV_OVERRIDE_CALL_NAMES, with the rationale in that diff."
    )


def test_explicit_env_spawn_functions_covers_the_required_floor():
    missing = _REQUIRED_EXPLICIT_ENV_SPAWN_FUNCTIONS - _BANNED_EXPLICIT_ENV_SPAWN_FUNCTIONS
    assert not missing, (
        "the explicit-environment spawn ban no longer covers every os.exec*e/"
        f"spawn*e/posix_spawn name it was specified with; missing: "
        f"{sorted(missing)}."
    )


def test_env_mutating_names_cover_the_required_floor():
    missing = (_REQUIRED_ENV_MUTATING_METHODS - _ENV_MUTATING_METHODS) | (
        _REQUIRED_ENV_MUTATING_FUNCTIONS - _ENV_MUTATING_FUNCTIONS
    )
    assert not missing, (
        "the process-environment mutation guard no longer recognizes every "
        f"mutating name it was specified with; missing: {sorted(missing)}."
    )


def test_the_real_cfe_py_run_streamed_allowlist_entry_is_still_live():
    """The `run_streamed` allowlist entry must never go stale (third review
    pass, Blind Hunter, reproduced): deleting the `env=` line from the real
    `cfe.py` entirely -- so `run_streamed`'s `env` parameter is accepted and
    silently ignored, and `_SANCTIONED_PASS_THROUGH_ENV_EXPR` matches
    nothing in the tree -- left every guard test in this file green. A
    carve-out nobody exercises is a carve-out that quietly comes to cover
    whatever that file grows next. Mirrors `test_adapter_sole_caller.py::
    test_cfe_path_allowlist_is_exactly_ad3s_two_live_carve_outs`. Story 2.9
    splits this from a single combined test into one test per allowlisted
    site (matching this file's own per-name-fixture convention) now that
    Guard 3a has two sites -- see the `_invoke_captured` counterpart below."""
    cfe_path = PKG_ROOT / "cfe.py"
    assert cfe_path.is_file(), f"cfe.py moved? {cfe_path}"

    allowlisted = _allowlisted_call_ids_in_named_function(
        _parse_file(cfe_path),
        "run_streamed",
        "Popen",
    )

    assert len(allowlisted) == 1, (
        "AD-14's run_streamed allowlist entry is dead: cfe.py's run_streamed "
        "no longer contains exactly one Popen call whose env= unparses to "
        f"{_SANCTIONED_PASS_THROUGH_ENV_EXPR!r}. Either the sanctioned "
        "pass-through was rewritten (a real AD-14 change -- justify it) or "
        "the allowlist is now covering nothing and must be deleted."
    )


def test_the_real_cfe_py_invoke_captured_allowlist_entry_is_still_live():
    """Story 2.9's second Guard-3a allowlist entry, mirroring the
    `run_streamed` test above: `cfe.py`'s own `_invoke_captured` must still
    contain exactly one `subprocess.run(...)` call whose `env=` unparses to
    exactly `_SANCTIONED_PASS_THROUGH_ENV_EXPR` -- proving `recipe.py::
    submit()`'s `CFE_RECIPES_ROOT` injection (module docstring) reaches a
    real, live, structurally-verified pass-through, not a carve-out nobody
    exercises."""
    cfe_path = PKG_ROOT / "cfe.py"
    assert cfe_path.is_file(), f"cfe.py moved? {cfe_path}"

    allowlisted = _allowlisted_call_ids_in_named_function(
        _parse_file(cfe_path),
        "_invoke_captured",
        "run",
    )

    assert len(allowlisted) == 1, (
        "AD-14's _invoke_captured allowlist entry is dead: cfe.py's "
        "_invoke_captured no longer contains exactly one subprocess.run "
        f"call whose env= unparses to exactly "
        f"{_SANCTIONED_PASS_THROUGH_ENV_EXPR!r}. Either the sanctioned "
        "pass-through was rewritten (a real AD-14 change -- justify it) or "
        "the allowlist is now covering nothing and must be deleted."
    )


def test_the_real_cfe_py_build_native_allowlist_entry_is_still_live():
    """Third Guard-3a allowlist entry (local-recipes PR #1354, 2026-09-14),
    mirroring the `run_streamed`/`_invoke_captured` tests above: `cfe.py`'s
    own `build_native` must still contain exactly one `run_streamed(...)`
    call whose `env=` unparses to exactly `_SANCTIONED_PASS_THROUGH_ENV_EXPR`
    -- proving Story 44.7's factory-island `MASON_FACTORY_ROOT` injection
    (read by `native-build.sh`) reaches a real, live, structurally-verified
    pass-through, not a carve-out nobody exercises."""
    cfe_path = PKG_ROOT / "cfe.py"
    assert cfe_path.is_file(), f"cfe.py moved? {cfe_path}"

    allowlisted = _allowlisted_call_ids_in_named_function(
        _parse_file(cfe_path),
        "build_native",
        "run_streamed",
    )

    assert len(allowlisted) == 1, (
        "AD-14's build_native allowlist entry is dead: cfe.py's build_native "
        "no longer contains exactly one run_streamed call whose env= "
        f"unparses to exactly {_SANCTIONED_PASS_THROUGH_ENV_EXPR!r}. Either "
        "the sanctioned pass-through was rewritten (a real AD-14 change -- "
        "justify it) or the allowlist is now covering nothing and must be "
        "deleted."
    )


def test_the_real_cfe_py_build_docker_allowlist_entry_is_still_live():
    """Fourth Guard-3a allowlist entry (local-recipes PR #1354, 2026-09-14),
    mirroring the `build_native` test above: `cfe.py`'s own `build_docker`
    must still contain exactly one `run_streamed(...)` call whose `env=`
    unparses to exactly `_SANCTIONED_PASS_THROUGH_ENV_EXPR`."""
    cfe_path = PKG_ROOT / "cfe.py"
    assert cfe_path.is_file(), f"cfe.py moved? {cfe_path}"

    allowlisted = _allowlisted_call_ids_in_named_function(
        _parse_file(cfe_path),
        "build_docker",
        "run_streamed",
    )

    assert len(allowlisted) == 1, (
        "AD-14's build_docker allowlist entry is dead: cfe.py's build_docker "
        "no longer contains exactly one run_streamed call whose env= "
        f"unparses to exactly {_SANCTIONED_PASS_THROUGH_ENV_EXPR!r}. Either "
        "the sanctioned pass-through was rewritten (a real AD-14 change -- "
        "justify it) or the allowlist is now covering nothing and must be "
        "deleted."
    )


# --- Guard 1 regression fixtures --------------------------------------------


def test_detector_fires_on_a_planted_jfrog_env_var_reference(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'import os\nKEY = os.environ.get("JFROG_API_KEY")\n',
        encoding="utf-8",
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
        'VALUE = os.environ.get("MASON_CFE_ROOT")\n',
        encoding="utf-8",
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
        'KEY = os.environ.get("STAGING_JFROG_API_KEY")\n',
        encoding="utf-8",
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
        "print('unrelated')\n'JFROG_API_KEY'\n",
        encoding="utf-8",
    )

    assert _find_jfrog_env_var_references(root) != []


def test_detector_fires_on_a_concatenated_jfrog_variable_name(tmp_path):
    """Follow-up review (both reviewers): `"JFROG" + "_API_KEY"` names the
    variable just as literally as one token does, but `ast.walk` sees each
    half separately and neither half matches alone -- it scanned clean."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'import os\nKEY = os.environ.get("JFROG" + "_API_KEY")\n',
        encoding="utf-8",
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


def test_detector_fires_on_a_bare_jfrog_prefix_filter(tmp_path):
    """Third review pass (Edge Case Hunter): reading a whole credential
    FAMILY by its bare `JFROG` prefix reads every `JFROG_*` variable while
    naming none of them, and the required trailing `_` let it scan clean."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'import os\nCREDS = {k: v for k, v in os.environ.items() if k.startswith("JFROG")}\n',
        encoding="utf-8",
    )

    violations = _find_jfrog_env_var_references(root)

    assert any(v.category == CATEGORY_ENV_VAR_NAME for v in violations)


def test_a_bare_jfrog_inside_an_alphanumeric_word_is_not_flagged(tmp_path):
    """The optional-suffix form keeps its alnum lookahead: `JFROGGY` is not
    a credential variable, and dropping the trailing guard would have made
    the bare form match inside any word starting with those five letters."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text('LABEL = "JFROGGY"\n', encoding="utf-8")

    assert _find_jfrog_env_var_references(root) == []


def test_detector_fires_on_a_foldable_chain_nested_in_an_unfoldable_one(tmp_path):
    """Third review pass (both reviewers): `"JFROG" + "_API_KEY" + suffix`
    parses as `(("JFROG" + "_API_KEY") + suffix)`. The outer chain is
    unfoldable (`suffix` is a `Name`), and the first cut had already marked
    the perfectly-foldable inner chain as "nested" before knowing that -- so
    nothing folded and neither leaf matched alone. One extra operand defeated
    the entire concatenation fix."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'import os\nsuffix = \'\'\nKEY = os.environ.get("JFROG" + "_API_KEY" + suffix)\n',
        encoding="utf-8",
    )

    violations = _find_jfrog_env_var_references(root)

    assert any(v.category == CATEGORY_ENV_VAR_NAME for v in violations)


def test_a_leaf_matching_alone_is_still_flagged_when_its_fold_does_not_match(tmp_path):
    """Third review pass (Blind Hunter): `"staging" + "JFROG_API_KEY"` folds
    to `stagingJFROG_API_KEY`, which the alnum lookbehind correctly rejects
    -- and the first cut then suppressed the leaf `"JFROG_API_KEY"` as
    "consumed", so adding the fold made this shape LESS detectable than
    before. Folding must only ever add detections."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'import os\nKEY = os.environ.get("staging" + "JFROG_API_KEY")\n',
        encoding="utf-8",
    )

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


@pytest.mark.parametrize("name", sorted(_REQUIRED_HTTP_IMPORTS))
def test_detector_fires_on_a_plain_import_of_each_banned_http_client(tmp_path, name):
    """Parametrized over the independently-spelled FLOOR, not over
    `_BANNED_HTTP_IMPORTS` (fourth review pass, Blind Hunter): deriving the
    cases from the live set is the self-deleting-fixture shape the floor was
    introduced to prevent, left in place in the one guard whose own
    docstring narrates that bug at greatest length. The two later per-name
    fixtures in this file already parametrize over their `_REQUIRED_*`
    floors; these two did not."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(f"import {name}\n", encoding="utf-8")

    violations = _find_http_client_imports(root)

    assert any(v.category == CATEGORY_HTTP_IMPORT and v.detail == name for v in violations)


@pytest.mark.parametrize("name", sorted(_REQUIRED_HTTP_IMPORTS))
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
        "from urllib import request\nfrom http import client\n",
        encoding="utf-8",
    )

    violations = {v.detail for v in _find_http_client_imports(root)}

    assert violations == {"urllib.request", "http.client"}


def test_clean_module_produces_zero_http_import_matches(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        "import subprocess\nfrom pathlib import Path\n",
        encoding="utf-8",
    )

    assert _find_http_client_imports(root) == []


@pytest.mark.parametrize(
    "statement",
    [
        "import requests.sessions",
        "import httpx._client",
        "from requests.sessions import Session",
        "from urllib.request import urlopen",
    ],
)
def test_detector_fires_on_a_submodule_of_a_banned_http_client(tmp_path, statement):
    """Third review pass (both reviewers, reproduced): `import
    requests.sessions` binds the name `requests` with `requests.get` fully
    callable, and `from requests.sessions import Session` hands back a
    complete session object -- both scanned clean under exact set
    membership. One dotted suffix was the cheapest possible defeat of this
    guard, and no declared residual covered it."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(f"{statement}\n", encoding="utf-8")

    violations = _find_http_client_imports(root)

    assert any(v.category == CATEGORY_HTTP_IMPORT for v in violations)


def test_a_submodule_import_is_reported_once_not_twice(tmp_path):
    """`from requests.sessions import Session` matches both the module name
    and the module-plus-alias dotted form; only one violation is right."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "from requests.sessions import Session\n",
        encoding="utf-8",
    )

    assert len(_find_http_client_imports(root)) == 1


def test_a_module_merely_prefixed_by_a_banned_name_is_not_flagged(tmp_path):
    """Submodule matching is on a dotted boundary, not a bare string
    prefix: `requestsx` and `httpxray` are unrelated third-party names."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        "import requestsx\nfrom httpxray import Tracer\n",
        encoding="utf-8",
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
        "from .requests import helper\nfrom .http import client\n",
        encoding="utf-8",
    )

    assert _find_http_client_imports(root) == []


def test_the_absolute_form_of_that_same_import_is_still_flagged(tmp_path):
    """Proves the `level == 0` narrowing is targeted at relative imports
    only, not a blanket suppression of the name."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "leaky.py").write_text("from requests import Session\n", encoding="utf-8")

    assert _find_http_client_imports(root) != []


@pytest.mark.parametrize("name", sorted(_REQUIRED_HTTP_IMPORTS))
def test_detector_fires_on_a_banned_client_named_only_as_a_string(tmp_path, name):
    """Fourth review pass (Blind Hunter, reproduced): a REBOUND handle on
    `importlib.import_module` reaches any module without an `import`
    statement --

        import importlib
        _dyn = importlib.import_module
        client = _dyn("requests")

    -- and the whole suite stayed green while `resolve.py` held a live HTTP
    client posting a bearer token. The two prior passes rejected the dynamic
    -import family on the premise that `test_dependency_direction.py`'s AD-4
    guard bans it unconditionally; that guard's own docstring
    (`test_dependency_direction.py`, `_find_importlib_or_exec_callers`)
    declares the exception in as many words: "It does not trace indirect
    rebinding (`dynamic_import = importlib.import_module;
    dynamic_import(...)`)". The direct spellings the prior passes actually
    verified ARE caught there; this one never was, and Guard 2 declared no
    residual covering it.

    Scanning string CONSTANTS closes the whole family at once -- every
    dynamic route (`import_module`, `__import__`,
    `globals()["__import__"]`, any rebinding of any of them) must still name
    its target as a string -- without this guard tracing a single
    callable."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        f'import importlib\n_dyn = importlib.import_module\nclient = _dyn("{name}")\n',
        encoding="utf-8",
    )

    violations = _find_http_client_imports(root)

    assert any(v.category == CATEGORY_HTTP_MODULE_NAME and v.detail == name for v in violations)


def test_a_submodule_named_only_as_a_string_is_flagged(tmp_path):
    """The string scan uses the same dotted-boundary match as the import
    scan, so `__import__("requests.sessions")` is no cheaper an escape than
    `import requests.sessions` was."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text('client = __import__("requests.sessions")\n', encoding="utf-8")

    violations = _find_http_client_imports(root)

    assert any(v.category == CATEGORY_HTTP_MODULE_NAME for v in violations)


def test_a_banned_client_named_in_a_data_table_is_not_flagged(tmp_path):
    """The real `cfe.py` shape, and the reason the string scan is scoped to
    call ARGUMENTS: `CFE_IMPORT_FLOOR` names `"requests"` because CFE (the
    child, in its own interpreter) depends on it. Mason declares that floor
    to probe it; Mason never imports it. The first cut of this patch scanned
    every constant and red the real tree on exactly this line -- a guard
    whose first red is a false positive is one a maintainer weakens."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "cfe.py").write_text(
        'CFE_IMPORT_FLOOR = {"requests": "requests", "httpx": "httpx"}\n',
        encoding="utf-8",
    )

    assert _find_http_client_imports(root) == []


def test_a_docstring_naming_a_banned_client_is_not_flagged(tmp_path):
    """Prose explaining the ban must not trip it -- the same exemption Guard
    1 grants, for the same reason: a false positive whose cheapest repair is
    to weaken the guard is the failure mode this file designs against."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "narrator.py").write_text(
        '"""Mason imports no requests/httpx client (AD-14)."""\n',
        encoding="utf-8",
    )

    assert _find_http_client_imports(root) == []


def test_a_string_merely_containing_a_banned_name_is_not_flagged(tmp_path):
    """The string scan matches a MODULE NAME exactly (or a dotted submodule
    of one), not any text mentioning it -- an error message or a URL is not
    a dynamic import."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        'log("no outbound requests are permitted")\nload("requestsx")\n',
        encoding="utf-8",
    )

    assert _find_http_client_imports(root) == []


# --- Guard 2 allowlist regression fixtures (Story 3.7) ----------------------


def test_urllib_request_import_in_pypi_index_py_is_not_flagged(tmp_path):
    """The one exemption this story adds: a file literally named
    `pypi_index.py` may `import urllib.request`."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "pypi_index.py").write_text("import urllib.request\n", encoding="utf-8")

    assert _find_http_client_imports(root) == []


def test_from_urllib_import_request_in_pypi_index_py_is_not_flagged(tmp_path):
    """The `from urllib import request` spelling reaches the identical
    submodule (module docstring's "parent, then submodule" note) and must
    be exempted too."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "pypi_index.py").write_text("from urllib import request\n", encoding="utf-8")

    assert _find_http_client_imports(root) == []


def test_urllib_request_import_in_any_other_file_is_still_flagged(tmp_path):
    """The allowlist is scoped to `pypi_index.py` specifically, not a
    blanket un-banning of `urllib.request` -- the identical import in any
    other file must still be caught."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "other.py").write_text("import urllib.request\n", encoding="utf-8")

    violations = _find_http_client_imports(root)

    assert any(v.detail == "urllib.request" for v in violations)


@pytest.mark.parametrize("name", ["requests", "httpx", "http.client"])
def test_requests_httpx_and_http_client_stay_banned_inside_pypi_index_py(tmp_path, name):
    """`pypi_index.py`'s own exempted set is `{"urllib.request"}` only
    (`_GUARD_2_HTTP_IMPORT_ALLOWLIST`'s own docstring) -- the OTHER three
    banned clients must still be caught inside this one exempted file,
    proving the allowlist is per-(file, module-name), not per-file."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "pypi_index.py").write_text(f"import {name}\n", encoding="utf-8")

    violations = _find_http_client_imports(root)

    assert any(v.category == CATEGORY_HTTP_IMPORT and v.detail == name for v in violations)


def test_urllib_request_submodule_in_pypi_index_py_is_also_exempted(tmp_path):
    """`_is_http_import_allowlisted`'s own dotted-boundary rule: a submodule
    of an allowlisted name is exactly as exempt as the bare name itself,
    mirroring `_is_banned_http_module`'s identical rule for the ban."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "pypi_index.py").write_text(
        "from urllib.request import urlopen\n",
        encoding="utf-8",
    )

    assert _find_http_client_imports(root) == []


def test_urllib_request_named_as_a_string_argument_in_pypi_index_py_is_exempted(tmp_path):
    """The allowlist also covers the call-argument scan
    (`_banned_module_name_arguments`), not only the static `import` scan --
    a dynamic `importlib.import_module("urllib.request")` inside
    `pypi_index.py` must not be flagged either, for the same structural
    reason the static form is exempted."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "pypi_index.py").write_text(
        'import importlib\n_dyn = importlib.import_module\nclient = _dyn("urllib.request")\n',
        encoding="utf-8",
    )

    assert _find_http_client_imports(root) == []


# --- Guard 3 regression fixtures --------------------------------------------


def test_detector_fires_on_a_planted_subprocess_run_env_override(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'import subprocess\nsubprocess.run(["x"], env={"FOO": "bar"})\n',
        encoding="utf-8",
    )

    violations = _find_env_override_violations(root)

    assert any(v.category == CATEGORY_ENV_OVERRIDE for v in violations)


def test_detector_fires_on_a_planted_run_streamed_caller_env_override(tmp_path):
    """The exact synthetic-caller shape the spec's I/O matrix names."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'from .cfe import run_streamed\nrun_streamed(["x"], timeout=5, env={"FOO": "bar"})\n',
        encoding="utf-8",
    )

    violations = _find_env_override_violations(root)

    assert any(v.category == CATEGORY_ENV_OVERRIDE for v in violations)


def test_detector_permits_an_explicit_bare_none_env_literal(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        "import subprocess\nsubprocess.run(['x'], env=None)\n",
        encoding="utf-8",
    )

    assert _find_env_override_violations(root) == []


def test_detector_permits_a_call_with_no_env_kwarg_at_all(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        "import subprocess\nsubprocess.run(['x'], timeout=5)\n",
        encoding="utf-8",
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
def test_allowlist_rejects_a_rewritten_env_expression_in_the_sanctioned_call(tmp_path, env_expr):
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


def test_allowlist_is_revoked_when_invoke_captured_gains_a_second_run_call(tmp_path):
    """Story 2.9's `_invoke_captured`-equivalent of
    `test_allowlist_is_revoked_when_run_streamed_gains_a_second_popen_call`
    above: more than one `subprocess.run` call in `_invoke_captured`'s own
    body revokes THAT site's allowlist entry entirely -- both calls must be
    flagged, not just the newly-planted one. `run_streamed`'s own entry
    (absent from this synthetic file) is unaffected by this file even
    defining `_invoke_captured` at all -- the two sites are checked
    independently."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "cfe.py").write_text(
        "import subprocess\n"
        "\n"
        "\n"
        "def _invoke_captured(script_key, args, *, root, interpreter, timeout, env=None):\n"
        "    leaked = subprocess.run(args, env={'JFROG_API_KEY': 'x'})\n"
        "    completed = subprocess.run(\n"
        "        args, env=dict(env) if env is not None else None,\n"
        "    )\n"
        "    return completed\n",
        encoding="utf-8",
    )

    violations = _find_env_override_violations(root)

    assert len(violations) == 2


@pytest.mark.parametrize(
    "env_expr",
    ["{}", '{"HTTPS_PROXY": "http://evil"}', "{k: v for k, v in os.environ.items()}"],
    ids=["empty-dict", "hostile-dict", "stripping-comprehension"],
)
def test_allowlist_rejects_a_rewritten_env_expression_in_the_sanctioned_invoke_captured_call(
    tmp_path,
    env_expr,
):
    """Story 2.9's `_invoke_captured`-equivalent of
    `test_allowlist_rejects_a_rewritten_env_expression_in_the_sanctioned_call`
    above: rewriting `_invoke_captured`'s own sanctioned `env=` -- to `{}`,
    to a hostile dict, or to a targeted `JFROG_*`-stripping comprehension --
    must still be caught at this second site, exactly as at the first."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "cfe.py").write_text(
        "import os\nimport subprocess\n"
        "\n"
        "\n"
        "def _invoke_captured(script_key, args, *, root, interpreter, timeout, env=None):\n"
        f"    return subprocess.run(args, env={env_expr})\n",
        encoding="utf-8",
    )

    violations = _find_env_override_violations(root)

    assert any(v.category == CATEGORY_ENV_OVERRIDE for v in violations)


@pytest.mark.parametrize("name", sorted(_REQUIRED_EXPLICIT_ENV_SPAWN_FUNCTIONS))
def test_detector_fires_on_each_explicit_environment_spawn_function(tmp_path, name):
    """Third review pass (both reviewers, reproduced): these take the
    environment POSITIONALLY (positional-ONLY for `os.posix_spawn`), so the
    `env=` keyword scan could not reach them, and
    `os.posix_spawn(path, argv, {"JFROG_API_KEY": tok})` was a complete
    one-line AD-14 break that every guard reported clean. The earlier
    docstring excused this on two grounds now verified FALSE:
    `inspect.signature(os.execve)` is `(path, argv, env)` -- keyword-capable
    -- and `test_adapter_sole_caller.py`'s AD-3 guard only fires when a
    spawn's arguments name a CFE path or script."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        f'import os\nos.{name}("/bin/sh", ["sh"], {{"JFROG_API_KEY": "x"}})\n',
        encoding="utf-8",
    )

    violations = _find_env_override_violations(root)

    assert any(v.category == CATEGORY_EXPLICIT_ENV_SPAWN for v in violations)


def test_an_inheriting_spawn_variant_is_not_flagged(tmp_path):
    """The ban covers only the variants that take an EXPLICIT environment
    (`*e`-suffixed, plus `posix_spawn`). `os.execv`/`os.spawnv` cannot carry
    one at all -- they inherit, which is what AD-14 requires, so they are
    outside this guard's rule (fourth review pass, Edge Case Hunter: this
    docstring used to delegate them to AD-3's guard, which in fact only
    fires on spawns naming a CFE path -- the same false-backstop claim
    corrected for `os.execve` one pass earlier)."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        'import os\nos.execv("/bin/sh", ["sh"])\n',
        encoding="utf-8",
    )

    assert _find_env_override_violations(root) == []


def test_allowlist_permits_an_async_run_streamed(tmp_path):
    """Third review pass (Edge Case Hunter, reproduced): matching only
    `ast.FunctionDef` meant an `async def run_streamed` voided the allowlist
    and red the guard on the sanctioned call itself -- a false positive
    whose cheapest repair is to weaken the guard."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "cfe.py").write_text(
        "import subprocess\n"
        "\n"
        "\n"
        "async def run_streamed(argv, *, timeout, env=None):\n"
        "    return subprocess.Popen(\n"
        "        argv, env=dict(env) if env is not None else None,\n"
        "    )\n",
        encoding="utf-8",
    )

    assert _find_env_override_violations(root) == []


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


@pytest.mark.parametrize(
    "mutation",
    [
        "os.environ |= {'JFROG_API_KEY': 't'}",
        "os.environb[b'JFROG_API_KEY'] = b't'",
        "os.environb.update({b'A': b'b'})",
        "os.environ['JFROG_API_KEY'], ok = 't', True",
        "[os.environ['A']] = ['b']",
    ],
    ids=["ior", "environb-subscript", "environb-update", "tuple-target", "list-target"],
)
def test_detector_fires_on_each_indirect_process_environment_mutation(tmp_path, mutation):
    """Third review pass (both reviewers, reproduced against real child
    processes). Three distinct holes in one family:

    * `os.environ |= {...}` is the operator that IS `update`
      (`MutableMapping.__ior__` -> `os._Environ.__setitem__` -> `putenv`),
      but its target is the bare attribute rather than a subscript, so it
      fell through every branch.
    * `os.environb` is the BYTES view of the identical POSIX environment; an
      exact `== "environ"` name match scanned it clean.
    * Unpacking targets were only inspected one level deep, so
      `os.environ['JFROG_API_KEY'], ok = token, True` scanned clean --
      `test_no_recipe_knowledge.py::_bound_names_in_target` already recurses
      for exactly this reason."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        f"import os\nimport subprocess\n{mutation}\nsubprocess.run(['x'])\n",
        encoding="utf-8",
    )

    violations = _find_env_mutation_violations(root)

    assert any(v.category == CATEGORY_ENV_MUTATION for v in violations)


@pytest.mark.parametrize(
    "statement",
    [
        "for os.environ['A'] in ['b']:\n    pass",
        "with open('f') as os.environ['A']:\n    pass",
    ],
    ids=["for-target", "with-target"],
)
def test_detector_fires_on_a_binding_target_that_is_not_an_assignment(tmp_path, statement):
    """`for` and `with ... as` targets bind exactly like an assignment does
    -- exotic spellings, but they mutate the real environment (third review
    pass, Edge Case Hunter, reproduced)."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(f"import os\n{statement}\n", encoding="utf-8")

    violations = _find_env_mutation_violations(root)

    assert any(v.category == CATEGORY_ENV_MUTATION for v in violations)


@pytest.mark.parametrize("name", sorted(_REQUIRED_ENV_MUTATING_METHODS))
def test_every_required_env_mutating_method_is_actually_detected(tmp_path, name):
    """Fourth review pass (Blind Hunter): 3b's floor listed seven names
    while its hardcoded fixture exercised four of them -- `popitem`,
    `__setitem__` and `__delitem__` had no detection fixture at all, and
    "membership in the frozenset is not detection" is this file's own
    standard, enforced with a per-name fixture for every other set. The
    parametrization is over the independently-spelled floor, never over
    `_ENV_MUTATING_METHODS` itself, which would delete its own coverage
    (`_REQUIRED_ENV_MUTATING_METHODS`' own docstring). Arity does not matter
    to the scanner -- it matches the attribute name on an `os.environ`
    receiver -- so one bare-call spelling covers every name."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(f"import os\nos.environ.{name}()\n", encoding="utf-8")

    violations = _find_env_mutation_violations(root)

    assert any(v.category == CATEGORY_ENV_MUTATION for v in violations)


@pytest.mark.parametrize("name", sorted(_REQUIRED_ENV_MUTATING_FUNCTIONS))
def test_every_required_env_mutating_function_is_actually_detected(tmp_path, name):
    """Same rationale as the method floor above."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(f"import os\nos.{name}('A', 'b')\n", encoding="utf-8")

    violations = _find_env_mutation_violations(root)

    assert any(v.category == CATEGORY_ENV_MUTATION for v in violations)


@pytest.mark.parametrize(
    "statement",
    [
        "[None for os.environ['ARTIFACTORY_TOKEN'] in ['scrubbed']]",
        "list(None for os.environ['ARTIFACTORY_TOKEN'] in ['scrubbed'])",
        "{k: None for os.environ['ARTIFACTORY_TOKEN'] in ['scrubbed']}",
    ],
    ids=["listcomp", "genexp", "dictcomp"],
)
def test_detector_fires_on_a_comprehension_binding_target(tmp_path, statement):
    """Fourth review pass (both reviewers, reproduced against a real child
    process): a comprehension's `for` target binds identically to the
    statement `for` the third pass already guarded, and mutates the real
    environment -- but it lives on `ast.comprehension`, its own node type,
    so it fell straight through. One line, no imports beyond `os`, and the
    whole suite stayed green."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(f"import os\nk = 'x'\n{statement}\n", encoding="utf-8")

    violations = _find_env_mutation_violations(root)

    assert any(v.category == CATEGORY_ENV_MUTATION for v in violations)


@pytest.mark.parametrize(
    "source",
    [
        "import os\n_env = os.environ\ndel _env['ARTIFACTORY_TOKEN']\n",
        "from os import environ as e\ne['JFROG_API_KEY'] = 't'\n",
        "import os\n_env = os.environ\n_alias = _env\n_alias.update({'A': 'b'})\n",
        "import os\n_envb = os.environb\n_envb[b'A'] = b'b'\n",
    ],
    ids=["local-alias", "import-as-alias", "alias-chain", "environb-alias"],
)
def test_detector_fires_through_an_alias_of_the_environment_mapping(tmp_path, source):
    """Fourth review pass (both reviewers, reproduced against the real
    `cfe.py`): ONE binding line defeated the whole of Guard 3b. `_env =
    os.environ` followed by a targeted `del` of the enterprise credential
    family is Mason scrubbing what the CFE child inherits -- the exact
    inverse of AD-14, at the exact seam this story protects -- and every
    guard plus both sentinel tests reported clean. `from os import environ`
    unaliased was already caught, which is what made the gap specifically
    about rebinding."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(source, encoding="utf-8")

    violations = _find_env_mutation_violations(root)

    assert any(v.category == CATEGORY_ENV_MUTATION for v in violations)


def test_detector_fires_on_the_explicit_ior_dunder(tmp_path):
    """Fourth review pass (both reviewers): the third pass closed
    `os.environ |= {...}` as a HIGH, but `os.environ.__ior__({...})` -- the
    identical call, spelled out -- still scanned clean, even though
    `__setitem__`/`__delitem__` were already in the method set for exactly
    that reason."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "import os\nos.environ.__ior__({'JFROG_API_KEY': 't'})\n",
        encoding="utf-8",
    )

    violations = _find_env_mutation_violations(root)

    assert any(v.category == CATEGORY_ENV_MUTATION for v in violations)


def test_an_unrelated_name_is_not_treated_as_the_environment(tmp_path):
    """Alias tracking follows assignment from `os.environ` only -- a local
    mapping that merely shares the shape must not be swept in, or the guard
    reds on ordinary code and the cheapest repair is to delete it."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        "import os\n_env = dict(os.environ)\n_env['A'] = 'b'\n_other = {'x': 1}\n_other.update({'y': 2})\n",
        encoding="utf-8",
    )

    assert _find_env_mutation_violations(root) == []


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
