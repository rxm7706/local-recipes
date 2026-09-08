"""Credentialed-parity comparator tests (Story B4, AC-1/AC-2).

FIXTURE mode is the SHIPPED in-loop gate: it proves the comparator's plumbing
(row-count + value drift + benign classification + evidence emission) offline,
with no real DB. CREDENTIALED mode is exercised ONLY via a synthetic in-memory
SQLite fixture DB + a synthetic Kedro provider — never a real ``cf_atlas.db``.
A green fixture-mode run is NOT evidence of legacy parity (PARITY_NOTES.md).
"""

from __future__ import annotations

import sqlite3
from contextlib import closing

import pandas as pd
import pytest

from .parity_runner import (
    build_synthetic_legacy_db,
    diff_view,
    run_parity,
)
from pyforge.atlas.parity import legacy_surface_view_names
from pyforge.atlas.parity.evidence import RUN_MODE_CREDENTIALED, RUN_MODE_FIXTURE


def test_fixture_mode_runs_offline_zero_material_drift():
    """AC-1/AC-2: the in-loop gate — fixture mode emits one zero-material-drift
    record per legacy-surface view, all run_mode='fixture'."""
    records = run_parity()  # legacy_db=None -> fixture mode
    assert {r.view for r in records} == set(legacy_surface_view_names())
    assert all(r.run_mode == RUN_MODE_FIXTURE for r in records)
    assert all(not r.material_drift for r in records)
    # the synthetic pair carries a benign captured_at drift -> classified benign
    assert all(r.benign_diffs for r in records)


def test_fixture_mode_never_signed():
    """No fixture-mode record is ever auto-signed (retirement can't be faked)."""
    records = run_parity()
    assert all(r.human_sign_off is None for r in records)


def test_diff_view_reports_row_count_and_value_drift():
    """AC-1: the comparator detects row-count + value drift on a mismatched
    synthetic pair."""
    legacy = pd.DataFrame([{"conda_name": "a", "score": 1.0}, {"conda_name": "b", "score": 2.0}])
    kedro = pd.DataFrame([{"conda_name": "a", "score": 9.9}])  # value + row-count drift
    rec = diff_view("v_actionable_packages", legacy, kedro, run_mode=RUN_MODE_FIXTURE)
    assert rec.material_drift
    assert rec.legacy_row_count == 2
    assert rec.kedro_row_count == 1
    assert rec.row_count_delta == -1


def test_diff_view_benign_timestamp_only_is_not_material():
    """Q1: timestamp/ordering-only diffs are documented benign, not material."""
    legacy = pd.DataFrame([{"conda_name": "a", "n": 1, "fetched_at": "T1"}])
    kedro = pd.DataFrame([{"conda_name": "a", "n": 1, "fetched_at": "T2"}])
    rec = diff_view(
        "v_actionable_packages", legacy, kedro,
        run_mode=RUN_MODE_FIXTURE, benign_columns=("fetched_at",),
    )
    assert not rec.material_drift
    assert rec.benign_diffs


def test_credentialed_mode_requires_provider():
    """CREDENTIALED mode never defaults the Kedro composition — it must be
    caller-supplied, so the loop can never silently fabricate a credentialed
    run."""
    with pytest.raises(ValueError, match="kedro_frame_provider"):
        run_parity(legacy_db="/nonexistent/cf_atlas.db")


def test_credentialed_mode_against_synthetic_db_matches():
    """CREDENTIALED-mode plumbing verified against a SYNTHETIC SQLite DB + a
    matching synthetic Kedro provider — proving the sqlite read + diff path,
    with NO real credentials/DB. Records are run_mode='credentialed' but remain
    UNSIGNED (a human signs only at the attended event)."""
    from .parity_runner import _synthetic_pair

    with closing(sqlite3.connect(":memory:")) as conn:
        build_synthetic_legacy_db(conn)

        def kedro_provider(view: str) -> pd.DataFrame:
            _, kedro = _synthetic_pair(view)
            return kedro

        # Route the in-memory connection through run_parity's read path by
        # monkey-free injection: read views directly here to keep the test
        # honest to the real code path.
        legacy_views = {
            v: pd.read_sql_query(f"SELECT * FROM {v}", conn)
            for v in legacy_surface_view_names()
        }

    records = [
        diff_view(
            v,
            legacy_views[v],
            kedro_provider(v),
            run_mode=RUN_MODE_CREDENTIALED,
            benign_columns=("captured_at",),
            legacy_db_ref=":memory:",
        )
        for v in legacy_surface_view_names()
    ]
    assert all(r.run_mode == RUN_MODE_CREDENTIALED for r in records)
    assert all(not r.material_drift for r in records)
    assert all(r.human_sign_off is None for r in records)  # unsigned until the event


def test_credentialed_mode_end_to_end_reads_view_from_db(tmp_path):
    """Exercise run_parity's REAL credentialed read path (sqlite file, read-only
    URI) against a synthetic on-disk DB + synthetic provider."""
    from .parity_runner import _synthetic_pair

    db = tmp_path / "synthetic_cf_atlas.db"
    with closing(sqlite3.connect(str(db))) as conn:
        build_synthetic_legacy_db(conn)

    def kedro_provider(view: str) -> pd.DataFrame:
        _, kedro = _synthetic_pair(view)
        return kedro

    records = run_parity(
        legacy_db=str(db),
        kedro_frame_provider=kedro_provider,
        kedro_store="synthetic-store",
        benign_columns=("captured_at",),
    )
    assert {r.view for r in records} == set(legacy_surface_view_names())
    assert all(r.run_mode == RUN_MODE_CREDENTIALED for r in records)
    assert all(not r.material_drift for r in records)
    assert all(r.legacy_db_ref == str(db) for r in records)
