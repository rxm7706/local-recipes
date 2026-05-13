"""pypi-only-candidates CLI surfaces the pypi_universe side table.

Reads `pypi_universe LEFT JOIN packages` to find PyPI projects with no
conda-forge equivalent. Output of the 2026-05-13 actionable-scope audit's
Wave 4 — the admin-persona candidate list that was 📋-open in
`reference/atlas-actionable-intelligence.md`.
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


@pytest.fixture(scope="module")
def cli_mod():
    return _load("pypi_only_candidates")


@pytest.fixture
def db(tmp_path, atlas_mod):
    """Seed an atlas with conda-linked rows + a populated pypi_universe.

    pypi_universe rows that ALSO appear in packages.pypi_name are NOT
    candidates; only universe rows with no matching packages row are.
    """
    db_path = tmp_path / "cf_atlas.db"
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    now = int(time.time())

    # 2 conda-linked rows (also exist in pypi_universe → NOT candidates)
    for conda, pypi in [("numpy", "numpy"), ("scipy", "scipy")]:
        conn.execute(
            "INSERT INTO packages "
            "(conda_name, pypi_name, relationship, match_source, match_confidence) "
            "VALUES (?, ?, 'test', 'test', 'high')",
            (conda, pypi),
        )
    # pypi_universe: 2 matched + 3 unmatched (the candidates we want)
    universe_rows = [
        ("numpy",       100, now),
        ("scipy",       200, now),
        ("flask-extra", 500, now),
        ("django-foo",  600, now),
        ("orphan-pkg",  700, now),
    ]
    for name, serial, ts in universe_rows:
        conn.execute(
            "INSERT INTO pypi_universe (pypi_name, last_serial, fetched_at) "
            "VALUES (?, ?, ?)",
            (name, serial, ts),
        )
    conn.commit()
    yield conn
    conn.close()


class TestFetchCandidates:
    def test_returns_only_unmatched_rows(self, db, cli_mod):
        rows = cli_mod.fetch_candidates(db, limit=100, min_serial=0)
        names = {r["pypi_name"] for r in rows}
        assert names == {"flask-extra", "django-foo", "orphan-pkg"}, \
            f"expected only unmatched candidates, got {names}"

    def test_respects_limit(self, db, cli_mod):
        rows = cli_mod.fetch_candidates(db, limit=2, min_serial=0)
        assert len(rows) == 2

    def test_orders_by_serial_desc(self, db, cli_mod):
        rows = cli_mod.fetch_candidates(db, limit=10, min_serial=0)
        serials = [r["last_serial"] for r in rows]
        assert serials == sorted(serials, reverse=True), \
            f"expected serial-desc order, got {serials}"

    def test_respects_min_serial_filter(self, db, cli_mod):
        rows = cli_mod.fetch_candidates(db, limit=10, min_serial=600)
        names = {r["pypi_name"] for r in rows}
        assert names == {"django-foo", "orphan-pkg"}, \
            f"min-serial filter dropped rows it shouldn't have: {names}"

    def test_matched_rows_excluded(self, db, cli_mod):
        rows = cli_mod.fetch_candidates(db, limit=100, min_serial=0)
        names = {r["pypi_name"] for r in rows}
        # numpy + scipy appear in both packages.pypi_name and pypi_universe;
        # they MUST be excluded from candidates.
        assert "numpy" not in names
        assert "scipy" not in names


class TestUniversePopulated:
    def test_empty_universe_returns_false(self, tmp_path, atlas_mod, cli_mod):
        db_path = tmp_path / "empty.db"
        conn = atlas_mod.open_db(db_path)
        atlas_mod.init_schema(conn)
        assert cli_mod._universe_is_populated(conn) is False
        conn.close()

    def test_populated_universe_returns_true(self, db, cli_mod):
        assert cli_mod._universe_is_populated(db) is True
