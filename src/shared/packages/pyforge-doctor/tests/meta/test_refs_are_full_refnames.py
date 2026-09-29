"""Story 31.1 (spec-pyforge-doctor CAP-85): no Doctor module hands git a bare branch name.

Git resolves a short name through ``refs/<n>``, ``refs/tags/<n>``, ``refs/heads/<n>``, then
``refs/remotes/<n>``, so ``main`` can be a tag's commit and ``origin/main`` a local branch's. Every
Doctor source reaches git through ``_git`` / ``_git_ok`` / ``run_git``; this scan renders each git
argument -- positional, ``args=``, a list or tuple literal, a starred or named argv list -- into
templates, the way marshal Story 61.1's meta test renders refs: literal text; a name through what
is bound to it in the module or an enclosing function (a literal, a parameter default, a constant
imported from another Doctor module, a tuple-unpacking, loop, comprehension or walrus target, or
any other assigned expression, up to three assignments deep); f-strings, ``+``, ``%``, ``str.format``, ``join``, ``or``/``and`` and conditionals rendered
through; anything else an opaque value. A template is flagged when a ``..``/``...``/``:`` side,
stripped of a leading ``^`` and a ``^``/``~``/``@{`` suffix, is ``main`` or ``origin/...``. The same judgement applies
to a base-like keyword at any call (``base=``, ``base_ref=``, ...), to a positional argument that
lands on a same-module function's base-like parameter, and to a base-like parameter's default
(lambdas too), since every caller runs the sources on their defaults. Text with whitespace is a message
people read, not a ref. ``pyforge.doctor.refs`` is exempt. Not scanned: method aliases,
``functools.partial``, ``**kwargs``, attributes (``self.REF``), ``format`` on a named string,
``join`` over a named list, and a positional ref passed to a function defined in another module.
"""

from __future__ import annotations

import ast
import itertools
import re
import string
from dataclasses import dataclass
from pathlib import Path

import pyforge.doctor

_PACKAGE = Path(pyforge.doctor.__file__).parent
_GIT_CALLS = {"_git", "run_git", "_git_ok"}
_BASE_PARAMS = {"base", "base_ref", "base_branch", "head", "ref", "rev", "branch", "since", "target_ref"}
_BARE = re.compile(r"^(?:main|origin/\S*)$")
_SIDES = re.compile(r"\.\.\.?|:")
_SUFFIX = re.compile(r"(?:\^|~|@\{).*$")
_VALUE = "\x00"  # an opaque value
_PERCENT_FIELD = re.compile(r"%(?:\((\w+)\))?[sdr]")
_MAX_ALTERNATIVES = 16
_MAX_DEPTH = 3
_FUNCTION = (ast.FunctionDef, ast.AsyncFunctionDef)


@dataclass(frozen=True)
class _Scope:
    strings: dict[str, set[str]]
    exprs: dict[str, list[ast.expr]]
    depth: int = 0

    def deeper(self) -> _Scope:
        return _Scope(self.strings, self.exprs, self.depth + 1)


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
    merged: dict[str, set[str]] = {}
    for path in _PACKAGE.rglob("*.py"):
        if path == _PACKAGE / "refs.py":
            continue
        for name, values in _module_constants(ast.parse(path.read_text(encoding="utf-8"))).items():
            merged.setdefault(name, set()).update(values)
    return merged


def _owners(tree: ast.Module) -> dict[ast.AST, ast.AST]:
    owner: dict[ast.AST, ast.AST] = {}

    def visit(node: ast.AST, current: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            owner[child] = current
            visit(child, child if isinstance(child, _FUNCTION) else current)

    visit(tree, tree)
    return owner


def _defaults(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda) -> list[tuple[ast.arg, ast.expr]]:
    positional = [*node.args.posonlyargs, *node.args.args]
    pairs = [*zip(positional[len(positional) - len(node.args.defaults) :], node.args.defaults)]
    return pairs + [(a, d) for a, d in zip(node.args.kwonlyargs, node.args.kw_defaults) if d is not None]


def _bind(home: _Scope, target: ast.expr, value: ast.expr) -> None:
    """Bind ``target`` (a name, or a tuple/list unpacked pairwise) to ``value``."""
    if isinstance(target, (ast.Tuple, ast.List)):
        if isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) == len(target.elts):
            for sub_target, sub_value in zip(target.elts, value.elts):
                _bind(home, sub_target, sub_value)
        return
    if not isinstance(target, ast.Name):
        return
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        home.strings.setdefault(target.id, set()).add(value.value)
    else:
        home.exprs.setdefault(target.id, []).append(value)


