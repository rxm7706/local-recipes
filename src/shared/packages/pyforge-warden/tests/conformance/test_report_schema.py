"""Conformance tests — the packaged ComplianceReport schema (Story 1.1).

The dissolved Story 4.2 conformance assertion lives here (NFR-I1/I2, FR28):
a minimal report built via ``models.py`` validates against the packaged
``data/report-schema.json``; the exit enum is closed; ``status.driver`` is
required for non-clean statuses; additive growth never breaks validation;
twice-run serialization is byte-identical.
"""

from __future__ import annotations

import json
from importlib import resources

import jsonschema
import pytest

from pyforge.warden.models import (
    AXIS_HYGIENE,
    AXIS_INGESTION,
    AXIS_VULNERABILITY,
    AxisCoverage,
    ComplianceReport,
    ErrorKind,
    ErrorRecord,
    Finding,
    ScannedManifest,
    Severity,
    SeverityTier,
    Status,
    StatusDriver,
    VulnData,
)

NON_CLEAN_DRIVER_REQUIRED = [
    Status.WARN,
    Status.BYPASSED,
    Status.POLICY_VIOLATION,
    Status.INDETERMINATE,
    Status.ERROR,
]
DRIVER_NULL_OK = [Status.CLEAN, Status.NOT_APPLICABLE]

# The schema-coherent exit code per status (warn shown at its default 0; the
# warn_is_error knob's 1 is also schema-legal).
COHERENT_EXIT = {
    Status.CLEAN: 0,
    Status.NOT_APPLICABLE: 0,
    Status.BYPASSED: 0,
    Status.WARN: 0,
    Status.POLICY_VIOLATION: 1,
    Status.INDETERMINATE: 1,
    Status.ERROR: 2,
}


def load_schema() -> dict:
    schema_file = (
        resources.files("pyforge.warden") / "data" / "report-schema.json"
    )
    return json.loads(schema_file.read_text(encoding="utf-8"))


def validate(document: dict) -> None:
    jsonschema.Draft202012Validator(load_schema()).validate(document)


def make_report(
    *,
    status: Status = Status.CLEAN,
    status_driver: StatusDriver | None = None,
    exit_code: int = 0,
    findings: tuple[Finding, ...] = (),
) -> ComplianceReport:
    return ComplianceReport(
        schema_version="1.0.0",
        tool_name="warden",
        tool_version="0.1.0",
        status=status,
        status_driver=status_driver,
        exit_code=exit_code,
        findings=findings,
        coverage=(
            AxisCoverage(
                axis=AXIS_HYGIENE,
                manifests_found=1,
                manifests_parsed=1,
                deps_total=2,
                deps_assessed=2,
                resolution_depth="direct-only",
            ),
        ),
        vuln_data=VulnData(source=None, snapshot_at=None, max_age_ok=None),
        inventory_count=2,
        resolved_scan_set=(ScannedManifest(path="pyproject.toml", kind="pyproject"),),
        errors=(),
    )


THREE_FAMILY_FINDINGS = (
    Finding(
        id="vuln:GHSA-abcd-1234:requests@2.31.0",
        axis=AXIS_VULNERABILITY,
        message="known vulnerability",
        subject="requests",
        severity=Severity(tier=SeverityTier.CRITICAL, raw="CVSS:3.1/AV:N/AC:L"),
    ),
    Finding(
        id="hygiene:DEP002:leftpad",
        axis=AXIS_HYGIENE,
        message="unused dependency",
        subject="leftpad",
        severity=None,
    ),
    Finding(
        id="indeterminate:no-version:numpy",
        axis=AXIS_VULNERABILITY,
        message="version unresolved; vuln match withheld",
        subject="numpy",
        severity=None,
    ),
)


def test_schema_is_draft_2020_12():
    schema = load_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    jsonschema.Draft202012Validator.check_schema(schema)


def test_minimal_report_validates():
    document = make_report().to_json_dict()
    validate(document)
    assert document["schema_version"] == "1.0.0"


