"""Unit tests for ``pyforge.core.landing_evidence`` (Story 20.8, FR-191 CAP-1).

Canonical grammar tests -- doctor and marshal conformance suites import
``conformance_fixtures()`` from here and re-run the same matrix without
either package importing ``pyforge.marshal``.
"""

from __future__ import annotations

import pytest
from pyforge.core.landing_evidence import (
    LandingEvidenceShape,
    PRE_CONVENTION_RECOVERY_COMMITS,
    RECOVERY_LANDING_CONVENTION,
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
    assert PRE_CONVENTION_RECOVERY_COMMITS == frozenset({
        "accc097e6a",
        "5290c9bcd2",
        "03d8fc8c86",
    })
    assert parse_recovery_commit_sha("accc097e6a") == StoryKeyRef(8, 2)
    assert parse_recovery_commit_sha("5290c9bcd2") == StoryKeyRef(10, 1)
    assert parse_recovery_commit_sha("03d8fc8c86") == StoryKeyRef(3, 7)


def test_github_pattern_rejects_cross_project_collision() -> None:
    subject = (
        "Merge pull request #274 from rxm7706/marshal/4-2-teardown-reachability-spec-recovery"
    )
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
# marshal Story 22.9: the station-scoped dispatch branch `dispatch/<slug>/<key>`
# --------------------------------------------------------------------------


def test_dispatch_branch_merge_subject_classifies_for_its_own_station() -> None:
    subject = "Merge pull request #900 from rxm7706/dispatch/pyforge-marshal/22.9"
    assert parse_github_pr_merge_subject(subject, "pyforge-marshal") == StoryKeyRef(22, 9)
    match = classify_merge_subject(
        subject, template=_TEMPLATE, project_slug="pyforge-marshal"
    )
    assert match is not None
    assert match.key == StoryKeyRef(22, 9)
    assert match.shape is LandingEvidenceShape.GITHUB_PR_MERGE_SUBJECT


def test_dispatch_branch_merge_subject_never_classifies_cross_station() -> None:
    """The FULL slug in the branch is what makes a shared story key safe:
    two stations dispatching `22.9` must never classify as each other."""
    subject = "Merge pull request #901 from rxm7706/dispatch/pyforge-mason/22.9"
    assert parse_github_pr_merge_subject(subject, "pyforge-marshal") is None
    assert parse_github_pr_merge_subject(subject, "pyforge-mason") == StoryKeyRef(22, 9)


def test_dispatch_branch_name_classifies_for_its_own_station() -> None:
    assert parse_station_branch_name(
        "dispatch/pyforge-marshal/22.9", "pyforge-marshal"
    ) == StoryKeyRef(22, 9)
    match = classify_branch_name(
        "dispatch/pyforge-marshal/22.9", project_slug="pyforge-marshal"
    )
    assert match is not None
    assert match.key == StoryKeyRef(22, 9)
    assert match.shape is LandingEvidenceShape.STATION_BRANCH_NAME


def test_dispatch_branch_name_never_classifies_cross_station() -> None:
    assert parse_station_branch_name(
        "dispatch/pyforge-mason/22.9", "pyforge-marshal"
    ) is None
    assert classify_branch_name(
        "dispatch/pyforge-mason/22.9", project_slug="pyforge-marshal"
    ) is None


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
