"""Story 61.1 (CAP-271): no marshal module hands a git read a bare local branch name.

Git resolves a short name through ``refs/<n>``, ``refs/tags/<n>``, ``refs/heads/<n>`` in that
order, so a tag named ``main`` stands in for the branch ``main``. Every revision argument of a
``VcsPort`` read therefore names a local branch through ``pyforge.marshal.core.refs.
local_branch_ref`` (``refs/heads/<branch>``).

The scan renders each argument at a revision position (``_REVISION_ARGS``) into templates -- one
per alternative of a conditional -- the way the Story 60.1 meta test renders remote refs: literal
text, ``local_branch_ref(...)``/``remote_tracking_ref(...)`` as ``refs/...``, a name bound to a
string literal (module-level, function-local, a parameter default, or imported from another
marshal module) as that literal, a name assigned some other expression as that expression (up to
``_MAX_DEPTH`` assignments deep), a name whose dotted text reads ``branch`` (without
``sha``/``tip``/``oid``/``commit``) or ends ``base``/``into`` as a branch, and anything else as an
opaque value (a sha). f-strings, ``+``,
``%``, ``str.format`` and ``join`` are rendered through. Each ``..``/``...`` side of a template
must then start with ``refs/``, ``HEAD`` or an opaque value -- a branch or bare literal there is
flagged. The reverse holds too: a parameter that takes a branch *name* and qualifies it itself
(``_NAME_ARGS``) must never receive a template starting ``refs/`` or a ``*_ref`` name, which would
read ``refs/heads/refs/heads/<branch>`` (``fetch`` is one: the adapter names the remote's branch
``refs/heads/<ref>`` itself). Every parameter of every ``VcsPort`` method whose type mentions
``str`` is classified in one of the three tables, so a new port parameter cannot slip past the scan.

Not scanned, by design: git argv lists built outside ``adapters/vcs_git.py`` (AD-4 makes the
adapter the git seam; the few direct shell-outs carry no branch names, per Story 61.1's reviews),
method aliases, ``functools.partial``, ``**kwargs`` and starred arguments, and attributes assigned
elsewhere (``self.x = ...``) -- the name rule still reads their text.
"""

from __future__ import annotations

import ast
import inspect
import itertools
import re
import string
from dataclasses import dataclass
from pathlib import Path

import pyforge.marshal
from pyforge.marshal.core import dispatch as core_dispatch
from pyforge.marshal.core import worktree_checkpoint
from pyforge.marshal.ports.vcs import VcsPort

_PACKAGE = Path(pyforge.marshal.__file__).parent

