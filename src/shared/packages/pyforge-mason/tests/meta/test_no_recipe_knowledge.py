"""AD-1 -- knowledge-free core: no module under `pyforge/mason/` may carry a
conda-forge gotcha identifier, policy/check-code identifier, distinctive v1
recipe-schema field name, or pin/constraint shape (FR-42).

The deny list below is the "one reviewable module-level table" FR-42
requires: each `DenyListEntry` is a structured record (category, compiled
pattern, CFE-artifact citation, rationale) rather than a bare string, so
weakening or removing an entry leaves a rationale behind in the diff.
`test_deny_list_entries_all_carry_a_citation_and_rationale` makes that a
standing invariant on present state, not just a git-diff convention.

AST-based, not regex-over-raw-text (matches every sibling meta-test's
documented rationale, e.g. `test_dependency_direction.py`'s docstring): a
raw-text scan would flag a comment that merely *mentions* a banned term,
which is the exact false-positive class that already bit an early draft of
`test_namespace_is_implicit.py`. Two kinds of AST node are examined:

* **String/bytes constant VALUES** (`ast.Constant`, `str` or `bytes` --
  `bytes` decoded `errors="replace"` before matching, review pass) -- never
  a comment (comments are not part of the AST at all); never a
  module/class/function's own **docstring** (the first statement of its
  body), nor a bare string statement immediately following a module- or
  class-level assignment (a "trailing attribute docstring" -- the PEP
  257-adjacent convention this very file uses for `_V1_FIELD_NAMES` below;
  review pass closed the gap where that exact style would otherwise
  false-positive on its own prose): Mason's own modules already narrate
  CFE/architecture concepts in prose by spec identifier (`cfe.py` cites
  AD-3/FR-4 throughout) without that constituting recipe knowledge.
* **Identifier POSITIONS** -- every place a denied name can be *bound*,
  *passed*, or *read*: function/lambda parameter names, `def`/`class` names,
  plain and annotated assignment targets, `for`/`with`/walrus/comprehension
  targets, `except ... as` names, `global`/`nonlocal` declarations, `match`
  captures, `import`/`from ... import` names and aliases, call-site keyword
  arguments, PEP 695 type aliases and type parameters (`type run_exports =
  ...`, `def build[pin_subpackage](...)` -- live syntax at this package's
  Python >=3.12 floor, review pass), **every bare name in any context, load
  included** (review pass: only binding positions were collected, so
  `from .helpers import *` followed by `return run_exports` was invisible and
  the "or read" claim above was false), and **every attribute name, read or
  written** (`self.run_exports = ...` and `return spec.run_exports` alike)
  (review pass: the original
  version only scanned string *values*, so `def build(*, run_exports=None):
  ...` sailed through; a second pass found the target set still covered only
  parameters and bare `Name` assignment targets, missing `self.<field> =
  ...` -- the single most plausible way recipe knowledge actually lands in a
  model class -- plus `def run_exports()`, `class run_exports`, and
  `build(run_exports=...)`; a third found the write side covered but the
  read side, imports, comprehension/except/match bindings, and
  `global`/`nonlocal` still invisible, which made the "every place" claim
  above false).
  Restricted to the gotcha-identifier and v1-field-name categories only --
  check-code and pin-shape patterns contain characters (`-`, comparison
  operators) that cannot appear in a Python identifier at all, so applying
  them there would be vacuous.

AD-1's actual target is recipe semantics encoded as something a use-case
could act on -- a constant, a table, a default, a parameter name -- not
prose documenting a delegation boundary.

Deny-list content, category by category:

* **Gotcha identifiers** (`G` + 1-3 digits, citing `SKILL.md`'s
  `## Recipe Authoring Gotchas` section, `### G<N>.` entries G1-G107). The
  boundary is spelled as explicit alphanumeric lookaround rather than `\\b`
  (review pass): `_` is a word character, so `\\b` never fires beside one and
  `G41_WORKAROUND = ...` / `def apply_G41_patch()` -- precisely the
  identifier-shaped gotcha knowledge the identifier scan below exists to
  catch -- slipped past the very pattern meant to catch them.
* **Check-code prefixes**, digit-suffixed
  (`ABT-/DEP-/FMT-/LIC-/MAINT-/PIN-/SCHEMA-/SCRIPT-/SEC-/SEL-/STD-/TEST-`
  followed by three digits, citing `SKILL.md`'s Core Tools Reference table
  + `reference/*.md`) -- the digit suffix is load-bearing: a bare `"CFE-"`
  substring already false-positives against Mason's own prose (`doctor.py`:
  "CFE-independent", `package.py`: "CFE-independent", `exit_codes.py`:
  "CFE-dependent"), so every entry here requires the trailing `\\d{3}`.
  Known, accepted residual: this shape is indistinguishable from an
  unrelated issue-tracker ID convention (`TEST-042`, `SEC-001`); zero
  current occurrences, recorded in the deferred-work ledger.
* **Distinctive v1 recipe-schema field names** (citing
  `reference/recipe-yaml-reference.md`), one entry per name, with the same
  asymmetric boundary the gotcha entry needed: a LEADING `_` is part of the
  name, not a boundary (review pass: `\\b` never fires beside `_`, so
  `self._run_exports = []` and `def build(*, _run_exports=None)` -- the
  private spelling of exactly the shape the identifier scan exists for --
  walked straight through), while a TRAILING `_` still is one, so a merely
  `run_exports`-containing name like `run_exports_list` stays unflagged.
  Drawn only from
  conda-forge vocabulary with zero ordinary-English collision risk. NEVER a
  generic top-level v1 key (`package`/`source`/`build`/`test(s)`/`about`/
  `extra`/`requirements`/`schema_version`/`context`/`outputs`/`cache`): a
  literal scan of the shipped tree shows these already occur 2-28 times each
  (`package.py`, the `build` verb, `tests/`) and `render.py` already
  legitimately emits the JSON-envelope key `"schema_version"` -- a deny-list
  including any of these would fail against Mason's own current code on day
  one, making the guard self-defeating.
* **Pin/constraint shapes**: a real comparison operator (`==`, `!=`, `<=`,
  `>=`, `~=`, `<`, `>` -- never a bare `=`) immediately before a digit,
  optional NON-NEWLINE whitespace between the two (review pass: conda-forge
  pins are conventionally written with no space, but tolerating one closes a
  real gap cheaply; a plain `\\s*` also spanned newlines, so a `<recipe>`
  usage line and a `3 exit codes` line two rows later matched as the pin
  `">\\n\\n3"`), and never an operator preceded by `-`, `=` or `:`:
  - `->` is this codebase's house notation for a resolution chain, used in
    every `cli.py` precedence help string -- "flag -> MASON_X -> default".
    Every such arrow in the tree today happens to be followed by a letter or
    `{`, so the guard was green by luck: documenting one numeric default
    inline -- "flag -> MASON_X -> 300" -- would have reported `"> 3"`.
    `=>` is the same arrow, one character different (review pass).
  - `:` immediately before the operator makes it a **format-spec
    alignment**, not a comparison: `"{:>6} {:<20}"` -- ordinary `.format()`
    table code -- reported two pins. The f-string spelling of the same thing
    (`f"{name:<30}"`) puts the spec in its own constant with no `:` to look
    behind, and is exempted structurally instead by
    `_format_spec_string_ids` (review pass; Mason has a `render.py` whose
    whole job is tabular output, so this was a live collision, not a
    hypothetical one).
  None of the three lookbehinds can mask a real pin, which never spells its
  operator that way. Citing `reference/pinning-reference.md`.
  Known, accepted residual (recorded in the deferred-work ledger): the
  pattern matches a lone operator-then-digit with no paired-bounds context,
  so ordinary numeric-constraint prose collides with it -- and Mason is a CLI
  with three numeric-flag validators and an interpreter-floor probe, so
  `"--timeout must be > 0"` or `"requires Python >=3.11"` is one rewording
  away from reding this guard. The tree is green today by wording, not by
  construction (`cli.py` says "must be a finite, positive number"). The
  failure message below therefore names the alternative explicitly, so the
  next maintainer rewords the message rather than weakening the pattern; a
  precise fix risks missing valid single-bound pins like `"==1.2.3"`.
  A bare `=` is excluded from the operator set because an ordinary
  `keyword=123` mention inside prose is not a pin and is not a conda-forge
  comparison operator at all: `[<>=!]=?\\d+` (an earlier illustrative pattern)
  matches `cfe.py`'s own `_SUBMIT_PR_TIMEOUT_SECONDS` narration of the MCP
  server's `timeout=300` default. That particular occurrence is in fact
  already exempt as a trailing attribute docstring (review pass corrected the
  earlier claim here that it was not -- the exemption below post-dated the
  sentence), but the exemptions do not reach every string position, so the
  operator restriction still carries its own weight. It costs nothing: the
  required planted fixture (`">=1.0,<2.0"`) still matches.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "mason"


@dataclass(frozen=True)
class DenyListEntry:
    """One deny-list row: a category, a name, a compiled pattern, and the
    CFE artifact + rationale it derives from. Both `citation` and
    `rationale` are asserted non-empty by
    `test_deny_list_entries_all_carry_a_citation_and_rationale` below."""

    category: str
    name: str
    pattern: re.Pattern[str]
    citation: str
    rationale: str


CATEGORY_GOTCHA = "gotcha-identifier"
CATEGORY_CHECK_CODE = "check-code-prefix"
CATEGORY_V1_FIELD = "v1-field-name"
CATEGORY_PIN_SHAPE = "pin-constraint-shape"

_REQUIRED_CATEGORIES = frozenset({CATEGORY_GOTCHA, CATEGORY_CHECK_CODE, CATEGORY_V1_FIELD, CATEGORY_PIN_SHAPE})

_IDENTIFIER_CAPABLE_CATEGORIES = frozenset({CATEGORY_GOTCHA, CATEGORY_V1_FIELD})
"""Categories whose pattern can also be expressed as a valid bare Python
identifier -- CHECK_CODE (`-`) and PIN_SHAPE (`<`/`>`/`=`/`!`) use
characters that cannot appear in a Python identifier at all, so applying
identifier-position scanning to them would be vacuous (module docstring)."""

_GOTCHA_ENTRY = DenyListEntry(
    category=CATEGORY_GOTCHA,
    name="gotcha-id",
    # Explicit alphanumeric lookaround, NOT `\b`: `_` is a word character,
    # so `\b` never fires beside one (module docstring).
    pattern=re.compile(r"(?<![0-9A-Za-z])G[0-9]{1,3}(?![0-9A-Za-z])"),
    citation="SKILL.md ## Recipe Authoring Gotchas (### G<N>. entries, G1-G107)",
    rationale=(
        "A gotcha identifier names one of CFE's own catalogued packaging pitfalls; "
        "Mason citing one by number would mean Mason itself tracks recipe-authoring "
        "judgement instead of treating CFE's findings as opaque data (AD-1)."
    ),
)

_CHECK_CODE_PREFIXES: tuple[str, ...] = (
    "ABT",
    "DEP",
    "FMT",
    "LIC",
    "MAINT",
    "PIN",
    "SCHEMA",
    "SCRIPT",
    "SEC",
    "SEL",
    "STD",
    "TEST",
)
"""CFE's own check-code prefixes, woven into the entry's pattern below."""

_REQUIRED_CHECK_CODE_PREFIXES = frozenset(
    {
        "ABT",
        "DEP",
        "FMT",
        "LIC",
        "MAINT",
        "PIN",
        "SCHEMA",
        "SCRIPT",
        "SEC",
        "SEL",
        "STD",
        "TEST",
    }
)
"""The check-code prefixes this guard is specified to cover, spelled out
INDEPENDENTLY of `_CHECK_CODE_PREFIXES` above (deriving it would delete itself
along with whatever prefix was dropped) and exercised one planted code per
prefix (review pass: only `STD-001` was ever planted, so eleven of the twelve
alternatives could be dropped from the pattern with the suite green)."""

_CHECK_CODE_ENTRY = DenyListEntry(
    category=CATEGORY_CHECK_CODE,
    name="check-code-prefix",
    # Case-insensitive (review pass): `"std-001"` names the same CFE check as
    # `"STD-001"` and scanned clean. Verified against the real tree first --
    # zero occurrences under either casing.
    pattern=re.compile(r"\b(?:" + "|".join(_CHECK_CODE_PREFIXES) + r")-\d{3}\b", re.IGNORECASE),
    citation="SKILL.md Core Tools Reference table (optimize_recipe check codes) + reference/*.md",
    rationale=(
        "A check-code identifier (e.g. STD-001) names one of CFE's own policy checks; "
        "Mason hardcoding one would duplicate CFE's check taxonomy instead of passing "
        "its findings through verbatim (Epic 2 context: preserve identifiers/check codes "
        "verbatim, apply no severity policy of Mason's own)."
    ),
)

_V1_FIELD_NAMES: tuple[str, ...] = (
    "run_exports",
    "ignore_run_exports",
    "run_constrained",
    "pin_subpackage",
    "pin_compatible",
    "zip_keys",
    "noarch_platforms",
    "conda_build_config",
    "recipe-maintainers",
    "skip_pyc_compilation",
)
"""Distinctive conda-forge v1 recipe-schema field names with zero ordinary-
English collision risk -- NEVER a generic top-level key (`package`/`source`/
`build`/`test(s)`/`about`/`extra`/`schema_version`/etc.; see module
docstring for why those are excluded)."""

_REQUIRED_V1_FIELD_NAMES = frozenset(
    {
        "run_exports",
        "ignore_run_exports",
        "run_constrained",
        "pin_subpackage",
        "pin_compatible",
        "zip_keys",
        "noarch_platforms",
        "conda_build_config",
        "recipe-maintainers",
        "skip_pyc_compilation",
    }
)
"""The v1 field names this story's spec enumerated, spelled out INDEPENDENTLY
of `_V1_FIELD_NAMES` above (deriving it from that tuple would delete itself
along with whatever entry was dropped) and pinned as a floor by
`test_deny_list_covers_the_required_v1_field_names` (review pass: a mutation
test proved nine of the ten entries above could be deleted with the whole
suite still green -- category *presence* was asserted, entry *coverage* was
not, so the table this file exists to defend was itself undefended). Widening
the deny list is free; narrowing it now has to delete a named floor entry
too, which is exactly the reviewable diff FR-42 asks for."""

_V1_FIELD_CITATION = "reference/recipe-yaml-reference.md"


def _v1_field_rationale(field_name: str) -> str:
    return (
        f"{field_name!r} is a distinctive conda-forge v1 recipe.yaml field with no "
        "ordinary-English collision risk; Mason holding it as a literal would mean "
        "Mason itself understands recipe.yaml field semantics instead of treating "
        "CFE's generated recipe as opaque data (AD-1)."
    )


def _v1_field_pattern(field_name: str) -> re.Pattern[str]:
    """Asymmetric boundary (module docstring): a LEADING `_` is part of the
    name (`_run_exports` is the same knowledge, privately spelled), a
    TRAILING one is a boundary (`run_exports_list` is a different name).

    Case-insensitive (review pass): `RUN_EXPORTS = (...)` -- the constant
    spelling, i.e. exactly the "recipe semantics encoded as data" shape AD-1
    targets -- scanned clean. Verified against the real tree first: zero
    occurrences under any casing. The gotcha entry deliberately stays
    case-SENSITIVE, since a case-folded `G[0-9]{1,3}` would collide with
    ordinary short lowercase identifiers (`g1`, `g2`)."""
    return re.compile(
        r"(?<![0-9A-Za-z])" + re.escape(field_name) + r"(?![0-9A-Za-z_])",
        re.IGNORECASE,
    )


_V1_FIELD_ENTRIES: tuple[DenyListEntry, ...] = tuple(
    DenyListEntry(
        category=CATEGORY_V1_FIELD,
        name=field_name,
        pattern=_v1_field_pattern(field_name),
        citation=_V1_FIELD_CITATION,
        rationale=_v1_field_rationale(field_name),
    )
    for field_name in _V1_FIELD_NAMES
)

_PIN_SHAPE_ENTRY = DenyListEntry(
    category=CATEGORY_PIN_SHAPE,
    name="pin-constraint-shape",
    # A real comparison operator (never a bare `=`; never one preceded by
    # `-`/`=`, which makes it an arrow rather than a comparison; never one
    # preceded by `:`, which makes it a format-spec alignment) immediately
    # before a digit, tolerating optional NON-NEWLINE whitespace between them
    # -- see module docstring for every decision.
    pattern=re.compile(r"(?<![-=:])(?:==|!=|<=|>=|~=|<|>)[^\S\n]*\d"),
    citation="reference/pinning-reference.md",
    rationale=(
        "A literal pin/constraint expression (e.g. '>=1.0,<2.0') is a packaging "
        "decision CFE's generator/optimizer makes; Mason embedding one would be a "
        "second, driftable copy of a pin CFE already owns (AD-1)."
    ),
)

_DENY_LIST: tuple[DenyListEntry, ...] = (
    _GOTCHA_ENTRY,
    _CHECK_CODE_ENTRY,
    *_V1_FIELD_ENTRIES,
    _PIN_SHAPE_ENTRY,
)


@dataclass(frozen=True)
class Violation:
    path: Path
    lineno: int
    category: str
    entry_name: str
    matched_text: str


def _read_source(path: Path) -> str:
    try:
        # `utf-8-sig`, matching `test_no_config_file.py`'s existing choice
        # (review pass): a plain `utf-8` read leaves a BOM in the text, and
        # `ast.parse` rejects it as a syntax error -- reporting a perfectly
        # runnable module as unscannable.
        return path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        # A file the scanner cannot even read (broken symlink, permissions)
        # is a file it cannot prove clean -- a raw traceback is not an
        # actionable test failure (mirrors test_dependency_direction.py).
        raise AssertionError(
            f"{path}: unreadable ({exc}); the AD-1 recipe-knowledge guard cannot AST-scan this file"
        ) from exc
    except UnicodeDecodeError as exc:
        raise AssertionError(
            f"{path}: not valid UTF-8; the AD-1 recipe-knowledge guard cannot AST-scan this file"
        ) from exc


def _parse_source(source: str, path: Path) -> ast.Module:
    try:
        return ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise AssertionError(
            f"{path}: invalid Python syntax; the AD-1 recipe-knowledge guard cannot AST-scan this file"
        ) from exc


def _constant_text_value(node: ast.expr) -> str | None:
    """Return the string form of a `Constant` node's value -- `str` values
    as-is, `bytes` values decoded (`errors="replace"`) -- or `None` for any
    other constant type or non-`Constant` node (review pass: a bytes literal
    is a real, if unlikely, way to hide denied text from a str-only scan)."""
    if not isinstance(node, ast.Constant):
        return None
    if isinstance(node.value, str):
        return node.value
    if isinstance(node.value, bytes):
        return node.value.decode("utf-8", errors="replace")
    return None


def _first_statement_docstring_ids(body: list[ast.stmt]) -> set[int]:
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return {id(body[0].value)}
    return set()


def _trailing_attribute_docstring_ids(body: list[ast.stmt]) -> set[int]:
    """Return `id()` for every bare string-`Expr` statement in `body` that
    immediately follows an assignment/annotated-assignment -- the PEP
    257-adjacent "attribute docstring" convention this very file uses for
    `_V1_FIELD_NAMES` above (review pass: the original version only
    exempted the first statement of a scope, so this file's own style would
    have false-positived on itself the moment its trailing docstring
    happened to mention a denied term)."""
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


def _format_spec_string_ids(tree: ast.Module) -> set[int]:
    """Return `id()` for every string constant inside an f-string's
    **format spec** (`f"{name:<30}"` -> the `"<30"` constant).

    Exempt from the PIN_SHAPE category only (review pass): a format spec's
    alignment characters are `<`/`>`/`^`/`=` followed by a field width, which
    is character-for-character the pin shape, so ordinary CLI table code --
    `f"{name:<30}{count:>8}"`, and Mason has a `render.py` whose whole job is
    tabular output -- reported two conda-forge pins. The plain `.format()`
    template spelling (`"{:>6} {:<20}"`) is covered by the pattern's `:`
    lookbehind instead, since there the `:` sits in the same constant.

    Scoped to PIN_SHAPE rather than exempting format specs wholesale: a
    gotcha ID or field name has no business in a format spec either, and
    every exemption granted here is a place recipe knowledge could be
    parked.
    """
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FormattedValue) and node.format_spec is not None:
            for sub in ast.walk(node.format_spec):
                if isinstance(sub, ast.Constant):
                    ids.add(id(sub))
    return ids


def _docstring_string_ids(tree: ast.Module) -> set[int]:
    """Return `id()` for every string-constant node exempted from the
    deny-list scan: a real module/class/function docstring, or a trailing
    "attribute docstring" at module or class level (module docstring)."""
    ids: set[int] = set()
    ids |= _first_statement_docstring_ids(tree.body)
    ids |= _trailing_attribute_docstring_ids(tree.body)
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            ids |= _first_statement_docstring_ids(node.body)
        if isinstance(node, ast.ClassDef):
            ids |= _trailing_attribute_docstring_ids(node.body)
    return ids


def _bound_names_in_target(node: ast.expr | None) -> list[tuple[int, str]]:
    """Return `(lineno, name)` for every name a binding target introduces --
    a bare `Name` (`x = ...`), an attribute (`self.run_exports = ...`, the
    single most plausible way a model class would carry recipe knowledge),
    or any nesting of tuple/list/starred unpacking targets."""
    if isinstance(node, ast.Name):
        return [(node.lineno, node.id)]
    if isinstance(node, ast.Attribute):
        return [(node.lineno, node.attr)]
    if isinstance(node, (ast.Tuple, ast.List)):
        return [n for elt in node.elts for n in _bound_names_in_target(elt)]
    if isinstance(node, ast.Starred):
        return _bound_names_in_target(node.value)
    return []


def _collect_identifier_targets(tree: ast.Module) -> list[tuple[int, str]]:
    """Return `(lineno, name)` for every identifier POSITION in `tree` where
    a denied name could be bound, passed, or read -- not string values
    (module docstring: closes the "identifier-shaped recipe knowledge" gap,
    e.g. `def build(*, run_exports=None): ...`, `self.run_exports = [...]`,
    `return spec.run_exports`, `from .helpers import run_exports`,
    `def run_exports(): ...`, `build(run_exports=[...])`).

    Deduplicated on `(lineno, name)`: several branches below legitimately
    see the same identifier (an attribute assignment target is both a
    binding and an `ast.Attribute`), and one violation per position reads
    better than two identical ones.
    """
    targets: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            args = node.args
            all_args = [*args.posonlyargs, *args.args, *args.kwonlyargs]
            if args.vararg is not None:
                all_args.append(args.vararg)
            if args.kwarg is not None:
                all_args.append(args.kwarg)
            targets.extend((a.lineno, a.arg) for a in all_args)

        # Every attribute name, READ as well as written (review pass): the
        # write side (`self.run_exports = ...`) was covered via
        # `_bound_names_in_target`, but `return spec.run_exports` -- the read
        # side of the very same field on a frozen model class -- was not.
        if isinstance(node, ast.Attribute):
            targets.append((node.lineno, node.attr))

        # Every bare name in ANY context, load included (review pass): the
        # docstring claimed read positions were covered, but only attribute
        # reads were -- `from .helpers import *` then `return run_exports`
        # bound the denied name with no `alias` and no assignment to see.
        if isinstance(node, ast.Name):
            targets.append((node.lineno, node.id))

        # PEP 695 type parameters and type aliases (review pass): the package
        # floor is Python >=3.12, so `type run_exports = list[str]` and
        # `def build[pin_subpackage](...)` are live syntax that bound a
        # denied name at a position nothing here looked at.
        if isinstance(node, ast.TypeAlias):
            targets.extend(_bound_names_in_target(node.name))
        if isinstance(node, (ast.TypeVar, ast.ParamSpec, ast.TypeVarTuple)):
            targets.append((node.lineno, node.name))

        # The def/class name itself -- a `def run_exports(...)` helper is
        # recipe knowledge encoded as a call surface (review pass).
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            targets.append((node.lineno, node.name))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                targets.extend(_bound_names_in_target(target))
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets.extend(_bound_names_in_target(node.target))
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            targets.extend(_bound_names_in_target(node.target))
        elif isinstance(node, ast.NamedExpr):
            targets.extend(_bound_names_in_target(node.target))
        elif isinstance(node, ast.withitem):
            targets.extend(_bound_names_in_target(node.optional_vars))
        elif isinstance(node, ast.comprehension):
            targets.extend(_bound_names_in_target(node.target))
        elif isinstance(node, ast.ExceptHandler) and node.name is not None:
            targets.append((node.lineno, node.name))
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            targets.extend((node.lineno, name) for name in node.names)
        elif isinstance(node, ast.alias):
            # `import x.run_exports`, `from .helpers import run_exports`,
            # `import helpers as pin_subpackage` -- an import binds a name
            # just as much as an assignment does (review pass).
            targets.append((node.lineno, node.name))
            if node.asname is not None:
                targets.append((node.lineno, node.asname))
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name is not None:
            targets.append((node.lineno, node.name))
        elif isinstance(node, ast.MatchMapping) and node.rest is not None:
            targets.append((node.lineno, node.rest))
        elif isinstance(node, ast.MatchClass):
            targets.extend((node.lineno, attr) for attr in node.kwd_attrs)
        elif isinstance(node, ast.keyword) and node.arg is not None:
            # A call-site keyword (`build(run_exports=[...])`) names the
            # callee's parameter even when the callee is out of tree.
            targets.append((node.value.lineno, node.arg))
    return list(dict.fromkeys(targets))


def _scan_file_for_deny_list_matches(path: Path, deny_list: Sequence[DenyListEntry]) -> list[Violation]:
    tree = _parse_source(_read_source(path), path)
    docstring_ids = _docstring_string_ids(tree)
    format_spec_ids = _format_spec_string_ids(tree)

    violations: list[Violation] = []
    for node in ast.walk(tree):
        text = _constant_text_value(node)
        if text is None or id(node) in docstring_ids:
            continue
        for entry in deny_list:
            if entry.category == CATEGORY_PIN_SHAPE and id(node) in format_spec_ids:
                continue
            match = entry.pattern.search(text)
            if match is not None:
                violations.append(
                    Violation(
                        path=path,
                        lineno=node.lineno,
                        category=entry.category,
                        entry_name=entry.name,
                        matched_text=match.group(),
                    )
                )

    for lineno, name in _collect_identifier_targets(tree):
        for entry in deny_list:
            if entry.category not in _IDENTIFIER_CAPABLE_CATEGORIES:
                continue
            match = entry.pattern.search(name)
            if match is not None:
                violations.append(
                    Violation(
                        path=path,
                        lineno=lineno,
                        category=entry.category,
                        entry_name=entry.name,
                        matched_text=match.group(),
                    )
                )

    return violations


def _scan_tree_for_deny_list_matches(root: Path, deny_list: Sequence[DenyListEntry]) -> list[Violation]:
    violations: list[Violation] = []
    for path in sorted(root.rglob("*.py")):
        violations.extend(_scan_file_for_deny_list_matches(path, deny_list))
    return violations


def _find_incomplete_entries(
    entries: Sequence[DenyListEntry],
) -> list[DenyListEntry]:
    """Return every entry whose `citation` or `rationale` is empty/
    whitespace-only."""
    return [e for e in entries if not e.citation.strip() or not e.rationale.strip()]


# --- The two real-tree assertions (FR-42) -----------------------------------


def test_no_recipe_knowledge_in_the_real_tree():
    # Guard the guard: a stale PKG_ROOT would make this pass vacuously.
    assert PKG_ROOT.is_dir(), f"AD-1 recipe-knowledge guard is scanning nothing -- package root moved? {PKG_ROOT}"
    # ...and a root that exists but holds no modules is the same vacuity with
    # a green result (review pass: the sibling AD-3 guard already fails loudly
    # when its own source -- cfe.py's table -- parses to nothing; this one had
    # no equivalent).
    assert list(PKG_ROOT.rglob("*.py")), (
        f"AD-1 recipe-knowledge guard found zero modules under {PKG_ROOT} -- it "
        "would pass vacuously; has the package moved or been renamed?"
    )
    violations = _scan_tree_for_deny_list_matches(PKG_ROOT, _DENY_LIST)
    assert not violations, (
        "AD-1: pyforge.mason must contain zero recipe-authoring knowledge; found:\n"
        + "\n".join(
            f"  {v.path}:{v.lineno} [{v.category}] entry {v.entry_name!r} matched {v.matched_text!r}"
            for v in violations
        )
        + (
            f"\n\nIf a [{CATEGORY_PIN_SHAPE}] hit above is an ordinary numeric "
            'message rather than a conda-forge pin ("--timeout must be > 0", '
            '"requires Python >=3.11"), reword the message -- do not weaken the '
            "pattern; see this module's docstring for why that collision is "
            "expected and why the pattern stays broad."
        )
    )


def test_deny_list_entries_all_carry_a_citation_and_rationale():
    incomplete = _find_incomplete_entries(_DENY_LIST)
    assert not incomplete, (
        "deny-list entries missing a citation and/or rationale (FR-42 requires "
        f"both on every entry): {[e.name for e in incomplete]}"
    )


def test_deny_list_covers_all_four_fr42_categories():
    present = {entry.category for entry in _DENY_LIST}
    assert present >= _REQUIRED_CATEGORIES, (
        f"FR-42 requires at minimum the four categories {sorted(_REQUIRED_CATEGORIES)}; "
        f"deny list only covers {sorted(present)}"
    )


def test_deny_list_covers_the_required_v1_field_names():
    """Category presence is not entry coverage (review pass): without this,
    nine of the ten v1 field names could be deleted and the whole suite stays
    green, because `test_deny_list_covers_all_four_fr42_categories` above is
    satisfied by the single survivor."""
    present = {entry.name for entry in _DENY_LIST if entry.category == CATEGORY_V1_FIELD}
    missing = _REQUIRED_V1_FIELD_NAMES - present
    assert not missing, (
        "the deny list no longer covers every v1 field name this guard was "
        f"specified with; missing: {sorted(missing)}. Widening the list is free; "
        "narrowing it must also delete the entry from _REQUIRED_V1_FIELD_NAMES, "
        "with the rationale for the removal in that diff."
    )


def test_deny_list_covers_the_required_check_code_prefixes():
    """The twelve prefixes live in one alternation, so dropping eleven of
    them is a single-token edit (review pass: only `STD-001` was planted, so
    that edit left the whole suite green)."""
    missing = _REQUIRED_CHECK_CODE_PREFIXES - set(_CHECK_CODE_PREFIXES)
    assert not missing, (
        "the deny list no longer covers every CFE check-code prefix this guard "
        f"was specified with; missing: {sorted(missing)}"
    )


@pytest.mark.parametrize("field_name", sorted(_REQUIRED_V1_FIELD_NAMES))
def test_every_required_v1_field_name_is_actually_detected(tmp_path, field_name):
    """Entry presence is not entry function (review pass): neutering seven of
    the ten patterns -- a subtler edit than deleting the entry, and one
    `test_deny_list_covers_the_required_v1_field_names` cannot see -- left the
    whole suite green."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(f'SPEC = {{"{field_name}": ["foo"]}}\n', encoding="utf-8")

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_V1_FIELD and v.entry_name == field_name for v in violations)


