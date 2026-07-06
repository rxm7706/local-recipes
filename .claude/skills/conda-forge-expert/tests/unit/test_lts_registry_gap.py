"""Fixture tests for lts_registry_gap.py (the LTS-registry suggester).

Pattern: open_db + init_schema + raw INSERTs into `packages` (satisfying the
v_actionable_packages triplet), injected products list, importlib load.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "scripts"
)


def _load_module():
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(
        "lts_registry_gap", _SCRIPTS_DIR / "lts_registry_gap.py")
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
    rows = [
        # (conda_name, pypi_name) — all active/non-archived → in the view
        ("django", "django"),            # registry-covered (excluded)
        ("nodejs", None),                # exact: conda_name == slug
        ("apache_kafka", None),          # likely: _ -> - normalization
        ("python-redis-server", None),   # likely: python- prefix strip (vs slug redis-server)
        ("totally-internal-pkg", None),  # no match
        ("langchain", "langchain"),      # no match (not an eol product)
    ]
    for conda_name, pypi_name in rows:
        conn.execute(
            "INSERT INTO packages (conda_name, pypi_name, latest_status, "
            "relationship, match_source, match_confidence, feedstock_archived) "
            "VALUES (?, ?, 'active', 'test', 'parselmouth', 'verified', 0)",
            (conda_name, pypi_name))
    conn.commit()
    return conn


PRODUCTS = ["django", "nodejs", "apache-kafka", "redis-server", "ubuntu"]
REGISTRY = {"django": {"slug": "django", "_name": "django"}}


def test_exact_and_likely_tiers(mod, fixture_db):
    proposals = mod.classify(
        mod._candidates(fixture_db), PRODUCTS, REGISTRY)
    by_name = {p["conda_name"]: p for p in proposals}
    assert by_name["nodejs"]["confidence"] == "exact"
    assert by_name["nodejs"]["slug"] == "nodejs"
    assert by_name["apache_kafka"]["confidence"] == "likely"
    assert by_name["apache_kafka"]["slug"] == "apache-kafka"
    assert by_name["python-redis-server"]["confidence"] == "likely"
    assert by_name["python-redis-server"]["slug"] == "redis-server"


def test_registry_covered_and_unmatched_excluded(mod, fixture_db):
    proposals = mod.classify(
        mod._candidates(fixture_db), PRODUCTS, REGISTRY)
    names = {p["conda_name"] for p in proposals}
    assert "django" not in names            # already in the registry
    assert "totally-internal-pkg" not in names
    assert "langchain" not in names


def test_registry_alias_exclusion(mod, fixture_db):
    # load_lts_registry indexes aliases too — an alias key must exclude
    registry = {"nodejs": {"slug": "nodejs", "_name": "node"}}
    proposals = mod.classify(
        mod._candidates(fixture_db), PRODUCTS, registry)
    assert "nodejs" not in {p["conda_name"] for p in proposals}


def test_load_products_stale_fallback(mod, tmp_path):
    cache = tmp_path / "eol_products.json"
    cache.write_text(json.dumps(
        {"fetched_at": 0, "products": ["django", "python"]}), encoding="utf-8")
    # expired cache + failing fetcher → stale fallback
    slugs, source, stale = mod.load_products(
        fetcher=lambda: None, cache_path=cache, ttl_days=7,
        now=10 * 86400)
    assert slugs == ["django", "python"]
    assert source == "cache" and stale is True


def test_load_products_fresh_fetch_writes_cache(mod, tmp_path):
    cache = tmp_path / "eol_products.json"
    slugs, source, stale = mod.load_products(
        fetcher=lambda: ["a", "b"], cache_path=cache, now=1000)
    assert slugs == ["a", "b"] and source == "endoflife" and stale is False
    doc = json.loads(cache.read_text(encoding="utf-8"))
    assert doc["products"] == ["a", "b"] and doc["fetched_at"] == 1000


def test_load_products_nothing_available(mod, tmp_path):
    slugs, source, stale = mod.load_products(
        fetcher=lambda: None, cache_path=tmp_path / "missing.json")
    assert slugs == [] and source == "unavailable" and stale is False


def test_cli_json_and_limit_and_no_registry_write(mod, fixture_db, tmp_path, capsys, monkeypatch):
    db_path = tmp_path / "cf_atlas.db"   # fixture_db already lives there
    products_file = tmp_path / "products.json"
    products_file.write_text(json.dumps(PRODUCTS), encoding="utf-8")
    registry_before = (Path(mod.__file__).resolve().parent.parent
                       / "data" / "lts-registry.yaml").read_bytes()
    monkeypatch.setattr(mod, "load_lts_registry", lambda: REGISTRY)
    rc = mod.main(["--db", str(db_path),
                   "--products-file", str(products_file),
                   "--limit", "1", "--json"])
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["counts"] == {"exact": 1, "likely": 1}   # limit=1 per tier
    assert doc["products_source"] == "file"
    registry_after = (Path(mod.__file__).resolve().parent.parent
                      / "data" / "lts-registry.yaml").read_bytes()
    assert registry_before == registry_after            # NEVER written


def test_yaml_snippet_shape(mod):
    snippets = mod.render_yaml_snippets(
        [{"conda_name": "nodejs", "pypi_name": None, "slug": "nodejs",
          "confidence": "exact", "matched_via": "conda_name == slug"}],
        today="2026-07-06")
    assert "  nodejs:" in snippets
    assert "    slug: nodejs" in snippets
    assert "source: endoflife" in snippets
    assert "added: 2026-07-06" in snippets
    assert "verify against the product page" in snippets
