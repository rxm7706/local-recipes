"""Unit tests for ``pyforge.doctor.models`` (Story 1.1) — covers every row of
the spec's I/O & Edge-Case Matrix for the Finding/DoctorReport contract,
plus schema validation of the packaged ``data/report-schema.json`` against
the two minimal fixtures and against ``DoctorReport.to_json_dict()`` output.
"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

import jsonschema
import pytest

from pyforge.doctor.models import (
    DoctorReport,
    DoctorStatus,
    Finding,
    Partition,
    Prescription,
    Source,
)

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _schema() -> dict:
    schema_text = (
        resources.files("pyforge.doctor")
        .joinpath("data", "report-schema.json")
        .read_text(encoding="utf-8")
    )
    return json.loads(schema_text)


def _fixture(name: str) -> dict:
    return json.loads((_FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _finding(status: DoctorStatus = DoctorStatus.OK) -> Finding:
    return Finding(
        source=Source.ENV_HYGIENE,
        check="x",
        status=status,
        message="m",
        evidence={},
    )


# --- Finding: valid / unknown status / unknown source ---------------------


def test_valid_finding_constructs():
    finding = Finding(
        source=Source.ENV_HYGIENE,
        check="x",
        status=DoctorStatus.WARN,
        message="m",
        evidence={},
    )
    assert finding.source is Source.ENV_HYGIENE
    assert finding.status is DoctorStatus.WARN


def test_finding_accepts_raw_string_source_and_status():
    finding = Finding(
        source="warden-doctor", check="x", status="ok", message="m", evidence={}
    )
    assert finding.source is Source.WARDEN_DOCTOR
    assert finding.status is DoctorStatus.OK


def test_finding_unknown_status_rejected():
    with pytest.raises(ValueError):
        Finding(
            source=Source.ENV_HYGIENE,
            check="x",
            status="critical",
            message="m",
            evidence={},
        )


def test_finding_unknown_source_rejected():
    with pytest.raises(ValueError):
        Finding(
            source="not-a-source",
            check="x",
            status=DoctorStatus.OK,
            message="m",
            evidence={},
        )


def test_finding_non_dict_evidence_rejected():
    with pytest.raises(ValueError):
        Finding(
            source=Source.ENV_HYGIENE,
            check="x",
            status=DoctorStatus.OK,
            message="m",
            evidence=["not", "a", "dict"],
        )


def test_finding_evidence_is_defensively_copied():
    """frozen=True only blocks attribute reassignment -- mutating the
    original dict after construction must not leak into the Finding."""
    evidence = {"k": "v"}
    finding = Finding(
        source=Source.ENV_HYGIENE,
        check="x",
        status=DoctorStatus.OK,
        message="m",
        evidence=evidence,
    )
    evidence["k"] = "mutated"
    assert finding.evidence == {"k": "v"}


def test_source_has_exactly_eight_members():
    # Story 4.3 (FR-12, AD-9) extends the closed taxonomy with ADOPTION --
    # a deliberate, reviewed addition, never an open/stringly-typed
    # escape hatch (still a fixed, enumerable set).
    assert {member.value for member in Source} == {
        "warden-doctor",
        "staleness-report",
        "cve-watcher",
        "behind-upstream",
        "feedstock-health",
        "release-cadence",
        "env-hygiene",
        "adoption",
    }


def test_finding_to_json_dict_shape():
    assert _finding().to_json_dict() == {
        "source": "env-hygiene",
        "check": "x",
        "status": "ok",
        "message": "m",
        "evidence": {},
    }


# --- Prescription -----------------------------------------------------


def test_prescription_unknown_partition_rejected():
    with pytest.raises(ValueError):
        Prescription(
            finding_ref="x",
            partition="not-a-partition",
            rank=None,
            rank_factors=None,
            action="do it",
            root_cause="because",
        )


def test_prescription_rank_and_rank_factors_stay_none_able():
    prescription = Prescription(
        finding_ref="x",
        partition=Partition.BLOCKED,
        rank=None,
        rank_factors=None,
        action="do it",
        root_cause="because",
    )
    assert prescription.rank is None
    assert prescription.rank_factors is None


def test_prescription_rank_factors_is_defensively_copied():
    rank_factors = {"k": "v"}
    prescription = Prescription(
        finding_ref="x",
        partition=Partition.ACTIONABLE,
        rank=1,
        rank_factors=rank_factors,
        action="do it",
        root_cause="because",
    )
    rank_factors["k"] = "mutated"
    assert prescription.rank_factors == {"k": "v"}


def test_prescription_to_json_dict_shape():
    prescription = Prescription(
        finding_ref="hygiene:DEP001:foo",
        partition=Partition.ACTIONABLE,
        rank=1,
        rank_factors={"severity": "high"},
        action="upgrade foo",
        root_cause="foo is unmaintained",
    )
    assert prescription.to_json_dict() == {
        "finding_ref": "hygiene:DEP001:foo",
        "partition": "actionable",
        "rank": 1,
        "rank_factors": {"severity": "high"},
        "action": "upgrade foo",
        "root_cause": "foo is unmaintained",
        "safe_upgrade_target": None,
        "safe_upgrade_reason": None,
    }


def test_prescription_safe_upgrade_fields_default_to_none():
    # Story 4.4: existing (pre-Epic-4) construction sites never pass these
    # kwargs -- they must default to None, not raise a TypeError.
    prescription = Prescription(
        finding_ref="x",
        partition=Partition.ACTIONABLE,
        rank=1,
        rank_factors={},
        action="do it",
        root_cause="because",
    )
    assert prescription.safe_upgrade_target is None
    assert prescription.safe_upgrade_reason is None


def test_prescription_safe_upgrade_fields_round_trip():
    prescription = Prescription(
        finding_ref="x",
        partition=Partition.ACTIONABLE,
        rank=1,
        rank_factors={},
        action="do it",
        root_cause="because",
        safe_upgrade_target="2.1.0",
        safe_upgrade_reason="patch version bump, no known breaking-change signal",
    )
    document = prescription.to_json_dict()
    assert document["safe_upgrade_target"] == "2.1.0"
    assert document["safe_upgrade_reason"] == (
        "patch version bump, no known breaking-change signal"
    )


# --- DoctorReport: verb/prescriptions coherence ----------------------------


def test_check_report_serializes_with_no_prescriptions_key():
    report = DoctorReport(
        schema_version=1,
        verb="check",
        generated_at="2026-07-25T00:00:00Z",
        findings=(_finding(),),
        prescriptions=None,
    )
    assert "prescriptions" not in report.to_json_dict()


def test_monitor_report_serializes_with_no_prescriptions_key():
    report = DoctorReport(
        schema_version=1,
        verb="monitor",
        generated_at="2026-07-25T00:00:00Z",
        findings=(),
        prescriptions=None,
    )
    assert "prescriptions" not in report.to_json_dict()


def test_diagnose_report_empty_prescriptions_serializes_as_empty_list():
    report = DoctorReport(
        schema_version=1,
        verb="diagnose",
        generated_at="2026-07-25T00:00:00Z",
        findings=(),
        prescriptions=[],
    )
    assert report.to_json_dict()["prescriptions"] == []


def test_diagnose_report_missing_prescriptions_rejected():
    with pytest.raises(ValueError):
        DoctorReport(
            schema_version=1,
            verb="diagnose",
            generated_at="2026-07-25T00:00:00Z",
            findings=(),
            prescriptions=None,
        )


def test_check_report_with_prescriptions_set_rejected():
    prescription = Prescription(
        finding_ref="x",
        partition=Partition.ACTIONABLE,
        rank=None,
        rank_factors=None,
        action="do it",
        root_cause="because",
    )
    with pytest.raises(ValueError):
        DoctorReport(
            schema_version=1,
            verb="check",
            generated_at="2026-07-25T00:00:00Z",
            findings=(),
            prescriptions=[prescription],
        )


def test_unknown_verb_rejected():
    with pytest.raises(ValueError):
        DoctorReport(
            schema_version=1,
            verb="bogus",
            generated_at="2026-07-25T00:00:00Z",
            findings=(),
        )


def test_schema_version_zero_rejected():
    with pytest.raises(ValueError):
        DoctorReport(
            schema_version=0,
            verb="check",
            generated_at="2026-07-25T00:00:00Z",
            findings=(),
        )


def test_schema_version_negative_rejected():
    with pytest.raises(ValueError):
        DoctorReport(
            schema_version=-1,
            verb="check",
            generated_at="2026-07-25T00:00:00Z",
            findings=(),
        )


def test_diagnose_report_with_a_real_prescription_round_trips_through_schema():
    """Exercises Prescription.to_json_dict() via a real DoctorReport (not
    just an empty prescriptions list), validated against the packaged
    schema's #/$defs/prescription."""
    prescription = Prescription(
        finding_ref="hygiene:DEP001:foo",
        partition=Partition.ACTIONABLE,
        rank=1,
        rank_factors={"severity": "high"},
        action="upgrade foo",
        root_cause="foo is unmaintained",
    )
    report = DoctorReport(
        schema_version=1,
        verb="diagnose",
        generated_at="2026-07-25T00:00:00Z",
        findings=(_finding(),),
        prescriptions=[prescription],
    )
    document = report.to_json_dict()
    assert document["prescriptions"] == [prescription.to_json_dict()]
    jsonschema.validate(document, _schema())