@pytest.mark.parametrize("prefix", sorted(_REQUIRED_CHECK_CODE_PREFIXES))
def test_every_required_check_code_prefix_is_actually_detected(tmp_path, prefix):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(f'MSG = "{prefix}-001 fired."\n', encoding="utf-8")

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_CHECK_CODE for v in violations)


# --- Regression fixtures proving the detector itself (mirrors
# test_dependency_direction.py's/test_capability_tiers.py's rigor): synthetic
# trees, not the real package, so these assert the scanner's own behavior
# independent of what src/pyforge/mason/ currently contains. -----------------


def test_detector_fires_on_a_planted_gotcha_identifier(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text('MSG = "See G41 for the fix."\n', encoding="utf-8")

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_GOTCHA for v in violations)


def test_detector_fires_on_a_planted_check_code(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text('MSG = "STD-001 fired."\n', encoding="utf-8")

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_CHECK_CODE for v in violations)


def test_detector_fires_on_a_planted_v1_field_name(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'SPEC = {"run_exports": ["foo"]}\n',
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_V1_FIELD for v in violations)


def test_detector_fires_on_a_planted_pin_shape(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text('PIN = ">=1.0,<2.0"\n', encoding="utf-8")

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_PIN_SHAPE for v in violations)


def test_clean_synthetic_module_produces_zero_matches(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        "VALUE = 42\ndef helper(x):\n    return x + 1\n",
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert violations == []


def test_docstring_mentioning_every_denied_term_is_not_flagged(tmp_path):
    """Design Notes: `cfe.py`'s own docstrings narrate CFE concepts
    extensively without that constituting recipe knowledge -- a module,
    class, and function docstring mentioning every category's term must
    produce zero matches."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "narrator.py").write_text(
        '"""Module docstring narrating G41, STD-001, run_exports, and >=1.0 in prose."""\n'
        "\n"
        "class Foo:\n"
        '    """Class docstring narrating G41, STD-001, run_exports, and >=1.0."""\n'
        "\n"
        "    def bar(self):\n"
        '        """Function docstring narrating G41, STD-001, run_exports, and >=1.0."""\n'
        "        return 1\n",
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert violations == []


def test_the_same_denied_term_outside_a_docstring_is_flagged(tmp_path):
    """Proves the docstring exclusion is targeted, not a blanket suppression
    that would make the whole detector vacuous: the identical text
    ("G41") flags when it is a plain string constant, not a docstring."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "leaky.py").write_text('MSG = "G41"\n', encoding="utf-8")

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert violations != []


def test_trailing_attribute_docstring_mentioning_a_denied_term_is_not_flagged(tmp_path):
    """Review pass: this file's own style for `_V1_FIELD_NAMES` above (a
    bare string statement right after a module-level assignment) must not
    false-positive on itself."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "narrator.py").write_text(
        "_SOME_NAMES = ('a', 'b')\n"
        '"""Mentions G41, STD-001, run_exports, and >=1.0 in prose, mirroring '
        'this file\'s own docstring style."""\n',
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert violations == []


def test_a_bare_string_not_preceded_by_an_assignment_is_still_flagged(tmp_path):
    """Proves the trailing-attribute-docstring exemption requires the
    adjacency (assignment immediately before the string) -- a bare string
    statement with no preceding assignment is not a docstring of anything
    and must still be flagged."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "leaky.py").write_text(
        "print('unrelated')\n'G41'\n",
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert violations != []


def test_detector_fires_on_a_planted_v1_field_as_a_function_parameter(tmp_path):
    """Review pass: identifier POSITIONS, not just string values -- the
    exact `def build(*, run_exports=None): ...` shape the story's own
    motivating pyforge-atlas precedent warns about."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "def build(*, run_exports=None):\n    return run_exports\n",
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_V1_FIELD for v in violations)


