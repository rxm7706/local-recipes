"""Unit tests — the frozen enum tokens + report/finding types (Story 1.1).

The freeze is testable, not aspirational: canonical string values, closed
sets, frozen-dataclass immutability, the full 13-field ``Component`` shape,
and the declared-but-unpopulated KEV/EPSS slots.
"""

from __future__ import annotations

import dataclasses

import pytest

from pyforge.warden.inventory import Component, Provenance, PypiIdentity
from pyforge.warden.models import (
    AXIS_HYGIENE,
    AXIS_VULNERABILITY,
    AxisCoverage,
    ComplianceReport,
    CveMatchLevel,
    Ecosystem,
    ErrorKind,
    ErrorRecord,
    ExtractionMode,
    Finding,
    IdentitySource,
    ScannedManifest,
    Severity,
    SeverityTier,
    Status,
    StatusDriver,
    VulnData,
    WithholdReason,
)


def test_status_tokens_exact():
    assert {member.name: member.value for member in Status} == {
        "ERROR": "error",
        "POLICY_VIOLATION": "policy-violation",
        "INDETERMINATE": "indeterminate",
        "WARN": "warn",
        "BYPASSED": "bypassed",
        "CLEAN": "clean",
        "NOT_APPLICABLE": "not-applicable",
    }


def test_warn_token_is_warn_not_warnings():
    assert Status.WARN.value == "warn"
    assert "warnings" not in {member.value for member in Status}


def test_ecosystem_closed_set():
    assert {member.value for member in Ecosystem} == {"pypi", "conda"}


def test_error_kind_tokens_exact():
    assert {member.value for member in ErrorKind} == {
        "unparsable-manifest",
        "engine-unavailable",
        "engine-output-unrecognized",
        "engine-output-unparseable",
        "engine-execution-failed",
        "engine-timeout",
        "config-parse",
        "config-validation",
        "internal-error",
    }


def test_withhold_reason_starter_set():
    # ambiguous-identity added 2026-07-13 (follow-up review) — sanctioned
    # additive growth of the growable enum.
    assert {member.value for member in WithholdReason} == {
        "no-version",
        "unmapped-ecosystem",
        "native-nonpypi",
        "range-only",
        "ambiguous-identity",
    }


def test_cve_match_level_starter_set():
    assert {member.value for member in CveMatchLevel} == {"exact", "name-only", "none"}


def test_identity_source_tokens_exact():
    assert {member.value for member in IdentitySource} == {
        "native",
        "lock",
        "pypi-section",
        "map",
        "none",
    }


def test_extraction_mode_tokens_exact():
    assert {member.value for member in ExtractionMode} == {
        "parsed",
        "name-only",
        "union-marked",
        "raw-malformed",
    }


def test_severity_tier_tokens_exact():
    assert {member.value for member in SeverityTier} == {
        "critical",
        "high",
        "medium",
        "low",
        "none",
        "unknown",
    }


def test_axis_is_open_str_with_constants():
    assert AXIS_HYGIENE == "hygiene"
    assert AXIS_VULNERABILITY == "vulnerability"
    assert type(AXIS_HYGIENE) is str
    assert type(AXIS_VULNERABILITY) is str


def _sample_component() -> Component:
    return Component(
        name="requests",
        version="2.31.0",
        ecosystem=Ecosystem.PYPI,
        pypi_identity=PypiIdentity(name="requests", version="2.31.0"),
        identity_source=IdentitySource.NATIVE,
        mapping_confidence=None,
        cve_match_level=CveMatchLevel.EXACT,
        extraction_mode=ExtractionMode.PARSED,
        purl="pkg:pypi/requests@2.31.0",
        provenance=(Provenance(manifest="pyproject.toml", section="dependencies"),),
        hygiene_covered=True,
        vuln_matchable=True,
        indeterminate_reason=None,
    )


def _sample_report() -> ComplianceReport:
    return ComplianceReport(
        schema_version="1.0.0",
        tool_name="warden",
        tool_version="0.1.0",
        status=Status.CLEAN,
        status_driver=None,
        exit_code=0,
        findings=(),
        coverage=(),
        vuln_data=VulnData(source=None, snapshot_at=None, max_age_ok=None),
        inventory_count=0,
        resolved_scan_set=(),
        errors=(),
    )