def test_rich_report_validates_across_all_three_finding_families():
    report = make_report(
        status=Status.POLICY_VIOLATION,
        status_driver=StatusDriver(
            axis=AXIS_VULNERABILITY,
            finding_id="vuln:GHSA-abcd-1234:requests@2.31.0",
        ),
        exit_code=1,
        findings=THREE_FAMILY_FINDINGS,
    )
    document = report.to_json_dict()
    validate(document)
    assert [finding["id"] for finding in document["findings"]] == sorted(
        finding.id for finding in THREE_FAMILY_FINDINGS
    )


def test_report_with_typed_error_validates():
    # The error-driver ID grammar is owned by Story 1.7; driver.finding_id is
    # deliberately unconstrained by the schema (and by the model layer — only
    # findings[].id is family-validated), so this placeholder token is legal.
    report = make_report(
        status=Status.ERROR,
        status_driver=StatusDriver(
            axis=AXIS_VULNERABILITY,
            finding_id="error:engine-timeout:osv-scanner",
        ),
        exit_code=2,
    )
    document = report.to_json_dict()
    document["errors"] = [
        {
            "kind": ErrorRecord(
                kind=ErrorKind.ENGINE_TIMEOUT, owner="engines", message="timed out"
            ).kind.value,
            "owner": "engines",
            "message": "timed out",
        }
    ]
    validate(document)


def test_exit_code_enum_is_closed():
    document = make_report().to_json_dict()
    document["exit_code"] = 3
    with pytest.raises(jsonschema.ValidationError):
        validate(document)


@pytest.mark.parametrize(
    ("status", "with_driver", "exit_code"),
    [
        (Status.CLEAN, False, 0),
        (Status.POLICY_VIOLATION, True, 1),
        (Status.ERROR, True, 2),
        (Status.CLEAN, False, 130),
    ],
    ids=["clean-0", "policy-violation-1", "error-2", "sigint-130"],
)
def test_frozen_exit_codes_accepted_in_coherent_pairings(status, with_driver, exit_code):
    driver = (
        StatusDriver(axis=AXIS_HYGIENE, finding_id="hygiene:DEP001:missingmod")
        if with_driver
        else None
    )
    document = make_report(
        status=status, status_driver=driver, exit_code=exit_code
    ).to_json_dict()
    validate(document)


@pytest.mark.parametrize("status", NON_CLEAN_DRIVER_REQUIRED, ids=lambda s: s.value)
def test_null_driver_rejected_for_non_clean_status(status):
    # Mutate the rendered dict — the model layer refuses to CONSTRUCT a
    # driverless non-clean report (ComplianceReport.__post_init__), so the
    # schema check exercises the document, not the dataclass.
    document = make_report().to_json_dict()
    document["status"]["value"] = status.value
    document["exit_code"] = COHERENT_EXIT[status]
    assert document["status"]["driver"] is None
    with pytest.raises(jsonschema.ValidationError):
        validate(document)


@pytest.mark.parametrize("status", DRIVER_NULL_OK, ids=lambda s: s.value)
def test_null_driver_permitted_for_clean_family(status):
    validate(make_report(status=status, status_driver=None).to_json_dict())


@pytest.mark.parametrize("status", NON_CLEAN_DRIVER_REQUIRED, ids=lambda s: s.value)
def test_non_clean_status_with_driver_validates(status):
    report = make_report(
        status=status,
        status_driver=StatusDriver(
            axis=AXIS_HYGIENE, finding_id="hygiene:DEP001:missingmod"
        ),
        exit_code=COHERENT_EXIT[status],
    )
    validate(report.to_json_dict())


def test_additive_extra_fields_still_validate():
    document = make_report().to_json_dict()
    document["future_top_level_field"] = {"anything": [1, 2, 3]}
    document["vuln_data"]["future_nested_field"] = "y"
    document["coverage"][0]["future_axis_metric"] = 42
    validate(document)


def test_malformed_finding_id_rejected():
    document = make_report().to_json_dict()
    document["findings"] = [
        {"id": "not-a-family-id", "axis": AXIS_HYGIENE, "message": "x"}
    ]
    with pytest.raises(jsonschema.ValidationError):
        validate(document)


