"""Tests for the Phase G + G' overlay aggregation (v8.6.0 Wave B).

Covers the pure-function `_aggregate_v8_6_0_overlays(affecting, epss_map,
cwe_map) -> (max_epss, max_epss_pct, cwe_top, cwe_json)` used by both
Phase G (`phase_g_vdb_summary`) and Phase G' (`phase_g_prime_per_version_vulns`).

Also covers the `_phase_g_sync_current_rollup` extension that propagates
the 2 new per-version columns (`vuln_max_epss_score`, `vuln_cwe_top`)
from `package_version_vulns` to `packages` at the row's CURRENT
`latest_conda_version`.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


def _load(name: str):
    path = _SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def atlas_mod():
    return _load("conda_forge_atlas")


@pytest.fixture
def schema_conn(atlas_mod, tmp_path):
    db = tmp_path / "atlas.db"
    conn = atlas_mod.open_db(path=db)
    atlas_mod.init_schema(conn)
    yield conn
    conn.close()


# ──────────────────────────────────────────────────────────────────────
# _aggregate_v8_6_0_overlays (pure function)
# ──────────────────────────────────────────────────────────────────────


def test_aggregate_empty_affecting_returns_all_none(atlas_mod):
    assert atlas_mod._aggregate_v8_6_0_overlays([], {}, {}) == (None, None, None, None)


def test_aggregate_empty_maps_returns_none_for_epss_and_cwe(atlas_mod):
    """affecting has CVEs but no epss_map / cwe_map → no overlay signal."""
    affecting = [{"id": "CVE-2024-0001"}, {"id": "CVE-2024-0002"}]
    assert atlas_mod._aggregate_v8_6_0_overlays(affecting, {}, {}) == (None, None, None, None)


def test_aggregate_max_epss_picks_highest(atlas_mod):
    affecting = [
        {"id": "CVE-2024-0001"},
        {"id": "CVE-2024-0002"},
        {"id": "CVE-2024-0003"},
    ]
    epss_map = {
        "CVE-2024-0001": (0.10, 50.0),
        "CVE-2024-0002": (0.94, 99.5),
        "CVE-2024-0003": (0.42, 75.0),
    }
    max_epss, max_pct, _, _ = atlas_mod._aggregate_v8_6_0_overlays(affecting, epss_map, {})
    assert max_epss == pytest.approx(0.94)
    assert max_pct == pytest.approx(99.5)


def test_aggregate_max_epss_ignores_unmapped_cves(atlas_mod):
    """A CVE not in epss_map contributes nothing — doesn't pull max to 0."""
    affecting = [
        {"id": "CVE-2024-0001"},
        {"id": "CVE-9999-NONE"},  # not in map; ignored
    ]
    epss_map = {"CVE-2024-0001": (0.7, 90.0)}
    max_epss, max_pct, _, _ = atlas_mod._aggregate_v8_6_0_overlays(affecting, epss_map, {})
    assert max_epss == pytest.approx(0.7)
    assert max_pct == pytest.approx(90.0)


def test_aggregate_cwe_top_picks_most_frequent(atlas_mod):
    affecting = [
        {"id": "CVE-2024-0001", "cwe": "CWE-79"},
        {"id": "CVE-2024-0002", "cwe": "CWE-79"},
        {"id": "CVE-2024-0003", "cwe": "CWE-79"},
        {"id": "CVE-2024-0004", "cwe": "CWE-22"},
    ]
    cwe_map = {"CWE-79": "Injection", "CWE-22": "Traversal"}
    _, _, cwe_top, cwe_json = atlas_mod._aggregate_v8_6_0_overlays(affecting, {}, cwe_map)
    assert cwe_top == "Injection"
    assert json.loads(cwe_json) == {"Injection": 3, "Traversal": 1}


