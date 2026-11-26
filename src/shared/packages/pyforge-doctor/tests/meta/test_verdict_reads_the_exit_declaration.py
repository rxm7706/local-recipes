"""Meta test -- Doctor's exit codes are the ``doctor`` domain of the one exit-code declaration
(doctor Story 63.1, spec-pyforge-steward:CAP-184).

``pyforge.core.exit_domains`` carries the declaration in process (the governance file it mirrors,
``docs/governance/guild-roster.json``, is held equal to it by pyforge-core's own live-tree test), so
this test needs no repository read: it holds ``verdict.py``'s lattice, its SIGINT constant and its
narrowing of warden's domain to the declaration, and pins that ``exit_code_for`` returns the codes it
returned before the numbers moved there.
"""

from __future__ import annotations

from pyforge.core.exit_domains import EXIT_CODE_DOMAINS_NARROWING, domain_codes, exit_code

from pyforge.doctor import verdict
from pyforge.doctor.models import DoctorStatus


def test_the_lattice_and_the_sigint_constant_are_the_declared_doctor_domain() -> None:
    assert verdict.LATTICE.exit_codes | {verdict.EXIT_SIGINT} == domain_codes("doctor")


def test_each_status_exits_with_its_declared_code() -> None:
    for status in DoctorStatus:
        assert verdict.LATTICE.exit_by_member[status] == exit_code("doctor", status.value)


def test_the_numbers_are_the_ones_doctor_always_used() -> None:
    assert (verdict._EXIT_OK, verdict._EXIT_FAIL, verdict.EXIT_SIGINT) == (0, 2, 130)


def test_the_declaration_says_doctor_narrows_warden() -> None:
    assert EXIT_CODE_DOMAINS_NARROWING["doctor"] == "warden"
    assert domain_codes("doctor") <= domain_codes("warden")