def test_schema_version_required_and_semver():
    document = make_report().to_json_dict()
    del document["schema_version"]
    with pytest.raises(jsonschema.ValidationError):
        validate(document)
    document = make_report().to_json_dict()
    document["schema_version"] = "v1"
    with pytest.raises(jsonschema.ValidationError):
        validate(document)


def test_unknown_status_value_rejected():
    """The canonical token is 'warn' — 'warnings' is not a rung."""
    document = make_report().to_json_dict()
    document["status"]["value"] = "warnings"
    with pytest.raises(jsonschema.ValidationError):
        validate(document)


def test_unknown_error_kind_rejected():
    document = make_report().to_json_dict()
    document["errors"] = [
        {"kind": "engine-exploded", "owner": "engines", "message": "boom"}
    ]
    with pytest.raises(jsonschema.ValidationError):
        validate(document)


def test_unknown_severity_tier_rejected():
    document = make_report().to_json_dict()
    document["findings"] = [
        {
            "id": "vuln:GHSA-abcd-1234:requests@2.31.0",
            "axis": AXIS_VULNERABILITY,
            "message": "known vulnerability",
            "severity": {"tier": "catastrophic", "raw": None},
        }
    ]
    with pytest.raises(jsonschema.ValidationError):
        validate(document)


def test_error_status_with_exit_zero_rejected():
    """Status/exit coherence: an error verdict can never exit 0."""
    document = make_report().to_json_dict()
    document["status"]["value"] = "error"
    document["status"]["driver"] = {
        "axis": AXIS_VULNERABILITY,
        "finding_id": "error:engine-timeout:osv-scanner",
    }
    document["exit_code"] = 0
    with pytest.raises(jsonschema.ValidationError):
        validate(document)


def test_indeterminate_status_with_exit_zero_accepted():
    """Status/exit coherence (Story 1.9): indeterminate is the ONE status
    that widened its legal-exit set — exit 0 is now a coherent pairing
    when the driver is EXACTLY the D2(c) empty-extraction id (the
    --allow-empty exception), mirroring warn's existing multi-exit shape.
    Status stays 'indeterminate', never 'clean'. Uses the real
    empty-extraction-shaped driver (review finding, 2026-07-17 pass 2) —
    a differently-shaped driver no longer qualifies, see
    test_indeterminate_status_with_exit_zero_rejected_for_unrelated_driver."""
    document = make_report(
        status=Status.INDETERMINATE,
        status_driver=StatusDriver(
            axis=AXIS_INGESTION, finding_id="indeterminate:empty-extraction:scan"
        ),
        exit_code=0,
    ).to_json_dict()
    validate(document)
    assert document["status"]["value"] == "indeterminate"


def test_indeterminate_status_with_exit_zero_rejected_for_unrelated_driver():
    """Review finding (2026-07-17, pass 2): the exit-0 exception must not
    leak to every indeterminate cause — only the exact D2(c)
    empty-extraction driver qualifies. A driver merely sharing its
    namespace, or an unrelated indeterminate cause entirely, must still be
    rejected at exit 0. Mutate the rendered dict — the model layer refuses
    to CONSTRUCT this incoherent pairing (ComplianceReport.__post_init__,
    also tightened this pass), so the schema check exercises the document,
    not the dataclass (mirrors test_null_driver_rejected_for_non_clean_status's
    established pattern)."""
    document = make_report(
        status=Status.INDETERMINATE,
        status_driver=StatusDriver(
            axis=AXIS_HYGIENE, finding_id="hygiene:DEP001:missingmod"
        ),
        exit_code=1,
    ).to_json_dict()
    document["exit_code"] = 0
    with pytest.raises(jsonschema.ValidationError):
        validate(document)


