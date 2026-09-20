"""Unit tests for ``pyforge.marshal.core.promotion`` (Story 4.1,
AD-4/AD-12/AD-13/AD-24/AD-29/AD-33) -- pure, no I/O, no fixtures touching
disk or git; every input is a plain value.
"""

from __future__ import annotations

from pyforge.marshal.core.identity import StoryKey, render_merge_subject
from pyforge.marshal.core.promotion import (
    SpecCandidate,
    classify_promotion_candidates,
    corroborated_merged_story_keys,
    count_conforming_subjects,
    extract_story_key_from_bmadloop_merge_subject,
    extract_story_key_from_github_merge_subject,
    is_valid_spec_text,
    marshal_native_merged_keys,
    merged_story_keys,
    read_spec_status,
)

_TEMPLATE = "Merge {key} into main"
_PROJECT_SLUG = "pyforge-marshal"

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
    "Merge bmad-loop/20260803-023308-65b7/3-7-escalation-deferral-and-resume into loop/pyforge-marshal (bmad-loop)"
)
_REAL_SUBJECT_NOT_A_MERGE_1 = "fastmcp-v4"
_REAL_SUBJECT_NOT_A_MERGE_2 = 'pixi update requires-pixi = ">=0.75.0"'

# Live cross-project collision fixtures (2026-08-15): PR #274 is a real
# MARSHAL story merge whose branch numerically collides with mason's own
# story 4.2 -- the exact subject `marshal land pyforge-mason` misread as
# "already landed". PR #441 is a routine dependency-bump branch with no
# story association at all, previously mis-parsed as a bogus key by the
# same unscoped classifier.
_REAL_SUBJECT_MARSHAL_4_2 = "Merge pull request #274 from rxm7706/marshal/4-2-teardown-reachability-spec-recovery"
_REAL_SUBJECT_PIXI_BUMP = "Merge pull request #441 from rxm7706/2026-08-11-Pixi-v0.76.2"
_MASON_PROJECT_SLUG = "pyforge-mason"


# --- extract_story_key_from_github_merge_subject -----------------------------


def test_extracts_key_from_real_github_merge_subject_2_3():
    assert extract_story_key_from_github_merge_subject(_REAL_SUBJECT_2_3, _PROJECT_SLUG) == StoryKey(2, 3)


def test_extracts_key_from_real_github_merge_subject_3_8():
    assert extract_story_key_from_github_merge_subject(_REAL_SUBJECT_3_8, _PROJECT_SLUG) == StoryKey(3, 8)


def test_ambiguous_real_subject_with_non_leading_digits_is_rejected():
    """`"marshal/refresh-dashboard-3-7"`'s digits appear but NOT as the
    branch segment's LEADING token -- `core.identity.normalize()` matches
    only at position 0, so this correctly returns None rather than
    extracting 3.7. This is the tricky case the spec's amendment calls
    out by name."""
    assert extract_story_key_from_github_merge_subject(_REAL_SUBJECT_AMBIGUOUS, _PROJECT_SLUG) is None


def test_real_non_story_merge_subject_returns_none():
    assert extract_story_key_from_github_merge_subject(_REAL_SUBJECT_NON_STORY_1, _PROJECT_SLUG) is None


def test_non_github_shaped_merge_subject_returns_none():
    assert extract_story_key_from_github_merge_subject(_REAL_SUBJECT_NON_STORY_2, _PROJECT_SLUG) is None


def test_non_merge_subject_returns_none():
    assert extract_story_key_from_github_merge_subject(_REAL_SUBJECT_NOT_A_MERGE_1, _PROJECT_SLUG) is None
    assert extract_story_key_from_github_merge_subject(_REAL_SUBJECT_NOT_A_MERGE_2, _PROJECT_SLUG) is None


def test_github_pattern_rejects_a_different_projects_story_key_collision():
    """The live bug (2026-08-15): PR #274 is a real MARSHAL story merge.
    Querying it under mason's own project_slug must return None, not
    StoryKey(4, 2) -- the exact false positive that made `marshal land
    pyforge-mason` report story 4.2 as already landed."""
    assert extract_story_key_from_github_merge_subject(_REAL_SUBJECT_MARSHAL_4_2, _MASON_PROJECT_SLUG) is None


def test_github_pattern_still_recognizes_the_owning_projects_own_key():
    """The same subject, queried under its OWN project_slug, still
    resolves correctly -- the fix narrows false positives, it does not
    break real matches."""
    assert extract_story_key_from_github_merge_subject(_REAL_SUBJECT_MARSHAL_4_2, _PROJECT_SLUG) == StoryKey(4, 2)


