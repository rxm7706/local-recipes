"""Story A3 dataset unit tests (collected by ``kedro-test``).

Covers AC-1 (round-trip), AC-2 (stale re-fetched / fresh skipped), FR-3 (per-dataset
TTL differentiation), AC-5 (resumability over persisted Parquet; no ``phase_state``),
and offline construction (mirrors the ``kedro-catalog-check`` resolution path).

Fixture-based, offline, non-credentialed (NFR-1/AD-11): tmp_path Parquet only, no
HTTP/DB. The class must not import any ``IO_DENYLIST`` client — asserted structurally
by ``tests/catalog/test_no_inline_io.py``; this suite proves behavior.
"""

from __future__ import annotations

import pandas as pd

from pyforge.atlas.datasets import IncrementalParquetDataset


def _fp(tmp_path, name="core_downloads"):
    return str(tmp_path / name / f"{name}.parquet")


# -- AC-1: round-trip -----------------------------------------------------


def test_save_stamps_fetched_at_and_load_round_trips(tmp_path):
    ds = IncrementalParquetDataset(filepath=_fp(tmp_path))
    df = pd.DataFrame({"conda_name": ["a", "b"], "downloads": [10, 20]})
    ds.save(df)
    back = ds.load()
    assert "fetched_at" in back.columns
    assert set(back["conda_name"]) == {"a", "b"}
    # every row got an epoch-seconds stamp
    assert (back["fetched_at"] > 0).all()


def test_save_preserves_caller_supplied_fetched_at(tmp_path):
    ds = IncrementalParquetDataset(filepath=_fp(tmp_path))
    df = pd.DataFrame({"conda_name": ["a", "b"], "fetched_at": [111, 222]})
    ds.save(df)
    back = ds.load().sort_values("conda_name").reset_index(drop=True)
    assert back["fetched_at"].tolist() == [111, 222]


def test_custom_fetched_at_column(tmp_path):
    ds = IncrementalParquetDataset(
        filepath=_fp(tmp_path), fetched_at_column="downloads_fetched_at"
    )
    ds.save(pd.DataFrame({"conda_name": ["a"]}))
    back = ds.load()
    assert "downloads_fetched_at" in back.columns


# -- AC-2: stale re-fetched / fresh skipped -------------------------------


def test_stale_mask_gates_old_stale_recent_fresh(tmp_path):
    now = 1_000_000
    ttl = 100
    ds = IncrementalParquetDataset(filepath=_fp(tmp_path), ttl_seconds=ttl)
    df = pd.DataFrame(
        {
            "conda_name": ["old", "boundary", "recent"],
            # old: well past ttl (stale); boundary: exactly at cutoff (fresh);
            # recent: within window (fresh)
            "fetched_at": [now - 500, now - ttl, now - 10],
        }
    )
    mask = ds.stale_mask(df, now=now)
    assert mask.tolist() == [True, False, False]
    # fresh_mask is the complement; is_stale is any()
    assert ds.fresh_mask(df, now=now).tolist() == [False, True, True]
    assert ds.is_stale(df, now=now) is True


def test_missing_fetched_at_is_treated_as_stale(tmp_path):
    now = 1_000_000
    ds = IncrementalParquetDataset(filepath=_fp(tmp_path), ttl_seconds=100)
    # a row with NaN timestamp has no proof of freshness -> stale (legacy
    # NULL-gate-column semantics)
    df = pd.DataFrame({"conda_name": ["a", "b"], "fetched_at": [now - 5, None]})
    assert ds.stale_mask(df, now=now).tolist() == [False, True]
    # and a frame with NO fetched_at column at all -> all stale
    df2 = pd.DataFrame({"conda_name": ["a", "b"]})
    assert ds.stale_mask(df2, now=now).tolist() == [True, True]


def test_ttl_none_never_stale(tmp_path):
    now = 1_000_000
    ds = IncrementalParquetDataset(filepath=_fp(tmp_path))  # ttl_seconds=None
    df = pd.DataFrame({"conda_name": ["ancient"], "fetched_at": [1]})
    assert ds.stale_mask(df, now=now).tolist() == [False]
    assert ds.is_stale(df, now=now) is False


