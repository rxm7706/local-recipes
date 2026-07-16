"""Unit tests — ``extract/_identity.py``'s conda-matchspec exactness
discipline (Story 2.2 shared foundation): ``classify_conda_specifier`` AND
``split_conda_dep_string`` exercised directly, no extractor in between.
"""

from __future__ import annotations

from pyforge.warden.extract._identity import (
    classify_conda_specifier,
    split_conda_dep_string,
)
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


# --- follow-up review (2026-07-16): the exactness gate generalized ----------


def test_compatible_release_operator_is_range_only_never_exact():
    """Root cause (verified live before the fix): `~=` was absent from the
    operator tuple, so `~=1.20` fell through to the bare-token path and a
    compatible-release RANGE was returned as a confident EXACT version
    string `'~=1.20'` -- the same C0 bug class as Fix 4's `===`, missed for
    `~=`."""
    assert classify_conda_specifier("~=1.20") == (None, WithholdReason.RANGE_ONLY)


def test_v0_version_build_pair_yields_the_version_never_the_pair():
    """The classic v0 3-token spec (`zlib 1.2.11 h470a237_3`): the version
    part IS exact conda semantics; the build string must be dropped, never
    baked into a corrupted `'1.2.11 h470a237_3'` \"version\" (verified live
    before the fix: the whole pair came back EXACT + vuln_matchable)."""
    assert classify_conda_specifier("1.2.11 h470a237_3") == ("1.2.11", None)


def test_three_part_or_garbage_specifiers_are_withheld():
    for specifier in (
        "1.2.11 h4 extra",  # 3+ whitespace parts: not the version/build pair
        "==1.20=py39",  # `=`-embedded value after `==`
        "# [linux]",  # post-substitution garbage (a baked-in YAML comment)
        "~1.2",  # lone-tilde debris
    ):
        assert classify_conda_specifier(specifier) == (
            None,
            WithholdReason.RANGE_ONLY,
        )


def test_conda_legal_letter_suffix_version_stays_exact():
    # `1.1.1k` is a REAL conda version shape (openssl) -- the shape gate
    # must not over-reject conda's own grammar.
    assert classify_conda_specifier("1.1.1k") == ("1.1.1k", None)


def test_split_recognizes_compatible_release_both_forms():
    assert split_conda_dep_string("numpy ~=1.20") == ("numpy", "~=1.20")
    # Contiguous form: `~` excluded from the name charset, so the name is
    # never corrupted to `numpy~` (verified live before the fix).
    assert split_conda_dep_string("numpy~=1.20") == ("numpy", "~=1.20")


def test_split_strips_a_channel_prefix_from_the_name():
    """`conda-forge::numpy=1.20` is standard environment.yml syntax -- the
    channel is routing, not part of the package name (it used to stay baked
    in, guaranteeing a conda->pypi map miss)."""
    assert split_conda_dep_string("conda-forge::numpy=1.20") == ("numpy", "=1.20")
    assert split_conda_dep_string("pkgs/main::python >=3.10") == (
        "python",
        ">=3.10",
    )
    assert split_conda_dep_string("conda-forge::") is None


def test_split_degrades_a_nameless_operator_leading_spec():
    """`==1.2.3` has no name -- previously the WHOLE spec text became a
    fabricated component NAME (`'==1.2.3'`); now it is unidentifiable and
    the caller degrades it."""
    assert split_conda_dep_string("==1.2.3") is None
