"""Unit tests for ``pyforge.doctor.prescribe.recommend_safe_upgrade`` (Story
4.4, FR-13, AD-10) -- covers every row of the story's AC matrix: a
confidently-known single-hop target, the multi-major-jump non-recommendation
case, the no-evidence case, and the breaking-change-signal case."""

from __future__ import annotations

from pyforge.doctor.models import DoctorStatus, Finding, Source
from pyforge.doctor.prescribe import recommend_safe_upgrade


def _finding(evidence: dict) -> Finding:
    return Finding(
        source=Source.STALENESS_REPORT,
        check="pkg-a",
        status=DoctorStatus.WARN,
        message="stub",
        evidence=evidence,
    )


def test_no_upstream_target_version_recommends_nothing():
    target, reason = recommend_safe_upgrade(_finding({}))
    assert target is None
    assert reason


def test_patch_bump_with_no_breaking_change_signal_is_recommended():
    target, reason = recommend_safe_upgrade(
        _finding({"latest_conda_version": "1.2.3", "upstream_version": "1.2.4"})
    )
    assert target == "1.2.4"
    assert "patch" in reason


def test_minor_bump_with_no_breaking_change_signal_is_recommended():
    target, reason = recommend_safe_upgrade(
        _finding({"latest_conda_version": "1.2.3", "upstream_version": "1.3.0"})
    )
    assert target == "1.3.0"
    assert "minor" in reason


def test_major_version_jump_is_not_confidently_recommended():
    target, reason = recommend_safe_upgrade(
        _finding({"latest_conda_version": "1.2.3", "upstream_version": "2.0.0"})
    )
    assert target is None
    assert "major" in reason


def test_explicit_breaking_change_signal_overrides_a_small_bump():
    target, reason = recommend_safe_upgrade(
        _finding(
            {
                "latest_conda_version": "1.2.3",
                "upstream_version": "1.2.4",
                "breaking_change": True,
            }
        )
    )
    assert target is None
    assert "breaking" in reason


def test_pypi_current_version_key_is_also_honored():
    target, _reason = recommend_safe_upgrade(
        _finding({"conda_version": "1.0.0", "pypi_current_version": "1.0.1"})
    )
    assert target == "1.0.1"


def test_unparseable_version_strings_recommend_nothing():
    target, reason = recommend_safe_upgrade(
        _finding({"latest_conda_version": "not-a-version", "upstream_version": "also-not"})
    )
    assert target is None
    assert reason


def test_reason_is_always_populated_even_when_target_is_none():
    for evidence in ({}, {"upstream_version": "2.0.0", "latest_conda_version": "1.0.0"}):
        _target, reason = recommend_safe_upgrade(_finding(evidence))
        assert reason and isinstance(reason, str)