def test_aggregate_cwe_unknown_buckets_to_other(atlas_mod):
    """A CWE that's not in cwe_map gets bucketed under 'Other' (not dropped).

    Tie-break determinism: Python's `max(iter, key=...)` returns the FIRST
    element at the max value. cwe_counts is built in iteration order of
    `affecting`, so "Injection" (encountered first) wins the tie over
    "Other" (encountered second). This is the documented contract.
    """
    affecting = [
        {"id": "CVE-2024-0001", "cwe": "CWE-79"},
        {"id": "CVE-2024-0002", "cwe": "CWE-99999"},  # not in seed
    ]
    cwe_map = {"CWE-79": "Injection"}
    _, _, cwe_top, cwe_json = atlas_mod._aggregate_v8_6_0_overlays(affecting, {}, cwe_map)
    assert json.loads(cwe_json) == {"Injection": 1, "Other": 1}
    assert cwe_top == "Injection"  # first-encountered wins the tie


def test_aggregate_cwe_tie_break_is_first_encountered(atlas_mod):
    """Inverse: when 'Other' is encountered first, it wins the tie."""
    affecting = [
        {"id": "CVE-2024-0001", "cwe": "CWE-99999"},  # not in seed → Other (FIRST)
        {"id": "CVE-2024-0002", "cwe": "CWE-79"},     # Injection (second)
    ]
    cwe_map = {"CWE-79": "Injection"}
    _, _, cwe_top, _ = atlas_mod._aggregate_v8_6_0_overlays(affecting, {}, cwe_map)
    assert cwe_top == "Other"


def test_aggregate_cwe_none_skipped(atlas_mod):
    """vulns with cwe=None / missing-key don't count toward any bucket."""
    affecting = [
        {"id": "CVE-2024-0001", "cwe": None},
        {"id": "CVE-2024-0002"},  # no cwe key
        {"id": "CVE-2024-0003", "cwe": "CWE-79"},
    ]
    cwe_map = {"CWE-79": "Injection"}
    _, _, cwe_top, cwe_json = atlas_mod._aggregate_v8_6_0_overlays(affecting, {}, cwe_map)
    assert cwe_top == "Injection"
    assert json.loads(cwe_json) == {"Injection": 1}


def test_aggregate_full_signal_all_overlays_active(atlas_mod):
    """Realistic: package with 3 CVEs spanning categories + EPSS scores."""
    affecting = [
        {"id": "CVE-2024-0001", "cwe": "CWE-79"},      # Injection, EPSS 0.5
        {"id": "CVE-2024-0002", "cwe": "CWE-22"},      # Traversal, EPSS 0.9
        {"id": "CVE-2024-0003", "cwe": "CWE-79"},      # Injection, no EPSS
    ]
    epss_map = {
        "CVE-2024-0001": (0.5, 80.0),
        "CVE-2024-0002": (0.9, 99.0),
    }
    cwe_map = {"CWE-79": "Injection", "CWE-22": "Traversal"}
    max_epss, max_pct, cwe_top, cwe_json = atlas_mod._aggregate_v8_6_0_overlays(
        affecting, epss_map, cwe_map
    )
    assert max_epss == pytest.approx(0.9)
    assert max_pct == pytest.approx(99.0)
    assert cwe_top == "Injection"
    assert json.loads(cwe_json) == {"Injection": 2, "Traversal": 1}


# ──────────────────────────────────────────────────────────────────────
# _phase_g_sync_current_rollup — v8.6.0 column propagation
# ──────────────────────────────────────────────────────────────────────


def _seed_pkg(conn, *, conda_name, latest):
    conn.execute(
        "INSERT INTO packages "
        "(conda_name, feedstock_name, latest_conda_version, latest_status, "
        " feedstock_archived, relationship, match_source, match_confidence) "
        "VALUES (?, ?, ?, 'active', 0, 'conda_and_pypi', 'test', 'verified')",
        (conda_name, conda_name, latest),
    )


