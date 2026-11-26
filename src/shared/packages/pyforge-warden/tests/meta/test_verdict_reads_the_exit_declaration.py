"""Meta test -- warden's exit codes are the ``warden`` domain of the one exit-code declaration
(warden Story 30.1, spec-pyforge-steward:CAP-184).

``pyforge.core.exit_domains`` carries the declaration in process (pyforge-core's own live-tree test
holds it equal to ``docs/governance/guild-roster.json``), so this test reads no repository file: it
holds ``verdict.py``'s rung table, its lattice, its SIGINT, warn-as-error and allow-empty codes to the
declaration, and pins the numbers warden always exited with.
"""

from __future__ import annotations

import pytest
from pyforge.core.exit_domains import domain_codes, exit_code

from pyforge.warden import verdict
from pyforge.warden.models import EMPTY_EXTRACTION_DRIVER_ID, Status, StatusDriver


def test_the_lattice_and_the_sigint_constant_are_the_declared_warden_domain() -> None:
    assert verdict.LATTICE.exit_codes | {verdict.EXIT_SIGINT} == domain_codes("warden")


@pytest.mark.parametrize("status", list(Status))
def test_each_rung_exits_with_its_declared_code(status: Status) -> None:
    assert verdict.exit_code_for(status) == exit_code("warden", status.value)


def test_the_numbers_are_the_ones_warden_always_used() -> None:
    assert {status.value: verdict.exit_code_for(status) for status in Status} == {
        "error": 2,
        "policy-violation": 1,
        "indeterminate": 1,
        "warn": 0,
        "bypassed": 0,
        "clean": 0,
        "not-applicable": 0,
    }
    assert verdict.EXIT_SIGINT == 130


def test_warn_as_error_exits_with_its_declared_code() -> None:
    assert verdict.exit_code_for(Status.WARN, warn_is_error=True) == exit_code("warden", "warn-as-error") == 1


def test_allow_empty_downgrades_to_the_clean_code_and_only_for_its_driver() -> None:
    empty = StatusDriver(axis="extraction", finding_id=EMPTY_EXTRACTION_DRIVER_ID)
    other = StatusDriver(axis="extraction", finding_id=EMPTY_EXTRACTION_DRIVER_ID + "-other")
    assert verdict.exit_code_for(Status.INDETERMINATE, driver=empty, allow_empty=True) == exit_code("warden", "clean")
    assert verdict.exit_code_for(Status.INDETERMINATE, driver=other, allow_empty=True) == exit_code(
        "warden", "indeterminate"
    )
