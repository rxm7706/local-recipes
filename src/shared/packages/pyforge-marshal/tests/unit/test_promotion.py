"""Unit tests for ``pyforge.marshal.core.promotion`` (Story 4.1,
AD-4/AD-12/AD-13/AD-24/AD-29/AD-33) -- pure, no I/O, no fixtures touching
disk or git; every input is a plain value.
"""

from __future__ import annotations

from pyforge.marshal.core.identity import StoryKey
from pyforge.marshal.core.promotion import (
    SpecCandidate,
    classify_promotion_candidates,
    count_conforming_subjects,
    extract_story_key_from_bmadloop_merge_subject,
    extract_story_key_from_github_merge_subject,
    is_valid_spec_text,
    merged_story_keys,
)

_TEMPLATE = "Merge {key} into main"

_VALID_SPEC = "---\ntitle: 'x'\nstatus: 'shipped'\n---\n\nbody\n"

# Real subject strings pulled verbatim from `git log --merges --format=%s`
# in THIS repo (the spec-amendment's own motivating evidence) -- pinned
# here so the regression is proven against observed data, not just
# constructed happy-path strings (Blind Hunter's own finding on the
# original pass: "only the tautological case where the template and the
# fixture agree by construction").
_REAL_SUBJECT_2_3 = "Merge pull request #269 from rxm7706/marshal/2-3-frozen-surface-scope-check"
_REAL_SUBJECT_3_8 = "Merge pull request #266 from rxm7706/marshal/3-8-stage-bound-durability"
_REAL_SUBJECT_AMBIGUOUS = "Merge pull request #265 from rxm7706/marshal/refresh-dashboard-3-7"
_REAL_SUBJECT_NON_STORY_1 = "Merge pull request #268 from rxm7706/marshal/epic-3-retro"
_REAL_SUBJECT_NON_STORY_2 = (
    "Merge bmad-loop/20260803-023308-65b7/3-7-escalation-deferral-and-resume "
    "into loop/pyforge-marshal (bmad-loop)"
)
_REAL_SUBJECT_NOT_A_MERGE_1 = "fastmcp-v4"
_REAL_SUBJECT_NOT_A_MERGE_2 = 'pixi update requires-pixi = ">=0.75.0"'


# --- extract_story_key_from_github_merge_subject -----------------------------


def test_extracts_key_from_real_github_merge_subject_2_3():
    assert extract_story_key_from_github_merge_subject(_REAL_SUBJECT_2_3) == StoryKey(2, 3)


def test_extracts_key_from_real_github_merge_subject_3_8():
    assert extract_story_key_from_github_merge_subject(_REAL_SUBJECT_3_8) == StoryKey(3, 8)


def test_ambiguous_real_subject_with_non_leading_digits_is_rejected():
    """`"marshal/refresh-dashboard-3-7"`'s digits appear but NOT as the
    branch segment's LEADING token -- `core.identity.normalize()` matches
    only at position 0, so this correctly returns None rather than
    extracting 3.7. This is the tricky case the spec's amendment calls
    out by name."""
    assert extract_story_key_from_github_merge_subject(_REAL_SUBJECT_AMBIGUOUS) is None


def test_real_non_story_merge_subject_returns_none():
    assert extract_story_key_from_github_merge_subject(_REAL_SUBJECT_NON_STORY_1) is None


def test_non_github_shaped_merge_subject_returns_none():
    assert extract_story_key_from_github_merge_subject(_REAL_SUBJECT_NON_STORY_2) is None


def test_non_merge_subject_returns_none():
    assert extract_story_key_from_github_merge_subject(_REAL_SUBJECT_NOT_A_MERGE_1) is None
    assert extract_story_key_from_github_merge_subject(_REAL_SUBJECT_NOT_A_MERGE_2) is None


