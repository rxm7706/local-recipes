"""Unit tests for ``pyforge.marshal.core.verdict`` (Story 1.1, AD-7/AD-31)
-- ``classify``/``compute_verdict``/``exit_code_for`` behavior via
monkeypatched registry + classify-table entries; empty-findings floor
behavior. ``_CLASSIFY_TABLE`` ships with Story 1.2's two real entries
(``MRS-IDENT-001``/``MRS-IDENT-002``, from ``core/identity.py``); the
tests here still exercise the MECHANISM via ``monkeypatch``-injected
synthetic entries, never the real ones. Story 2.2 adds the AD-8 property
tests (``test_ad8_*``): the closed-lattice, floor-swept exhaustive proof
that no input containing an ``unevaluable``-classified finding ever
computes ``clean``, plus its real-registry counterpart.
"""

from __future__ import annotations

import itertools

import pytest

from pyforge.marshal.core import findings, verdict
from pyforge.marshal.core.model import Finding, Severity, Status, Verdict, status_for

_CODE_CLEAN = "MRS-TST-001"
_CODE_WARN = "MRS-TST-002"
_CODE_ERROR = "MRS-TST-003"


@pytest.fixture
def synthetic_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        findings,
        "REGISTERED_CODES",
        frozenset({_CODE_CLEAN, _CODE_WARN, _CODE_ERROR}),
    )
    monkeypatch.setattr(
        verdict,
        "_CLASSIFY_TABLE",
        {
            _CODE_CLEAN: Verdict.CLEAN,
            _CODE_WARN: Verdict.WARN,
            _CODE_ERROR: Verdict.ERROR,
        },
    )


def test_lattice_order_has_six_members_strongest_first():
    assert verdict.LATTICE_ORDER == (
        Verdict.ERROR,
        Verdict.GATE_FAILED,
        Verdict.SCOPE_VIOLATION,
        Verdict.UNEVALUABLE,
        Verdict.WARN,
        Verdict.CLEAN,
    )


def test_exit_sigint_constant():
    assert verdict.EXIT_SIGINT == 130


def test_cli_boundary_constants_and_guarded_domain():
    """verdict.py is the sole owner of every guarded exit-code literal
    (AD-7): the CLI imports these names instead of spelling the integers.
    The literal expectations live HERE (a test, not an installed module) on
    purpose -- an independent copy that catches the domain drifting."""
    assert verdict.EXIT_OK == 0
    assert verdict.EXIT_USAGE == 2
    assert verdict.GUARDED_EXIT_CODES == frozenset({0, 1, 2, 3, 4, 130})


@pytest.mark.parametrize(
    "member,expected_exit",
    [
        (Verdict.CLEAN, 0),
        (Verdict.WARN, 0),
        (Verdict.UNEVALUABLE, 1),
        (Verdict.SCOPE_VIOLATION, 2),
        (Verdict.GATE_FAILED, 3),
        (Verdict.ERROR, 4),
    ],
)
def test_exit_code_for_every_lattice_member(member, expected_exit):
    assert verdict.exit_code_for(member) == expected_exit


def test_exit_code_for_accepts_raw_string():
    assert verdict.exit_code_for("clean") == 0


def test_exit_code_for_rejects_an_invalid_verdict():
    with pytest.raises(ValueError):
        verdict.exit_code_for("not-a-verdict")


def test_warn_never_shares_unevaluables_nonzero_exit():
    """AD-31's own reasoning: warn is a distinct rung from unevaluable only
    because warn's exit stays 0 while unevaluable's does not."""
    assert verdict.exit_code_for(Verdict.WARN) == 0
    assert verdict.exit_code_for(Verdict.UNEVALUABLE) != 0


def test_classify_rejects_unregistered_code():
    with pytest.raises(findings.UnregisteredFindingCodeError):
        verdict.classify("MRS-ZZZ-999")


def test_classify_rejects_malformed_code():
    with pytest.raises(findings.UnregisteredFindingCodeError):
        verdict.classify("not-a-code")


def test_classify_on_registered_but_unclassified_code_raises(monkeypatch):
    monkeypatch.setattr(findings, "REGISTERED_CODES", frozenset({"MRS-TST-999"}))
    with pytest.raises(ValueError):
        verdict.classify("MRS-TST-999")


def test_classify_returns_the_synthetic_classification(synthetic_registry):
    assert verdict.classify(_CODE_WARN) is Verdict.WARN
    assert verdict.classify(_CODE_ERROR) is Verdict.ERROR


def test_compute_verdict_empty_findings_returns_floor():
    assert verdict.compute_verdict([]) == Verdict.CLEAN


def test_compute_verdict_empty_findings_returns_custom_floor():
    assert verdict.compute_verdict([], floor=Verdict.WARN) == Verdict.WARN


def test_compute_verdict_returns_the_strongest_finding(synthetic_registry):
    findings_list = [
        Finding(code=_CODE_WARN, severity=Severity.WARN, message="m"),
        Finding(code=_CODE_ERROR, severity=Severity.ERROR, message="m"),
        Finding(code=_CODE_CLEAN, severity=Severity.INFO, message="m"),
    ]
    assert verdict.compute_verdict(findings_list) == Verdict.ERROR


def test_compute_verdict_floor_wins_when_stronger_than_findings(synthetic_registry):
    findings_list = [Finding(code=_CODE_CLEAN, severity=Severity.INFO, message="m")]
    assert (
        verdict.compute_verdict(findings_list, floor=Verdict.GATE_FAILED)
        == Verdict.GATE_FAILED
    )


