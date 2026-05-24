"""Tests for the CISA KEV fetcher + Phase G overlay (DW13 / Path C).

Background: appthreat-vulnerability-db's aqua.py hardcodes the `kevc`
directory into DEFAULT_IGNORE_SOURCE_PATTERNS, so even a successful
`vdb --cache-os` leaves the KEV signal empty. Path C bypasses vdb for
KEV entirely: `cisa_kev_fetcher.py` pulls the CISA JSON feed directly
into a `cisa_kev` table, and Phase G / G' overlay it on vdb's per-CVE
output.

Covers:
  * `_map_ransomware_use` — Known→1, Unknown→0, anything else→None
  * `upsert_kev_rows` — insert, update, idempotent re-run
  * `_load_kev_cves` — missing table (empty set), empty table, populated
  * Overlay formula — kev=True ALONE, overlay match ALONE, both, neither
"""
from __future__ import annotations

import importlib.util
import sqlite3
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


@pytest.fixture(scope="module")
def fetcher_mod():
    return _load("cisa_kev_fetcher")


@pytest.fixture
def schema_conn(atlas_mod, tmp_path):
    """Fresh atlas conn with the full schema (cisa_kev table included)."""
    db = tmp_path / "atlas.db"
    conn = atlas_mod.open_db(path=db)
    atlas_mod.init_schema(conn)
    yield conn
    conn.close()


# ──────────────────────────────────────────────────────────────────────
# _map_ransomware_use
# ──────────────────────────────────────────────────────────────────────


def test_map_ransomware_use_known(fetcher_mod):
    assert fetcher_mod._map_ransomware_use("Known") == 1
    assert fetcher_mod._map_ransomware_use("known") == 1
    assert fetcher_mod._map_ransomware_use(" KNOWN ") == 1


def test_map_ransomware_use_unknown(fetcher_mod):
    assert fetcher_mod._map_ransomware_use("Unknown") == 0
    assert fetcher_mod._map_ransomware_use("unknown") == 0


def test_map_ransomware_use_other_returns_none(fetcher_mod):
    """Future-proof: CISA could add a new value; surface as NULL so
    SQL queries can `IS NOT NULL` rather than misclassify."""
    assert fetcher_mod._map_ransomware_use(None) is None
    assert fetcher_mod._map_ransomware_use("") is None
    assert fetcher_mod._map_ransomware_use("Likely") is None
    assert fetcher_mod._map_ransomware_use("Suspected") is None


# ──────────────────────────────────────────────────────────────────────
# upsert_kev_rows
# ──────────────────────────────────────────────────────────────────────


def _sample_catalog(vulns=None, version="2026.05.23"):
    return {
        "title": "CISA Catalog of Known Exploited Vulnerabilities",
        "catalogVersion": version,
        "dateReleased": "2026-05-23T11:00:00.000Z",
        "count": len(vulns) if vulns else 0,
        "vulnerabilities": vulns or [],
    }


def _sample_vuln(cve_id, vendor="ACME", product="Widget", ransom="Unknown",
                 cwes=None):
    return {
        "cveID": cve_id,
        "vendorProject": vendor,
        "product": product,
        "vulnerabilityName": f"{vendor} {product} Foo Bar",
        "dateAdded": "2026-05-23",
        "shortDescription": "Test vuln",
        "requiredAction": "Apply mitigations",
        "dueDate": "2026-06-13",
        "knownRansomwareCampaignUse": ransom,
        "notes": "https://example.com/advisory",
        "cwes": cwes,
    }


def test_upsert_inserts_new_rows(fetcher_mod, schema_conn):
    catalog = _sample_catalog([
        _sample_vuln("CVE-2024-0001"),
        _sample_vuln("CVE-2024-0002", ransom="Known"),
    ])
    stats = fetcher_mod.upsert_kev_rows(schema_conn, catalog, fetched_at=1779999000)
    assert stats["rows_in_feed"] == 2
    assert stats["rows_before"] == 0
    assert stats["rows_after"] == 2
    assert stats["rows_new"] == 2
    assert stats["catalog_version"] == "2026.05.23"

    rows = list(schema_conn.execute(
        "SELECT cve_id, vendor, known_ransomware_use, source_fetched_at "
        "FROM cisa_kev ORDER BY cve_id"
    ))
    assert [tuple(r) for r in rows] == [
        ("CVE-2024-0001", "ACME", 0, 1779999000),
        ("CVE-2024-0002", "ACME", 1, 1779999000),
    ]


def test_upsert_updates_existing_rows(fetcher_mod, schema_conn):
    """A second fetch with the same CVE but different ransomware flag
    must overwrite — CISA can flip Unknown→Known when new intel arrives."""
    fetcher_mod.upsert_kev_rows(
        schema_conn,
        _sample_catalog([_sample_vuln("CVE-2024-0003", ransom="Unknown")]),
        fetched_at=1779999000,
    )
    stats = fetcher_mod.upsert_kev_rows(
        schema_conn,
        _sample_catalog([_sample_vuln("CVE-2024-0003", ransom="Known")],
                        version="2026.05.24"),
        fetched_at=1780085400,
    )
    assert stats["rows_before"] == 1
    assert stats["rows_after"] == 1
    assert stats["rows_new"] == 0  # net delta is 0, but content changed

    row = schema_conn.execute(
        "SELECT known_ransomware_use, cisa_catalog_version, source_fetched_at "
        "FROM cisa_kev WHERE cve_id='CVE-2024-0003'"
    ).fetchone()
    assert tuple(row) == (1, "2026.05.24", 1780085400)


