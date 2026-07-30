"""Unit tests for ``pyforge.marshal.core.identity`` (Story 1.2,
AD-23/AD-24/AD-38) -- ``normalize()`` across every I/O & Edge-Case Matrix
scenario, the four render functions' output shapes, ``StoryKey`` total
ordering, the merge-subject render/parse round-trip (parametrized over key
shapes x templates), and ``resolve_feed()``'s completeness reporting.

``MRS-IDENT-001``/``MRS-IDENT-002`` are real, already-registered codes
(Story 1.2's first real registrations) -- unlike ``test_model.py``'s
synthetic-code fixtures, no monkeypatching is needed here.
"""

from __future__ import annotations

import pytest

from pyforge.marshal.core import verdict
from pyforge.marshal.core.identity import (
    FeedResolution,
    MalformedStoryKeyError,
    MergeSubjectConformanceError,
    StoryKey,
    normalize,
    parse_merge_subject,
    render_branch_segment,
    render_feed_key,
    render_filename_slug,
    render_merge_subject,
    resolve_feed,
)
from pyforge.marshal.core.model import Verdict

# --- normalize(): the I/O & Edge-Case Matrix --------------------------------


def test_normalize_dot_feed_key_with_suffix():
    assert normalize("6.1a") == StoryKey(epic=6, seq=1, suffix="a")


def test_normalize_hyphen_key_with_trailing_slug():
    key = normalize(
        "1-2-story-identity-merge-subject-rendering-and-feed-completeness"
    )
    assert key == StoryKey(epic=1, seq=2, suffix="")


def test_normalize_lowercases_uppercase_suffix():
    assert normalize("2-6A") == StoryKey(epic=2, seq=6, suffix="a")


def test_normalize_strips_surrounding_whitespace():
    assert normalize("  1.2  ") == StoryKey(epic=1, seq=2)


def test_normalize_rejects_no_separator_between_key_and_trailing_text():
    with pytest.raises(MalformedStoryKeyError):
        normalize("1-23extra")


def test_normalize_rejects_non_key_text():
    with pytest.raises(MalformedStoryKeyError):
        normalize("story-identity")


def test_normalize_rejects_multi_letter_suffix():
    """The suffix token is a SINGLE letter -- a second trailing letter glued
    on with no separator is non-conforming, not a two-char suffix."""
    with pytest.raises(MalformedStoryKeyError):
        normalize("6.1ab")


def test_normalize_glued_suffix_with_trailing_slug():
    """The module's own headline motivating scenario: a letter-suffixed key
    (the harness's documented ``2-6a`` shape) AND trailing descriptive slug
    text in the same token, e.g. a real branch-segment/filename-slug form.
    The two existing cases test suffix-without-slug and slug-without-suffix
    separately -- this pins the combined case the whole module exists for."""
    key = normalize("2-6a-some-story-title")
    assert key == StoryKey(epic=2, seq=6, suffix="a")


def test_malformed_story_key_error_is_a_value_error():
    assert issubclass(MalformedStoryKeyError, ValueError)


def test_malformed_story_key_error_names_the_raw_input():
    with pytest.raises(MalformedStoryKeyError, match="story-identity"):
        normalize("story-identity")


def test_normalize_rejects_non_str_input():
    """A real footgun: YAML parses an unquoted ``1.2:`` feed key as the
    float ``1.2``, not the string ``"1.2"``. This must report, not crash
    with a raw ``AttributeError``."""
    with pytest.raises(MalformedStoryKeyError):
        normalize(1.2)  # type: ignore[arg-type]


# --- StoryKey: canonical __str__ + total ordering ---------------------------


def test_story_key_str_is_the_dot_form():
    assert str(StoryKey(epic=6, seq=1, suffix="a")) == "6.1a"
    assert str(StoryKey(epic=1, seq=2)) == "1.2"


def test_story_key_total_ordering():
    base = StoryKey(epic=6, seq=1)
    with_a = StoryKey(epic=6, seq=1, suffix="a")
    with_b = StoryKey(epic=6, seq=1, suffix="b")
    assert base < with_a < with_b


@pytest.mark.parametrize(
    "kwargs",
    [
        {"epic": -1, "seq": 1},
        {"epic": 1, "seq": -1},
        {"epic": 1, "seq": 1, "suffix": "ab"},
        {"epic": 1, "seq": 1, "suffix": "A"},
        {"epic": 1, "seq": 1, "suffix": "1"},
        # Unicode lowercase letters pass islower()/isalpha() but are NOT
        # a-z -- the guard must be an explicit ASCII range or this mints a
        # key normalize() can never round-trip.
        {"epic": 1, "seq": 1, "suffix": "ß"},
    ],
)
def test_story_key_post_init_rejects_invalid_direct_construction(kwargs):
    """``normalize()`` always produces a valid ``StoryKey``, but direct
    construction (bypassing it) must not silently accept an invalid one --
    matching ``model.py``'s ``Finding``/``Envelope`` convention of
    validating in ``__post_init__``, not just via one blessed constructor."""
    with pytest.raises(ValueError):
        StoryKey(**kwargs)