@pytest.mark.parametrize(
    "instance",
    [
        Severity(tier=SeverityTier.HIGH, raw="CVSS:3.1/AV:N"),
        VulnData(source=None, snapshot_at=None, max_age_ok=None),
        StatusDriver(axis=AXIS_VULNERABILITY, finding_id="vuln:GHSA-x:requests@2.31.0"),
        Finding(
            id="hygiene:DEP002:leftpad",
            axis=AXIS_HYGIENE,
            message="unused dependency",
            subject="leftpad",
            severity=None,
        ),
        AxisCoverage(
            axis=AXIS_HYGIENE,
            manifests_found=1,
            manifests_parsed=1,
            deps_total=3,
            deps_assessed=3,
            resolution_depth=None,
        ),
        ErrorRecord(kind=ErrorKind.ENGINE_TIMEOUT, owner="engines", message="timed out"),
        ScannedManifest(path="pyproject.toml", kind="pyproject"),
        _sample_component(),
        _sample_report(),
    ],
    ids=lambda instance: type(instance).__name__,
)
def test_frozen_dataclasses_are_immutable(instance):
    field_name = dataclasses.fields(instance)[0].name
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(instance, field_name, "mutated")


def test_component_full_field_set_frozen():
    """All 13 fields, with declared type/optionality — introspected, exact."""
    declared = {field.name: field.type for field in dataclasses.fields(Component)}
    assert declared == {
        "name": "str",
        "version": "str | None",
        "ecosystem": "Ecosystem",
        "pypi_identity": "PypiIdentity | None",
        "identity_source": "IdentitySource",
        "mapping_confidence": "str | None",
        "cve_match_level": "CveMatchLevel",
        "extraction_mode": "ExtractionMode",
        "purl": "str",
        "provenance": "tuple[Provenance, ...]",
        "hygiene_covered": "bool",
        "vuln_matchable": "bool",
        "indeterminate_reason": "WithholdReason | None",
    }
    assert len(declared) == 13


def test_finding_kev_epss_present_but_none_by_default():
    finding = Finding(
        id="vuln:GHSA-abcd:requests@2.31.0",
        axis=AXIS_VULNERABILITY,
        message="known vulnerability",
        subject="requests",
        severity=Severity(tier=SeverityTier.CRITICAL, raw="CRITICAL"),
    )
    field_names = {field.name for field in dataclasses.fields(Finding)}
    assert {"kev", "epss"} <= field_names
    assert finding.kev is None
    assert finding.epss is None


def test_report_status_renders_value_plus_driver():
    document = _sample_report().to_json_dict()
    assert document["status"] == {"value": "clean", "driver": None}
    assert document["tool"] == {
        "name": "warden",
        "version": "0.1.0",
    }


def test_report_exit_code_outside_frozen_set_raises():
    with pytest.raises(ValueError, match="exit_code"):
        dataclasses.replace(_sample_report(), exit_code=5)


def test_non_clean_driverless_report_raises():
    with pytest.raises(ValueError, match="status_driver"):
        dataclasses.replace(
            _sample_report(), status=Status.POLICY_VIOLATION, exit_code=1
        )


def test_report_schema_version_must_be_v1_core_semver():
    for bad in ("2.0.0", "1.0", "1.0.0-rc1", "v1.0.0"):
        with pytest.raises(ValueError, match="schema_version"):
            dataclasses.replace(_sample_report(), schema_version=bad)


def test_malformed_finding_id_raises():
    with pytest.raises(ValueError, match="finding id"):
        Finding(
            id="not-a-family-id",
            axis=AXIS_HYGIENE,
            message="x",
            subject=None,
            severity=None,
        )


@pytest.mark.parametrize("epss", [float("nan"), 1.5], ids=["nan", "above-one"])
def test_finding_invalid_epss_raises(epss):
    with pytest.raises(ValueError, match="epss"):
        Finding(
            id="vuln:GHSA-abcd:requests@2.31.0",
            axis=AXIS_VULNERABILITY,
            message="known vulnerability",
            subject=None,
            severity=None,
            epss=epss,
        )


