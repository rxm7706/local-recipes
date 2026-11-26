"""Meta test -- marshal's exit codes are the ``marshal`` and ``marshal-seed`` domains of the one
exit-code declaration (marshal Story 122.1, spec-pyforge-steward:CAP-184).

``pyforge.core.exit_domains`` carries the declaration in process (pyforge-core's own live-tree test
holds it equal to ``docs/governance/guild-roster.json``), so this test reads no repository file: it
holds AD-7's frozen ``GUARDED_EXIT_CODES``, each rung's projection, the boundary constants and the
seed verb's six leaves to the declaration, and pins the numbers marshal always exited with.
"""

from __future__ import annotations

import pytest
from pyforge.core.exit_domains import domain_codes, exit_code

from pyforge.marshal.core import verdict
from pyforge.marshal.core.model import Verdict
from pyforge.marshal.seed import errors


def test_guarded_exit_codes_are_the_declared_marshal_domain() -> None:
    assert verdict.GUARDED_EXIT_CODES == domain_codes("marshal")


@pytest.mark.parametrize("member", list(Verdict))
def test_each_rung_exits_with_its_declared_code(member: Verdict) -> None:
    assert verdict._EXIT_BY_VERDICT[member] == exit_code("marshal", member.value)


def test_the_numbers_are_the_ones_marshal_always_used() -> None:
    assert {member.value: code for member, code in verdict._EXIT_BY_VERDICT.items()} == {
        "clean": 0,
        "warn": 0,
        "unevaluable": 1,
        "scope-violation": 2,
        "gate-failed": 3,
        "error": 4,
    }
    assert (verdict.EXIT_OK, verdict.EXIT_USAGE, verdict.EXIT_SIGINT) == (0, 2, 130)


def test_seed_exit_codes_are_the_declared_marshal_seed_domain() -> None:
    assert errors.SEED_EXIT_CODES == domain_codes("marshal-seed")
    assert {leaf.__name__: leaf.exit_code for leaf in errors.SeedError.__subclasses__()} == {
        "ConformanceFailure": 1,
        "UsageError": 2,
        "PreconditionFailure": 3,
        "NeverWriteViolation": 4,
        "StateInvalid": 5,
        "InternalError": 10,
    }
