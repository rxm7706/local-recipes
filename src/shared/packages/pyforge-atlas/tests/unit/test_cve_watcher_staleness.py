"""Story 37.13 (spec-pyforge-atlas CAP-69, CAP-64): the cve-watcher never presents an earlier run's diff as current.

A run whose vulnerability database build fails rolls up nothing, so the snapshot store appends nothing and the diff
equals the run before (DW-atlas-37-12-3). The store now leaves its AD-13 marker on such a save, and with
``pyforge.atlas.board_projections`` on the board is stamped from its latest snapshot (AC3-AC6). Pure; no network.
"""

from __future__ import annotations

import datetime
import json
import os
import types
from pathlib import Path

import pandas as pd
import pytest
from kedro.io import DataCatalog, MemoryDataset
from kedro.runner import SequentialRunner
from kedro_datasets.pandas import ParquetDataset

from pyforge.atlas import provenance
from pyforge.atlas.dashboard import app, data
from pyforge.atlas.datasets import SnapshotHistoryDataset
from pyforge.atlas.datasets.catalog_index import entry_stats
from pyforge.atlas.datasets.snapshot_history import staleness_path
from pyforge.atlas.pipelines.vulnerability import create_pipeline, nodes

DAY = 86_400
T0 = 1_700_000_000
STAMP = "2026-10-24T00:00:00Z"
EMPTY_REASON = "no snapshot appended: the frame saved was empty"


def _iso(epoch: float) -> str:
    return datetime.datetime.fromtimestamp(epoch, tz=datetime.UTC).isoformat()


def _rollup(rows: dict[str, int]) -> pd.DataFrame:
    """``{package: vuln_count}`` as a rollup; an empty dict is a run whose vulnerability database did not build."""
    return pd.DataFrame(
        {
            "package_name": pd.Series(list(rows), dtype="object"),
            "vuln_count": pd.Series(list(rows.values()), dtype="int64"),
            "vuln_critical_high": pd.Series([0] * len(rows), dtype="int64"),
            "vuln_kev_affecting_current": pd.Series([0] * len(rows), dtype="int64"),
        }
    )


def _store(root: Path) -> SnapshotHistoryDataset:
    return SnapshotHistoryDataset(
        filepath=str(root / data.VULN_ROLLUP_SNAPSHOTS_PARQUET),
        key_columns=["snapshot_at", "conda_name"],
        columns=nodes.SNAPSHOT_COLUMNS,
    )


def _write_store(root: Path, stamps: list[float | None]) -> Path:
    path = root / data.VULN_ROLLUP_SNAPSHOTS_PARQUET
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"snapshot_at": stamps, "conda_name": ["a"] * len(stamps)}).to_parquet(path, index=False)
    return path


def _write_diff(root: Path, mtime: float) -> Path:
    path = root / data.DERIVED_VULN_HISTORY_PARQUET
    path.parent.mkdir(parents=True, exist_ok=True)
    nodes.diff_vulnerability_snapshots(pd.DataFrame(), 7).to_parquet(path, index=False)
    os.utime(path, (mtime, mtime))
    return path


def _mark(path: Path, payload: object) -> None:
    staleness_path(path).write_text(json.dumps(payload), encoding="utf-8")


# -- AC3: the store's own stamp ---------------------------------------------------------------------------------------


def test_the_store_is_stamped_with_its_latest_snapshot(tmp_path):
    path = _write_store(tmp_path, [T0, T0 + 9 * DAY, T0 + 3 * DAY])
    os.utime(path, (T0 + 30 * DAY, T0 + 30 * DAY))  # the file's mtime is not the data's build time
    found = provenance.resolve_for_snapshot_history(path)
    assert found == provenance.ProvenanceInfo(kind="snapshot-at", build_stamp=_iso(T0 + 9 * DAY))


def test_an_absent_store_is_unavailable(tmp_path):
    found = provenance.resolve_for_snapshot_history(tmp_path / "s.parquet")
    assert found.kind == "unavailable" and found.build_stamp is None
    assert found.reason == f"backing file not found: {tmp_path / 's.parquet'}"


def test_an_absent_store_with_its_marker_says_both(tmp_path):
    store = _store(tmp_path)
    store.save(_rollup({}))  # a fresh root whose first run rolled up nothing
    found = provenance.resolve_for_snapshot_history(tmp_path / data.VULN_ROLLUP_SNAPSHOTS_PARQUET)
    assert found.kind == "unavailable"
    assert found.reason.startswith("backing file not found: ")
    assert f"; stale: {EMPTY_REASON} (marked " in found.reason


