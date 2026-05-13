"""Schema v20 migration moves pypi_only rows from packages to pypi_universe.

Regression test for the 2026-05-13 actionable-scope audit: existing v19
atlases carry ~660k `relationship='pypi_only'` rows in `packages` that
pollute every working-set query. v20 extracts them to a dedicated
`pypi_universe` side table and DELETEs them from `packages`. Migration
is wrapped in a transaction with rollback; idempotent re-run is a no-op.
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


def _seed_v19_db_with_pypi_only_rows(db_path: Path, atlas_mod) -> sqlite3.Connection:
    """Create a v19-shaped DB with pypi_only rows pre-existing.

    Simulates an existing atlas built under the v19 schema where Phase D
    inserted pypi_only rows into `packages`. The v20 migration in
    `init_schema` should move them to `pypi_universe`.
    """
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    # Insert mixed rows that look like a v19 build
    seeds = [
        # Conda-linked rows — must SURVIVE the migration
        ("numpy",      "numpy",      100, "both_same_name"),
        ("scipy",      "scipy",      200, "both_same_name"),
        # pypi_only rows — must MOVE to pypi_universe and DELETE from packages
        (None,         "pypi-only-a", 1001, "pypi_only"),
        (None,         "pypi-only-b", 1002, "pypi_only"),
        (None,         "pypi-only-c", 1003, "pypi_only"),
    ]
    for conda, pypi, serial, rel in seeds:
        conn.execute(
            "INSERT INTO packages "
            "(conda_name, pypi_name, pypi_last_serial, relationship, "
            " match_source, match_confidence) "
            "VALUES (?, ?, ?, ?, 'test', 'high')",
            (conda, pypi, serial, rel),
        )
    conn.commit()
    return conn


class TestSchemaV20Migration:
    def test_pypi_only_rows_migrate_to_universe(self, tmp_path, atlas_mod):
        db_path = tmp_path / "cf_atlas.db"
        conn = _seed_v19_db_with_pypi_only_rows(db_path, atlas_mod)
        conn.close()

        # Re-open + init_schema — triggers the v20 migration
        conn = atlas_mod.open_db(db_path)
        atlas_mod.init_schema(conn)

        # packages no longer has pypi_only rows
        leftover = conn.execute(
            "SELECT COUNT(*) FROM packages WHERE relationship = 'pypi_only'"
        ).fetchone()[0]
        assert leftover == 0, "v20 migration must delete all pypi_only rows"

        # pypi_universe has the migrated rows
        universe = list(conn.execute(
            "SELECT pypi_name, last_serial FROM pypi_universe ORDER BY pypi_name"
        ))
        assert {(r[0], r[1]) for r in universe} == {
            ("pypi-only-a", 1001),
            ("pypi-only-b", 1002),
            ("pypi-only-c", 1003),
        }

        # Conda-linked rows survived
        survivors = list(conn.execute(
            "SELECT conda_name FROM packages ORDER BY conda_name"
        ))
        assert [r[0] for r in survivors] == ["numpy", "scipy"]
        conn.close()

    def test_migration_is_idempotent(self, tmp_path, atlas_mod):
        """Running init_schema twice must produce the same end state."""
        db_path = tmp_path / "cf_atlas.db"
        conn = _seed_v19_db_with_pypi_only_rows(db_path, atlas_mod)
        conn.close()

        # First migration
        conn = atlas_mod.open_db(db_path)
        atlas_mod.init_schema(conn)
        first_universe = list(conn.execute(
            "SELECT pypi_name, last_serial FROM pypi_universe ORDER BY pypi_name"
        ))
        first_packages = list(conn.execute(
            "SELECT conda_name FROM packages ORDER BY conda_name"
        ))
        conn.close()

        # Second invocation — should be a no-op (no new rows in universe, no
        # rows added to packages, no rows lost from either)
        conn = atlas_mod.open_db(db_path)
        atlas_mod.init_schema(conn)
        second_universe = list(conn.execute(
            "SELECT pypi_name, last_serial FROM pypi_universe ORDER BY pypi_name"
        ))
        second_packages = list(conn.execute(
            "SELECT conda_name FROM packages ORDER BY conda_name"
        ))
        assert first_universe == second_universe
        assert first_packages == second_packages
        conn.close()

    def test_fresh_v20_db_has_empty_universe_and_v20_schema(self, tmp_path, atlas_mod):
        """A brand-new DB starts at schema v20 with empty pypi_universe."""
        db_path = tmp_path / "cf_atlas.db"
        conn = atlas_mod.open_db(db_path)
        atlas_mod.init_schema(conn)

        # Schema version is 20
        schema = conn.execute(
            "SELECT value FROM meta WHERE key='schema_version'"
        ).fetchone()
        assert schema[0] == "20"

        # pypi_universe table exists
        exists = bool(list(conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='pypi_universe'"
        )))
        assert exists

        # Empty
        assert conn.execute(
            "SELECT COUNT(*) FROM pypi_universe"
        ).fetchone()[0] == 0
        conn.close()
