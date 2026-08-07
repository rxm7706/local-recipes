"""Unit tests for ``pyforge.doctor.prescribe.name_root_cause`` (Story 3.3,
FR-8) -- covers every row of the story spec's I/O & Edge-Case Matrix."""

from __future__ import annotations

from pyforge.doctor.models import DoctorStatus, Finding, Source
from pyforge.doctor.prescribe import name_root_cause


def _finding(source, check, status=DoctorStatus.WARN, evidence=None, message="stub"):
    return Finding(
        source=source, check=check, status=status, message=message, evidence=evidence or {}
    )


def test_cve_traced_to_staleness_names_the_lag_not_only_the_cve():
    cve = _finding(
        Source.CVE_WATCHER,
        "some-package",
        status=DoctorStatus.FAIL,
        evidence={"severity": "C", "delta": 2, "now_v": 3},
    )
    staleness = _finding(
        Source.STALENESS_REPORT,
        "some-package",
        evidence={"age_days": 400, "latest_conda_version": "1.2.3"},
    )
    root_cause = name_root_cause(cve, [cve, staleness])
    assert "staleness" in root_cause.lower()
    assert "400" in root_cause
    assert "1.2.3" in root_cause
    # Names more than just the CVE id/count -- the AC's own bar.
    assert "some-package" in root_cause


def test_cve_without_correlated_staleness_still_names_a_cause():
    cve = _finding(
        Source.CVE_WATCHER,
        "other-package",
        status=DoctorStatus.FAIL,
        evidence={"severity": "C", "delta": 1, "now_v": 1},
    )
    root_cause = name_root_cause(cve, [cve])
    assert "other-package" in root_cause
    assert "staleness" not in root_cause.lower() or "no correlated staleness" in root_cause.lower()


def test_cve_correlation_ignores_a_different_package_staleness_finding():
    cve = _finding(
        Source.CVE_WATCHER,
        "pkg-a",
        status=DoctorStatus.FAIL,
        evidence={"severity": "C", "delta": 1, "now_v": 1},
    )
    unrelated_staleness = _finding(
        Source.STALENESS_REPORT, "pkg-b", evidence={"age_days": 999}
    )
    root_cause = name_root_cause(cve, [cve, unrelated_staleness])
    assert "999" not in root_cause


def test_engine_missing_finding_templates_from_its_own_evidence():
    finding = _finding(
        Source.ENV_HYGIENE,
        "credential-header-scan",
        status=DoctorStatus.WARN,
        evidence={"file": "scripts/_http.py", "line": 42, "var_name": "JFROG_API_KEY"},
        message="unconditional credential injection",
    )
    root_cause = name_root_cause(finding, [finding])
    assert "scripts/_http.py" in root_cause
    assert "42" in root_cause
    assert "JFROG_API_KEY" in root_cause
    assert "unconditional credential injection" in root_cause  # message not discarded


def test_empty_evidence_falls_back_to_message_verbatim():
    finding = _finding(
        Source.WARDEN_DOCTOR,
        "pyforge-warden",
        status=DoctorStatus.FAIL,
        evidence={},
        message="pyforge-warden not installed -- install the gate extra",
    )
    root_cause = name_root_cause(finding, [finding])
    assert root_cause == "pyforge-warden not installed -- install the gate extra"


def test_root_cause_is_never_empty():
    for source in Source:
        finding = _finding(source, "check", evidence={})
        assert name_root_cause(finding, [finding])


def test_does_not_correlate_a_finding_with_itself():
    # A CVE Finding is never treated as "correlated" with itself even if it
    # happened to also carry Source.STALENESS_REPORT-shaped evidence keys.
    cve = _finding(
        Source.CVE_WATCHER,
        "pkg-a",
        status=DoctorStatus.FAIL,
        evidence={"severity": "C", "delta": 1, "now_v": 1, "age_days": 1},
    )
    root_cause = name_root_cause(cve, [cve])
    assert "no correlated staleness" in root_cause.lower()
