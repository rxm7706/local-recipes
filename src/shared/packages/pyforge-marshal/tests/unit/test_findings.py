"""Unit tests for ``pyforge.marshal.core.findings`` (Story 1.1, AD-15) --
format + membership checks via ``monkeypatch``-registered synthetic codes.
``REGISTERED_CODES`` starts an empty ``frozenset()`` in the shipped module
(Design Notes) -- no test here fabricates a production code.
"""

from __future__ import annotations

import pytest

from pyforge.marshal.core import findings


def test_registered_codes_starts_empty():
    assert findings.REGISTERED_CODES == frozenset()


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

    def require_registered_uses_fullmatch() -> None:
        with pytest.raises(findings.UnregisteredFindingCodeError):
            findings.require_registered("MRS-GATE-0001")

    require_registered_uses_fullmatch()


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
