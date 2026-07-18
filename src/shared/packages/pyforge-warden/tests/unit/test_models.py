"""Unit tests — the frozen enum tokens + report/finding types (Story 1.1).

The freeze is testable, not aspirational: canonical string values, closed
sets, frozen-dataclass immutability, the full 15-field ``Component`` shape,
and the declared-but-unpopulated KEV/EPSS/license/currency slots.
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from pyforge.warden.inventory import Component, Provenance, PypiIdentity
from pyforge.warden.models import (
    AXIS_CURRENCY,
    AXIS_HYGIENE,
    AXIS_LICENSE,
    AXIS_VULNERABILITY,
    AxisCoverage,
    ComplianceReport,
    CurrencyInfo,
    CurrencyVerdict,
    CveMatchLevel,
    Ecosystem,
    Epss,
    ErrorKind,
    ErrorRecord,
    ExtractionMode,
    Finding,
    IdentitySource,
    LicenseInfo,
    LicenseVerdict,
    ScannedManifest,
    Severity,
    SeverityTier,
    Status,
    StatusDriver,
    SuppressedFinding,
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
        license_covered=True,
        currency_covered=True,
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
    """All 15 fields, with declared type/optionality — introspected, exact."""
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
        "license_covered": "bool",
        "currency_covered": "bool",
        "indeterminate_reason": "WithholdReason | None",
    }
    assert len(declared) == 15


def test_finding_kev_epss_present_but_none_by_default():
    finding = Finding(
        id="vuln:GHSA-abcd:requests@2.31.0",
        axis=AXIS_VULNERABILITY,
        message="known vulnerability",
        subject="requests",
        severity=Severity(tier=SeverityTier.CRITICAL, raw="CRITICAL"),
    )
    field_names = {field.name for field in dataclasses.fields(Finding)}
    # Story 6.1 reserved kev_date/license/currency alongside the shipped
    # kev/epss slots; all default None and the v1 producer never sets them.
    assert {"kev", "kev_date", "epss", "license", "currency"} <= field_names
    assert finding.kev is None
    assert finding.kev_date is None
    assert finding.epss is None
    assert finding.license is None
    assert finding.currency is None


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


@pytest.mark.parametrize("bad", [float("nan"), 1.5, -0.1], ids=["nan", "above-one", "below-zero"])
def test_epss_object_out_of_range_raises(bad):
    """Story 6.1: epss moved from a bare float to an Epss{score, percentile}
    object; both fields must be finite probabilities in [0, 1]."""
    with pytest.raises(ValueError, match="epss"):
        Epss(score=bad, percentile=0.5)
    with pytest.raises(ValueError, match="epss"):
        Epss(score=0.5, percentile=bad)


def test_finding_epss_must_be_epss_object():
    """A bare float (the pre-6.1 shape) is no longer a valid epss value —
    Finding requires the Epss object, failing loud at construction."""
    with pytest.raises(ValueError, match="epss"):
        Finding(
            id="vuln:GHSA-abcd:requests@2.31.0",
            axis=AXIS_VULNERABILITY,
            message="known vulnerability",
            subject=None,
            severity=None,
            epss=0.5,
        )


def test_finding_accepts_epss_object():
    finding = Finding(
        id="vuln:GHSA-abcd:requests@2.31.0",
        axis=AXIS_VULNERABILITY,
        message="known vulnerability",
        subject=None,
        severity=None,
        epss=Epss(score=0.42, percentile=0.9),
    )
    assert finding.epss.score == 0.42
    assert finding.epss.percentile == 0.9



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
        (Status.INDETERMINATE, 2),
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


def test_indeterminate_exit_zero_is_coherent():
    """Story 1.9: Status.INDETERMINATE widened its legal-exit set to
    {0, 1, 130} (mirroring Status.WARN's existing two-legal-exit shape) —
    the ONE sanctioned --allow-empty exception. Construction must accept
    the pairing (not merely reject it, per the OLD, now-superseded
    incoherence the parametrized test above used to pin at (INDETERMINATE,
    0) — moved to (INDETERMINATE, 2), still genuinely incoherent)."""
    driver = StatusDriver(
        axis=AXIS_VULNERABILITY, finding_id="indeterminate:empty-extraction:scan"
    )
    report = dataclasses.replace(
        _sample_report(),
        status=Status.INDETERMINATE,
        status_driver=driver,
        exit_code=0,
    )
    assert report.status is Status.INDETERMINATE
    assert report.exit_code == 0


@pytest.mark.parametrize(
    "driver",
    [
        StatusDriver(axis=AXIS_VULNERABILITY, finding_id="hygiene:DEP001:missingmod"),
        # Shares the empty-extraction NAMESPACE but not the exact id — the
        # exception is an exact match, never a prefix (review finding,
        # 2026-07-17 pass 2).
        StatusDriver(
            axis=AXIS_VULNERABILITY,
            finding_id="indeterminate:empty-extraction:not-the-sanctioned-one",
        ),
    ],
    ids=["unrelated-driver", "namespace-collision-not-exact-match"],
)
def test_indeterminate_exit_zero_rejected_for_non_empty_extraction_driver(driver):
    """Review finding (2026-07-17 pass 2): the exit-0 exception must be
    enforced at CONSTRUCTION time too (not just verdict.exit_code_for) —
    a directly-built ComplianceReport must not be able to claim exit 0 for
    an indeterminate cause other than the exact D2(c) empty-extraction
    driver, including one that merely shares its id namespace."""
    with pytest.raises(ValueError, match="empty-extraction"):
        dataclasses.replace(
            _sample_report(),
            status=Status.INDETERMINATE,
            status_driver=driver,
            exit_code=0,
        )


def test_indeterminate_exit_zero_rejected_with_null_driver():
    """A driverless indeterminate report already fails the earlier
    'status requires a driver' check — this pins that the NEW
    empty-extraction-exactness check doesn't crash (AttributeError on
    None) ahead of that existing, more specific error."""
    with pytest.raises(ValueError):
        dataclasses.replace(
            _sample_report(),
            status=Status.INDETERMINATE,
            status_driver=None,
            exit_code=0,
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
        Epss(score=True, percentile=0.5)
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
    epss = Epss(score=-0.0, percentile=-0.0)
    import math

    # -0.0 became 0.0 on BOTH fields (equal under comparison but rendering
    # differently, which would break byte-identical serialization).
    assert math.copysign(1.0, epss.score) == 1.0
    assert math.copysign(1.0, epss.percentile) == 1.0


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


# --- Story 6.1 (P2): license/currency finding coherence at CONSTRUCTION -------
# An incoherent license:/currency: finding can never be BUILT (the model's own
# docstring promise), mirroring the schema's allOf coherence clauses.


def test_license_finding_without_license_subobject_raises():
    """(a) A license: id with license=None is incoherent — the sub-object
    carrying the verdict/expression must be present."""
    with pytest.raises(ValueError, match="license"):
        Finding(
            id="license:MIT:x@1",
            axis=AXIS_LICENSE,
            message="m",
            subject=None,
            severity=None,
            license=None,
        )


def test_license_finding_with_allowed_verdict_raises():
    """(b) A license: finding is only ever emitted for denied/unknown — an
    'allowed' verdict on a license: id is incoherent (findings exist only for
    problems)."""
    with pytest.raises(ValueError, match="denied/unknown"):
        Finding(
            id="license:MIT:x@1",
            axis=AXIS_LICENSE,
            message="m",
            subject=None,
            severity=None,
            license=LicenseInfo(
                expression="MIT", family=None, verdict=LicenseVerdict.ALLOWED
            ),
        )


def test_currency_finding_verdict_must_match_reason_token():
    """(c) The id's reason token pins the verdict: currency:eol: -> EOL, so a
    SUPPORTED verdict on an eol: id is incoherent."""
    with pytest.raises(ValueError, match="verdict"):
        Finding(
            id="currency:eol:x@1",
            axis=AXIS_CURRENCY,
            message="m",
            subject=None,
            severity=None,
            currency=CurrencyInfo(
                verdict=CurrencyVerdict.SUPPORTED,
                latest="2.0",
                lag=3,
                eol_date="2020-01-01",
            ),
        )


def test_currency_finding_without_currency_subobject_raises():
    with pytest.raises(ValueError, match="currency"):
        Finding(
            id="currency:eol:x@1",
            axis=AXIS_CURRENCY,
            message="m",
            subject=None,
            severity=None,
            currency=None,
        )


@pytest.mark.parametrize(
    ("finding_id", "verdict"),
    [
        ("currency:eol:x@1", CurrencyVerdict.EOL),
        ("currency:over-lag:x@1", CurrencyVerdict.SUPPORTED),
    ],
    ids=["eol", "over-lag"],
)
def test_currency_eol_over_lag_finding_requires_non_null_provenance(
    finding_id, verdict
):
    """(d) An eol/over-lag finding whose CurrencyInfo leaves latest/lag/
    eol_date at their None defaults is incoherent — there is a problem to
    explain, so its provenance must be stated."""
    with pytest.raises(ValueError, match="latest/lag/eol_date"):
        Finding(
            id=finding_id,
            axis=AXIS_CURRENCY,
            message="m",
            subject=None,
            severity=None,
            currency=CurrencyInfo(verdict=verdict),
        )


def test_currency_info_lag_rejects_non_int():
    """(e) lag is an integer release count — a float or bool is rejected at
    CurrencyInfo construction (matches AxisCoverage/Epss's numeric guard)."""
    with pytest.raises(ValueError, match="lag"):
        CurrencyInfo(verdict=CurrencyVerdict.EOL, lag=1.5)
    with pytest.raises(ValueError, match="lag"):
        CurrencyInfo(verdict=CurrencyVerdict.EOL, lag=True)


def test_coherent_license_and_currency_findings_still_construct():
    """The coherence guards NEVER block a well-formed finding: reason token,
    verdict, and non-null provenance all consistent."""
    denied = Finding(
        id="license:GPL-3.0-only:numpy@1.26.4",
        axis=AXIS_LICENSE,
        message="denied",
        subject="numpy",
        severity=None,
        license=LicenseInfo(
            expression="GPL-3.0-only", family=None, verdict=LicenseVerdict.DENIED
        ),
    )
    assert denied.license.verdict is LicenseVerdict.DENIED
    eol = Finding(
        id="currency:eol:django@1.11.29",
        axis=AXIS_CURRENCY,
        message="eol",
        subject="django",
        severity=None,
        currency=CurrencyInfo(
            verdict=CurrencyVerdict.EOL,
            latest="5.0",
            lag=9,
            eol_date="2020-04-01",
            tier="endoflife-date",
        ),
    )
    assert eol.currency.verdict is CurrencyVerdict.EOL


# --- Story 6.1 (P4): determinism (NFR-R3b) with the new fields POPULATED ------


def _report_with_all_new_fields() -> ComplianceReport:
    """A report exercising every new 6.1 field: two license: findings with
    distinct LicenseInfo, two currency: findings with distinct CurrencyInfo, a
    vuln: finding carrying kev_date + Epss(score, percentile), and a
    multi-entry suppressions tuple (waiver + baseline)."""
    findings = (
        Finding(
            id="license:GPL-3.0-only:numpy@1.26.4",
            axis=AXIS_LICENSE,
            message="denied license",
            subject="numpy",
            severity=None,
            license=LicenseInfo(
                expression="GPL-3.0-only", family=None, verdict=LicenseVerdict.DENIED
            ),
        ),
        Finding(
            id="license:unknown:mystery@0.1.0",
            axis=AXIS_LICENSE,
            message="unresolvable license",
            subject="mystery",
            severity=None,
            license=LicenseInfo(
                expression="unknown", family="permissive", verdict=LicenseVerdict.UNKNOWN
            ),
        ),
        Finding(
            id="currency:eol:django@1.11.29",
            axis=AXIS_CURRENCY,
            message="eol",
            subject="django",
            severity=None,
            currency=CurrencyInfo(
                verdict=CurrencyVerdict.EOL,
                latest="5.0",
                lag=9,
                eol_date="2020-04-01",
                tier="endoflife-date",
            ),
        ),
        Finding(
            id="currency:over-lag:requests@2.10.0",
            axis=AXIS_CURRENCY,
            message="behind latest",
            subject="requests",
            severity=None,
            currency=CurrencyInfo(
                verdict=CurrencyVerdict.SUPPORTED,
                latest="2.31.0",
                lag=5,
                eol_date="2099-01-01",
                tier="channel-n-n-1",
            ),
        ),
        Finding(
            id="vuln:GHSA-xxxx-yyyy:pkg@1.0.0",
            axis=AXIS_VULNERABILITY,
            message="known vuln",
            subject="pkg",
            severity=Severity(tier=SeverityTier.HIGH, raw="CVSS:3.1/AV:N"),
            kev=True,
            kev_date="2021-06-01",
            epss=Epss(score=0.5, percentile=0.9),
        ),
    )
    suppressions = (
        SuppressedFinding(
            finding_id="license:GPL-3.0-only:numpy@1.26.4",
            origin="waiver",
            reason="tracked in ticket",
            authorized_by="alice",
            expires_at="2027-01-01T00:00:00Z",
        ),
        SuppressedFinding(
            finding_id="currency:eol:django@1.11.29",
            origin="baseline",
            reason="bulk-accepted",
        ),
    )
    return dataclasses.replace(
        _sample_report(),
        status=Status.POLICY_VIOLATION,
        status_driver=StatusDriver(
            axis=AXIS_LICENSE, finding_id="license:GPL-3.0-only:numpy@1.26.4"
        ),
        exit_code=1,
        findings=findings,
        suppressions=suppressions,
    )


def test_report_with_new_fields_populated_is_twice_run_deterministic():
    """NFR-R3b: two independent constructions of a report populating ALL the
    new 6.1 fields serialize byte-identically. The heterogeneous finding set
    (some license-only, some currency-only, one vuln-only) sorts without any
    cross-type comparison error — a TypeError there would surface as this
    call raising, not a mismatch."""
    first = json.dumps(_report_with_all_new_fields().to_json_dict(), sort_keys=True)
    second = json.dumps(_report_with_all_new_fields().to_json_dict(), sort_keys=True)
    assert first.encode("utf-8") == second.encode("utf-8")


def test_shipped_shape_report_renders_new_fields_null_and_empty():
    """Backward-compat guard: a report that sets NONE of the new fields
    serializes with epss/license/currency/kev_date null on every finding and
    empty/null suppressions + feed sections (the epss-always-null,
    behavior-neutral claim for shipped scans)."""
    finding = Finding(
        id="vuln:GHSA-abcd:requests@2.31.0",
        axis=AXIS_VULNERABILITY,
        message="known vulnerability",
        subject="requests",
        severity=None,
    )
    document = dataclasses.replace(
        _sample_report(),
        status=Status.WARN,
        status_driver=StatusDriver(axis=AXIS_VULNERABILITY, finding_id=finding.id),
        exit_code=0,
        findings=(finding,),
    ).to_json_dict()
    (rendered,) = document["findings"]
    assert rendered["epss"] is None
    assert rendered["license"] is None
    assert rendered["currency"] is None
    assert rendered["kev_date"] is None
    assert document["suppressions"] == []
    assert document["license_data"] is None
    assert document["currency_data"] is None
    assert document["kev_data"] is None
    assert document["epss_data"] is None
