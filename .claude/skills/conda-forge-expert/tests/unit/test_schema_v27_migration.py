"""Schema v27 migration (v8.18.0 Phase F+ Wave 2).

Adds five new columns to `packages` (`downloads_30d`, `downloads_90d`,
`downloads_trend_90d`, `first_nonzero_month`, `last_nonzero_month`) plus
two new side tables (`package_platform_downloads`,
`package_python_downloads`). On a v26 → v27 upgrade the migration writes
a one-shot `phase_f_force_refresh_pending` meta sentinel so the next
Phase F run bypasses the 7-day TTL and re-aggregates the cached parquet
to populate the new columns + tables immediately.
"""
from __future__ import annotations

import importlib.util
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


def _seed_v26_db(db_path: Path, atlas_mod) -> None:
    """Bootstrap a v27 DB then stamp it back to v26 to simulate an upgrade.

    The init_schema path is forward-only — we can't easily build a real
    v26 schema short of pinning to an older revision. Stamping the
    SCHEMA_VERSION metadata back to '26' AND dropping the Wave-2-specific
    artifacts (5 new packages columns + 2 new side tables) is required
    so the subsequent init_schema call actually exercises the v26 → v27
    migration ladder + CREATE TABLE statements. Without the drops, the
    column-existence guard short-circuits every ALTER TABLE and the
    CREATE TABLE IF NOT EXISTS calls become no-ops — the test would
    "pass" without exercising the migration at all (L1 fix).
    """
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    # Seed one conda-linked row that pre-existed at v26.
    conn.execute(
        "INSERT INTO packages "
        "(conda_name, pypi_name, relationship, match_source, "
        " match_confidence, latest_status) "
        "VALUES (?, ?, 'both_same_name', 'test', 'high', 'active')",
        ("numpy", "numpy"),
    )
    # L1 fix: drop the 5 Wave 2 columns + 2 new tables so init_schema's
    # migration ladder genuinely runs them. SQLite ≥3.35 (pixi env pins
    # 3.46+; verified 3.53.1) supports native DROP COLUMN.
    for col in (
        "downloads_30d",
        "downloads_90d",
        "downloads_trend_90d",
        "first_nonzero_month",
        "last_nonzero_month",
    ):
        conn.execute(f"ALTER TABLE packages DROP COLUMN {col}")
    conn.execute("DROP TABLE IF EXISTS package_platform_downloads")
    conn.execute("DROP TABLE IF EXISTS package_python_downloads")
    # Stamp schema_version back to 26 to simulate a pre-upgrade DB.
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        ("schema_version", "26"),
    )
    conn.commit()
    conn.close()