def test_compute_verdict_coerces_a_raw_string_floor():
    """``compute_verdict`` is meant to be as total/defensive as
    ``exit_code_for`` -- a raw string ``floor`` must coerce via
    ``Verdict(floor)``, not pass through unvalidated."""
    assert verdict.compute_verdict([], floor="warn") is Verdict.WARN


def test_compute_verdict_rejects_an_invalid_floor():
    with pytest.raises(ValueError):
        verdict.compute_verdict([], floor="not-a-verdict")


def test_compute_verdict_rejects_non_finding_elements(synthetic_registry):
    """Same member strictness as Envelope.__post_init__: a raw code string
    (or anything else that isn't a Finding) is a fail-loud ValueError, not a
    raw AttributeError from ``finding.code``."""
    with pytest.raises(ValueError):
        verdict.compute_verdict([_CODE_WARN])


def test_ad8_no_combination_of_the_full_lattice_produces_clean_when_any_finding_is_unevaluable(
    monkeypatch,
):
    """AD-8: there exists no input producing ``clean`` when any check is
    ``unevaluable``. Exhaustive over lengths 1-3 (not sampled) -- every
    combination of 1-3 synthetic findings drawn from the full 6-member
    lattice (``itertools.product``, not ``hypothesis``: not a project
    dependency, and the closed 6-member lattice is small enough that full
    enumeration is strictly stronger than sampling over this bounded
    length), filtered to combinations containing at least one
    ``Verdict.UNEVALUABLE``, checked against every possible ``floor``.
    Bounded to 3 findings because ``compute_verdict``'s fold is a simple
    per-element max with no length-dependent state -- a 4th+ finding can
    only ever repeat a classification already exercised in a
    shorter combination, never introduce new aggregation behavior. Same
    monkeypatch pattern as ``synthetic_registry`` above, generalized to a
    per-combination classify table since the classification itself varies
    per combination.

    Each assertion checks TWO independent projections of the "never a
    false green" property, not just enum identity: ``is not Verdict.CLEAN``
    (the literal AD-8 wording) AND ``status_for(...) is Status.ERROR`` (the
    AD-8 CONSEQUENCE -- "projects to a non-zero exit and blocks
    progression"). ``status_for`` maps both ``clean`` and ``warn`` to
    ``Status.OK``, so this closes the gap a bare CLEAN-identity check would
    leave open: a hypothetical regression that resolved an
    unevaluable-containing input to ``Verdict.WARN`` (exit 0, non-blocking)
    would still be a false green even though it is "not clean"."""
    codes = ("MRS-TST-101", "MRS-TST-102", "MRS-TST-103")
    executed = 0
    for length in (1, 2, 3):
        active_codes = codes[:length]
        assert len(active_codes) == length, (
            "codes tuple is shorter than the tested length -- zip(active_codes, "
            "combo) would silently truncate and drop tested combinations"
        )
        monkeypatch.setattr(
            findings, "REGISTERED_CODES", frozenset(active_codes)
        )
        for combo in itertools.product(Verdict, repeat=length):
            if Verdict.UNEVALUABLE not in combo:
                continue
            monkeypatch.setattr(
                verdict, "_CLASSIFY_TABLE", dict(zip(active_codes, combo))
            )
            findings_list = [
                Finding(code=code, severity=Severity.INFO, message="m")
                for code in active_codes
            ]
            for floor in Verdict:
                result = verdict.compute_verdict(findings_list, floor=floor)
                assert result is not Verdict.CLEAN
                assert status_for(result) is Status.ERROR
                executed += 1
    # Proof the exhaustive sweep above actually ran assertions and did not
    # silently degenerate into a no-op (e.g. a typo'd/inverted `continue`
    # filter, or an emptied `itertools.product` call) -- a loop with no
    # reachable assertion is a PASSING test that proves nothing, the exact
    # false-green class this test file exists to prevent.
    assert executed > 0


def test_ad8_real_unevaluable_code_list_is_non_empty():
    """Guards ``test_ad8_every_real_unevaluable_code_never_projects_to_clean``'s
    own parametrize list, which is derived from ``verdict._CLASSIFY_TABLE``
    at collection time (never hand-copied). pytest's default behavior for
    an empty parametrize set is to silently collect zero test cases, not to
    fail -- so if a future story ever reclassified every currently
    ``unevaluable`` code away, that regression test would quietly stop
    running instead of loudly failing. This test fails loud instead."""
    assert any(
        member is Verdict.UNEVALUABLE for member in verdict._CLASSIFY_TABLE.values()
    )


@pytest.mark.parametrize(
    "code",
    [
        code
        for code, member in verdict._CLASSIFY_TABLE.items()
        if member is Verdict.UNEVALUABLE
    ],
)
def test_ad8_every_real_unevaluable_code_never_projects_to_clean(code):
    """AD-8 against the ACTUAL registry, not only synthetic codes -- the
    parametrized code list is derived from ``_CLASSIFY_TABLE`` at
    collection time, never hand-copied, so a future story's new
    ``unevaluable`` code is covered automatically (non-emptiness of that
    list is separately guarded by
    ``test_ad8_real_unevaluable_code_list_is_non_empty`` above). Checks the
    same two projections as the exhaustive sweep above: enum identity and
    the AD-8 consequence (``status_for`` is ``Status.ERROR``, never the
    ``ok`` that ``clean``/``warn`` share)."""
    finding = Finding(code=code, severity=Severity.INFO, message="m")
    result = verdict.compute_verdict([finding])
    assert result is not Verdict.CLEAN
    assert status_for(result) is Status.ERROR
