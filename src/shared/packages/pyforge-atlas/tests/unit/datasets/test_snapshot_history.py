"""Story 37.5 — the append-only snapshot store (AC1)."""

from __future__ import annotations

import pandas as pd
import pytest
from kedro.io.core import DatasetError

from pyforge.atlas.datasets import SnapshotHistoryDataset

KEYS = ["snapshot_at", "conda_name"]
COLUMNS = ["snapshot_at", "conda_name", "vuln_total"]


def _store(tmp_path):
    return SnapshotHistoryDataset(filepath=str(tmp_path / "s" / "store.parquet"), key_columns=KEYS, columns=COLUMNS)


def test_absent_store_loads_empty_with_the_declared_columns(tmp_path):
    frame = _store(tmp_path).load()
    assert frame.empty
    assert list(frame.columns) == COLUMNS


def test_a_save_appends_to_the_stored_rows(tmp_path):
    ds = _store(tmp_path)
    ds.save(pd.DataFrame({"snapshot_at": [1, 1], "conda_name": ["a", "b"], "vuln_total": [2, 3]}))
    ds.save(pd.DataFrame({"snapshot_at": [2], "conda_name": ["a"], "vuln_total": [4]}))
    got = ds.load()
    assert list(zip(got["snapshot_at"], got["conda_name"], got["vuln_total"], strict=True)) == [
        (1, "a", 2),
        (1, "b", 3),
        (2, "a", 4),
    ]


def test_a_repeated_key_keeps_the_new_row(tmp_path):
    ds = _store(tmp_path)
    ds.save(pd.DataFrame({"snapshot_at": [1], "conda_name": ["a"], "vuln_total": [2]}))
    ds.save(pd.DataFrame({"snapshot_at": [1], "conda_name": ["a"], "vuln_total": [9]}))
    got = ds.load()
    assert len(got) == 1
    assert got["vuln_total"].iloc[0] == 9


def test_an_empty_save_keeps_the_store(tmp_path):
    ds = _store(tmp_path)
    ds.save(pd.DataFrame({"snapshot_at": [1], "conda_name": ["a"], "vuln_total": [2]}))
    path = tmp_path / "s" / "store.parquet"
    before = path.read_bytes()
    ds.save(pd.DataFrame(columns=COLUMNS))
    assert path.read_bytes() == before


def test_an_unreadable_store_is_never_overwritten(tmp_path):
    path = tmp_path / "s" / "store.parquet"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"not parquet")
    ds = _store(tmp_path)
    assert ds.load().empty
    ds.save(pd.DataFrame({"snapshot_at": [1], "conda_name": ["a"], "vuln_total": [2]}))
    assert path.read_bytes() == b"not parquet"


def test_rows_without_the_keys_are_refused(tmp_path):
    with pytest.raises(DatasetError, match="key columns"):
        _store(tmp_path).save(pd.DataFrame({"conda_name": ["a"], "vuln_total": [2]}))


def test_a_store_needs_a_key():
    with pytest.raises(ValueError, match="at least one key"):
        SnapshotHistoryDataset(filepath="x.parquet", key_columns=[])