# --- extract_story_key_from_bmadloop_merge_subject ---------------------------
#
# Post-merge finding (2026-08-06): closing out Epic 2 with a real
# `marshal deploy promote` run found five of its seven stories (2.1/2.2/
# 2.4/2.5/2.6) landed via bmad-loop's own shared `loop/pyforge-marshal`
# branch, not a per-story branch -- matching NEITHER of the two patterns
# above. These fixtures are real subjects pulled verbatim from this repo's
# own `git log --merges --format=%s`, the same discipline the original
# GitHub-pattern fixtures above already follow.


def test_extract_story_key_from_bmadloop_merge_subject_parses_a_real_one():
    subject = (
        "Merge bmad-loop/20260803-023308-65b7/2-4-doc-only-story-classification "
        "into loop/pyforge-marshal (bmad-loop)"
    )
    assert extract_story_key_from_bmadloop_merge_subject(subject) == StoryKey(2, 4)


def test_extract_story_key_from_bmadloop_merge_subject_parses_a_different_project():
    """Not marshal-specific -- every project in this factory uses the same
    bmad-loop merge shape (verified against pyforge-warden's own history)."""
    subject = (
        "Merge bmad-loop/20260724-042801-7c01/6-7-epss-feed-the-min-epss-gate "
        "into loop/pyforge-warden (bmad-loop)"
    )
    assert extract_story_key_from_bmadloop_merge_subject(subject) == StoryKey(6, 7)


def test_extract_story_key_from_bmadloop_merge_subject_returns_none_for_github_shape():
    assert extract_story_key_from_bmadloop_merge_subject(_REAL_SUBJECT_2_3) is None


def test_extract_story_key_from_bmadloop_merge_subject_returns_none_for_non_merge():
    assert extract_story_key_from_bmadloop_merge_subject(_REAL_SUBJECT_NOT_A_MERGE_1) is None


# --- merged_story_keys -------------------------------------------------------


def test_merged_story_keys_parses_conforming_subjects():
    subjects = ("Merge 1.2 into main", "Merge 3.8 into main")
    assert merged_story_keys(subjects, _TEMPLATE) == frozenset(
        {StoryKey(1, 2), StoryKey(3, 8)}
    )


def test_merged_story_keys_skips_a_non_story_merge_subject():
    """A commit subject that isn't a story merge at all -- e.g. this
    repo's own real history ("fastmcp-v4", "pixi update requires-pixi") --
    is skipped, never a hard failure for the whole scan."""
    subjects = (
        "fastmcp-v4",
        "pixi update requires-pixi = \">=0.75.0\"",
        "Merge 2.3 into main",
    )
    assert merged_story_keys(subjects, _TEMPLATE) == frozenset({StoryKey(2, 3)})


def test_merged_story_keys_empty_subjects_returns_empty_set():
    assert merged_story_keys((), _TEMPLATE) == frozenset()


def test_merged_story_keys_deduplicates_repeated_subjects():
    subjects = ("Merge 1.2 into main", "Merge 1.2 into main")
    assert merged_story_keys(subjects, _TEMPLATE) == frozenset({StoryKey(1, 2)})


def test_merged_story_keys_recognizes_real_github_merge_subjects_too():
    """The spec-amendment's own regression: this repo's real merge history
    is entirely GitHub PR-merge subjects, never the templated form -- both
    must be recognized by the SAME `merged_story_keys` call."""
    subjects = (_REAL_SUBJECT_2_3, _REAL_SUBJECT_3_8, _REAL_SUBJECT_AMBIGUOUS)
    assert merged_story_keys(subjects, _TEMPLATE) == frozenset({StoryKey(2, 3), StoryKey(3, 8)})