def _seed_pvv(conn, *, conda_name, version, max_epss=None, cwe_top=None):
    conn.execute(
        "INSERT INTO package_version_vulns "
        "(conda_name, version, vuln_total, vuln_critical_affecting_version, "
        " vuln_high_affecting_version, vuln_kev_affecting_version, "
        " vuln_max_epss_score, vuln_cwe_top, scanned_at) "
        "VALUES (?, ?, 0, 0, 0, 0, ?, ?, 1779999000)",
        (conda_name, version, max_epss, cwe_top),
    )


def test_rollup_sync_propagates_v8_6_0_columns(atlas_mod, schema_conn):
    _seed_pkg(schema_conn, conda_name="pkg-a", latest="1.0.0")
    _seed_pvv(schema_conn, conda_name="pkg-a", version="1.0.0",
              max_epss=0.85, cwe_top="RCE")
    schema_conn.commit()

    n = atlas_mod._phase_g_sync_current_rollup(schema_conn)
    assert n == 1

    row = schema_conn.execute(
        "SELECT vuln_max_epss_score, vuln_cwe_top "
        "FROM packages WHERE conda_name = 'pkg-a'"
    ).fetchone()
    assert row[0] == pytest.approx(0.85)
    assert row[1] == "RCE"


def test_rollup_sync_preserves_existing_when_per_version_null(atlas_mod, schema_conn):
    """When per-version vuln row exists but has NULL EPSS/CWE (e.g. Phase G'
    ran with empty epss_map before fetch-epss was populated), the rollup
    must PRESERVE the existing packages.* values (which Phase G wrote
    directly) rather than clobber them to NULL.

    Mirrors the COALESCE-to-existing pattern the DW12 fix uses for
    vuln_total. The bug-shaped alternative — write-NULL-through —
    silently destroys Phase G's valid signal whenever Phase G' runs in
    an env where fetch-epss / fetch-cwe-catalog hadn't been re-run.
    """
    _seed_pkg(schema_conn, conda_name="pkg-b", latest="2.0.0")
    # Phase G wrote valid values directly into packages
    schema_conn.execute(
        "UPDATE packages SET vuln_max_epss_score = 0.94, vuln_cwe_top = 'RCE' "
        "WHERE conda_name = 'pkg-b'"
    )
    # Phase G' wrote a per-version row with NULL EPSS/CWE
    _seed_pvv(schema_conn, conda_name="pkg-b", version="2.0.0",
              max_epss=None, cwe_top=None)
    schema_conn.commit()

    n = atlas_mod._phase_g_sync_current_rollup(schema_conn)
    assert n == 1  # row matched the EXISTS clause

    row = schema_conn.execute(
        "SELECT vuln_max_epss_score, vuln_cwe_top "
        "FROM packages WHERE conda_name = 'pkg-b'"
    ).fetchone()
    # Existing valid values preserved — NOT clobbered to NULL
    assert row[0] == pytest.approx(0.94)
    assert row[1] == "RCE"


def test_rollup_sync_is_idempotent_with_v8_6_0_columns(atlas_mod, schema_conn):
    _seed_pkg(schema_conn, conda_name="pkg-c", latest="3.0.0")
    _seed_pvv(schema_conn, conda_name="pkg-c", version="3.0.0",
              max_epss=0.42, cwe_top="DoS")
    schema_conn.commit()

    n1 = atlas_mod._phase_g_sync_current_rollup(schema_conn)
    row1 = tuple(schema_conn.execute(
        "SELECT vuln_max_epss_score, vuln_cwe_top FROM packages WHERE conda_name='pkg-c'"
    ).fetchone())
    n2 = atlas_mod._phase_g_sync_current_rollup(schema_conn)
    row2 = tuple(schema_conn.execute(
        "SELECT vuln_max_epss_score, vuln_cwe_top FROM packages WHERE conda_name='pkg-c'"
    ).fetchone())
    assert n1 == n2 == 1
    assert row1 == row2 == (pytest.approx(0.42), "DoS")
