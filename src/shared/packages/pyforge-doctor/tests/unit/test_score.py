"""Unit tests for ``pyforge.doctor.score`` (Story 4.1, FR-10) -- covers every
row of the story's AC matrix: pure computation, determinism, the
incomplete-gather degrade case, and per-axis/composite grading."""

from __future__ import annotations

from pyforge.doctor.models import DoctorStatus, Finding, Source
from pyforge.doctor.score import AxisScore, Grade, GradeResult, grade


def _finding(source, check="pkg-a", status=DoctorStatus.OK, evidence=None):
    return Finding(source=source, check=check, status=status, message="stub", evidence=evidence or {})


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
    findings = tuple(_finding(Source.STALENESS_REPORT, check=f"pkg-{i}", status=DoctorStatus.OK) for i in range(3))
    result = grade(findings)
    assert result.grade is Grade.A
    assert result.axis_scores == (AxisScore(axis="staleness-report", ok=3, warn=0, fail=0, grade=Grade.A),)


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
            Source.CVE_WATCHER,
            check="real-package",
            status=DoctorStatus.FAIL,
            evidence={"delta": 3},
        ),
    )
    result = grade(findings)
    assert result.grade is Grade.F  # a real, computed grade -- not incomplete


def _degrade_warn(source, check="dream-chain", exception="OSError"):
    """The shape ``sources.degrade_on_exception`` leaves behind when a gather raised
    outright: the source's OWN ``check`` plus ``evidence={"exception": <class name>}``."""
    return Finding(
        source=source,
        check=check,
        status=DoctorStatus.WARN,
        message=f"{check} could not be evaluated here",
        evidence={"exception": exception},
    )


def test_a_degrade_on_exception_warn_grades_its_axis_incomplete():
    # DW-FU-6-6-11: this finding failed BOTH halves of the old atlas-only predicate and
    # graded the axis C -- a letter standing in for a gather that never completed.
    result = grade([_degrade_warn(Source.DREAM_CHAIN)])
    assert result.grade is Grade.INCOMPLETE
    assert result.axis_scores == (AxisScore(axis="dream-chain", ok=0, warn=0, fail=0, grade=Grade.INCOMPLETE),)
    assert "dream-chain" in result.reason


def test_a_degrade_on_exception_warn_poisons_the_composite_beside_healthy_axes():
    result = grade(
        [
            _finding(Source.STALENESS_REPORT, status=DoctorStatus.OK),
            _degrade_warn(Source.SPEC_SURFACE, check="spec-surface"),
        ]
    )
    assert result.grade is Grade.INCOMPLETE
    axis_grades = {axis.axis: axis.grade for axis in result.axis_scores}
    assert axis_grades["spec-surface"] is Grade.INCOMPLETE
    assert axis_grades["staleness-report"] is Grade.A


def test_an_ordinary_warn_with_no_exception_evidence_still_takes_a_letter_grade():
    result = grade([_finding(Source.DREAM_CHAIN, check="dream-chain", status=DoctorStatus.WARN, evidence={"x": 1})])
    assert result.grade is Grade.C
    assert result.axis_scores == (AxisScore(axis="dream-chain", ok=0, warn=1, fail=0, grade=Grade.C),)


def test_an_ordinary_warn_with_empty_evidence_still_takes_a_letter_grade():
    assert grade([_finding(Source.DREAM_CHAIN, check="dream-chain", status=DoctorStatus.WARN)]).grade is Grade.C


def test_a_fail_carrying_exception_evidence_is_a_real_finding_not_a_gather_failure():
    # `degrade_on_exception` only ever emits a WARN; a FAIL that happens to mention an
    # exception is a verdict about the subject, and keeps its letter.
    fail = _finding(Source.DREAM_CHAIN, check="dream-chain", status=DoctorStatus.FAIL, evidence={"exception": "X"})
    assert grade([fail]).grade is Grade.F


# --- JSON round trip ---------------------------------------------------------


def test_axis_score_to_json_dict_shape():
    axis = AxisScore(axis="cve-watcher", ok=1, warn=2, fail=3, grade=Grade.F)
    assert axis.to_json_dict() == {
        "axis": "cve-watcher",
        "ok": 1,
        "warn": 2,
        "fail": 3,
        "grade": "F",
    }


def test_grade_result_to_json_dict_shape():
    result = GradeResult(grade=Grade.INCOMPLETE, axis_scores=(), reason="no findings gathered")
    assert result.to_json_dict() == {
        "grade": "incomplete",
        "axis_scores": [],
        "reason": "no findings gathered",
    }


# --- cannot-evaluate marker (DW-doctor-40-1) -------------------------------


def test_a_warn_marked_unevaluable_makes_its_axis_incomplete():
    findings = (
        _finding(Source.LEDGER_REGRESSION, check="ledger-regression", status=DoctorStatus.OK),
        _finding(
            Source.LEDGER_REGRESSION,
            check="ledger-regression",
            status=DoctorStatus.WARN,
            evidence={"base": "origin/main", "head": "nope", "target": "/x", "unevaluable": True},
        ),
    )
    result = grade(findings)
    assert result.grade is Grade.INCOMPLETE
    assert result.axis_scores[0].grade is Grade.INCOMPLETE


def test_the_marker_must_be_true_not_merely_present():
    result = grade(
        (_finding(Source.CHAIN_LAYERS_AUDIT, status=DoctorStatus.WARN, evidence={"unevaluable": "no"}),),
    )
    assert result.grade is Grade.C


def test_real_cannot_evaluate_emitters_grade_incomplete(tmp_path):
    from pyforge.doctor.sources import factory, ledger

    for finding in (
        factory._unevaluable("check_pins", "boom", tmp_path),
        *ledger.gather(tmp_path, base="no-such-base", head="HEAD"),
    ):
        assert grade((finding,)).grade is Grade.INCOMPLETE, finding


# --- per-check axes for independent capabilities (DW-FU-10-2) --------------


def test_bmad_method_cap1_ok_does_not_dilute_a_cap2_warn():
    findings = (
        _finding(Source.BMAD_METHOD_VERSION_DRIFT, check="bmad-method-version-drift", status=DoctorStatus.OK),
        _finding(Source.BMAD_METHOD_VERSION_DRIFT, check="bmad-method-upstream-drift", status=DoctorStatus.WARN),
    )
    result = grade(findings)
    axes = {axis.axis: axis.grade for axis in result.axis_scores}
    assert axes == {
        "bmad-method-version-drift/bmad-method-upstream-drift": Grade.C,
        "bmad-method-version-drift/bmad-method-version-drift": Grade.A,
    }
    assert result.grade is Grade.C


def test_other_sources_still_grade_one_axis_per_source():
    findings = (
        _finding(Source.CVE_WATCHER, check="pkg-a", status=DoctorStatus.OK),
        _finding(Source.CVE_WATCHER, check="pkg-b", status=DoctorStatus.WARN),
    )
    result = grade(findings)
    assert [(axis.axis, axis.grade) for axis in result.axis_scores] == [("cve-watcher", Grade.B)]
