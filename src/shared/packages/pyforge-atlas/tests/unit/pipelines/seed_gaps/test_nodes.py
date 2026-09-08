"""Per-node fixtures for the four seed-gap suggesters (Story B6, AC-1).

Each pure node over a small fixture input produces the expected proposals +
tiers (lts exact/likely; cwe strong/weak on the ported keyword heuristic; spdx
add-to-schema/non-standard/upstream-drift; license-map likely/report), an
empty input degrades to an empty report, and every report carries the
documented columns. The ``classify`` logic is a VERBATIM port of the shipped
read-only CLIs, so these fixtures pin the ported contract.
"""

from __future__ import annotations

import pandas as pd

from pyforge.atlas.pipelines.seed_gaps import nodes as N

_LTS_COLS = ["conda_name", "pypi_name", "slug", "confidence", "matched_via"]
_CWE_COLS = ["cwe_id", "cwe_name", "category", "confidence", "matched"]
_SPDX_COLS = ["license", "spdx_id", "packages", "tier"]
_LICMAP_COLS = ["license_raw", "packages", "candidates", "confidence", "suggested_spdx"]


# -- report_lts_registry_gap ------------------------------------------------

def test_lts_exact_and_likely_and_registry_exclusion():
    seed = {"products": {"django": {"slug": "django", "aliases": ["Django"]}}}
    core = pd.DataFrame({"conda_name": ["numpy", "python-foo", "django", "orphan"]})
    mapping = pd.DataFrame(
        {"conda_name": ["numpy"], "pypi_name": ["numpy"], "match_source": ["parselmouth"]}
    )
    eol = ["numpy", "foo", "django"]

    df = N.report_lts_registry_gap(seed, eol, core, mapping)

    assert list(df.columns) == _LTS_COLS
    rows = {r["conda_name"]: r for r in df.to_dict("records")}
    # exact: conda_name == slug
    assert rows["numpy"]["confidence"] == "exact"
    assert rows["numpy"]["slug"] == "numpy"
    assert rows["numpy"]["matched_via"] == "conda_name == slug"
    # likely: stripped python- prefix
    assert rows["python-foo"]["confidence"] == "likely"
    assert rows["python-foo"]["slug"] == "foo"
    # django is registry-covered (an exact slug hit too) → excluded, and the
    # unmatched 'orphan' produces no row.
    assert "django" not in rows
    assert "orphan" not in rows


def test_lts_empty_feed_and_empty_candidates_give_empty_report():
    seed = {"products": {}}
    core = pd.DataFrame({"conda_name": ["numpy"]})
    mapping = pd.DataFrame(columns=["conda_name", "pypi_name"])
    # empty slug feed → empty
    empty_feed = N.report_lts_registry_gap(seed, [], core, mapping)
    assert empty_feed.empty and list(empty_feed.columns) == _LTS_COLS
    # empty candidates → empty
    empty_cand = N.report_lts_registry_gap(seed, ["numpy"], pd.DataFrame(), mapping)
    assert empty_cand.empty and list(empty_cand.columns) == _LTS_COLS


# -- report_cwe_seed_gap ----------------------------------------------------

def test_cwe_strong_weak_and_seed_exclusion():
    seed = {"_doc": {"note": "meta"}, "CWE-89": "Injection"}
    vcwe = pd.DataFrame(
        {
            "cwe_id": ["CWE-89", "CWE-22", "CWE-502", "CWE-000"],
            "cwe_name": [
                "SQL Injection",            # seeded → excluded
                "Path Traversal",           # strong
                "Deserialization foobar",   # weak (serialization)
                "Totally unclassifiable",   # no hit → dropped
            ],
            "category": ["Other", "Other", "Other", "Other"],
        }
    )

    df = N.report_cwe_seed_gap(seed, vcwe)

    assert list(df.columns) == _CWE_COLS
    rows = {r["cwe_id"]: r for r in df.to_dict("records")}
    assert "CWE-89" not in rows  # seeded exclusion
    assert rows["CWE-22"]["confidence"] == "strong"
    assert rows["CWE-22"]["category"] == "Traversal"
    assert rows["CWE-502"]["confidence"] == "weak"
    assert rows["CWE-502"]["category"] == "Injection"
    assert "CWE-000" not in rows


def test_cwe_only_other_rows_are_candidates():
    seed = {}
    vcwe = pd.DataFrame(
        {
            "cwe_id": ["CWE-22", "CWE-79"],
            "cwe_name": ["Path Traversal", "Cross-site Scripting"],
            "category": ["Traversal", "Other"],  # CWE-22 already categorized
        }
    )
    df = N.report_cwe_seed_gap(seed, vcwe)
    ids = set(df["cwe_id"])
    assert ids == {"CWE-79"}  # only the 'Other' row is a candidate


def test_cwe_empty_input_gives_empty_report():
    df = N.report_cwe_seed_gap({}, pd.DataFrame())
    assert df.empty and list(df.columns) == _CWE_COLS


# -- report_spdx_schema_gap -------------------------------------------------