def test_coverage_parsed_exceeding_found_raises():
    with pytest.raises(ValueError, match="manifests_parsed"):
        AxisCoverage(
            axis=AXIS_HYGIENE,
            manifests_found=1,
            manifests_parsed=2,
            deps_total=0,
            deps_assessed=0,
            resolution_depth=None,
        )


def test_coverage_assessed_exceeding_total_raises():
    with pytest.raises(ValueError, match="deps_assessed"):
        AxisCoverage(
            axis=AXIS_HYGIENE,
            manifests_found=1,
            manifests_parsed=1,
            deps_total=1,
            deps_assessed=2,
            resolution_depth=None,
        )


def test_coverage_negative_count_raises():
    with pytest.raises(ValueError, match="manifests_found"):
        AxisCoverage(
            axis=AXIS_HYGIENE,
            manifests_found=-1,
            manifests_parsed=0,
            deps_total=0,
            deps_assessed=0,
            resolution_depth=None,
        )


def test_coverage_unknown_resolution_depth_raises():
    with pytest.raises(ValueError, match="resolution_depth"):
        AxisCoverage(
            axis=AXIS_HYGIENE,
            manifests_found=1,
            manifests_parsed=1,
            deps_total=1,
            deps_assessed=1,
            resolution_depth="direct_only",
        )


def test_duplicate_coverage_axis_raises():
    coverage = AxisCoverage(
        axis=AXIS_HYGIENE,
        manifests_found=1,
        manifests_parsed=1,
        deps_total=1,
        deps_assessed=1,
        resolution_depth=None,
    )
    with pytest.raises(ValueError, match="unique"):
        dataclasses.replace(_sample_report(), coverage=(coverage, coverage))


def test_vuln_family_finding_with_hygiene_axis_raises():
    finding = Finding(
        id="vuln:GHSA-abcd:requests@2.31.0",
        axis=AXIS_HYGIENE,
        message="known vulnerability",
        subject=None,
        severity=None,
    )
    with pytest.raises(ValueError, match="must carry axis"):
        dataclasses.replace(_sample_report(), findings=(finding,))


def test_hygiene_family_finding_with_vulnerability_axis_raises():
    finding = Finding(
        id="hygiene:DEP002:leftpad",
        axis=AXIS_VULNERABILITY,
        message="unused dependency",
        subject=None,
        severity=None,
    )
    with pytest.raises(ValueError, match="must carry axis"):
        dataclasses.replace(_sample_report(), findings=(finding,))


# --- Follow-up review (2026-07-13) regression suite ---------------------------


def test_raw_string_status_fails_at_construction():
    """StrEnum equality must not admit raw strings that crash later at
    serialization — construction coerces and fails loud."""
    with pytest.raises(ValueError):
        dataclasses.replace(_sample_report(), status="warnings")
    # A VALID raw token coerces to the member and renders fine.
    report = dataclasses.replace(_sample_report(), status="clean")
    assert report.status is Status.CLEAN
    assert report.to_json_dict()["status"]["value"] == "clean"


def test_raw_string_error_kind_and_severity_tier_coerce_or_raise():
    assert ErrorRecord(kind="engine-timeout", owner="infra", message="m").kind is (
        ErrorKind.ENGINE_TIMEOUT
    )
    with pytest.raises(ValueError):
        ErrorRecord(kind="engine-explosion", owner="infra", message="m")
    assert Severity(tier="high", raw=None).tier is SeverityTier.HIGH
    with pytest.raises(ValueError):
        Severity(tier="catastrophic", raw=None)


@pytest.mark.parametrize(
    ("status", "exit_code"),
    [
        (Status.CLEAN, 2),
        (Status.ERROR, 0),
        (Status.ERROR, 1),
        (Status.POLICY_VIOLATION, 0),
        (Status.INDETERMINATE, 0),
        (Status.BYPASSED, 1),
    ],
)
def test_incoherent_status_exit_pairs_fail_at_construction(status, exit_code):
    driver = (
        None
        if status in (Status.CLEAN, Status.NOT_APPLICABLE)
        else StatusDriver(axis=AXIS_VULNERABILITY, finding_id="vuln:GHSA-x:p@1.0")
    )
    with pytest.raises(ValueError, match="incoherent"):
        dataclasses.replace(
            _sample_report(), status=status, status_driver=driver, exit_code=exit_code
        )