#: method -> the parameters git reads as a revision (positional index after the receiver, name).
_REVISION_ARGS: dict[str, tuple[tuple[int | None, str], ...]] = {
    "commit_subjects": ((1, "ref"),),
    "merge_base": ((1, "a"), (2, "b")),
    "changed_files": ((None, "base"),),
    "merge_tree_conflict_paths": ((1, "base"), (2, "branch")),
    "merge_tree_write": ((1, "base"), (2, "branch")),
    "file_text_at_ref": ((1, "ref"),),
    "fast_forward": ((1, "ref"),),
    "commits_behind": ((1, "tip_ref"),),
    "merge_branch": ((1, "branch"),),
    "merge_ref_resolving": ((1, "ref"),),
    "add_worktree": ((None, "base"),),
    "add_worktree_for_tree": ((2, "tree_oid"), (None, "parent")),
    "worktree_unified_patch": ((None, "baseline_sha"),),
    "spec_text_at_ref": ((None, "ref"),),
    "commit_worktree_checkpoint": ((None, "base"),),
}
#: method -> the parameters that take a branch NAME (qualified by the method, or read as a name).
_NAME_ARGS: dict[str, tuple[tuple[int | None, str], ...]] = {
    "branch_exists": ((1, "branch"),),
    "worktree_path_for_branch": ((1, "branch"),),
    "add_worktree": ((2, "branch"),),
    "is_branch_merged": ((1, "branch"), (None, "into")),
    "delete_branch": ((1, "branch"),),
    "push": ((1, "branch"),),
    "resolve_ref": ((1, "ref"),),
    "merge_branch": ((None, "into"),),
    "fetch": ((2, "ref"),),
    "commit_paths_onto_remote_tip": ((None, "ref"),),
}
#: `str` parameters that are no ref at all.
_NOT_A_REF = {
    ("tracked_paths_matching", "pathspec"),
    ("merge_branch", "subject"),
    ("fetch", "remote"),
    ("file_text_at_ref", "path"),
    ("merge_ref_resolving", "message"),
    ("commit_paths", "message"),
    ("commit_paths_onto_remote_tip", "remote"),
    ("commit_paths_onto_remote_tip", "message"),
    ("push", "proven_on_main_sha"),  # a sha the adapter re-proves against the full origin/main ref
    ("spec_text_at_ref", "slug"),
    ("spec_text_at_ref", "story"),
    ("commit_worktree_checkpoint", "story_key"),
    ("commit_paths_onto_remote_tip", "writes"),  # (path, text) pairs
    ("merge_ref_resolving", "resolutions"),  # path -> text
}
#: A revision parameter handed straight through to one of the reads above; its callers are
#: scanned in turn (`commit_worktree_checkpoint` defaults `base` to "HEAD").
_PASS_THROUGH = {("core/worktree_checkpoint.py", "base")}
_NON_PORT = {"spec_text_at_ref": core_dispatch.spec_text_at_ref, "commit_worktree_checkpoint": None}
_REF_HELPERS = {"local_branch_ref", "remote_tracking_ref"}
_SHA_MARKERS = ("sha", "tip", "oid", "commit")
_BRANCH = "\x00B"  # a piece holding a branch name
_VALUE = "\x00V"  # a piece holding an opaque value (a sha, HEAD, a ref built elsewhere)
_RANGE = re.compile(r"\.\.\.?")
_PERCENT_FIELD = re.compile(r"%(?:\((\w+)\))?[sdr]")
_MAX_ALTERNATIVES = 16
_MAX_DEPTH = 3  # how many assignments deep a name is rendered through


def _module_constants(tree: ast.Module) -> dict[str, set[str]]:
    bound: dict[str, set[str]] = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        bound.setdefault(target.id, set()).add(node.value.value)
    return bound


def _package_constants() -> dict[str, set[str]]:
    """Module-level string constants across the package, by name -- what an import can bring in."""
    merged: dict[str, set[str]] = {}
    for path in _PACKAGE.rglob("*.py"):
        for name, values in _module_constants(ast.parse(path.read_text(encoding="utf-8"))).items():
            merged.setdefault(name, set()).update(values)
    return merged


@dataclass(frozen=True)
class _Scope:
    """What a name in one scope can hold: string literals, and other expressions assigned to it."""

    strings: dict[str, set[str]]
    exprs: dict[str, list[ast.expr]]
    depth: int = 0

    def deeper(self) -> _Scope:
        return _Scope(self.strings, self.exprs, self.depth + 1)


_FUNCTION = (ast.FunctionDef, ast.AsyncFunctionDef)


