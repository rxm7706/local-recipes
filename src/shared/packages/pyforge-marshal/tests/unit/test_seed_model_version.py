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


# --- the grammar is validated on the FIELDS, not just on the parsed string ----


@pytest.mark.parametrize(
    "identifier",
    [
        "²",  # superscript two: .isdigit() is True, int() raises
        "١",  # Arabic-Indic one: non-ASCII, outside the grammar
        "01",  # leading zero: forbidden by SemVer 2.0.0
        "",  # empty identifier
        "al pha",  # illegal character
    ],
)
def test_direct_construction_rejects_non_grammar_prerelease_identifier(identifier):
    """`parse` is not the only way in -- tests, `dataclasses.replace`, and a
    future state deserializer construct this directly. An identifier
    outside the grammar breaks ORDERING itself, so it cannot be accepted."""
    with pytest.raises(ValueError, match="not a valid SemVer 2.0.0 identifier"):
        ModelVersion(major=1, minor=0, patch=0, prerelease=(identifier,))


def test_direct_construction_rejects_non_grammar_build_identifier():
    with pytest.raises(ValueError, match="not a valid SemVer 2.0.0 identifier"):
        ModelVersion(major=1, minor=0, patch=0, build=("has space",))


def test_comparison_is_total_for_every_constructible_version():
    """Trichotomy: for any two constructible versions exactly one of <, >,
    == holds. `("01",)` vs `("1",)` used to satisfy none of the three --
    equal numerically, unequal by `__eq__` -- silently corrupting `sorted`."""
    versions = [
        ModelVersion.parse(text) for text in ("1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-1", "1.0.0-2", "1.0.0", "1.0.1")
    ]
    for left in versions:
        for right in versions:
            assert sum((left < right, left > right, left == right)) == 1


def test_isdigit_only_identifiers_never_reach_the_int_comparator():
    """Guard the comparator directly: even handed a superscript, it must
    not raise the `int()` ValueError that `.isdigit()` alone invites."""
    left = ModelVersion.parse("1.0.0-1")
    right = object.__new__(ModelVersion)
    object.__setattr__(right, "major", 1)
    object.__setattr__(right, "minor", 0)
    object.__setattr__(right, "patch", 0)
    object.__setattr__(right, "prerelease", ("²",))
    object.__setattr__(right, "build", ())
    assert isinstance(left < right, bool)
    assert isinstance(right < left, bool)


# --- str() round-trips to the string parse() accepts --------------------------


@pytest.mark.parametrize(
    "text",
    ["1.2.3", "0.0.0", "1.0.0-alpha", "1.0.0-alpha.1", "1.0.0+build.1", "1.2.3-rc.1+exp.sha.5114f85"],
)
def test_str_round_trips_through_parse(text):
    version = ModelVersion.parse(text)
    assert str(version) == text
    assert ModelVersion.parse(str(version)) == version


def test_str_is_used_in_error_messages_not_the_dataclass_repr():
    assert "ModelVersion(" not in str(ModelVersion.parse("1.0.0"))


def test_parse_rejects_a_numeric_component_int_cannot_convert():
    """CPython refuses int() past 4300 digits -- a raw ValueError there
    would sail past every caller catching InvalidVersionError."""
    with pytest.raises(InvalidVersionError, match="unusable numeric component"):
        ModelVersion.parse("1" * 5000 + ".0.0")


def test_long_numeric_prerelease_identifiers_compare_without_int():
    """SemVer 2.0.0 puts no length bound on a numeric pre-release
    identifier, but CPython refuses ``int()`` past 4300 digits -- so an
    ``int()``-based comparator raised a raw ValueError straight out of
    ``__lt__``. Ordering must still be correct, not merely non-raising."""
    smaller = ModelVersion.parse("1.0.0-" + "1" * 5000)
    larger = ModelVersion.parse("1.0.0-" + "2" * 5000)
    longer = ModelVersion.parse("1.0.0-" + "1" * 5001)
    assert smaller < larger
    assert not larger < smaller
    assert smaller < longer  # more digits == larger number
    assert smaller == ModelVersion.parse("1.0.0-" + "1" * 5000)


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("1.0.0-1", "1.0.0-2"),
        ("1.0.0-2", "1.0.0-10"),  # numeric, NOT lexicographic
        ("1.0.0-9", "1.0.0-" + "1" * 4400),
        ("1.0.0-" + "9" * 4400, "1.0.0-" + "1" * 4401),
    ],
)
def test_numeric_prerelease_ordering_is_numeric_at_every_length(left, right):
    assert ModelVersion.parse(left) < ModelVersion.parse(right)
    assert not ModelVersion.parse(right) < ModelVersion.parse(left)


def test_long_numeric_prerelease_stays_inside_in_range():
    """The comparator is reached through ``in_range`` by
    ``load_manifest``'s post-validation filter, which sits outside every
    ``try/except`` -- a raw ValueError there escapes the loader's
    ManifestError-only contract entirely."""
    version = ModelVersion.parse("1.0.0-" + "1" * 5000)
    since = ModelVersion.parse("1.0.0-" + "1" * 4999)
    until = ModelVersion.parse("1.0.0-" + "2" * 5000)
    assert in_range(version, since, until) is True


@pytest.mark.parametrize("component", ["major", "minor", "patch"])
def test_unrenderable_numeric_component_is_rejected_at_construction(component):
    """``parse`` already converts an over-long numeric component to
    ``InvalidVersionError``, but ``__post_init__`` -- the second, unguarded
    entry point -- accepted any ``int``, and CPython refuses to RENDER one
    past 4300 digits. ``__str__`` then blew up while FORMATTING this
    module's own AC-mandated error ("until (...) must be strictly greater
    than since (...)") instead of reporting it."""
    with pytest.raises(ValueError, match=rf"^{component} has an unusable numeric component: "):
        ModelVersion(**{"major": 0, "minor": 0, "patch": 0, component: 10**5000})


def test_every_constructible_version_is_renderable():
    """The invariant behind the guard above: if a ModelVersion exists, any
    message that interpolates it can be formatted."""
    version = ModelVersion(major=10**300, minor=0, patch=0)
    assert str(version).startswith("1" + "0" * 300)
    assert ModelVersion.parse(str(version)) == version
