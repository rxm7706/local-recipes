"""``progress.py``'s SQLite-backed storage (Story 8.1, scaled-down Epic 8;
Story 13.3 moved the backing store to ``db.py``'s shared
``.herald/herald.db``).

Every case uses an explicit ``tmp_path``-derived ``progress_path`` --
``progress.py`` never assumes a cwd, mirroring ``state.py``'s own
convention (and its test suite's shape). Paths are named ``herald.db``,
not ``progress.json`` -- Story 13.3's one-time legacy import looks for
sibling files literally named ``progress.json``/``claims.json``/
``notices-index.json`` next to the database file, so a test path that
happened to share one of those names would collide with the DB file
itself; production code never hits this because ``DEFAULT_PROGRESS_PATH``
is ``.herald/herald.db``, never ``progress.json``."""

from __future__ import annotations

import sqlite3
import threading
import time
from datetime import date
from pathlib import Path

import pytest

from pyforge.herald import db
from pyforge.herald import progress as progress_module
from pyforge.herald.errors import HeraldError
from pyforge.herald.progress import (
    DEFAULT_PROGRESS_PATH,
    Progress,
    latest_for_station,
    list_records,
    read_all,
    upsert,
    write_all,
)


def test_default_progress_path_is_the_shared_herald_db():
    assert DEFAULT_PROGRESS_PATH == db.DEFAULT_DB_PATH == Path(".herald/herald.db")


def test_read_of_a_missing_file_returns_empty_list(tmp_path: Path):
    assert read_all(tmp_path / "does-not-exist" / "herald.db") == []


def test_upsert_creates_a_new_record(tmp_path: Path):
    progress_path = tmp_path / "herald.db"
    record = upsert(
        progress_path,
        station="warden",
        date="2026-08-08",
        shipped_capabilities=["hygiene gate"],
        compute_hours=1.5,
        token_spend=1000,
        wall_clock_hours=2.0,
        unblock_narrative="none",
    )
    assert record.station == "warden"
    assert record.date == "2026-08-08"
    assert record.created_at == record.updated_at
    assert read_all(progress_path) == [record]


@pytest.mark.parametrize(
    ("field", "kwargs"),
    [
        ("compute_hours", {"compute_hours": -5.0}),
        ("token_spend", {"token_spend": -1000}),
        ("wall_clock_hours", {"wall_clock_hours": -3.0}),
    ],
)
def test_upsert_refuses_a_negative_cost_field(tmp_path: Path, field, kwargs):
    """Regression: no field-level validation meant a negative cost value
    (a typo'd flag) was silently stored and rendered as-is (e.g. "-5h
    compute") with no indication anything was wrong."""
    progress_path = tmp_path / "herald.db"
    base = {
        "station": "warden",
        "date": "2026-08-08",
        "shipped_capabilities": [],
        "compute_hours": 1.0,
        "token_spend": 100,
        "wall_clock_hours": 1.0,
        "unblock_narrative": "",
    }
    base.update(kwargs)
    with pytest.raises(HeraldError, match=f"{field} must not be negative"):
        upsert(progress_path, **base)
    assert read_all(progress_path) == []


def test_upsert_replaces_the_same_station_date_in_place(tmp_path: Path):
    progress_path = tmp_path / "herald.db"
    first = upsert(
        progress_path,
        station="warden",
        date="2026-08-08",
        shipped_capabilities=["a"],
        compute_hours=1.0,
        token_spend=100,
        wall_clock_hours=1.0,
        unblock_narrative="",
    )
    second = upsert(
        progress_path,
        station="warden",
        date="2026-08-08",
        shipped_capabilities=["a", "b"],
        compute_hours=2.0,
        token_spend=200,
        wall_clock_hours=2.0,
        unblock_narrative="unblocked now",
    )
    records = read_all(progress_path)
    assert len(records) == 1
    assert second.id == first.id
    assert second.created_at == first.created_at
    assert second.shipped_capabilities == ["a", "b"]
    assert records[0] == second


def test_upsert_a_different_date_appends_rather_than_replaces(tmp_path: Path):
    progress_path = tmp_path / "herald.db"
    upsert(
        progress_path,
        station="warden",
        date="2026-08-07",
        shipped_capabilities=[],
        compute_hours=0,
        token_spend=0,
        wall_clock_hours=0,
        unblock_narrative="",
    )
    upsert(
        progress_path,
        station="warden",
        date="2026-08-08",
        shipped_capabilities=[],
        compute_hours=0,
        token_spend=0,
        wall_clock_hours=0,
        unblock_narrative="",
    )
    assert len(read_all(progress_path)) == 2