def test_github_pattern_rejects_an_empty_station_rather_than_matching_any_branch():
    """Edge Case Hunter finding (2026-08-15): an empty station (project_slug
    `""` or exactly `"pyforge-"`) must never degrade to `branch.startswith("/")`
    -- a subject with an empty leading branch segment (double slash) would
    otherwise pass, reopening a narrow version of the collision this
    scoping exists to close."""
    evil_subject = "Merge pull request #1 from a//4-2-evil"
    assert extract_story_key_from_github_merge_subject(evil_subject, "") is None
    assert extract_story_key_from_github_merge_subject(evil_subject, "pyforge-") is None


def test_github_pattern_rejects_an_unrelated_branch_for_any_project():
    """A routine dependency-bump branch with no story association at all
    (PR #441) must never resolve to a key for ANY project."""
    assert extract_story_key_from_github_merge_subject(_REAL_SUBJECT_PIXI_BUMP, _PROJECT_SLUG) is None
    assert extract_story_key_from_github_merge_subject(_REAL_SUBJECT_PIXI_BUMP, _MASON_PROJECT_SLUG) is None


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
        "Merge bmad-loop/20260803-023308-65b7/2-4-doc-only-story-classification into loop/pyforge-marshal (bmad-loop)"
    )
    assert extract_story_key_from_bmadloop_merge_subject(subject, _PROJECT_SLUG) == StoryKey(2, 4)


def test_extract_story_key_from_bmadloop_merge_subject_parses_a_different_project():
    """Not marshal-specific -- every project in this factory uses the same
    bmad-loop merge shape (verified against pyforge-warden's own history) --
    as long as the CALLER passes the matching project_slug."""
    subject = (
        "Merge bmad-loop/20260724-042801-7c01/6-7-epss-feed-the-min-epss-gate into loop/pyforge-warden (bmad-loop)"
    )
    assert extract_story_key_from_bmadloop_merge_subject(subject, "pyforge-warden") == StoryKey(6, 7)


def test_extract_story_key_from_bmadloop_merge_subject_rejects_a_different_projects_merge():
    """Live cross-project collision this scoping exists to prevent
    (post-merge finding, 2026-08-06): pyforge-warden's own Story 6.8 merge
    must NOT be read as pyforge-marshal's Story 6.8 just because the key
    segment happens to parse -- the merge TARGET has to match too."""
    warden_subject = (
        "Merge bmad-loop/20260724-055419-3c0e/6-8-baseline-grandfathering into loop/pyforge-warden (bmad-loop)"
    )
    assert extract_story_key_from_bmadloop_merge_subject(warden_subject, _PROJECT_SLUG) is None


def test_extract_story_key_from_bmadloop_merge_subject_returns_none_for_github_shape():
    assert extract_story_key_from_bmadloop_merge_subject(_REAL_SUBJECT_2_3, _PROJECT_SLUG) is None


def test_extract_story_key_from_bmadloop_merge_subject_returns_none_for_non_merge():
    assert extract_story_key_from_bmadloop_merge_subject(_REAL_SUBJECT_NOT_A_MERGE_1, _PROJECT_SLUG) is None


# --- merged_story_keys -------------------------------------------------------


def test_merged_story_keys_parses_conforming_subjects():
    subjects = ("Merge 1.2 into main", "Merge 3.8 into main")
    assert merged_story_keys(subjects, _TEMPLATE, _PROJECT_SLUG) == frozenset({StoryKey(1, 2), StoryKey(3, 8)})


def test_merged_story_keys_skips_a_non_story_merge_subject():
    """A commit subject that isn't a story merge at all -- e.g. this
    repo's own real history ("fastmcp-v4", "pixi update requires-pixi") --
    is skipped, never a hard failure for the whole scan."""
    subjects = (
        "fastmcp-v4",
        'pixi update requires-pixi = ">=0.75.0"',
        "Merge 2.3 into main",
    )
    assert merged_story_keys(subjects, _TEMPLATE, _PROJECT_SLUG) == frozenset({StoryKey(2, 3)})


def test_merged_story_keys_empty_subjects_returns_empty_set():
    assert merged_story_keys((), _TEMPLATE, _PROJECT_SLUG) == frozenset()


def test_merged_story_keys_does_not_leak_another_projects_story_into_mason():
    """The live bug, exercised through the public `merged_story_keys` entry
    point every caller (`marshal land`, `marshal deploy batch-pr`) actually
    uses: a marshal PR-merge subject must never contribute a mason key,
    even mixed alongside mason's OWN real merges."""
    subjects = (_REAL_SUBJECT_MARSHAL_4_2, _REAL_SUBJECT_PIXI_BUMP)
    assert merged_story_keys(subjects, _TEMPLATE, _MASON_PROJECT_SLUG) == frozenset()
    assert merged_story_keys(subjects, _TEMPLATE, _PROJECT_SLUG) == frozenset({StoryKey(4, 2)})


