"""Tests for the DW12 rollup-staleness fix (v8.5.3+).

Background: `packages.vuln_*_affecting_current` columns are written by
Phase G against `latest_conda_version` at G-run time. When Phase B
advances `latest_conda_version` on a subsequent run, the rollup goes
stale until the next Phase G. The 2026-05-23 channel-wide CVE audit
caught 6 false positives this way (airflow / ibis-framework /
jupyterlite-core / pytorch-cpu / starlette / strawberry-graphql).

v8.5.3 fixes this two ways:
  1. `_phase_g_sync_current_rollup` — pure-SQL tail step (added at the
     end of `phase_g_prime_per_version_vulns`) that re-derives the
     rollup columns from `package_version_vulns` at the row's CURRENT
     `latest_conda_version`. Idempotent.
  2. `v_current_version_vulns` — query-time-correct SQL view (joined
     to packages.latest_conda_version at SELECT time). New code should
     prefer this over the rollup columns.
"""
from __future__ import annotations

import importlib.util
import sqlite3
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
def schema_conn(atlas_mod, tmp_path):
    """Fresh in-memory atlas conn with the full schema applied."""
    db = tmp_path / "atlas.db"
    conn = atlas_mod.open_db(path=db)
    atlas_mod.init_schema(conn)
    yield conn
    conn.close()


def _seed_pkg(conn, *, conda_name, latest, vuln_total=None, crit_cur=None,
              high_cur=None, kev_cur=None, relationship="conda_and_pypi",
              match_source="test", match_confidence="verified"):
    """Insert a packages row representing a feedstock at a given version."""
    conn.execute(
        "INSERT INTO packages "
        "(conda_name, feedstock_name, latest_conda_version, latest_status, "
        " feedstock_archived, relationship, match_source, match_confidence, "
        " vuln_total, vuln_critical_affecting_current, "
        " vuln_high_affecting_current, vuln_kev_affecting_current) "
        "VALUES (?, ?, ?, 'active', 0, ?, ?, ?, ?, ?, ?, ?)",
        (conda_name, conda_name, latest, relationship, match_source,
         match_confidence, vuln_total, crit_cur, high_cur, kev_cur),
    )


def _seed_pvv(conn, *, conda_name, version, total, crit, high, kev):
    """Insert a package_version_vulns row (per-version truth source)."""
    conn.execute(
        "INSERT INTO package_version_vulns "
        "(conda_name, version, vuln_total, "
        " vuln_critical_affecting_version, vuln_high_affecting_version, "
        " vuln_kev_affecting_version, scanned_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 1779550000)",
        (conda_name, version, total, crit, high, kev),
    )


# ──────────────────────────────────────────────────────────────────────
# _phase_g_sync_current_rollup
# ──────────────────────────────────────────────────────────────────────


def test_rollup_sync_fixes_drift_after_latest_version_advance(atlas_mod, schema_conn):
    """The drift scenario from the 2026-05-23 audit: Phase G saw airflow
    at v3.0.1 (had 5 Crit + 14 High) and wrote those counts; Phase B
    later advanced latest_conda_version to v3.2.1 which has 0 vulns.
    The tail step must overwrite the stale 5/14 with the live 0/0."""
    conn = schema_conn
    # Pre-existing stale state from a prior Phase G run
    _seed_pkg(conn, conda_name="airflow", latest="3.2.1",
              vuln_total=137, crit_cur=5, high_cur=14, kev_cur=0)
    # Live truth from Phase G' at the new version
    _seed_pvv(conn, conda_name="airflow", version="3.2.1",
              total=137, crit=0, high=0, kev=0)
    conn.commit()

    n = atlas_mod._phase_g_sync_current_rollup(conn)
    assert n == 1

    r = conn.execute(
        "SELECT vuln_critical_affecting_current, vuln_high_affecting_current, "
        "       vuln_kev_affecting_current FROM packages WHERE conda_name='airflow'"
    ).fetchone()
    assert tuple(r) == (0, 0, 0), f"stale rollup not reset: {r}"


