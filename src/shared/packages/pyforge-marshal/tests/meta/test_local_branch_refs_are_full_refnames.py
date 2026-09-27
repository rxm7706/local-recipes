"""Story 61.1 (CAP-271): no marshal module hands a git read a bare local branch name.

Git resolves a short name through ``refs/<n>``, ``refs/tags/<n>``, ``refs/heads/<n>`` in that
order, so a tag named ``main`` stands in for the branch ``main``. Every revision argument of a
``VcsPort`` read therefore names a local branch through ``pyforge.marshal.core.refs.
local_branch_ref`` (``refs/heads/<branch>``). This scan looks at each call to a method in
``_REVISION_ARGS`` and flags an argument that is a bare-name literal (anything but ``HEAD`` or a
``refs/...`` string), a module constant bound to one, or a name whose dotted text reads
``branch`` (and no ``sha``/``tip``/``oid``/``commit``) or ends ``base``/``into`` -- directly or
inside an f-string range. The reverse holds too: a method that takes a branch *name* and
qualifies it itself (``_NAME_ARGS``) must never receive a full ref, which would read
``refs/heads/refs/heads/<branch>``. Where the Story 60.1 meta test renders remote refs from
their text, local branches carry no text of their own, so this one reads names; the self-tests
pin each spelling.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pyforge.marshal
from pyforge.marshal.core import dispatch as core_dispatch
from pyforge.marshal.core import worktree_checkpoint
from pyforge.marshal.ports.vcs import VcsPort

_PACKAGE = Path(pyforge.marshal.__file__).parent

#: method -> the parameters that git reads as a revision (positional index after the receiver,
#: keyword name). `add_worktree`'s `branch` is a name (the attach path is bare on purpose).
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
    "add_worktree_for_tree": ((None, "parent"),),
    "spec_text_at_ref": ((None, "ref"),),
    "commit_worktree_checkpoint": ((None, "base"),),
}
#: method -> the parameters that take a branch NAME the method qualifies (or reads as a name).
_NAME_ARGS: dict[str, tuple[tuple[int | None, str], ...]] = {
    "branch_exists": ((1, "branch"),),
    "worktree_path_for_branch": ((1, "branch"),),
    "add_worktree": ((2, "branch"),),
    "is_branch_merged": ((1, "branch"), (None, "into")),
    "delete_branch": ((1, "branch"),),
    "push": ((1, "branch"),),
    "resolve_ref": ((1, "ref"),),
    "merge_branch": ((None, "into"),),
}
#: A revision parameter handed straight through to one of the reads above; its callers are
#: scanned in turn (`commit_worktree_checkpoint` defaults `base` to "HEAD").
_PASS_THROUGH = {("core/worktree_checkpoint.py", "base")}
_REF_HELPERS = {"local_branch_ref", "remote_tracking_ref"}
_SHA_MARKERS = ("sha", "tip", "oid", "commit")


def _module_strings(tree: ast.Module) -> dict[str, str]:
    """Module-level ``NAME = "literal"`` bindings."""
    bound: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                bound |= {t.id: node.value.value for t in targets if isinstance(t, ast.Name)}
    return bound


def _is_helper_call(expr: ast.expr) -> bool:
    if not isinstance(expr, ast.Call):
        return False
    func = expr.func
    name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
    return name in _REF_HELPERS


def _bare(expr: ast.expr, strings: dict[str, str]) -> bool:
    """True when ``expr`` hands git a bare local branch name."""
    if _is_helper_call(expr):
        return False
    if isinstance(expr, ast.Name) and expr.id in strings:
        expr = ast.Constant(strings[expr.id])
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value != "HEAD" and not expr.value.startswith("refs/")
    if isinstance(expr, ast.JoinedStr):
        return any(_bare(v.value, strings) for v in expr.values if isinstance(v, ast.FormattedValue))
    if isinstance(expr, (ast.Name, ast.Attribute)):
        text = ast.unparse(expr).lower()
        last = text.rsplit(".", 1)[-1]
        branchy = "branch" in text and not any(marker in last for marker in _SHA_MARKERS)
        return branchy or last in ("base", "into")
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


def _findings(tree: ast.Module, rel: str) -> tuple[list[int], list[int]]:
    """(lines where a read gets a bare branch name, lines where a name-taking method gets a ref)."""
    strings = _module_strings(tree)
    bare, doubled = set(), set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        method = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ""
        for arg in _args_for(node, _REVISION_ARGS.get(method, ())):
            if isinstance(arg, ast.Name) and (rel, arg.id) in _PASS_THROUGH:
                continue
            if _bare(arg, strings):
                bare.add(node.lineno)
        for arg in _args_for(node, _NAME_ARGS.get(method, ())):
            if _is_helper_call(arg) or (isinstance(arg, ast.Constant) and str(arg.value).startswith("refs/")):
                doubled.add(node.lineno)
    return sorted(bare), sorted(doubled)


def test_the_parameter_tables_match_the_port() -> None:
    """A renamed or moved parameter must not silently drop out of the scan."""
    for table in (_REVISION_ARGS, _NAME_ARGS):
        for method, spec in table.items():
            if method == "spec_text_at_ref":
                params = list(inspect.signature(core_dispatch.spec_text_at_ref).parameters)
            elif method == "commit_worktree_checkpoint":
                params = list(inspect.signature(worktree_checkpoint.commit_worktree_checkpoint).parameters)
            else:
                params = list(inspect.signature(getattr(VcsPort, method)).parameters)[1:]  # drop self
            for index, name in spec:
                assert name in params, (method, name)
                if index is not None:
                    assert params[index] == name, (method, index, name)


def test_no_git_read_receives_a_bare_local_branch_name() -> None:
    bare, doubled = [], []
    for path in sorted(_PACKAGE.rglob("*.py")):
        if path == _PACKAGE / "core" / "refs.py":
            continue
        rel = path.relative_to(_PACKAGE).as_posix()
        found_bare, found_doubled = _findings(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)), rel)
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
            "vcs.commit_subjects(root, local_branch_ref(_MERGE_BASE))",  # 13: wrapped
            "vcs.merge_base(root, head_ref, base_ref)",  # 14: already refs
            'vcs.commit_subjects(root, f"{merge_base_sha}..{head_ref}")',  # 15
            "vcs.merge_branch(root, branch_tip_after_gate, into=_MERGE_BASE_BRANCH, subject=s)",  # 16: a sha
            'vcs.changed_files(root, home, base="HEAD")',  # 17
            "vcs.changed_files(root, home, base=ORIGIN_MAIN)",  # 18
            "vcs.add_worktree(root, home, branch, base=_BASE_REF)",  # 19
            "vcs.resolve_ref(root, local_branch_ref(branch))",  # 20: a name-taker given a ref
            "vcs.push(root, local_branch_ref(base))",  # 21: likewise
            "vcs.is_branch_merged(root, branch, into=local_branch_ref(base))",  # 22: likewise
            "vcs.resolve_ref(root, head_branch)",  # 23: a name-taker given a name
        ]
    )
    bare, doubled = _findings(ast.parse(source), "scratch.py")
    assert bare == [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    assert doubled == [20, 21, 22]