def test_upsert_is_idempotent(fetcher_mod, schema_conn):
    """Re-upserting the exact same catalog produces zero net diff."""
    catalog = _sample_catalog([
        _sample_vuln("CVE-2024-0004"),
        _sample_vuln("CVE-2024-0005"),
        _sample_vuln("CVE-2024-0006"),
    ])
    fetcher_mod.upsert_kev_rows(schema_conn, catalog, fetched_at=1779999000)
    stats = fetcher_mod.upsert_kev_rows(schema_conn, catalog, fetched_at=1780000000)
    assert stats["rows_before"] == 3
    assert stats["rows_after"] == 3
    assert stats["rows_new"] == 0


def test_upsert_skips_rows_without_cve_id(fetcher_mod, schema_conn):
    """Defensive: CISA has never shipped a vuln without a cveID, but a
    bad row should be skipped rather than crash the upsert."""
    catalog = _sample_catalog([
        _sample_vuln("CVE-2024-0007"),
        {"vendorProject": "MISSING", "product": "X"},  # no cveID key
        _sample_vuln("CVE-2024-0008"),
    ])
    stats = fetcher_mod.upsert_kev_rows(schema_conn, catalog)
    assert stats["rows_in_feed"] == 3  # raw count
    assert stats["rows_after"] == 2    # only the well-formed two land


def test_upsert_serializes_cwes_as_json(fetcher_mod, schema_conn):
    catalog = _sample_catalog([
        _sample_vuln("CVE-2024-0009", cwes=["CWE-22", "CWE-78"]),
        _sample_vuln("CVE-2024-0010", cwes=None),
    ])
    fetcher_mod.upsert_kev_rows(schema_conn, catalog)
    rows = dict(schema_conn.execute(
        "SELECT cve_id, cwes FROM cisa_kev WHERE cve_id IN ('CVE-2024-0009','CVE-2024-0010')"
    ).fetchall())
    assert rows["CVE-2024-0009"] == '["CWE-22", "CWE-78"]'
    assert rows["CVE-2024-0010"] is None


# ──────────────────────────────────────────────────────────────────────
# _load_kev_cves (Phase G / G' overlay helper)
# ──────────────────────────────────────────────────────────────────────


def test_load_kev_cves_missing_table_returns_empty_set(atlas_mod, tmp_path):
    """Defensive: pre-v23 atlas DBs don't have cisa_kev. Phase G must
    handle that without crashing — degrade to vdb's native kev field."""
    db = tmp_path / "old.db"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    # No init_schema → no cisa_kev table
    assert atlas_mod._load_kev_cves(conn) == set()
    conn.close()


def test_load_kev_cves_empty_table(atlas_mod, schema_conn):
    """Fresh schema: table exists but no rows yet (operator hasn't run
    fetch-cisa-kev). Must return empty set, not crash."""
    assert atlas_mod._load_kev_cves(schema_conn) == set()


def test_load_kev_cves_populated(atlas_mod, fetcher_mod, schema_conn):
    fetcher_mod.upsert_kev_rows(
        schema_conn,
        _sample_catalog([
            _sample_vuln("CVE-2023-1111"),
            _sample_vuln("CVE-2023-2222"),
            _sample_vuln("CVE-2024-3333"),
        ]),
    )
    cves = atlas_mod._load_kev_cves(schema_conn)
    assert cves == {"CVE-2023-1111", "CVE-2023-2222", "CVE-2024-3333"}


# ──────────────────────────────────────────────────────────────────────
# Overlay formula behavior
# ──────────────────────────────────────────────────────────────────────


def _kev_count(affecting, kev_cves):
    """Mirror of the in-phase formula: counts a vuln if vdb says kev OR
    if the CVE is in the local CISA overlay set."""
    return sum(1 for v in affecting if v.get("kev") or v.get("id") in kev_cves)


def test_overlay_empty_set_equals_legacy_behavior():
    """With an empty kev_cves set, the formula must equal the historical
    `sum(... if v.get("kev"))` behavior — i.e., overlay is a strict
    superset, not a replacement."""
    affecting = [
        {"id": "CVE-2024-0100", "kev": False},
        {"id": "CVE-2024-0101", "kev": True},
        {"id": "CVE-2024-0102", "kev": False},
    ]
    assert _kev_count(affecting, set()) == 1  # only the vdb-marked one


def test_overlay_activates_for_local_kev_match():
    """The whole point of DW13: even when vdb says kev=False for every
    CVE (because aqua.py ignores `kevc/`), a local CISA match must count."""
    affecting = [
        {"id": "CVE-2024-0200", "kev": False},
        {"id": "CVE-2024-0201", "kev": False},
        {"id": "CVE-2024-0202", "kev": False},
    ]
    kev_cves = {"CVE-2024-0200", "CVE-2024-0202"}
    assert _kev_count(affecting, kev_cves) == 2


def test_overlay_or_dedupes_naturally():
    """A CVE that's BOTH vdb-flagged AND in the local overlay is counted
    once, not twice — the `or` is short-circuit."""
    affecting = [
        {"id": "CVE-2024-0300", "kev": True},   # both
        {"id": "CVE-2024-0301", "kev": True},   # vdb-only
        {"id": "CVE-2024-0302", "kev": False},  # local-only
        {"id": "CVE-2024-0303", "kev": False},  # neither
    ]
    kev_cves = {"CVE-2024-0300", "CVE-2024-0302"}
    assert _kev_count(affecting, kev_cves) == 3


def test_overlay_handles_missing_id_field():
    """Defensive: vdb's _extract_vuln_fields always sets `id` to the
    cve_id (or '?' if missing). A '?' id must not accidentally hit the
    overlay (we don't add '?' to cisa_kev)."""
    affecting = [
        {"id": "?", "kev": False},
        {"id": "CVE-2024-0400", "kev": False},
    ]
    kev_cves = {"CVE-2024-0400"}
    assert _kev_count(affecting, kev_cves) == 1
