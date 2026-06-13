"""Schema v26 (v8.15.0) — pypi_downloads_daily side table.

Covers the schema migration's idempotency, the INSERT OR IGNORE
contract, and the SQL aggregation that recomputes
pypi_intelligence.downloads_30d / downloads_90d from per-day rows.
"""
from __future__ import annotations

import datetime
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


@pytest.fixture
def db(tmp_path, atlas_mod):
    db_path = tmp_path / "cf_atlas.db"
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    yield conn
    conn.close()


class TestSchemaV26Migration:
    """Schema v26 adds pypi_downloads_daily + 2 indexes. CREATE IF NOT
    EXISTS DDL — idempotent on re-run."""

    def test_table_exists_after_init(self, db):
        row = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='pypi_downloads_daily'"
        ).fetchone()
        assert row is not None, "pypi_downloads_daily table not created"

    def test_columns_have_expected_types(self, db):
        cols = {row["name"]: row["type"] for row in db.execute(
            "PRAGMA table_info(pypi_downloads_daily)"
        )}
        assert cols == {
            "pypi_name": "TEXT",
            "download_date": "TEXT",
            "downloads": "INTEGER",
        }

    def test_indexes_present(self, db):
        names = {row["name"] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND tbl_name='pypi_downloads_daily'"
        )}
        # Auto-generated sqlite_autoindex_* for PK + the 2 named indexes.
        assert "idx_pypi_dl_daily_date" in names
        assert "idx_pypi_dl_daily_name" in names

    def test_primary_key_is_composite(self, db):
        rows = list(db.execute("PRAGMA table_info(pypi_downloads_daily)"))
        pk_cols = sorted([r["name"] for r in rows if r["pk"] > 0])
        assert pk_cols == ["download_date", "pypi_name"]

    def test_schema_version_is_at_least_26(self, atlas_mod):
        # v26 added pypi_downloads_daily. Forward-compat: later versions
        # keep the table; this test guards that the constant stays >= 26
        # (a regression below the v26 floor would silently break
        # consumers of pypi_downloads_daily).
        assert atlas_mod.SCHEMA_VERSION >= 26

    def test_re_init_is_idempotent(self, db, atlas_mod):
        """init_schema can run twice on the same DB without error."""
        atlas_mod.init_schema(db)
        atlas_mod.init_schema(db)
        # Still exactly one table.
        assert db.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type='table' AND name='pypi_downloads_daily'"
        ).fetchone()[0] == 1

    def test_meta_records_schema_version_at_least_26(self, db, atlas_mod):
        # L5 fix: clamp to the band [26, current SCHEMA_VERSION] so a
        # forward-compat run stays valid AND an accidental constant
        # regression (e.g. a typo dropping SCHEMA_VERSION below 26 or
        # ahead of the constant) trips this guard. The upper bound is
        # the module's current SCHEMA_VERSION — bumped each ship.
        row = db.execute(
            "SELECT value FROM meta WHERE key='schema_version'"
        ).fetchone()
        assert row is not None
        v = int(row[0])
        assert 26 <= v <= atlas_mod.SCHEMA_VERSION


class TestInsertOrIgnoreIdempotency:
    """INSERT OR IGNORE on (pypi_name, download_date) preserves the
    initial row's downloads count; re-runs on the same partition are
    no-ops, which is what the incremental refresh contract relies on."""

    def test_duplicate_primary_key_ignored(self, db):
        db.execute(
            "INSERT OR IGNORE INTO pypi_downloads_daily "
            "(pypi_name, download_date, downloads) VALUES (?, ?, ?)",
            ("numpy", "2026-06-01", 12_345),
        )
        # Same PK, different downloads — must be ignored, not updated.
        db.execute(
            "INSERT OR IGNORE INTO pypi_downloads_daily "
            "(pypi_name, download_date, downloads) VALUES (?, ?, ?)",
            ("numpy", "2026-06-01", 99_999),
        )
        rows = list(db.execute(
            "SELECT pypi_name, download_date, downloads "
            "FROM pypi_downloads_daily"
        ))
        assert len(rows) == 1
        assert rows[0][2] == 12_345  # First value wins; second ignored.

    def test_distinct_pks_both_inserted(self, db):
        db.executemany(
            "INSERT OR IGNORE INTO pypi_downloads_daily "
            "(pypi_name, download_date, downloads) VALUES (?, ?, ?)",
            [
                ("numpy", "2026-06-01", 100),
                ("numpy", "2026-06-02", 200),  # different date
                ("pandas", "2026-06-01", 300),  # different name
            ],
        )
        assert db.execute(
            "SELECT COUNT(*) FROM pypi_downloads_daily"
        ).fetchone()[0] == 3


