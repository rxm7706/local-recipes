"""Story 60.1 (CAP-270): no marshal module hands git a short remote ref.

Git resolves ``origin/main`` to a local branch or tag of that name before the remote-tracking
ref, so every git-facing read names ``refs/remotes/<remote>/<branch>`` through
``pyforge.marshal.core.refs``. This scan fails on any expression that builds a short remote ref
-- a string, f-string, concatenation, ``%`` format or ``"/".join`` whose text (placeholders
aside) has no whitespace and starts with ``origin/`` (or ``<rev>..origin/``), or an f-string
``{remote}/{...}`` -- anywhere in the package except ``core/refs.py``. Text with whitespace is a
message a person reads, not a ref, and is not flagged. Review 1 found two live spellings the
first matcher missed (``f"origin/loop/{slug}"``, ``f"{remote}/{ref}"``); both are pinned below.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pyforge.marshal

_PACKAGE = Path(pyforge.marshal.__file__).parent
_REF_START = re.compile(r"^(?:\S*\.\.\.?)?origin/")


def _has_space(text: str) -> bool:
    return any(ch.isspace() for ch in text)


def _is_short_ref_text(text: str) -> bool:
    return not _has_space(text) and bool(_REF_START.match(text))


def _name(expr: ast.expr) -> str:
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        return expr.attr
    return ""


def _remoteish(expr: ast.expr) -> bool:
    name = _name(expr)
    return "remote" in name.lower() or name in {"ORIGIN", "origin"}


def _names_origin(expr: ast.expr) -> bool:
    if isinstance(expr, ast.Constant):
        return expr.value == "origin"
    if isinstance(expr, (ast.Tuple, ast.List)):
        return any(_names_origin(element) for element in expr.elts)
    return _remoteish(expr)


def _template(node: ast.JoinedStr) -> str:
    return "".join(v.value if isinstance(v, ast.Constant) else "{}" for v in node.values)


def _short_refs(tree: ast.AST) -> list[int]:
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and _is_short_ref_text(node.value):
            lines.add(node.lineno)
        elif isinstance(node, ast.JoinedStr):
            tpl = _template(node)
            first = node.values[0] if node.values else None
            if _is_short_ref_text(tpl) or (
                not _has_space(tpl)
                and tpl.startswith("{}/")
                and isinstance(first, ast.FormattedValue)
                and _remoteish(first.value)
            ):
                lines.add(node.lineno)
        elif isinstance(node, ast.BinOp) and isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
            left = node.left.value
            if isinstance(node.op, ast.Add) and _is_short_ref_text(left):
                lines.add(node.lineno)
            elif isinstance(node.op, ast.Mod) and not _has_space(left) and "/" in left and _names_origin(node.right):
                lines.add(node.lineno)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "join"
            and isinstance(node.func.value, ast.Constant)
            and node.func.value.value == "/"
            and node.args
            and _names_origin(node.args[0])
        ):
            lines.add(node.lineno)
    return sorted(lines)


def test_no_module_outside_core_refs_spells_a_short_remote_ref() -> None:
    offenders = []
    for path in sorted(_PACKAGE.rglob("*.py")):
        if path == _PACKAGE / "core" / "refs.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        offenders += [f"{path.relative_to(_PACKAGE)}:{line}" for line in _short_refs(tree)]
    assert offenders == [], f"short remote refs (use pyforge.marshal.core.refs): {offenders}"


def test_the_scan_catches_every_spelling_and_spares_messages() -> None:
    source = "\n".join(
        [
            'a = "origin/main"',  # 1
            'b = f"origin/{base}"',  # 2
            'c = f"origin/loop/{slug}"',  # 3 (live in cli/watch.py before review 1)
            'd = f"{remote}/{ref}"',  # 4 (live in adapters/vcs_git.py before review 1)
            'e = "origin/" + base',  # 5
            'f = "%s/%s" % ("origin", base)',  # 6
            'g = "/".join(("origin", base))',  # 7
            'h = f"{ORIGIN}/{base}"',  # 8
            'i = f"HEAD..origin/{base}"',  # 9
            'j = f"origin/{base}...HEAD"',  # 10
            "k = f\"could not reach 'origin/{base}'\"",  # 11: a message
            'm = "refs/remotes/origin/main"',  # 12: the full ref
            'n = f"refs/remotes/{remote}/{base}"',  # 13: the full ref
            'o = f"cannot resolve {remote}/{ref} after fetch"',  # 14: a message
        ]
    )
    assert _short_refs(ast.parse(source)) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