@pytest.mark.parametrize("payload", [b"not parquet", b""])
def test_an_unreadable_store_is_unavailable(tmp_path, payload):
    path = tmp_path / "s.parquet"
    path.write_bytes(payload)
    found = provenance.resolve_for_snapshot_history(path)
    assert found.kind == "unavailable" and found.reason.startswith(f"snapshot store unreadable: {path} (")


def test_a_store_without_the_column_is_unavailable(tmp_path):
    path = tmp_path / "s.parquet"
    pd.DataFrame({"conda_name": ["a"]}).to_parquet(path, index=False)
    found = provenance.resolve_for_snapshot_history(path)
    assert found.kind == "unavailable" and found.reason == f"no 'snapshot_at' column in {path}"


def test_a_store_with_no_snapshot_time_is_unavailable(tmp_path):
    path = _write_store(tmp_path, [None])
    found = provenance.resolve_for_snapshot_history(path)
    assert found.kind == "unavailable" and found.reason == f"no 'snapshot_at' recorded in {path}"


def test_a_snapshot_time_out_of_range_is_unavailable(tmp_path):
    path = _write_store(tmp_path, [1e20])
    found = provenance.resolve_for_snapshot_history(path)
    assert found.kind == "unavailable" and found.reason.startswith("latest 'snapshot_at' out of convertible range")


def test_a_store_marked_stale_says_why_and_when(tmp_path):
    path = _write_store(tmp_path, [T0])
    _mark(path, {"stale": True, "reason": "no snapshot appended: the store could not be read", "marked_at": T0 + DAY})
    found = provenance.resolve_for_snapshot_history(path)
    assert found.kind == "snapshot-at" and found.build_stamp == _iso(T0)
    assert found.reason == f"stale: no snapshot appended: the store could not be read (marked {_iso(T0 + DAY)})"


def test_a_marker_that_says_fresh_adds_nothing(tmp_path):
    path = _write_store(tmp_path, [T0])
    _mark(path, {"stale": False, "reason": "", "marked_at": T0})
    assert provenance.resolve_for_snapshot_history(path).reason is None


@pytest.mark.parametrize("marked_at", [0, 1e20, "never"])
def test_a_marker_time_that_cannot_be_read_is_left_out(tmp_path, marked_at):
    path = _write_store(tmp_path, [T0])
    _mark(path, {"stale": True, "reason": "r", "marked_at": marked_at})
    assert provenance.resolve_for_snapshot_history(path).reason == "stale: r"


@pytest.mark.parametrize("payload", [{}, {"stale": True, "reason": None}, {"stale": True, "reason": ""}])
def test_a_marker_with_no_reason_says_so(tmp_path, payload):
    path = _write_store(tmp_path, [T0])
    _mark(path, payload)
    assert provenance.resolve_for_snapshot_history(path).reason == "stale: no reason recorded"


def test_a_marker_that_cannot_be_read_reads_as_stale(tmp_path):
    path = _write_store(tmp_path, [T0])
    staleness_path(path).write_text("{", encoding="utf-8")
    assert provenance.resolve_for_snapshot_history(path).reason == "stale: staleness marker unreadable"


# -- AC4: the cve-watcher's stamp -------------------------------------------------------------------------------------


def test_an_absent_diff_wins(tmp_path):
    _write_store(tmp_path, [T0])
    diff = tmp_path / data.DERIVED_VULN_HISTORY_PARQUET
    found = app._resolve_cve_watcher_provenance(diff, tmp_path / data.VULN_ROLLUP_SNAPSHOTS_PARQUET)
    assert found.kind == "unavailable" and found.reason == f"backing file not found: {diff}"


def test_with_neither_file_the_diff_is_named(tmp_path):
    diff = tmp_path / data.DERIVED_VULN_HISTORY_PARQUET
    found = app._resolve_cve_watcher_provenance(diff, tmp_path / data.VULN_ROLLUP_SNAPSHOTS_PARQUET)
    assert found.kind == "unavailable" and found.reason == f"backing file not found: {diff}"


