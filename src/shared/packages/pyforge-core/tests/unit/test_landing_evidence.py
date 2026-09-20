"""Unit tests for ``pyforge.core.landing_evidence`` (Story 20.8, FR-191 CAP-1).

Canonical grammar tests -- doctor and marshal conformance suites import
``conformance_fixtures()`` from here and re-run the same matrix without
either package importing ``pyforge.marshal``.
"""

from __future__ import annotations

import pytest

from pyforge.core.landing_evidence import (
    PRE_CONVENTION_RECOVERY_COMMITS,
    RECOVERY_LANDING_CONVENTION,
    BranchDerivedShape,
    LandingEvidenceShape,
    StoryKeyRef,
    classify_branch_name,
    classify_commit,
    classify_merge_subject,
    conformance_fixtures,
    merged_story_keys,
    parse_github_pr_merge_subject,
    parse_recovery_commit_sha,
    parse_station_branch_name,
)

_TEMPLATE = "Merge {key} into main"


@pytest.mark.parametrize("fixture", conformance_fixtures(), ids=lambda f: str(f["label"]))
def test_conformance_matrix(fixture: dict[str, object]) -> None:
    project_slug = str(fixture["project_slug"])
    template = str(fixture["template"])
    expected_key = fixture["expected_key"]
    expected_shape = fixture["expected_shape"]

    if "commit_sha" in fixture:
        match = classify_commit(
            str(fixture["commit_sha"]),
            str(fixture.get("subject", "")),
            template=template,
            project_slug=project_slug,
        )
    elif "subject" in fixture:
        match = classify_merge_subject(
            str(fixture["subject"]),
            template=template,
            project_slug=project_slug,
            branch=fixture.get("branch"),
        )
    elif "branch" in fixture:
        match = classify_branch_name(str(fixture["branch"]), project_slug=project_slug)
    else:
        pytest.fail(f"fixture {fixture['label']} has no subject, branch, or commit_sha")

    assert match is not None, f"fixture {fixture['label']} did not match"
    assert match.key == expected_key
    assert match.shape == expected_shape


def test_three_recovery_commits_are_allowlisted() -> None:
    assert PRE_CONVENTION_RECOVERY_COMMITS == frozenset(
        {
            "accc097e6a",
            "5290c9bcd2",
            "03d8fc8c86",
        }
    )
    assert parse_recovery_commit_sha("accc097e6a") == StoryKeyRef(8, 2)
    assert parse_recovery_commit_sha("5290c9bcd2") == StoryKeyRef(10, 1)
    assert parse_recovery_commit_sha("03d8fc8c86") == StoryKeyRef(3, 7)


def test_github_pattern_rejects_cross_project_collision() -> None:
    subject = "Merge pull request #274 from rxm7706/marshal/4-2-teardown-reachability-spec-recovery"
    assert parse_github_pr_merge_subject(subject, "pyforge-marshal") == StoryKeyRef(4, 2)
    assert parse_github_pr_merge_subject(subject, "pyforge-mason") is None


def test_ambiguous_branch_segment_with_non_leading_digits_is_rejected() -> None:
    subject = "Merge pull request #265 from rxm7706/marshal/refresh-dashboard-3-7"
    assert parse_github_pr_merge_subject(subject, "pyforge-marshal") is None


def test_merged_story_keys_deduplicates_and_skips_non_story_subjects() -> None:
    subjects = (
        "Merge 4-2-teardown into main",
        "Merge 4-2-teardown into main",
        "fastmcp-v4",
        "recover marshal 10-1 (Copier engine wrapper — the single seam)",
    )
    keys = merged_story_keys(subjects, template=_TEMPLATE, project_slug="pyforge-marshal")
    assert keys == frozenset({StoryKeyRef(4, 2), StoryKeyRef(10, 1)})


def test_recovery_convention_document_is_non_empty() -> None:
    assert "land/<station>" in RECOVERY_LANDING_CONVENTION
    assert "recover <station>" in RECOVERY_LANDING_CONVENTION
    assert "PRE_CONVENTION_RECOVERY_COMMITS" in RECOVERY_LANDING_CONVENTION


# --------------------------------------------------------------------------
# Story 50.4/FR-191 CAP-247: `{slug}`-scoped templated subjects and
# branch-corroborated story-direct commits.
# --------------------------------------------------------------------------


def test_templated_merge_subject_rejects_a_foreign_slug() -> None:
    """A `{slug}`-scoped template rendered under a DIFFERENT project_slug
    carries a different literal prefix/suffix and simply fails to match --
    the fix for atlas's `Merge 23-N into main` poisoning herald's own
    23.1..23.6 once herald renders under its own scoped template."""
    template = "Merge {slug}/{key} into main"
    subject = "Merge pyforge-atlas/23-1 into main"
    match = classify_merge_subject(subject, template=template, project_slug="pyforge-herald")
    assert match is None


def test_templated_merge_subject_slug_scoped_still_classifies_for_its_own_station() -> None:
    template = "Merge {slug}/{key} into main"
    subject = "Merge pyforge-herald/23-1 into main"
    match = classify_merge_subject(subject, template=template, project_slug="pyforge-herald")
    assert match is not None
    assert match.key == StoryKeyRef(23, 1)
    assert match.shape is LandingEvidenceShape.TEMPLATED_MERGE_SUBJECT


def test_story_direct_commit_refuses_without_a_corroborating_branch() -> None:
    """Steward's `Story 48.2:`/`Story 48.4:` subjects must not poison
    marshal's own 48.2/48.4 -- ``branch`` defaults to ``None``, which
    refuses by default when a caller has no branch data at all."""
    subject = "Story 48.4: R-20 secrets profile for platform deploy."
    match = classify_merge_subject(subject, template=_TEMPLATE, project_slug="pyforge-marshal")
    assert match is None


