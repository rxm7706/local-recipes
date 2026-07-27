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
import pytest

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


def test_load_missing_payload_returns_empty_dataframe(tmp_path):
    # AUD-ATLAS-015: cold-start upsert nodes need an empty frame, not a raise.
    ds = IncrementalParquetDataset(filepath=_fp(tmp_path, "missing_store"))
    back = ds.load()
    assert isinstance(back, pd.DataFrame)
    assert back.empty


def test_merge_on_upsert_retains_unmatched_existing_rows(tmp_path):
    # AUD-ATLAS-015: eligible delta must not wipe fresh keys from the store.
    ds = IncrementalParquetDataset(filepath=_fp(tmp_path, "pypi_current"), merge_on="pypi_name")
    ds.save(
        pd.DataFrame(
            {
                "pypi_name": ["fresh", "other"],
                "version": ["4.0", "9.0"],
            }
        )
    )
    ds.save(pd.DataFrame({"pypi_name": ["never"], "version": ["1.1"]}))
    back = ds.load().set_index("pypi_name")["version"].to_dict()
    assert back == {"fresh": "4.0", "other": "9.0", "never": "1.1"}


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


def test_ms_normalization_and_coercion_created_nan_is_filled(tmp_path):
    """DW-A3-P10 + review regression: a fetched_at column mixing a ms-magnitude int
    with a non-numeric junk cell must (a) normalize the ms value to seconds and (b)
    FILL the NaN that coercion creates — persisting it would loop re-fetch forever.
    needs_fill is computed pre-coercion (junk is not NaN), so the fill must re-check
    AFTER _to_epoch_seconds."""
    ds = IncrementalParquetDataset(filepath=_fp(tmp_path))
    df = pd.DataFrame({"conda_name": ["ms", "junk"], "fetched_at": [1_700_000_000_000, "oops"]})
    ds.save(df)
    back = ds.load().set_index("conda_name")
    assert back.loc["ms", "fetched_at"] == 1_700_000_000  # ms -> s
    assert pd.notna(back.loc["junk", "fetched_at"])        # coercion-NaN was filled
    assert back.loc["junk", "fetched_at"] > 0


def test_partially_nan_fetched_at_column_is_fully_stamped(tmp_path):
    """Review-pass P1 (perpetual re-fetch loop): an incremental append leaves an
    already-present ``fetched_at`` column with existing rows stamped and NEW rows
    NaN. Stamping only at COLUMN level (``if col not in df.columns``) would take
    the else branch and persist NaN forever → the new rows read stale on every run
    → the dataset never converges. save() must FILL the missing entries so the
    whole frame round-trips fully stamped."""
    ds = IncrementalParquetDataset(filepath=_fp(tmp_path), ttl_seconds=100)
    df = pd.DataFrame(
        {
            "conda_name": ["existing", "appended"],
            # existing row already stamped; appended row has no timestamp yet
            "fetched_at": [111, None],
        }
    )
    ds.save(df)
    back = ds.load().sort_values("conda_name").reset_index(drop=True)
    # NO NaN survives — the appended row got a fresh epoch-seconds stamp.
    assert back["fetched_at"].notna().all()
    assert (back["fetched_at"] > 0).all()
    # the pre-existing stamp is preserved verbatim (not overwritten).
    existing = back.loc[back["conda_name"] == "existing", "fetched_at"].iloc[0]
    assert int(existing) == 111
    # the APPENDED row (was NaN) now carries a real recent stamp — so a freshness
    # check just after it was written classifies it FRESH, not perpetually stale.
    # (The 'existing' row stamped 111 is legitimately ancient → stale; that is
    # correct behavior, not the P1 bug.)
    now = int(back["fetched_at"].max()) + 1
    verdict = dict(zip(back["conda_name"], ds.stale_mask(back, now=now)))
    assert bool(verdict["appended"]) is False  # the loop is broken


# -- AC-2: stale re-fetched / fresh skipped -------------------------------