def _owners(tree: ast.Module) -> dict[ast.AST, ast.AST]:
    """Every node -> the innermost function whose body holds it (the module for top-level code;
    a function's own parameter defaults belong to that function)."""
    owner: dict[ast.AST, ast.AST] = {}

    def visit(node: ast.AST, current: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            owner[child] = current
            visit(child, child if isinstance(child, _FUNCTION) else current)

    visit(tree, tree)
    return owner


def _bindings_by_owner(tree: ast.Module, package: dict[str, set[str]]) -> dict[ast.AST, _Scope]:
    """Bindings per module / function: string literals assigned (and literal parameter defaults),
    other expressions assigned (review 2: `ref = head_branch`, `probe = ... else base`, `_A = _B`),
    and names imported from sibling marshal modules (module scope). Per function, not per module
    (review 3): `ref = "main"` in one function says nothing about a `ref` in another."""
    owner = _owners(tree)
    scopes: dict[ast.AST, _Scope] = {}

    def scope(node: ast.AST) -> _Scope:
        return scopes.setdefault(node, _Scope({}, {}))

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level > 0:
            for alias in node.names:
                if alias.name in package:
                    scope(tree).strings.setdefault(alias.asname or alias.name, set()).update(package[alias.name])
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            home = scope(owner.get(node, tree))
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    home.strings.setdefault(target.id, set()).add(node.value.value)
                else:
                    home.exprs.setdefault(target.id, []).append(node.value)
        elif isinstance(node, _FUNCTION):
            positional = [*node.args.posonlyargs, *node.args.args]
            pairs = [*zip(positional[len(positional) - len(node.args.defaults) :], node.args.defaults)]
            pairs += [(a, d) for a, d in zip(node.args.kwonlyargs, node.args.kw_defaults) if d is not None]
            for arg, default in pairs:
                if isinstance(default, ast.Constant) and isinstance(default.value, str):
                    scope(node).strings.setdefault(arg.arg, set()).add(default.value)
    return scopes


def _scope_at(node: ast.AST, tree: ast.Module, owner: dict[ast.AST, ast.AST], scopes: dict[ast.AST, _Scope]) -> _Scope:
    """The module's bindings plus every enclosing function's, innermost last."""
    chain: list[ast.AST] = []
    current = owner.get(node, tree)
    while current is not tree:
        chain.append(current)
        current = owner.get(current, tree)
    merged = _Scope({}, {})
    for holder in [tree, *reversed(chain)]:
        found = scopes.get(holder)
        if found is None:
            continue
        for name, values in found.strings.items():
            merged.strings.setdefault(name, set()).update(values)
        for name, exprs in found.exprs.items():
            merged.exprs.setdefault(name, []).extend(exprs)
    return merged


def _is_helper_call(expr: ast.expr) -> bool:
    if not isinstance(expr, ast.Call):
        return False
    func = expr.func
    name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
    return name in _REF_HELPERS


def _branchy(expr: ast.expr) -> bool:
    text = ast.unparse(expr).lower()
    last = text.rsplit(".", 1)[-1]
    return ("branch" in text and not any(marker in last for marker in _SHA_MARKERS)) or last in ("base", "into")


def _product(parts: list[list[str]]) -> list[str]:
    return ["".join(combo) for combo in itertools.islice(itertools.product(*parts), _MAX_ALTERNATIVES)]


def _render(expr: ast.expr | None, bound: _Scope) -> list[str]:
    """Every template ``expr`` can produce."""
    if expr is None:
        return [_VALUE]
    if isinstance(expr, ast.FormattedValue):
        return _render(expr.value, bound)
    if _is_helper_call(expr):
        return ["refs/" + _VALUE]
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return [expr.value]
    if isinstance(expr, ast.IfExp):
        return (_render(expr.body, bound) + _render(expr.orelse, bound))[:_MAX_ALTERNATIVES]
    if isinstance(expr, ast.BoolOp):  # review 3: `base or "main"`
        return [t for value in expr.values for t in _render(value, bound)][:_MAX_ALTERNATIVES]
    if isinstance(expr, ast.Name) and (expr.id in bound.strings or expr.id in bound.exprs):
        alternatives = sorted(bound.strings.get(expr.id, ()))
        if bound.depth < _MAX_DEPTH:
            for value in bound.exprs.get(expr.id, ()):
                alternatives += _render(value, bound.deeper())
        if expr.id in bound.exprs and (_branchy(expr) or bound.depth >= _MAX_DEPTH):
            # Review 3: a name that reads like a branch stays one whatever it was reassigned
            # (`head_branch = head_branch.strip()`); past the depth cap it is judged by name.
            alternatives.append(_BRANCH if _branchy(expr) else _VALUE)
        return alternatives[:_MAX_ALTERNATIVES]
    if isinstance(expr, (ast.Name, ast.Attribute)):
        return [_BRANCH if _branchy(expr) else _VALUE]
    if isinstance(expr, ast.JoinedStr):
        return _product([_render(v, bound) for v in expr.values])
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
        return _product([_render(expr.left, bound), _render(expr.right, bound)])
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Mod) and isinstance(expr.left, ast.Constant):
        fmt = str(expr.left.value)
        values = list(expr.right.elts) if isinstance(expr.right, (ast.Tuple, ast.List)) else [expr.right]
        by_key = {}
        if isinstance(expr.right, ast.Dict):
            by_key = {k.value: v for k, v in zip(expr.right.keys, expr.right.values) if isinstance(k, ast.Constant)}
        pieces: list[list[str]] = []
        position, last = 0, 0
        for match in _PERCENT_FIELD.finditer(fmt):
            pieces.append([fmt[last : match.start()]])
            key = match.group(1)
            if key is not None:
                pieces.append(_render(by_key.get(key), bound))
            else:
                pieces.append(_render(values[position] if position < len(values) else None, bound))
                position += 1
            last = match.end()
        pieces.append([fmt[last:]])
        return _product(pieces)
    if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute):
        func, receiver = expr.func.attr, expr.func.value
        if func == "format" and isinstance(receiver, ast.Constant) and isinstance(receiver.value, str):
            kwargs = {kw.arg: kw.value for kw in expr.keywords if kw.arg}
            pieces, position = [], 0
            for literal, field, _spec, _conv in string.Formatter().parse(receiver.value):
                pieces.append([literal])
                if field is None:
                    continue
                if field == "" or field.isdigit():
                    index = position if field == "" else int(field)
                    position += 1
                    pieces.append(_render(expr.args[index] if index < len(expr.args) else None, bound))
                else:
                    pieces.append(_render(kwargs.get(field), bound))
            return _product(pieces)
        if func == "join" and isinstance(receiver, ast.Constant) and isinstance(receiver.value, str):
            if expr.args and isinstance(expr.args[0], (ast.List, ast.Tuple)):
                parts: list[list[str]] = []
                for index, element in enumerate(expr.args[0].elts):
                    if index:
                        parts.append([receiver.value])
                    parts.append(_render(element, bound))
                return _product(parts)
    return [_VALUE]