def test_story_direct_commit_refuses_a_foreign_branch() -> None:
    subject = "Story 48.4: R-20 secrets profile for platform deploy."
    match = classify_merge_subject(
        subject,
        template=_TEMPLATE,
        project_slug="pyforge-marshal",
        branch="steward/48-4-secrets-profile",
    )
    assert match is None


def test_story_direct_commit_classifies_with_a_corroborating_branch() -> None:
    subject = "Story 48.4: R-20 secrets profile for platform deploy."
    match = classify_merge_subject(
        subject,
        template=_TEMPLATE,
        project_slug="pyforge-steward",
        branch="steward/48-4-secrets-profile",
    )
    assert match is not None
    assert match.key == StoryKeyRef(48, 4)
    assert match.shape is LandingEvidenceShape.STORY_DIRECT_COMMIT_SUBJECT


# --------------------------------------------------------------------------
# marshal Story 22.9: the station-scoped dispatch branch `dispatch/<slug>/<key>`
# --------------------------------------------------------------------------


def test_dispatch_branch_merge_subject_classifies_for_its_own_station() -> None:
    subject = "Merge pull request #900 from rxm7706/dispatch/pyforge-marshal/22.9"
    assert parse_github_pr_merge_subject(subject, "pyforge-marshal") == StoryKeyRef(22, 9)
    match = classify_merge_subject(subject, template=_TEMPLATE, project_slug="pyforge-marshal")
    assert match is not None
    assert match.key == StoryKeyRef(22, 9)
    assert match.shape is LandingEvidenceShape.GITHUB_PR_MERGE_SUBJECT
    assert match.branch_shape is BranchDerivedShape.DISPATCH_BRANCH


def test_dispatch_branch_merge_subject_never_classifies_cross_station() -> None:
    """The FULL slug in the branch is what makes a shared story key safe:
    two stations dispatching `22.9` must never classify as each other."""
    subject = "Merge pull request #901 from rxm7706/dispatch/pyforge-mason/22.9"
    assert parse_github_pr_merge_subject(subject, "pyforge-marshal") is None
    assert parse_github_pr_merge_subject(subject, "pyforge-mason") == StoryKeyRef(22, 9)


def test_dispatch_branch_name_classifies_for_its_own_station() -> None:
    assert parse_station_branch_name("dispatch/pyforge-marshal/22.9", "pyforge-marshal") == StoryKeyRef(22, 9)
    match = classify_branch_name("dispatch/pyforge-marshal/22.9", project_slug="pyforge-marshal")
    assert match is not None
    assert match.key == StoryKeyRef(22, 9)
    assert match.shape is LandingEvidenceShape.STATION_BRANCH_NAME


def test_dispatch_branch_name_never_classifies_cross_station() -> None:
    assert parse_station_branch_name("dispatch/pyforge-mason/22.9", "pyforge-marshal") is None
    assert classify_branch_name("dispatch/pyforge-mason/22.9", project_slug="pyforge-marshal") is None


def test_legacy_station_branch_shapes_still_classify() -> None:
    """The pre-22.9 names must keep working -- in-flight and already-landed
    dispatches carry them."""
    assert parse_station_branch_name("marshal/22.9", "pyforge-marshal") == StoryKeyRef(22, 9)
    assert parse_github_pr_merge_subject(
        "Merge pull request #887 from rxm7706/marshal/22.7", "pyforge-marshal"
    ) == StoryKeyRef(22, 7)
    assert parse_station_branch_name("marshal/22.9", "pyforge-mason") is None


def test_dispatch_prefix_alone_is_not_a_project_branch() -> None:
    """`dispatch/<key>` without a slug segment, and a same-named foreign
    prefix, must not classify."""
    assert parse_station_branch_name("dispatch/22.9", "pyforge-marshal") is None
    assert parse_station_branch_name("dispatch/pyforge-marshalx/22.9", "pyforge-marshal") is None


# --------------------------------------------------------------------------
# Story 51.7/CAP-255: ``branch_shape`` -- the metadata marshal's
# ``corroborated_merged_story_keys`` needs to tell a trustworthy dispatch
# landing apart from an ambiguous station-branch one (no grammar change).
# --------------------------------------------------------------------------


def test_station_branch_merge_subject_reports_station_branch_shape() -> None:
    """The 2026-09-18 ``doctor/27-4-mint`` incident: a bare
    ``<station>/<key>-<desc>`` branch reached through a GitHub PR-merge
    subject is ambiguous -- a mint/fallout/fix PR carries the exact same
    shape as a real landing. Exposed as ``STATION_BRANCH`` so a caller can
    require independent corroboration for it."""
    subject = "Merge pull request #1477 from rxm7706/doctor/27-4-mint"
    match = classify_merge_subject(subject, template=_TEMPLATE, project_slug="pyforge-doctor")
    assert match is not None
    assert match.key == StoryKeyRef(27, 4)
    assert match.shape is LandingEvidenceShape.GITHUB_PR_MERGE_SUBJECT
    assert match.branch_shape is BranchDerivedShape.STATION_BRANCH


def test_branch_shape_is_none_for_non_github_pr_shapes() -> None:
    """``branch_shape`` is populated only for ``GITHUB_PR_MERGE_SUBJECT`` --
    every other shape leaves it ``None``, including when no branch is
    involved at all."""
    match = classify_merge_subject("Merge 4-2-teardown into main", template=_TEMPLATE, project_slug="pyforge-marshal")
    assert match is not None
    assert match.branch_shape is None