def test_merged_story_keys_land_slug_branch_shape_recognized_for_owning_station():
    """Story 20.10: ``land/<station>-<epic>-<seq>`` recovery branches embedded
    in GitHub PR merge subjects are recognized via
    ``classify_branch_name`` at the grammar boundary."""
    subject = "Merge pull request #516 from rxm7706/land/mason-4-4"
    assert merged_story_keys((subject,), _TEMPLATE, _MASON_PROJECT_SLUG) == frozenset({StoryKey(4, 4)})
    assert merged_story_keys((subject,), _TEMPLATE, _PROJECT_SLUG) == frozenset()


def test_merged_story_keys_recognizes_recovery_and_story_direct_subjects():
    """Story 50.4/FR-191 CAP-247: ``merged_story_keys`` scans plain commit
    subjects with no branch info available to corroborate -- the recovery
    shape carries its own station token in the text and still classifies,
    but the bare ``Story 8.2: ...`` direct-commit subject alone no longer
    does (this is the exact shape steward's real ``Story 48.2:``/
    ``Story 48.4:`` subjects used to poison marshal's own ledger with)."""
    subjects = (
        "recover marshal 10-1 (Copier engine wrapper — the single seam)",
        "Story 8.2: region parser -- span discovery, nesting rejection, fence awareness",
    )
    assert merged_story_keys(subjects, _TEMPLATE, _PROJECT_SLUG) == frozenset({StoryKey(10, 1)})


def test_branch_story_merge_confirmed_by_grammar_when_patch_id_alone_fails():
    branch = "land/marshal-10-1-recovery"
    subjects = ("recover marshal 10-1 (Copier engine wrapper — the single seam)",)
    from pyforge.marshal.core.promotion import branch_story_merge_confirmed_by_grammar

    assert branch_story_merge_confirmed_by_grammar(
        branch,
        StoryKey(10, 1),
        subjects,
        _TEMPLATE,
        _PROJECT_SLUG,
    )
    assert not branch_story_merge_confirmed_by_grammar(
        branch,
        StoryKey(10, 1),
        subjects,
        _TEMPLATE,
        _MASON_PROJECT_SLUG,
    )


def test_merged_story_keys_deduplicates_repeated_subjects():
    subjects = ("Merge 1.2 into main", "Merge 1.2 into main")
    assert merged_story_keys(subjects, _TEMPLATE, _PROJECT_SLUG) == frozenset({StoryKey(1, 2)})


def test_merged_story_keys_recognizes_real_github_merge_subjects_too():
    """The spec-amendment's own regression: this repo's real merge history
    is entirely GitHub PR-merge subjects, never the templated form -- both
    must be recognized by the SAME `merged_story_keys` call."""
    subjects = (_REAL_SUBJECT_2_3, _REAL_SUBJECT_3_8, _REAL_SUBJECT_AMBIGUOUS)
    assert merged_story_keys(subjects, _TEMPLATE, _PROJECT_SLUG) == frozenset({StoryKey(2, 3), StoryKey(3, 8)})


def test_merged_story_keys_recognizes_real_bmadloop_merge_subjects_too():
    """The post-merge finding's own regression: a repo that lands stories
    via BOTH manual GitHub PRs and bmad-loop runs must recognize both
    shapes in the same `merged_story_keys` call, alongside a genuine
    non-story merge (an epic-retro PR) that matches neither."""
    bmadloop_subject = (
        "Merge bmad-loop/20260803-023308-65b7/2-4-doc-only-story-classification into loop/pyforge-marshal (bmad-loop)"
    )
    subjects = (_REAL_SUBJECT_2_3, bmadloop_subject, _REAL_SUBJECT_NON_STORY_1)
    assert merged_story_keys(subjects, _TEMPLATE, _PROJECT_SLUG) == frozenset({StoryKey(2, 3), StoryKey(2, 4)})


def test_merged_story_keys_tries_templated_pattern_before_github_pattern():
    """A subject conforming to the templated form is still recognized even
    though it would also superficially resemble neither GitHub shape."""
    subjects = ("Merge 5.5 into main",)
    assert merged_story_keys(subjects, _TEMPLATE, _PROJECT_SLUG) == frozenset({StoryKey(5, 5)})


# --- known_keys scoping for the templated shape (Story 35.1,
# spec-marshal-templated-merge-subject-cross-project-collision CAP-1) ---------


def test_merged_story_keys_templated_form_unscoped_when_known_keys_omitted():
    """The live bug, still reproducible by omission: the templated shape
    carries no station token in its own text, so with no `known_keys`
    corroboration a bare `"Merge 22.5 into main"` subject is accepted for
    ANY project_slug -- the exact cross-station collision this Story
    closes when the caller opts in."""
    subjects = ("Merge 22.5 into main",)
    assert merged_story_keys(subjects, _TEMPLATE, "pyforge-doctor") == frozenset({StoryKey(22, 5)})
    assert merged_story_keys(subjects, _TEMPLATE, _MASON_PROJECT_SLUG) == frozenset({StoryKey(22, 5)})


