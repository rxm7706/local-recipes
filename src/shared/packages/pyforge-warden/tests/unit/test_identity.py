"""Unit tests — ``extract/_identity.py``'s conda-matchspec exactness
discipline (Story 2.2 shared foundation): ``classify_conda_specifier``
exercised directly, no extractor in between.
"""

from __future__ import annotations

from pyforge.warden.extract._identity import classify_conda_specifier
from pyforge.warden.models import WithholdReason


# --- exact pins -----------------------------------------------------------


def test_double_equals_is_exact():
    assert classify_conda_specifier("==1.2.3") == ("1.2.3", None)


def test_bare_version_no_operator_is_exact():
    assert classify_conda_specifier("1.2.3") == ("1.2.3", None)


# --- conservative withholds -------------------------------------------------


def test_single_equals_fuzzy_prefix_is_range_only():
    assert classify_conda_specifier("=1.2") == (None, WithholdReason.RANGE_ONLY)


def test_other_comparison_operators_are_range_only():
    for specifier in (">=1.2.3", "<=1.2.3", "!=1.2.3", ">1.2.3", "<1.2.3"):
        assert classify_conda_specifier(specifier) == (
            None,
            WithholdReason.RANGE_ONLY,
        )


def test_wildcard_suffixed_exact_pin_is_range_only():
    assert classify_conda_specifier("==1.2.*") == (None, WithholdReason.RANGE_ONLY)


def test_bare_wildcard_version_is_range_only():
    assert classify_conda_specifier("1.2.*") == (None, WithholdReason.RANGE_ONLY)


def test_none_or_star_specifier_is_no_version():
    assert classify_conda_specifier(None) == (None, WithholdReason.NO_VERSION)
    assert classify_conda_specifier("*") == (None, WithholdReason.NO_VERSION)
    assert classify_conda_specifier("") == (None, WithholdReason.NO_VERSION)


# --- Fix 4 (2026-07-16 review): `===` must never corrupt a version --------


def test_triple_equals_never_yields_a_corrupted_version():
    """Root cause (verified live before the fix):
    `classify_conda_specifier('===1.2.3')` used to strip exactly 2 leading
    `=` characters unconditionally, returning `('=1.2.3', None)` -- a
    corrupted version with a stray leading `=` baked in, silently treated
    as a confident EXACT match (a C0 'never guess a version' violation:
    poisons CVE/vuln-match lookups with a wrong version string). `===` is
    not standard conda matchspec syntax (conda uses bare/`=`/`==`, not PEP
    440's `===` arbitrary-equality) -- the chosen, conservative fix treats
    it the same as any other unrecognized/non-`==` shape: withheld as
    RANGE_ONLY, never guessed, and NEVER a version string containing a
    stray `=`."""
    version, reason = classify_conda_specifier("===1.2.3")
    assert version is None
    assert reason is WithholdReason.RANGE_ONLY
    # Explicit belt-and-suspenders: whatever the chosen behavior, a
    # returned version must never itself carry a leftover `=`.
    if version is not None:
        assert "=" not in version


def test_quadruple_equals_is_also_withheld_never_corrupted():
    version, reason = classify_conda_specifier("====1.2.3")
    assert version is None
    assert reason is WithholdReason.RANGE_ONLY
