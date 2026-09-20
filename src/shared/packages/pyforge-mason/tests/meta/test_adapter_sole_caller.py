"""AD-3 -- the CFE port is the sole CFE caller: `cfe.py` is the only module
that may name a CFE script, hold a CFE path, or spawn a process against one
(FR-43).

Three flagged shapes, AST-based (walking `ast.Constant` string/bytes nodes
and `ast.Call` nodes, never raw-text/regex -- matches every sibling
meta-test's documented rationale), over every `.py` file under
`src/pyforge/mason/` **except `cfe.py` itself**, which is excluded from the
scan entirely (it is the one module allowed to hold this knowledge):

(a) **CFE path** -- a string constant containing the literal substring
    `.claude/scripts/conda-forge-expert` (NOT the bare word
    `"conda-forge-expert"` alone, which legitimately appears in `cli.py`'s
    help text -- "wraps the conda-forge-expert craft" -- without naming a
    filesystem path), OR the same path **assembled from segments** --
    `root / ".claude" / "scripts" / "conda-forge-expert" / ...` or
    `os.path.join(...)`/`.joinpath(...)`/`Path(a, b, c)`, including segments
    passed as a list/tuple literal or unpacked with `*` (`"/".join([".claude",
    ...])`, `os.path.join(*SEGMENTS_LITERAL)`) -- whose string-constant parts
    join to that substring. The segment form is not an exotic evasion: it is
    `cfe.py`'s own house idiom (`cfe.py:730`), so before the review pass that
    added it here, a second module could have reimplemented `cfe.py`'s entire
    invocation verbatim -- path build plus `subprocess.run` -- and the one
    guard whose job is to make `cfe.py` the sole CFE caller would have
    reported the tree clean. Spellings are folded together by
    `_normalized_path_text` before matching -- separators, doubled
    separators, `.` components and CASE (review pass: macOS/Windows
    filesystems are case-insensitive, so `".Claude\\Scripts\\
    conda-forge-expert"` names the same directory and scanned clean while
    this very paragraph already claimed the Windows spelling was covered).
    Allowlisted for exactly two files, matched by
    **resolved path relative to the scan root**, not bare filename (review
    pass: a bare-filename allowlist would silently exempt any future
    same-named file elsewhere in the tree, e.g. `engines/resolve.py` --
    mirrors `test_dependency_direction.py`'s own documented "full resolved
    paths, not bare filenames" fix for the identical footgun):
    `resolve.py` (AD-3's carve-out for `_CFE_MARKER`, needed for AD-5's pure
    root-resolution walk) and `errors.py` (`CfeUnresolvedError._MESSAGE`'s
    user-guidance echo of that same path). No other file is allowlisted for
    this category, and this scan examines every string constant, including
    docstrings -- unlike `test_no_recipe_knowledge.py`'s deny-list scan,
    which excludes docstrings for an unrelated reason (AD-1 targets recipe
    *semantics*, not the mere mention of a CFE path).

(b) **CFE script filename** -- a string constant CONTAINING one of
    `cfe.py`'s own `_CFE_SCRIPTS` table values, parsed from `cfe.py`'s AST
    (never hand-duplicated, so the two tables cannot silently drift apart as
    later stories add entries to `_CFE_SCRIPTS` -- Design Notes). Parsing
    fails loudly (not silently skips) if the table is missing, duplicated,
    or holds a non-literal-string value (review pass) -- a silent skip there
    would make every downstream assertion in this file pass vacuously. No
    allowlist anywhere, including `resolve.py`/`errors.py`.
    Containment, not equality (review pass): under an equality test a script
    name hoisted into a module constant -- `_CMD = "python validate_recipe.py
    --json"`, then `os.system(_CMD)` -- matched nothing, and the whole CFE
    script path spelled out inside an allowlisted file
    (`resolve.py`: `VALIDATE = ".claude/scripts/conda-forge-expert/
    validate_recipe.py"`) matched nothing either, since category (a) is
    allowlisted there and the string equals no bare table value. Both scanned
    completely clean. Naming a CFE script in Mason prose is itself what AD-3
    forbids, so the widening has no false-positive class to trade against:
    zero non-`cfe.py` occurrences exist today.

(c) **Subprocess call carrying either pattern** -- a call shaped like
    `subprocess.run`/`Popen`/`call`/`check_call`/`check_output`/`getoutput`/
    `getstatusoutput`/`os.system`/`os.popen`/`os.startfile`/`os.spawn*`/
    `os.exec*`/`os.posix_spawn`/`asyncio.create_subprocess_exec`/
    `create_subprocess_shell` (review pass: the original set only recognized
    five `subprocess`-module names, missing `os`/`asyncio`'s own spawn
    surfaces -- AD-2's subprocess-import guard restricts `import subprocess`
    but not `import os`/`import asyncio`, so those were a real, unguarded
    evasion route; a follow-up pass added the `os.exec*` family and
    `subprocess.getoutput`/`getstatusoutput`, whose single-shell-string shape
    is exactly the one that motivated the containment rule below) whose
    argument list (positional or keyword) contains a string -- literal **or
    segment-assembled, as in (a)** -- matching (a) or **containing** (b).
    Containment, not equality, is the rule here (review pass): a shell
    one-liner passes one argument, so
    `os.system("python validate_recipe.py --json")` names a CFE script in a
    string that equals no table value and slipped past an equality test.
    (Category (b) itself stays exact-equality over standalone constants, per
    spec.) No allowlist anywhere, including inside an
    otherwise-allowlisted file -- `resolve.py`/`errors.py` may hold the
    marker/echo as inert data, but neither may ever spawn a process with it.
    The segment-assembled form is checked here independently of (a)'s
    allowlist suppression (review pass: (a)'s join scan is skipped wholesale
    inside an allowlisted file, so a spawn there against a joined CFE path
    was invisible -- the one shape this category's "no allowlist anywhere"
    guarantee most needed to cover).

Every process-spawning call name this file recognizes is pinned by
`_REQUIRED_SPAWN_CALL_NAMES` and exercised by a parametrized fixture (review
pass: the table could be narrowed from nineteen names to two with the whole
suite green, since only three names had a fixture).

Both (a) and (b) also recognize a `bytes` constant (`b"..."`), decoded
UTF-8/`errors="replace"` before matching (review pass) -- the deny-list
scanner in `test_no_recipe_knowledge.py` needs no equivalent, since a
`bytes` literal is never a docstring and the two files' matching logic is
otherwise independent.

Known, accepted residual limitations (not attempted here -- open-ended,
belongs to a dedicated static-analysis effort, not a meta-test): a CFE path
or script name assembled via string concatenation (`"a" + "b"`), segments
routed through an intermediate variable (`base = root / ".claude"; base /
"scripts" / ...`, which the segment-join detector above sees as two unrelated
expressions), a dynamically-constructed call target (`getattr(subprocess,
"run")(...)`), or indirect rebinding (`spawn = subprocess.run; spawn(...)`)
evade every detector in this file. Each needs dataflow, not pattern matching.
Recorded in the project's deferred-work ledger. An f-string is NOT in this
list (review pass corrected the earlier claim that it was): its literal parts
are ordinary `ast.Constant` children, so `f"{root}/.claude/scripts/
conda-forge-expert/{name}"` is reported -- a maintainer who trusts a stale
"f-strings evade" note would read that red as a false positive and exempt it.

`_SUBPROCESS_CALL_NAMES` is a NAME LIST, not a proof of completeness: it
covers `subprocess`/`os`/`asyncio`/`pty`/`runpy`/`multiprocessing`, and any
launcher outside it is invisible to category (c). Outside an allowlisted file
category (a) still backstops a literal CFE path; INSIDE `resolve.py`/
`errors.py` there is no backstop, which is what made `pty.spawn`/
`runpy.run_path`/`multiprocessing.Process` a real hole rather than a
theoretical one (review pass added all three). Widening the list further is
free.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "mason"
_CFE_MODULE_NAME = "cfe.py"

_CFE_PATH_SUBSTRING = ".claude/scripts/conda-forge-expert"
"""The literal substring the CFE-path detector searches for -- NOT the bare
word "conda-forge-expert" alone (module docstring)."""

_ALLOWLISTED_CFE_PATH_RELATIVE_PATHS = frozenset({Path("resolve.py"), Path("errors.py")})
"""AD-3's exactly-two-entry carve-out, matched by path RELATIVE TO THE SCAN
ROOT (resolved to an absolute path before comparison), not bare filename
(module docstring) -- applies only to the CFE-PATH category (a). CFE script
filenames (b) and subprocess calls (c) have no allowlist anywhere, including
inside these two files."""

_SUBPROCESS_CALL_NAMES = frozenset(
    {
        "run",
        "Popen",
        "call",
        "check_call",
        "check_output",
        "getoutput",
        "getstatusoutput",
        "system",
        "popen",
        "startfile",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "posix_spawn",
        "posix_spawnp",
        "execl",
        "execle",
        "execlp",
        "execlpe",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        "create_subprocess_exec",
        "create_subprocess_shell",
        "subprocess_exec",
        "subprocess_shell",
        "spawn",
        "run_path",
        "run_module",
        "Process",
    }
)
"""Every process-spawning call name this guard recognizes, across
`subprocess`/`os`/`asyncio`/`pty`/`runpy`/`multiprocessing` -- matched on
bare attribute/function name only
(module docstring's "known, accepted residual limitations": no receiver or
import-origin resolution, so an unrelated method sharing one of these names
is indistinguishable from a real spawn call by this detector alone)."""

_REQUIRED_SPAWN_CALL_NAMES = frozenset(
    {
        "run",
        "Popen",
        "call",
        "check_call",
        "check_output",
        "getoutput",
        "getstatusoutput",
        "system",
        "popen",
        "startfile",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "posix_spawn",
        "posix_spawnp",
        "execl",
        "execle",
        "execlp",
        "execlpe",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        "create_subprocess_exec",
        "create_subprocess_shell",
        "subprocess_exec",
        "subprocess_shell",
        "spawn",
        "run_path",
        "run_module",
        "Process",
    }
)
"""The spawn surface this guard is specified to cover, spelled out
INDEPENDENTLY of `_SUBPROCESS_CALL_NAMES` above (deriving it from that set
would delete itself along with whatever name was dropped) and pinned as a
floor by `test_spawn_call_names_cover_the_required_process_spawning_surface`
+ a parametrized detection fixture per name (review pass: only `run`,
`system` and a bare `run` had fixtures, so the table could be narrowed to
those two names with the whole suite green -- making "delete a line from the
frozenset" the cheapest way to reopen AD-3's spawn seam). Widening is free;
narrowing now has to delete a named floor entry too, which is the reviewable
diff this guard exists to force."""

CATEGORY_CFE_PATH = "cfe-path"
CATEGORY_CFE_SCRIPT = "cfe-script-filename"
CATEGORY_SUBPROCESS_ARG = "subprocess-cfe-argument"


@dataclass(frozen=True)
class Violation:
    path: Path
    lineno: int
    category: str
    detail: str


def _read_source(path: Path) -> str:
    try:
        # `utf-8-sig`, matching `test_no_config_file.py`'s existing choice
        # (review pass): a plain `utf-8` read leaves a BOM in the text, and
        # `ast.parse` rejects it as a syntax error -- reporting a perfectly
        # runnable module as unscannable.
        return path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise AssertionError(
            f"{path}: unreadable ({exc}); the AD-3 sole-caller guard cannot AST-scan this file"
        ) from exc
    except UnicodeDecodeError as exc:
        raise AssertionError(f"{path}: not valid UTF-8; the AD-3 sole-caller guard cannot AST-scan this file") from exc


def _parse_source(source: str, path: Path) -> ast.Module:
    try:
        return ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise AssertionError(
            f"{path}: invalid Python syntax; the AD-3 sole-caller guard cannot AST-scan this file"
        ) from exc


def _constant_text_value(node: ast.expr) -> str | None:
    """Return the string form of a `Constant` node's value -- `str` values
    as-is, `bytes` values decoded (`errors="replace"`, matching this suite's
    established encoding-tolerance convention) -- or `None` for any other
    constant type or non-`Constant` node (review pass: a bytes literal is a
    real, if unlikely, way to hide a CFE path/script name from a str-only
    scan)."""
    if not isinstance(node, ast.Constant):
        return None
    if isinstance(node.value, str):
        return node.value
    if isinstance(node.value, bytes):
        return node.value.decode("utf-8", errors="replace")
    return None


def _parse_cfe_script_filenames(cfe_path: Path) -> frozenset[str]:
    """Parse `_CFE_SCRIPTS`'s dict *values* (script filenames) out of
    `cfe.py`'s own AST -- never hand-duplicated (Design Notes: "so the two
    tables cannot silently drift apart as Stories 2.4-2.10 add entries").

    Recognizes both the annotated (`_CFE_SCRIPTS: dict[str, str] = {...}`,
    `cfe.py`'s real shape) and plain (`_CFE_SCRIPTS = {...}`) assignment
    forms. Fails loudly -- rather than silently returning an empty set, or
    silently keeping only the first of several matches -- if the table is
    missing, duplicated, or holds a value that isn't a plain string literal
    (review pass): any of those would make this guard's allowlist source
    quietly wrong, and every downstream assertion in this file pass
    vacuously or incorrectly.
    """
    tree = _parse_source(_read_source(cfe_path), cfe_path)
    tables: list[ast.Dict] = []
    for node in ast.walk(tree):
        target_name: str | None = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name = node.target.id
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name = node.targets[0].id

        if target_name == "_CFE_SCRIPTS" and isinstance(node.value, ast.Dict):
            tables.append(node.value)

    if len(tables) != 1:
        raise AssertionError(
            f"{cfe_path}: expected exactly one `_CFE_SCRIPTS` dict-literal "
            f"assignment, found {len(tables)} -- has cfe.py's table been "
            "renamed, restructured, or duplicated?"
        )

    filenames: list[str] = []
    for value_node in tables[0].values:
        text = _constant_text_value(value_node)
        if text is None:
            raise AssertionError(
                f"{cfe_path}: a `_CFE_SCRIPTS` value is not a plain string/bytes "
                f"literal ({ast.dump(value_node)}) -- this guard can only verify "
                "script filenames declared as literals"
            )
        filenames.append(text)
    return frozenset(filenames)


def _normalized_path_text(text: str) -> str:
    """`text` reduced to the one spelling `_CFE_PATH_SUBSTRING` is written
    in: forward separators, no doubled separators, no `.` components, lower
    case. Every normalization here exists because the un-normalized spelling
    was found to walk straight through:

    * backslashes -- `_CFE_PATH_SUBSTRING` is POSIX-spelled, so the identical
      path written Windows-style missed (review pass);
    * doubled separators -- a segment carrying its own trailing separator
      (`Path(".claude/") / "scripts" / ...`) assembles to `.claude//scripts/
      ...` (review pass);
    * `.` components -- `".claude/./scripts/conda-forge-expert"` names the
      same directory (review pass);
    * case -- macOS and Windows filesystems are case-insensitive, so
      `".Claude\\Scripts\\conda-forge-expert"` resolves to the CFE wrapper
      directory on the platforms Mason supports, yet scanned clean while this
      module's docstring already claimed the Windows spelling was covered
      (review pass).
    """
    normalized = re.sub(r"/+", "/", text.replace("\\", "/"))
    return re.sub(r"/(?:\./)+", "/", normalized).lower()


def _names_a_cfe_path(text: str) -> bool:
    """True if `text` names the CFE wrapper directory, under any spelling
    `_normalized_path_text` folds together."""
    return _CFE_PATH_SUBSTRING in _normalized_path_text(text)


_PATH_CONSTRUCTOR_NAMES = frozenset(
    {"Path", "PurePath", "PurePosixPath", "PureWindowsPath", "PosixPath", "WindowsPath"}
)
"""`pathlib` constructors that join their arguments -- `Path("a", "b", "c")`
is exactly `Path("a") / "b" / "c"` (review pass: the multi-argument
constructor is the most idiomatic pathlib spelling of a path build and was
recognized by neither the `/`-operator form nor the `join`/`joinpath` name,
so `Path(root, ".claude", "scripts", "conda-forge-expert", name)` -- with its
`subprocess.run` -- scanned completely clean)."""


def _is_join_call(node: ast.expr) -> bool:
    """True for an `os.path.join(...)`/`posixpath.join(...)`/
    `Path(...).joinpath(...)`/bare `join(...)` call, or a MULTI-argument
    `pathlib` constructor (`Path("a", "b", "c")`, review pass -- a
    single-argument `Path("a")` is a wrapper `_segment_text` already unwraps,
    not a join). Matched on the bare `join`/`joinpath`/constructor name, like
    `_SUBPROCESS_CALL_NAMES` above: no receiver resolution, so
    `", ".join(parts)` is treated as a path build too -- it simply assembles
    to nothing reportable unless its own arguments spell the CFE path, which
    is precisely the `"/".join([".claude", "scripts", "conda-forge-expert"])`
    shape this must catch (review pass: the earlier wording here claimed a
    `str.join` could not assemble a reportable path at all, which was true
    only for the `join(parts)` form and false for the literal-list form that
    walked straight through)."""
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Attribute):
        name = node.func.attr
    elif isinstance(node.func, ast.Name):
        name = node.func.id
    else:
        return False
    if name in {"join", "joinpath"}:
        return True
    # `pathlib.Path(a, b, c)` as well as a bare `Path(a, b, c)`.
    return name in _PATH_CONSTRUCTOR_NAMES and len(node.args) > 1


def _segment_text(node: ast.expr) -> str | None:
    """The literal path text one segment of a join expression contributes:
    a string/bytes constant, a nested join, the elements of a list/tuple
    literal or a `*`-unpacked one (`"/".join([".claude", ...])`,
    `os.path.join(*SEGMENTS)`, review pass), or the constant arguments of a
    wrapping call (`Path(".claude")`). `None` for a segment carrying no
    literal at all -- a `Name` (`root`), a `Subscript`
    (`_CFE_SCRIPTS[key]`) -- which is simply skipped.

    Skipping deliberately errs toward over-detection: the assembled text CAN
    span a skipped segment, so `base / ".claude" / plugin / "scripts" /
    "conda-forge-expert"` is reported as the CFE path (review pass corrected
    the earlier claim here that this could not happen). That is the safer
    direction for a guard whose whole value is that it cannot be evaded --
    substituting a placeholder instead would let `root / ".claude" /
    SCRIPTS_DIRNAME / "conda-forge-expert"` walk straight through, and the
    failure message names the assembled path, so a false positive is one
    glance to dismiss.
    """
    nested = _joined_segment_text(node)
    if nested is not None:
        return nested

    text = _constant_text_value(node)
    if text is not None:
        return text

    if isinstance(node, (ast.List, ast.Tuple)):
        elements = [t for elt in node.elts if (t := _segment_text(elt)) is not None]
        return "/".join(elements) if elements else None

    if isinstance(node, ast.Starred):
        return _segment_text(node.value)

    if isinstance(node, ast.Call):
        args = [t for arg in node.args if (t := _constant_text_value(arg)) is not None]
        return "/".join(args) if args else None

    return None


def _joined_segment_text(node: ast.expr) -> str | None:
    """Assemble the literal segments of a path-joining expression -- a `/`
    operator chain (`root / ".claude" / "scripts" / ...`, `cfe.py:730`'s own
    idiom) or an `os.path.join(...)`/`.joinpath(...)`/`Path(a, b, c)` call --
    into a `/`-separated path, or return `None` if `node` is not one of those
    shapes **or carries no literal segment at all** (review pass: returning
    `""` for the latter made the stated contract false and collected every
    ordinary arithmetic `total / count` in the tree as a "path build")."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        segments = [text for side in (node.left, node.right) if (text := _segment_text(side)) is not None]
        return "/".join(segments) if segments else None

    if _is_join_call(node):
        # `.joinpath(...)`'s RECEIVER carries the leading segment
        # (`Path(".claude").joinpath("scripts", ...)`), unlike `join`'s,
        # which is a separator string or the `os.path` module.
        parts = list(node.args)  # type: ignore[attr-defined]
        if isinstance(node.func, ast.Attribute) and node.func.attr == "joinpath":  # type: ignore[attr-defined]
            parts.insert(0, node.func.value)  # type: ignore[attr-defined]
        segments = [text for part in parts if (text := _segment_text(part)) is not None]
        return "/".join(segments) if segments else None

    return None


def _segment_child_nodes(node: ast.expr) -> list[ast.expr]:
    """The sub-expressions `node` consumes as join segments -- so they are
    segments of a larger build, not path builds in their own right."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return [node.left, node.right]

    if _is_join_call(node):
        children: list[ast.expr] = []
        if isinstance(node.func, ast.Attribute) and node.func.attr == "joinpath":  # type: ignore[attr-defined]
            children.append(node.func.value)  # type: ignore[attr-defined]
        for arg in node.args:  # type: ignore[attr-defined]
            children.append(arg)
            if isinstance(arg, (ast.List, ast.Tuple)):
                children.extend(arg.elts)
            elif isinstance(arg, ast.Starred):
                children.append(arg.value)
        return children

    return []


def _outermost_join_nodes(tree: ast.AST) -> list[ast.expr]:
    """Every path-joining expression in `tree` that is not itself a segment
    of a larger one -- reporting each nesting level would report one path
    build several times (review pass: the earlier version collected only a
    `/` chain's LEFT operand, so a right-nested chain or a join call nested
    inside another one was still reported twice)."""
    nested_ids = {
        id(child) for node in ast.walk(tree) if isinstance(node, ast.expr) for child in _segment_child_nodes(node)
    }
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.expr) and id(node) not in nested_ids and _joined_segment_text(node) is not None
    ]


def _is_subprocess_spawn_call(func: ast.expr) -> bool:
    """True for a call shaped like `subprocess.run(...)`/`os.system(...)`
    (an attribute access ending in one of the spawn names) or a bare
    `run(...)` (the `from subprocess import run` idiom)."""
    if isinstance(func, ast.Attribute):
        return func.attr in _SUBPROCESS_CALL_NAMES
    if isinstance(func, ast.Name):
        return func.id in _SUBPROCESS_CALL_NAMES
    return False


def _string_constants_in(nodes: list[ast.expr]) -> list[str]:
    values: list[str] = []
    for node in nodes:
        for sub in ast.walk(node):
            text = _constant_text_value(sub)
            if text is not None:
                values.append(text)
    return values


def _joined_path_texts_in(nodes: list[ast.expr]) -> list[str]:
    """Every segment-assembled path text reachable inside `nodes` -- the
    category-(a) join detector applied to a call's argument list, so a spawn
    against a joined CFE path is caught by category (c) even inside a file
    allowlisted for holding that path (review pass)."""
    texts: list[str] = []
    for node in nodes:
        for join_node in _outermost_join_nodes(node):
            joined = _joined_segment_text(join_node)
            if joined is not None:
                texts.append(joined)
    return texts


def _scan_file(path: Path, is_allowlisted_for_path: bool, cfe_script_filenames: frozenset[str]) -> list[Violation]:
    tree = _parse_source(_read_source(path), path)

    violations: list[Violation] = []
    for node in ast.walk(tree):
        text = _constant_text_value(node)
        if text is not None:
            if _names_a_cfe_path(text) and not is_allowlisted_for_path:
                violations.append(Violation(path, node.lineno, CATEGORY_CFE_PATH, text))
            if any(name in text for name in cfe_script_filenames):
                violations.append(Violation(path, node.lineno, CATEGORY_CFE_SCRIPT, text))
        elif isinstance(node, ast.Call) and _is_subprocess_spawn_call(node.func):
            arg_nodes = [*node.args, *(kw.value for kw in node.keywords)]
            arg_values = _string_constants_in(arg_nodes) + _joined_path_texts_in(arg_nodes)
            for value in arg_values:
                if _names_a_cfe_path(value) or any(name in value for name in cfe_script_filenames):
                    violations.append(Violation(path, node.lineno, CATEGORY_SUBPROCESS_ARG, value))

    if not is_allowlisted_for_path:
        for node in _outermost_join_nodes(tree):
            joined = _joined_segment_text(node)
            if joined is not None and _names_a_cfe_path(joined):
                violations.append(Violation(path, node.lineno, CATEGORY_CFE_PATH, joined))

    return violations


def _scan_tree(root: Path, cfe_script_filenames: frozenset[str]) -> list[Violation]:
    """Scan every `.py` file under `root` except a file literally named
    `cfe.py` directly inside it -- the one module this guard does not
    police."""
    excluded = (root / _CFE_MODULE_NAME).resolve()
    allowlisted_for_path = {(root / rel).resolve() for rel in _ALLOWLISTED_CFE_PATH_RELATIVE_PATHS}
    violations: list[Violation] = []
    for path in sorted(root.rglob("*.py")):
        resolved = path.resolve()
        if resolved == excluded:
            continue
        violations.extend(_scan_file(path, resolved in allowlisted_for_path, cfe_script_filenames))
    return violations


# --- The real-tree assertion (FR-43) -----------------------------------


def test_no_unallowlisted_cfe_reference_outside_cfe_py():
    # Guard the guard: a stale PKG_ROOT would make this pass vacuously.
    assert PKG_ROOT.is_dir(), f"AD-3 sole-caller guard is scanning nothing -- package root moved? {PKG_ROOT}"
    script_filenames = _parse_cfe_script_filenames(PKG_ROOT / _CFE_MODULE_NAME)
    assert script_filenames, (
        "cfe.py's _CFE_SCRIPTS table parsed to zero script filenames -- has it moved or been renamed?"
    )

    violations = _scan_tree(PKG_ROOT, script_filenames)

    assert not violations, (
        "AD-3: only cfe.py may reference a CFE path, a CFE script filename, or "
        "spawn a process against one; found:\n"
        + "\n".join(f"  {v.path}:{v.lineno} [{v.category}] {v.detail!r}" for v in violations)
    )


def test_cfe_path_allowlist_is_exactly_ad3s_two_live_carve_outs():
    """The allowlist is the one place AD-3 can be widened, and widening it
    costs a single line (review pass: adding a third entry -- or keeping a
    dead one after its file stops needing the exemption -- left the whole
    suite green). Pins the membership to AD-3's two named carve-outs and
    proves each is still live: the file exists and still holds the CFE path
    it was exempted for."""
    assert _ALLOWLISTED_CFE_PATH_RELATIVE_PATHS == frozenset({Path("resolve.py"), Path("errors.py")}), (
        "AD-3 carves out exactly two files (resolve.py's _CFE_MARKER and "
        "errors.py's guidance echo); changing this set widens the seam this "
        "guard exists to hold closed"
    )

    for relative_path in sorted(_ALLOWLISTED_CFE_PATH_RELATIVE_PATHS):
        path = PKG_ROOT / relative_path
        assert path.is_file(), f"allowlisted file no longer exists: {path}"
        # Liveness is checked through the AST scanner with the allowlist
        # bypassed, NOT by raw text (review pass): a raw-text check sees only
        # a literal spelling, so the moment a carve-out file adopted the
        # segment-join form this very file's own fixtures bless
        # (`Path('.claude') / 'scripts' / 'conda-forge-expert'`) the guard
        # would have reported its still-live exemption dead -- and the
        # obvious repair to that failure is deleting a live carve-out.
        held_paths = [v for v in _scan_file(path, False, frozenset()) if v.category == CATEGORY_CFE_PATH]
        assert held_paths, (
            f"stale carve-out: {relative_path} no longer contains a CFE path, so "
            "its AD-3 exemption is dead and should be deleted rather than left "
            "covering whatever that file grows next"
        )


def test_parse_cfe_script_filenames_reads_the_real_cfe_py():
    """Ties this guard's allowlist source directly to cfe.py's real table --
    if a future story renames `_CFE_SCRIPTS` or restructures it, this test
    (not just the vacuity guard above) fails first. Story 2.4 adds
    `recipe-generator.py` to the Story 1.9 fixture pair. Story 2.6 adds the
    two build-adapter entries (`build_native`/`build_docker`). Story 2.7
    adds `failure_analyzer.py`. Story 2.8 adds `recipe_optimizer.py`/
    `vulnerability_scanner.py`. Story 2.10 adds `recipe_updater.py`/
    `github_updater.py`, the table's ninth and tenth entries."""
    assert _parse_cfe_script_filenames(PKG_ROOT / _CFE_MODULE_NAME) == frozenset(
        {
            "validate_recipe.py",
            "submit_pr.py",
            "recipe-generator.py",
            "native-build.sh",
            "build-locally.py",
            "failure_analyzer.py",
            "recipe_optimizer.py",
            "vulnerability_scanner.py",
            "recipe_updater.py",
            "github_updater.py",
        }
    )


# --- Regression fixtures proving the detector itself (mirrors the sibling
# meta-tests' rigor): synthetic trees, not the real package. -----------------

_SCRIPT_FILENAMES = frozenset({"validate_recipe.py", "submit_pr.py"})


def test_detector_fires_on_a_cfe_path_outside_the_allowlist(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'MARKER = ".claude/scripts/conda-forge-expert"\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_CFE_PATH for v in violations)


def test_detector_permits_the_real_marker_in_resolve_and_errors(tmp_path):
    """The two-entry allowlist as it exists in the real tree today:
    `resolve.py`'s `_CFE_MARKER` and `errors.py`'s guidance echo."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "resolve.py").write_text(
        '_CFE_MARKER = ".claude/scripts/conda-forge-expert"\n',
        encoding="utf-8",
    )
    (root / "errors.py").write_text(
        '_MESSAGE = "... below a directory containing .claude/scripts/conda-forge-expert/."\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert violations == []


def test_allowlist_is_matched_by_path_not_bare_filename(tmp_path):
    """Review pass: a same-named file OUTSIDE the two allowlisted top-level
    paths must not inherit the carve-out -- e.g. a future `engines/resolve.py`
    mirrors `test_dependency_direction.py`'s own "full resolved paths, not
    bare filenames" regression test for the identical footgun."""
    root = tmp_path / "mason"
    root.mkdir()
    nested = root / "engines"
    nested.mkdir()
    (nested / "resolve.py").write_text(
        'MARKER = ".claude/scripts/conda-forge-expert"\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_CFE_PATH for v in violations)


def test_detector_fires_on_a_cfe_script_filename_anywhere_no_allowlist(tmp_path):
    """Pattern (b) has no allowlist -- planting a bare script filename even
    inside the allowlisted `resolve.py` must still be flagged."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "resolve.py").write_text('X = "validate_recipe.py"\n', encoding="utf-8")

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_CFE_SCRIPT for v in violations)


def test_detector_fires_on_a_subprocess_call_with_a_cfe_argument(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'import subprocess\nsubprocess.run(["python", "validate_recipe.py"])\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_SUBPROCESS_ARG for v in violations)


def test_detector_fires_on_an_os_system_call_with_a_cfe_argument(tmp_path):
    """Review pass: `os.system`/`os.spawn*`/`asyncio.create_subprocess_*`
    require `import os`/`import asyncio`, neither restricted by AD-2's
    subprocess-import guard -- an unguarded evasion route the original
    5-name `_SUBPROCESS_CALL_NAMES` set missed entirely."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'import os\nos.system("python .claude/scripts/conda-forge-expert/validate_recipe.py")\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_SUBPROCESS_ARG for v in violations)


def test_detector_fires_on_a_subprocess_call_even_inside_an_allowlisted_file(tmp_path):
    """Pattern (c) has no allowlist anywhere -- a subprocess call planted
    inside `resolve.py` (allowlisted only for holding the CFE path as inert
    data) must still be flagged."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "resolve.py").write_text(
        'import subprocess\nsubprocess.run(["python", ".claude/scripts/conda-forge-expert/validate_recipe.py"])\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_SUBPROCESS_ARG for v in violations)


def test_detector_fires_on_a_bare_imported_subprocess_call_form(tmp_path):
    """The `from subprocess import run` idiom -- a bare `run(...)` call --
    must be recognized identically to `subprocess.run(...)`."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'from subprocess import run\nrun(["python", "submit_pr.py"])\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_SUBPROCESS_ARG for v in violations)


def test_detector_fires_on_a_segment_joined_cfe_path(tmp_path):
    """Review pass, highest-consequence gap closed in this file: `cfe.py:730`
    builds the CFE path as `root / ".claude" / "scripts" / ...`, so a module
    reimplementing `cfe.py`'s own invocation verbatim -- the exact failure
    AD-3 exists to prevent -- contained no matching string constant and
    scanned completely clean."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "import subprocess\n"
        "from pathlib import Path\n"
        "\n"
        "_SCRIPTS = {'validate_recipe': 'validate_recipe.py'}\n"
        "\n"
        "\n"
        "def run(cfe_root, key):\n"
        "    script = cfe_root / '.claude' / 'scripts' / 'conda-forge-expert' / _SCRIPTS[key]\n"
        "    return subprocess.run(['python', str(script)])\n",
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_CFE_PATH for v in violations)


def test_detector_fires_on_an_os_path_join_cfe_path(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "import os.path\n\nCFE_DIR = os.path.join('.claude', 'scripts', 'conda-forge-expert')\n",
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_CFE_PATH for v in violations)


def test_segment_join_detection_honours_the_two_entry_allowlist(tmp_path):
    """The segment-join detector is the same category (a) as the literal
    one, so `resolve.py`'s carve-out covers it identically -- and a nested
    same-named file still does not inherit that carve-out."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "resolve.py").write_text(
        "from pathlib import Path\n\n_CFE_MARKER = Path('.claude') / 'scripts' / 'conda-forge-expert'\n",
        encoding="utf-8",
    )
    nested = root / "engines"
    nested.mkdir()
    (nested / "resolve.py").write_text(
        "from pathlib import Path\n\n_MARKER = Path('.claude') / 'scripts' / 'conda-forge-expert'\n",
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert [v.path for v in violations] == [nested / "resolve.py"]


def test_segment_join_detection_does_not_flag_an_unrelated_path_build(tmp_path):
    """Clean control: joining ordinary path segments -- including a lone
    `.claude` that never reaches the CFE wrapper directory -- must not
    fire."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        "from pathlib import Path\n\n\ndef find(base):\n    return base / '.claude' / 'settings.json'\n",
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert violations == []


def test_detector_fires_on_a_join_call_with_a_list_of_segments(tmp_path):
    """Review pass: the join detector read a call's positional arguments but
    never descended into a list/tuple literal, so this module -- a generic
    "run any CFE script" passthrough, the whole of what AD-3 forbids -- had
    no matching string constant anywhere and scanned completely clean. The
    script name never appears as a literal either, so category (b) cannot
    backstop it."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "import subprocess\n"
        '\n_CFE_DIR = "/".join([".claude", "scripts", "conda-forge-expert"])\n'
        "\n"
        "\ndef run_any_cfe_script(root, script, args):\n"
        '    return subprocess.run(["python", f"{root}/{_CFE_DIR}/{script}", *args])\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_CFE_PATH for v in violations)


def test_detector_fires_on_a_joinpath_call(tmp_path):
    """`Path(...).joinpath(...)` is the same path build as the `/` chain and
    was matched by neither the `join` name nor the operator form."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'from pathlib import Path\n\nMARKER = Path(".claude").joinpath("scripts", "conda-forge-expert")\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_CFE_PATH for v in violations)


def test_detector_fires_on_a_starred_join_argument(tmp_path):
    """`os.path.join(*(...))` unpacks a literal tuple -- the segments are all
    present in the expression, just one node deeper."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'import os.path\n\nCFE_DIR = os.path.join(*(".claude", "scripts", "conda-forge-expert"))\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_CFE_PATH for v in violations)


def test_detector_fires_on_a_multi_argument_path_constructor(tmp_path):
    """Review pass: `Path(a, b, c)` is exactly `Path(a) / b / c` and is the
    most idiomatic pathlib spelling of a path build, but was matched by
    neither the `/`-operator form nor the `join`/`joinpath` name -- so this
    module, a verbatim reimplementation of `cfe.py`'s invocation with the
    script name caller-supplied, scanned completely clean."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "import subprocess\n"
        "from pathlib import Path\n"
        "\n"
        "\ndef go(cfe_root, name):\n"
        "    script = Path(cfe_root, '.claude', 'scripts', 'conda-forge-expert', name)\n"
        "    return subprocess.run(['python', str(script)])\n",
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_CFE_PATH for v in violations)


def test_single_argument_path_constructor_is_not_treated_as_a_join(tmp_path):
    """Negative control for the constructor rule above: `Path(".claude")` is
    a wrapper, not a join, and joining it with an unrelated segment must stay
    clean -- otherwise the widening would have bought detection with a false
    positive on ordinary pathlib code."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        'from pathlib import Path\n\nSETTINGS = Path(".claude") / "settings.json"\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert violations == []


def test_detector_fires_on_a_case_variant_cfe_path(tmp_path):
    """Review pass: macOS and Windows filesystems are case-insensitive, so
    this literal names the real CFE wrapper directory -- yet the match was
    case-sensitive while the module docstring already claimed the Windows
    spelling was covered."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'MARKER = ".Claude\\\\Scripts\\\\conda-forge-expert"\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_CFE_PATH for v in violations)


def test_detector_fires_on_a_dot_segment_cfe_path(tmp_path):
    """`.claude/./scripts/...` names the same directory (review pass)."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'MARKER = ".claude/./scripts/conda-forge-expert"\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_CFE_PATH for v in violations)


def test_detector_fires_on_a_full_script_path_inside_an_allowlisted_file(tmp_path):
    """Review pass: the category-(a) carve-out is file-level per spec, so
    `resolve.py` may hold the CFE path -- but a COMPLETE script path there is
    category (b), which has no allowlist. Under the previous exact-equality
    rule the string equalled no bare table value and category (a) was
    suppressed, so it scanned clean."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "resolve.py").write_text(
        'VALIDATE = ".claude/scripts/conda-forge-expert/validate_recipe.py"\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_CFE_SCRIPT for v in violations)


def test_detector_fires_on_a_script_name_hoisted_into_a_module_constant(tmp_path):
    """Review pass: category (c) reads only the spawn call's OWN argument
    subtree, so hoisting the command one line up left nothing for it to read
    -- and exact-equality category (b) did not match the longer string. The
    fixture proving the shell-one-liner shape was covered was defeated by a
    one-line hoist."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'import os\n\n_CMD = "python validate_recipe.py --json"\n\n\ndef go():\n    return os.system(_CMD)\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_CFE_SCRIPT for v in violations)


def test_detector_fires_on_a_non_subprocess_launcher_inside_an_allowlisted_file(
    tmp_path,
):
    """Review pass, highest-consequence gap closed in this pass: inside an
    allowlisted file category (a) is suppressed wholesale, so category (c) is
    the only guard left -- and it recognized neither `pty.spawn` nor
    `runpy.run_path` nor `multiprocessing.Process`. `resolve.py` could
    therefore launch a CFE script and the tree reported clean."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "resolve.py").write_text(
        "import pty\n"
        "import runpy\n"
        "\n"
        "\ndef go():\n"
        '    pty.spawn(["python", ".claude/scripts/conda-forge-expert/validate_recipe.py"])\n'
        '    runpy.run_path(".claude/scripts/conda-forge-expert/submit_pr.py")\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert [v.lineno for v in violations if v.category == CATEGORY_SUBPROCESS_ARG] == [
        6,
        7,
    ]


def test_ordinary_division_is_not_collected_as_a_path_build():
    """Review pass: `_joined_segment_text` returned `""` -- not `None` -- for
    a `/` expression carrying no literal, contradicting its own documented
    contract and collecting every arithmetic division in the tree."""
    tree = ast.parse("ratio = total / count\n")
    assert _outermost_join_nodes(tree) == []


def test_detector_fires_on_a_doubled_separator_cfe_path(tmp_path):
    """A segment carrying its own trailing separator assembles to
    `.claude//scripts/...`, which the raw substring test missed."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'from pathlib import Path\n\nMARKER = Path(".claude/") / "scripts" / "conda-forge-expert"\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_CFE_PATH for v in violations)


def test_subprocess_detection_sees_a_joined_path_inside_an_allowlisted_file(tmp_path):
    """Category (c)'s "no allowlist anywhere" guarantee, for the segment
    form (review pass): category (a)'s join scan is skipped wholesale inside
    an allowlisted file, so `resolve.py` could assemble the CFE path inside
    the spawn call itself and run it -- with the script name supplied by a
    variable, so category (b) never fires either -- and the guard reported
    the tree clean. (Hoisting the path build into a preceding local first is
    the module docstring's already-recorded intermediate-variable
    limitation, not this fixture's subject.)"""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "resolve.py").write_text(
        "import subprocess\n"
        "from pathlib import Path\n"
        "\n"
        "\ndef go(root, name):\n"
        "    return subprocess.run(\n"
        "        ['python', str(root / '.claude' / 'scripts' / 'conda-forge-expert' / name)]\n"
        "    )\n",
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_SUBPROCESS_ARG for v in violations)


def test_spawn_call_names_cover_the_required_process_spawning_surface():
    """Review pass: `_SUBPROCESS_CALL_NAMES` could be narrowed from nineteen
    names to two with the whole suite green, because only three names had a
    fixture -- making a one-line deletion the cheapest way to reopen the
    spawn seam."""
    missing = _REQUIRED_SPAWN_CALL_NAMES - _SUBPROCESS_CALL_NAMES
    assert not missing, (
        "the spawn detector no longer recognizes every process-spawning call "
        f"name this guard was specified with; missing: {sorted(missing)}. "
        "Widening the set is free; narrowing it must also delete the name from "
        "_REQUIRED_SPAWN_CALL_NAMES, with the rationale in that diff."
    )


@pytest.mark.parametrize("call_name", sorted(_REQUIRED_SPAWN_CALL_NAMES))
def test_every_required_spawn_call_name_is_actually_detected(tmp_path, call_name):
    """One planted call per recognized name -- membership in the frozenset
    is not detection, and only three of the names were ever exercised."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        f'import os\n\nos.{call_name}("python validate_recipe.py")\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_SUBPROCESS_ARG for v in violations)


def test_detector_fires_on_a_script_name_inside_a_shell_command_string(tmp_path):
    """Review pass: a shell one-liner passes the whole command as ONE
    argument, so an equality test against `_CFE_SCRIPTS`' values never
    matched it."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'import os\n\nos.system("python validate_recipe.py --json /tmp/recipe")\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_SUBPROCESS_ARG for v in violations)


def test_detector_fires_on_a_backslash_spelled_cfe_path(tmp_path):
    """Review pass: `_CFE_PATH_SUBSTRING` is POSIX-spelled, so the identical
    path written with Windows separators walked straight through."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'MARKER = ".claude\\\\scripts\\\\conda-forge-expert"\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_CFE_PATH for v in violations)


def test_a_utf8_bom_file_is_scanned_not_reported_as_unparseable(tmp_path):
    """Review pass: a BOM-prefixed module is perfectly runnable Python, but a
    plain `utf-8` read leaves the BOM in the text and `ast.parse` rejects
    it."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_bytes(b'\xef\xbb\xbfMARKER = ".claude/scripts/conda-forge-expert"\n')

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_CFE_PATH for v in violations)


def test_detector_fires_on_a_bytes_literal_cfe_path(tmp_path):
    """Review pass: a `bytes` literal (`b"..."`) is a real, if unlikely, way
    to spell a CFE path/script name past a `str`-only scan."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'MARKER = b".claude/scripts/conda-forge-expert"\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert any(v.category == CATEGORY_CFE_PATH for v in violations)


def test_detector_ignores_cfe_py_itself(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "cfe.py").write_text(
        'PATH = ".claude/scripts/conda-forge-expert"\n'
        'SCRIPT = "validate_recipe.py"\n'
        "import subprocess\n"
        'subprocess.run(["python", "validate_recipe.py"])\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert violations == []


def test_bare_conda_forge_expert_mention_without_path_prefix_is_not_flagged(tmp_path):
    """`cli.py`'s real help text ("wraps the conda-forge-expert craft")
    mentions the bare word without the `.claude/scripts/` path prefix and
    must not be flagged."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "cli.py").write_text(
        'HELP = "author, validate and build conda recipes (wraps the conda-forge-expert craft)"\n',
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert violations == []


def test_clean_synthetic_module_produces_zero_matches(tmp_path):
    """Clean-tree control: a synthetic module with no CFE reference at all
    produces zero matches -- proves the detector is not vacuously flagging
    everything."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        "def helper(x):\n    return x + 1\n",
        encoding="utf-8",
    )

    violations = _scan_tree(root, _SCRIPT_FILENAMES)

    assert violations == []


def test_non_utf8_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").write_bytes(b"\xff\xfe not valid utf-8 \x80\x81")

    with pytest.raises(AssertionError, match="not valid UTF-8"):
        _scan_tree(root, _SCRIPT_FILENAMES)


def test_invalid_syntax_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").write_text("def(:\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="invalid Python syntax"):
        _scan_tree(root, _SCRIPT_FILENAMES)


def test_unreadable_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").symlink_to(root / "does-not-exist.py")

    with pytest.raises(AssertionError, match="unreadable"):
        _scan_tree(root, _SCRIPT_FILENAMES)


def test_parse_cfe_script_filenames_fails_loudly_on_a_non_literal_value(tmp_path):
    """Review pass: a `_CFE_SCRIPTS` value that isn't a plain string/bytes
    literal (e.g. a variable reference) must not be silently dropped from
    the allowlist source -- that would make the real-tree assertion pass
    vacuously for whatever script it names."""
    root = tmp_path / "mason"
    root.mkdir()
    fake_cfe = root / "cfe.py"
    fake_cfe.write_text(
        "SOME_NAME = 'x.py'\n_CFE_SCRIPTS: dict[str, str] = {'validate_recipe': SOME_NAME}\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="not a plain string/bytes literal"):
        _parse_cfe_script_filenames(fake_cfe)


def test_parse_cfe_script_filenames_fails_loudly_on_a_duplicated_table(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    fake_cfe = root / "cfe.py"
    fake_cfe.write_text(
        "_CFE_SCRIPTS = {'a': 'a.py'}\n_CFE_SCRIPTS = {'b': 'b.py'}\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="found 2"):
        _parse_cfe_script_filenames(fake_cfe)