def test_merged_story_keys_templated_form_filters_to_known_keys():
    """The fix: with `known_keys` supplied, a templated-form match is kept
    only when its key is a member -- corroboration a project's own tracked
    ledger provides, since the subject text cannot."""
    subjects = ("Merge 22.5 into main", "Merge 22.11 into main")
    doctors_own_keys = frozenset({StoryKey(22, 1), StoryKey(22, 5), StoryKey(22, 6)})
    assert merged_story_keys(subjects, _TEMPLATE, "pyforge-doctor", known_keys=doctors_own_keys) == frozenset(
        {StoryKey(22, 5)}
    )


def test_merged_story_keys_templated_form_known_keys_empty_set_excludes_everything():
    """An empty `known_keys` (a project with no tracked stories at all, or a
    ledger that failed to load) trusts nothing from the templated shape --
    fails closed, not open."""
    subjects = ("Merge 1.1 into main",)
    assert merged_story_keys(subjects, _TEMPLATE, _PROJECT_SLUG, known_keys=frozenset()) == frozenset()


def test_merged_story_keys_known_keys_does_not_affect_already_scoped_shapes():
    """`known_keys` only gates the templated shape -- GitHub PR-merge,
    bmad-loop-native, recovery, and story-direct subjects already carry
    real `project_slug` scoping and must be unaffected by an unrelated
    (even empty) `known_keys`."""
    subjects = (_REAL_SUBJECT_2_3, _REAL_SUBJECT_3_8)
    assert merged_story_keys(subjects, _TEMPLATE, _PROJECT_SLUG, known_keys=frozenset()) == frozenset(
        {StoryKey(2, 3), StoryKey(3, 8)}
    )


# --- Story 50.4/FR-191 CAP-247: the station-scoped `{slug}` template and
# branch-corroborated story-direct commits -------------------------------------

# Real subjects pulled verbatim from `git log origin/main --format='%s'`
# (2026-09-18) -- the exact 2026-09-18 fixture this story's spec names.
_SLUG_SCOPED_TEMPLATE = "Merge {slug}/{key} into main"

_ATLAS_23_SUBJECTS = tuple(f"Merge 23-{n} into main" for n in range(1, 10))
_HERALD_23_SUBJECTS = (
    "Merge pyforge-herald/23-1 into main",
    "Merge pyforge-herald/23-2 into main",
    "Merge pyforge-herald/23-5 into main",
    "Merge pyforge-herald/23-6 into main",
)
_STEWARD_DIRECT_SUBJECT_48_2 = "Story 48.2: R-18 platform chart sizing rewrite."
_STEWARD_DIRECT_SUBJECT_48_4 = "Story 48.4: R-20 secrets profile for platform deploy."


def test_merged_story_keys_slug_scoped_template_never_inherits_a_foreign_stations_landings():
    """The motivating 2026-09-18 incident: atlas's seven unscoped `Merge
    23-N into main` commits must NOT read as herald's own 23.1/23.2/23.5/
    23.6 once herald renders/parses under the new `{slug}`-scoped default
    template -- a foreign-station subject carries no `pyforge-herald/`
    prefix at all and simply fails to match."""
    assert merged_story_keys(_ATLAS_23_SUBJECTS, _SLUG_SCOPED_TEMPLATE, "pyforge-herald") == frozenset()


def test_merged_story_keys_slug_scoped_template_still_recognizes_its_own_stations_landings():
    """The fix narrows false positives, it does not break real matches --
    herald's OWN rendered subjects still classify under its own slug."""
    assert merged_story_keys(_HERALD_23_SUBJECTS, _SLUG_SCOPED_TEMPLATE, "pyforge-herald") == frozenset(
        {StoryKey(23, 1), StoryKey(23, 2), StoryKey(23, 5), StoryKey(23, 6)}
    )


def test_merged_story_keys_story_direct_commit_no_longer_poisons_a_foreign_stations_same_numbered_key():
    """The other 2026-09-18 incident: steward's real `Story 48.2:`/`Story
    48.4:` direct-commit subjects must NOT poison marshal's own 48.2/48.4 --
    `merged_story_keys` never has branch data (a subject-only
    `git log --format=%s` scan), so the story-direct shape now refuses by
    default rather than matching unscoped."""
    subjects = (_STEWARD_DIRECT_SUBJECT_48_2, _STEWARD_DIRECT_SUBJECT_48_4)
    assert merged_story_keys(subjects, _TEMPLATE, _PROJECT_SLUG) == frozenset()


