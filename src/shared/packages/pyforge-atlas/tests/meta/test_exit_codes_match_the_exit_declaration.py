"""Meta test -- atlas's exit codes are the ``atlas`` domain of the one exit-code declaration
(atlas Story 54.1, spec-pyforge-steward:CAP-184 as amended 2026-11-26).

``pyforge.core.exit_domains`` carries the declaration in process (pyforge-core's own live-tree test
holds it equal to ``docs/governance/guild-roster.json``), so this test reads no repository file.
Atlas has no verdict module and spells its own numbers; this test fails when one of them
differs from the declaration, and pins the numbers atlas always exited with.
"""

from __future__ import annotations

import ast
from pathlib import Path

from pyforge.core.exit_domains import domain_codes, exit_code

from pyforge.atlas import __main__ as entry


def test_the_usage_constant_is_the_declared_usage_code() -> None:
    assert entry.EXIT_USAGE == exit_code("atlas", "usage") == 2


def test_the_declared_domain_is_the_frozen_atlas_domain() -> None:
    assert domain_codes("atlas") == frozenset({0, 1, 2, 130})


def test_the_numbers_are_the_ones_atlas_always_used() -> None:
    assert {member: exit_code("atlas", member) for member in ("ok", "failed", "usage", "interrupted")} == {
        "ok": 0,
        "failed": 1,
        "usage": 2,
        "interrupted": 130,
    }


def _literal_int_returns(module_file: str) -> set[int]:
    """Every integer literal a function in the module returns: the codes its entry point spells in place."""
    tree = ast.parse(Path(module_file).read_text(encoding="utf-8"))
    return {
        node.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and type(node.value.value) is int
    }


def _literal_exit_calls(module_file: str) -> set[int]:
    """Every integer literal handed to ``SystemExit`` or ``sys.exit`` in the module."""
    tree = ast.parse(Path(module_file).read_text(encoding="utf-8"))
    return {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and ast.unparse(node.func) in ("SystemExit", "sys.exit")
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and type(node.args[0].value) is int
    }


def test_no_literal_code_in_the_entry_point_falls_outside_the_declared_domain() -> None:
    """``pyforge atlas`` hands its exit to Click; a number its own module spells in place must be a declared one."""
    spelled = _literal_int_returns(entry.__file__) | _literal_exit_calls(entry.__file__)
    assert spelled <= domain_codes("atlas")