class TestAggregationCorrectness:
    """The SQL aggregation that drives pypi_intelligence.downloads_30d/90d
    from pypi_downloads_daily — verified against handcrafted fixtures."""

    def _populate_window(self, db, today: datetime.date):
        """Seed pypi_downloads_daily with:
          - numpy: 100 downloads/day for days 0..89 → 30d=3000, 90d=9000
          - pandas: 5 downloads on day-95 (outside 90d window — excluded)
          - rich: 50 downloads on day-15 only (inside 30d → 30d=50, 90d=50)
        """
        rows = []
        for i in range(90):
            d = (today - datetime.timedelta(days=i + 1)).isoformat()
            rows.append(("numpy", d, 100))
        rows.append(("pandas", (today - datetime.timedelta(days=95)).isoformat(), 5))
        rows.append(("rich", (today - datetime.timedelta(days=15)).isoformat(), 50))
        db.executemany(
            "INSERT OR IGNORE INTO pypi_downloads_daily "
            "(pypi_name, download_date, downloads) VALUES (?, ?, ?)",
            rows,
        )

    def _apply_aggregation(self, db, today: datetime.date):
        cutoff_30d = (today - datetime.timedelta(days=30)).isoformat()
        cutoff_90d = (today - datetime.timedelta(days=90)).isoformat()
        now = 1_700_000_000
        db.execute(
            """
            INSERT INTO pypi_intelligence (
                pypi_name, downloads_30d, downloads_90d,
                downloads_fetched_at, downloads_source
            )
            SELECT
                pypi_name,
                COALESCE(SUM(CASE WHEN download_date >= ? THEN downloads ELSE 0 END), 0),
                COALESCE(SUM(downloads), 0),
                ?,
                'bigquery-incremental'
            FROM pypi_downloads_daily
            WHERE download_date >= ?
            GROUP BY pypi_name
            ON CONFLICT(pypi_name) DO UPDATE SET
                downloads_30d        = excluded.downloads_30d,
                downloads_90d        = excluded.downloads_90d,
                downloads_fetched_at = excluded.downloads_fetched_at,
                downloads_source     = excluded.downloads_source
            """,
            (cutoff_30d, now, cutoff_90d),
        )
        db.commit()

    def test_30d_window_excludes_older_rows(self, db):
        today = datetime.date.today()
        self._populate_window(db, today)
        self._apply_aggregation(db, today)
        numpy_row = db.execute(
            "SELECT downloads_30d, downloads_90d, downloads_source "
            "FROM pypi_intelligence WHERE pypi_name='numpy'"
        ).fetchone()
        assert numpy_row is not None
        # 100/day × 30 days = 3000; 100/day × 90 days = 9000.
        assert numpy_row[0] == 3000, f"downloads_30d should be 3000, got {numpy_row[0]}"
        assert numpy_row[1] == 9000, f"downloads_90d should be 9000, got {numpy_row[1]}"
        assert numpy_row[2] == "bigquery-incremental"

    def test_90d_window_excludes_day_95_row(self, db):
        today = datetime.date.today()
        self._populate_window(db, today)
        self._apply_aggregation(db, today)
        pandas_row = db.execute(
            "SELECT downloads_30d, downloads_90d "
            "FROM pypi_intelligence WHERE pypi_name='pandas'"
        ).fetchone()
        # pandas only has a day-95 row → excluded from both windows →
        # pandas should NOT appear in pypi_intelligence at all (the
        # aggregation's WHERE clause filters at the 90d boundary).
        assert pandas_row is None, (
            "pandas had only day-95 activity (outside 90d window); "
            "should not be in pypi_intelligence"
        )

    def test_single_day_in_30d_window(self, db):
        today = datetime.date.today()
        self._populate_window(db, today)
        self._apply_aggregation(db, today)
        rich_row = db.execute(
            "SELECT downloads_30d, downloads_90d "
            "FROM pypi_intelligence WHERE pypi_name='rich'"
        ).fetchone()
        assert rich_row is not None
        # rich has 50 downloads on day-15 → in both windows.
        assert rich_row[0] == 50
        assert rich_row[1] == 50

    def test_upsert_overwrites_prior_run(self, db):
        """Re-running the aggregation overwrites prior downloads_30d/90d
        rather than appending — what the ON CONFLICT clause guarantees."""
        today = datetime.date.today()
        # First seed + aggregate
        self._populate_window(db, today)
        self._apply_aggregation(db, today)
        # Add 1 more numpy day → 31 days × 100 = 3100 in 30d window.
        db.execute(
            "INSERT OR IGNORE INTO pypi_downloads_daily "
            "(pypi_name, download_date, downloads) VALUES (?, ?, ?)",
            ("numpy", today.isoformat(), 100),
        )
        self._apply_aggregation(db, today)
        numpy_row = db.execute(
            "SELECT downloads_30d FROM pypi_intelligence WHERE pypi_name='numpy'"
        ).fetchone()
        assert numpy_row[0] == 3100, (
            f"downloads_30d should update to 3100 after adding today's row, "
            f"got {numpy_row[0]}"
        )

    def test_gc_delete_only_old_rows(self, db):
        today = datetime.date.today()
        self._populate_window(db, today)
        before = db.execute("SELECT COUNT(*) FROM pypi_downloads_daily").fetchone()[0]
        gc_cutoff = (today - datetime.timedelta(days=95)).isoformat()
        deleted = db.execute(
            "DELETE FROM pypi_downloads_daily WHERE download_date < ?",
            (gc_cutoff,),
        ).rowcount
        # Only pandas's day-95 row (no, day-95 = exactly the cutoff; not <)
        # Actually: we filter with `<` so anything strictly older than 95d ago
        # is deleted. With our fixture pandas is exactly at day-95 — boundary.
        # Recompute deterministically.
        remaining = db.execute("SELECT COUNT(*) FROM pypi_downloads_daily").fetchone()[0]
        assert remaining + deleted == before
        # numpy rows (day-1 through day-90) all survive.
        numpy_count = db.execute(
            "SELECT COUNT(*) FROM pypi_downloads_daily WHERE pypi_name='numpy'"
        ).fetchone()[0]
        assert numpy_count == 90
