"""Story B7 — the six-bucket matcher (AC-4) + the AD-12 produce-not-assemble guard.
Six-bucket classification reproduced VERBATIM on a fixture inventory. Also covers the
review findings: HIGH-1 (ADD membership from the full pypi_universe), MEDIUM-2 (truthful
stale report field), MEDIUM-3 (the G10 bare-match guard)."""

from __future__ import annotations

import time

import pandas as pd

from pyforge.atlas.pipelines.universal_sbom.nodes import (
    classify_bucket,
    cmp_versions,
    match_against_universe,
)


def _fresh_universe(universe_pypi=()):
    """A fresh universe BOM (built now). build_universe_sbom emits ONLY conda
    components in production, so ADD membership must come from pypi_universe — the
    standalone pypi arg here exercises only the DW-B7-3 fallback path."""
    comps = [{"name": p, "purl": f"pkg:pypi/{p}"} for p in universe_pypi]
    return {
        "metadata": {"properties": [{"name": "cfe:atlas_built_at", "value": str(int(time.time()))}]},
        "components": comps,
    }


def _pypi_universe(names):
    """The full PyPI universe membership set (pypi_intelligence.enumerate_pypi_universe
    output columns: pypi_name, last_serial) — the authoritative ADD-path signal."""
    return pd.DataFrame([{"pypi_name": n, "last_serial": 1} for n in names])


def _core():
    # conda_name, latest_version (cf), upstream_version (fixture supplies it, DW-B7-1)
    return pd.DataFrame(
        [
            {"conda_name": "numpy", "latest_version": "1.26.0", "upstream_version": "1.26.0"},   # CURRENT
            {"conda_name": "requests", "latest_version": "2.31.0", "upstream_version": "2.32.0"},  # UPDATE-FEEDSTOCK
            {"conda_name": "rich", "latest_version": "13.7.0", "upstream_version": "13.7.0"},     # UPDATE-PIN
            {"conda_name": "noversion", "latest_version": None, "upstream_version": None},        # UNKNOWN (no cf version)
        ]
    )


def _mapping():
    # numpy is mapped conda<->pypi; flask is deliberately ABSENT (the ADD case must be
    # in the full pypi_universe but UNMATCHED by the mapping).
    return pd.DataFrame([{"pypi_name": "numpy", "conda_name": "numpy"}])


def _bom(components):
    return {"bomFormat": "CycloneDX", "components": components}


def test_all_six_buckets_reproduced_on_a_fixture_inventory():
    """AC-4: one component per bucket -> exactly the shipped six-bucket set. The ADD
    case (flask) is present in the full pypi_universe but unmatched to conda."""
    components = [
        {"name": "numpy", "version": "1.26.0", "purl": "pkg:conda/numpy@1.26.0?channel=conda-forge"},  # CURRENT
        {"name": "requests", "version": "2.31.0", "purl": "pkg:conda/requests@2.31.0?channel=conda-forge"},  # UPDATE-FEEDSTOCK
        {"name": "rich", "version": "13.0.0", "purl": "pkg:conda/rich@13.0.0?channel=conda-forge"},  # UPDATE-PIN
        {"name": "noversion", "version": "1.0", "purl": "pkg:conda/noversion@1.0?channel=conda-forge"},  # UNKNOWN
        {"name": "flask", "version": None, "purl": "pkg:pypi/flask"},  # ADD (pypi in universe, unmatched)
        {"name": "left-pad", "version": "1.0.0", "purl": "pkg:npm/left-pad@1.0.0"},  # ADD-NONPYPI
    ]
    report = match_against_universe(
        _bom(components), _core(), _mapping(), _fresh_universe(), _pypi_universe(["flask", "numpy"]), {}
    )
    by_name = {r["name"]: r["bucket"] for r in report["components"]}
    assert by_name == {
        "numpy": "CURRENT",
        "requests": "UPDATE-FEEDSTOCK",
        "rich": "UPDATE-PIN",
        "noversion": "UNKNOWN",
        "flask": "ADD",
        "left-pad": "ADD-NONPYPI",
    }
    assert set(by_name.values()) == {"ADD", "ADD-NONPYPI", "UPDATE-FEEDSTOCK", "UPDATE-PIN", "CURRENT", "UNKNOWN"}
    assert report["buckets"]["ADD"] == 1 and report["buckets"]["CURRENT"] == 1


def test_add_membership_comes_from_the_full_pypi_universe_not_the_mapping():
    """HIGH-1: a pypi name in the full pypi_universe but NOT in the conda mapping is
    ADD (reachable in production, where build_universe_sbom emits no standalone pypi)."""
    components = [{"name": "flask", "version": None, "purl": "pkg:pypi/flask"}]
    report = match_against_universe(
        _bom(components), _core(), _mapping(), _fresh_universe(), _pypi_universe(["flask"]), {}
    )
    assert report["components"][0]["bucket"] == "ADD"