# --- corroborated_merged_story_keys (Story 51.7/CAP-255) ----------------------
#
# The 2026-09-18 `doctor/27-4-mint` incident: PR #1477 merged a MINT branch
# (spec-27-4 at `status: ready`), not a landing, and `merged_story_keys` read
# 27.4 as already-landed anyway. `corroborated_merged_story_keys` requires a
# `status: done` tracked spec before trusting a GITHUB_PR_MERGE_SUBJECT match
# reached through a bare station branch -- every other shape is trusted
# exactly as `merged_story_keys` already trusts it, with no `spec_status_for`
# call at all.

_REAL_SUBJECT_DOCTOR_27_4_MINT = "Merge pull request #1477 from rxm7706/doctor/27-4-mint"
_DOCTOR_PROJECT_SLUG = "pyforge-doctor"


def test_corroborated_merged_story_keys_excludes_a_mint_pr_whose_spec_is_not_done():
    """The PR #1477 fixture itself: 27.4 is present in the unscoped
    `merged_story_keys` but ABSENT from `corroborated_merged_story_keys`
    while its tracked spec reads `status: ready` (a mint PR, not a
    landing)."""
    subjects = (_REAL_SUBJECT_DOCTOR_27_4_MINT,)
    assert merged_story_keys(subjects, _TEMPLATE, _DOCTOR_PROJECT_SLUG) == frozenset({StoryKey(27, 4)})
    assert (
        corroborated_merged_story_keys(subjects, _TEMPLATE, _DOCTOR_PROJECT_SLUG, spec_status_for=lambda key: "ready")
        == frozenset()
    )


def test_corroborated_merged_story_keys_includes_a_landing_whose_spec_is_done():
    """The same shape, once the tracked spec has been promoted to `status:
    done` (a real landing merges the promoted twin) -- now corroborated."""
    subjects = (_REAL_SUBJECT_DOCTOR_27_4_MINT,)
    assert corroborated_merged_story_keys(
        subjects, _TEMPLATE, _DOCTOR_PROJECT_SLUG, spec_status_for=lambda key: "done"
    ) == frozenset({StoryKey(27, 4)})


def test_corroborated_merged_story_keys_excludes_on_an_unreadable_spec():
    """A git-read failure (unreadable ref, missing path, malformed
    frontmatter) reports `None` and must fail closed -- never corroborate."""
    subjects = (_REAL_SUBJECT_DOCTOR_27_4_MINT,)
    assert (
        corroborated_merged_story_keys(subjects, _TEMPLATE, _DOCTOR_PROJECT_SLUG, spec_status_for=lambda key: None)
        == frozenset()
    )


def test_corroborated_merged_story_keys_never_calls_spec_status_for_a_dispatch_branch():
    """Story 22.9's own `dispatch/<slug>/<key>` branch is an intent signal
    marshal mints only when it dispatched THIS key -- trusted exactly as
    `merged_story_keys` already trusts it, with no spec read at all."""
    subject = "Merge pull request #900 from rxm7706/dispatch/pyforge-marshal/22.9"

    def _boom(key):
        raise AssertionError("spec_status_for must not be called for a dispatch branch")

    assert corroborated_merged_story_keys((subject,), _TEMPLATE, _PROJECT_SLUG, spec_status_for=_boom) == frozenset(
        {StoryKey(22, 9)}
    )


def test_corroborated_merged_story_keys_never_calls_spec_status_for_non_github_shapes():
    """The templated, bmad-loop-native and recovery-commit shapes never
    reach a station branch at all -- `spec_status_for` must not be called
    for them either."""

    def _boom(key):
        raise AssertionError("spec_status_for must not be called")

    subjects = (
        "Merge 5.5 into main",
        "Merge bmad-loop/20260803-023308-65b7/2-4-doc-only-story-classification into loop/pyforge-marshal (bmad-loop)",
        "recover marshal 10-1 (Copier engine wrapper — the single seam)",
    )
    assert corroborated_merged_story_keys(subjects, _TEMPLATE, _PROJECT_SLUG, spec_status_for=_boom) == frozenset(
        {StoryKey(5, 5), StoryKey(2, 4), StoryKey(10, 1)}
    )


def test_corroborated_merged_story_keys_land_branch_fallback_needs_no_corroboration():
    """The `land/<station>-<epic>-<seq>` recovery-branch fallback embedded
    in a GitHub PR merge subject only fires once the grammar's own
    merge-subject shapes have all failed -- it is not the
    `GITHUB_PR_MERGE_SUBJECT` shape at all, so it is trusted with no spec
    read, exactly as `merged_story_keys` already trusts it."""
    subject = "Merge pull request #500 from rxm7706/land/marshal-10-1-recovery"

    def _boom(key):
        raise AssertionError("spec_status_for must not be called for the land/ fallback")

    assert corroborated_merged_story_keys((subject,), _TEMPLATE, _PROJECT_SLUG, spec_status_for=_boom) == frozenset(
        {StoryKey(10, 1)}
    )