def test_an_absent_store_comes_next(tmp_path):
    diff = _write_diff(tmp_path, T0)
    store = tmp_path / data.VULN_ROLLUP_SNAPSHOTS_PARQUET
    found = app._resolve_cve_watcher_provenance(diff, store)
    assert found.kind == "unavailable" and found.reason == f"backing file not found: {store}"


def test_a_diff_written_after_its_snapshot_is_stamped_with_the_snapshot(tmp_path):
    store = _write_store(tmp_path, [T0, T0 + 7 * DAY])
    diff = _write_diff(tmp_path, T0 + 7 * DAY + 60)
    found = app._resolve_cve_watcher_provenance(diff, store)
    assert found == provenance.ProvenanceInfo(kind="snapshot-at", build_stamp=_iso(T0 + 7 * DAY))


def test_a_stale_store_stamps_the_diff_with_its_snapshot_and_reason(tmp_path):
    store = _write_store(tmp_path, [T0, T0 + 7 * DAY])
    _mark(store, {"stale": True, "reason": EMPTY_REASON, "marked_at": T0 + 14 * DAY})
    diff = _write_diff(tmp_path, T0 + 14 * DAY)  # rewritten by the run that rolled up nothing
    found = app._resolve_cve_watcher_provenance(diff, store)
    assert found.kind == "snapshot-at" and found.build_stamp == _iso(T0 + 7 * DAY)
    assert found.reason == f"stale: {EMPTY_REASON} (marked {_iso(T0 + 14 * DAY)})"


def test_a_diff_older_than_the_latest_snapshot_keeps_its_own_stamp(tmp_path):
    """The diff did not run after the latest snapshot: the board's data is the older diff file."""
    store = _write_store(tmp_path, [T0, T0 + 7 * DAY])
    _mark(store, {"stale": True, "reason": "r", "marked_at": 0})
    diff = _write_diff(tmp_path, T0 + DAY)
    found = app._resolve_cve_watcher_provenance(diff, store)
    assert found == provenance.ProvenanceInfo(kind="file-mtime", build_stamp=_iso(T0 + DAY), reason="stale: r")


def test_the_stamp_line_carries_the_reason():
    stale = provenance.ProvenanceInfo(kind="snapshot-at", build_stamp="2026-10-17T05:17:31+00:00", reason="stale: r")
    assert (
        app._provenance_line(stale)
        == "**Data build stamp (AD-17):** `2026-10-17T05:17:31+00:00` (snapshot-at) — stale: r"
    )
    fresh = provenance.ProvenanceInfo(kind="file-mtime", build_stamp="2026-10-17T05:17:31+00:00")
    assert app._provenance_line(fresh) == "**Data build stamp (AD-17):** `2026-10-17T05:17:31+00:00` (file-mtime)"


def _card(dashboard, page_id: str = "cve-watcher") -> str:
    page = next(p for p in dashboard.pages if p.id == page_id)
    return next(c.text for c in page.components if hasattr(c, "text"))


def test_with_the_flag_on_a_stale_store_reads_stale_on_the_board(tmp_path):
    store = _write_store(tmp_path, [T0, T0 + 7 * DAY])
    _mark(store, {"stale": True, "reason": EMPTY_REASON, "marked_at": T0 + 14 * DAY})
    _write_diff(tmp_path, T0 + 14 * DAY)
    text = _card(app.build_dashboard(build_stamp=STAMP, data_root=tmp_path, now=T0, board_projections=True))
    assert (
        f"**Data build stamp (AD-17):** `{_iso(T0 + 7 * DAY)}` (snapshot-at) — stale: {EMPTY_REASON} "
        f"(marked {_iso(T0 + 14 * DAY)})"
    ) in text
    assert f"**{app.NOTE_LABEL}:**" in text  # the data is there, dated and marked


def test_with_the_flag_on_no_store_reads_as_a_data_gap(tmp_path):
    _write_diff(tmp_path, T0)
    text = _card(app.build_dashboard(build_stamp=STAMP, data_root=tmp_path, now=T0, board_projections=True))
    store = tmp_path / data.VULN_ROLLUP_SNAPSHOTS_PARQUET
    assert f"**Data build stamp (AD-17):** unavailable — backing file not found: {store}" in text
    assert f"**{app.GAP_LABEL}:**" in text


