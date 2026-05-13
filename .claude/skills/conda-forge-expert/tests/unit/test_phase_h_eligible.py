"""Phase H denominator gate must scope to actionable conda-linked rows.

Regression test for the 2026-05-13 actionable-scope audit: before the v20
schema change, Phase H's `pypi-json` path selected on `pypi_name IS NOT NULL`
+ TTL only, which silently included ~660k `relationship='pypi_only'` rows
that no CLI consumes. The fix adopts the canonical persona-filter triplet
(conda_name + active + !archived) used by Phases F/G/G'/K/L/N.
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
    """Seed an atlas with mixed scope cases for Phase H's gate.

    Six rows that together exercise every branch of the canonical triplet:
      - actionable: conda-linked, active, not archived → MUST be selected
      - pypi_only: conda_name IS NULL → MUST be excluded
      - archived: feedstock_archived = 1 → MUST be excluded
      - inactive: latest_status = 'inactive' → MUST be excluded
      - stale TTL fresh: fetched_at recent → MUST be excluded (TTL gate)
      - no pypi_name: pypi_name IS NULL → MUST be excluded
    """
    db_path = tmp_path / "cf_atlas.db"
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    now = int(time.time())
    stale = now - 30 * 86400  # 30 days ago, well past PHASE_H_TTL_DAYS=7

    # (conda_name, pypi_name, fetched_at, latest_status, feedstock_archived, relationship)
    seeds = [
        # Actionable — should pass the gate
        ("numpy",       "numpy",       stale, "active",   0, "both_same_name"),
        ("scipy",       "scipy",       stale, "active",   0, "both_same_name"),
        # pypi_only (no conda equivalent) — must be excluded
        (None,          "pypi-only-1", stale, "active",   0, "pypi_only"),
        (None,          "pypi-only-2", stale, "active",   0, "pypi_only"),
        # Archived feedstock — must be excluded
        ("archived-pkg", "archived-pkg", stale, "active", 1, "both_same_name"),
        # Inactive (yanked) — must be excluded
        ("inactive-pkg", "inactive-pkg", stale, "inactive", 0, "both_same_name"),
        # TTL-fresh — must be excluded
        ("fresh-pkg",   "fresh-pkg",   now,   "active",   0, "both_same_name"),
        # No pypi_name — must be excluded (Phase H is PyPI-scoped)
        ("conda-only",  None,          None,  "active",   0, "conda_only"),
    ]
    for conda, pypi, ts, status, archived, rel in seeds:
        conn.execute(
            "INSERT INTO packages "
            "(conda_name, pypi_name, pypi_version_fetched_at, latest_status, "
            " feedstock_archived, relationship, match_source, match_confidence) "
            "VALUES (?, ?, ?, ?, ?, ?, 'test', 'high')",
            (conda, pypi, ts, status, archived, rel),
        )
    conn.commit()
    yield conn
    conn.close()


class TestPhaseHEligible:
    def test_includes_actionable_conda_linked_active_unarchived_rows(self, db, atlas_mod):
        """The happy path: rows with conda equivalents, active, not archived."""
        rows, _ttl, _conc, _lim = atlas_mod._phase_h_eligible_pypi_names(db)
        names = {r["pypi_name"] for r in rows}
        assert "numpy" in names
        assert "scipy" in names

    def test_excludes_pypi_only_rows(self, db, atlas_mod):
        """The audit's load-bearing finding — pypi_only rows must NOT be fetched."""
        rows, _ttl, _conc, _lim = atlas_mod._phase_h_eligible_pypi_names(db)
        names = {r["pypi_name"] for r in rows}
        assert "pypi-only-1" not in names, \
            "Phase H must not fetch pypi_only rows — they have no consumer"
        assert "pypi-only-2" not in names

    def test_excludes_archived_feedstocks(self, db, atlas_mod):
        rows, _ttl, _conc, _lim = atlas_mod._phase_h_eligible_pypi_names(db)
        names = {r["pypi_name"] for r in rows}
        assert "archived-pkg" not in names

    def test_excludes_inactive_rows(self, db, atlas_mod):
        rows, _ttl, _conc, _lim = atlas_mod._phase_h_eligible_pypi_names(db)
        names = {r["pypi_name"] for r in rows}
        assert "inactive-pkg" not in names

    def test_excludes_ttl_fresh_rows(self, db, atlas_mod):
        rows, _ttl, _conc, _lim = atlas_mod._phase_h_eligible_pypi_names(db)
        names = {r["pypi_name"] for r in rows}
        assert "fresh-pkg" not in names

    def test_exact_eligible_count(self, db, atlas_mod):
        """Of 8 seeded rows, exactly 2 are actionable (numpy, scipy)."""
        rows, _ttl, _conc, _lim = atlas_mod._phase_h_eligible_pypi_names(db)
        assert len(rows) == 2, \
            f"expected exactly 2 actionable rows, got {len(rows)}: {[r['pypi_name'] for r in rows]}"