def test_corroborated_merged_story_keys_known_keys_parity_with_merged_story_keys():
    """`known_keys` gates the templated shape identically to
    `merged_story_keys` -- this function does not relax or replace that
    pre-existing Story 35.1 corroboration."""
    subjects = ("Merge 22.5 into main", "Merge 22.11 into main")
    doctors_own_keys = frozenset({StoryKey(22, 5)})
    assert corroborated_merged_story_keys(
        subjects,
        _TEMPLATE,
        "pyforge-doctor",
        spec_status_for=lambda key: "done",
        known_keys=doctors_own_keys,
    ) == frozenset({StoryKey(22, 5)})


def test_corroborated_merged_story_keys_regression_parity_with_real_subjects():
    """Regression guard (the spec's own "0 regressions" bar): every real,
    already-landed subject `merged_story_keys`'s own suite covers still
    classifies once its ambiguous match is corroborated `status: done`."""
    subjects = (_REAL_SUBJECT_2_3, _REAL_SUBJECT_3_8, _REAL_SUBJECT_MARSHAL_4_2)
    assert corroborated_merged_story_keys(
        subjects, _TEMPLATE, _PROJECT_SLUG, spec_status_for=lambda key: "done"
    ) == frozenset({StoryKey(2, 3), StoryKey(3, 8), StoryKey(4, 2)})


# --- marshal_native_merged_keys (Story 5.9) -----------------------------------


def test_marshal_native_merged_keys_recognizes_the_templated_form():
    """The AD-24 templated form -- `deploy land-story`'s own rendered
    merge-subject signature -- is Marshal-driven and IS included."""
    subjects = ("Merge 5.5 into main",)
    assert marshal_native_merged_keys(subjects, _TEMPLATE, _PROJECT_SLUG) == frozenset({StoryKey(5, 5)})


def test_marshal_native_merged_keys_recognizes_a_land_rendered_subject():
    """Story 5.10: `marshal land`'s full-merge path renders its subject via
    the SAME `identity.render_merge_subject(key, template, slug)` `deploy
    land-story` already uses -- proving that rendered subject classifies as
    Marshal-native, not merely reading the code that claims it does."""
    key = StoryKey(5, 10)
    rendered_subject = render_merge_subject(key, _TEMPLATE, _PROJECT_SLUG)
    assert marshal_native_merged_keys((rendered_subject,), _TEMPLATE, _PROJECT_SLUG) == frozenset({key})


def test_marshal_native_merged_keys_recognizes_the_bmadloop_native_form():
    """bmad-loop's own native merge-commit shape is ALSO Marshal-driven
    (Story 5.9's own Design Notes: "Marshal already knows") and IS
    included."""
    bmadloop_subject = (
        "Merge bmad-loop/20260803-023308-65b7/2-4-doc-only-story-classification into loop/pyforge-marshal (bmad-loop)"
    )
    assert marshal_native_merged_keys((bmadloop_subject,), _TEMPLATE, _PROJECT_SLUG) == frozenset({StoryKey(2, 4)})


def test_marshal_native_merged_keys_excludes_the_github_pr_form():
    """The one real-world regression this function exists to prove: a
    real GitHub PR-merge subject (this repo's own actually-observed shape
    for a bmad-quick-dev-completed story landed by hand) is EXCLUDED --
    that route is not Marshal-driven, and is the whole reason Story 5.9
    exists."""
    subjects = (_REAL_SUBJECT_2_3, _REAL_SUBJECT_3_8)
    assert marshal_native_merged_keys(subjects, _TEMPLATE, _PROJECT_SLUG) == frozenset()


def test_marshal_native_merged_keys_is_a_strict_subset_of_merged_story_keys():
    """The story's own detection contract: `merged_story_keys - marshal_
    native_merged_keys` names exactly the quick-dev route. Mixing all
    three subject shapes in one call proves the narrowing, not merely the
    exclusion of one shape in isolation."""
    bmadloop_subject = (
        "Merge bmad-loop/20260803-023308-65b7/2-4-doc-only-story-classification into loop/pyforge-marshal (bmad-loop)"
    )
    subjects = ("Merge 5.5 into main", bmadloop_subject, _REAL_SUBJECT_2_3)

    full = merged_story_keys(subjects, _TEMPLATE, _PROJECT_SLUG)
    native = marshal_native_merged_keys(subjects, _TEMPLATE, _PROJECT_SLUG)

    assert full == frozenset({StoryKey(5, 5), StoryKey(2, 4), StoryKey(2, 3)})
    assert native == frozenset({StoryKey(5, 5), StoryKey(2, 4)})
    assert full - native == frozenset({StoryKey(2, 3)})