def _scopes(tree: ast.Module, package: dict[str, set[str]]) -> dict[ast.AST, _Scope]:
    owner = _owners(tree)
    scopes: dict[ast.AST, _Scope] = {}

    def scope(node: ast.AST) -> _Scope:
        return scopes.setdefault(node, _Scope({}, {}))

    for node in ast.walk(tree):
        own = (
            node.level > 0 or (node.module or "").startswith("pyforge.doctor")
            if isinstance(node, ast.ImportFrom)
            else False
        )
        if isinstance(node, ast.ImportFrom) and own:
            for alias in node.names:
                if alias.name in package:
                    scope(tree).strings.setdefault(alias.asname or alias.name, set()).update(package[alias.name])
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                _bind(scope(owner.get(node, tree)), target, node.value)
        elif isinstance(node, ast.NamedExpr):
            _bind(scope(owner.get(node, tree)), node.target, node.value)
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
            if isinstance(node.iter, (ast.List, ast.Tuple, ast.Set)):
                for element in node.iter.elts:
                    _bind(scope(owner.get(node, tree)), node.target, element)
        elif isinstance(node, _FUNCTION):
            for arg, default in _defaults(node):
                if isinstance(default, ast.Constant) and isinstance(default.value, str):
                    scope(node).strings.setdefault(arg.arg, set()).add(default.value)
    return scopes


def _scope_at(node: ast.AST, tree: ast.Module, owner: dict[ast.AST, ast.AST], scopes: dict[ast.AST, _Scope]) -> _Scope:
    chain: list[ast.AST] = []
    current = owner.get(node, tree)
    while current is not tree:
        chain.append(current)
        current = owner.get(current, tree)
    merged = _Scope({}, {})
    for holder in [tree, *reversed(chain)]:
        found = scopes.get(holder)
        if found is not None:
            for name, values in found.strings.items():
                merged.strings.setdefault(name, set()).update(values)
            for name, exprs in found.exprs.items():
                merged.exprs.setdefault(name, []).extend(exprs)
    return merged


def _product(parts: list[list[str]]) -> list[str]:
    return ["".join(combo) for combo in itertools.islice(itertools.product(*parts), _MAX_ALTERNATIVES)]


def _render(expr: ast.expr | None, bound: _Scope) -> list[str]:
    """Every template ``expr`` can produce."""
    if expr is None:
        return [_VALUE]
    if isinstance(expr, ast.FormattedValue):
        return _render(expr.value, bound)
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return [expr.value]
    if isinstance(expr, ast.IfExp):
        return (_render(expr.body, bound) + _render(expr.orelse, bound))[:_MAX_ALTERNATIVES]
    if isinstance(expr, ast.BoolOp):
        return [t for value in expr.values for t in _render(value, bound)][:_MAX_ALTERNATIVES]
    if isinstance(expr, ast.Name) and (expr.id in bound.strings or expr.id in bound.exprs):
        alternatives = sorted(bound.strings.get(expr.id, ()))
        if bound.depth < _MAX_DEPTH:
            for value in bound.exprs.get(expr.id, ()):
                alternatives += _render(value, bound.deeper())
        else:
            alternatives.append(_VALUE)
        return alternatives[:_MAX_ALTERNATIVES] or [_VALUE]
    if isinstance(expr, ast.JoinedStr):
        return _product([_render(v, bound) for v in expr.values])
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
        return _product([_render(expr.left, bound), _render(expr.right, bound)])
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Mod) and isinstance(expr.left, ast.Constant):
        fmt = str(expr.left.value)
        values = list(expr.right.elts) if isinstance(expr.right, (ast.Tuple, ast.List)) else [expr.right]
        by_key: dict[object, ast.expr] = {}
        if isinstance(expr.right, ast.Dict):
            by_key = {k.value: v for k, v in zip(expr.right.keys, expr.right.values) if isinstance(k, ast.Constant)}
        pieces: list[list[str]] = []
        position, last = 0, 0
        for match in _PERCENT_FIELD.finditer(fmt):
            pieces.append([fmt[last : match.start()]])
            if match.group(1) is not None:
                pieces.append(_render(by_key.get(match.group(1)), bound))
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


def _bare(template: str) -> bool:
    if any(ch.isspace() for ch in template):
        return False
    return any(_BARE.match(_SUFFIX.sub("", side.lstrip("^"))) for side in _SIDES.split(template))