# --- render functions: one per external form --------------------------------


def test_render_functions_are_four_distinct_callables():
    functions = [
        render_feed_key,
        render_filename_slug,
        render_branch_segment,
        render_merge_subject,
    ]
    assert len({id(function) for function in functions}) == 4


def test_render_feed_key_is_the_dot_form():
    assert render_feed_key(StoryKey(epic=6, seq=1, suffix="a")) == "6.1a"


def test_render_filename_slug_is_the_hyphen_form():
    assert render_filename_slug(StoryKey(epic=6, seq=1, suffix="a")) == "6-1a"


def test_render_branch_segment_is_the_hyphen_form():
    assert render_branch_segment(StoryKey(epic=6, seq=1, suffix="a")) == "6-1a"


def test_render_filename_slug_and_branch_segment_agree_on_shape_only():
    """Same shape today (AD-23) -- but they must remain independently
    callable, distinct functions, not aliases of one another."""
    key = StoryKey(epic=1, seq=2)
    assert render_filename_slug(key) == render_branch_segment(key) == "1-2"
    assert render_filename_slug is not render_branch_segment


@pytest.mark.parametrize(
    "render",
    [render_feed_key, render_filename_slug, render_branch_segment],
    ids=lambda fn: fn.__name__,
)
def test_render_functions_reject_a_non_story_key(render):
    """``render_feed_key``'s bare ``str(key)`` would otherwise silently echo
    un-normalized input (``"6-1A"``) as if it were canonical -- the exact
    silent coercion this module exists to prevent -- and the hyphen forms
    would raise an incidental ``AttributeError`` instead of a typed one."""
    with pytest.raises(TypeError):
        render(  # type: ignore[arg-type]
            "6-1A"
        )


# --- merge-subject render/parse round-trip ----------------------------------

_KEY_SHAPES = [
    StoryKey(epic=1, seq=2),
    StoryKey(epic=6, seq=1, suffix="a"),
    StoryKey(epic=12, seq=34, suffix="b"),
]

_TEMPLATES = [
    "Merge {key} into main",
    "{key}",
    "bmad-loop/run-42/{key}-story-title into main",
]


@pytest.mark.parametrize("key", _KEY_SHAPES, ids=str)
@pytest.mark.parametrize("template", _TEMPLATES)
def test_merge_subject_round_trip(key, template):
    subject = render_merge_subject(key, template)
    assert parse_merge_subject(subject, template) == key


def test_render_merge_subject_substitutes_the_hyphen_form():
    subject = render_merge_subject(
        StoryKey(epic=6, seq=1, suffix="a"), "Merge {key} into main"
    )
    assert subject == "Merge 6-1a into main"


def test_render_merge_subject_rejects_a_template_without_the_placeholder():
    with pytest.raises(ValueError):
        render_merge_subject(StoryKey(epic=1, seq=2), "Merge into main")


def test_render_merge_subject_rejects_a_template_with_two_placeholders():
    with pytest.raises(ValueError):
        render_merge_subject(StoryKey(epic=1, seq=2), "{key} then {key}")


def test_parse_merge_subject_rejects_non_conforming_subject():
    with pytest.raises(MergeSubjectConformanceError):
        parse_merge_subject("totally different text", "Merge {key} into main")


def test_parse_merge_subject_rejects_a_malformed_extracted_key():
    with pytest.raises(MergeSubjectConformanceError):
        parse_merge_subject("Merge not-a-key into main", "Merge {key} into main")


def test_parse_merge_subject_rejects_a_malformed_template_too():
    """Wrapped the same way as every other failure mode -- a caller of
    ``parse_merge_subject`` never needs to catch a second exception type."""
    with pytest.raises(MergeSubjectConformanceError):
        parse_merge_subject("Merge 1-2 into main", "no placeholder here")


def test_merge_subject_conformance_error_is_a_value_error():
    assert issubclass(MergeSubjectConformanceError, ValueError)


def test_merge_subject_conformance_error_chains_the_original_failure():
    with pytest.raises(MergeSubjectConformanceError) as excinfo:
        parse_merge_subject("totally different text", "Merge {key} into main")
    assert excinfo.value.__cause__ is not None


def test_merge_subject_conformance_error_carries_a_real_mrs_ident_002_finding():
    """MRS-IDENT-002 is a registered, classified code (findings.py,
    verdict.py) -- this is its real construction site, not just a docstring
    claim. A caller extracts ``.finding`` the same way ``resolve_feed``'s
    ``.findings`` tuple is used."""
    with pytest.raises(MergeSubjectConformanceError) as excinfo:
        parse_merge_subject("totally different text", "Merge {key} into main")
    finding = excinfo.value.finding
    assert finding.code == "MRS-IDENT-002"
    assert verdict.compute_verdict([finding]) == Verdict.UNEVALUABLE


def test_parse_merge_subject_rejects_non_str_subject():
    with pytest.raises(MergeSubjectConformanceError):
        parse_merge_subject(123, "Merge {key} into main")  # type: ignore[arg-type]


def test_render_merge_subject_rejects_non_str_template():
    with pytest.raises(ValueError):
        render_merge_subject(StoryKey(epic=1, seq=2), 123)  # type: ignore[arg-type]