def test_upsert_a_different_station_same_date_appends(tmp_path: Path):
    progress_path = tmp_path / "herald.db"
    upsert(
        progress_path,
        station="warden",
        date="2026-08-08",
        shipped_capabilities=[],
        compute_hours=0,
        token_spend=0,
        wall_clock_hours=0,
        unblock_narrative="",
    )
    upsert(
        progress_path,
        station="atlas",
        date="2026-08-08",
        shipped_capabilities=[],
        compute_hours=0,
        token_spend=0,
        wall_clock_hours=0,
        unblock_narrative="",
    )
    assert len(read_all(progress_path)) == 2


def test_latest_for_station_returns_the_most_recent_date(tmp_path: Path):
    progress_path = tmp_path / "herald.db"
    for day in ("2026-08-01", "2026-08-08", "2026-08-05"):
        upsert(
            progress_path,
            station="warden",
            date=day,
            shipped_capabilities=[],
            compute_hours=0,
            token_spend=0,
            wall_clock_hours=0,
            unblock_narrative="",
        )
    latest = latest_for_station(progress_path, "warden")
    assert latest is not None
    assert latest.date == "2026-08-08"


def test_latest_for_station_with_no_records_returns_none(tmp_path: Path):
    assert latest_for_station(tmp_path / "herald.db", "warden") is None


def test_list_records_filters_by_station(tmp_path: Path):
    progress_path = tmp_path / "herald.db"
    upsert(
        progress_path,
        station="warden",
        date="2026-08-08",
        shipped_capabilities=[],
        compute_hours=0,
        token_spend=0,
        wall_clock_hours=0,
        unblock_narrative="",
    )
    upsert(
        progress_path,
        station="atlas",
        date="2026-08-08",
        shipped_capabilities=[],
        compute_hours=0,
        token_spend=0,
        wall_clock_hours=0,
        unblock_narrative="",
    )
    records = list_records(progress_path, station="warden")
    assert len(records) == 1
    assert records[0].station == "warden"


def test_list_records_filters_by_date_range(tmp_path: Path):
    progress_path = tmp_path / "herald.db"
    for day in ("2026-08-01", "2026-08-08", "2026-08-15"):
        upsert(
            progress_path,
            station="warden",
            date=day,
            shipped_capabilities=[],
            compute_hours=0,
            token_spend=0,
            wall_clock_hours=0,
            unblock_narrative="",
        )
    records = list_records(
        progress_path,
        date_range=(date(2026, 8, 5), date(2026, 8, 10)),
    )
    assert [r.date for r in records] == ["2026-08-08"]


def test_list_records_sorted_newest_first(tmp_path: Path):
    progress_path = tmp_path / "herald.db"
    for day in ("2026-08-01", "2026-08-08", "2026-08-05"):
        upsert(
            progress_path,
            station="warden",
            date=day,
            shipped_capabilities=[],
            compute_hours=0,
            token_spend=0,
            wall_clock_hours=0,
            unblock_narrative="",
        )
    records = list_records(progress_path)
    assert [r.date for r in records] == ["2026-08-08", "2026-08-05", "2026-08-01"]


def test_read_of_a_corrupt_database_file_raises_herald_error(tmp_path: Path):
    progress_path = tmp_path / "herald.db"
    progress_path.write_bytes(b"not a sqlite database")
    with pytest.raises(HeraldError, match=str(progress_path)):
        read_all(progress_path)


def test_read_of_a_record_with_malformed_shipped_capabilities_json_raises(
    tmp_path: Path,
):
    """The one corruption still reachable once the store is a
    schema-enforced database: every other field is a plain, typed SQL
    column, but ``shipped_capabilities`` is a JSON TEXT column that a raw
    write outside this module's own API could still leave malformed."""
    progress_path = tmp_path / "herald.db"
    record = upsert(
        progress_path,
        station="warden",
        date="2026-08-08",
        shipped_capabilities=["a"],
        compute_hours=0,
        token_spend=0,
        wall_clock_hours=0,
        unblock_narrative="",
    )
    raw = sqlite3.connect(progress_path)
    raw.execute(
        "UPDATE progress SET shipped_capabilities = ? WHERE id = ?",
        ("{not valid json", record.id),
    )
    raw.commit()
    raw.close()
    with pytest.raises(HeraldError, match="shipped_capabilities"):
        read_all(progress_path)


def test_write_all_creates_the_parent_directory(tmp_path: Path):
    progress_path = tmp_path / "nested" / "dir" / "herald.db"
    write_all(progress_path, [])
    assert progress_path.exists()


def test_write_all_round_trips_field_for_field(tmp_path: Path):
    progress_path = tmp_path / "herald.db"
    record = Progress(
        id="x",
        station="warden",
        date="2026-08-08",
        shipped_capabilities=["a", "b"],
        compute_hours=1.5,
        token_spend=42,
        wall_clock_hours=3.0,
        unblock_narrative="narrative",
        created_at="t1",
        updated_at="t2",
    )
    write_all(progress_path, [record])
    assert read_all(progress_path) == [record]


