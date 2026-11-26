"""Meta test -- scribe's exit codes are the ``scribe`` domain of the one exit-code declaration
(scribe Story 36.1, spec-pyforge-steward:CAP-184 as amended 2026-11-26).

``pyforge.core.exit_domains`` carries the declaration in process (pyforge-core's own live-tree test
holds it equal to ``docs/governance/guild-roster.json``), so this test reads no repository file.
Scribe has no verdict module and spells its own numbers; this test fails when one of them
differs from the declaration, and pins the numbers scribe always exited with.
"""

from __future__ import annotations

import ast
from pathlib import Path

from pyforge.core.exit_domains import domain_codes, exit_code

import pyforge.scribe


def _is_exit_call(func: ast.expr) -> bool:
    """``typer.Exit`` however it is imported, ``SystemExit`` and ``sys.exit``."""
    return ast.unparse(func) in ("typer.Exit", "Exit", "SystemExit", "sys.exit")


def _typer_exit_codes() -> set[int]:
    """Every literal code an exit call in the package carries; a bare ``typer.Exit()`` is 0."""
    codes: set[int] = set()
    package = Path(pyforge.scribe.__file__).parent
    for path in sorted(package.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not (isinstance(node, ast.Call) and _is_exit_call(node.func)):
                continue
            keyword = next((k.value for k in node.keywords if k.arg == "code"), None)
            value = keyword if keyword is not None else (node.args[0] if node.args else None)
            if value is None:
                codes.add(0)
            else:
                assert isinstance(value, ast.Constant) and type(value.value) is int, f"{path.name}:{node.lineno}"
                codes.add(value.value)
    return codes


def test_the_codes_scribe_exits_with_are_the_declared_domain() -> None:
    assert _typer_exit_codes() == domain_codes("scribe")


def test_the_numbers_are_the_ones_scribe_always_used() -> None:
    assert {member: exit_code("scribe", member) for member in ("ok", "drift", "could-not-run")} == {
        "ok": 0,
        "drift": 1,
        "could-not-run": 2,
    }
