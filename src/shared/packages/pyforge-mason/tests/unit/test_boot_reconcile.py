"""Steward 25.4 — killed Mason boot re-indexes without duplicating rows."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.mason.boot import BootInterrupted, NaiveAppendStore, SqliteIndexStore, insert_always, reconcile_boot


def _three_files(root: Path) -> None:
    (root / "a.bin").write_bytes(b"aaa")
    nested = root / "nested"
    nested.mkdir()
    (nested / "b.bin").write_bytes(b"bb")
    (root / "c.bin").write_bytes(b"c")


def test_interrupted_boot_then_restart_applies_once(tmp_path: Path) -> None:
    rwx = tmp_path / "media"
    rwx.mkdir()
    _three_files(rwx)
    store = SqliteIndexStore()

    with pytest.raises(BootInterrupted):
        reconcile_boot(store, rwx, interrupt_after=1)
    assert store.row_count() == 1

    report = reconcile_boot(store, rwx)
    assert report.scanned == 3
    assert report.row_count == 3
    assert len(set(store.keys())) == 3
    assert store.keys() == ("a.bin", "c.bin", "nested/b.bin")


def test_second_full_boot_does_not_add_rows(tmp_path: Path) -> None:
    rwx = tmp_path / "media"
    rwx.mkdir()
    _three_files(rwx)
    store = SqliteIndexStore()
    first = reconcile_boot(store, rwx)
    second = reconcile_boot(store, rwx)
    assert first.row_count == 3
    assert second.row_count == 3
    assert len(set(store.keys())) == 3


def test_pg_only_missing_rwx_does_not_duplicate() -> None:
    store = SqliteIndexStore()
    store.upsert("already", 4, "pg")
    report = reconcile_boot(store, rwx_root=None)
    assert report.scanned == 0
    assert report.row_count == 1
    assert store.keys() == ("already",)


def test_rwx_files_index_by_relative_path(tmp_path: Path) -> None:
    rwx = tmp_path / "media"
    rwx.mkdir()
    (rwx / "only.bin").write_bytes(b"xy")
    (rwx / "skip_dir").mkdir()
    store = SqliteIndexStore()
    report = reconcile_boot(store, rwx)
    assert report.scanned == 1
    assert report.row_count == 1
    assert store.keys() == ("only.bin",)


def test_naive_insert_duplicates_on_restart(tmp_path: Path) -> None:
    rwx = tmp_path / "media"
    rwx.mkdir()
    _three_files(rwx)
    store = NaiveAppendStore()

    with pytest.raises(BootInterrupted):
        reconcile_boot(store, rwx, interrupt_after=1, apply=insert_always)
    first = store.row_count()
    assert first == 1

    reconcile_boot(store, rwx, apply=insert_always)
    assert store.row_count() == first + 3
    assert len(store.keys()) == 4