def test_two_concurrent_upserts_for_different_stations_both_land(tmp_path: Path, monkeypatch):
    """Story 13.1/13.3 regression: two ``upsert`` calls for different
    ``(station, date)`` keys racing the same database must both survive --
    forced, deterministic interleaving (not a timing-dependent sleep
    race). A monkeypatched delay on ``now_iso`` (called from inside
    ``upsert``'s own ``db.transaction``, right after its read and before
    its write) gives the other writer's whole ``BEGIN IMMEDIATE`` attempt
    room to genuinely block during the pause -- a second writer cannot
    even begin its own transaction until the first has committed.

    Scope, stated honestly: this asserts the OUTCOME (both rows land), not
    the mechanism. Story 13.3 rewrote ``upsert`` to touch only its own
    ``(station, date)`` row (a targeted SELECT then UPDATE/INSERT) instead
    of rewriting the whole table, so two writers on DIFFERENT keys cannot
    clobber each other whatever the locking does -- verified: this test
    still passes against a ``db.transaction`` stripped of its ``BEGIN
    IMMEDIATE``. ``test_write_all_is_not_silently_discarded_by_a_concurrent_upsert``
    is the one that genuinely fails without the transaction, and is what
    holds DW-1-4-2's guarantee for this module."""
    progress_path = tmp_path / "herald.db"
    original_now_iso = progress_module.now_iso

    def delayed_now_iso():
        timestamp = original_now_iso()
        time.sleep(0.2)
        return timestamp

    monkeypatch.setattr(progress_module, "now_iso", delayed_now_iso)

    barrier = threading.Barrier(2)

    def writer(station: str) -> None:
        barrier.wait(timeout=5)
        upsert(
            progress_path,
            station=station,
            date="2026-08-08",
            shipped_capabilities=[],
            compute_hours=0,
            token_spend=0,
            wall_clock_hours=0,
            unblock_narrative="",
        )

    t1 = threading.Thread(target=writer, args=("warden",))
    t2 = threading.Thread(target=writer, args=("atlas",))
    t1.start()
    t2.start()
    # Bounded joins plus an explicit liveness assertion: without it a genuine
    # deadlock regression fails below with a confusing content mismatch that
    # reads as a lost update rather than a hang, and leaves two abandoned
    # threads still holding the transaction open for the rest of the session.
    t1.join(timeout=5)
    t2.join(timeout=5)
    assert not t1.is_alive() and not t2.is_alive(), "a writer deadlocked"

    stations = {r.station for r in read_all(progress_path)}
    assert stations == {"warden", "atlas"}


def test_write_all_is_not_silently_discarded_by_a_concurrent_upsert(tmp_path: Path, monkeypatch):
    """``write_all`` is public, so it must open the same ``db.transaction``
    ``upsert`` does. A writer that skipped it would land in the middle of
    ``upsert``'s read-modify-write span and be clobbered by ``upsert``'s
    own commit -- computed from a read taken before it -- reopening
    exactly the lost-update race this module's Concurrency note claims is
    closed.

    Deterministic ordering, no timing race: a monkeypatched delay on
    ``now_iso`` signals the instant ``upsert`` has entered its
    transaction (so it is provably holding the write lock) and then holds
    there long enough for ``write_all`` to attempt its own transaction
    during the pause -- which must genuinely block until ``upsert``
    commits, guaranteeing ``write_all`` is the LAST writer and its
    whole-table replace is what survives."""
    progress_path = tmp_path / "herald.db"
    original_now_iso = progress_module.now_iso
    upsert_holds_transaction = threading.Event()

    def delayed_now_iso():
        timestamp = original_now_iso()
        upsert_holds_transaction.set()
        time.sleep(0.2)
        return timestamp

    monkeypatch.setattr(progress_module, "now_iso", delayed_now_iso)

    def upserter() -> None:
        upsert(
            progress_path,
            station="warden",
            date="2026-08-08",
            shipped_capabilities=[],
            compute_hours=0,
            token_spend=0,
            wall_clock_hours=0,
            unblock_narrative="",
        )

    def wholesale_writer() -> None:
        assert upsert_holds_transaction.wait(timeout=5), "upsert never reached its transaction"
        write_all(
            progress_path,
            [
                Progress(
                    id="fixed-id",
                    station="atlas",
                    date="2026-08-08",
                    created_at="2026-08-08T00:00:00+00:00",
                    updated_at="2026-08-08T00:00:00+00:00",
                )
            ],
        )

    t1 = threading.Thread(target=upserter)
    t2 = threading.Thread(target=wholesale_writer)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)
    assert not t1.is_alive() and not t2.is_alive(), "a writer never finished"

    stations = [r.station for r in read_all(progress_path)]
    assert stations == ["atlas"], (
        f"write_all's whole-table write was silently discarded by a concurrent upsert: {stations}"
    )