def test_sigint_exit_is_coherent_with_every_status():
    """130 (SIGINT) is legal alongside any status — an interrupt can land
    during any verdict (mirrors the schema's coherence clauses)."""
    for status in Status:
        driver = (
            None
            if status in (Status.CLEAN, Status.NOT_APPLICABLE)
            else StatusDriver(axis=AXIS_VULNERABILITY, finding_id="vuln:GHSA-x:p@1.0")
        )
        report = dataclasses.replace(
            _sample_report(), status=status, status_driver=driver, exit_code=130
        )
        assert report.exit_code == 130


def test_duplicate_finding_ids_rejected():
    finding = Finding(
        id="hygiene:DEP002:leftpad",
        axis=AXIS_HYGIENE,
        message="unused",
        subject=None,
        severity=None,
    )
    twin = dataclasses.replace(finding, message="unused (different message)")
    with pytest.raises(ValueError, match="unique"):
        dataclasses.replace(_sample_report(), findings=(finding, twin))


def test_bool_rejected_by_numeric_guards():
    with pytest.raises(ValueError, match="exit_code"):
        dataclasses.replace(_sample_report(), exit_code=True)
    with pytest.raises(ValueError, match="inventory_count"):
        dataclasses.replace(_sample_report(), inventory_count=True)
    with pytest.raises(ValueError, match="epss"):
        Finding(
            id="vuln:GHSA-x:p@1.0",
            axis=AXIS_VULNERABILITY,
            message="m",
            subject=None,
            severity=None,
            epss=True,
        )
    with pytest.raises(ValueError, match="manifests_found"):
        AxisCoverage(
            axis=AXIS_HYGIENE,
            manifests_found=True,
            manifests_parsed=0,
            deps_total=0,
            deps_assessed=0,
            resolution_depth=None,
        )


def test_vuln_data_concrete_verdict_requires_provenance():
    with pytest.raises(ValueError, match="provenance"):
        VulnData(source=None, snapshot_at=None, max_age_ok=True)
    with pytest.raises(ValueError, match="provenance"):
        VulnData(source="osv-offline", snapshot_at=None, max_age_ok=False)
    assert VulnData(
        source="osv-offline", snapshot_at="2026-07-10", max_age_ok=True
    ).max_age_ok is True


def test_trailing_and_embedded_newlines_rejected():
    with pytest.raises(ValueError, match="schema_version"):
        dataclasses.replace(_sample_report(), schema_version="1.0.0\n")
    with pytest.raises(ValueError, match="finding id"):
        Finding(
            id="hygiene:DEP002:leftpad\n",
            axis=AXIS_HYGIENE,
            message="m",
            subject=None,
            severity=None,
        )
    with pytest.raises(ValueError, match="finding id"):
        Finding(
            id="vuln:GH\nSA:p@1.0",
            axis=AXIS_VULNERABILITY,
            message="m",
            subject=None,
            severity=None,
        )


def test_negative_zero_epss_canonicalizes():
    finding = Finding(
        id="vuln:GHSA-x:p@1.0",
        axis=AXIS_VULNERABILITY,
        message="m",
        subject=None,
        severity=None,
        epss=-0.0,
    )
    import math

    assert math.copysign(1.0, finding.epss) == 1.0  # -0.0 became 0.0


def test_resolution_depth_closed_vocabulary():
    coverage = AxisCoverage(
        axis=AXIS_VULNERABILITY,
        manifests_found=1,
        manifests_parsed=1,
        deps_total=3,
        deps_assessed=3,
        resolution_depth="locked-closure",
    )
    assert coverage.resolution_depth == "locked-closure"
    with pytest.raises(ValueError):
        AxisCoverage(
            axis=AXIS_VULNERABILITY,
            manifests_found=1,
            manifests_parsed=1,
            deps_total=3,
            deps_assessed=3,
            resolution_depth="locked-clsoure",
        )