def test_unmatched_pypi_not_in_universe_is_unknown_never_add():
    components = [{"name": "totally-unknown-pkg", "version": None, "purl": "pkg:pypi/totally-unknown-pkg"}]
    report = match_against_universe(
        _bom(components), _core(), _mapping(), _fresh_universe(), _pypi_universe(["flask"]), {}
    )
    assert report["components"][0]["bucket"] == "UNKNOWN"


def test_g10_bare_match_guard_rejects_a_name_coincidence():
    """MEDIUM-3: a pypi dep `wasmtime` must NOT bind to the same-named conda pkg that
    is mapped to a DIFFERENT pypi project (`wasmtime-py`) — it falls through to ADD."""
    core = pd.DataFrame([{"conda_name": "wasmtime", "latest_version": "45.0.0"}])
    mapping = pd.DataFrame([{"pypi_name": "wasmtime-py", "conda_name": "wasmtime"}])  # different pypi project
    components = [{"name": "wasmtime", "version": None, "purl": "pkg:pypi/wasmtime"}]
    report = match_against_universe(
        _bom(components), core, mapping, _fresh_universe(), _pypi_universe(["wasmtime"]), {}
    )
    row = report["components"][0]
    assert row["bucket"] == "ADD"  # NOT matched to the coincidental conda wasmtime
    assert row["conda_name"] is None


def test_matched_conda_row_carries_channel_qualifier_purl_and_version_comparison():
    components = [{"name": "numpy", "version": "1.26.0", "purl": "pkg:conda/numpy@1.26.0?channel=conda-forge"}]
    report = match_against_universe(_bom(components), _core(), _mapping(), _fresh_universe(), _pypi_universe([]), {})
    row = report["components"][0]
    assert row["conda_purl"] == "pkg:conda/numpy@1.26.0?channel=conda-forge"
    assert row["version_comparison"] == "reliable"


def test_stale_field_is_truthful_under_allow_stale():
    """MEDIUM-2: when allow_stale bypasses a stale/unverifiable atlas, the report must
    still record stale=True (never claim the atlas is fresh when it is not)."""
    now = time.time()
    stale_bom = {
        "metadata": {"properties": [{"name": "cfe:atlas_built_at", "value": str(int(now - 30 * 86400))}]},
        "components": [],
    }
    params = {"freshness": {"stale_after_days": 14}, "sbom": {"now": now, "allow_stale": True}}
    report = match_against_universe(_bom([]), _core(), _mapping(), stale_bom, _pypi_universe([]), params)
    assert report["stale"] is True
    # a missing built_at bypassed by allow_stale is also reported stale
    nostamp = {"metadata": {}, "components": []}
    params["sbom"].pop("now")
    report2 = match_against_universe(_bom([]), _core(), _mapping(), nostamp, _pypi_universe([]), params)
    assert report2["stale"] is True and report2["atlas_built_at"] is None


def test_ad12_matcher_produces_an_input_not_a_compliance_report():
    """AD-12 GUARD: a six-bucket match report (a security INPUT), NEVER a ComplianceReport."""
    report = match_against_universe(_bom([]), _core(), _mapping(), _fresh_universe(), _pypi_universe([]), {})
    assert report["kind"] == "sbom-match-report"
    assert "axes" not in report and "gating" not in report and "exit_code" not in report


def test_cmp_versions_ladder_matches_legacy():
    assert cmp_versions("1.0", "2.0") == (-1, True)
    assert cmp_versions("2.0", "1.0") == (1, True)
    assert cmp_versions("1.0", "1.0") == (0, True)
    assert cmp_versions(None, "1.0") == (None, True)


def test_classify_bucket_verbatim_decision_tree():
    assert classify_bucket({"ecosystem": "pypi", "pinned": None}, None, None, True) == "ADD"
    assert classify_bucket({"ecosystem": "pypi", "pinned": None}, None, None, False) == "UNKNOWN"
    assert classify_bucket({"ecosystem": "conda", "pinned": None}, None, None, False) == "UNKNOWN"
    assert classify_bucket({"ecosystem": "cargo", "pinned": None}, None, None, False) == "ADD-NONPYPI"
    assert classify_bucket({"pinned": "1.0"}, {"cf_latest": None}, None, False) == "UNKNOWN"
    assert classify_bucket({"pinned": "1.0"}, {"cf_latest": "1.0"}, "2.0", False) == "UPDATE-FEEDSTOCK"
    assert classify_bucket({"pinned": "1.0"}, {"cf_latest": "2.0"}, "2.0", False) == "UPDATE-PIN"
    assert classify_bucket({"pinned": "2.0"}, {"cf_latest": "2.0"}, "2.0", False) == "CURRENT"
