"""Fixture tests for spdx_schema_gap.py (the SPDX-schema suggester).

Pattern: open_db + init_schema + raw INSERTs into packages, injected upstream
SPDX list, importlib load.
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
        "spdx_schema_gap", _SCRIPTS_DIR / "spdx_schema_gap.py")
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
    # conda_license values with package counts
    licenses = [
        ("MIT", 5),                     # in vendored enum → covered
        ("Cool-New-1.0", 3),            # upstream-only → add-to-schema
        ("Made-Up-License", 2),         # neither → non-standard
        ("Apache-2.0 AND MIT", 4),      # expression → skipped
    ]
    i = 0
    for lic, count in licenses:
        for _ in range(count):
            i += 1
            conn.execute(
                "INSERT INTO packages (conda_name, latest_status, relationship, "
                "match_source, match_confidence, feedstock_archived, "
                "conda_license) VALUES (?, 'active', 'test', 'parselmouth', "
                "'verified', 0, ?)",
                (f"pkg{i}", lic))
    conn.commit()
    return conn


UPSTREAM = ["MIT", "Apache-2.0", "BSD-3-Clause", "Cool-New-1.0", "0BSD"]


def test_is_expression(mod):
    assert mod._is_expression("Apache-2.0 AND MIT")
    assert mod._is_expression("GPL-3.0-or-later WITH GCC-exception")
    assert mod._is_expression("(MIT OR Apache-2.0)")
    assert not mod._is_expression("MIT")
    assert not mod._is_expression("Cool-New-1.0")


def test_classify_add_and_nonstandard(mod, fixture_db):
    vendored = {"MIT", "Apache-2.0", "BSD-3-Clause"}
    result = mod.classify(
        mod._atlas_license_counts(fixture_db), vendored, set(UPSTREAM))
    add_ids = {r["spdx_id"] for r in result["add_to_schema"]}
    nonstd = {r["license"] for r in result["non_standard"]}
    assert add_ids == {"Cool-New-1.0"}                 # upstream-only, on packages
    assert result["add_to_schema"][0]["packages"] == 3
    assert nonstd == {"Made-Up-License"}               # neither
    assert "Apache-2.0 AND MIT" not in add_ids | nonstd   # expression skipped
    assert "MIT" not in add_ids | nonstd               # vendored-covered


def test_load_upstream_stale_fallback(mod, tmp_path):
    cache = tmp_path / "spdx_license_list.json"
    cache.write_text(json.dumps({"fetched_at": 0, "ids": ["MIT", "0BSD"]}),
                     encoding="utf-8")
    ids, source, stale = mod.load_upstream_spdx(
        fetcher=lambda: None, cache_path=cache, ttl_days=7, now=10 * 86400)
    assert ids == ["MIT", "0BSD"] and source == "cache" and stale is True


def test_load_upstream_fresh_fetch_writes_cache(mod, tmp_path):
    cache = tmp_path / "spdx_license_list.json"
    ids, source, stale = mod.load_upstream_spdx(
        fetcher=lambda: ["MIT", "X-1.0"], cache_path=cache, now=1000)
    assert ids == ["MIT", "X-1.0"] and source == "spdx" and stale is False
    assert json.loads(cache.read_text(encoding="utf-8"))["ids"] == ["MIT", "X-1.0"]


def test_load_upstream_nothing(mod, tmp_path):
    ids, source, stale = mod.load_upstream_spdx(
        fetcher=lambda: None, cache_path=tmp_path / "missing.json")
    assert ids == [] and source == "unavailable"


def test_cli_source_file_json_and_schema_untouched(mod, fixture_db, tmp_path, capsys):
    db_path = tmp_path / "cf_atlas.db"
    src = tmp_path / "licenses.json"
    src.write_text(json.dumps(
        {"licenses": [{"licenseId": x} for x in UPSTREAM]}), encoding="utf-8")
    from _sbom import _SPDX_ENUM_PATH
    before = _SPDX_ENUM_PATH.read_bytes()
    rc = mod.main(["--db", str(db_path), "--source-file", str(src),
                   "--drift", "--json"])
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["upstream_source"] == "file"
    assert doc["counts"]["add_to_schema"] == 1         # Cool-New-1.0
    assert "upstream_drift_ids" in doc                 # --drift
    assert _SPDX_ENUM_PATH.read_bytes() == before      # NEVER written


def test_render_enum_lines_shape(mod):
    out = mod.render_enum_lines([{"license": "Cool-New-1.0",
                                  "spdx_id": "Cool-New-1.0", "packages": 3}])
    assert '"Cool-New-1.0",' in out and "3 package(s)" in out