def test_marshal_native_merged_keys_scopes_bmadloop_pattern_to_project_slug():
    """The identical live cross-project collision `extract_story_key_from_
    bmadloop_merge_subject`'s own docstring documents -- a DIFFERENT
    project's bmad-loop merge must never be misread as this project's own
    key."""
    warden_subject = (
        "Merge bmad-loop/20260724-055419-3c0e/6-8-baseline-grandfathering into loop/pyforge-warden (bmad-loop)"
    )
    assert marshal_native_merged_keys((warden_subject,), _TEMPLATE, _PROJECT_SLUG) == frozenset()


def test_marshal_native_merged_keys_skips_non_merge_subjects():
    subjects = (_REAL_SUBJECT_NOT_A_MERGE_1, _REAL_SUBJECT_NOT_A_MERGE_2)
    assert marshal_native_merged_keys(subjects, _TEMPLATE, _PROJECT_SLUG) == frozenset()


def test_marshal_native_merged_keys_empty_subjects_returns_empty_set():
    assert marshal_native_merged_keys((), _TEMPLATE, _PROJECT_SLUG) == frozenset()


def test_marshal_native_merged_keys_templated_form_filters_to_known_keys():
    """Story 35.1: `marshal_native_merged_keys` runs its own independent
    templated-shape loop (never delegates to `_classify_merge_subject`) --
    it needs the identical `known_keys` scoping, not just `merged_story_
    keys`, or its own callers (`run_reconcile_completions`'s write path)
    stay exposed to the same cross-station collision."""
    subjects = ("Merge 22.5 into main", "Merge 22.11 into main")
    doctors_own_keys = frozenset({StoryKey(22, 5)})
    assert marshal_native_merged_keys(subjects, _TEMPLATE, "pyforge-doctor", known_keys=doctors_own_keys) == frozenset(
        {StoryKey(22, 5)}
    )


def test_marshal_native_merged_keys_templated_form_unscoped_when_known_keys_omitted():
    subjects = ("Merge 22.11 into main",)
    assert marshal_native_merged_keys(subjects, _TEMPLATE, "pyforge-doctor") == frozenset({StoryKey(22, 11)})


# --- count_conforming_subjects ------------------------------------------------


def test_count_conforming_subjects_counts_both_patterns_not_deduplicated():
    subjects = (
        "Merge 1.2 into main",
        _REAL_SUBJECT_2_3,
        _REAL_SUBJECT_2_3,  # same key twice -- must still count as 2
        _REAL_SUBJECT_AMBIGUOUS,  # conforms to neither -- not counted
        _REAL_SUBJECT_NOT_A_MERGE_1,
    )
    assert count_conforming_subjects(subjects, _TEMPLATE, _PROJECT_SLUG) == 3


def test_count_conforming_subjects_zero_for_no_conforming_subjects():
    subjects = (_REAL_SUBJECT_NOT_A_MERGE_1, _REAL_SUBJECT_NOT_A_MERGE_2)
    assert count_conforming_subjects(subjects, _TEMPLATE, _PROJECT_SLUG) == 0


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
    assert is_valid_spec_text("---\nstatus: 'draft'\ntitle: 'x'\n---\n\nbody\n") is True


# --- leading provenance banner (Story 50.5, CAP-248) --------------------------


def test_is_valid_spec_text_true_for_banner_above_frontmatter():
    """Herald's pre-#1460 `spec-1-4` shape: a single-line HTML-comment
    banner sits above the `---` fence instead of below it."""
    text = "<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->\n" + _VALID_SPEC
    assert is_valid_spec_text(text) is True


def test_is_valid_spec_text_true_for_multiline_banner_above_frontmatter():
    text = "<!--\nRECOVERED\nfrom a session transcript\n-->\n" + _VALID_SPEC
    assert is_valid_spec_text(text) is True


def test_is_valid_spec_text_true_for_banner_below_frontmatter_unaffected():
    """The PR #1460 data-side fix's own shape (banner directly below the
    closing fence) never starts with `<!--`, so it is untouched by the
    banner-skip and must keep parsing exactly as before."""
    text = "---\ntitle: 'x'\nstatus: 'shipped'\n---\n\n<!-- Promoted ... -->\n\nbody\n"
    assert is_valid_spec_text(text) is True


def test_is_valid_spec_text_false_for_unclosed_banner():
    """An unclosed `<!--` is not a banner this parser recognizes -- the
    text still doesn't start with `---`, so it stays invalid."""
    text = "<!-- never closed\n" + _VALID_SPEC
    assert is_valid_spec_text(text) is False


def test_is_valid_spec_text_true_for_blank_line_before_banner():
    """Story 51.8 (DW-FU-50-6): a leading blank line before the banner's
    opening marker must not fall through to "no frontmatter"."""
    text = "\n<!-- Promoted ... -->\n" + _VALID_SPEC
    assert is_valid_spec_text(text) is True


def test_is_valid_spec_text_true_for_spaces_before_banner():
    text = "  <!-- Promoted ... -->\n" + _VALID_SPEC
    assert is_valid_spec_text(text) is True


