"""Tests for the EPSS fetcher + _load_epss_scores helper (v8.6.0 Wave A).

Covers:
  * `_normalize_percentile` — 0.0-1.0 → 0.0-100.0 transform
  * `_parse_snapshot_date` — extracts score_date from `#` header comment
  * `upsert_epss_rows` — insert, idempotent, malformed-row skip
  * `_load_epss_scores` — missing table (empty dict), empty table, populated
  * `main()` error-path exit-code propagation
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
    return _load("epss_fetcher")


@pytest.fixture
def schema_conn(atlas_mod, tmp_path):
    """Fresh atlas conn with the full v24 schema (epss_scores table included)."""
    db = tmp_path / "atlas.db"
    conn = atlas_mod.open_db(path=db)
    atlas_mod.init_schema(conn)
    yield conn
    conn.close()


# ──────────────────────────────────────────────────────────────────────
# _normalize_percentile
# ──────────────────────────────────────────────────────────────────────


def test_normalize_percentile_mid_range(fetcher_mod):
    assert fetcher_mod._normalize_percentile(0.94532) == pytest.approx(94.532)


def test_normalize_percentile_zero_and_one(fetcher_mod):
    assert fetcher_mod._normalize_percentile(0.0) == 0.0
    assert fetcher_mod._normalize_percentile(1.0) == 100.0


# ──────────────────────────────────────────────────────────────────────
# _parse_snapshot_date
# ──────────────────────────────────────────────────────────────────────


def test_parse_snapshot_date_present(fetcher_mod):
    csv_text = (
        "#model_version:v2025.03.14,score_date:2026-05-22T00:00:00+0000\n"
        "cve,epss,percentile\n"
        "CVE-2024-0001,0.1,0.5\n"
    )
    assert fetcher_mod._parse_snapshot_date(csv_text) == "2026-05-22T00:00:00+0000"


def test_parse_snapshot_date_missing(fetcher_mod):
    csv_text = "cve,epss,percentile\nCVE-2024-0001,0.1,0.5\n"
    assert fetcher_mod._parse_snapshot_date(csv_text) is None


# ──────────────────────────────────────────────────────────────────────
# upsert_epss_rows
# ──────────────────────────────────────────────────────────────────────


_SAMPLE_CSV = (
    "#model_version:v2025.03.14,score_date:2026-05-22T00:00:00+0000\n"
    "cve,epss,percentile\n"
    "CVE-2024-1000,0.94532,0.99876\n"
    "CVE-2024-1001,0.00012,0.00501\n"
    "CVE-2024-1002,0.5,0.5\n"
)


def test_upsert_inserts_new_rows(fetcher_mod, schema_conn):
    stats = fetcher_mod.upsert_epss_rows(
        schema_conn, _SAMPLE_CSV, fetched_at=1779999000
    )
    assert stats["rows_in_feed"] == 3
    assert stats["rows_before"] == 0
    assert stats["rows_after"] == 3
    assert stats["rows_new"] == 3
    assert stats["rows_skipped"] == 0
    assert stats["snapshot_date"] == "2026-05-22T00:00:00+0000"

    rows = [tuple(r) for r in schema_conn.execute(
        "SELECT cve_id, epss_score, epss_percentile, snapshot_date, source_fetched_at "
        "FROM epss_scores ORDER BY cve_id"
    )]
    assert rows[0] == ("CVE-2024-1000", pytest.approx(0.94532),
                       pytest.approx(99.876), "2026-05-22T00:00:00+0000", 1779999000)
    assert rows[1] == ("CVE-2024-1001", pytest.approx(0.00012),
                       pytest.approx(0.501), "2026-05-22T00:00:00+0000", 1779999000)


def test_upsert_is_idempotent(fetcher_mod, schema_conn):
    """Re-upserting the same CSV produces zero net diff."""
    fetcher_mod.upsert_epss_rows(schema_conn, _SAMPLE_CSV, fetched_at=1779999000)
    stats = fetcher_mod.upsert_epss_rows(
        schema_conn, _SAMPLE_CSV, fetched_at=1780000000
    )
    assert stats["rows_before"] == 3
    assert stats["rows_after"] == 3
    assert stats["rows_new"] == 0


def test_upsert_updates_changed_score(fetcher_mod, schema_conn):
    """FIRST can revise EPSS scores day-to-day; upsert must overwrite."""
    fetcher_mod.upsert_epss_rows(schema_conn, _SAMPLE_CSV, fetched_at=1779999000)
    revised_csv = (
        "#score_date:2026-05-23T00:00:00+0000\n"
        "cve,epss,percentile\n"
        "CVE-2024-1000,0.99999,0.99999\n"
    )
    stats = fetcher_mod.upsert_epss_rows(
        schema_conn, revised_csv, fetched_at=1780085400
    )
    assert stats["rows_before"] == 3
    assert stats["rows_after"] == 3  # same count; one row replaced

    row = schema_conn.execute(
        "SELECT epss_score, epss_percentile, snapshot_date, source_fetched_at "
        "FROM epss_scores WHERE cve_id='CVE-2024-1000'"
    ).fetchone()
    assert row[0] == pytest.approx(0.99999)
    assert row[1] == pytest.approx(99.999)
    assert row[2] == "2026-05-23T00:00:00+0000"
    assert row[3] == 1780085400


def test_upsert_skips_malformed_rows(fetcher_mod, schema_conn):
    """Missing cve / unparseable score / missing percentile → skipped, others land."""
    bad_csv = (
        "cve,epss,percentile\n"
        "CVE-2024-2000,0.5,0.5\n"
        ",0.5,0.5\n"                         # missing cve_id
        "CVE-2024-2001,notanumber,0.5\n"     # unparseable epss
        "CVE-2024-2002,0.5\n"                # missing percentile column
        "CVE-2024-2003,0.7,0.8\n"
    )
    stats = fetcher_mod.upsert_epss_rows(schema_conn, bad_csv)
    assert stats["rows_in_feed"] == 5
    assert stats["rows_after"] == 2
    assert stats["rows_skipped"] == 3

    cve_ids = {r[0] for r in schema_conn.execute("SELECT cve_id FROM epss_scores")}
    assert cve_ids == {"CVE-2024-2000", "CVE-2024-2003"}


# ──────────────────────────────────────────────────────────────────────
# _load_epss_scores (Phase G / G' overlay helper, Wave B consumer-ready)
# ──────────────────────────────────────────────────────────────────────


def test_load_epss_scores_missing_table_returns_empty_dict(atlas_mod, tmp_path):
    """Pre-v24 atlas DBs don't have epss_scores. Phase G/G' must not crash."""
    db = tmp_path / "old.db"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    # No init_schema → no epss_scores table
    assert atlas_mod._load_epss_scores(conn) == {}
    conn.close()


def test_load_epss_scores_empty_table(atlas_mod, schema_conn):
    """Fresh v24 schema: table exists, no rows yet. Must return {} cleanly."""
    assert atlas_mod._load_epss_scores(schema_conn) == {}


def test_load_epss_scores_populated(atlas_mod, fetcher_mod, schema_conn):
    fetcher_mod.upsert_epss_rows(schema_conn, _SAMPLE_CSV)
    epss = atlas_mod._load_epss_scores(schema_conn)
    assert set(epss.keys()) == {"CVE-2024-1000", "CVE-2024-1001", "CVE-2024-1002"}
    score, pct = epss["CVE-2024-1000"]
    assert score == pytest.approx(0.94532)
    assert pct == pytest.approx(99.876)


# ──────────────────────────────────────────────────────────────────────
# main() error-path exit-code propagation
# ──────────────────────────────────────────────────────────────────────


def test_main_exits_nonzero_on_fetch_failure(fetcher_mod, monkeypatch, capsys):
    """When fetch_with_fallback raises, main() must exit 1 with stderr msg."""
    def boom(*_a, **_kw):
        raise RuntimeError("simulated network failure")

    monkeypatch.setattr(fetcher_mod, "fetch_epss_csv", boom)
    rc = fetcher_mod.main(["--dry-run"])  # dry-run doesn't touch DB; just fetch
    assert rc == 1
    captured = capsys.readouterr()
    assert "EPSS fetch FAILED" in captured.err
    assert "RuntimeError" in captured.err
