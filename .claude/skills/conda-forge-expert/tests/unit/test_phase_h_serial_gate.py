"""Phase H eligible-rows gate becomes serial-aware in schema v21+.

Layer 2 of the actionable-scope audit's freshness thread. Phase D's
daily-lean path populates `packages.pypi_last_serial` from the PyPI
Simple API. Phase H's worker stamps `pypi_version_serial_at_fetch` on
each successful fetch. The eligible-rows gate becomes:

    Row is eligible WHEN ANY of:
      (a) pypi_version_fetched_at IS NULL          (never fetched)
      (b) pypi_last_serial != pypi_version_serial_at_fetch  (serial moved)
      (c) pypi_version_fetched_at < (now - 30d)    (safety re-check)

Net: warm-daily Phase H drops from ~5 min to ~30 s on a typical day
because only the ~30-100 packages whose upstream actually moved
get re-fetched.
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
    """Seed atlas with rows exercising each gate branch."""
    db_path = tmp_path / "cf_atlas.db"
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    now = int(time.time())
    recent = now - 2 * 86400   # 2 days ago — within both 7d TTL and 30d safety
    old = now - 40 * 86400      # 40 days ago — past 30d safety

    # (conda_name, pypi_name, fetched_at, last_serial, serial_at_fetch, expected_eligible, reason)
    seeds = [
        # (a) Never fetched — eligible
        ("never-a",         "never-a",         None,   500, None, True,  "never_fetched"),
        # (b) Serial moved — eligible
        ("moved-b",         "moved-b",         recent, 600, 500,  True,  "serial_moved"),
        # (c) 30d safety re-check — eligible
        ("safety-c",        "safety-c",        old,    500, 500,  True,  "safety_recheck"),
        # No conditions met (unchanged + recent) — NOT eligible
        ("unchanged-d",     "unchanged-d",     recent, 500, 500,  False, "unchanged"),
        # Serial NULL (Phase D never ran) — treat as eligible via the NULL-vs-NULL
        # comparison: NULL != NULL is NULL in SQL, so this row exercises the
        # `pypi_version_fetched_at IS NULL` branch only when fetched_at is also NULL.
        ("no-serial-e",     "no-serial-e",     None,   None, None, True,  "never_fetched"),
    ]
    for conda, pypi, fetched_at, serial, sat, _expected, _reason in seeds:
        conn.execute(
            "INSERT INTO packages "
            "(conda_name, pypi_name, pypi_version_fetched_at, "
            " pypi_last_serial, pypi_version_serial_at_fetch, "
            " latest_status, feedstock_archived, "
            " relationship, match_source, match_confidence) "
            "VALUES (?, ?, ?, ?, ?, 'active', 0, 'test', 'test', 'high')",
            (conda, pypi, fetched_at, serial, sat),
        )
    conn.commit()
    yield conn
    conn.close()


class TestSerialGateBranches:
    def test_never_fetched_is_eligible(self, db, atlas_mod):
        rows, *_ = atlas_mod._phase_h_eligible_pypi_names(db)
        names = {r["pypi_name"] for r in rows}
        assert "never-a" in names
        assert "no-serial-e" in names

    def test_serial_moved_is_eligible(self, db, atlas_mod):
        rows, *_ = atlas_mod._phase_h_eligible_pypi_names(db)
        names = {r["pypi_name"] for r in rows}
        assert "moved-b" in names

    def test_safety_recheck_is_eligible(self, db, atlas_mod):
        rows, *_ = atlas_mod._phase_h_eligible_pypi_names(db)
        names = {r["pypi_name"] for r in rows}
        assert "safety-c" in names, \
            "row past 30d should be eligible for safety re-check"

    def test_unchanged_within_safety_window_is_skipped(self, db, atlas_mod):
        rows, *_ = atlas_mod._phase_h_eligible_pypi_names(db)
        names = {r["pypi_name"] for r in rows}
        assert "unchanged-d" not in names, \
            "row with unchanged serial + recent fetch should be skipped"

    def test_eligible_set_is_exactly_four(self, db, atlas_mod):
        rows, *_ = atlas_mod._phase_h_eligible_pypi_names(db)
        names = {r["pypi_name"] for r in rows}
        assert names == {"never-a", "moved-b", "safety-c", "no-serial-e"}, \
            f"unexpected eligible set: {names}"


class TestSerialStampOnFetch:
    """The Phase H worker's UPDATE statements must set
    pypi_version_serial_at_fetch = pypi_last_serial so future runs of
    the eligible-rows gate skip this row until the serial moves again.
    """
    def test_update_statement_includes_serial_stamp(self, atlas_mod):
        """Source-level check: the pypi-json successful-fetch UPDATE writes
        `pypi_version_serial_at_fetch = pypi_last_serial`.
        """
        src = (_SCRIPTS_DIR / "conda_forge_atlas.py").read_text()
        # Look for the canonical pattern in the pypi-json path
        assert "pypi_version_serial_at_fetch = pypi_last_serial" in src, \
            "Phase H worker must stamp pypi_version_serial_at_fetch on fetch"
        # Make sure it appears in BOTH the success path AND the 404 path AND
        # the cf-graph success path (3 occurrences expected).
        count = src.count("pypi_version_serial_at_fetch = pypi_last_serial")
        assert count >= 3, \
            f"expected stamp in ≥3 UPDATE statements (pypi-json success, " \
            f"pypi-json 404, cf-graph success); found {count}"
