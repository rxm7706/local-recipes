"""Unit tests — the vulnerability engine's non-subprocess logic (Story 1.5):
DB-cache resolution, the CONTENT pre-flight, ``name==version`` input
synthesis (NFR-S6 purity guard), the CVSS-tier mapping table, and
``parse_osv_output``. Story 1.6 adds the severity->rung composition
(``DEFAULT_VULN_SEVERITY_POLICY``, ``status_for_severity_tier``,
``vuln_rung``), unit-tested here alongside the pre-existing coverage.

Synthetic osv JSON / hand-built zips in, ``Finding``s + booleans out — no
real subprocess (``OsvEngine`` itself is exercised in
``tests/conformance/test_osv_engine.py`` against the real binary). The
content pre-flight's VALID-DB case reuses the Story 1.4 fixture builder
(``tests/fixtures/osv_db_builder.build_offline_db``), imported BY PATH
exactly like ``test_osv_offline_db_spike.py`` does — never imported as a
package (the fixtures dir is test data, not shipped in the built package).
"""

from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

from pyforge.warden.inventory import PypiIdentity
from pyforge.warden.models import (
    AXIS_VULNERABILITY,
    Ecosystem,
    ErrorKind,
    Finding,
    Severity,
    SeverityTier,
    Status,
    StatusDriver,
)
from pyforge.warden.vuln import (
    DEFAULT_VULN_SEVERITY_POLICY,
    OSV_DB_CACHE_ENV_VAR,
    OsvParse,
    SynthesizedInput,
    _cvss_score_to_tier,
    _db_has_valid_advisory,
    _is_valid_osv_advisory,
    _synthesize_requirements,
    db_zip_path,
    offline_db_unavailable_finding,
    parse_osv_output,
    resolve_cache_dir,
    status_for_severity_tier,
    unsafe_identity_finding,
    vuln_rung,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
OSV_RECORDS_DIR = FIXTURES / "osv-db" / "pypi"
FIXTURE_ADVISORY_ID = "PDOS-FIXTURE-0001"
FIXTURE_PACKAGE = "pdos-vuln-fixture"


def _load_builder():
    """Import ``fixtures/osv_db_builder`` by path — mirrors
    ``test_osv_offline_db_spike.py``'s ``_load_builder()``; production code
    never imports this module."""
    module_path = FIXTURES / "osv_db_builder.py"
    spec = importlib.util.spec_from_file_location("osv_db_builder", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- resolve_cache_dir / db_zip_path -----------------------------------------


def test_resolve_cache_dir_reads_the_env_var():
    assert resolve_cache_dir(env={OSV_DB_CACHE_ENV_VAR: "/some/cache"}) == "/some/cache"


def test_resolve_cache_dir_is_none_when_unset():
    assert resolve_cache_dir(env={}) is None


def test_resolve_cache_dir_is_none_when_empty_string():
    assert resolve_cache_dir(env={OSV_DB_CACHE_ENV_VAR: ""}) is None


def test_db_zip_path_uses_the_exact_case_sensitive_PyPI_segment():
    path = db_zip_path("/cache", Ecosystem.PYPI)
    assert path == Path("/cache/osv-scanner/PyPI/all.zip")
    # NOT the lowercase Ecosystem enum value (decision record § 4 / M1).
    assert "pypi" not in path.parts


def test_db_zip_path_unmapped_ecosystem_is_none():
    # v1 only maps PyPI; CONDA has no osv-dir mapping yet (Epic 2).
    assert db_zip_path("/cache", Ecosystem.CONDA) is None


# --- content pre-flight: _is_valid_osv_advisory (the per-entry shape check) --


def test_valid_advisory_shape_with_versions_passes():
    record = {
        "id": "GHSA-xxxx",
        "affected": [
            {
                "package": {"ecosystem": "PyPI", "name": "foo"},
                "versions": ["1.0.0"],
            }
        ],
    }
    assert _is_valid_osv_advisory(record, "PyPI") is True


def test_valid_advisory_shape_with_ranges_passes():
    record = {
        "id": "GHSA-xxxx",
        "affected": [
            {
                "package": {"ecosystem": "PyPI", "name": "foo"},
                "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}]}],
            }
        ],
    }
    assert _is_valid_osv_advisory(record, "PyPI") is True


@pytest.mark.parametrize(
    "record",
    [
        {},
        {"id": ""},
        {"id": 123, "affected": []},
        {"id": "x", "affected": "not-a-list"},
        {"id": "x", "affected": [{"package": {"ecosystem": "npm", "name": "foo"}, "versions": ["1"]}]},
        {"id": "x", "affected": [{"package": {"ecosystem": "PyPI", "name": ""}, "versions": ["1"]}]},
        {"id": "x", "affected": [{"package": {"ecosystem": "PyPI", "name": "foo"}, "versions": [""]}]},
        {"id": "x", "affected": [{"package": {"ecosystem": "PyPI", "name": "foo"}}]},
        {"id": "x", "affected": [{"package": {"ecosystem": "PyPI", "name": "foo"}, "ranges": [{}]}]},
        "not-a-dict",
        None,
        123,
    ],
)
def test_invalid_advisory_shapes_fail(record):
    assert _is_valid_osv_advisory(record, "PyPI") is False


# --- content pre-flight: _db_has_valid_advisory (the whole-zip check) -------


def test_preflight_passes_on_the_story_1_4_fixture_db(tmp_path):
    builder = _load_builder()
    cache_root = builder.build_offline_db(OSV_RECORDS_DIR, tmp_path / "cache")
    zip_path = db_zip_path(cache_root, Ecosystem.PYPI)
    assert _db_has_valid_advisory(zip_path) is True


def test_preflight_fails_on_an_absent_directory(tmp_path):
    zip_path = db_zip_path(tmp_path / "does-not-exist", Ecosystem.PYPI)
    assert _db_has_valid_advisory(zip_path) is False


def test_preflight_fails_on_a_present_but_empty_zip(tmp_path):
    db_dir = tmp_path / "cache" / "osv-scanner" / "PyPI"
    db_dir.mkdir(parents=True)
    zip_path = db_dir / "all.zip"
    with zipfile.ZipFile(zip_path, "w"):
        pass  # a valid zip container, zero entries
    assert _db_has_valid_advisory(zip_path) is False


@pytest.mark.parametrize(
    "corrupt_entry",
    [
        b"{}",
        b"{ not valid json ]",
        b'{"id": "PDOS-FIXTURE-0001"}',  # no affected[]
    ],
    ids=["empty-object", "malformed-json", "no-affected"],
)
def test_preflight_fails_on_a_content_corrupt_entry(tmp_path, corrupt_entry):
    """A valid zip CONTAINER whose sole entry is content-corrupt must fail
    the pre-flight even though the container opens fine (the exit-0
    false-green class the decision record documents)."""
    db_dir = tmp_path / "cache" / "osv-scanner" / "PyPI"
    db_dir.mkdir(parents=True)
    zip_path = db_dir / "all.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(f"{FIXTURE_ADVISORY_ID}.json", corrupt_entry)
    assert _db_has_valid_advisory(zip_path) is False


def test_preflight_fails_on_a_container_corrupt_zip(tmp_path):
    db_dir = tmp_path / "cache" / "osv-scanner" / "PyPI"
    db_dir.mkdir(parents=True)
    zip_path = db_dir / "all.zip"
    zip_path.write_bytes(b"not a zip file at all\x00\x01\x02")
    assert _db_has_valid_advisory(zip_path) is False


def test_preflight_tolerates_one_bad_entry_beside_a_good_one(tmp_path):
    """One malformed entry must not mask a good one elsewhere in the zip."""
    db_dir = tmp_path / "cache" / "osv-scanner" / "PyPI"
    db_dir.mkdir(parents=True)
    zip_path = db_dir / "all.zip"
    good = {
        "id": "GHSA-good",
        "affected": [
            {"package": {"ecosystem": "PyPI", "name": "foo"}, "versions": ["1.0"]}
        ],
    }
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("GHSA-bad.json", b"{ not json ]")
        zf.writestr("GHSA-good.json", json.dumps(good))
    assert _db_has_valid_advisory(zip_path) is True


def test_preflight_ignores_non_json_entries(tmp_path):
    """A namelist entry that isn't a .json file (e.g. an index/manifest a
    future osv version might ship) is skipped without even attempting to
    parse it — a good .json entry elsewhere in the zip still passes."""
    db_dir = tmp_path / "cache" / "osv-scanner" / "PyPI"
    db_dir.mkdir(parents=True)
    zip_path = db_dir / "all.zip"
    good = {
        "id": "GHSA-good",
        "affected": [
            {"package": {"ecosystem": "PyPI", "name": "foo"}, "versions": ["1.0"]}
        ],
    }
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("README.txt", b"not json at all, and not even .json-named")
        zf.writestr("GHSA-good.json", json.dumps(good))
    assert _db_has_valid_advisory(zip_path) is True


# --- CVSS v3.1 §5 qualitative severity-rating bands --------------------------


@pytest.mark.parametrize(
    "score,tier",
    [
        ("0.0", SeverityTier.NONE),
        ("0.05", SeverityTier.NONE),
        ("0.1", SeverityTier.LOW),
        ("3.9", SeverityTier.LOW),
        ("3.99", SeverityTier.LOW),
        ("4.0", SeverityTier.MEDIUM),
        ("6.9", SeverityTier.MEDIUM),
        ("6.99", SeverityTier.MEDIUM),
        ("7.0", SeverityTier.HIGH),
        ("8.9", SeverityTier.HIGH),
        ("8.99", SeverityTier.HIGH),
        ("9.0", SeverityTier.CRITICAL),
        ("9.8", SeverityTier.CRITICAL),
        ("10.0", SeverityTier.CRITICAL),
    ],
)
def test_cvss_score_to_tier_bands(score, tier):
    assert _cvss_score_to_tier(score) is tier


@pytest.mark.parametrize(
    "raw_score",
    [None, "", "not-a-number", "nan", "inf", "-inf", 9.8, True, [], {}],
)
def test_cvss_score_to_tier_unparsable_or_absent_is_unknown(raw_score):
    assert _cvss_score_to_tier(raw_score) is SeverityTier.UNKNOWN


# --- NFR-S6 purity guard: _synthesize_requirements ---------------------------


def test_synthesize_requirements_emits_sorted_safe_lines(component_factory):
    components = [
        component_factory(
            name="Zeta",
            version="2.0",
            pypi_identity=PypiIdentity(name="zeta", version="2.0"),
        ),
        component_factory(
            name="Alpha",
            version="1.0",
            pypi_identity=PypiIdentity(name="alpha", version="1.0"),
        ),
    ]
    result = _synthesize_requirements(components)
    assert isinstance(result, SynthesizedInput)
    assert result.lines == ("alpha==1.0", "zeta==2.0")
    assert result.excluded == ()


def test_synthesize_requirements_excludes_leading_dash_name():
    from pyforge.warden.inventory import Component, Provenance
    from pyforge.warden.models import CveMatchLevel, ExtractionMode, IdentitySource

    component = Component(
        name="-rf",
        version="1.0",
        ecosystem=Ecosystem.PYPI,
        pypi_identity=PypiIdentity(name="-rf", version="1.0"),
        identity_source=IdentitySource.NATIVE,
        mapping_confidence=None,
        cve_match_level=CveMatchLevel.EXACT,
        extraction_mode=ExtractionMode.PARSED,
        purl="pkg:pypi/-rf@1.0",
        provenance=(Provenance(manifest="pyproject.toml", section="dependencies"),),
        hygiene_covered=True,
        vuln_matchable=True,
        indeterminate_reason=None,
    )
    result = _synthesize_requirements([component])
    assert result.lines == ()
    assert result.excluded == (component,)


def test_synthesize_requirements_excludes_leading_dash_version(component_factory):
    component = component_factory(
        name="foo",
        version="1.0",
        pypi_identity=PypiIdentity(name="foo", version="-1.0"),
    )
    result = _synthesize_requirements([component])
    assert result.lines == ()
    assert result.excluded == (component,)


@pytest.mark.parametrize(
    "unsafe_version",
    ["1.0; rm -rf /", "1.0 ", "1.0\n", "1.0/../", "1.0@evil", "1.0 && echo hi"],
)
def test_synthesize_requirements_excludes_unsafe_token_chars(
    component_factory, unsafe_version
):
    component = component_factory(
        name="foo",
        version="1.0",
        pypi_identity=PypiIdentity(name="foo", version=unsafe_version),
    )
    result = _synthesize_requirements([component])
    assert result.lines == ()
    assert result.excluded == (component,)


def test_synthesize_requirements_safe_token_charset_accepts_dots_underscores_hyphens(
    component_factory,
):
    component = component_factory(
        name="foo",
        version="1.0",
        pypi_identity=PypiIdentity(name="foo_bar.baz-qux", version="1.0.0-rc.1"),
    )
    result = _synthesize_requirements([component])
    assert result.lines == ("foo_bar.baz-qux==1.0.0-rc.1",)
    assert result.excluded == ()


def test_unsafe_identity_finding_id_grammar(component_factory):
    component = component_factory(name="-rf", version="1.0")
    finding = unsafe_identity_finding(component)
    assert finding.id == "indeterminate:unsafe-identity:-rf@1.0"
    assert finding.axis == AXIS_VULNERABILITY
    assert finding.subject == "-rf"


def test_offline_db_unavailable_finding_id_grammar(component_factory):
    component = component_factory(name="requests", version="2.31.0")
    finding = offline_db_unavailable_finding(component)
    assert finding.id == "indeterminate:offline-db-unavailable:requests@2.31.0"
    assert finding.axis == AXIS_VULNERABILITY


def test_indeterminate_finding_id_includes_version_to_avoid_cross_version_collision(
    component_factory,
):
    """Two components sharing a name but differing by version are a
    legitimate, distinct inventory state (inventory.py: 'distinct versions
    of the same name stay distinct'). A name-only id would collide and
    DefaultPolicy's engine-finding dedup would silently drop the second
    one's finding — the version segment (or 'unspecified' for a
    version-less component) keeps their ids distinct."""
    older = component_factory(name="requests", version="2.25.0")
    newer = component_factory(name="requests", version="2.31.0")
    finding_older = offline_db_unavailable_finding(older)
    finding_newer = offline_db_unavailable_finding(newer)
    assert finding_older.id != finding_newer.id
    assert finding_older.id == "indeterminate:offline-db-unavailable:requests@2.25.0"
    assert finding_newer.id == "indeterminate:offline-db-unavailable:requests@2.31.0"


# --- parse_osv_output ---------------------------------------------------------


def _doc(*packages: dict) -> str:
    return json.dumps({"results": [{"packages": list(packages)}]})


def _package(
    name: str,
    version: str,
    *,
    ids: list[str],
    max_severity: str | None,
    vulnerabilities: list[dict] | None = None,
) -> dict:
    return {
        "package": {"name": name, "version": version, "ecosystem": "PyPI"},
        "groups": [{"ids": ids, "aliases": ids, "max_severity": max_severity}],
        "vulnerabilities": vulnerabilities or [],
    }


def test_parse_osv_output_emits_one_finding_per_group_id():
    raw = _doc(
        _package(
            "pdos-vuln-fixture",
            "1.0.0",
            ids=["PDOS-FIXTURE-0001"],
            max_severity="9.8",
            vulnerabilities=[
                {
                    "id": "PDOS-FIXTURE-0001",
                    "severity": [
                        {
                            "type": "CVSS_V3",
                            "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                        }
                    ],
                }
            ],
        )
    )
    parse = parse_osv_output(raw)
    assert isinstance(parse, OsvParse)
    assert parse.errors == ()
    (finding,) = parse.findings
    assert finding.id == "vuln:PDOS-FIXTURE-0001:pdos-vuln-fixture@1.0.0"
    assert finding.axis == AXIS_VULNERABILITY
    assert finding.subject == "pdos-vuln-fixture"
    assert finding.severity.tier is SeverityTier.CRITICAL
    assert finding.severity.raw == "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"


def test_parse_osv_output_attributes_group_max_severity_to_every_aliased_id():
    """max_severity is per-GROUP; every id in the group's ids[] gets that
    tier attributed (conservative — never under-claims severity), even an
    alias with no matching vulnerabilities[] record (severity.raw is None
    for it)."""
    raw = _doc(
        _package(
            "foo",
            "1.0",
            ids=["GHSA-primary", "CVE-alias"],
            max_severity="9.5",
            vulnerabilities=[
                {
                    "id": "GHSA-primary",
                    "severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/PRIMARY"}],
                }
                # No record for CVE-alias.
            ],
        )
    )
    parse = parse_osv_output(raw)
    by_id = {f.id: f for f in parse.findings}
    assert set(by_id) == {
        "vuln:GHSA-primary:foo@1.0",
        "vuln:CVE-alias:foo@1.0",
    }
    assert by_id["vuln:GHSA-primary:foo@1.0"].severity.tier is SeverityTier.CRITICAL
    assert by_id["vuln:GHSA-primary:foo@1.0"].severity.raw == "CVSS:3.1/PRIMARY"
    assert by_id["vuln:CVE-alias:foo@1.0"].severity.tier is SeverityTier.CRITICAL
    assert by_id["vuln:CVE-alias:foo@1.0"].severity.raw is None


def test_parse_osv_output_findings_are_sorted_by_id():
    raw = _doc(
        _package("zzz-pkg", "1.0", ids=["ZZZ-0001"], max_severity="5.0"),
        _package("aaa-pkg", "1.0", ids=["AAA-0001"], max_severity="5.0"),
    )
    parse = parse_osv_output(raw)
    ids = [f.id for f in parse.findings]
    assert ids == sorted(ids)


def test_parse_osv_output_no_vulnerabilities_is_empty_and_error_free():
    raw = json.dumps({"results": []})
    parse = parse_osv_output(raw)
    assert parse.findings == ()
    assert parse.errors == ()


def test_parse_osv_output_missing_version_degrades_to_unspecified():
    raw = json.dumps(
        {
            "results": [
                {
                    "packages": [
                        {
                            "package": {"name": "foo", "ecosystem": "PyPI"},
                            "groups": [{"ids": ["GHSA-x"], "max_severity": "1.0"}],
                            "vulnerabilities": [],
                        }
                    ]
                }
            ]
        }
    )
    parse = parse_osv_output(raw)
    (finding,) = parse.findings
    assert finding.id == "vuln:GHSA-x:foo@unspecified"


def test_parse_osv_output_empty_string_is_unparseable():
    parse = parse_osv_output("")
    assert parse.findings == ()
    (error,) = parse.errors
    assert error.kind is ErrorKind.ENGINE_OUTPUT_UNPARSEABLE


def test_parse_osv_output_invalid_json_is_unparseable():
    parse = parse_osv_output("{ not valid json ]")
    assert parse.findings == ()
    (error,) = parse.errors
    assert error.kind is ErrorKind.ENGINE_OUTPUT_UNPARSEABLE


def test_parse_osv_output_non_object_top_level_is_unparseable():
    parse = parse_osv_output("[1, 2, 3]")
    assert parse.findings == ()
    (error,) = parse.errors
    assert error.kind is ErrorKind.ENGINE_OUTPUT_UNPARSEABLE


def test_parse_osv_output_missing_results_key_is_empty_not_an_error():
    """A schema-drifted-but-still-JSON-object document with no 'results' key
    is treated as nothing-to-report, not a parse failure."""
    parse = parse_osv_output(json.dumps({"unexpected": "shape"}))
    assert parse.findings == ()
    assert parse.errors == ()


def test_parse_osv_output_malformed_package_entries_are_skipped_not_crashed():
    raw = json.dumps(
        {
            "results": [
                {"packages": "not-a-list"},
                {"packages": [123, None, "not-a-dict"]},
                {
                    "packages": [
                        {"package": "not-a-dict", "groups": []},
                        {"package": {"name": ""}, "groups": []},  # empty name
                        {"package": {"name": "ok"}, "groups": "not-a-list"},
                    ]
                },
                "not-a-dict-result",
            ]
        }
    )
    parse = parse_osv_output(raw)
    assert parse.findings == ()
    assert parse.errors == ()


def test_parse_osv_output_deduplicates_by_finding_id():
    """The same (advisory-id, package) pair appearing twice (e.g. two
    results[] entries scanning the same lockfile) collapses to one finding."""
    raw = json.dumps(
        {
            "results": [
                {"packages": [_package("foo", "1.0", ids=["GHSA-x"], max_severity="5.0")]},
                {"packages": [_package("foo", "1.0", ids=["GHSA-x"], max_severity="5.0")]},
            ]
        }
    )
    parse = parse_osv_output(raw)
    assert len(parse.findings) == 1


# --- Story 1.6: the default vuln-severity policy table -----------------------


def test_default_vuln_severity_policy_table_is_exactly_critical_plus_four_warns():
    # CRITICAL is the only tier that blocks (policy-violation, FR18's default
    # gate); HIGH/MEDIUM/LOW/NONE all warn (mirrors 1.3's DEP001-005 ceiling).
    # UNKNOWN is deliberately ABSENT -- an out-of-range/unparseable CVSS score
    # degrades to indeterminate via status_for_severity_tier's fallback,
    # never a silent warn.
    assert DEFAULT_VULN_SEVERITY_POLICY == {
        SeverityTier.CRITICAL: Status.POLICY_VIOLATION,
        SeverityTier.HIGH: Status.WARN,
        SeverityTier.MEDIUM: Status.WARN,
        SeverityTier.LOW: Status.WARN,
        SeverityTier.NONE: Status.WARN,
    }
    assert SeverityTier.UNKNOWN not in DEFAULT_VULN_SEVERITY_POLICY


def test_default_vuln_severity_policy_never_maps_to_clean():
    """C0c structural guard: a finding-carrying report must never compose
    clean. Pins the invariant directly (not just today's literal table), so
    a future edit mapping any tier to clean fails here even if the golden
    literal above were updated to match."""
    assert Status.CLEAN not in DEFAULT_VULN_SEVERITY_POLICY.values()


@pytest.mark.parametrize(
    "tier,expected",
    [
        (SeverityTier.CRITICAL, Status.POLICY_VIOLATION),
        (SeverityTier.HIGH, Status.WARN),
        (SeverityTier.MEDIUM, Status.WARN),
        (SeverityTier.LOW, Status.WARN),
        (SeverityTier.NONE, Status.WARN),
    ],
)
def test_status_for_known_severity_tier(tier, expected):
    assert status_for_severity_tier(tier) is expected


def test_unknown_severity_tier_degrades_to_indeterminate_never_clean():
    """An out-of-range/unparseable CVSS score (SeverityTier.UNKNOWN) must
    never false-green."""
    assert status_for_severity_tier(SeverityTier.UNKNOWN) is Status.INDETERMINATE


# --- Story 1.6: vuln_rung -----------------------------------------------------


@pytest.mark.parametrize(
    "tier,expected_status",
    [
        (SeverityTier.CRITICAL, Status.POLICY_VIOLATION),
        (SeverityTier.HIGH, Status.WARN),
        (SeverityTier.MEDIUM, Status.WARN),
        (SeverityTier.LOW, Status.WARN),
        (SeverityTier.NONE, Status.WARN),
        (SeverityTier.UNKNOWN, Status.INDETERMINATE),
    ],
)
def test_vuln_rung_for_each_severity_tier(tier, expected_status):
    finding = Finding(
        id="vuln:GHSA-xxxx:foo@1.0.0",
        axis=AXIS_VULNERABILITY,
        message="foo: GHSA-xxxx",
        subject="foo",
        severity=Severity(tier=tier, raw="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"),
    )
    status, driver = vuln_rung(finding)
    assert status is expected_status
    assert driver == StatusDriver(
        axis=AXIS_VULNERABILITY, finding_id="vuln:GHSA-xxxx:foo@1.0.0"
    )


def test_vuln_rung_with_no_severity_is_indeterminate():
    """A vulnerability-axis finding with severity=None (the axis's own
    indeterminate: withhold findings -- no-version, unsafe-identity,
    offline-db-unavailable) still routes to indeterminate, unchanged from
    the pre-1.6 backstop."""
    finding = Finding(
        id="indeterminate:no-version:leftpad",
        axis=AXIS_VULNERABILITY,
        message="withheld",
        subject="leftpad",
        severity=None,
    )
    status, driver = vuln_rung(finding)
    assert status is Status.INDETERMINATE
    assert driver == StatusDriver(
        axis=AXIS_VULNERABILITY, finding_id="indeterminate:no-version:leftpad"
    )