def test_stale_mask_gates_old_stale_recent_fresh(tmp_path):
    now = 1_000_000
    ttl = 100
    ds = IncrementalParquetDataset(filepath=_fp(tmp_path), ttl_seconds=ttl)
    df = pd.DataFrame(
        {
            "conda_name": ["old", "boundary", "recent"],
            # old: well past ttl (stale); boundary: exactly at cutoff — FRESH under
            # the DW-A3-TTL-parity STRICT `<` call (verified vs legacy eligibility SQL
            # CFA:2803/5167 `COALESCE(fetched_at,0) < now-ttl`); recent: fresh
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


def test_ttl_none_fail_closed_all_stale(tmp_path):
    # AUD-ATLAS-031: unset TTL must not silently skip refresh.
    now = 1_000_000
    ds = IncrementalParquetDataset(filepath=_fp(tmp_path))  # ttl_seconds=None
    df = pd.DataFrame({"conda_name": ["ancient"], "fetched_at": [1]})
    assert ds.stale_mask(df, now=now).tolist() == [True]
    assert ds.is_stale(df, now=now) is True


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
    assert ds.stale_mask(df, now=now).tolist() == [True]
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


# -- P3: ttl_seconds type validation --------------------------------------


def test_ttl_string_is_coerced_to_int(tmp_path):
    """A ttl arriving as a string (e.g. a mis-typed params value) is coerced."""
    ds = IncrementalParquetDataset(filepath=_fp(tmp_path), ttl_seconds="3600")
    assert ds.ttl_seconds == 3600
    assert isinstance(ds.ttl_seconds, int)
    # the same coercion applies at the runtime setter (hook injection point)
    ds.ttl_seconds = "60"
    assert ds.ttl_seconds == 60


def test_ttl_zero_means_everything_stale(tmp_path):
    """ttl_seconds=0 is FALSY but NOT None — it must gate (cutoff == now), so a
    row stamped in the past is stale, distinct from the None 'never stale' case."""
    now = 1_000_000
    ds = IncrementalParquetDataset(filepath=_fp(tmp_path), ttl_seconds=0)
    assert ds.ttl_seconds == 0
    df = pd.DataFrame({"conda_name": ["a"], "fetched_at": [now - 1]})
    assert ds.stale_mask(df, now=now).tolist() == [True]


def test_negative_ttl_raises(tmp_path):
    with pytest.raises(ValueError, match=">= 0"):
        IncrementalParquetDataset(filepath=_fp(tmp_path), ttl_seconds=-1)
    ds = IncrementalParquetDataset(filepath=_fp(tmp_path))
    with pytest.raises(ValueError, match=">= 0"):
        ds.ttl_seconds = -5


def test_non_numeric_ttl_raises(tmp_path):
    with pytest.raises(ValueError, match="integer"):
        IncrementalParquetDataset(filepath=_fp(tmp_path), ttl_seconds="not-a-number")
    with pytest.raises(ValueError, match="integer"):
        IncrementalParquetDataset(filepath=_fp(tmp_path), ttl_seconds=object())
    # bool is an int subclass but is never a meaningful ttl -> rejected
    with pytest.raises(ValueError, match="integer"):
        IncrementalParquetDataset(filepath=_fp(tmp_path), ttl_seconds=True)


def test_runtime_none_injection_warns_but_construction_none_is_silent(tmp_path, caplog):
    """None at construction is the legitimate 'no ttl yet' default (offline
    resolution path) — silent. None injected at runtime (a misconfigured
    params:ttls.<name>: null) is suspicious — warned, distinctly."""
    import logging

    with caplog.at_level(logging.WARNING):
        ds = IncrementalParquetDataset(filepath=_fp(tmp_path))  # ttl_seconds=None
    assert ds.ttl_seconds is None
    assert not caplog.records  # construction-time None is silent

    with caplog.at_level(logging.WARNING):
        ds.ttl_seconds = None  # runtime injection of None
    assert ds.ttl_seconds is None
    assert any("None at runtime" in r.getMessage() for r in caplog.records)


# -- P4: outer versioning is unsupported (rejected clearly) ----------------


def test_version_is_rejected_with_clear_error(tmp_path):
    """The outer versioned machinery is delegated to the inner ParquetDataset and
    is unsupported here (a mis-wired exists_function signature would otherwise
    raise an opaque TypeError only at version-resolution time). Construction with
    any non-None ``version`` must fail fast and clearly."""
    from kedro.io.core import Version

    with pytest.raises(ValueError, match="does not support outer catalog versioning"):
        IncrementalParquetDataset(filepath=_fp(tmp_path), version=Version(None, None))
    with pytest.raises(ValueError, match="does not support outer catalog versioning"):
        IncrementalParquetDataset(filepath=_fp(tmp_path), version="2024-01-01T00.00.00.000Z")


def test_remote_filepath_protocol_is_not_mangled():
    """Review-pass P12: PurePosixPath('proto://b/k') mangles '//' to '/'
    ('proto:/b/k'). The outer filepath must strip the fsspec protocol first (via
    kedro's get_protocol_and_path), so a remote path is never handed to the base
    in a corrupted 'proto:/...' form. Uses the built-in ``memory://`` protocol so
    construction needs no extra fsspec backend (s3fs/gcsfs) — construction only."""
    from kedro.io.core import get_protocol_and_path

    fp = "memory://my-bucket/data/x/x.parquet"
    ds = IncrementalParquetDataset(filepath=fp)
    _protocol, expected_path = get_protocol_and_path(fp)
    # the outer base stored the protocol-less path (no mangled 'memory:/' prefix)
    assert "memory:" not in str(ds._filepath)
    assert str(ds._filepath) == expected_path
