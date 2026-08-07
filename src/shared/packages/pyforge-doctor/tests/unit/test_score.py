"""Unit tests for ``pyforge.doctor.score`` (Story 4.1, FR-10) -- covers every
row of the story's AC matrix: pure computation, determinism, the
incomplete-gather degrade case, and per-axis/composite grading."""

from __future__ import annotations

from pyforge.doctor.models import DoctorStatus, Finding, Source
from pyforge.doctor.score import AxisScore, Grade, GradeResult, grade


def _finding(source, check="pkg-a", status=DoctorStatus.OK, evidence=None):
    return Finding(
        source=source, check=check, status=status, message="stub", evidence=evidence or {}
    )


def _gather_failure(source):
    """Mirrors sources/atlas.py's own ``_one_fail_finding`` sentinel shape
    (``check="doctor.sources.atlas"``, ``evidence={}``)."""
    return Finding(
        source=source,
        check="doctor.sources.atlas",
        status=DoctorStatus.FAIL,
        message="axis unavailable",
        evidence={},
    )


# --- empty input -------------------------------------------------------


def test_grade_empty_findings_is_incomplete():
    result = grade([])
    assert result.grade is Grade.INCOMPLETE
    assert result.axis_scores == ()


# --- determinism ---------------------------------------------------------


def test_grade_is_deterministic_across_two_calls():
    findings = (
        _finding(Source.STALENESS_REPORT, check="pkg-a", status=DoctorStatus.WARN),
        _finding(Source.CVE_WATCHER, check="pkg-b", status=DoctorStatus.FAIL),
    )
    first = grade(findings)
    second = grade(findings)
    assert first == second


# --- pure per-axis grading -------------------------------------------------


def test_all_ok_findings_grade_a():
    findings = tuple(
        _finding(Source.STALENESS_REPORT, check=f"pkg-{i}", status=DoctorStatus.OK)
        for i in range(3)
    )
    result = grade(findings)
    assert result.grade is Grade.A
    assert result.axis_scores == (
        AxisScore(axis="staleness-report", ok=3, warn=0, fail=0, grade=Grade.A),
    )


def test_majority_warn_grades_c_minority_warn_grades_b():
    majority_warn = (
        _finding(Source.STALENESS_REPORT, status=DoctorStatus.WARN),
        _finding(Source.STALENESS_REPORT, check="pkg-b", status=DoctorStatus.WARN),
        _finding(Source.STALENESS_REPORT, check="pkg-c", status=DoctorStatus.OK),
    )
    assert grade(majority_warn).grade is Grade.C

    minority_warn = (
        _finding(Source.STALENESS_REPORT, status=DoctorStatus.WARN),
        _finding(Source.STALENESS_REPORT, check="pkg-b", status=DoctorStatus.OK),
        _finding(Source.STALENESS_REPORT, check="pkg-c", status=DoctorStatus.OK),
    )
    assert grade(minority_warn).grade is Grade.B


def test_majority_fail_grades_f_minority_fail_grades_d():
    majority_fail = (
        _finding(Source.CVE_WATCHER, status=DoctorStatus.FAIL),
        _finding(Source.CVE_WATCHER, check="pkg-b", status=DoctorStatus.FAIL),
        _finding(Source.CVE_WATCHER, check="pkg-c", status=DoctorStatus.OK),
    )
    assert grade(majority_fail).grade is Grade.F

    minority_fail = (
        _finding(Source.CVE_WATCHER, status=DoctorStatus.FAIL),
        _finding(Source.CVE_WATCHER, check="pkg-b", status=DoctorStatus.OK),
        _finding(Source.CVE_WATCHER, check="pkg-c", status=DoctorStatus.OK),
    )
    assert grade(minority_fail).grade is Grade.D


# --- composite = worst axis -------------------------------------------------


def test_composite_is_the_worst_axis_grade():
    findings = (
        _finding(Source.STALENESS_REPORT, status=DoctorStatus.OK),  # axis: A
        _finding(Source.CVE_WATCHER, check="pkg-b", status=DoctorStatus.FAIL),  # axis: D (1/1 fail -> F actually)
    )
    result = grade(findings)
    # cve-watcher: 1 fail / 1 total = 100% -> F; staleness-report: A.
    # Composite must be the worst (F), never averaged into a middling grade.
    assert result.grade is Grade.F
    axis_grades = {axis.axis: axis.grade for axis in result.axis_scores}
    assert axis_grades["staleness-report"] is Grade.A
    assert axis_grades["cve-watcher"] is Grade.F


def test_axis_scores_are_sorted_by_source_value():
    findings = (
        _finding(Source.STALENESS_REPORT, status=DoctorStatus.OK),
        _finding(Source.CVE_WATCHER, check="pkg-b", status=DoctorStatus.OK),
        _finding(Source.ENV_HYGIENE, check="pkg-c", status=DoctorStatus.OK),
    )
    result = grade(findings)
    assert [axis.axis for axis in result.axis_scores] == [
        "cve-watcher",
        "env-hygiene",
        "staleness-report",
    ]


# --- incomplete-gather degrade ----------------------------------------------


def test_one_axis_gather_failure_poisons_the_whole_composite():
    findings = (
        _finding(Source.STALENESS_REPORT, status=DoctorStatus.OK),  # real, healthy data
        _gather_failure(Source.CVE_WATCHER),  # cve axis timed out
    )
    result = grade(findings)
    assert result.grade is Grade.INCOMPLETE
    assert "cve-watcher" in result.reason
    axis_grades = {axis.axis: axis.grade for axis in result.axis_scores}
    assert axis_grades["cve-watcher"] is Grade.INCOMPLETE
    assert axis_grades["staleness-report"] is Grade.A  # still recorded, not discarded


def test_gather_failure_sentinel_with_a_different_check_name_is_not_mistaken_for_one():
    # A REAL fail Finding about an actual package problem (not the
    # sources/atlas.py gather-degrade sentinel) must never be misread as
    # "gather incomplete" just because it happens to be a FAIL.
    findings = (
        _finding(
            Source.CVE_WATCHER, check="real-package", status=DoctorStatus.FAIL,
            evidence={"delta": 3},
        ),
    )
    result = grade(findings)
    assert result.grade is Grade.F  # a real, computed grade -- not incomplete


# --- JSON round trip ---------------------------------------------------------


def test_axis_score_to_json_dict_shape():
    axis = AxisScore(axis="cve-watcher", ok=1, warn=2, fail=3, grade=Grade.F)
    assert axis.to_json_dict() == {
        "axis": "cve-watcher", "ok": 1, "warn": 2, "fail": 3, "grade": "F",
    }


def test_grade_result_to_json_dict_shape():
    result = GradeResult(grade=Grade.INCOMPLETE, axis_scores=(), reason="no findings gathered")
    assert result.to_json_dict() == {
        "grade": "incomplete", "axis_scores": [], "reason": "no findings gathered",
    }