def test_with_the_flag_off_the_board_is_stamped_as_before(tmp_path):
    store = _write_store(tmp_path, [T0])
    _mark(store, {"stale": True, "reason": EMPTY_REASON, "marked_at": T0})
    legacy = tmp_path / data.VULN_HISTORY_PARQUET
    legacy.parent.mkdir(parents=True)
    pd.DataFrame({"conda_name": ["a"]}).to_parquet(legacy, index=False)
    os.utime(legacy, (T0 + DAY, T0 + DAY))
    text = _card(app.build_dashboard(build_stamp=STAMP, data_root=tmp_path, now=T0, board_projections=False))
    assert f"**Data build stamp (AD-17):** `{_iso(T0 + DAY)}` (file-mtime)\n" in text + "\n"
    assert "— stale:" not in text


# -- AC5: the runs that DW-atlas-37-12-3 describes, through Kedro's runner --------------------------------------------


def _run(root: Path, rollup: pd.DataFrame, stamp: int, monkeypatch) -> pd.DataFrame:
    monkeypatch.setattr(nodes, "time", types.SimpleNamespace(time=lambda: stamp))
    out = root / data.DERIVED_VULN_HISTORY_PARQUET
    out.parent.mkdir(parents=True, exist_ok=True)
    catalog = DataCatalog(
        {
            "vulnerability_package_rollup": MemoryDataset(rollup),
            "vulnerability_rollup_snapshots": _store(root),
            "params:cve_watcher.since_days": MemoryDataset(7),
            "derived_vuln_history": ParquetDataset(filepath=str(out)),
        }
    )
    pipe = create_pipeline().only_nodes("snapshot_vulnerability_rollup", "diff_vulnerability_snapshots")
    SequentialRunner().run(pipe, catalog)
    return pd.read_parquet(out)


def test_a_run_that_rolls_up_nothing_never_reads_as_current(tmp_path, monkeypatch):
    store = tmp_path / data.VULN_ROLLUP_SNAPSHOTS_PARQUET
    _run(tmp_path, _rollup({"a": 1, "b": 2}), T0, monkeypatch)
    second = _run(tmp_path, _rollup({"a": 4, "b": 2}), T0 + 8 * DAY, monkeypatch)
    assert not second.empty and not staleness_path(store).exists()
    fresh = _card(app.build_dashboard(build_stamp=STAMP, data_root=tmp_path, now=T0, board_projections=True))
    assert f"`{_iso(T0 + 8 * DAY)}` (snapshot-at)\n" in fresh + "\n"

    stored = store.read_bytes()
    third = _run(tmp_path, _rollup({}), T0 + 15 * DAY, monkeypatch)  # the vulnerability database did not build
    pd.testing.assert_frame_equal(third, second)  # the same diff as the run before ...
    assert store.read_bytes() == stored
    stale = _card(app.build_dashboard(build_stamp=STAMP, data_root=tmp_path, now=T0, board_projections=True))
    # ... dated by the second run's snapshot and marked stale, not stamped with the diff file's fresh mtime
    assert f"`{_iso(T0 + 8 * DAY)}` (snapshot-at) — stale: {EMPTY_REASON} (marked " in stale

    fourth = _run(tmp_path, _rollup({"a": 4, "b": 5}), T0 + 22 * DAY, monkeypatch)
    assert set(fourth["latest_snapshot_at"]) == {T0 + 22 * DAY}
    assert not staleness_path(store).exists()
    current = _card(app.build_dashboard(build_stamp=STAMP, data_root=tmp_path, now=T0, board_projections=True))
    assert f"`{_iso(T0 + 22 * DAY)}` (snapshot-at)\n" in current + "\n"
    assert "— stale:" not in current


# -- AC6: the bootstrap-index-health reads the store's marker ---------------------------------------------------------


def test_the_index_health_reads_the_store_marker_as_stale(tmp_path):
    store = _store(tmp_path)
    store.save(_rollup({"a": 1}).pipe(nodes.snapshot_vulnerability_rollup, now=T0))
    assert entry_stats(tmp_path / data.VULN_ROLLUP_SNAPSHOTS_PARQUET)["stale"] is False
    store.save(nodes.snapshot_vulnerability_rollup(_rollup({})))
    stats = entry_stats(tmp_path / data.VULN_ROLLUP_SNAPSHOTS_PARQUET)
    assert stats["stale"] is True and stats["stale_reason"] == EMPTY_REASON
    assert stats["row_count"] == 1
