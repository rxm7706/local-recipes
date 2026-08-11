"""Unit tests for ``pyforge.marshal.seed.model.version`` (Story 7.4) --
covers the spec's I/O & Edge-Case Matrix rows for parsing, SemVer 2.0.0
precedence (including the spec's own example chain from
<https://semver.org>), build-metadata-ignored-for-equality, and
``in_range``'s half-open boundary semantics.
"""

from __future__ import annotations

from itertools import pairwise

import pytest
from pyforge.marshal.seed.model.version import (
    InvalidVersionError,
    ModelVersion,
    in_range,
)

# --- parse: valid versions --------------------------------------------------


@pytest.mark.parametrize(
    "text,major,minor,patch,prerelease,build",
    [
        ("1.2.3", 1, 2, 3, (), ()),
        ("0.0.0", 0, 0, 0, (), ()),
        ("10.20.30", 10, 20, 30, (), ()),
        ("1.0.0-alpha", 1, 0, 0, ("alpha",), ()),
        ("1.0.0-alpha.1", 1, 0, 0, ("alpha", "1"), ()),
        ("1.0.0-x.7.z.92", 1, 0, 0, ("x", "7", "z", "92"), ()),
        ("1.0.0-x-y-z.--", 1, 0, 0, ("x-y-z", "--"), ()),
        ("1.0.0+20130313144700", 1, 0, 0, (), ("20130313144700",)),
        ("1.0.0+build1", 1, 0, 0, (), ("build1",)),
        (
            "1.0.0-beta+exp.sha.5114f85",
            1,
            0,
            0,
            ("beta",),
            ("exp", "sha", "5114f85"),
        ),
        ("1.0.0-alpha+001", 1, 0, 0, ("alpha",), ("001",)),
    ],
)
def test_parse_valid_versions(text, major, minor, patch, prerelease, build):
    version = ModelVersion.parse(text)
    assert version.major == major
    assert version.minor == minor
    assert version.patch == patch
    assert version.prerelease == prerelease
    assert version.build == build


# --- parse: invalid grammar --------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "",
        "1",
        "1.0",
        "1.0.0.0",
        "01.0.0",
        "1.01.0",
        "1.0.01",
        "1.0.0-01",
        "-1.0.0",
        "1.-1.0",
        "1.0.0-",
        "1.0.0+",
        "1.0.0-alpha_beta",
        "1.0.0+build_meta",
        "v1.0.0",
        "1.0.0\n",
        "1.0.0 ",
        "not-a-version",
    ],
)
def test_parse_rejects_malformed_grammar(text):
    with pytest.raises(InvalidVersionError):
        ModelVersion.parse(text)


def test_parse_rejects_non_str_input():
    with pytest.raises(InvalidVersionError):
        ModelVersion.parse(None)
    with pytest.raises(InvalidVersionError):
        ModelVersion.parse(100)


def test_invalid_version_error_is_a_value_error():
    assert issubclass(InvalidVersionError, ValueError)


def test_parse_rejects_non_ascii_digits():
    """SemVer 2.0.0's grammar is ASCII-only -- Python's bare `\\d` also
    matches non-ASCII Unicode decimal digits (e.g. Arabic-Indic), which
    would otherwise let ``"1٠3.0.0"`` parse as a silently-wrong
    ``major=103`` instead of raising (review finding)."""
    with pytest.raises(InvalidVersionError):
        ModelVersion.parse("1٠3.0.0")
    with pytest.raises(InvalidVersionError):
        ModelVersion.parse("1.0.0-٠")


# --- ModelVersion.__post_init__ direct-construction validation -------------


def test_direct_construction_rejects_negative_component():
    with pytest.raises(ValueError):
        ModelVersion(major=-1, minor=0, patch=0)


def test_direct_construction_rejects_bool_component():
    with pytest.raises(ValueError):
        ModelVersion(major=True, minor=0, patch=0)


def test_direct_construction_rejects_non_str_prerelease_member():
    with pytest.raises(ValueError):
        ModelVersion(major=1, minor=0, patch=0, prerelease=(1,))


# --- SemVer 2.0.0 precedence: the spec's own worked example -----------------


