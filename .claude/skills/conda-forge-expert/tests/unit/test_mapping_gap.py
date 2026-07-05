"""mapping-gap CLI + the v28→v29 `v_pypi_intelligence_valid` migration.

cyclonedx-universe-inventory Wave A / S2. Pins: dry-run-by-default (zero
UPDATEs), the no-clobber writeback + idempotency (second `--write` run
writes 0 rows), D2 confidence tiers (`verified` needs an independent
corroborator; `likely` on universe membership alone), ambiguous/collision
buckets (the wasmtime-vs-wasmtime-py trap), grayskull-absent likely-only
mode, classification buckets, and the D3 schema view (orphans excluded;
migration idempotent on a v28 fixture).
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


@pytest.fixture(scope="module")
def cli_mod():
    return _load("mapping_gap")


def _insert_pkg(conn, conda, pypi=None, match_source="none", match_confidence="n/a"):
    # match_source / match_confidence are NOT NULL in the live schema —
    # unattributed rows store the LITERAL 'none' / 'n/a'.
    conn.execute(
        "INSERT INTO packages (conda_name, pypi_name, match_source, "
        "match_confidence, relationship) VALUES (?,?,?,?, 'test')",
        (conda, pypi, match_source, match_confidence),
    )


def _python_dep(conn, conda):
    conn.execute(
        "INSERT INTO dependencies (source_conda_name, target_conda_name, "
        "requirement_type) VALUES (?, 'python', 'run')", (conda,),
    )


def _universe(conn, *names):
    for n in names:
        conn.execute(
            "INSERT OR IGNORE INTO pypi_universe (pypi_name, last_serial, "
            "fetched_at) VALUES (?, 1, 1)", (n,),
        )


@pytest.fixture
def db(tmp_path, atlas_mod):
    """Working-set fixture covering every D2 branch."""
    conn = atlas_mod.open_db(tmp_path / "cf_atlas.db")
    atlas_mod.init_schema(conn)
    # verified: grayskull reverse corroborates foo-py → foo
    _insert_pkg(conn, "foo-py");        _python_dep(conn, "foo-py")
    # likely: universe membership alone
    _insert_pkg(conn, "bar");           _python_dep(conn, "bar")
    # ambiguous: both `baz` and `baz-py` exist in the universe, no tiebreak
    _insert_pkg(conn, "baz-py");        _python_dep(conn, "baz-py")
    # collision: pypi `wasmtime` is already claimed by conda `wasmtime-py`
    _insert_pkg(conn, "wasmtime");      _python_dep(conn, "wasmtime")
    _insert_pkg(conn, "wasmtime-py", pypi="wasmtime",
                match_source="parselmouth", match_confidence="verified")
    # no-clobber: parselmouth provenance, unmapped — recoverable but never written
    _insert_pkg(conn, "pm-pkg", pypi="", match_source="parselmouth")
    _python_dep(conn, "pm-pkg")
    # unrecovered python-track: nothing in the universe
    _insert_pkg(conn, "lost");          _python_dep(conn, "lost")
    # non-python buckets
    _insert_pkg(conn, "gotool")
    conn.execute(
        "INSERT INTO upstream_versions (conda_name, source, version, url, "
        "fetched_at) VALUES ('gotool', 'github', '1.0', "
        "'https://github.com/a/gotool', 1)"
    )
    _insert_pkg(conn, "mystery")
    _universe(conn, "foo", "bar", "baz", "baz-py", "wasmtime", "pm-pkg")
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def grayskull_cache(tmp_path):
    p = tmp_path / "pypi_conda_map.json"
    p.write_text(json.dumps({"foo": "foo-py"}), encoding="utf-8")
    return p


def _run(cli_mod, conn, write, grayskull_path, tmp_path, **kw):
    return cli_mod.run(
        conn, write=write, limit=None,
        grayskull_path=grayskull_path,
        associator_path=kw.get("associator_path", tmp_path / "absent-assoc.json"),
    )


class TestClassification:
    def test_buckets(self, db, cli_mod, grayskull_cache, tmp_path):
        r = _run(cli_mod, db, False, grayskull_cache, tmp_path)
        assert set(r["python_track"]) == {"foo-py", "bar", "baz-py", "wasmtime",
                                          "pm-pkg", "lost"}
        assert r["non_python_with_identity"] == ["gotool"]
        assert r["non_python_no_identity"] == ["mystery"]


class TestRecovery:
    def test_confidence_tiers_and_buckets(self, db, cli_mod, grayskull_cache, tmp_path):
        r = _run(cli_mod, db, False, grayskull_cache, tmp_path)
        by_name = {rec["conda_name"]: rec for rec in r["recovered"]}
        assert by_name["foo-py"]["pypi_name"] == "foo"
        assert by_name["foo-py"]["confidence"] == "verified"
        assert by_name["foo-py"]["transform"] == "strip-py"
        assert by_name["bar"]["confidence"] == "likely"
        assert [a["conda_name"] for a in r["ambiguous"]] == ["baz-py"]
        assert sorted(r["ambiguous"][0]["candidates"]) == ["baz", "baz-py"]
        assert r["collisions"] == [{
            "conda_name": "wasmtime", "candidate": "wasmtime",
            "claimed_by": "wasmtime-py",
        }]
        assert r["unrecovered_python_track"] == ["lost"]

    def test_grayskull_absent_likely_only(self, db, cli_mod, tmp_path):
        r = _run(cli_mod, db, False, tmp_path / "no-cache.json", tmp_path)
        assert r["grayskull_cache_present"] is False
        confidences = {rec["confidence"] for rec in r["recovered"]}
        assert confidences == {"likely"}
        # Without the grayskull tiebreak nothing can be `verified`;
        # the ambiguous bucket still holds baz-py.
        assert [a["conda_name"] for a in r["ambiguous"]] == ["baz-py"]

    def test_intra_run_duplicate_claim_is_collision(self, cli_mod, atlas_mod, tmp_path):
        """Two unmapped packages folding to the SAME universe name in one
        run: the first accepted recovery claims it; the second must land in
        the collisions bucket (the intra-run face of the wasmtime trap)."""
        conn = atlas_mod.open_db(tmp_path / "dup.db")
        atlas_mod.init_schema(conn)
        _insert_pkg(conn, "dup");     _python_dep(conn, "dup")
        _insert_pkg(conn, "dup-py");  _python_dep(conn, "dup-py")
        _universe(conn, "dup")
        conn.commit()
        r = cli_mod.run(conn, write=True, limit=None,
                        grayskull_path=tmp_path / "no-cache.json",
                        associator_path=tmp_path / "no-assoc.json")
        recovered = {rec["conda_name"] for rec in r["recovered"]}
        assert recovered == {"dup"}, "only ONE package may claim pypi `dup`"
        assert r["collisions"] == [{
            "conda_name": "dup-py", "candidate": "dup", "claimed_by": "dup",
        }]
        assert r["rows_written"] == 1
        mapped = [tuple(row) for row in conn.execute(
            "SELECT conda_name, pypi_name FROM packages "
            "WHERE pypi_name = 'dup'"
        )]
        assert mapped == [("dup", "dup")]
        conn.close()

    def test_corroborator_disagreement_routes_to_ambiguous(self, cli_mod, atlas_mod, tmp_path):
        """A corroborator that names a DIFFERENT pypi project than the sole
        universe hit is contrary evidence — no `likely` write; triage."""
        conn = atlas_mod.open_db(tmp_path / "disagree.db")
        atlas_mod.init_schema(conn)
        _insert_pkg(conn, "sneaky");  _python_dep(conn, "sneaky")
        _universe(conn, "sneaky")
        conn.commit()
        cache = tmp_path / "gs.json"
        cache.write_text(json.dumps({"totally-other-name": "sneaky"}),
                         encoding="utf-8")
        r = cli_mod.run(conn, write=True, limit=None,
                        grayskull_path=cache,
                        associator_path=tmp_path / "no-assoc.json")
        assert r["recovered"] == [] and r["rows_written"] == 0
        assert r["ambiguous"] == [{
            "conda_name": "sneaky",
            "candidates": ["sneaky"],
            "corroborator_suggests": ["totally-other-name"],
        }]
        conn.close()

    def test_corrupt_grayskull_cache_reported_distinctly(self, db, cli_mod, tmp_path):
        corrupt = tmp_path / "corrupt.json"
        corrupt.write_text("{not json", encoding="utf-8")
        r = _run(cli_mod, db, False, corrupt, tmp_path)
        assert r["grayskull_cache_present"] is False
        assert r["grayskull_cache_state"] == "corrupt"
        assert r["grayskull_cache_mtime"] is not None
        assert "PRESENT BUT UNREADABLE" in cli_mod.render_report(r)

    def test_purl_associator_corroborates(self, db, cli_mod, tmp_path):
        assoc = tmp_path / "assoc.json"
        assoc.write_text(json.dumps(
            {"foo-py": {"purl": "pkg:conda/foo-py?channel=conda-forge",
                        "alternative_purls": ["pkg:pypi/foo"]}}
        ), encoding="utf-8")
        r = cli_mod.run(db, write=False, limit=None,
                        grayskull_path=tmp_path / "no-cache.json",
                        associator_path=assoc)
        by_name = {rec["conda_name"]: rec for rec in r["recovered"]}
        assert by_name["foo-py"]["confidence"] == "verified"
        assert r["purl_associator_present"] is True


class TestWritePath:
    def test_dry_run_writes_nothing(self, db, cli_mod, grayskull_cache, tmp_path):
        r = _run(cli_mod, db, False, grayskull_cache, tmp_path)
        assert r["mode"] == "dry-run"
        assert r["rows_written"] == 0
        assert db.execute(
            "SELECT pypi_name FROM packages WHERE conda_name='foo-py'"
        ).fetchone()[0] is None

    def test_write_no_clobber_and_idempotency(self, db, cli_mod, grayskull_cache, tmp_path):
        r1 = _run(cli_mod, db, True, grayskull_cache, tmp_path)
        # foo-py + bar written; pm-pkg blocked by the provenance guard.
        assert r1["rows_written"] == 2
        row = db.execute(
            "SELECT pypi_name, match_source, match_confidence FROM packages "
            "WHERE conda_name='foo-py'"
        ).fetchone()
        assert tuple(row) == ("foo", "g10_spelling", "verified")
        # no-clobber: parselmouth provenance untouched even though recovered.
        pm = db.execute(
            "SELECT pypi_name, match_source FROM packages "
            "WHERE conda_name='pm-pkg'"
        ).fetchone()
        assert tuple(pm) == ("", "parselmouth")
        # already-mapped rows untouched.
        wt = db.execute(
            "SELECT pypi_name, match_source FROM packages "
            "WHERE conda_name='wasmtime-py'"
        ).fetchone()
        assert tuple(wt) == ("wasmtime", "parselmouth")
        # Second --write run: recovered rows left the working set → 0 written.
        r2 = _run(cli_mod, db, True, grayskull_cache, tmp_path)
        assert r2["rows_written"] == 0
        assert r1["mapped_after"] == r1["mapped_before"] + 2


class TestReadOnlyDryRun:
    def test_dry_run_works_on_readonly_connection(self, tmp_path, atlas_mod, cli_mod):
        """main() opens the DB with `mode=ro` for dry-runs; classify()'s
        temp-table scoping must keep working there (SQLite temp tables live
        in the separate temp database, which stays writable on a ro main DB
        — pinned so a future PRAGMA/refactor can't silently break the
        production dry-run path the read-write test fixtures don't cover)."""
        import sqlite3 as _sq
        db_path = tmp_path / "ro.db"
        conn = atlas_mod.open_db(db_path)
        atlas_mod.init_schema(conn)
        _insert_pkg(conn, "foo-py")
        _python_dep(conn, "foo-py")
        _universe(conn, "foo")
        conn.commit()
        conn.close()
        ro = _sq.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            r = cli_mod.run(ro, write=False, limit=None,
                            grayskull_path=tmp_path / "absent.json",
                            associator_path=tmp_path / "absent2.json")
        finally:
            ro.close()
        assert r["mode"] == "dry-run" and r["rows_written"] == 0
        assert [(x["conda_name"], x["pypi_name"]) for x in r["recovered"]] == \
            [("foo-py", "foo")]


class TestOrphanRuleAndMigration:
    def test_view_excludes_orphans(self, db, cli_mod):
        db.execute("INSERT INTO pypi_intelligence (pypi_name) VALUES ('ghost')")
        db.execute("INSERT INTO pypi_intelligence (pypi_name) VALUES ('foo')")
        db.commit()
        live = [r[0] for r in db.execute(
            "SELECT pypi_name FROM v_pypi_intelligence_valid"
        )]
        assert live == ["foo"], "orphan (no universe counterpart) must be excluded"
        stats = cli_mod.orphan_intelligence_stats(db)
        assert stats["count"] == 1
        assert stats["sample"] == ["ghost"]
        assert "v_pypi_intelligence_valid" in stats["rule"]

    def test_v28_to_v29_migration_idempotent(self, tmp_path, atlas_mod):
        """Simulated v28 DB (view dropped, version stamped 28): init_schema
        recreates the view + stamps 29; a second run is a no-op."""
        conn = atlas_mod.open_db(tmp_path / "v28.db")
        atlas_mod.init_schema(conn)
        conn.execute("DROP VIEW IF EXISTS v_pypi_intelligence_valid")
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', '28')"
        )
        conn.commit()
        assert atlas_mod.SCHEMA_VERSION >= 29

        for _ in range(2):  # second pass proves idempotency
            atlas_mod.init_schema(conn)
            have_view = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='view' "
                "AND name='v_pypi_intelligence_valid'"
            ).fetchone()
            assert have_view
            version = conn.execute(
                "SELECT value FROM meta WHERE key='schema_version'"
            ).fetchone()[0]
            assert int(version) == atlas_mod.SCHEMA_VERSION
        conn.close()


class TestReport:
    def test_report_sections(self, db, cli_mod, grayskull_cache, tmp_path):
        r = _run(cli_mod, db, False, grayskull_cache, tmp_path)
        text = cli_mod.render_report(r)
        for heading in ("# mapping-gap report", "## Summary", "## Classification",
                        "### Ambiguous", "### Collisions",
                        "## Orphan pypi_intelligence rows",
                        "## Recovered pairs (appendix)"):
            assert heading in text
        assert "DRY-RUN" in text
