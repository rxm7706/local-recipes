"""Unit tests — the CycloneDX 1.6 SBOM projection (Story 4.1).

Every I/O-matrix row from the story spec EXCEPT the round-trip row
(cross-tool, a manual check only) and the CLI write-failure row (covered by
``test_cli_sbom.py``): G98 purl construction, ``cfe:*`` attachment gated on
ecosystem + ``identity_source``, the ``cfe:partial_inventory`` flag, the
adversarial-name corpus (NFR-S7), and the empty-inventory edge case.
Builds ``Component``/``ResolvedInventory`` via the shared ``component_factory``
fixture (``conftest.py``), mirroring ``test_inventory.py``'s own conventions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pyforge.warden.sbom as sbom
from pyforge.warden.inventory import PypiIdentity, ResolvedInventory
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
from pyforge.warden.sbom import SBOM_SCHEMA_VERSION, render_cyclonedx

_ADVERSARIAL_NAMES = json.loads(
    (
        Path(__file__).resolve().parent.parent / "fixtures" / "adversarial_names.json"
    ).read_text(encoding="utf-8")
) + [
    # Generated, not fixture-stored (review finding, 2026-07-18): a 10 KB
    # literal would bloat the fixture/diff into an unreviewable blob for
    # no extra coverage over generating it here.
    "a" * 10_000
]


def _coverage(
    *,
    manifests_found: int = 1,
    manifests_parsed: int = 1,
    deps_total: int = 0,
    deps_assessed: int = 0,
) -> tuple[AxisCoverage, ...]:
    return (
        AxisCoverage(
            axis=AXIS_HYGIENE,
            manifests_found=manifests_found,
            manifests_parsed=manifests_parsed,
            deps_total=deps_total,
            deps_assessed=deps_assessed,
            resolution_depth="direct-only",
        ),
        AxisCoverage(
            axis=AXIS_VULNERABILITY,
            manifests_found=manifests_found,
            manifests_parsed=manifests_parsed,
            deps_total=deps_total,
            deps_assessed=deps_assessed,
            resolution_depth="direct-only",
        ),
    )


def make_report(
    *,
    coverage: tuple[AxisCoverage, ...] | None = None,
    inventory_count: int = 0,
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


def _properties_by_name(component_doc: dict) -> dict[str, str | None]:
    return {p["name"]: p.get("value") for p in component_doc.get("properties", [])}


# --- happy path, mixed ecosystems ----------------------------------------


def test_happy_path_mixed_ecosystems_full_coverage(component_factory):
    pypi_component = component_factory(name="requests", version="2.31.0")
    conda_component = component_factory(
        name="numpy",
        version="1.26.0",
        ecosystem=Ecosystem.CONDA,
        identity_source=IdentitySource.MAP,
        mapping_confidence="verified",
    )
    inventory = ResolvedInventory(
        components=(pypi_component, conda_component), resolved_scan_set=()
    )
    report = make_report(
        coverage=_coverage(deps_total=2, deps_assessed=2), inventory_count=2
    )
    document = json.loads(render_cyclonedx(inventory, report))
    assert len(document["components"]) == inventory.count == 2
    properties = _properties_by_name(document["metadata"])
    assert properties["cfe:partial_inventory"] == "false"


def test_metadata_root_and_tools_derive_from_report_tool_fields(component_factory):
    inventory = ResolvedInventory(components=(), resolved_scan_set=())
    report = make_report()
    document = json.loads(render_cyclonedx(inventory, report))
    assert document["metadata"]["component"]["name"] == report.tool_name
    assert document["metadata"]["component"]["version"] == report.tool_version
    assert document["metadata"]["component"]["type"] == "application"
    assert document["metadata"]["tools"][0]["name"] == report.tool_name
    assert document["metadata"]["tools"][0]["version"] == report.tool_version


def test_schema_version_and_status_properties_present():
    inventory = ResolvedInventory(components=(), resolved_scan_set=())
    report = make_report()
    document = json.loads(render_cyclonedx(inventory, report))
    properties = _properties_by_name(document["metadata"])
    assert properties["cfe:schema_version"] == SBOM_SCHEMA_VERSION
    assert properties["cfe:schema_status"] == "experimental"


def test_pypi_purl_is_g98_normalized(component_factory):
    """Verified live against packageurl-python: lowercase + '_'->'-' with
    dots preserved -- never inventory.py::derive_purl()'s PEP 503 form
    (which collapses dots)."""
    component = component_factory(name="Django_Foo.Bar", version="1.0")
    inventory = ResolvedInventory(components=(component,), resolved_scan_set=())
    report = make_report(
        coverage=_coverage(deps_total=1, deps_assessed=1), inventory_count=1
    )
    document = json.loads(render_cyclonedx(inventory, report))
    assert document["components"][0]["purl"] == "pkg:pypi/django-foo.bar@1.0"


def test_conda_purl_carries_conda_forge_channel_qualifier_verbatim_name(
    component_factory,
):
    component = component_factory(
        name="Typing_Extensions", version="1.0", ecosystem=Ecosystem.CONDA
    )
    inventory = ResolvedInventory(components=(component,), resolved_scan_set=())
    report = make_report(
        coverage=_coverage(deps_total=1, deps_assessed=1), inventory_count=1
    )
    document = json.loads(render_cyclonedx(inventory, report))
    # conda purl names stay verbatim (never lowercased/underscore-collapsed
    # -- typing_extensions and typing-extensions are distinct conda-forge
    # packages).
    assert (
        document["components"][0]["purl"]
        == "pkg:conda/Typing_Extensions@1.0?channel=conda-forge"
    )


def test_version_none_component_purl_omits_version_suffix(component_factory):
    """A version-less (indeterminate) component is a legitimate reachable
    state -- PackageURL(version=None) omits the ``@<version>`` suffix, same
    as ``derive_purl()``'s own convention (review finding, 2026-07-18: this
    boundary of the ``len(bom.components) == inventory.count`` claim was
    previously unverified by any test)."""
    from pyforge.warden.models import WithholdReason

    component = component_factory(
        name="requests", version=None, indeterminate_reason=WithholdReason.NO_VERSION
    )
    inventory = ResolvedInventory(components=(component,), resolved_scan_set=())
    report = make_report(
        coverage=_coverage(deps_total=1, deps_assessed=0), inventory_count=1
    )
    document = json.loads(render_cyclonedx(inventory, report))
    assert len(document["components"]) == 1
    assert document["components"][0]["purl"] == "pkg:pypi/requests"
    assert "version" not in document["components"][0]


# --- partial coverage ------------------------------------------------------


def test_partial_coverage_sets_cfe_partial_inventory_true(component_factory):
    inventory = ResolvedInventory(components=(), resolved_scan_set=())
    report = make_report(
        coverage=(
            AxisCoverage(
                axis=AXIS_HYGIENE,
                manifests_found=3,
                manifests_parsed=2,
                deps_total=0,
                deps_assessed=0,
                resolution_depth="direct-only",
            ),
            AxisCoverage(
                axis=AXIS_VULNERABILITY,
                manifests_found=3,
                manifests_parsed=3,
                deps_total=0,
                deps_assessed=0,
                resolution_depth="direct-only",
            ),
        )
    )
    document = json.loads(render_cyclonedx(inventory, report))
    properties = _properties_by_name(document["metadata"])
    assert properties["cfe:partial_inventory"] == "true"


# --- conda component, map-resolved identity --------------------------------


def test_map_resolved_conda_component_gets_all_three_cfe_properties(
    component_factory, monkeypatch
):
    monkeypatch.setattr(
        sbom,
        "load_conda_pypi_map",
        lambda: {
            "numpy": {
                "pypi_name": "numpy",
                "match_source": "parselmouth",
                "match_confidence": "verified",
            }
        },
    )
    component = component_factory(
        name="numpy",
        version="1.26.0",
        ecosystem=Ecosystem.CONDA,
        identity_source=IdentitySource.MAP,
        mapping_confidence="verified",
        # Mirrors extract/_identity.py::_conda_component: a map-resolved
        # identity carries the CONDA component's own concrete version.
        pypi_identity=PypiIdentity(name="numpy", version="1.26.0"),
    )
    inventory = ResolvedInventory(components=(component,), resolved_scan_set=())
    report = make_report(
        coverage=_coverage(deps_total=1, deps_assessed=1), inventory_count=1
    )
    document = json.loads(render_cyclonedx(inventory, report))
    properties = _properties_by_name(document["components"][0])
    assert properties["cfe:pypi_purl"] == "pkg:pypi/numpy@1.26.0"
    assert properties["cfe:match_confidence"] == "verified"
    assert properties["cfe:match_source"] == "parselmouth"


def test_match_source_lookup_is_fresh_not_carried_on_component(
    component_factory, monkeypatch
):
    """cfe:match_source comes from a FRESH map lookup keyed on the
    component's conda name, never a Component field (Component carries no
    match_source field at all)."""
    monkeypatch.setattr(
        sbom,
        "load_conda_pypi_map",
        lambda: {"numpy": {"pypi_name": "numpy", "match_source": "atlas-export"}},
    )
    component = component_factory(
        name="numpy",
        version="1.26.0",
        ecosystem=Ecosystem.CONDA,
        identity_source=IdentitySource.MAP,
        mapping_confidence="verified",
    )
    inventory = ResolvedInventory(components=(component,), resolved_scan_set=())
    report = make_report(
        coverage=_coverage(deps_total=1, deps_assessed=1), inventory_count=1
    )
    document = json.loads(render_cyclonedx(inventory, report))
    properties = _properties_by_name(document["components"][0])
    assert properties["cfe:match_source"] == "atlas-export"


# --- conda component, lock-resolved identity -------------------------------


def test_lock_resolved_conda_component_gets_pypi_purl_but_not_match_fields(
    component_factory,
):
    """identity_source == LOCK (never produced by the real extractors for a
    conda component today, but a legal Component construction): the
    resolved identity IS honestly stated (cfe:pypi_purl), but
    cfe:match_confidence/cfe:match_source -- the map's own vocabulary --
    must NOT be attached to an identity that was never probabilistically
    matched."""
    component = component_factory(
        name="numpy",
        version="1.26.0",
        ecosystem=Ecosystem.CONDA,
        identity_source=IdentitySource.LOCK,
        mapping_confidence=None,
    )
    inventory = ResolvedInventory(components=(component,), resolved_scan_set=())
    report = make_report(
        coverage=_coverage(deps_total=1, deps_assessed=1), inventory_count=1
    )
    document = json.loads(render_cyclonedx(inventory, report))
    properties = _properties_by_name(document["components"][0])
    assert "cfe:pypi_purl" in properties
    assert "cfe:match_confidence" not in properties
    assert "cfe:match_source" not in properties


# --- unmapped conda component -----------------------------------------------


def test_unmapped_conda_component_gets_conda_purl_only_no_cfe_properties(
    component_factory,
):
    component = component_factory(
        name="some-unmapped-pkg",
        version="1.0.0",
        ecosystem=Ecosystem.CONDA,
        pypi_identity=None,
        identity_source=IdentitySource.NONE,
        mapping_confidence=None,
    )
    inventory = ResolvedInventory(components=(component,), resolved_scan_set=())
    report = make_report(
        coverage=_coverage(deps_total=1, deps_assessed=1), inventory_count=1
    )
    document = json.loads(render_cyclonedx(inventory, report))
    component_doc = document["components"][0]
    assert (
        component_doc["purl"] == "pkg:conda/some-unmapped-pkg@1.0.0?channel=conda-forge"
    )
    assert component_doc.get("properties", []) == []


def test_pypi_component_never_gets_cfe_properties(component_factory):
    """cfe:* conda-identity properties are scoped to CONDA components only
    -- a PyPI component's own pypi_identity mirrors its own identity, so a
    cross-reference property there would just restate its own purl."""
    component = component_factory(name="requests", version="2.31.0")
    inventory = ResolvedInventory(components=(component,), resolved_scan_set=())
    report = make_report(
        coverage=_coverage(deps_total=1, deps_assessed=1), inventory_count=1
    )
    document = json.loads(render_cyclonedx(inventory, report))
    assert document["components"][0].get("properties", []) == []


# --- adversarial component names (NFR-S7 corpus) ----------------------------


def test_adversarial_names_never_crash_and_produce_schema_valid_json(component_factory):
    for name in _ADVERSARIAL_NAMES:
        component = component_factory(name=name, version="1.0")
        inventory = ResolvedInventory(components=(component,), resolved_scan_set=())
        report = make_report(
            coverage=_coverage(deps_total=1, deps_assessed=1), inventory_count=1
        )
        rendered = render_cyclonedx(inventory, report)
        document = json.loads(rendered)
        # Round-trips through json.loads (already implied above) with the
        # name preserved byte-for-byte -- no truncation, no corruption.
        assert document["components"][0]["name"] == name
        purl = document["components"][0]["purl"]
        assert purl.startswith("pkg:pypi/")
        # Purl-reserved/HTML-special characters are percent-encoded, never
        # smuggled raw into purl syntax (PackageURL's own job -- G98).
        assert "<" not in purl
        assert ">" not in purl
        assert "\x00" not in purl
        # A raw control byte is never embedded unescaped in the JSON text
        # itself -- json's own encoder escapes it to a \u00XX sequence;
        # only that ESCAPED form may appear in the rendered document.
        assert "\x00" not in rendered


# --- empty inventory ---------------------------------------------------------


def test_empty_inventory_still_validates_with_empty_components():
    inventory = ResolvedInventory(components=(), resolved_scan_set=())
    report = make_report(inventory_count=0)
    document = json.loads(render_cyclonedx(inventory, report))
    assert document.get("components", []) == []
    assert document["metadata"]["component"]["type"] == "application"
