"""Tests for the CWE catalog fetcher + _load_cwe_categories helper (v8.6.0 Wave B).

Covers:
  * `_load_seed_mapping` — strips _doc key, returns flat dict
  * `parse_cwe_csv` — extracts inner CSV from a fixture zip
  * `upsert_cwe_rows` — seed-match → category, unmapped → 'Other', idempotent
  * `_load_cwe_categories` — missing table → {}, populated → dict
  * `main()` error-path exit-code propagation
"""
from __future__ import annotations

import importlib.util
import io
import json
import sqlite3
import sys
import zipfile
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
    return _load("cwe_catalog_fetcher")


@pytest.fixture
def schema_conn(atlas_mod, tmp_path):
    """Fresh v24 atlas conn — cwe_categories table is empty."""
    db = tmp_path / "atlas.db"
    conn = atlas_mod.open_db(path=db)
    atlas_mod.init_schema(conn)
    yield conn
    conn.close()


_SAMPLE_SEED = {
    "CWE-79": "Injection",
    "CWE-22": "Traversal",
    "CWE-78": "RCE",
    "CWE-200": "Info-Disclosure",
}


def _build_sample_zip() -> bytes:
    """Build an in-memory zip mirroring MITRE's CWE 1000 layout."""
    csv_text = (
        "CWE-ID,Name,Weakness Abstraction,Status,Description\n"
        "79,Cross-site Scripting (XSS),Base,Stable,Generates a web page with unneutralized inputs.\n"
        "22,Path Traversal,Base,Stable,Constructs file pathname without neutralizing special elements.\n"
        "78,OS Command Injection,Base,Stable,Constructs an OS command without neutralizing inputs.\n"
        "9999,Custom Synthetic CWE,Variant,Draft,Not in seed; falls to Other.\n"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("1000.csv", csv_text)
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────────
# _load_seed_mapping
# ──────────────────────────────────────────────────────────────────────


def test_seed_mapping_strips_doc_key(fetcher_mod, tmp_path):
    seed_file = tmp_path / "seed.json"
    seed_file.write_text(json.dumps({
        "_doc": {"purpose": "metadata"},
        "_provenance": "should also be stripped",
        "CWE-79": "Injection",
        "CWE-22": "Traversal",
    }))
    seed = fetcher_mod._load_seed_mapping(seed_file)
    assert seed == {"CWE-79": "Injection", "CWE-22": "Traversal"}


def test_seed_mapping_missing_file_returns_empty(fetcher_mod, tmp_path):
    assert fetcher_mod._load_seed_mapping(tmp_path / "nonexistent.json") == {}


def test_committed_seed_loads_and_has_expected_categories(fetcher_mod):
    """The committed seed JSON must load and contain entries for the well-known
    high-impact CWEs we surface in operator-facing tooling."""
    seed = fetcher_mod._load_seed_mapping()
    assert "CWE-79" in seed and seed["CWE-79"] == "Injection"
    assert "CWE-22" in seed and seed["CWE-22"] == "Traversal"
    assert "CWE-78" in seed and seed["CWE-78"] == "RCE"
    assert "CWE-502" in seed and seed["CWE-502"] == "RCE"
    categories = set(seed.values())
    assert categories <= {"RCE", "DoS", "Info-Disclosure", "Auth-Bypass",
                          "Memory-Safety", "Traversal", "Injection", "Other"}


# ──────────────────────────────────────────────────────────────────────
# parse_cwe_csv
# ──────────────────────────────────────────────────────────────────────


def test_parse_cwe_csv_extracts_rows(fetcher_mod):
    rows = fetcher_mod.parse_cwe_csv(_build_sample_zip())
    assert len(rows) == 4
    assert rows[0]["CWE-ID"] == "79"
    assert rows[0]["Name"] == "Cross-site Scripting (XSS)"
    assert rows[0]["Weakness Abstraction"] == "Base"


def test_parse_cwe_csv_missing_csv_in_zip_raises(fetcher_mod):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("readme.txt", "no CSV here")
    with pytest.raises(RuntimeError, match="no .csv"):
        fetcher_mod.parse_cwe_csv(buf.getvalue())


# ──────────────────────────────────────────────────────────────────────
# upsert_cwe_rows
# ──────────────────────────────────────────────────────────────────────


def test_upsert_inserts_with_seed_match_and_other_fallback(fetcher_mod, schema_conn):
    rows = fetcher_mod.parse_cwe_csv(_build_sample_zip())
    stats = fetcher_mod.upsert_cwe_rows(
        schema_conn, rows, _SAMPLE_SEED, fetched_at=1779999000
    )
    assert stats["rows_in_feed"] == 4
    assert stats["rows_after"] == 4
    assert stats["rows_seeded"] == 3   # CWE-79, CWE-22, CWE-78
    assert stats["rows_other"] == 1    # CWE-9999
    assert stats["rows_skipped"] == 0

    rows_db = [tuple(r) for r in schema_conn.execute(
        "SELECT cwe_id, cwe_name, cf_atlas_category, cwe_abstraction "
        "FROM cwe_categories ORDER BY cwe_id"
    )]
    assert rows_db[0] == ("CWE-22", "Path Traversal", "Traversal", "Base")
    assert rows_db[1] == ("CWE-78", "OS Command Injection", "RCE", "Base")
    assert rows_db[2] == ("CWE-79", "Cross-site Scripting (XSS)", "Injection", "Base")
    assert rows_db[3] == ("CWE-9999", "Custom Synthetic CWE", "Other", "Variant")


def test_upsert_is_idempotent(fetcher_mod, schema_conn):
    rows = fetcher_mod.parse_cwe_csv(_build_sample_zip())
    fetcher_mod.upsert_cwe_rows(schema_conn, rows, _SAMPLE_SEED)
    stats = fetcher_mod.upsert_cwe_rows(schema_conn, rows, _SAMPLE_SEED)
    assert stats["rows_before"] == 4
    assert stats["rows_after"] == 4
    assert stats["rows_new"] == 0


def test_upsert_skips_rows_without_cwe_id(fetcher_mod, schema_conn):
    rows = [
        {"CWE-ID": "100", "Name": "Has ID", "Weakness Abstraction": "Base"},
        {"CWE-ID": "", "Name": "Empty ID", "Weakness Abstraction": "Base"},
        {"Name": "Missing ID column entirely", "Weakness Abstraction": "Base"},
    ]
    stats = fetcher_mod.upsert_cwe_rows(schema_conn, rows, {})
    assert stats["rows_in_feed"] == 3
    assert stats["rows_after"] == 1
    assert stats["rows_skipped"] == 2


# ──────────────────────────────────────────────────────────────────────
# _load_cwe_categories
# ──────────────────────────────────────────────────────────────────────


def test_load_cwe_categories_missing_table(atlas_mod, tmp_path):
    """Pre-v24 atlas DBs lack cwe_categories. Phase G/G' must not crash."""
    db = tmp_path / "old.db"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    assert atlas_mod._load_cwe_categories(conn) == {}
    conn.close()


def test_load_cwe_categories_empty_table(atlas_mod, schema_conn):
    assert atlas_mod._load_cwe_categories(schema_conn) == {}


def test_load_cwe_categories_populated(atlas_mod, fetcher_mod, schema_conn):
    rows = fetcher_mod.parse_cwe_csv(_build_sample_zip())
    fetcher_mod.upsert_cwe_rows(schema_conn, rows, _SAMPLE_SEED)
    cwe = atlas_mod._load_cwe_categories(schema_conn)
    assert cwe == {
        "CWE-22":   "Traversal",
        "CWE-78":   "RCE",
        "CWE-79":   "Injection",
        "CWE-9999": "Other",
    }


# ──────────────────────────────────────────────────────────────────────
# main() error-path
# ──────────────────────────────────────────────────────────────────────


def test_main_exits_nonzero_on_fetch_failure(fetcher_mod, monkeypatch, capsys):
    def boom(*_a, **_kw):
        raise RuntimeError("simulated network failure")
    monkeypatch.setattr(fetcher_mod, "fetch_cwe_zip", boom)
    rc = fetcher_mod.main(["--dry-run"])
    assert rc == 1
    captured = capsys.readouterr()
    assert "CWE fetch FAILED" in captured.err
    assert "RuntimeError" in captured.err