def test_rollup_sync_updates_vulnerable_current_correctly(atlas_mod, schema_conn):
    """When the current version IS vulnerable, the rollup must reflect
    the per-version row's counts."""
    conn = schema_conn
    _seed_pkg(conn, conda_name="salt", latest="2016.3.0",
              vuln_total=0, crit_cur=0, high_cur=0, kev_cur=0)
    _seed_pvv(conn, conda_name="salt", version="2016.3.0",
              total=45, crit=10, high=10, kev=0)
    conn.commit()

    n = atlas_mod._phase_g_sync_current_rollup(conn)
    assert n == 1

    r = conn.execute(
        "SELECT vuln_total, vuln_critical_affecting_current, "
        "       vuln_high_affecting_current, vuln_kev_affecting_current "
        "FROM packages WHERE conda_name='salt'"
    ).fetchone()
    assert tuple(r) == (45, 10, 10, 0)


def test_rollup_sync_skips_rows_with_no_per_version_data(atlas_mod, schema_conn):
    """If Phase G' hasn't scored the current version yet, leave the
    existing rollup alone — don't zero it out (we don't have authority
    to say 'no vulns' just because the per-version table is empty)."""
    conn = schema_conn
    _seed_pkg(conn, conda_name="lmdb", latest="0.9.35",
              vuln_total=5, crit_cur=3, high_cur=2, kev_cur=0)
    # NO package_version_vulns row for lmdb @ 0.9.35
    conn.commit()

    n = atlas_mod._phase_g_sync_current_rollup(conn)
    assert n == 0  # nothing matched the EXISTS subquery

    r = conn.execute(
        "SELECT vuln_total, vuln_critical_affecting_current, "
        "       vuln_high_affecting_current, vuln_kev_affecting_current "
        "FROM packages WHERE conda_name='lmdb'"
    ).fetchone()
    assert tuple(r) == (5, 3, 2, 0), "rollup overwritten despite no per-version data"


def test_rollup_sync_is_idempotent(atlas_mod, schema_conn):
    """Running the sync twice in a row produces the same result as
    running it once."""
    conn = schema_conn
    _seed_pkg(conn, conda_name="ckan", latest="2.9.4",
              vuln_total=20, crit_cur=99, high_cur=99, kev_cur=99)  # nonsense
    _seed_pvv(conn, conda_name="ckan", version="2.9.4",
              total=8, crit=1, high=3, kev=0)
    conn.commit()

    n1 = atlas_mod._phase_g_sync_current_rollup(conn)
    state1 = conn.execute(
        "SELECT vuln_total, vuln_critical_affecting_current, "
        "       vuln_high_affecting_current, vuln_kev_affecting_current "
        "FROM packages WHERE conda_name='ckan'"
    ).fetchone()

    n2 = atlas_mod._phase_g_sync_current_rollup(conn)
    state2 = conn.execute(
        "SELECT vuln_total, vuln_critical_affecting_current, "
        "       vuln_high_affecting_current, vuln_kev_affecting_current "
        "FROM packages WHERE conda_name='ckan'"
    ).fetchone()

    assert tuple(state1) == tuple(state2) == (8, 1, 3, 0)
    assert n1 == n2 == 1