def test_detector_fires_on_a_planted_v1_field_as_an_assignment_target(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text("noarch_platforms = ['linux-64']\n", encoding="utf-8")

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_V1_FIELD for v in violations)


def test_detector_fires_on_a_planted_gotcha_as_a_function_parameter(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "def apply_fix(*, G41=False):\n    return G41\n",
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_GOTCHA for v in violations)


def test_detector_fires_on_a_planted_v1_field_as_an_attribute_target(tmp_path):
    """Review pass: `self.<field> = ...` on a model class is the most
    plausible real-world shape for recipe knowledge to land in Mason, and the
    original target set (bare `Name` only) missed it entirely."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "class Spec:\n    def __init__(self):\n        self.run_exports = []\n",
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_V1_FIELD for v in violations)


def test_detector_fires_on_a_planted_v1_field_as_a_function_name(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "def pin_subpackage(name):\n    return name\n",
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_V1_FIELD for v in violations)


def test_detector_fires_on_a_planted_v1_field_as_a_call_site_keyword(tmp_path):
    """`build(run_exports=[...])` names the callee's parameter even when the
    callee lives outside this tree (review pass)."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "from elsewhere import build\n\nbuild(run_exports=['libfoo'])\n",
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_V1_FIELD for v in violations)


def test_detector_fires_on_a_privately_spelled_v1_field(tmp_path):
    """Review pass: `\\b` never fires beside `_`, so the private spelling of
    a denied field -- `self._run_exports`, `def build(*, _run_exports=None)`
    -- passed the very pattern meant to catch it, exactly as
    `G41_WORKAROUND` did before the gotcha entry got the same treatment."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "class Spec:\n"
        "    def __init__(self):\n"
        "        self._run_exports = []\n"
        "\n"
        "\ndef build(*, _pin_subpackage=None):\n"
        "    return _pin_subpackage\n",
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert {v.entry_name for v in violations} >= {"run_exports", "pin_subpackage"}


def test_detector_fires_on_a_v1_field_read_as_an_attribute(tmp_path):
    """Review pass: the write side (`self.run_exports = ...`) was covered
    and the read side was not, so a model class defined elsewhere could be
    consumed field-by-field with no guard firing."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "def summarize(spec):\n    return spec.run_exports\n",
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_V1_FIELD for v in violations)


