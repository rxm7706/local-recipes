"""Story 60.1 (CAP-270): no marshal module hands git a short remote ref.

Git resolves ``origin/main`` to a local branch or tag of that name before the remote-tracking
ref, so every git-facing read names ``refs/remotes/<remote>/<branch>`` through
``pyforge.marshal.core.refs``. This scan renders every string-building expression -- a literal,
an f-string, a ``+`` chain, a ``%`` format, ``str.format``, ``sep.join`` or ``os.path.join`` --
into one template (literal text, ``{R}`` for anything holding the remote, ``{}`` otherwise) and
fails on a template with no whitespace that starts ``origin/``, ``{R}/`` or ``<rev>..`` either,
anywhere in the package except ``core/refs.py``. Text with whitespace is a message a person
reads, not a ref. Reviews 1 and 2 found spellings the earlier matchers missed; every one is
pinned in the self-test below.
"""

from __future__ import annotations

import ast
import re
import string
from pathlib import Path

import pyforge.marshal

_PACKAGE = Path(pyforge.marshal.__file__).parent
_REF_START = re.compile(r"^(?:\S*\.\.\.?)?(?:origin|\{R\})/")
_PERCENT_FIELD = re.compile(r"%(?:\((\w+)\))?[sdr]")


def _origin_names(tree: ast.AST) -> set[str]:
    """Names that hold the remote: ``ORIGIN``, ``origin``, anything named ``*remote*``, and any
    name the module assigns the literal ``"origin"``."""
    names = {"ORIGIN", "origin"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(node.value, ast.Constant):
            if node.value.value == "origin":
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names |= {t.id for t in targets if isinstance(t, ast.Name)}
    return names


def _piece(expr: ast.expr, origin_names: set[str]) -> str:
    """The text one part contributes to a template."""
    if isinstance(expr, ast.FormattedValue):
        expr = expr.value
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value
    name = expr.id if isinstance(expr, ast.Name) else expr.attr if isinstance(expr, ast.Attribute) else ""
    if name and ("remote" in name.lower() or name in origin_names):
        return "{R}"
    return "{}"


def _flatten_add(node: ast.expr) -> list[ast.expr]:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _flatten_add(node.left) + _flatten_add(node.right)
    return [node]


def _format_template(fmt: str, args: list[ast.expr], kwargs: dict[str, ast.expr], names: set[str]) -> str:
    out, position = [], 0
    for literal, field, _spec, _conv in string.Formatter().parse(fmt):
        out.append(literal)
        if field is None:
            continue
        if field == "" or field.isdigit():
            index = position if field == "" else int(field)
            position += 1
            out.append(_piece(args[index], names) if index < len(args) else "{}")
        else:
            out.append(_piece(kwargs[field], names) if field in kwargs else "{}")
    return "".join(out)


def _percent_template(fmt: str, right: ast.expr, names: set[str]) -> str:
    values: list[ast.expr] = list(right.elts) if isinstance(right, (ast.Tuple, ast.List)) else [right]
    by_key = {}
    if isinstance(right, ast.Dict):
        by_key = {k.value: v for k, v in zip(right.keys, right.values) if isinstance(k, ast.Constant)}
    position = 0

    def fill(match: re.Match[str]) -> str:
        nonlocal position
        key = match.group(1)
        if key is not None:
            return _piece(by_key[key], names) if key in by_key else "{}"
        value = values[position] if position < len(values) else None
        position += 1
        return _piece(value, names) if value is not None else "{}"

    return _PERCENT_FIELD.sub(fill, fmt)


def _templates(tree: ast.AST) -> list[tuple[int, str]]:
    names = _origin_names(tree)
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.append((node.lineno, node.value))
        elif isinstance(node, ast.JoinedStr):
            found.append((node.lineno, "".join(_piece(v, names) for v in node.values)))
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            found.append((node.lineno, "".join(_piece(part, names) for part in _flatten_add(node))))
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod) and isinstance(node.left, ast.Constant):
            if isinstance(node.left.value, str):
                found.append((node.lineno, _percent_template(node.left.value, node.right, names)))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            func, receiver = node.func.attr, node.func.value
            if func == "format" and isinstance(receiver, ast.Constant) and isinstance(receiver.value, str):
                kwargs = {kw.arg: kw.value for kw in node.keywords if kw.arg}
                found.append((node.lineno, _format_template(receiver.value, list(node.args), kwargs, names)))
            elif func == "join" and isinstance(receiver, ast.Constant) and isinstance(receiver.value, str):
                if node.args and isinstance(node.args[0], (ast.List, ast.Tuple)):
                    found.append((node.lineno, receiver.value.join(_piece(e, names) for e in node.args[0].elts)))
            elif (
                func == "join" and _piece(receiver, set()) == "{}" and ast.unparse(receiver) in {"os.path", "posixpath"}
            ):
                found.append((node.lineno, "/".join(_piece(arg, names) for arg in node.args)))
    return found


def _short_refs(tree: ast.AST) -> list[int]:
    return sorted(
        {line for line, text in _templates(tree) if not any(ch.isspace() for ch in text) and _REF_START.match(text)}
    )


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
            'k = remote + "/" + base',  # 11 (review 2)
            'l = "origin" + "/" + base',  # 12 (review 2)
            'm = "%(r)s/%(b)s" % {"r": "origin", "b": base}',  # 13 (review 2)
            'n = "".join(["origin", "/", base])',  # 14 (review 2)
            'o = "{}/{}".format("origin", base)',  # 15 (review 2)
            'p = os.path.join("origin", base)',  # 16 (review 2)
            'r = "origin"',  # 17: the remote's name alone is not a ref
            's = f"{r}/{base}"',  # 18 (review 2: a variable holding "origin")
            "t = f\"could not reach 'origin/{base}'\"",  # 19: a message
            'u = "refs/remotes/origin/main"',  # 20: the full ref
            'v = f"refs/remotes/{remote}/{base}"',  # 21: the full ref
            'w = f"cannot resolve {remote}/{ref} after fetch"',  # 22: a message
            'x = f"{sha}:refs/heads/{remote_branch}"',  # 23: a push refspec
        ]
    )
    assert _short_refs(ast.parse(source)) == [*range(1, 17), 18]
