"""Meta test -- herald's exit codes are the ``herald`` domain of the one exit-code declaration
(herald Story 56.1, spec-pyforge-steward:CAP-184 as amended 2026-11-26).

``pyforge.core.exit_domains`` carries the declaration in process (pyforge-core's own live-tree test
holds it equal to ``docs/governance/guild-roster.json``), so this test reads no repository file.
Herald has no verdict module and spells its own numbers; this test fails when one of them
differs from the declaration, and pins the numbers herald always exited with.
"""

from __future__ import annotations

import ast
from pathlib import Path

from pyforge.core.exit_domains import domain_codes, exit_code

from pyforge.herald import cli, errors


def test_each_mapped_error_exits_with_its_declared_code() -> None:
    assert errors.exit_code_for(errors.DeckUsageError("probe")) == exit_code("herald", "usage")
    for conflict in (errors.SeedConflictError, errors.PullConflictError, errors.ExportConflictError):
        assert errors.exit_code_for(conflict("probe")) == exit_code("herald", "conflict"), conflict.__name__
    assert errors.exit_code_for(errors.TransportError("probe")) == exit_code("herald", "transport")


def test_an_unmapped_error_exits_with_the_declared_failed_code() -> None:
    assert errors.exit_code_for(errors.HeraldError("probe")) == exit_code("herald", "failed")


def test_the_error_map_stays_inside_the_declared_domain() -> None:
    mapped = {code for _, code in errors._EXIT_BY_ERROR}  # noqa: SLF001 -- the map is the surface under test
    assert mapped | {exit_code("herald", "failed")} <= domain_codes("herald")
    assert mapped == {exit_code("herald", member) for member in ("usage", "conflict", "transport")}


def test_the_numbers_are_the_ones_herald_always_used() -> None:
    assert {member: exit_code("herald", member) for member in ("ok", "failed", "usage", "conflict", "transport")} == {
        "ok": 0,
        "failed": 1,
        "usage": 2,
        "conflict": 3,
        "transport": 4,
    }
    assert exit_code("herald", "interrupted") == 130


def _literal_int_returns(module_file: str) -> set[int]:
    """Every integer literal a function in the module returns: the codes its entry point spells in place."""
    tree = ast.parse(Path(module_file).read_text(encoding="utf-8"))
    return {
        node.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and type(node.value.value) is int
    }


def test_every_literal_code_the_cli_returns_is_inside_the_declared_domain() -> None:
    """``cli.py`` spells its usage, flag-off, failure and interrupt codes in place; each must be a declared one."""
    returned = _literal_int_returns(cli.__file__)
    assert {exit_code("herald", "ok"), exit_code("herald", "usage"), exit_code("herald", "interrupted")} <= returned
    assert returned <= domain_codes("herald")