def test_rollup_sync_handles_mixed_population(atlas_mod, schema_conn):
    """A realistic atlas state: some packages have current-version
    per-version data, some don't. Only the ones with data get synced."""
    conn = schema_conn
    # airflow: stale rollup, fresh per-version data → MUST sync
    _seed_pkg(conn, conda_name="airflow", latest="3.2.1",
              vuln_total=137, crit_cur=5, high_cur=14, kev_cur=0)
    _seed_pvv(conn, conda_name="airflow", version="3.2.1",
              total=137, crit=0, high=0, kev=0)
    # lmdb: no per-version data → leave alone
    _seed_pkg(conn, conda_name="lmdb", latest="0.9.35",
              vuln_total=5, crit_cur=3, high_cur=2, kev_cur=0)
    # salt: per-version data confirms current is vulnerable → sync
    _seed_pkg(conn, conda_name="salt", latest="2016.3.0",
              vuln_total=0, crit_cur=0, high_cur=0, kev_cur=0)
    _seed_pvv(conn, conda_name="salt", version="2016.3.0",
              total=45, crit=10, high=10, kev=0)
    conn.commit()

    n = atlas_mod._phase_g_sync_current_rollup(conn)
    assert n == 2

    afl = conn.execute(
        "SELECT vuln_critical_affecting_current FROM packages WHERE conda_name='airflow'"
    ).fetchone()
    lmdb = conn.execute(
        "SELECT vuln_critical_affecting_current FROM packages WHERE conda_name='lmdb'"
    ).fetchone()
    salt = conn.execute(
        "SELECT vuln_critical_affecting_current FROM packages WHERE conda_name='salt'"
    ).fetchone()
    assert afl[0] == 0   # synced down from 5
    assert lmdb[0] == 3  # untouched
    assert salt[0] == 10  # synced up from 0


# ──────────────────────────────────────────────────────────────────────
# v_current_version_vulns view
# ──────────────────────────────────────────────────────────────────────


def test_view_exists_and_returns_query_time_correct_data(atlas_mod, schema_conn):
    """The view must compute counts at SELECT time, so stale rollup
    columns can't poison it. Set the rollup columns to nonsense; the
    view should still return the per-version truth."""
    conn = schema_conn
    _seed_pkg(conn, conda_name="airflow", latest="3.2.1",
              vuln_total=137, crit_cur=99, high_cur=99, kev_cur=99)  # all wrong
    _seed_pvv(conn, conda_name="airflow", version="3.2.1",
              total=137, crit=0, high=0, kev=0)
    conn.commit()

    r = conn.execute(
        "SELECT current_version, vuln_critical_current, vuln_high_current, "
        "       vuln_kev_current FROM v_current_version_vulns "
        "WHERE conda_name='airflow'"
    ).fetchone()
    assert tuple(r) == ("3.2.1", 0, 0, 0), f"view returned stale rollup: {r}"


def test_view_returns_zeros_for_unsynced_versions(atlas_mod, schema_conn):
    """If Phase G' hasn't scored the current version, the view's
    COALESCE returns 0 across the board (since the LEFT JOIN is NULL).
    Distinct from the sync helper, the view does NOT preserve stale
    rollup data — it represents 'what does package_version_vulns say
    about this version' which is 'we haven't scored it yet'."""
    conn = schema_conn
    _seed_pkg(conn, conda_name="lmdb", latest="0.9.35",
              vuln_total=5, crit_cur=3, high_cur=2, kev_cur=0)
    # No package_version_vulns row
    conn.commit()

    r = conn.execute(
        "SELECT vuln_critical_current, vuln_high_current, vuln_kev_current, "
        "       vuln_scanned_at FROM v_current_version_vulns WHERE conda_name='lmdb'"
    ).fetchone()
    assert tuple(r) == (0, 0, 0, None)


def test_view_handles_null_latest_version(atlas_mod, schema_conn):
    """Packages with no latest_conda_version (e.g. PyPI-only rows) should
    not error in the view; they just return NULL/0 from the LEFT JOIN."""
    conn = schema_conn
    conn.execute(
        "INSERT INTO packages "
        "(conda_name, pypi_name, latest_status, feedstock_archived, "
        " relationship, match_source, match_confidence) "
        "VALUES (NULL, 'some-pypi-only-package', 'pypi_only', 0, "
        "        'pypi_only', 'test', 'verified')"
    )
    conn.commit()

    rows = list(conn.execute("SELECT * FROM v_current_version_vulns"))
    assert len(rows) == 1  # row exists; no error
    assert rows[0]["current_version"] is None
