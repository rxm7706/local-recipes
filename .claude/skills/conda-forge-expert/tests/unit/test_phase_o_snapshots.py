"""Phase O — pypi_universe serial-snapshot deltas + activity_band classification.

Tier 1 of the v8.1.0 PyPI intelligence layer. No new HTTP — Phase O reads
`pypi_universe.last_serial`, writes a daily snapshot row, prunes old
snapshots past `PHASE_O_SNAPSHOT_RETAIN_DAYS`, then computes per-name
serial_delta_7d / serial_delta_30d and classifies into hot / warm / cold /
dormant.
"""
from __future__ import annotations

import importlib.util
import sys
import time
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
    """Fresh v22 atlas with a few pypi_universe seeds."""
    db_path = tmp_path / "cf_atlas.db"
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    now = int(time.time())
    seeds = [
        # (pypi_name, current_last_serial)
        ("hot-pkg",     1_000_000),  # will get historical snapshots at 1d & 30d ago
        ("warm-pkg",    2_000_000),
        ("cold-pkg",    3_000_000),
        ("dormant-pkg", 4_000_000),
    ]
    for name, serial in seeds:
        conn.execute(
            "INSERT INTO pypi_universe (pypi_name, last_serial, fetched_at) "
            "VALUES (?, ?, ?)",
            (name, serial, now),
        )
    conn.commit()
    yield conn
    conn.close()


class TestPhaseOFirstRun:
    """First-run behavior: with no prior snapshots, every row classifies as
    'dormant' (delta = 0)."""

    def test_first_run_classifies_all_as_dormant(self, db, atlas_mod):
        result = atlas_mod.phase_o_serial_snapshots(db)
        assert not result.get("skipped")
        assert result["snapshot_rows_inserted"] == 4
        assert result["activity_band_counts"] == {"dormant": 4}

    def test_first_run_populates_pypi_intelligence(self, db, atlas_mod):
        atlas_mod.phase_o_serial_snapshots(db)
        rows = list(db.execute(
            "SELECT pypi_name, activity_band, serial_delta_7d, serial_delta_30d "
            "FROM pypi_intelligence ORDER BY pypi_name"
        ))
        assert len(rows) == 4
        for r in rows:
            assert r["activity_band"] == "dormant"
            assert r["serial_delta_7d"] == 0
            assert r["serial_delta_30d"] == 0


class TestPhaseOActivityBands:
    """When historical snapshots exist, deltas drive the activity_band
    classification. Snapshot lookup: most-recent row with `snapshot_at <=
    cutoff` for each of the 7d and 30d cutoffs. A snapshot inside the
    window (e.g. 3d ago) does NOT qualify as the "7d-ago reference" because
    it's more recent than the 7d cutoff."""

    def test_hot_band_when_serial_jumped_in_last_7d(self, db, atlas_mod):
        # Seed snapshot AT-OR-BEFORE 7d ago: 8d-ago snapshot with serial 10 less.
        # delta_7d = current(1_000_000) - reference(999_990) = 10 >= hot_threshold(5).
        now = int(time.time())
        db.execute(
            "INSERT INTO pypi_universe_serial_snapshots "
            "(pypi_name, last_serial, snapshot_at) VALUES (?, ?, ?)",
            ("hot-pkg", 1_000_000 - 10, now - 8 * 86400),
        )
        db.commit()
        result = atlas_mod.phase_o_serial_snapshots(db)
        row = db.execute(
            "SELECT activity_band, serial_delta_7d, serial_delta_30d "
            "FROM pypi_intelligence WHERE pypi_name='hot-pkg'"
        ).fetchone()
        assert row["activity_band"] == "hot"
        assert row["serial_delta_7d"] == 10
        assert result["activity_band_counts"].get("hot") == 1

    def test_warm_band_when_only_30d_threshold_met(self, db, atlas_mod):
        # Need delta_7d < hot_threshold AND delta_30d >= warm_threshold.
        # Two snapshots needed: a close-to-7d-cutoff one with small delta,
        # and a 30d+ one with bigger delta.
        now = int(time.time())
        db.execute(
            "INSERT INTO pypi_universe_serial_snapshots "
            "(pypi_name, last_serial, snapshot_at) VALUES (?, ?, ?)",
            ("warm-pkg", 2_000_000 - 2, now - 8 * 86400),     # 7d ref: delta=2
        )
        db.execute(
            "INSERT INTO pypi_universe_serial_snapshots "
            "(pypi_name, last_serial, snapshot_at) VALUES (?, ?, ?)",
            ("warm-pkg", 2_000_000 - 10, now - 31 * 86400),   # 30d ref: delta=10
        )
        db.commit()
        atlas_mod.phase_o_serial_snapshots(db)
        row = db.execute(
            "SELECT activity_band, serial_delta_7d, serial_delta_30d "
            "FROM pypi_intelligence WHERE pypi_name='warm-pkg'"
        ).fetchone()
        # delta_7d=2 < hot_threshold(5); delta_30d=10 >= warm_threshold(5) → warm
        assert row["serial_delta_7d"] == 2
        assert row["serial_delta_30d"] == 10
        assert row["activity_band"] == "warm"

    def test_cold_band_when_only_one_event_in_30d(self, db, atlas_mod):
        # delta_7d=0 (no <=7d snapshot), delta_30d=1 (single event in 30d window).
        now = int(time.time())
        db.execute(
            "INSERT INTO pypi_universe_serial_snapshots "
            "(pypi_name, last_serial, snapshot_at) VALUES (?, ?, ?)",
            ("cold-pkg", 3_000_000, now - 8 * 86400),         # 7d ref: delta=0
        )
        db.execute(
            "INSERT INTO pypi_universe_serial_snapshots "
            "(pypi_name, last_serial, snapshot_at) VALUES (?, ?, ?)",
            ("cold-pkg", 3_000_000 - 1, now - 31 * 86400),    # 30d ref: delta=1
        )
        db.commit()
        atlas_mod.phase_o_serial_snapshots(db)
        row = db.execute(
            "SELECT activity_band, serial_delta_7d, serial_delta_30d "
            "FROM pypi_intelligence WHERE pypi_name='cold-pkg'"
        ).fetchone()
        assert row["serial_delta_7d"] == 0
        assert row["serial_delta_30d"] == 1
        assert row["activity_band"] == "cold"


