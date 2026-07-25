"""Unit tests for ``pyforge.doctor.verdict`` (Story 1.1, architecture spine
AD-2) — domain exactly ``{0, 2, 130}``; a ``warn`` Finding never changes the
exit code; ``fail`` always projects to ``2``.
"""

from __future__ import annotations

from itertools import product

from pyforge.doctor.models import DoctorReport, DoctorStatus, Finding, Source
from pyforge.doctor.verdict import EXIT_SIGINT, exit_code_for


def _finding(status: DoctorStatus) -> Finding:
    return Finding(
        source=Source.ENV_HYGIENE, check="x", status=status, message="m", evidence={}
    )


def test_exit_sigint_constant():
    assert EXIT_SIGINT == 130


def test_empty_findings_exit_zero():
    assert exit_code_for([]) == 0


def test_all_ok_findings_exit_zero():
    assert exit_code_for([_finding(DoctorStatus.OK)]) == 0


def test_all_warn_findings_exit_zero():
    assert exit_code_for([_finding(DoctorStatus.WARN)]) == 0


def test_mixed_ok_and_warn_findings_exit_zero():
    assert (
        exit_code_for([_finding(DoctorStatus.OK), _finding(DoctorStatus.WARN)]) == 0
    )


def test_one_fail_present_exits_two():
    findings = [
        _finding(DoctorStatus.OK),
        _finding(DoctorStatus.FAIL),
        _finding(DoctorStatus.WARN),
    ]
    assert exit_code_for(findings) == 2


def test_all_fail_exits_two():
    assert exit_code_for([_finding(DoctorStatus.FAIL)]) == 2


def test_warn_never_changes_the_exit_code():
    ok_only = exit_code_for([_finding(DoctorStatus.OK)])
    ok_and_warn = exit_code_for(
        [_finding(DoctorStatus.OK), _finding(DoctorStatus.WARN)]
    )
    fail_only = exit_code_for([_finding(DoctorStatus.FAIL)])
    fail_and_warn = exit_code_for(
        [_finding(DoctorStatus.FAIL), _finding(DoctorStatus.WARN)]
    )
    assert ok_only == ok_and_warn == 0
    assert fail_only == fail_and_warn == 2


def test_exit_code_for_accepts_a_doctor_report():
    report = DoctorReport(
        schema_version=1,
        verb="check",
        generated_at="2026-07-25T00:00:00Z",
        findings=(_finding(DoctorStatus.FAIL),),
    )
    assert exit_code_for(report) == 2


def test_exit_code_for_accepts_a_clean_doctor_report():
    report = DoctorReport(
        schema_version=1,
        verb="check",
        generated_at="2026-07-25T00:00:00Z",
        findings=(_finding(DoctorStatus.OK),),
    )
    assert exit_code_for(report) == 0


def test_exit_code_for_stays_in_zero_or_two_over_all_finding_combinations():
    """``exit_code_for`` never derives 130 from a Finding list (it's the
    SIGINT constant, produced only at the CLI boundary -- see
    ``verdict.py``'s module docstring) -- this asserts the narrower {0, 2}
    range it can actually produce, not the full {0, 2, 130} domain."""
    for combo in product(list(DoctorStatus), repeat=2):
        findings = [_finding(status) for status in combo]
        assert exit_code_for(findings) in {0, 2}
