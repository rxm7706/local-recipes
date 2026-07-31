"""Unit tests for ``pyforge.marshal.core.findings`` (Story 1.1, AD-15) --
format + membership checks via ``monkeypatch``-registered synthetic codes.
Most tests below still exercise the mechanism via synthetic codes, never a
fabricated production one -- ``test_registered_codes_contains_the_real_codes``
is the one exception, asserting the registry's REAL, currently-shipped
contents.
"""

from __future__ import annotations

import pytest

from pyforge.marshal.core import findings


def test_registered_codes_contains_the_real_codes():
    """The registry no longer starts empty -- Story 1.2's core/identity.py
    is its first real caller, registering MRS-IDENT-001/002. Story 1.3's
    core/policy.py/cli/config.py add MRS-POLICY-001/002/003/004/005/006.
    Story 1.4's cli/init.py adds MRS-INIT-001/002/003/004. Story 1.5's
    cli/init.py tier3_backlink step adds MRS-INIT-005. Story 1.6's
    cli/init.py::run_homes adds MRS-HOMES-001/002/003. Story 1.7's
    cli/init.py::run_preflight adds MRS-PREFLIGHT-001..010. This asserts the
    registry's exact real contents."""
    assert findings.REGISTERED_CODES == frozenset(
        {
            "MRS-IDENT-001",
            "MRS-IDENT-002",
            "MRS-POLICY-001",
            "MRS-POLICY-002",
            "MRS-POLICY-003",
            "MRS-POLICY-004",
            "MRS-POLICY-005",
            "MRS-POLICY-006",
            "MRS-INIT-001",
            "MRS-INIT-002",
            "MRS-INIT-003",
            "MRS-INIT-004",
            "MRS-INIT-005",
            "MRS-HOMES-001",
            "MRS-HOMES-002",
            "MRS-HOMES-003",
            "MRS-PREFLIGHT-001",
            "MRS-PREFLIGHT-002",
            "MRS-PREFLIGHT-003",
            "MRS-PREFLIGHT-004",
            "MRS-PREFLIGHT-005",
            "MRS-PREFLIGHT-006",
            "MRS-PREFLIGHT-007",
            "MRS-PREFLIGHT-008",
            "MRS-PREFLIGHT-009",
            "MRS-PREFLIGHT-010",
        }
    )


def test_code_pattern_matches_well_formed_code():
    assert findings.CODE_PATTERN.fullmatch("MRS-GATE-001")


@pytest.mark.parametrize(
    "code",
    [
        "not-a-code",
        "mrs-gate-001",
        "MRS-GATE-1",
        "MRS-001",
        "MRS-GATE-0001",
        "",
        "MRS-GATE-001\n",  # the `$`-before-trailing-newline `re` pitfall
        "MRS-GATE-001 ",
        "MRS-GATE-١٢٣",  # Arabic-Indic digits: Python's \d
        # would accept these; [0-9] (matching the schema's ECMA reading)
        # must not.
    ],
)
def test_code_pattern_rejects_malformed_codes(code):
    assert findings.CODE_PATTERN.fullmatch(code) is None


def test_code_pattern_is_matched_with_fullmatch_not_match():
    """Regression: CODE_PATTERN carries no ^/$ anchors and MUST be matched
    with .fullmatch(), never .match() -- .match() only anchors at the start,
    so an unanchored pattern would wrongly accept a code with a trailing
    extra digit or newline as long as its PREFIX is well-formed."""
    assert findings.CODE_PATTERN.match("MRS-GATE-0001") is not None  # prefix matches
    assert findings.CODE_PATTERN.fullmatch("MRS-GATE-0001") is None  # but not fully
    with pytest.raises(findings.UnregisteredFindingCodeError):
        findings.require_registered("MRS-GATE-0001")


def test_require_registered_rejects_malformed_code_before_membership_check():
    with pytest.raises(findings.UnregisteredFindingCodeError):
        findings.require_registered("not-a-code")


def test_require_registered_rejects_wellformed_but_unregistered_code():
    with pytest.raises(findings.UnregisteredFindingCodeError):
        findings.require_registered("MRS-ZZZ-999")


def test_require_registered_accepts_monkeypatched_synthetic_code(monkeypatch):
    monkeypatch.setattr(findings, "REGISTERED_CODES", frozenset({"MRS-TST-001"}))
    assert findings.require_registered("MRS-TST-001") == "MRS-TST-001"


def test_require_registered_still_rejects_other_codes_after_monkeypatch(monkeypatch):
    monkeypatch.setattr(findings, "REGISTERED_CODES", frozenset({"MRS-TST-001"}))
    with pytest.raises(findings.UnregisteredFindingCodeError):
        findings.require_registered("MRS-TST-002")


def test_unregistered_finding_code_error_is_a_value_error():
    assert issubclass(findings.UnregisteredFindingCodeError, ValueError)
