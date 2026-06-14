"""Schema v28 migration (v8.19.0 Phase F+ Wave 3).

Adds `packages.python_min TEXT` (Phase E writes from cf-graph raw_meta_yaml)
and the `package_channel_downloads` side table (Phase F populates from the
extended parquet sweep). On a v27 → v28 upgrade the migration writes BOTH
`phase_e_force_refresh_pending` AND `phase_f_force_refresh_pending` meta
sentinels so the next admin run populates both pieces immediately, rather
than waiting for the cf-graph TTL + Phase F TTL to expire.

Test cases mirror `test_schema_v27_migration.py`:
  1. Fresh DB at SCHEMA_VERSION >= 28 has the column + table; NO sentinels.
  2. v27 DB upgrades cleanly: column + table created, BOTH sentinels set,
     pre-existing data preserved.
  3. Already-v28 DB is an idempotent no-op (sentinels are NOT re-set).
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


def _seed_v27_db(db_path: Path, atlas_mod) -> None:
    """Bootstrap a v28 DB then stamp it back to v27 to simulate an upgrade.

    Drops the v28-specific artifacts (`packages.python_min` column +
    `package_channel_downloads` table) so the subsequent init_schema call
    actually exercises the v27 → v28 migration ladder + CREATE TABLE
    statement. Without the drops the column-existence guard would short-
    circuit the ALTER and IF NOT EXISTS would skip the CREATE — the test
    would "pass" without exercising the migration at all (mirrors v27 L1
    fix in test_schema_v27_migration.py).
    """
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    conn.execute(
        "INSERT INTO packages "
        "(conda_name, pypi_name, relationship, match_source, "
        " match_confidence, latest_status) "
        "VALUES (?, ?, 'both_same_name', 'test', 'high', 'active')",
        ("numpy", "numpy"),
    )
    # Drop the v28 column + table so the migration ladder actually runs.
    conn.execute("ALTER TABLE packages DROP COLUMN python_min")
    conn.execute("DROP TABLE IF EXISTS package_channel_downloads")
    # Stamp schema_version back to 27 to simulate the pre-upgrade DB.
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        ("schema_version", "27"),
    )
    conn.commit()
    conn.close()


class TestSchemaV28Migration:
    def test_fresh_db_has_v28_column_and_table(self, tmp_path, atlas_mod):
        """A brand-new DB lands at SCHEMA_VERSION >= 28 with all Wave 3 artifacts."""
        db_path = tmp_path / "cf_atlas.db"
        conn = atlas_mod.open_db(db_path)
        atlas_mod.init_schema(conn)

        schema = conn.execute(
            "SELECT value FROM meta WHERE key='schema_version'"
        ).fetchone()
        assert int(schema[0]) >= 28

        cols = {r[1] for r in conn.execute("PRAGMA table_info(packages)")}
        assert "python_min" in cols, "v28: packages.python_min must exist"

        tbl_exists = bool(list(conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='package_channel_downloads'"
        )))
        assert tbl_exists, "v28: package_channel_downloads must exist"

        actual = {
            r[1] for r in conn.execute(
                "PRAGMA table_info(package_channel_downloads)"
            )
        }
        expected = {
            "conda_name", "data_source", "downloads_90d",
            "downloads_total", "fetched_at",
        }
        assert expected.issubset(actual), (
            f"package_channel_downloads missing cols: {expected - actual}"
        )

        # Fresh DBs don't set either force-refresh sentinel.
        for sentinel_key in ("phase_e_force_refresh_pending",
                             "phase_f_force_refresh_pending"):
            sentinel = conn.execute(
                "SELECT value FROM meta WHERE key=?", (sentinel_key,)
            ).fetchone()
            assert sentinel is None, (
                f"fresh-DB init must not set {sentinel_key}"
            )
        conn.close()

    def test_v27_db_upgrades_to_v28_and_sets_both_sentinels(
        self, tmp_path, atlas_mod
    ):
        """v27 → v28 upgrade adds column + table AND writes BOTH sentinels."""
        db_path = tmp_path / "cf_atlas.db"
        _seed_v27_db(db_path, atlas_mod)

        conn = atlas_mod.open_db(db_path)
        atlas_mod.init_schema(conn)

        schema = conn.execute(
            "SELECT value FROM meta WHERE key='schema_version'"
        ).fetchone()
        assert int(schema[0]) == atlas_mod.SCHEMA_VERSION

        cols = {r[1] for r in conn.execute("PRAGMA table_info(packages)")}
        assert "python_min" in cols

        assert bool(list(conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='package_channel_downloads'"
        )))

        # BOTH sentinels set by the migration.
        for sentinel_key in ("phase_e_force_refresh_pending",
                             "phase_f_force_refresh_pending"):
            sentinel = conn.execute(
                "SELECT value FROM meta WHERE key=?", (sentinel_key,)
            ).fetchone()
            assert sentinel is not None and sentinel[0] == "1", (
                f"v27 → v28 upgrade must set {sentinel_key}"
            )

        # Pre-existing data survives.
        row = conn.execute(
            "SELECT conda_name FROM packages WHERE conda_name = 'numpy'"
        ).fetchone()
        assert row is not None and row[0] == "numpy"
        conn.close()

    def test_v27_migration_recovers_from_partial_kill(
        self, tmp_path, atlas_mod
    ):
        """DW-test-1 (v8.21.0): simulate a SIGKILL mid-DDL on the v27 → v28
        migration. After re-running init_schema cleanly, assert
        (a) `packages.python_min` column present, (b)
        `package_channel_downloads` table present, (c) BOTH
        `phase_e_force_refresh_pending` and `phase_f_force_refresh_pending`
        sentinels set, (d) schema_version at SCHEMA_VERSION.

        Strategy: subclass sqlite3.Connection so the second `ALTER TABLE
        packages` call raises mid-ladder, then re-run init_schema with the
        plain Connection to verify idempotent recovery.
        """
        import sqlite3

        db_path = tmp_path / "cf_atlas.db"
        _seed_v27_db(db_path, atlas_mod)

        call_log: list[str] = []

        # v27 → v28 only adds ONE new column (`packages.python_min`) +
        # one new table; the ALTER ladder fires that one ADD COLUMN, then
        # the sentinel writes wait. Crash AT that first ALTER so the
        # migration aborts mid-state (column added, sentinels not written).
        class _CrashingConnection(sqlite3.Connection):
            def execute(self, sql, *args, **kwargs):  # type: ignore[override]
                call_log.append(sql)
                if (
                    "ALTER TABLE packages" in sql
                    and "python_min" in sql
                ):
                    # Let the ALTER execute first so the column lands, then
                    # crash on the next call (which is typically another
                    # PRAGMA or sentinel write — exercises the post-DDL
                    # recovery path).
                    result = super().execute(sql, *args, **kwargs)
                    raise RuntimeError(
                        "simulated SIGKILL mid-v28-migration (DW-test-1)"
                    )
                return super().execute(sql, *args, **kwargs)

        crashing_conn = sqlite3.connect(
            str(db_path), factory=_CrashingConnection
        )
        crashing_conn.row_factory = sqlite3.Row
        with pytest.raises(RuntimeError, match="simulated SIGKILL"):
            atlas_mod.init_schema(crashing_conn)
        crashing_conn.close()

        # Re-run init_schema cleanly. Idempotent migration ladder must
        # complete end-to-end from whatever partial state was left.
        recovery_conn = atlas_mod.open_db(db_path)
        atlas_mod.init_schema(recovery_conn)

        # (a) packages.python_min present.
        cols = {r[1] for r in recovery_conn.execute("PRAGMA table_info(packages)")}
        assert "python_min" in cols, "recovery missing packages.python_min"

        # (b) package_channel_downloads table present.
        tbl_exists = bool(list(recovery_conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='package_channel_downloads'"
        )))
        assert tbl_exists, "recovery missing package_channel_downloads table"

        # (c) BOTH sentinels set so the next Phase E + Phase F populate.
        for sentinel_key in ("phase_e_force_refresh_pending",
                             "phase_f_force_refresh_pending"):
            sentinel = recovery_conn.execute(
                "SELECT value FROM meta WHERE key=?", (sentinel_key,)
            ).fetchone()
            assert sentinel is not None and sentinel[0] == "1", (
                f"recovery missing {sentinel_key}=1"
            )

        # (d) schema_version at SCHEMA_VERSION.
        schema = recovery_conn.execute(
            "SELECT value FROM meta WHERE key='schema_version'"
        ).fetchone()
        assert int(schema[0]) == atlas_mod.SCHEMA_VERSION
        recovery_conn.close()

    def test_already_v28_db_is_idempotent_no_op(self, tmp_path, atlas_mod):
        """Re-running init_schema on a v28 DB must not re-set the sentinels."""
        db_path = tmp_path / "cf_atlas.db"
        conn = atlas_mod.open_db(db_path)
        atlas_mod.init_schema(conn)
        conn.execute(
            "INSERT INTO packages "
            "(conda_name, relationship, match_source, match_confidence, latest_status) "
            "VALUES (?, 'has_conda', 'test', 'high', 'active')",
            ("scipy",),
        )
        # Clear any sentinels that may exist from a prior init run.
        conn.execute(
            "DELETE FROM meta WHERE key IN "
            "('phase_e_force_refresh_pending', 'phase_f_force_refresh_pending')"
        )
        conn.commit()
        conn.close()

        # Re-init on already-v28 DB.
        conn = atlas_mod.open_db(db_path)
        atlas_mod.init_schema(conn)

        # Neither sentinel should be re-set (would force unnecessary re-runs).
        for sentinel_key in ("phase_e_force_refresh_pending",
                             "phase_f_force_refresh_pending"):
            sentinel = conn.execute(
                "SELECT value FROM meta WHERE key=?", (sentinel_key,)
            ).fetchone()
            assert sentinel is None, (
                f"already-v28 DB must not have {sentinel_key} re-set"
            )

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