def _names_a_bare_branch(template: str) -> bool:
    """A ``..``/``...`` side that starts with a branch or with literal text other than ``refs/``
    or ``HEAD``."""
    for side in _RANGE.split(template):
        if not side or side.startswith(_VALUE) or side.startswith(("refs/", "HEAD")):
            continue
        return True
    return False


def _args_for(call: ast.Call, spec: tuple[tuple[int | None, str], ...]) -> list[ast.expr]:
    found = []
    keywords = {kw.arg: kw.value for kw in call.keywords if kw.arg}
    for index, name in spec:
        if name in keywords:
            found.append(keywords[name])
        elif index is not None and index < len(call.args):
            found.append(call.args[index])
    return found


def _findings(tree: ast.Module, rel: str, package: dict[str, set[str]] | None = None) -> tuple[list[int], list[int]]:
    """(lines where a read gets a bare branch name, lines where a name-taking method gets a ref)."""
    owner = _owners(tree)
    scopes = _bindings_by_owner(tree, package or {})
    bare, doubled = set(), set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        method = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ""
        if method not in _REVISION_ARGS and method not in _NAME_ARGS:
            continue
        bound = _scope_at(node, tree, owner, scopes)
        for arg in _args_for(node, _REVISION_ARGS.get(method, ())):
            if isinstance(arg, ast.Name) and (rel, arg.id) in _PASS_THROUGH:
                continue
            if any(_names_a_bare_branch(t) for t in _render(arg, bound)):
                bare.add(node.lineno)
        for arg in _args_for(node, _NAME_ARGS.get(method, ())):
            named_ref = isinstance(arg, (ast.Name, ast.Attribute)) and ast.unparse(arg).endswith("_ref")
            if named_ref or any(t.startswith("refs/") for t in _render(arg, bound)):
                doubled.add(node.lineno)
    return sorted(bare), sorted(doubled)


def _str_params(method: str) -> list[str]:
    if method in _NON_PORT:
        func = _NON_PORT[method] or worktree_checkpoint.commit_worktree_checkpoint
        params = inspect.signature(func).parameters
    else:
        params = dict(list(inspect.signature(getattr(VcsPort, method)).parameters.items())[1:])  # drop self
    return [name for name, p in params.items() if "str" in str(p.annotation)]


def test_every_str_parameter_of_every_port_method_is_classified() -> None:
    """A new or renamed `VcsPort` parameter must not silently drop out of the scan."""
    port_methods = [
        name for name, member in inspect.getmembers(VcsPort, inspect.isfunction) if not name.startswith("_")
    ]
    classified = {(m, n) for table in (_REVISION_ARGS, _NAME_ARGS) for m, spec in table.items() for _i, n in spec}
    classified |= _NOT_A_REF
    missing = [(m, n) for m in [*port_methods, *_NON_PORT] for n in _str_params(m) if (m, n) not in classified]
    assert missing == [], f"classify these in _REVISION_ARGS, _NAME_ARGS or _NOT_A_REF: {missing}"
    for method, name in classified:
        assert name in _str_params(method), (method, name)


