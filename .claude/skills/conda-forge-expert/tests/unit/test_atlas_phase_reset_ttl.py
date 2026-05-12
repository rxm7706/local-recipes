"""--reset-ttl must scope UPDATE to rows the phase would actually process."""
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


@pytest.fixture(scope="module")
def phase_mod():
    return _load("atlas_phase")


@pytest.fixture
def db(tmp_path, atlas_mod):
    """Seed a tiny atlas with three rows: one for each Phase H scope case."""
    db_path = tmp_path / "cf_atlas.db"
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    import time
    now = int(time.time())
    seeds = [
        # (conda_name, pypi_name, pypi_version_fetched_at) — should be reset
        ("numpy",        "numpy",        now),
        # PyPI-only row that Phase H DOES process — should also be reset
        (None,           "pypi-only-x",  now),
        # Conda-only row Phase H ignores — fetched_at NULL means nothing to clear,
        # and the predicate must not touch it
        ("conda-only-y", None,           None),
    ]
    for conda, pypi, ts in seeds:
        conn.execute(
            "INSERT INTO packages "
            "(conda_name, pypi_name, pypi_version_fetched_at, "
            " relationship, match_source, match_confidence) "
            "VALUES (?, ?, ?, 'test', 'test', 'high')",
            (conda, pypi, ts),
        )
    conn.commit()
    yield conn
    conn.close()


class TestResetTtlScoping:
    def test_phase_h_resets_only_rows_with_pypi_name(self, db, phase_mod):
        touched = phase_mod._reset_ttl(db, "H")
        # Only the two rows with pypi_name are eligible — the conda-only
        # row must be untouched (and untouched means rowcount excludes it).
        assert touched == 2

        rows = list(db.execute(
            "SELECT conda_name, pypi_name, pypi_version_fetched_at "
            "FROM packages ORDER BY COALESCE(conda_name, pypi_name)"
        ))
        # Both pypi_name-bearing rows must now have NULL fetched_at
        for r in rows:
            if r["pypi_name"] is not None:
                assert r["pypi_version_fetched_at"] is None, \
                    f"row {dict(r)} should have NULL fetched_at"

    def test_phase_h_does_not_touch_conda_only_rows(self, db, phase_mod):
        # Seed a sentinel on a column the reset wouldn't touch anyway,
        # then run the reset and verify nothing else changed.
        db.execute(
            "UPDATE packages SET notes = 'sentinel' WHERE conda_name = 'conda-only-y'"
        )
        db.commit()
        phase_mod._reset_ttl(db, "H")
        note = db.execute(
            "SELECT notes FROM packages WHERE conda_name = 'conda-only-y'"
        ).fetchone()
        assert note["notes"] == "sentinel"

    def test_unknown_phase_no_op(self, db, phase_mod):
        assert phase_mod._reset_ttl(db, "B") == 0  # not in _TTL_GATED

    def test_gprime_emits_no_op(self, db, phase_mod, capsys):
        assert phase_mod._reset_ttl(db, "G'") == 0
        out = capsys.readouterr().out
        assert "no simple TTL column" in out