def test_spdx_add_nonstandard_and_drift_tiers():
    schema = {"enum": ["MIT", "Apache-2.0"]}
    upstream = {
        "licenses": [
            {"licenseId": "MIT"},
            {"licenseId": "BSD-3-Clause"},
            {"licenseId": "GPL-2.0-only"},
        ]
    }
    core = pd.DataFrame(
        {
            "conda_name": ["a", "b", "c"],
            "conda_license": ["BSD-3-Clause", "BSD-3-Clause", "FooBarLicense"],
        }
    )

    df = N.report_spdx_schema_gap(schema, upstream, core)

    assert list(df.columns) == _SPDX_COLS
    by_tier: dict[str, list[dict]] = {}
    for r in df.to_dict("records"):
        by_tier.setdefault(r["tier"], []).append(r)
    # add-to-schema: BSD-3-Clause is a real upstream id missing from vendored,
    # ranked by 2 packages
    add = by_tier["add-to-schema"]
    assert len(add) == 1 and add[0]["spdx_id"] == "BSD-3-Clause" and add[0]["packages"] == 2
    # non-standard: FooBarLicense not upstream, report-only
    nonstd = by_tier["non-standard"]
    assert [r["license"] for r in nonstd] == ["FooBarLicense"]
    # upstream-drift: every upstream id absent from vendored (atlas-independent)
    drift = {r["spdx_id"] for r in by_tier["upstream-drift"]}
    assert drift == {"BSD-3-Clause", "GPL-2.0-only"}


def test_spdx_drift_nonempty_without_conda_license():
    """DW-B6-1: no conda_license column → atlas usage empty, but the drift
    partition still carries the staleness (the report is non-empty)."""
    schema = {"enum": ["MIT"]}
    upstream = {"licenses": [{"licenseId": "MIT"}, {"licenseId": "BSD-3-Clause"}]}
    core = pd.DataFrame({"conda_name": ["a"]})  # NO conda_license column

    df = N.report_spdx_schema_gap(schema, upstream, core)

    assert set(df["tier"]) == {"upstream-drift"}
    assert set(df["spdx_id"]) == {"BSD-3-Clause"}


def test_spdx_expression_is_skipped_from_atlas_tiers():
    schema = {"enum": ["MIT"]}
    upstream = {"licenses": [{"licenseId": "MIT"}]}
    core = pd.DataFrame({"conda_name": ["a"], "conda_license": ["MIT OR Apache-2.0"]})
    df = N.report_spdx_schema_gap(schema, upstream, core)
    # the compound expression is skipped; MIT is vendored → no atlas tier rows,
    # and no upstream drift (MIT is vendored) → empty report
    assert df.empty and list(df.columns) == _SPDX_COLS


def test_spdx_empty_upstream_gives_empty_report():
    df = N.report_spdx_schema_gap({"enum": ["MIT"]}, {}, pd.DataFrame())
    assert df.empty and list(df.columns) == _SPDX_COLS


# -- report_license_map_gap -------------------------------------------------

def test_licmap_likely_and_report_tiers():
    schema = {"enum": ["MIT", "Apache-2.0", "BSD-3-Clause"]}
    enriched = pd.DataFrame(
        {
            "license_spdx": [None, None, "MIT", None],
            "license_raw": [
                "the mit license",     # single candidate MIT → likely
                "some weird license",  # no candidate → report
                " MIT ",               # already mapped (license_spdx set) → skipped
                "unknown",             # junk → skipped
            ],
        }
    )

    df = N.report_license_map_gap(schema, enriched)

    assert list(df.columns) == _LICMAP_COLS
    rows = {r["license_raw"]: r for r in df.to_dict("records")}
    assert rows["the mit license"]["confidence"] == "likely"
    assert rows["the mit license"]["suggested_spdx"] == "MIT"
    assert rows["the mit license"]["candidates"] == "MIT"
    assert rows["some weird license"]["confidence"] == "report"
    assert rows["some weird license"]["suggested_spdx"] is None
    assert "unknown" not in rows  # junk
    assert " MIT " not in rows and "MIT" not in rows  # already-mapped skipped


def test_licmap_candidates_serialized_as_comma_string():
    schema = {"enum": ["MIT", "Apache-2.0"]}
    enriched = pd.DataFrame(
        {"license_spdx": [None], "license_raw": ["mit / apache-2.0 dual"]}
    )
    df = N.report_license_map_gap(schema, enriched)
    # two whole-token candidates → a comma-joined string, tier 'report'
    (row,) = df.to_dict("records")
    assert isinstance(row["candidates"], str)
    assert set(row["candidates"].split(",")) == {"MIT", "Apache-2.0"}
    assert row["confidence"] == "report"


def test_licmap_empty_input_gives_empty_report():
    df = N.report_license_map_gap({"enum": ["MIT"]}, pd.DataFrame())
    assert df.empty and list(df.columns) == _LICMAP_COLS


# -- review patch: enum-less schema degrades gracefully (AD-13/AD-15) --------

def test_enum_less_schema_does_not_crash_the_report_nodes():
    """A malformed vendored-schema dict lacking ``enum`` must NOT crash a
    derived report node (a per-rebuild run degrades, never hard-fails)."""
    bad_schema = {"type": "string"}  # no 'enum' key
    # spdx: vendored empty -> every upstream id is drift (non-empty, no crash)
    spdx = N.report_spdx_schema_gap(
        bad_schema, {"licenses": [{"licenseId": "MIT"}]}, pd.DataFrame({"conda_name": ["a"]})
    )
    assert list(spdx.columns) == _SPDX_COLS
    assert set(spdx["tier"]) == {"upstream-drift"}
    # license-map: empty enum -> no candidates -> all 'report' (no crash)
    lic = N.report_license_map_gap(
        bad_schema, pd.DataFrame({"license_spdx": [None], "license_raw": ["weird license"]})
    )
    assert list(lic.columns) == _LICMAP_COLS
    assert set(lic["confidence"]) == {"report"}
