"""Conformance tests — the CycloneDX 1.6 SBOM projection (Story 4.1).

Mirrors ``test_report_schema.py``'s pattern: hand-built MINIMAL
``ResolvedInventory``/``ComplianceReport`` objects (never a full
end-to-end scan) validated against the CycloneDX 1.6 schema via
``JsonStrictValidator``. NFR-I1's report-schema assertion already exists
(Story 1.1) -- this file only asserts the SBOM's own CycloneDX validity,
never a second report-schema conformance test (see the story spec's
Boundaries & Constraints).
"""

from __future__ import annotations

import json

from cyclonedx.schema import SchemaVersion
from cyclonedx.validation.json import JsonStrictValidator

from pyforge.warden.inventory import ResolvedInventory
from pyforge.warden.models import (
    AXIS_HYGIENE,
    AXIS_VULNERABILITY,
    AxisCoverage,
    ComplianceReport,
    Ecosystem,
    IdentitySource,
    Status,
    VulnData,
)
from pyforge.warden.sbom import render_cyclonedx

_VALIDATOR = JsonStrictValidator(SchemaVersion.V1_6)


def _coverage(
    *, deps_total: int = 0, deps_assessed: int = 0
) -> tuple[AxisCoverage, ...]:
    return (
        AxisCoverage(
            axis=AXIS_HYGIENE,
            manifests_found=1,
            manifests_parsed=1,
            deps_total=deps_total,
            deps_assessed=deps_assessed,
            resolution_depth="direct-only",
        ),
        AxisCoverage(
            axis=AXIS_VULNERABILITY,
            manifests_found=1,
            manifests_parsed=1,
            deps_total=deps_total,
            deps_assessed=deps_assessed,
            resolution_depth="direct-only",
        ),
    )


def make_report(
    *, coverage: tuple[AxisCoverage, ...] | None = None, inventory_count: int = 0
) -> ComplianceReport:
    return ComplianceReport(
        schema_version="1.0.0",
        tool_name="warden",
        tool_version="0.1.0",
        status=Status.CLEAN,
        status_driver=None,
        exit_code=0,
        findings=(),
        coverage=coverage if coverage is not None else _coverage(),
        vuln_data=VulnData(source=None, snapshot_at=None, max_age_ok=None),
        inventory_count=inventory_count,
        resolved_scan_set=(),
        errors=(),
    )


def validate(document_str: str) -> None:
    error = _VALIDATOR.validate_str(document_str)
    assert error is None, error


def test_schema_version_and_bom_format():
    inventory = ResolvedInventory(components=(), resolved_scan_set=())
    document = json.loads(render_cyclonedx(inventory, make_report()))
    assert document["bomFormat"] == "CycloneDX"
    assert document["specVersion"] == "1.6"


def test_empty_inventory_validates():
    inventory = ResolvedInventory(components=(), resolved_scan_set=())
    document_str = render_cyclonedx(inventory, make_report(inventory_count=0))
    validate(document_str)
    document = json.loads(document_str)
    assert document.get("components", []) == []
    assert document["metadata"]["component"]["type"] == "application"


def test_minimal_populated_inventory_validates(component_factory):
    component = component_factory(name="requests", version="2.31.0")
    inventory = ResolvedInventory(components=(component,), resolved_scan_set=())
    report = make_report(
        coverage=_coverage(deps_total=1, deps_assessed=1), inventory_count=1
    )
    document_str = render_cyclonedx(inventory, report)
    validate(document_str)
    document = json.loads(document_str)
    assert len(document["components"]) == 1
    assert document["components"][0]["purl"] == "pkg:pypi/requests@2.31.0"


def test_rich_inventory_across_ecosystems_and_identity_sources_validates(
    component_factory,
):
    components = (
        component_factory(name="requests", version="2.31.0"),
        component_factory(
            name="numpy",
            version="1.26.0",
            ecosystem=Ecosystem.CONDA,
            identity_source=IdentitySource.MAP,
            mapping_confidence="verified",
        ),
        component_factory(
            name="unmapped-conda-pkg",
            version="1.0.0",
            ecosystem=Ecosystem.CONDA,
            pypi_identity=None,
            identity_source=IdentitySource.NONE,
            mapping_confidence=None,
        ),
    )
    inventory = ResolvedInventory(components=components, resolved_scan_set=())
    report = make_report(
        coverage=_coverage(deps_total=3, deps_assessed=3), inventory_count=3
    )
    document_str = render_cyclonedx(inventory, report)
    validate(document_str)
    document = json.loads(document_str)
    assert len(document["components"]) == 3
    assert len(document["dependencies"]) == 4  # 3 leaves + 1 root->all edge


def test_additive_cfe_property_still_validates(component_factory):
    """CycloneDX's own extensibility model: ``properties[]`` is an
    open-ended name/value bag by spec (unlike this repo's own report
    schema's separate additive-growth precedent), so a brand-new,
    currently-unused ``cfe:*`` property (simulating a future story's
    addition) must still validate."""
    component = component_factory(name="requests", version="2.31.0")
    inventory = ResolvedInventory(components=(component,), resolved_scan_set=())
    report = make_report(
        coverage=_coverage(deps_total=1, deps_assessed=1), inventory_count=1
    )
    document = json.loads(render_cyclonedx(inventory, report))
    document["components"][0].setdefault("properties", []).append(
        {"name": "cfe:future-field", "value": "anything"}
    )
    document["metadata"].setdefault("properties", []).append(
        {"name": "cfe:another-future-field", "value": "anything"}
    )
    validate(json.dumps(document))


def test_malformed_document_rejected():
    """The validator itself is strict -- a structurally invalid document
    (missing the required bomFormat/specVersion pair) must fail, proving
    ``validate()``'s ``None``-return-on-success convention is meaningful."""
    error = _VALIDATOR.validate_str(json.dumps({"components": []}))
    assert error is not None
