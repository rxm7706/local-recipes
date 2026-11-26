"""Meta test -- mason's exit codes are the ``mason`` domain of the one exit-code declaration
(mason Story 43.1, spec-pyforge-steward:CAP-184 as amended 2026-11-26).

``pyforge.core.exit_domains`` carries the declaration in process (pyforge-core's own live-tree test
holds it equal to ``docs/governance/guild-roster.json``), so this test reads no repository file.
Mason has no verdict module and spells its own numbers; this test fails when one of them
differs from the declaration, and pins the numbers mason always exited with.
"""

from __future__ import annotations

import ast
from pathlib import Path

from pyforge.core.exit_domains import domain_codes, exit_code

from pyforge.mason import cli, exit_codes

MEMBERS = {
    "EXIT_OK": "ok",
    "EXIT_FAILED": "failed",
    "EXIT_USAGE": "usage",
    "EXIT_CFE_UNAVAILABLE": "cfe-unavailable",
    "EXIT_INTERRUPTED": "interrupted",
}


def _constants() -> dict[str, int]:
    return {name: value for name, value in vars(exit_codes).items() if name.startswith("EXIT_")}


def test_every_exit_constant_is_a_declared_member_with_its_code() -> None:
    constants = _constants()
    assert set(constants) == set(MEMBERS)
    for name, member in MEMBERS.items():
        assert constants[name] == exit_code("mason", member), name


def test_the_constants_cover_the_declared_domain() -> None:
    assert set(_constants().values()) == domain_codes("mason")


def test_the_numbers_are_the_ones_mason_always_used() -> None:
    assert _constants() == {
        "EXIT_OK": 0,
        "EXIT_FAILED": 1,
        "EXIT_USAGE": 2,
        "EXIT_CFE_UNAVAILABLE": 3,
        "EXIT_INTERRUPTED": 130,
    }


def _literal_int_returns(module_file: str) -> set[int]:
    """Every integer literal a function in the module returns: the codes its entry point spells in place."""
    tree = ast.parse(Path(module_file).read_text(encoding="utf-8"))
    return {
        node.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and type(node.value.value) is int
    }


def test_no_literal_code_in_the_cli_falls_outside_the_declared_domain() -> None:
    """``cli.main`` returns the ``EXIT_*`` names; a number spelled in place must still be a declared one."""
    assert _literal_int_returns(cli.__file__) <= domain_codes("mason")
