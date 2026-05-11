"""Schema migration v17 → v18: idempotency + column presence."""
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


@pytest.fixture
def fresh_db(tmp_path, atlas_mod):
    db_path = tmp_path / "cf_atlas.db"
    conn = atlas_mod.open_db(db_path)
    yield conn
    conn.close()


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _schema_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute(
        "SELECT value FROM meta WHERE key='schema_version'"
    ).fetchone()[0])


class TestMigrationV18:
    def test_fresh_db_reaches_v18(self, fresh_db, atlas_mod):
        atlas_mod.init_schema(fresh_db)
        assert _schema_version(fresh_db) == 18

    def test_packages_has_downloads_source_column(self, fresh_db, atlas_mod):
        atlas_mod.init_schema(fresh_db)
        assert "downloads_source" in _columns(fresh_db, "packages")

    def test_pvd_has_source_column(self, fresh_db, atlas_mod):
        atlas_mod.init_schema(fresh_db)
        assert "source" in _columns(fresh_db, "package_version_downloads")

    def test_rerun_is_noop(self, fresh_db, atlas_mod):
        atlas_mod.init_schema(fresh_db)
        pkgs_before = _columns(fresh_db, "packages")
        pvd_before = _columns(fresh_db, "package_version_downloads")
        atlas_mod.init_schema(fresh_db)
        atlas_mod.init_schema(fresh_db)
        assert _columns(fresh_db, "packages") == pkgs_before
        assert _columns(fresh_db, "package_version_downloads") == pvd_before
        assert _schema_version(fresh_db) == 18

    def test_v17_simulated_upgrades_cleanly(self, fresh_db, atlas_mod):
        atlas_mod.init_schema(fresh_db)
        # Simulate a pre-v18 DB by stripping the v18-added columns and
        # rolling schema_version back. The next init_schema must restore both.
        fresh_db.execute(
            "CREATE TABLE packages_v17 AS SELECT * FROM packages"
        )
        fresh_db.execute("DROP TABLE packages")
        cols = [c for c in _columns(fresh_db, "packages_v17") if c != "downloads_source"]
        select_list = ", ".join(cols)
        fresh_db.execute(
            f"CREATE TABLE packages AS SELECT {select_list} FROM packages_v17"
        )
        fresh_db.execute("DROP TABLE packages_v17")
        fresh_db.execute(
            "ALTER TABLE package_version_downloads RENAME COLUMN source TO source_old"
        )
        fresh_db.execute(
            "UPDATE meta SET value='17' WHERE key='schema_version'"
        )
        fresh_db.commit()
        assert "downloads_source" not in _columns(fresh_db, "packages")

        atlas_mod.init_schema(fresh_db)
        assert _schema_version(fresh_db) == 18
        assert "downloads_source" in _columns(fresh_db, "packages")
        # pvd already has `source_old` in addition to a recreated `source`;
        # migration just adds the missing `source` column idempotently
        assert "source" in _columns(fresh_db, "package_version_downloads")
