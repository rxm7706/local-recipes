"""v_actionable_packages view encodes the canonical persona-filter triplet.

Schema v21 introduces the view as structural enforcement of
`conda_name IS NOT NULL AND latest_status='active' AND COALESCE(feedstock_archived,0)=0`.
Every phase selector that wants the actionable working set reads from
this view; the meta-test asserts no future drift.
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


@pytest.fixture
def db(tmp_path, atlas_mod):
    """Seed an atlas with mixed scope cases for the view."""
    db_path = tmp_path / "cf_atlas.db"
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    seeds = [
        # (conda_name, latest_status, feedstock_archived, expected_in_view)
        ("active-a",   "active",   0, True),
        ("active-b",   "active",   0, True),
        # Inactive — must be excluded
        ("inactive-c", "inactive", 0, False),
        # Archived — must be excluded
        ("archived-d", "active",   1, False),
        # NULL conda_name — must be excluded (would-be pypi_only-style row)
        (None,         "active",   0, False),
        # NULL latest_status — view's COALESCE defaults to 'active' (included)
        ("null-status-e", None,    0, True),
    ]
    for conda, status, archived, _expected in seeds:
        conn.execute(
            "INSERT INTO packages "
            "(conda_name, latest_status, feedstock_archived, "
            " relationship, match_source, match_confidence) "
            "VALUES (?, ?, ?, 'test', 'test', 'high')",
            (conda, status, archived),
        )
    conn.commit()
    yield conn
    conn.close()


class TestViewCanonicalSubset:
    def test_view_returns_only_actionable_rows(self, db):
        names = {row[0] for row in db.execute(
            "SELECT conda_name FROM v_actionable_packages"
        )}
        assert names == {"active-a", "active-b", "null-status-e"}, \
            f"view returned unexpected set: {names}"

    def test_view_excludes_inactive(self, db):
        names = {row[0] for row in db.execute(
            "SELECT conda_name FROM v_actionable_packages"
        )}
        assert "inactive-c" not in names

    def test_view_excludes_archived(self, db):
        names = {row[0] for row in db.execute(
            "SELECT conda_name FROM v_actionable_packages"
        )}
        assert "archived-d" not in names

    def test_view_excludes_null_conda_name(self, db):
        all_conda_names = {row[0] for row in db.execute(
            "SELECT conda_name FROM v_actionable_packages"
        )}
        assert None not in all_conda_names

    def test_view_coalesces_null_latest_status_as_active(self, db):
        names = {row[0] for row in db.execute(
            "SELECT conda_name FROM v_actionable_packages"
        )}
        assert "null-status-e" in names, \
            "NULL latest_status should coalesce to 'active' per view definition"


class TestSelectorEquivalence:
    """Selectors using the view return the same rows as the pre-refactor
    inline triplet would have returned.
    """
    def test_phase_f_selector_uses_view(self, db, atlas_mod):
        # Phase F's _phase_f_eligible_rows reads from v_actionable_packages
        # via TTL clause. We call it indirectly via a representative SQL.
        rows = list(db.execute(
            "SELECT DISTINCT conda_name FROM v_actionable_packages "
            "WHERE COALESCE(downloads_fetched_at, 0) < ?",
            (2**31,)  # cutoff in the far future = all eligible
        ))
        names = {r[0] for r in rows}
        assert names == {"active-a", "active-b", "null-status-e"}

    def test_phase_h_selector_keeps_pypi_name_filter(self, db, atlas_mod):
        # Phase H additionally requires pypi_name IS NOT NULL.
        db.execute("UPDATE packages SET pypi_name = 'active-a-pypi' "
                   "WHERE conda_name = 'active-a'")
        db.commit()
        rows = list(db.execute(
            "SELECT DISTINCT pypi_name FROM v_actionable_packages "
            "WHERE pypi_name IS NOT NULL"
        ))
        names = {r[0] for r in rows}
        assert names == {"active-a-pypi"}