def test_is_valid_spec_text_true_for_bom_before_banner():
    text = "\ufeff<!-- Promoted ... -->\n" + _VALID_SPEC
    assert is_valid_spec_text(text) is True


def test_is_valid_spec_text_false_for_no_frontmatter_still_invalid():
    """A leading blank line/BOM tolerance must not widen into accepting a
    spec with no frontmatter at all once the (non-existent) banner is
    skipped."""
    assert is_valid_spec_text("\nno frontmatter here\n") is False


# --- read_spec_status (Story 51.7/CAP-255) -------------------------------------


def test_read_spec_status_extracts_the_value():
    assert read_spec_status(_VALID_SPEC) == "shipped"


def test_read_spec_status_none_for_none():
    assert read_spec_status(None) is None


def test_read_spec_status_none_for_empty_string():
    assert read_spec_status("") is None


def test_read_spec_status_none_for_no_frontmatter():
    assert read_spec_status("just some body text, no frontmatter at all\n") is None


def test_read_spec_status_none_for_unterminated_frontmatter():
    assert read_spec_status("---\nstatus: 'shipped'\nno closing fence\n") is None


def test_read_spec_status_none_for_frontmatter_missing_status():
    assert read_spec_status("---\ntitle: 'x'\n---\n\nbody\n") is None


def test_read_spec_status_none_for_status_as_a_bare_substring_not_a_key():
    assert read_spec_status("---\ntitle: 'x'\nsubstatus: 'draft'\n---\n\nbody\n") is None


def test_read_spec_status_unquoted_value():
    assert read_spec_status("---\ntitle: 'x'\nstatus: done\n---\n\nbody\n") == "done"


def test_read_spec_status_double_quoted_value():
    text = "---\ntitle: 'x'\nstatus: \"ready\"\n---\n\nbody\n"
    assert read_spec_status(text) == "ready"


def test_read_spec_status_tolerates_a_leading_banner():
    """Story 50.5/CAP-248's banner tolerance, extended to `read_spec_status`
    per Story 51.8/CAP-256."""
    text = "<!-- Promoted from implementation-artifacts/ -->\n" + _VALID_SPEC
    assert read_spec_status(text) == "shipped"


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
    plan = classify_promotion_candidates(candidates=(), merged_keys=frozenset(), already_promoted=frozenset())
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


def test_missing_spec_keys_names_only_the_no_spec_at_all_case():
    """Story 4.2's own extension: ``missing_spec_keys`` carries ONLY the
    durable-with-no-Tier-3-spec-at-all subset of ``gaps`` (MRS-DEPLOY-001)
    as a structured set -- the invalid-spec case (MRS-DEPLOY-002, a
    zero-byte/truncated spec that DOES exist) lands in the SEPARATE
    ``invalid_spec_keys`` field (code review, 2026-08-06, P3) instead, never
    mixed into this one."""
    missing_key = StoryKey(1, 3)
    invalid_key = StoryKey(1, 4)
    promoted_key = StoryKey(1, 5)
    invalid = SpecCandidate(story_key=invalid_key, path="spec-1-4.md", text=None)
    promoted = SpecCandidate(story_key=promoted_key, path="spec-1-5.md", text=_VALID_SPEC)

    plan = classify_promotion_candidates(
        candidates=(invalid, promoted),
        merged_keys=frozenset({missing_key, invalid_key, promoted_key}),
        already_promoted=frozenset(),
    )

    assert plan.missing_spec_keys == frozenset({missing_key})
    assert plan.invalid_spec_keys == frozenset({invalid_key})
    assert plan.to_promote == (promoted,)


def test_missing_spec_keys_defaults_to_empty_for_a_clean_plan():
    plan = classify_promotion_candidates(candidates=(), merged_keys=frozenset(), already_promoted=frozenset())
    assert plan.missing_spec_keys == frozenset()
    assert plan.invalid_spec_keys == frozenset()


def test_invalid_spec_keys_names_the_zero_byte_or_truncated_case():
    """Code review, 2026-08-06, P3 (Blind Hunter): a durable story whose
    Tier-3 spec exists but is zero-byte/truncated (MRS-DEPLOY-002) is now
    named in its own structured ``invalid_spec_keys`` set -- a corrupt
    paper trail is at least as concerning as a missing one, so teardown's
    reachability check (``cli/deploy.py::unreachable_promotions_for_slug``)
    can fold it into the unreachable set too."""
    invalid_key = StoryKey(2, 9)
    invalid = SpecCandidate(story_key=invalid_key, path="spec-2-9.md", text="")

    plan = classify_promotion_candidates(
        candidates=(invalid,),
        merged_keys=frozenset({invalid_key}),
        already_promoted=frozenset(),
    )

    assert plan.invalid_spec_keys == frozenset({invalid_key})
    assert plan.missing_spec_keys == frozenset()
    assert plan.to_promote == ()