# -- FR-3: per-dataset TTL differentiation --------------------------------


def test_two_instances_with_different_ttls_gate_differently(tmp_path):
    now = 1_000_000
    df = pd.DataFrame(
        {"conda_name": ["x"], "fetched_at": [now - 3600]}  # 1 h old
    )
    short = IncrementalParquetDataset(filepath=_fp(tmp_path, "a"), ttl_seconds=60)  # 1 m
    long = IncrementalParquetDataset(filepath=_fp(tmp_path, "b"), ttl_seconds=86400)  # 1 d
    assert short.stale_mask(df, now=now).tolist() == [True]  # past 1 m -> stale
    assert long.stale_mask(df, now=now).tolist() == [False]  # within 1 d -> fresh


def test_ttl_settable_at_runtime_mirrors_hook_injection(tmp_path):
    now = 1_000_000
    df = pd.DataFrame({"conda_name": ["x"], "fetched_at": [now - 3600]})
    ds = IncrementalParquetDataset(filepath=_fp(tmp_path))
    assert ds.ttl_seconds is None
    assert ds.stale_mask(df, now=now).tolist() == [False]
    ds.ttl_seconds = 60  # what ProjectHooks.after_catalog_created does
    assert ds.ttl_seconds == 60
    assert ds.stale_mask(df, now=now).tolist() == [True]


# -- AC-5: resumability over persisted Parquet ----------------------------


def test_second_load_over_persisted_parquet_needs_no_refetch(tmp_path):
    now = 1_000_000
    ttl = 1000
    ds = IncrementalParquetDataset(filepath=_fp(tmp_path), ttl_seconds=ttl)
    # persist a mix: one fresh row, one stale row
    df = pd.DataFrame(
        {"conda_name": ["fresh", "stale"], "fetched_at": [now - 10, now - 5000]}
    )
    ds.save(df)

    # a NEW instance (simulating a re-run / resumed pipeline) reads the SAME
    # persisted Parquet and reconstructs the freshness verdict with no re-fetch
    resumed = IncrementalParquetDataset(filepath=_fp(tmp_path), ttl_seconds=ttl)
    reloaded = resumed.load()
    verdict = dict(
        zip(reloaded["conda_name"], resumed.stale_mask(reloaded, now=now))
    )
    # only the stale row is surfaced for re-fetch; the fresh row is skipped
    assert bool(verdict["fresh"]) is False
    assert bool(verdict["stale"]) is True


def test_no_phase_state_or_checkpoint_cursor(tmp_path):
    """FR-4: resumability = runner + persisted Parquet; the dataset owns no
    checkpoint cursor table (`phase_state` is deleted from the migrated surface).
    The freshness verdict is derived purely from the persisted `fetched_at`
    column — no side table, no sqlite cursor, no in-memory state carried between
    loads."""
    ds = IncrementalParquetDataset(filepath=_fp(tmp_path), ttl_seconds=100)
    for banned in ("phase_state", "_phase_state", "checkpoint", "_checkpoint", "cursor"):
        assert not hasattr(ds, banned)
    # the module imports no sqlite/DB client (structurally proven by
    # tests/catalog/test_no_inline_io.py; asserted here at the module level too)
    import pyforge.atlas.datasets.incremental_parquet as mod

    assert not hasattr(mod, "sqlite3")


# -- offline construction (mirrors the resolution path) -------------------


def test_constructs_offline_from_catalog_shaped_config(tmp_path):
    """The resolution test builds each flipped entry from config carrying only
    type/filepath/metadata — ttl_seconds must be optional and construction must
    touch no network."""
    ds = IncrementalParquetDataset(
        filepath=_fp(tmp_path), metadata={"layer": "primary"}
    )
    assert ds.ttl_seconds is None
    described = ds._describe()
    assert described["ttl_seconds"] is None
    assert described["fetched_at_column"] == "fetched_at"
    assert "filepath" in described


def test_describe_reports_ttl_and_column(tmp_path):
    ds = IncrementalParquetDataset(filepath=_fp(tmp_path), ttl_seconds=42)
    d = ds._describe()
    assert d["ttl_seconds"] == 42
    assert d["fetched_at_column"] == "fetched_at"
