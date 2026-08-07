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
    cli/init.py::run_preflight adds MRS-PREFLIGHT-001..010. Story 1.8's
    cli/init.py::run_teardown adds MRS-TEARDOWN-001/002/003. Story 1.9's
    cli/init.py::run_preflight adds MRS-PREFLIGHT-011, graduating the
    harness-version check into two tiers. Story 2.1's cli/gate.py/core/gate.py
    add MRS-GATE-001/002/003/004/005. Story 2.4's
    core/gate.py::classify_doc_only_declaration adds MRS-GATE-006. Story
    3.2's core/journal.py::fold adds MRS-JOURNAL-001/002. Story 3.3's
    cli/spin.py adds MRS-SPIN-001/002/003/004/005/006. Story 3.4's
    cli/spin.py adds a seventh code to the same caller, MRS-SPIN-007. Story
    3.5's supervisor/__main__.py adds a NEW area, MRS-SUPV-001/002/003, and
    cli/spin.py adds an eighth code, MRS-SPIN-008. Story 3.6's
    supervisor/__main__.py adds MRS-SUPV-004/005/006 to the same area, and
    cli/spin.py adds a ninth code, MRS-SPIN-009. Story 3.7's
    supervisor/__main__.py adds MRS-SUPV-007 to the same area, and
    cli/spin.py adds MRS-SPIN-010/011/012. Story 3.8's
    supervisor/__main__.py adds MRS-SUPV-008 to the same area. Story 2.3's
    cli/gate.py/core/gate.py add MRS-GATE-007/008/009. Story 4.1's
    cli/deploy.py/core/promotion.py add a NEW area, MRS-DEPLOY-001/002/003.
    Story 2.7's cli/gate.py/core/gate.py add MRS-GATE-010/011. Story 4.2's
    cli/init.py/cli/deploy.py add MRS-TEARDOWN-004/MRS-DEPLOY-004. Code
    review (2026-08-06) adds MRS-TEARDOWN-005 (P1) and MRS-DEPLOY-005 (P5).
    Story 4.3's cli/deploy.py::run_land_story adds MRS-DEPLOY-006/007/008/
    009. Story 4.8's cli/land.py adds a NEW area, MRS-LAND-001..007. Story
    4.9's cli/deploy.py::run_promote adds MRS-DEPLOY-023 (the new specs_dir
    advisory lock, AD-42). This asserts the registry's exact real
    contents."""
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
            "MRS-PREFLIGHT-011",
            "MRS-TEARDOWN-001",
            "MRS-TEARDOWN-002",
            "MRS-TEARDOWN-003",
            "MRS-GATE-001",
            "MRS-GATE-002",
            "MRS-GATE-003",
            "MRS-GATE-004",
            "MRS-GATE-005",
            "MRS-GATE-006",
            "MRS-JOURNAL-001",
            "MRS-JOURNAL-002",
            "MRS-SPIN-001",
            "MRS-SPIN-002",
            "MRS-SPIN-003",
            "MRS-SPIN-004",
            "MRS-SPIN-005",
            "MRS-SPIN-006",
            "MRS-SPIN-007",
            "MRS-SPIN-008",
            "MRS-SPIN-009",
            "MRS-SUPV-001",
            "MRS-SUPV-002",
            "MRS-SUPV-003",
            "MRS-SUPV-004",
            "MRS-SUPV-005",
            "MRS-SUPV-006",
            "MRS-SUPV-007",
            "MRS-SPIN-010",
            "MRS-SPIN-011",
            "MRS-SPIN-012",
            "MRS-SUPV-008",
            "MRS-GATE-007",
            "MRS-GATE-008",
            "MRS-GATE-009",
            "MRS-DEPLOY-001",
            "MRS-DEPLOY-002",
            "MRS-DEPLOY-003",
            "MRS-GATE-010",
            "MRS-GATE-011",
            "MRS-TEARDOWN-004",
            "MRS-DEPLOY-004",
            "MRS-TEARDOWN-005",
            "MRS-DEPLOY-005",
            "MRS-DEPLOY-006",
            "MRS-DEPLOY-007",
            "MRS-DEPLOY-008",
            "MRS-DEPLOY-009",
            "MRS-DEPLOY-010",
            "MRS-DEPLOY-011",
            "MRS-DEPLOY-012",
            "MRS-DEPLOY-013",
            "MRS-DEPLOY-014",
            "MRS-DEPLOY-015",
            "MRS-DEPLOY-016",
            "MRS-DEPLOY-017",
            "MRS-DEPLOY-018",
            "MRS-DEPLOY-019",
            "MRS-DEPLOY-020",
            "MRS-STATUS-001",
            "MRS-DEPLOY-021",
            "MRS-DEPLOY-022",
            "MRS-LAND-001",
            "MRS-LAND-002",
            "MRS-LAND-003",
            "MRS-LAND-004",
            "MRS-LAND-005",
            "MRS-LAND-006",
            "MRS-LAND-007",
            "MRS-DEPLOY-023",
            "MRS-RETIRE-001",
            "MRS-RETIRE-002",
            "MRS-RETIRE-003",
            "MRS-STATUS-002",
            "MRS-STATUS-003",
            "MRS-STATUS-004",
            "MRS-STATUS-005",
            "MRS-STATUS-006",
            "MRS-STATUS-007",
            "MRS-STATUS-008",
            "MRS-STATUS-009",
            "MRS-CHECK-001",
            "MRS-CHECK-002",
            "MRS-CHECK-003",
            "MRS-CHECK-004",
            "MRS-SPIN-013",
            "MRS-SPIN-014",
            "MRS-SPIN-015",
            "MRS-ADP-001",
            "MRS-ADP-002",
            "MRS-ADP-003",
            "MRS-ADP-004",
            "MRS-ADP-005",
            "MRS-ADP-006",
            "MRS-ADP-007",
            "MRS-ADP-008",
            "MRS-ADP-009",
            "MRS-ADP-010",
            "MRS-ADP-011",
            "MRS-CONFORM-001",
            "MRS-ADP-012",
            "MRS-ADP-013",
            "MRS-ADP-014",
            "MRS-ADP-015",
            "MRS-ADP-016",
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
