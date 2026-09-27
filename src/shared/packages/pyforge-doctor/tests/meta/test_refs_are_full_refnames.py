"""Story 31.1 (spec-pyforge-doctor CAP-85): no Doctor module hands git a bare branch name.

Git resolves a short name through ``refs/<n>``, ``refs/tags/<n>``, ``refs/heads/<n>``, then
``refs/remotes/<n>``, so ``main`` can be a tag's commit and ``origin/main`` a local branch's. Every
Doctor source reaches git through ``_git(target, *args)`` or ``run_git(target, [args])``; this scan
renders each argument (a literal, an f-string, or a name bound to a module-level literal) and
flags one whose revision part is ``main`` or ``origin/...`` -- also either side of a ``..`` range
and the revision before a ``rev:path`` colon. It flags a base-like parameter (``base``,
``base_ref``, ``head``, ``ref``, ``rev``, ``branch``) whose default is such a literal, since every
caller runs the sources on their defaults. Text with whitespace is a message people read, not a
ref. Full refs come from ``pyforge.doctor.refs``, which is exempt.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pyforge.doctor

_PACKAGE = Path(pyforge.doctor.__file__).parent
_GIT_CALLS = {"_git", "run_git", "_git_ok"}
_BASE_PARAMS = {"base", "base_ref", "head", "ref", "rev", "branch"}
_BARE = re.compile(r"^(?:main|origin/\S*)$")
_SPLIT = re.compile(r"\.\.\.?|:")


def _constants(tree: ast.Module) -> dict[str, str]:
    bound: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                bound |= {t.id: node.value.value for t in targets if isinstance(t, ast.Name)}
    return bound


def _text(expr: ast.expr, bound: dict[str, str]) -> str | None:
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value
    if isinstance(expr, ast.Name) and expr.id in bound:
        return bound[expr.id]
    if isinstance(expr, ast.JoinedStr):
        parts = []
        for value in expr.values:
            text = _text(value.value, bound) if isinstance(value, ast.FormattedValue) else _text(value, bound)
            parts.append(text if text is not None else "\x00")  # an opaque value
        return "".join(parts)
    return None


def _bare(text: str | None) -> bool:
    if text is None or any(ch.isspace() for ch in text):
        return False
    return any(_BARE.match(side) for side in _SPLIT.split(text))


def _findings(tree: ast.Module) -> list[int]:
    bound = _constants(tree)
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
            if name not in _GIT_CALLS:
                continue
            args: list[ast.expr] = []
            for arg in node.args:
                args.extend(arg.elts if isinstance(arg, (ast.List, ast.Tuple)) else [arg])
            if any(_bare(_text(arg, bound)) for arg in args):
                lines.add(node.lineno)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            positional = [*node.args.posonlyargs, *node.args.args]
            pairs = [*zip(positional[len(positional) - len(node.args.defaults) :], node.args.defaults)]
            pairs += [(a, d) for a, d in zip(node.args.kwonlyargs, node.args.kw_defaults) if d is not None]
            for arg, default in pairs:
                if arg.arg in _BASE_PARAMS and _bare(_text(default, bound)):
                    lines.add(node.lineno)
    return sorted(lines)


def test_no_doctor_module_hands_git_a_bare_branch_name() -> None:
    offenders = []
    for path in sorted(_PACKAGE.rglob("*.py")):
        if path == _PACKAGE / "refs.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        offenders += [f"{path.relative_to(_PACKAGE)}:{line}" for line in _findings(tree)]
    assert offenders == [], f"bare branch names handed to git (use pyforge.doctor.refs): {offenders}"


def test_the_scan_catches_every_spelling_and_spares_the_rest() -> None:
    source = "\n".join(
        [
            '_MAIN = "main"',  # 1
            '_git(target, "log", "--format=%s", "main")',  # 2: route 3 before Story 31.1
            "_git(target, 'log', _MAIN)",  # 3: a constant bound to it
            'run_git(target, ["diff", "--name-only", "origin/main..HEAD"])',  # 4: a range
            '_git(target, "show", f"main:{rel}")',  # 5: rev:path
            'def gather(target, *, base="origin/main", head="HEAD"): ...',  # 6: a base default
            'def gather_direction(target, *, base_ref="main"): ...',  # 7
            '_git(target, "diff", f"{base}..origin/main")',  # 8: the right side of a range
            '_git(target, "log", MAIN)',  # 9: from pyforge.doctor.refs
            '_git(target, "log", "refs/heads/main")',  # 10
            'def gather(target, *, base=ORIGIN_MAIN, head="HEAD"): ...',  # 11
            'run_git(target, ["log", "-1", "--format=%cs", "--", rel])',  # 12
            'Finding(message="could not diff origin/main..HEAD")',  # 13: not a git call
            '_git(target, "show", f"{base_ref}:{rel}")',  # 14: a parameter, judged by its default
            'def pick(main="main"): ...',  # 15: not a base-like parameter
        ]
    )
    assert _findings(ast.parse(source)) == [2, 3, 4, 5, 6, 7, 8]