def test_merged_story_keys_recognizes_real_bmadloop_merge_subjects_too():
    """The post-merge finding's own regression: a repo that lands stories
    via BOTH manual GitHub PRs and bmad-loop runs must recognize both
    shapes in the same `merged_story_keys` call, alongside a genuine
    non-story merge (an epic-retro PR) that matches neither."""
    bmadloop_subject = (
        "Merge bmad-loop/20260803-023308-65b7/2-4-doc-only-story-classification "
        "into loop/pyforge-marshal (bmad-loop)"
    )
    subjects = (_REAL_SUBJECT_2_3, bmadloop_subject, _REAL_SUBJECT_NON_STORY_1)
    assert merged_story_keys(subjects, _TEMPLATE) == frozenset({StoryKey(2, 3), StoryKey(2, 4)})


def test_merged_story_keys_tries_templated_pattern_before_github_pattern():
    """A subject conforming to the templated form is still recognized even
    though it would also superficially resemble neither GitHub shape."""
    subjects = ("Merge 5.5 into main",)
    assert merged_story_keys(subjects, _TEMPLATE) == frozenset({StoryKey(5, 5)})


# --- count_conforming_subjects ------------------------------------------------


def test_count_conforming_subjects_counts_both_patterns_not_deduplicated():
    subjects = (
        "Merge 1.2 into main",
        _REAL_SUBJECT_2_3,
        _REAL_SUBJECT_2_3,  # same key twice -- must still count as 2
        _REAL_SUBJECT_AMBIGUOUS,  # conforms to neither -- not counted
        _REAL_SUBJECT_NOT_A_MERGE_1,
    )
    assert count_conforming_subjects(subjects, _TEMPLATE) == 3


def test_count_conforming_subjects_zero_for_no_conforming_subjects():
    subjects = (_REAL_SUBJECT_NOT_A_MERGE_1, _REAL_SUBJECT_NOT_A_MERGE_2)
    assert count_conforming_subjects(subjects, _TEMPLATE) == 0


# --- is_valid_spec_text -------------------------------------------------------


def test_is_valid_spec_text_true_for_frontmatter_with_status():
    assert is_valid_spec_text(_VALID_SPEC) is True


def test_is_valid_spec_text_false_for_none():
    assert is_valid_spec_text(None) is False


def test_is_valid_spec_text_false_for_empty_string():
    assert is_valid_spec_text("") is False


def test_is_valid_spec_text_false_for_whitespace_only():
    assert is_valid_spec_text("   \n\n  ") is False


def test_is_valid_spec_text_false_for_no_frontmatter():
    assert is_valid_spec_text("just some body text, no frontmatter at all\n") is False


def test_is_valid_spec_text_false_for_frontmatter_missing_status():
    assert is_valid_spec_text("---\ntitle: 'x'\n---\n\nbody\n") is False


def test_is_valid_spec_text_false_for_unterminated_frontmatter():
    assert is_valid_spec_text("---\nstatus: 'shipped'\nno closing fence\n") is False


def test_is_valid_spec_text_false_for_status_as_a_bare_substring_not_a_key():
    """Review finding: the prior check was a raw substring test, matching
    `"status:"` anywhere in the frontmatter -- including as PART of a
    different key's name. `substatus:` is not `status:`."""
    assert is_valid_spec_text("---\ntitle: 'x'\nsubstatus: 'draft'\n---\n\nbody\n") is False


def test_is_valid_spec_text_false_for_status_inside_a_comment():
    text = "---\ntitle: 'x'\n# a comment mentioning status: here\n---\n\nbody\n"
    assert is_valid_spec_text(text) is False


def test_is_valid_spec_text_true_for_status_key_regardless_of_line_position():
    assert (
        is_valid_spec_text("---\nstatus: 'draft'\ntitle: 'x'\n---\n\nbody\n") is True
    )


# --- classify_promotion_candidates -------------------------------------------


def test_durable_candidate_with_valid_spec_is_promoted():
    key = StoryKey(1, 2)
    candidate = SpecCandidate(story_key=key, path="spec-1-2.md", text=_VALID_SPEC)

    plan = classify_promotion_candidates(
        candidates=(candidate,),
        merged_keys=frozenset({key}),
        already_promoted=frozenset(),
    )

    assert plan.to_promote == (candidate,)
    assert plan.gaps == ()