def test_parse_merge_subject_rejects_non_str_template():
    with pytest.raises(MergeSubjectConformanceError):
        parse_merge_subject("Merge 1-2 into main", 123)  # type: ignore[arg-type]


# --- resolve_feed(): AD-38 completeness --------------------------------------


def test_resolve_feed_returns_a_feed_resolution():
    assert isinstance(resolve_feed(["1.1"]), FeedResolution)


def test_resolve_feed_all_resolve():
    result = resolve_feed(["1.1", "1.2"])
    assert result.total == 2
    assert result.resolved == (StoryKey(1, 1), StoryKey(1, 2))
    assert result.unresolved == ()
    assert result.findings == ()


def test_resolve_feed_partial_failure_reports_raw_total_and_finding():
    result = resolve_feed(["1.1", "not-a-key", "1.2"])
    assert result.total == 3
    assert result.resolved == (StoryKey(1, 1), StoryKey(1, 2))
    assert result.unresolved == ("not-a-key",)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "MRS-IDENT-001"
    assert finding.path == "not-a-key"
    assert "not-a-key" in finding.message


def test_resolve_feed_partial_failure_classifies_unevaluable():
    result = resolve_feed(["1.1", "not-a-key"])
    assert verdict.compute_verdict(result.findings) == Verdict.UNEVALUABLE


def test_resolve_feed_total_is_the_raw_pre_parse_count():
    """F-13's fix: ``total`` is ``len(raw_keys)``, never the post-parse
    count -- a silently-dropped entry must not report a false "N of N"."""
    result = resolve_feed(["1.1", "also-not-a-key", "still-not-a-key"])
    assert result.total == 3
    assert len(result.resolved) == 1
    assert len(result.unresolved) == 2
    assert len(result.findings) == 2


def test_resolve_feed_multi_failure_per_item_attribution():
    """Each unresolved entry and its ``Finding`` must name the SAME raw
    key it corresponds to, by position -- not just match in aggregate
    count. A regression that scrambled which finding names which raw key
    would pass a counts-only assertion."""
    result = resolve_feed(["also-not-a-key", "still-not-a-key"])
    assert result.unresolved == ("also-not-a-key", "still-not-a-key")
    assert [finding.path for finding in result.findings] == [
        "also-not-a-key",
        "still-not-a-key",
    ]
    assert "also-not-a-key" in result.findings[0].message
    assert "still-not-a-key" in result.findings[1].message


def test_resolve_feed_reports_non_str_entries_instead_of_crashing():
    """A real footgun: an unquoted YAML feed key like ``1.2:`` parses as
    the float ``1.2``, not the string ``"1.2"``. A non-str entry must be
    reported in ``unresolved``/``findings`` (repr'd), never raise -- and
    because ``repr(1.2)`` is the quoteless, valid-looking ``1.2``, the
    finding's message must also name the type, or the diagnostic would
    claim a well-formed key failed to resolve."""
    result = resolve_feed(["1.1", 1.2, "1.3"])  # type: ignore[list-item]
    assert result.total == 3
    assert result.resolved == (StoryKey(1, 1), StoryKey(1, 3))
    assert result.unresolved == ("1.2",)
    assert result.findings[0].path == "1.2"
    assert "(float)" in result.findings[0].message


def test_resolve_feed_rejects_a_bare_str_feed():
    """A ``str`` satisfies ``Sequence[str]``, so a single feed key passed
    where a list was meant would otherwise shred into per-character garbage
    findings (``total=3``, unresolved ``('1', '.', '2')``) -- the same
    footgun ``model.py``'s ``Envelope`` guards ``assumptions`` against."""
    with pytest.raises(TypeError):
        resolve_feed("1.2")


def test_resolve_feed_empty_feed_is_a_clean_zero_of_zero():
    """Pinned deliberately, not left accidental: an empty feed resolves to
    a clean 0-of-0. Whether an empty feed is itself an error is the
    caller's policy (the loop's completeness gate), not identity's."""
    result = resolve_feed([])
    assert result.total == 0
    assert result.resolved == ()
    assert result.unresolved == ()
    assert result.findings == ()
    assert verdict.compute_verdict(result.findings) == Verdict.CLEAN


@pytest.mark.parametrize(
    "kwargs",
    [
        # total fabricated: 5 raw entries claimed, only 1 accounted for.
        {
            "resolved": (StoryKey(1, 1),),
            "unresolved": (),
            "total": 5,
            "findings": (),
        },
        # findings not 1:1 with unresolved.
        {
            "resolved": (),
            "unresolved": ("not-a-key",),
            "total": 1,
            "findings": (),
        },
    ],
)
def test_feed_resolution_post_init_rejects_fabricated_completeness(kwargs):
    """``FeedResolution`` is AD-38's completeness attestation -- a directly
    constructed instance (bypassing ``resolve_feed()``) must not be able to
    claim a false "N of M", matching ``StoryKey``/``model.py``'s
    construct-time validation convention."""
    with pytest.raises(ValueError):
        FeedResolution(**kwargs)