def _argv(expr: ast.expr, bound: _Scope, depth: int = 0) -> list[ast.expr]:
    """The elements a git argument stands for: a list/tuple literal's, a starred or named list's."""
    if isinstance(expr, ast.Starred):
        return _argv(expr.value, bound, depth)
    if isinstance(expr, (ast.List, ast.Tuple)):
        return [e for element in expr.elts for e in _argv(element, bound, depth)]
    if isinstance(expr, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
        return [expr.elt]  # its generators' targets are bound in the enclosing scope
    if isinstance(expr, ast.Name) and depth < _MAX_DEPTH and expr.id in bound.exprs:
        lists = [v for v in bound.exprs[expr.id] if isinstance(v, (ast.List, ast.Tuple))]
        if lists:
            return [e for value in lists for e in _argv(value, bound, depth + 1)]
    return [expr]


def _findings(tree: ast.Module, package: dict[str, set[str]] | None = None) -> list[int]:
    owner = _owners(tree)
    scopes = _scopes(tree, package or {})
    positional_bases = {
        node.name: [i for i, a in enumerate([*node.args.posonlyargs, *node.args.args]) if a.arg in _BASE_PARAMS]
        for node in ast.walk(tree)
        if isinstance(node, _FUNCTION)
    }
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            bound = _scope_at(node, tree, owner, scopes)
            func = node.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
            candidates: list[ast.expr] = []
            if name in _GIT_CALLS:
                for arg in [*node.args[1:], *(kw.value for kw in node.keywords if kw.arg == "args")]:
                    candidates += _argv(arg, bound)
            candidates += [kw.value for kw in node.keywords if kw.arg in _BASE_PARAMS]
            candidates += [node.args[i] for i in positional_bases.get(name, ()) if i < len(node.args)]
            if any(_bare(t) for arg in candidates for t in _render(arg, bound)):
                lines.add(node.lineno)
        elif isinstance(node, (*_FUNCTION, ast.Lambda)):
            bound = _scope_at(node, tree, owner, scopes)
            for arg, default in _defaults(node):
                if arg.arg in _BASE_PARAMS and any(_bare(t) for t in _render(default, bound)):
                    lines.add(node.lineno)
    return sorted(lines)


def test_no_doctor_module_hands_git_a_bare_branch_name() -> None:
    package = _package_constants()
    offenders = []
    for path in sorted(_PACKAGE.rglob("*.py")):
        if path == _PACKAGE / "refs.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        offenders += [f"{path.relative_to(_PACKAGE)}:{line}" for line in _findings(tree, package)]
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
            'Finding(message="could not diff origin/main..HEAD")',  # 13: a message, not a ref
            '_git(target, "show", f"{base_ref}:{rel}")',  # 14: a parameter, judged by its default
            'def pick(main="main"): ...',  # 15: not a base-like parameter
        ]
    )
    assert _findings(ast.parse(source)) == [2, 3, 4, 5, 6, 7, 8]


def test_the_scan_catches_the_spellings_review_1_found() -> None:
    """Doctor Story 31.1 review 1: the first scan read literals, f-strings and module constants in
    positional git arguments only."""
    source = "\n".join(
        [
            "def a(target):",  # 1
            '    ref = "main"',  # 2
            '    _git(target, "log", ref)',  # 3: a function-local binding
            "def b(target, base):",  # 4
            '    _git(target, "log", base or "origin/main")',  # 5: `or`
            '    _git(target, "log", "main" if base else base)',  # 6: a conditional
            '    _git(target, "diff", "origin/" + "main" + "..HEAD")',  # 7: `+`
            '    _git(target, "diff", "%s..HEAD" % "main")',  # 8: `%`
            '    _git(target, "diff", "{}..HEAD".format("origin/main"))',  # 9: format
            '    _git(target, "log", "main^")',  # 10: a suffix
            '    run_git(target, args=["log", "main~1"])',  # 11: `args=`
            '    argv = ["log", "origin/main"]',  # 12
            "    run_git(target, argv)",  # 13: a named argv list
            '    _git(target, *("log", "main"))',  # 14: starred
            '    _changed_paths(target, base="origin/main")',  # 15: a call-site keyword
            '    ledger.gather(target, base_branch="main")',  # 16
            'def c(target, *, since="origin/main"): ...',  # 17: a wider base-like default
            "from .x import IMPORTED",  # 18
            '_git(target, "log", IMPORTED)',  # 19: an imported constant
            "def d(target):",  # 20
            '    ref = "HEAD"',  # 21: d's own binding
            '    _git(target, "log", ref)',  # 22: not a's `ref`
            'def e(target, ref="refs/heads/main"): _git(target, "log", ref)',  # 23
        ]
    )
    assert _findings(ast.parse(source), {"IMPORTED": {"main"}}) == [3, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 19]


def test_the_scan_catches_the_spellings_review_2_found() -> None:
    """Doctor Story 31.1 review 2."""
    source = "\n".join(
        [
            "def a(target):",  # 1
            '    _git(target, "log", "HEAD", "^main")',  # 2: a leading `^`
            '    run_git(target, ["rev-list", "HEAD", "^origin/main"])',  # 3
            '    base, head = "origin/main", "HEAD"',  # 4
            '    _git(target, "diff", f"{base}..{head}")',  # 5: tuple unpacking
            '    for ref in ("main",):',  # 6
            '        _git(target, "log", ref)',  # 7: a loop target
            '    _git(target, "log", *[r for r in ["origin/main"]])',  # 8: a comprehension target
            '    if (rev := "main"):',  # 9
            '        _git(target, "log", rev)',  # 10: walrus
            '    _git(target, "diff", "%(b)s..HEAD" % {"b": "origin/main"})',  # 11: `%` with a mapping
            'pick = lambda target, base="origin/main": base',  # 12: a lambda default
            "from pyforge.doctor.sources.x import ABS",  # 13
            '_git(target, "log", ABS)',  # 14: an absolute import
            "def _check(target, base, head): ...",  # 15
            '_check(target, "origin/main", "HEAD")',  # 16: positional onto a base-like parameter
            '_check(target, ORIGIN_MAIN, "HEAD")',  # 17: fine
            '_git(target, "log", "HEAD", "^refs/heads/main")',  # 18: fine
        ]
    )
    assert _findings(ast.parse(source), {"ABS": {"main"}}) == [2, 3, 5, 7, 8, 10, 11, 12, 14, 16]
