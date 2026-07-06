"""Fixture tests for cwe_seed_gap.py (the CWE-seed suggester).

Pattern: open_db + init_schema + raw INSERTs into cwe_categories + packages,
importlib load. Fully offline (no network).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


def _load_module():
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(
        "cwe_seed_gap", _SCRIPTS_DIR / "cwe_seed_gap.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_module()


@pytest.fixture()
def fixture_db(tmp_path, mod):
    import conda_forge_atlas as atlas_mod
    conn = atlas_mod.open_db(tmp_path / "cf_atlas.db")
    atlas_mod.init_schema(conn)
    # cwe_categories rows: some already-categorized, some 'Other'
    rows = [
        ("CWE-89", "SQL Injection", "Injection"),          # already seeded
        ("CWE-843", "Access of Resource Using Incompatible Type ('Type Confusion')", "Other"),  # strong → Memory-Safety
        ("CWE-113", "Improper Neutralization of CRLF Sequences in HTTP Headers", "Other"),       # strong → Injection
        ("CWE-284", "Improper Access Control", "Other"),   # strong → Auth-Bypass
        ("CWE-1004", "Sensitive Cookie Without 'HttpOnly' Flag", "Other"),   # no keyword → not proposed
        ("CWE-266", "Incorrect Privilege Assignment", "Other"),   # weak → Auth-Bypass (privilege)
    ]
    for cwe_id, name, cat in rows:
        conn.execute(
            "INSERT INTO cwe_categories (cwe_id, cwe_name, cf_atlas_category, "
            "cwe_abstraction, source_fetched_at) VALUES (?, ?, ?, 'Base', 0)",
            (cwe_id, name, cat))
    # a package carrying an 'Other' CWE bucket (impact signal)
    conn.execute(
        "INSERT INTO packages (conda_name, latest_status, relationship, "
        "match_source, match_confidence, feedstock_archived, "
        "vuln_cwe_categories_json) VALUES "
        "('somepkg', 'active', 'test', 'parselmouth', 'verified', 0, ?)",
        (json.dumps({"RCE": 2, "Other": 3}),))
    conn.execute(
        "INSERT INTO packages (conda_name, latest_status, relationship, "
        "match_source, match_confidence, feedstock_archived, "
        "vuln_cwe_categories_json) VALUES "
        "('cleanpkg', 'active', 'test', 'parselmouth', 'verified', 0, ?)",
        (json.dumps({"RCE": 1}),))
    conn.commit()
    return conn


def test_classify_cwe_strong_and_weak(mod):
    assert mod.classify_cwe("Out-of-bounds Read")[:2] == ("Memory-Safety", "strong")
    assert mod.classify_cwe("SQL Injection")[:2] == ("Injection", "strong")
    assert mod.classify_cwe("Improper Authentication")[:2] == ("Auth-Bypass", "strong")
    assert mod.classify_cwe("Path Traversal")[:2] == ("Traversal", "strong")
    # weak: generic word only
    assert mod.classify_cwe("Incorrect Privilege Assignment")[:2] == ("Auth-Bypass", "weak")
    # no keyword → None
    assert mod.classify_cwe("Sensitive Cookie Without HttpOnly Flag") is None or \
        mod.classify_cwe("Sensitive Cookie Without HttpOnly Flag")[0] == "Info-Disclosure"


def test_precedence_command_injection_is_rce_not_injection(mod):
    cat, tier, _ = mod.classify_cwe("OS Command Injection")
    assert (cat, tier) == ("RCE", "strong")


def test_classify_proposals_exclude_seeded_and_unmatched(mod, fixture_db):
    seed = {"CWE-89": "Injection"}   # only 89 is seeded
    proposals = mod.classify(mod._other_cwes(fixture_db), seed)
    by_id = {p["cwe_id"]: p for p in proposals}
    assert "CWE-89" not in by_id                       # seeded (and not 'Other')
    assert by_id["CWE-843"]["category"] == "Memory-Safety"
    assert by_id["CWE-843"]["confidence"] == "strong"
    assert by_id["CWE-113"]["category"] == "Injection"
    assert by_id["CWE-284"]["category"] == "Auth-Bypass"
    assert by_id["CWE-266"]["confidence"] == "weak"


def test_seed_exclusion_belt_and_braces(mod, fixture_db):
    # even if a seeded id somehow appears as 'Other', the seed excludes it
    seed = {"CWE-843": "Memory-Safety"}
    proposals = mod.classify(mod._other_cwes(fixture_db), seed)
    assert "CWE-843" not in {p["cwe_id"] for p in proposals}


def test_other_impact_counts_packages(mod, fixture_db):
    assert mod._other_impact(fixture_db) == 1   # only 'somepkg' has Other>0


def test_cli_json_limit_and_seed_untouched(mod, fixture_db, tmp_path, capsys):
    db_path = tmp_path / "cf_atlas.db"
    from cwe_catalog_fetcher import _SEED_PATH
    before = _SEED_PATH.read_bytes()
    rc = mod.main(["--db", str(db_path), "--limit", "1", "--json"])
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["counts"]["strong"] <= 1 and doc["counts"]["weak"] <= 1
    assert doc["packages_with_other_bucket"] == 1
    assert _SEED_PATH.read_bytes() == before    # NEVER written


def test_render_seed_lines_shape(mod):
    lines = mod.render_seed_lines([
        {"cwe_id": "CWE-843", "cwe_name": "Type Confusion",
         "category": "Memory-Safety", "confidence": "strong",
         "matched": "type confusion"}])
    assert '"CWE-843": "Memory-Safety"' in lines
    assert "Type Confusion" in lines and "type confusion" in lines
