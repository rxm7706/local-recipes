"""Phase D split into always-on lean path + TTL-gated universe upsert.

Regression test for the 2026-05-13 actionable-scope audit: Phase D used
to INSERT ~660k pypi_only rows into `packages` on every build. v20 moves
those rows to a `pypi_universe` side table, gated by PHASE_D_UNIVERSE_TTL_DAYS.
The daily-lean path always updates conda-linked serials + discovers
name-coincidence matches; the universe upsert runs weekly.
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
    """Seed an atlas with two conda-linked rows that already have pypi_name."""
    db_path = tmp_path / "cf_atlas.db"
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    seeds = [
        ("numpy", "numpy", None, "both_same_name"),  # pypi_last_serial NULL initially
        ("scipy", "scipy", None, "both_same_name"),
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
    yield conn
    conn.close()


_FAKE_SIMPLE_PROJECTS = [
    {"name": "numpy", "_last-serial": 5000},
    {"name": "scipy", "_last-serial": 5100},
    {"name": "pypi-only-x", "_last-serial": 9001},
    {"name": "pypi-only-y", "_last-serial": 9002},
]


class TestPhaseDWorkingSetUpdate:
    def test_updates_pypi_last_serial_on_conda_linked_rows(self, db, atlas_mod):
        updated, _coincidence = atlas_mod._phase_d_update_working_set(
            db, _FAKE_SIMPLE_PROJECTS
        )
        assert updated == 2

        serials = dict(db.execute(
            "SELECT pypi_name, pypi_last_serial FROM packages "
            "WHERE pypi_name IS NOT NULL"
        ).fetchall())
        assert serials["numpy"] == 5000
        assert serials["scipy"] == 5100

    def test_does_not_insert_pypi_only_rows_in_packages(self, db, atlas_mod):
        atlas_mod._phase_d_update_working_set(db, _FAKE_SIMPLE_PROJECTS)
        pypi_only = db.execute(
            "SELECT COUNT(*) FROM packages WHERE relationship = 'pypi_only'"
        ).fetchone()[0]
        assert pypi_only == 0, \
            "v20+ Phase D must NOT insert pypi_only rows into packages"


class TestPhaseDUniverseFresh:
    def test_empty_universe_returns_not_fresh(self, db, atlas_mod):
        assert atlas_mod._phase_d_universe_is_fresh(db, 7.0) is False

    def test_recent_fetched_at_returns_fresh(self, db, atlas_mod):
        now = int(time.time())
        db.execute(
            "INSERT INTO pypi_universe (pypi_name, last_serial, fetched_at) "
            "VALUES ('x', 1, ?)", (now,)
        )
        db.commit()
        assert atlas_mod._phase_d_universe_is_fresh(db, 7.0) is True

    def test_stale_fetched_at_returns_not_fresh(self, db, atlas_mod):
        old = int(time.time()) - 14 * 86400  # 14 days ago
        db.execute(
            "INSERT INTO pypi_universe (pypi_name, last_serial, fetched_at) "
            "VALUES ('x', 1, ?)", (old,)
        )
        db.commit()
        assert atlas_mod._phase_d_universe_is_fresh(db, 7.0) is False


class TestPhaseDUpsertUniverse:
    def test_inserts_all_projects(self, db, atlas_mod):
        n = atlas_mod._phase_d_upsert_universe(db, _FAKE_SIMPLE_PROJECTS)
        assert n == 4

        rows = list(db.execute(
            "SELECT pypi_name, last_serial FROM pypi_universe ORDER BY pypi_name"
        ))
        assert [(r[0], r[1]) for r in rows] == [
            ("numpy", 5000),
            ("pypi-only-x", 9001),
            ("pypi-only-y", 9002),
            ("scipy", 5100),
        ]

    def test_upsert_is_idempotent(self, db, atlas_mod):
        atlas_mod._phase_d_upsert_universe(db, _FAKE_SIMPLE_PROJECTS)
        atlas_mod._phase_d_upsert_universe(db, _FAKE_SIMPLE_PROJECTS)
        assert db.execute(
            "SELECT COUNT(*) FROM pypi_universe"
        ).fetchone()[0] == 4


class TestPhaseDOrchestration:
    def test_disabled_via_env(self, db, atlas_mod, monkeypatch):
        monkeypatch.setenv("PHASE_D_DISABLED", "1")
        result = atlas_mod.phase_d_pypi_enumeration(db)
        assert result.get("skipped") is True

    def test_universe_disabled_via_env_skips_upsert_only(
        self, db, atlas_mod, monkeypatch
    ):
        monkeypatch.setenv("PHASE_D_UNIVERSE_DISABLED", "1")
        monkeypatch.setattr(atlas_mod, "_fetch_pypi_simple",
                            lambda: _FAKE_SIMPLE_PROJECTS)
        result = atlas_mod.phase_d_pypi_enumeration(db)
        # working set ran
        assert result["serial_updates"] == 2
        # universe did NOT
        assert result["universe_upserts"] == 0
        assert result["universe_skipped_reason"] == "PHASE_D_UNIVERSE_DISABLED=1"
        assert db.execute(
            "SELECT COUNT(*) FROM pypi_universe"
        ).fetchone()[0] == 0

    def test_universe_ttl_fresh_skips_upsert(
        self, db, atlas_mod, monkeypatch
    ):
        # Pre-seed a fresh universe row
        db.execute(
            "INSERT INTO pypi_universe (pypi_name, last_serial, fetched_at) "
            "VALUES ('preexisting', 1, ?)", (int(time.time()),)
        )
        db.commit()

        monkeypatch.setattr(atlas_mod, "_fetch_pypi_simple",
                            lambda: _FAKE_SIMPLE_PROJECTS)
        result = atlas_mod.phase_d_pypi_enumeration(db)
        assert result["universe_upserts"] == 0
        assert "TTL fresh" in (result["universe_skipped_reason"] or "")
        # Universe still has the single pre-existing row, no new ones
        assert db.execute(
            "SELECT COUNT(*) FROM pypi_universe"
        ).fetchone()[0] == 1

    def test_universe_ttl_stale_triggers_upsert(
        self, db, atlas_mod, monkeypatch
    ):
        # Pre-seed a stale universe row
        old = int(time.time()) - 14 * 86400
        db.execute(
            "INSERT INTO pypi_universe (pypi_name, last_serial, fetched_at) "
            "VALUES ('stale', 1, ?)", (old,)
        )
        db.commit()

        monkeypatch.setattr(atlas_mod, "_fetch_pypi_simple",
                            lambda: _FAKE_SIMPLE_PROJECTS)
        result = atlas_mod.phase_d_pypi_enumeration(db)
        assert result["universe_upserts"] == 4  # all 4 fake projects
        assert result["universe_skipped_reason"] is None