def test_prerelease_ordering_chain_matches_semver_spec_example():
    """<https://semver.org>'s own worked example, verbatim: this exact chain
    is strictly increasing under SemVer 2.0.0 precedence."""
    chain = [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0",
    ]
    versions = [ModelVersion.parse(text) for text in chain]
    for earlier, later in pairwise(versions):
        assert earlier < later, f"{earlier} should be < {later}"
        assert later > earlier
        assert earlier != later
        assert earlier <= later
        assert later >= earlier


def test_release_has_higher_precedence_than_its_own_prerelease():
    assert ModelVersion.parse("1.0.0-alpha") < ModelVersion.parse("1.0.0")
    assert ModelVersion.parse("1.0.0") > ModelVersion.parse("1.0.0-alpha")


def test_numeric_prerelease_identifiers_compare_numerically_not_lexically():
    """``"11"`` must compare greater than ``"2"`` numerically -- a naive
    string compare would say the opposite (``"11" < "2"`` lexically)."""
    assert ModelVersion.parse("1.0.0-beta.2") < ModelVersion.parse("1.0.0-beta.11")


def test_numeric_identifier_always_lower_precedence_than_alphanumeric():
    assert ModelVersion.parse("1.0.0-1") < ModelVersion.parse("1.0.0-a")
    assert ModelVersion.parse("1.0.0-9") < ModelVersion.parse("1.0.0-0a")


def test_more_prerelease_fields_is_higher_precedence_when_prefix_equal():
    assert ModelVersion.parse("1.0.0-alpha") < ModelVersion.parse("1.0.0-alpha.1")


def test_core_version_differences_dominate_prerelease():
    assert ModelVersion.parse("1.0.0") < ModelVersion.parse("1.0.1-alpha")
    assert ModelVersion.parse("1.9.9") < ModelVersion.parse("2.0.0-alpha")


# --- build metadata: parsed, but never affects precedence/equality ---------


def test_build_metadata_ignored_for_equality():
    left = ModelVersion.parse("1.0.0+build1")
    right = ModelVersion.parse("1.0.0+build2")
    assert left == right
    assert left <= right
    assert left >= right
    assert not (left < right)
    assert not (left > right)


def test_build_metadata_round_trips_but_does_not_affect_ordering():
    with_build = ModelVersion.parse("1.0.0-alpha+001")
    without_build = ModelVersion.parse("1.0.0-alpha")
    assert with_build.build == ("001",)
    assert with_build == without_build


# --- equality / ordering type handling --------------------------------------


def test_eq_against_non_model_version_is_not_equal():
    assert ModelVersion.parse("1.0.0") != "1.0.0"


def test_lt_against_non_model_version_raises_type_error():
    with pytest.raises(TypeError):
        _ = ModelVersion.parse("1.0.0") < "1.0.0"


# --- in_range: half-open [since, until) -------------------------------------


def test_in_range_both_bounds_none_always_true():
    version = ModelVersion.parse("1.0.0")
    assert in_range(version, None, None) is True


def test_in_range_since_is_inclusive():
    since = ModelVersion.parse("1.0.0")
    assert in_range(ModelVersion.parse("1.0.0"), since, None) is True
    assert in_range(ModelVersion.parse("0.9.9"), since, None) is False
    assert in_range(ModelVersion.parse("1.0.1"), since, None) is True


def test_in_range_until_is_exclusive():
    until = ModelVersion.parse("2.0.0")
    assert in_range(ModelVersion.parse("1.9.9"), None, until) is True
    assert in_range(ModelVersion.parse("2.0.0"), None, until) is False
    assert in_range(ModelVersion.parse("2.0.1"), None, until) is False


def test_in_range_both_bounds_set():
    since = ModelVersion.parse("1.0.0")
    until = ModelVersion.parse("2.0.0")
    assert in_range(ModelVersion.parse("0.9.9"), since, until) is False
    assert in_range(ModelVersion.parse("1.0.0"), since, until) is True
    assert in_range(ModelVersion.parse("1.5.0"), since, until) is True
    assert in_range(ModelVersion.parse("2.0.0"), since, until) is False
    assert in_range(ModelVersion.parse("2.0.1"), since, until) is False
