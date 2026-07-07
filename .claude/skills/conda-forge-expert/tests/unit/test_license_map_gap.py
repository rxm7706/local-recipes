"""Fixture tests for license_map_gap.py (the _LICENSE_TO_SPDX suggester).

Pattern: open_db + init_schema + raw INSERTs into pypi_intelligence, importlib
load. Fully offline (no network). The read-only invariant is asserted by
confirming conda_forge_atlas.py is byte-identical across a full CLI run.
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
        "license_map_gap", _SCRIPTS_DIR / "license_map_gap.py")
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
    # (pypi_name, license_raw, license_spdx) — spdx NULL == the map missed
    rows = [
        ("pkg-mapped", "MIT", "MIT"),                    # mapped → excluded
        ("pkg-zpl", "Zope Public License", None),        # unmapped, 1 candidate → likely (ZPL-2.1?)
        ("pkg-artistic", "Artistic License", None),      # unmapped, candidate(s)
        ("pkg-blank", "", None),                         # empty → junk
        ("pkg-unknown", "UNKNOWN", None),                # unknown → junk
        ("pkg-expr", "Apache-2.0 OR MIT", None),         # expression → junk
        ("pkg-seealso", "See LICENSE file", None),       # see... → junk
        ("pkg-fulltext", "Permission is hereby granted, free of charge, to any person " * 2, None),  # long → junk
        ("pkg-already", "mit license", None),            # already a map key → excluded
    ]
    def _add(name, raw, spdx):
        conn.execute(
            "INSERT INTO pypi_intelligence (pypi_name, license_raw, "
            "license_spdx) VALUES (?, ?, ?)", (name, raw, spdx))
        # the version-truth view joins pypi_universe (ORPHAN_RULE) — seed it
        conn.execute("INSERT INTO pypi_universe (pypi_name) VALUES (?)", (name,))

    for name, raw, spdx in rows:
        _add(name, raw, spdx)
    # give one unmapped form extra weight for ranking
    _add("pkg-zpl2", "Zope Public License", None)
    conn.commit()
    return conn


ENUM = {"MIT", "Apache-2.0", "ZPL-2.1", "Artistic-1.0", "Artistic-2.0", "BSD-3-Clause"}
SEED = {"mit": "MIT", "mit license": "MIT", "apache-2.0": "Apache-2.0"}


def test_is_junk(mod):
    assert mod._is_junk("")
    assert mod._is_junk("UNKNOWN")
    assert mod._is_junk("See LICENSE")
    assert mod._is_junk("Apache-2.0 OR MIT")          # expression
    assert mod._is_junk("x" * 61)                     # too long
    assert mod._is_junk("https://opensource.org/MIT")
    assert not mod._is_junk("Zope Public License")
    assert not mod._is_junk("Artistic License")


def test_candidates_whole_token(mod):
    enum_by_lower = {e.lower(): e for e in ENUM}
    # "Zope Public License" contains no enum id token → no candidate here
    assert mod._candidates("Zope Public License", enum_by_lower) == []
    # a form literally containing an id token matches that id only
    assert mod._candidates("licensed under ZPL-2.1 terms", enum_by_lower) == ["ZPL-2.1"]
    # "MIT" as a whole token, not a substring of "committed"
    assert mod._candidates("committed work", enum_by_lower) == []


def test_classify_excludes_junk_and_mapped(mod, fixture_db):
    proposals = mod.classify(mod._unmapped_licenses(fixture_db), ENUM, SEED)
    forms = {p["license_raw"] for p in proposals}
    assert "MIT" not in forms                          # mapped (license_spdx set)
    assert "mit license" not in forms                  # already a seed key
    assert "" not in forms and "UNKNOWN" not in forms  # junk
    assert "Apache-2.0 OR MIT" not in forms            # expression
    assert "See LICENSE file" not in forms
    assert not any(len(f) > 60 for f in forms)         # full text dropped
    # the real unmapped licenses survive
    assert "Zope Public License" in forms
    assert "Artistic License" in forms


def test_ranked_by_package_count(mod, fixture_db):
    proposals = mod.classify(mod._unmapped_licenses(fixture_db), ENUM, SEED)
    zpl = next(p for p in proposals if p["license_raw"] == "Zope Public License")
    assert zpl["packages"] == 2                        # two rows carry it
    # highest count first
    assert proposals[0]["packages"] >= proposals[-1]["packages"]


def test_tiering_likely_vs_report(mod):
    enum = {"ZPL-2.1", "Artistic-1.0", "Artistic-2.0"}
    # one candidate → likely with a suggested target
    single = mod.classify({"licensed under ZPL-2.1": 3}, enum, {})
    assert single[0]["confidence"] == "likely"
    assert single[0]["suggested_spdx"] == "ZPL-2.1"
    # two candidates → report, no committed target
    multi = mod.classify({"Artistic-1.0 or Artistic-2.0 choose": 1}, enum, {})
    assert multi[0]["confidence"] == "report"
    assert multi[0]["suggested_spdx"] is None
    assert set(multi[0]["candidates"]) == {"Artistic-1.0", "Artistic-2.0"}


def test_render_map_lines_only_likely(mod):
    proposals = [
        {"license_raw": "Foo ZPL-2.1", "packages": 3, "candidates": ["ZPL-2.1"],
         "confidence": "likely", "suggested_spdx": "ZPL-2.1"},
        {"license_raw": "Ambiguous", "packages": 5, "candidates": ["A", "B"],
         "confidence": "report", "suggested_spdx": None},
    ]
    out = mod.render_map_lines(proposals)
    assert '"foo zpl-2.1": "ZPL-2.1",' in out
    assert "Ambiguous" not in out                      # report tier not rendered
    assert "3 package(s)" in out


def test_cli_json_limit_and_source_untouched(mod, fixture_db, tmp_path, capsys):
    import conda_forge_atlas
    src = Path(conda_forge_atlas.__file__)
    before = src.read_bytes()
    db_path = tmp_path / "cf_atlas.db"                  # fixture_db lives here
    rc = mod.main(["--db", str(db_path), "--limit", "5", "--json"])
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["map_entries"] == len(conda_forge_atlas._LICENSE_TO_SPDX)
    assert doc["unmapped_forms"] >= 1
    assert src.read_bytes() == before                  # READ-ONLY: never written