class TestPhaseORetention:
    """Snapshots older than PHASE_O_SNAPSHOT_RETAIN_DAYS are pruned each run."""

    def test_old_snapshots_pruned(self, db, atlas_mod):
        now = int(time.time())
        days_ago_120 = now - 120 * 86400   # past 90 d default retention
        db.execute(
            "INSERT INTO pypi_universe_serial_snapshots "
            "(pypi_name, last_serial, snapshot_at) VALUES (?, ?, ?)",
            ("hot-pkg", 999_999, days_ago_120),
        )
        db.commit()
        pre = db.execute(
            "SELECT COUNT(*) FROM pypi_universe_serial_snapshots WHERE snapshot_at = ?",
            (days_ago_120,),
        ).fetchone()[0]
        assert pre == 1
        result = atlas_mod.phase_o_serial_snapshots(db)
        post = db.execute(
            "SELECT COUNT(*) FROM pypi_universe_serial_snapshots WHERE snapshot_at = ?",
            (days_ago_120,),
        ).fetchone()[0]
        assert post == 0
        assert result["snapshot_rows_pruned"] >= 1

    def test_retain_env_var_honored(self, db, atlas_mod, monkeypatch):
        monkeypatch.setenv("PHASE_O_SNAPSHOT_RETAIN_DAYS", "1")
        now = int(time.time())
        days_ago_3 = now - 3 * 86400
        db.execute(
            "INSERT INTO pypi_universe_serial_snapshots "
            "(pypi_name, last_serial, snapshot_at) VALUES (?, ?, ?)",
            ("hot-pkg", 999_998, days_ago_3),
        )
        db.commit()
        atlas_mod.phase_o_serial_snapshots(db)
        # 3d-old snapshot is past the 1d retention — should be pruned
        post = db.execute(
            "SELECT COUNT(*) FROM pypi_universe_serial_snapshots WHERE snapshot_at = ?",
            (days_ago_3,),
        ).fetchone()[0]
        assert post == 0


class TestPhaseOIdempotency:
    """Re-running Phase O within the same second is a no-op for that
    timestamp; pypi_intelligence rows are upserted in-place."""

    def test_rerun_same_second_is_idempotent(self, db, atlas_mod):
        atlas_mod.phase_o_serial_snapshots(db)
        first_row_count = db.execute(
            "SELECT COUNT(*) FROM pypi_universe_serial_snapshots"
        ).fetchone()[0]
        first_intel_count = db.execute(
            "SELECT COUNT(*) FROM pypi_intelligence"
        ).fetchone()[0]
        atlas_mod.phase_o_serial_snapshots(db)
        second_row_count = db.execute(
            "SELECT COUNT(*) FROM pypi_universe_serial_snapshots"
        ).fetchone()[0]
        second_intel_count = db.execute(
            "SELECT COUNT(*) FROM pypi_intelligence"
        ).fetchone()[0]
        # Same number of rows; INSERT OR REPLACE preserves the count, not
        # double-inserting.
        assert second_row_count == first_row_count
        assert second_intel_count == first_intel_count


class TestPhaseODisableEnv:
    """PHASE_O_DISABLED=1 skips Phase O cleanly."""

    def test_disabled_env_skips(self, db, atlas_mod, monkeypatch):
        monkeypatch.setenv("PHASE_O_DISABLED", "1")
        result = atlas_mod.phase_o_serial_snapshots(db)
        assert result.get("skipped") is True
        # No rows written
        n = db.execute(
            "SELECT COUNT(*) FROM pypi_universe_serial_snapshots"
        ).fetchone()[0]
        assert n == 0


class TestPhaseOEmptyUniverse:
    """When pypi_universe is empty (cold-start before Phase D ran), Phase O
    skips cleanly without raising."""

    def test_empty_universe_skips(self, tmp_path, atlas_mod):
        db_path = tmp_path / "empty.db"
        conn = atlas_mod.open_db(db_path)
        atlas_mod.init_schema(conn)
        result = atlas_mod.phase_o_serial_snapshots(conn)
        assert result.get("skipped") is True
        assert "Phase D first" in result.get("reason", "")
        conn.close()
