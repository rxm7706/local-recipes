"""``pyforge.core.exit_domains`` -- the exit-code declaration's in-process table (steward Story 137.1,
spec-pyforge-steward:CAP-184)."""

from __future__ import annotations

import pytest

from pyforge.core.exit_domains import (
    EXIT_CODE_DOMAINS,
    EXIT_CODE_DOMAINS_NARROWING,
    domain_codes,
    exit_code,
)


def test_the_five_domains_are_declared() -> None:
    assert set(EXIT_CODE_DOMAINS) == {"doctor", "warden", "marshal", "marshal-seed", "detectors"}


@pytest.mark.parametrize(
    ("domain", "codes"),
    [
        ("doctor", {0, 2, 130}),
        ("warden", {0, 1, 2, 130}),
        ("marshal", {0, 1, 2, 3, 4, 130}),
        ("marshal-seed", {1, 2, 3, 4, 5, 10}),
        ("detectors", {0, 1, 2}),
    ],
)
def test_each_domain_keeps_the_codes_its_module_used(domain: str, codes: set[int]) -> None:
    assert domain_codes(domain) == frozenset(codes)


def test_two_means_fail_to_doctor_and_could_not_run_to_the_aggregator() -> None:
    assert exit_code("doctor", "fail") == 2
    assert exit_code("detectors", "could-not-run") == 2
    assert exit_code("detectors", "findings") == 1
    assert 1 not in domain_codes("doctor")


def test_a_warn_never_changes_an_exit_code() -> None:
    assert exit_code("doctor", "warn") == 0
    assert exit_code("warden", "warn") == 0
    assert exit_code("marshal", "warn") == 0


def test_every_declared_narrowing_holds() -> None:
    assert dict(EXIT_CODE_DOMAINS_NARROWING) == {"doctor": "warden"}
    for narrow, wide in EXIT_CODE_DOMAINS_NARROWING.items():
        assert domain_codes(narrow) <= domain_codes(wide), (narrow, wide)


def test_the_table_is_read_only() -> None:
    with pytest.raises(TypeError):
        EXIT_CODE_DOMAINS["doctor"]["fail"] = 1  # type: ignore[index]
    with pytest.raises(TypeError):
        EXIT_CODE_DOMAINS["new"] = {}  # type: ignore[index]


@pytest.mark.parametrize(("domain", "member"), [("nope", "fail"), ("doctor", "nope")])
def test_an_undeclared_name_is_a_key_error_naming_it(domain: str, member: str) -> None:
    with pytest.raises(KeyError, match="nope"):
        exit_code(domain, member)


def test_an_undeclared_domain_has_no_code_set() -> None:
    with pytest.raises(KeyError, match="nope"):
        domain_codes("nope")
