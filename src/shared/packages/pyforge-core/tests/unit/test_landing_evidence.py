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