def test_the_positional_indexes_match_the_signatures() -> None:
    for table in (_REVISION_ARGS, _NAME_ARGS):
        for method, spec in table.items():
            if method in _NON_PORT:
                func = _NON_PORT[method] or worktree_checkpoint.commit_worktree_checkpoint
                params = list(inspect.signature(func).parameters)
            else:
                params = list(inspect.signature(getattr(VcsPort, method)).parameters)[1:]
            for index, name in spec:
                if index is not None:
                    assert params[index] == name, (method, index, name)


def test_no_git_read_receives_a_bare_local_branch_name() -> None:
    package = _package_constants()
    bare, doubled = [], []
    for path in sorted(_PACKAGE.rglob("*.py")):
        if path == _PACKAGE / "core" / "refs.py":
            continue
        rel = path.relative_to(_PACKAGE).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        found_bare, found_doubled = _findings(tree, rel, package)
        bare += [f"{rel}:{line}" for line in found_bare]
        doubled += [f"{rel}:{line}" for line in found_doubled]
    assert bare == [], f"bare local branch names handed to a git read (wrap in local_branch_ref): {bare}"
    assert doubled == [], f"a full ref handed to a method that takes a branch name: {doubled}"


def test_the_scan_catches_every_spelling_and_spares_the_rest() -> None:
    source = "\n".join(
        [
            '_MERGE_BASE = "main"',  # 1
            "vcs.commit_subjects(root, _MERGE_BASE)",  # 2: a constant bound to a bare name
            'vcs.commit_subjects(root, "main")',  # 3: the literal
            "vcs.merge_base(root, head_branch, base)",  # 4: *branch* and base
            'vcs.commit_subjects(root, f"{merge_base_sha}..{head_branch}")',  # 5: a range
            'vcs.add_worktree(root, home, branch, base="main")',  # 6: the mint's start point
            "vcs.changed_files(root, home, base=_SCOPE_CHECK_BASE_BRANCH)",  # 7
            "vcs.merge_base(repo_root, commit_sha, into)",  # 8: the supervisor's station branch
            "vcs.commit_subjects(root, effective.landing_base_branch.value)",  # 9: the policy value
            "vcs.merge_branch(root, head_branch, into=base, subject=s)",  # 10: the heal's merge
            "vcs.merge_tree_conflict_paths(root, probe, head_branch)",  # 11
            "vcs.file_text_at_ref(root, head_branch, rel)",  # 12
            'from ..elsewhere import IMPORTED_BASE; ref = "main"',  # 13
            "vcs.commit_subjects(root, ref)",  # 14: review 1 -- a function-local literal
            "vcs.commit_subjects(root, IMPORTED_BASE)",  # 15: review 1 -- an imported constant
            'vcs.commit_subjects(root, sha if c else "main")',  # 16: review 1 -- a conditional
            'vcs.commit_subjects(root, sha + ".." + head_branch)',  # 17: review 1 -- a + chain
            'vcs.commit_subjects(root, "%s..%s" % (sha, head_branch))',  # 18: review 1 -- %-format
            'vcs.commit_subjects(root, "{}..{}".format(sha, head_branch))',  # 19: review 1 -- format
            'vcs.worktree_unified_patch(wt, baseline_sha="main")',  # 20: review 1 -- an unlisted read
            "vcs.commit_subjects(root, local_branch_ref(_MERGE_BASE))",  # 21: wrapped
            "vcs.merge_base(root, head_ref, base_ref)",  # 22: already refs
            'vcs.commit_subjects(root, f"{merge_base_sha}..{head_ref}")',  # 23
            "vcs.merge_branch(root, branch_tip_after_gate, into=_MERGE_BASE_BRANCH, subject=s)",  # 24: a sha
            'vcs.changed_files(root, home, base="HEAD")',  # 25
            "vcs.changed_files(root, home, base=ORIGIN_MAIN)",  # 26
            'vcs.commit_subjects(root, f"refs/heads/{branch}")',  # 27: review 1 -- hand-built full ref
            "vcs.resolve_ref(root, local_branch_ref(branch))",  # 28: a name-taker given a ref
            "vcs.push(root, local_branch_ref(base))",  # 29: likewise
            "vcs.is_branch_merged(root, branch, into=local_branch_ref(base))",  # 30: likewise
            "vcs.resolve_ref(root, head_ref)",  # 31: review 1 -- a *_ref variable
            'vcs.is_branch_merged(root, branch, into=f"refs/heads/{base}")',  # 32: review 1 -- f-string
            'vcs.commit_paths_onto_remote_tip(root, remote="origin", ref=local_branch_ref("main"), w=w, message=m)',  # 33
            "vcs.resolve_ref(root, head_branch)",  # 34: a name-taker given a name
            'vcs.fetch(root, "origin", "main")',  # 35: likewise
        ]
    )
    bare, doubled = _findings(ast.parse(source), "scratch.py", {"IMPORTED_BASE": {"main"}})
    assert bare == [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20]
    assert doubled == [28, 29, 30, 31, 32, 33]