class TestSchemaV27Migration:
    def test_fresh_db_has_v27_columns_and_tables(self, tmp_path, atlas_mod):
        """A brand-new DB lands at SCHEMA_VERSION >= 27 with all Wave 2 artifacts."""
        db_path = tmp_path / "cf_atlas.db"
        conn = atlas_mod.open_db(db_path)
        atlas_mod.init_schema(conn)

        # Schema version stamped to current SCHEMA_VERSION (>= 27).
        schema = conn.execute(
            "SELECT value FROM meta WHERE key='schema_version'"
        ).fetchone()
        assert int(schema[0]) >= 27

        # All five new columns exist on `packages`.
        cols = {r[1] for r in conn.execute("PRAGMA table_info(packages)")}
        for required in (
            "downloads_30d", "downloads_90d", "downloads_trend_90d",
            "first_nonzero_month", "last_nonzero_month",
        ):
            assert required in cols, f"missing column {required}"

        # Both new side tables exist with the documented schema.
        for tbl, expected in (
            ("package_platform_downloads",
                {"conda_name", "pkg_platform", "downloads_90d",
                 "downloads_total", "fetched_at"}),
            ("package_python_downloads",
                {"conda_name", "pkg_python", "downloads_90d",
                 "downloads_total", "fetched_at"}),
        ):
            tbl_exists = bool(list(conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (tbl,),
            )))
            assert tbl_exists, f"missing table {tbl}"
            actual = {r[1] for r in conn.execute(f"PRAGMA table_info({tbl})")}
            assert expected.issubset(actual), (
                f"{tbl} missing cols: {expected - actual}"
            )

        # Fresh DBs don't set the force-refresh sentinel (no v26 → v27 hop).
        sentinel = conn.execute(
            "SELECT value FROM meta WHERE key='phase_f_force_refresh_pending'"
        ).fetchone()
        assert sentinel is None, (
            "fresh-DB init must not set the force-refresh sentinel"
        )
        conn.close()

    def test_v26_db_upgrades_to_v27_and_sets_force_refresh_sentinel(
        self, tmp_path, atlas_mod
    ):
        """v26 → v27 upgrade adds columns + tables AND writes the sentinel."""
        db_path = tmp_path / "cf_atlas.db"
        _seed_v26_db(db_path, atlas_mod)

        # Re-open + init_schema → triggers the migration.
        conn = atlas_mod.open_db(db_path)
        atlas_mod.init_schema(conn)

        # schema_version advanced to current SCHEMA_VERSION.
        schema = conn.execute(
            "SELECT value FROM meta WHERE key='schema_version'"
        ).fetchone()
        assert int(schema[0]) == atlas_mod.SCHEMA_VERSION

        # Five new columns present.
        cols = {r[1] for r in conn.execute("PRAGMA table_info(packages)")}
        for required in (
            "downloads_30d", "downloads_90d", "downloads_trend_90d",
            "first_nonzero_month", "last_nonzero_month",
        ):
            assert required in cols

        # Both new tables present.
        for tbl in ("package_platform_downloads", "package_python_downloads"):
            assert bool(list(conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (tbl,),
            )))

        # Force-refresh sentinel set by the migration.
        sentinel = conn.execute(
            "SELECT value FROM meta WHERE key='phase_f_force_refresh_pending'"
        ).fetchone()
        assert sentinel is not None and sentinel[0] == "1", (
            "v26 → v27 upgrade must set the force-refresh sentinel"
        )

        # Pre-existing data survives.
        row = conn.execute(
            "SELECT conda_name FROM packages WHERE conda_name = 'numpy'"
        ).fetchone()
        assert row is not None and row[0] == "numpy"
        conn.close()

    def test_already_v27_db_is_idempotent_no_op(self, tmp_path, atlas_mod):
        """Re-running init_schema on a v27 DB must not re-set the sentinel."""
        db_path = tmp_path / "cf_atlas.db"
        # First init lands at v27 (fresh path; no sentinel).
        conn = atlas_mod.open_db(db_path)
        atlas_mod.init_schema(conn)
        # Seed a row + clear sentinel just in case.
        conn.execute(
            "INSERT INTO packages "
            "(conda_name, relationship, match_source, match_confidence, latest_status) "
            "VALUES (?, 'has_conda', 'test', 'high', 'active')",
            ("scipy",),
        )
        conn.execute(
            "DELETE FROM meta WHERE key = 'phase_f_force_refresh_pending'"
        )
        conn.commit()
        conn.close()

        # Re-init on already-v27 DB.
        conn = atlas_mod.open_db(db_path)
        atlas_mod.init_schema(conn)

        # Sentinel must NOT be re-set (would force unnecessary re-aggregation).
        sentinel = conn.execute(
            "SELECT value FROM meta WHERE key='phase_f_force_refresh_pending'"
        ).fetchone()
        assert sentinel is None, (
            "already-v27 DB must not have the force-refresh sentinel re-set"
        )

        # schema_version stays at SCHEMA_VERSION.
        schema = conn.execute(
            "SELECT value FROM meta WHERE key='schema_version'"
        ).fetchone()
        assert int(schema[0]) == atlas_mod.SCHEMA_VERSION

        # Pre-existing data survives.
        row = conn.execute(
            "SELECT conda_name FROM packages WHERE conda_name = 'scipy'"
        ).fetchone()
        assert row is not None
        conn.close()