# --- Schema validation: fixtures + live-constructed reports ----------------


def test_minimal_check_report_fixture_validates_against_schema():
    jsonschema.validate(_fixture("minimal_check_report.json"), _schema())


def test_minimal_diagnose_report_fixture_validates_against_schema():
    jsonschema.validate(_fixture("minimal_diagnose_report.json"), _schema())


def test_check_report_json_dict_validates_against_schema():
    report = DoctorReport(
        schema_version=1,
        verb="check",
        generated_at="2026-07-25T00:00:00Z",
        findings=(),
        prescriptions=None,
    )
    jsonschema.validate(report.to_json_dict(), _schema())


def test_diagnose_report_json_dict_validates_against_schema():
    report = DoctorReport(
        schema_version=1,
        verb="diagnose",
        generated_at="2026-07-25T00:00:00Z",
        findings=(),
        prescriptions=[],
    )
    jsonschema.validate(report.to_json_dict(), _schema())


def test_diagnose_report_missing_prescriptions_key_fails_schema():
    """The raw (un-validated-by-the-model) document shape a schema consumer
    might still receive from elsewhere — the schema itself must independently
    reject a diagnose document lacking prescriptions."""
    document = {
        "schema_version": 1,
        "verb": "diagnose",
        "generated_at": "2026-07-25T00:00:00Z",
        "findings": [],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(document, _schema())


def test_check_report_with_prescriptions_key_fails_schema():
    document = {
        "schema_version": 1,
        "verb": "check",
        "generated_at": "2026-07-25T00:00:00Z",
        "findings": [],
        "prescriptions": [],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(document, _schema())
