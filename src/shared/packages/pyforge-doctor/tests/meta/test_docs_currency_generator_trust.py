"""Story 40.2 conformance: ``docs_currency`` never subprocesses a file under ``target``.

DW-doctor-40-1-2 (high, unverified) named the pre-fix site at
``sources/docs_currency.py`` running ``target / <generator> --check``. This
meta test pins the trust model: every :func:`cli_bridge.run_check_script`
call in ``docs_currency.py`` passes a checkout-resolved script path and
includes ``--root`` so the judged tree is data only.
"""

from __future__ import annotations

import ast
from pathlib import Path

DOCS_CURRENCY_SOURCE = (
    Path(__file__).resolve().parents[2] / "src" / "pyforge" / "doctor" / "sources" / "docs_currency.py"
)


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _run_check_script_calls(tree: ast.Module) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "run_check_script":
            calls.append(node)
        elif (
            isinstance(func, ast.Attribute)
            and func.attr == "run_check_script"
            and isinstance(func.value, ast.Name)
            and func.value.id == "run_check_script"
        ):
            calls.append(node)
    return calls


def _expr_uses_target(expr: ast.expr) -> bool:
    for sub in ast.walk(expr):
        if isinstance(sub, ast.Name) and sub.id == "target":
            return True
        if isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.Div):
            left, right = sub.left, sub.right
            if isinstance(left, ast.Name) and left.id == "target":
                return True
            if isinstance(right, ast.Name) and right.id == "target":
                return True
    return False


def test_docs_currency_run_check_script_never_targets_judged_tree_script() -> None:
    tree = _parse(DOCS_CURRENCY_SOURCE)
    calls = _run_check_script_calls(tree)
    assert calls, "expected at least one run_check_script call in docs_currency.py"

    for call in calls:
        script_arg = call.args[0]
        assert not _expr_uses_target(script_arg), (
            f"run_check_script must not receive a path under target (line {script_arg.lineno})"
        )
        string_args: list[str] = []
        for arg in call.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                string_args.append(arg.value)
            elif isinstance(arg, ast.List):
                for elt in arg.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        string_args.append(elt.value)
        assert "--root" in string_args, (
            f"run_check_script call at line {call.lineno} must pass --root for the judged tree"
        )