def test_detector_fires_on_a_v1_field_bound_by_an_import(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "from .helpers import run_exports\nimport helpers as pin_subpackage\n",
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert {v.entry_name for v in violations} >= {"run_exports", "pin_subpackage"}


def test_detector_fires_on_a_v1_field_bound_by_a_comprehension_or_except(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "PAIRS = [zip_keys for zip_keys in range(3)]\n"
        "\n"
        "\ndef load():\n"
        "    try:\n"
        "        return 1\n"
        "    except ValueError as noarch_platforms:\n"
        "        return noarch_platforms\n",
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert {v.entry_name for v in violations} >= {"zip_keys", "noarch_platforms"}


def test_detector_fires_on_an_underscore_adjacent_gotcha_identifier(tmp_path):
    """Review pass: `_` is a word character, so the original `\\bG[0-9]{1,3}\\b`
    never fired beside one -- `G41_WORKAROUND` and `apply_G41_patch` are
    exactly the identifier-shaped gotcha knowledge this scan exists for."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "G41_WORKAROUND = True\n\n\ndef apply_G41_patch():\n    return G41_WORKAROUND\n",
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_GOTCHA for v in violations)


def test_resolution_chain_arrow_before_a_number_is_not_a_pin(tmp_path):
    """Review pass: `->` is this codebase's house notation for a precedence
    chain (`cli.py`'s help strings). Documenting a numeric default inline
    must not be reported as a conda-forge pin."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "cli.py").write_text(
        'HELP = "per-operation CFE subprocess timeout (flag -> MASON_TIMEOUT -> 300)"\n',
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert violations == []


def test_a_real_pin_is_still_flagged_despite_the_arrow_exemption(tmp_path):
    """Negative control for the `-` lookbehind: it must not weaken detection
    of an actual pin expression."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text('PIN = "python >=3.9"\n', encoding="utf-8")

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_PIN_SHAPE for v in violations)


def test_format_spec_alignment_is_not_a_pin(tmp_path):
    """Review pass: a format spec's alignment character is `<`/`>` followed
    by a field width -- character-for-character the pin shape. Mason has a
    `render.py` whose whole job is tabular output, so this collision was one
    table away, not hypothetical. Both spellings must stay clean: the
    f-string form (exempted structurally, the spec is its own constant) and
    the `.format()` template form (exempted by the `:` lookbehind)."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "render.py").write_text(
        'ROW_TEMPLATE = "{:>6} {:<20}"\n\n\ndef row(name, count):\n    return f"{name:<30}{count:>8}"\n',
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert violations == []


def test_a_real_pin_inside_an_f_string_is_still_flagged(tmp_path):
    """Negative control for the format-spec exemption: it is scoped to the
    SPEC, so a pin in the f-string's ordinary literal part still fires."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'def msg(name):\n    return f"{name} >=1.0,<2.0"\n',
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_PIN_SHAPE for v in violations)


def test_pin_shape_does_not_span_a_newline(tmp_path):
    """Review pass: `\\s*` between operator and digit also matched newlines,
    so a `<recipe>` usage line and a `3 exit codes` line two rows below
    reported the pin `">\\n\\n3"`."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "cli.py").write_text(
        'EPILOG = "usage: mason build <recipe>\\n\\n3 exit codes are possible.\\n"\n',
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert violations == []


def test_fat_arrow_before_a_number_is_not_a_pin(tmp_path):
    """Review pass: the `-` lookbehind cleared `->` but not `=>`, the same
    arrow one character different."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "cli.py").write_text(
        'HELP = "flag => MASON_TIMEOUT => 300"\n',
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert violations == []


def test_detector_fires_on_an_uppercase_v1_field_name(tmp_path):
    """Review pass: `RUN_EXPORTS = (...)` is the module-constant spelling --
    recipe semantics encoded as data, exactly AD-1's target -- and the
    case-sensitive pattern let it through."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'RUN_EXPORTS = ("libfoo",)\nX = "IGNORE_RUN_EXPORTS"\n',
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert {v.lineno for v in violations if v.category == CATEGORY_V1_FIELD} == {1, 2}


def test_detector_fires_on_a_lowercase_check_code(tmp_path):
    """Review pass: `"std-001"` names the same CFE check as `"STD-001"`."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text('CODE = "std-001"\n', encoding="utf-8")

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_CHECK_CODE for v in violations)


def test_detector_fires_on_a_v1_field_bound_by_a_pep695_type_alias(tmp_path):
    """Review pass: the package floor is Python >=3.12, so `type X = ...` and
    `def f[X](...)` are live syntax -- and both bound a denied name at a
    position the identifier scan never looked at, while the docstring claimed
    "every place a denied name can be bound"."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "type run_exports = list[str]\n\n\ndef build[pin_subpackage](x):\n    return x\n",
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert {v.lineno for v in violations if v.category == CATEGORY_V1_FIELD} == {1, 4}


def test_detector_fires_on_a_v1_field_read_as_a_bare_name(tmp_path):
    """Review pass: only binding positions were collected, so a star-import
    supplying the name left `return run_exports` -- a read of exactly the
    denied field -- invisible."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "from .helpers import *\n\n\ndef go():\n    return run_exports\n",
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_V1_FIELD for v in violations)


def test_a_utf8_bom_file_is_scanned_not_reported_as_unparseable(tmp_path):
    """Review pass: a BOM-prefixed module is perfectly runnable Python, but a
    plain `utf-8` read leaves the BOM in the text and `ast.parse` rejects it
    -- the guard would red on a valid file with a misleading message."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_bytes(b'\xef\xbb\xbfMSG = "G41"\n')

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_GOTCHA for v in violations)


def test_identifier_scan_does_not_flag_an_unrelated_parameter_name(tmp_path):
    """A parameter name that merely CONTAINS a denied word as a substring
    (not an exact identifier match) must not be flagged -- the detector
    targets the specific field, not any name that happens to embed it."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        "def build(*, run_exports_list=None):\n    return run_exports_list\n",
        encoding="utf-8",
    )

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert violations == []


def test_detector_fires_on_a_bytes_literal_denied_term(tmp_path):
    """Review pass: a `bytes` literal (`b"..."`) is a real, if unlikely, way
    to spell denied text past a `str`-only scan."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text('MSG = b"G41"\n', encoding="utf-8")

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_GOTCHA for v in violations)


def test_pin_shape_detector_tolerates_whitespace_between_operator_and_digit(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text('PIN = ">= 1.0"\n', encoding="utf-8")

    violations = _scan_tree_for_deny_list_matches(root, _DENY_LIST)

    assert any(v.category == CATEGORY_PIN_SHAPE for v in violations)


def test_non_utf8_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").write_bytes(b"\xff\xfe not valid utf-8 \x80\x81")

    with pytest.raises(AssertionError, match="not valid UTF-8"):
        _scan_tree_for_deny_list_matches(root, _DENY_LIST)


def test_invalid_syntax_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").write_text("def(:\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="invalid Python syntax"):
        _scan_tree_for_deny_list_matches(root, _DENY_LIST)


def test_unreadable_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").symlink_to(root / "does-not-exist.py")

    with pytest.raises(AssertionError, match="unreadable"):
        _scan_tree_for_deny_list_matches(root, _DENY_LIST)


# --- Regression fixtures for the rationale-completeness companion test
# itself (I/O matrix: "Deny-list entry missing a citation/rationale ... ->
# companion test fails, naming the entry"). ----------------------------------


def test_completeness_checker_fires_on_a_synthetic_entry_missing_a_rationale():
    incomplete_entry = DenyListEntry(
        category=CATEGORY_GOTCHA,
        name="test-entry-missing-rationale",
        pattern=re.compile(r"\bZZZ\b"),
        citation="some citation",
        rationale="",
    )

    assert _find_incomplete_entries((incomplete_entry,)) == [incomplete_entry]


def test_completeness_checker_fires_on_a_synthetic_entry_missing_a_citation():
    incomplete_entry = DenyListEntry(
        category=CATEGORY_GOTCHA,
        name="test-entry-missing-citation",
        pattern=re.compile(r"\bZZZ\b"),
        citation="   ",
        rationale="some rationale",
    )

    assert _find_incomplete_entries((incomplete_entry,)) == [incomplete_entry]


def test_completeness_checker_permits_a_fully_specified_entry():
    complete_entry = DenyListEntry(
        category=CATEGORY_GOTCHA,
        name="test-entry-complete",
        pattern=re.compile(r"\bZZZ\b"),
        citation="some citation",
        rationale="some rationale",
    )

    assert _find_incomplete_entries((complete_entry,)) == []
