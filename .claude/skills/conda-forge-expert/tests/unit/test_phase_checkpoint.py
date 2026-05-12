"""Tests for the phase_state checkpoint helpers used by Phase N."""
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
    db_path = tmp_path / "cf_atlas.db"
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    yield conn
    conn.close()


class TestPhaseCheckpoint:
    def test_load_returns_none_when_empty(self, db, atlas_mod):
        assert atlas_mod.load_phase_checkpoint(db, "N") is None

    def test_save_and_load_round_trip(self, db, atlas_mod):
        atlas_mod.save_phase_checkpoint(
            db, "N",
            cursor="numpy", items_completed=100, items_total=500,
            status="in_progress",
        )
        cp = atlas_mod.load_phase_checkpoint(db, "N")
        assert cp is not None
        assert cp["last_completed_cursor"] == "numpy"
        assert cp["items_completed"] == 100
        assert cp["items_total"] == 500
        assert cp["status"] == "in_progress"
        assert cp["run_completed_at"] is None
        assert cp["run_started_at"] is not None

    def test_in_progress_continuation_preserves_run_started_at(self, db, atlas_mod):
        atlas_mod.save_phase_checkpoint(
            db, "N", cursor="numpy", items_completed=100,
            items_total=500, status="in_progress",
        )
        started = atlas_mod.load_phase_checkpoint(db, "N")["run_started_at"]
        time.sleep(1.1)
        atlas_mod.save_phase_checkpoint(
            db, "N", cursor="requests", items_completed=200,
            items_total=500, status="in_progress",
        )
        cp = atlas_mod.load_phase_checkpoint(db, "N")
        assert cp["run_started_at"] == started
        assert cp["last_completed_cursor"] == "requests"
        assert cp["items_completed"] == 200

    def test_completion_sets_run_completed_at(self, db, atlas_mod):
        atlas_mod.save_phase_checkpoint(
            db, "N", cursor="zipp", items_completed=500,
            items_total=500, status="completed",
        )
        cp = atlas_mod.load_phase_checkpoint(db, "N")
        assert cp["status"] == "completed"
        assert cp["run_completed_at"] is not None

    def test_new_run_after_completion_resets_started_at(self, db, atlas_mod):
        atlas_mod.save_phase_checkpoint(
            db, "N", cursor="zipp", items_completed=500,
            items_total=500, status="completed",
        )
        completed_started = atlas_mod.load_phase_checkpoint(db, "N")["run_started_at"]
        time.sleep(1.1)
        atlas_mod.save_phase_checkpoint(
            db, "N", cursor="aaa", items_completed=1,
            items_total=300, status="in_progress",
        )
        cp = atlas_mod.load_phase_checkpoint(db, "N")
        assert cp["run_started_at"] > completed_started, \
            "new in_progress run should reset run_started_at"

    def test_multiple_phase_names_independent(self, db, atlas_mod):
        atlas_mod.save_phase_checkpoint(
            db, "N", cursor="numpy", items_completed=10,
            items_total=100, status="in_progress",
        )
        atlas_mod.save_phase_checkpoint(
            db, "B", cursor="abc", items_completed=5,
            items_total=50, status="completed",
        )
        n = atlas_mod.load_phase_checkpoint(db, "N")
        b = atlas_mod.load_phase_checkpoint(db, "B")
        assert n["status"] == "in_progress"
        assert b["status"] == "completed"
        assert n["last_completed_cursor"] == "numpy"
        assert b["last_completed_cursor"] == "abc"

    def test_last_error_stored(self, db, atlas_mod):
        atlas_mod.save_phase_checkpoint(
            db, "N", cursor="numpy", items_completed=1,
            items_total=10, status="failed", last_error="GraphQL 502",
        )
        cp = atlas_mod.load_phase_checkpoint(db, "N")
        assert cp["status"] == "failed"
        assert cp["last_error"] == "GraphQL 502"
