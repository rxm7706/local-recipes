"""Meta test -- steward's exit codes are the ``steward`` domain of the one exit-code declaration
(steward Story 142.1, spec-pyforge-steward:CAP-184 as amended 2026-11-26).

``pyforge.core.exit_domains`` carries the declaration in process (pyforge-core's own live-tree test
holds it equal to ``docs/governance/guild-roster.json``), so this test reads no repository file.
Steward has no verdict module and spells its own numbers; this test fails when one of them
differs from the declaration, and pins the numbers steward always exited with.
"""

from __future__ import annotations

import ast
from pathlib import Path

from pyforge.core.exit_domains import domain_codes, exit_code

import pyforge.steward
from pyforge.steward import cli

MEMBERS = {
    "EXIT_OK": "ok",
    "EXIT_FAILED": "failed",
    "EXIT_USAGE": "usage",
    "EXIT_BUDGET_NOT_CONFIGURED": "refusal",
    "EXIT_INTERNAL": "internal-error",
    "EXIT_INTERRUPTED": "interrupted",
}


def test_the_dispatcher_constants_are_the_declared_members() -> None:
    for name, member in MEMBERS.items():
        assert getattr(cli, name) == exit_code("steward", member), name


def test_the_documented_exits_are_the_declared_domain() -> None:
    assert cli._DOCUMENTED_EXITS == domain_codes("steward")  # noqa: SLF001 -- the set main() projects through


def _module_level_exit_constants() -> dict[str, int]:
    found: dict[str, int] = {}
    package = Path(pyforge.steward.__file__).parent
    for path in sorted(package.rglob("*.py")):
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            pairs: list[tuple[ast.expr, ast.expr]] = []
            if isinstance(node, ast.AnnAssign) and node.value is not None:
                pairs.append((node.target, node.value))
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple):
                        pairs += list(zip(target.elts, node.value.elts, strict=True))  # EXIT_A, EXIT_B = 0, 1
                    else:
                        pairs.append((target, node.value))
            for target, value in pairs:
                if isinstance(target, ast.Name) and target.id.startswith("EXIT_"):
                    assert isinstance(value, ast.Constant) and type(value.value) is int, f"{path.name}:{target.id}"
                    found[f"{path.relative_to(package)}:{target.id}"] = value.value
    return found


def test_every_exit_constant_in_the_package_is_inside_the_declared_domain() -> None:
    """Covers the duty modules' refusal codes and the constants of the scripts the package also ships
    (``preflight.py``, ``frames.py``): none may spell a number steward's own domain does not hold."""
    constants = _module_level_exit_constants()
    assert len(constants) > len(MEMBERS)  # the duty modules define their own refusal codes
    assert "frames.py:EXIT_COULD_NOT_RUN" in constants  # a tuple assignment is read too
    outside = {name: code for name, code in constants.items() if code not in domain_codes("steward")}
    assert outside == {}


def test_the_numbers_are_the_ones_steward_always_used() -> None:
    assert {name: getattr(cli, name) for name in MEMBERS} == {
        "EXIT_OK": 0,
        "EXIT_FAILED": 1,
        "EXIT_USAGE": 2,
        "EXIT_BUDGET_NOT_CONFIGURED": 3,
        "EXIT_INTERNAL": 70,
        "EXIT_INTERRUPTED": 130,
    }