def test_an_imported_constant_is_resolved_across_modules() -> None:
    source = "from ..dispatch_land import _MERGE_BASE as BASE\nvcs.commit_subjects(root, BASE)\n"
    bare, _doubled = _findings(ast.parse(source), "scratch.py", _package_constants())
    assert bare == [2]


def test_the_scan_follows_a_name_through_what_is_assigned_to_it() -> None:
    """Review 2: a branch reaching a read through one more name."""
    source = "\n".join(
        [
            "ref = head_branch",  # 1
            "vcs.commit_subjects(root, ref)",  # 2
            '_DEFAULT = "main"',  # 3
            "_MERGE_INTO = _DEFAULT",  # 4
            "vcs.commit_subjects(root, _MERGE_INTO)",  # 5
            "probe = probe_ref if probe_ref is not None else base",  # 6: the pre-61.1 heal
            "vcs.file_text_at_ref(root, probe, rel)",  # 7
            "healed = probe_ref if probe_ref is not None else local_branch_ref(base)",  # 8: the fix
            "vcs.file_text_at_ref(root, healed, rel)",  # 9
            "full = local_branch_ref(branch)",  # 10
            "vcs.resolve_ref(root, full)",  # 11: a name-taker given a ref through a name
            'def f(start="main"):',  # 12
            "    vcs.commit_subjects(root, start)",  # 13: a parameter's literal default
        ]
    )
    bare, doubled = _findings(ast.parse(source), "scratch.py")
    assert bare == [2, 5, 7, 13]
    assert doubled == [11]


def test_a_reassigned_branch_stays_a_branch_and_bindings_stay_in_their_function() -> None:
    """Review 3: the review-2 rendering dropped the name rule once a name was reassigned, and read
    one function's bindings into another."""
    source = "\n".join(
        [
            "def a(base):",  # 1
            '    base = base or "main"',  # 2: the package's own default idiom
            "    vcs.commit_subjects(root, base)",  # 3
            "def b(effective):",  # 4
            "    base = effective.landing_base_branch.value or _DEFAULT",  # 5
            "    vcs.commit_subjects(root, base)",  # 6
            "def c(head_branch):",  # 7
            "    head_branch = head_branch.strip()",  # 8
            "    vcs.commit_subjects(root, head_branch)",  # 9
            "def d(args):",  # 10
            "    branch = str(args.branch)",  # 11
            "    vcs.commit_subjects(root, branch)",  # 12
            "def e(cfg):",  # 13
            '    into = cfg["into"]',  # 14
            "    vcs.merge_base(root, sha, into)",  # 15
            "def g(base):",  # 16
            "    vcs.commit_subjects(root, base)",  # 17: h's `base = compute()` is not g's
            "def h():",  # 18
            "    base = compute()",  # 19
            'def i(ref="HEAD"):',  # 20
            "    vcs.commit_subjects(root, ref)",  # 21: j's default is j's
            'def j(ref="main"):',  # 22
            "    return ref",  # 23
            "def k(sha):",  # 24
            "    ref = sha",  # 25
            "    vcs.commit_subjects(root, ref)",  # 26: l's `ref = head_branch` is l's
            "def l(head_branch):",  # 27
            "    ref = head_branch",  # 28
            "    return ref",  # 29
        ]
    )
    bare, _doubled = _findings(ast.parse(source), "scratch.py")
    assert bare == [3, 6, 9, 12, 15, 17]