def test_policy_violation_status_with_exit_zero_still_rejected():
    """The indeterminate-only widening must not leak to policy-violation —
    splitting the combined allOf clause must not accidentally widen its
    sibling too."""
    document = make_report().to_json_dict()
    document["status"]["value"] = "policy-violation"
    document["status"]["driver"] = {
        "axis": AXIS_HYGIENE,
        "finding_id": "hygiene:DEP001:missingmod",
    }
    document["exit_code"] = 0
    with pytest.raises(jsonschema.ValidationError):
        validate(document)


def test_epss_above_one_rejected():
    document = make_report().to_json_dict()
    document["findings"] = [
        {
            "id": "vuln:GHSA-abcd-1234:requests@2.31.0",
            "axis": AXIS_VULNERABILITY,
            "message": "known vulnerability",
            "epss": 1.5,
        }
    ]
    with pytest.raises(jsonschema.ValidationError):
        validate(document)


def test_max_age_ok_with_null_source_rejected():
    """A concrete max_age_ok verdict implies vuln data was consulted, so its
    provenance must be stated."""
    document = make_report().to_json_dict()
    document["vuln_data"] = {
        "source": None,
        "snapshot_at": "2026-07-12T00:00:00Z",
        "max_age_ok": True,
    }
    with pytest.raises(jsonschema.ValidationError):
        validate(document)


def test_resolution_depth_underscore_spelling_rejected():
    document = make_report().to_json_dict()
    document["coverage"][0]["resolution_depth"] = "direct_only"
    with pytest.raises(jsonschema.ValidationError):
        validate(document)


def test_vuln_family_finding_with_hygiene_axis_rejected():
    document = make_report().to_json_dict()
    document["findings"] = [
        {
            "id": "vuln:GHSA-abcd-1234:requests@2.31.0",
            "axis": AXIS_HYGIENE,
            "message": "known vulnerability",
        }
    ]
    with pytest.raises(jsonschema.ValidationError):
        validate(document)


def test_near_equal_findings_serialize_identically_across_feed_orders():
    """Findings equal on (axis, message) but with distinct ids order
    deterministically — byte-identical across both feed orders. (The original
    same-id tie case is superseded: duplicate finding ids are now a
    construction-time ValueError — follow-up review 2026-07-13 — so id is
    always a total discriminator; see test_duplicate_finding_ids_rejected.)"""
    finding_a = Finding(
        id="hygiene:DEP002:leftpad",
        axis=AXIS_HYGIENE,
        message="unused dependency",
        subject="aaa",
        severity=None,
    )
    finding_b = Finding(
        id="hygiene:DEP002:rightpad",
        axis=AXIS_HYGIENE,
        message="unused dependency",
        subject="bbb",
        severity=None,
    )
    forward = make_report(findings=(finding_a, finding_b)).to_json_dict()
    backward = make_report(findings=(finding_b, finding_a)).to_json_dict()
    assert [f["subject"] for f in forward["findings"]] == ["aaa", "bbb"]
    dump_forward = json.dumps(forward, sort_keys=True)
    dump_backward = json.dumps(backward, sort_keys=True)
    assert dump_forward.encode("utf-8") == dump_backward.encode("utf-8")


def test_twice_run_serialization_is_byte_identical():
    """Fresh objects, findings fed in opposite orders -> identical bytes."""
    first = make_report(
        status=Status.POLICY_VIOLATION,
        status_driver=StatusDriver(
            axis=AXIS_VULNERABILITY,
            finding_id="vuln:GHSA-abcd-1234:requests@2.31.0",
        ),
        exit_code=1,
        findings=THREE_FAMILY_FINDINGS,
    )
    second = make_report(
        status=Status.POLICY_VIOLATION,
        status_driver=StatusDriver(
            axis=AXIS_VULNERABILITY,
            finding_id="vuln:GHSA-abcd-1234:requests@2.31.0",
        ),
        exit_code=1,
        findings=tuple(reversed(THREE_FAMILY_FINDINGS)),
    )
    dump_one = json.dumps(first.to_json_dict(), sort_keys=True)
    dump_two = json.dumps(second.to_json_dict(), sort_keys=True)
    assert dump_one.encode("utf-8") == dump_two.encode("utf-8")