def test_already_promoted_candidate_is_skipped_not_repromoted():
    key = StoryKey(3, 8)
    candidate = SpecCandidate(story_key=key, path="spec-3-8.md", text=_VALID_SPEC)

    plan = classify_promotion_candidates(
        candidates=(candidate,),
        merged_keys=frozenset({key}),
        already_promoted=frozenset({key}),
    )

    assert plan.to_promote == ()
    assert plan.gaps == ()


def test_merged_story_with_no_matching_spec_is_a_gap():
    key = StoryKey(4, 1)

    plan = classify_promotion_candidates(
        candidates=(),
        merged_keys=frozenset({key}),
        already_promoted=frozenset(),
    )

    assert plan.to_promote == ()
    assert len(plan.gaps) == 1
    assert plan.gaps[0].code == "MRS-DEPLOY-001"
    assert "4.1" in plan.gaps[0].message


def test_merged_story_with_invalid_spec_is_a_gap_never_promoted():
    key = StoryKey(2, 3)
    candidate = SpecCandidate(story_key=key, path="spec-2-3.md", text="")

    plan = classify_promotion_candidates(
        candidates=(candidate,),
        merged_keys=frozenset({key}),
        already_promoted=frozenset(),
    )

    assert plan.to_promote == ()
    assert len(plan.gaps) == 1
    assert plan.gaps[0].code == "MRS-DEPLOY-002"
    assert plan.gaps[0].path == "spec-2-3.md"


def test_not_yet_merged_story_produces_nothing_in_either_bucket():
    """A key not in merged_keys is correctly not yet a candidate at all --
    not promoted, not a gap."""
    key = StoryKey(5, 1)
    candidate = SpecCandidate(story_key=key, path="spec-5-1.md", text=_VALID_SPEC)

    plan = classify_promotion_candidates(
        candidates=(candidate,),
        merged_keys=frozenset(),
        already_promoted=frozenset(),
    )

    assert plan.to_promote == ()
    assert plan.gaps == ()


def test_zero_candidates_and_zero_merged_keys_is_a_clean_empty_plan():
    plan = classify_promotion_candidates(
        candidates=(), merged_keys=frozenset(), already_promoted=frozenset()
    )
    assert plan.to_promote == ()
    assert plan.gaps == ()


def test_mixed_batch_promotes_valid_and_gaps_invalid_independently():
    good_key = StoryKey(1, 1)
    bad_key = StoryKey(1, 2)
    missing_key = StoryKey(1, 3)
    good = SpecCandidate(story_key=good_key, path="spec-1-1.md", text=_VALID_SPEC)
    bad = SpecCandidate(story_key=bad_key, path="spec-1-2.md", text=None)

    plan = classify_promotion_candidates(
        candidates=(good, bad),
        merged_keys=frozenset({good_key, bad_key, missing_key}),
        already_promoted=frozenset(),
    )

    assert plan.to_promote == (good,)
    codes = sorted(finding.code for finding in plan.gaps)
    assert codes == ["MRS-DEPLOY-001", "MRS-DEPLOY-002"]


def test_plan_order_is_deterministic_by_sorted_story_key():
    key_a = StoryKey(1, 1)
    key_b = StoryKey(2, 1)
    candidate_a = SpecCandidate(story_key=key_a, path="spec-1-1.md", text=_VALID_SPEC)
    candidate_b = SpecCandidate(story_key=key_b, path="spec-2-1.md", text=_VALID_SPEC)

    # Deliberately supplied out of key order.
    plan = classify_promotion_candidates(
        candidates=(candidate_b, candidate_a),
        merged_keys=frozenset({key_b, key_a}),
        already_promoted=frozenset(),
    )

    assert plan.to_promote == (candidate_a, candidate_b)
