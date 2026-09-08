"""Story B7 — normalize_intake_to_cyclonedx: the cfe:*/?channel-preservation
HEADLINE (AC-2, AD-10) + resolution depth/fan-out recording (AC-1)."""

from __future__ import annotations

from pyforge.atlas.pipelines.universal_sbom.nodes import normalize_intake_to_cyclonedx


def _props(comp):
    return {p["name"]: p["value"] for p in comp.get("properties", [])}


def test_cfe_namespace_and_channel_qualifier_are_never_stripped():
    """THE HEADLINE (AD-10): a CycloneDX passthrough carrying cfe:* props + a
    ?channel=conda-forge purl round-trips with BOTH preserved verbatim."""
    intake = {
        "format": "cyclonedx",
        "passthrough": True,
        "deps": [
            {
                "name": "numpy",
                "version": "1.26.0",
                "ecosystem": "conda",
                "manifest": "sbom.cdx.json",
                "purl": "pkg:conda/numpy@1.26.0?channel=conda-forge",
                "properties": [
                    {"name": "cfe:gap_status", "value": "CURRENT"},
                    {"name": "cfe:conda_purl", "value": "pkg:conda/numpy@1.26.0?channel=conda-forge"},
                ],
            }
        ],
    }
    resolution = {"resolution": "unresolved", "deps": []}
    bom = normalize_intake_to_cyclonedx(intake, resolution, {})
    comp = bom["components"][0]
    # ?channel qualifier NEVER stripped
    assert comp["purl"] == "pkg:conda/numpy@1.26.0?channel=conda-forge"
    # cfe:* namespace NEVER stripped
    props = _props(comp)
    assert props["cfe:gap_status"] == "CURRENT"
    assert props["cfe:conda_purl"] == "pkg:conda/numpy@1.26.0?channel=conda-forge"


def test_fresh_conda_dep_gains_channel_qualifier():
    """A freshly-parsed conda dep (no incoming purl) gets ?channel=conda-forge added."""
    intake = {"deps": [{"name": "scipy", "version": "1.13.0", "ecosystem": "conda", "manifest": "environment.yml"}]}
    bom = normalize_intake_to_cyclonedx(intake, {"resolution": "unresolved"}, {})
    assert bom["components"][0]["purl"] == "pkg:conda/scipy@1.13.0?channel=conda-forge"


def test_pypi_dep_purl_has_no_channel_qualifier():
    intake = {"deps": [{"name": "rich", "version": "13.7.0", "ecosystem": "pypi", "manifest": "requirements.txt"}]}
    bom = normalize_intake_to_cyclonedx(intake, {"resolution": "unresolved"}, {})
    assert bom["components"][0]["purl"] == "pkg:pypi/rich@13.7.0"


def test_resolved_transitive_deps_are_merged_with_depth_and_fanout():
    """AC-1: a bare requirements.txt resolves to a full transitive set; depth +
    fan-out are recorded as cfe:* metadata."""
    intake = {"deps": [{"name": "flask", "version": None, "ecosystem": "pypi", "manifest": "requirements.txt"}]}
    resolution = {
        "resolution": "resolved",
        "deps": [
            {"name": "jinja2", "version": "3.1.4", "ecosystem": "pypi", "manifest": "resolved"},
            {"name": "werkzeug", "version": "3.0.3", "ecosystem": "pypi", "manifest": "resolved"},
        ],
        "depth": 2,
        "fanout": 2,
    }
    bom = normalize_intake_to_cyclonedx(intake, resolution, {})
    names = {c["name"] for c in bom["components"]}
    assert names == {"flask", "jinja2", "werkzeug"}
    meta = {p["name"]: p["value"] for p in bom["metadata"]["properties"]}
    assert meta["cfe:resolution"] == "resolved"
    assert meta["cfe:resolution_depth"] == "2"
    assert meta["cfe:resolution_fanout"] == "2"


def test_nameless_dep_row_never_crashes_normalize():
    """AD-13 / Edge-MEDIUM: a malformed (injected) resolution row with no name is
    skipped, never a KeyError. The named base dep still normalizes."""
    intake = {"deps": [{"name": "numpy", "version": "1.26.0", "ecosystem": "pypi", "manifest": "requirements.txt"}]}
    resolution = {
        "resolution": "resolved",
        "deps": [{"version": "1.0", "ecosystem": "pypi", "manifest": "resolved"}],  # NO name
        "depth": 1,
        "fanout": 1,
    }
    bom = normalize_intake_to_cyclonedx(intake, resolution, {})  # must NOT raise
    assert {c["name"] for c in bom["components"]} == {"numpy"}


def test_offline_unresolved_marker_recorded_on_the_bom():
    """AC-1 / AD-13: offline -> the BOM is marked unresolved (never a crash)."""
    intake = {"deps": [{"name": "numpy", "version": None, "ecosystem": "pypi", "manifest": "requirements.txt"}]}
    resolution = {"resolution": "unresolved", "reason": "offline: no transitive resolver injected", "deps": []}
    bom = normalize_intake_to_cyclonedx(intake, resolution, {})
    meta = {p["name"]: p["value"] for p in bom["metadata"]["properties"]}
    assert meta["cfe:resolution"] == "unresolved"
    assert "offline" in meta["cfe:resolution_reason"]
    # base deps still normalize
    assert {c["name"] for c in bom["components"]} == {"numpy"}
