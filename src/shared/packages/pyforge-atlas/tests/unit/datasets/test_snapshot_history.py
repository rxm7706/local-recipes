"""Story 37.5 — the append-only snapshot store (AC1). Story 37.13 — its AD-13 marker (AC1, AC2)."""

from __future__ import annotations

import json

import pandas as pd
import pytest
from kedro.io.core import DatasetError

from pyforge.atlas.datasets import SnapshotHistoryDataset
from pyforge.atlas.datasets.snapshot_history import read_staleness, staleness_path

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


# -- Story 37.13: a save that appends no snapshot leaves the AD-13 marker ---------------------------------------------

ROW = {"snapshot_at": [1], "conda_name": ["a"], "vuln_total": [2]}


def _marker(tmp_path) -> dict:
    return json.loads((tmp_path / "s" / "store.parquet.staleness.json").read_text(encoding="utf-8"))


def test_the_marker_sits_beside_the_store(tmp_path):
    assert staleness_path(tmp_path / "s" / "store.parquet") == tmp_path / "s" / "store.parquet.staleness.json"


def test_an_empty_save_marks_the_store_stale_and_keeps_its_bytes(tmp_path):
    ds = _store(tmp_path)
    ds.save(pd.DataFrame(ROW))
    before = (tmp_path / "s" / "store.parquet").read_bytes()
    ds.save(pd.DataFrame(columns=COLUMNS))
    assert (tmp_path / "s" / "store.parquet").read_bytes() == before
    marker = _marker(tmp_path)
    assert marker["stale"] is True
    assert marker["reason"] == "no snapshot appended: the frame saved was empty"
    assert marker["last_good_exists"] is True
    assert marker["marked_at"] > 0
    assert ds.staleness() is not None and ds.staleness().stale


def test_an_empty_save_on_a_fresh_root_marks_it_with_no_store(tmp_path):
    _store(tmp_path).save(pd.DataFrame(columns=COLUMNS))
    assert not (tmp_path / "s" / "store.parquet").exists()
    assert _marker(tmp_path)["last_good_exists"] is False


def test_a_save_over_an_unreadable_store_marks_it_stale(tmp_path):
    path = tmp_path / "s" / "store.parquet"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"not parquet")
    _store(tmp_path).save(pd.DataFrame(ROW))
    assert path.read_bytes() == b"not parquet"
    assert _marker(tmp_path)["reason"] == "no snapshot appended: the store could not be read"


def test_a_save_that_appends_removes_the_marker(tmp_path):
    ds = _store(tmp_path)
    ds.save(pd.DataFrame(columns=COLUMNS))
    assert staleness_path(tmp_path / "s" / "store.parquet").is_file()
    ds.save(pd.DataFrame(ROW))
    assert not staleness_path(tmp_path / "s" / "store.parquet").exists()
    assert ds.staleness() is None
    assert len(ds.load()) == 1


def test_rows_without_the_keys_leave_the_marker_as_it_was(tmp_path):
    ds = _store(tmp_path)
    ds.save(pd.DataFrame(columns=COLUMNS))
    before = (tmp_path / "s" / "store.parquet.staleness.json").read_bytes()
    with pytest.raises(DatasetError, match="key columns"):
        ds.save(pd.DataFrame({"conda_name": ["a"], "vuln_total": [2]}))
    assert (tmp_path / "s" / "store.parquet.staleness.json").read_bytes() == before


def test_a_marker_that_cannot_be_written_never_fails_the_save(tmp_path, monkeypatch):
    import pyforge.atlas.datasets.snapshot_history as module

    def _refuse(*_args, **_kwargs):
        raise OSError("read-only")

    monkeypatch.setattr(module, "atomic_write_text", _refuse)
    _store(tmp_path).save(pd.DataFrame(columns=COLUMNS))  # no raise
    assert not staleness_path(tmp_path / "s" / "store.parquet").exists()


def test_a_marker_that_cannot_be_removed_never_fails_the_save(tmp_path, monkeypatch):
    ds = _store(tmp_path)
    ds.save(pd.DataFrame(columns=COLUMNS))

    def _refuse(self, *_args, **_kwargs):
        raise OSError("read-only")

    monkeypatch.setattr(type(tmp_path), "unlink", _refuse)
    ds.save(pd.DataFrame(ROW))  # no raise; the rows are appended, the marker stays
    monkeypatch.undo()
    assert len(ds.load()) == 1
    assert staleness_path(tmp_path / "s" / "store.parquet").is_file()


@pytest.mark.parametrize("text", ["not json", "[1, 2]", "", "null"])
def test_a_marker_that_cannot_be_read_reads_as_stale(tmp_path, text):
    store = tmp_path / "s" / "store.parquet"
    store.parent.mkdir(parents=True)
    staleness_path(store).write_text(text, encoding="utf-8")
    marker = read_staleness(store)
    assert marker is not None and marker.stale
    assert marker.reason == "staleness marker unreadable"


def test_no_marker_reads_as_none(tmp_path):
    assert read_staleness(tmp_path / "s" / "store.parquet") is None
