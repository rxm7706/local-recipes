"""``progress.py``'s local JSON storage (Story 8.1, scaled-down Epic 8).

Every case uses an explicit ``tmp_path``-derived ``progress_path`` --
``progress.py`` never assumes a cwd, mirroring ``state.py``'s own
convention (and its test suite's shape)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

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


def test_default_progress_path_is_dot_herald_progress_json():
    assert DEFAULT_PROGRESS_PATH == Path(".herald/progress.json")


def test_read_of_a_missing_file_returns_empty_list(tmp_path: Path):
    assert read_all(tmp_path / "does-not-exist" / "progress.json") == []


def test_upsert_creates_a_new_record(tmp_path: Path):
    progress_path = tmp_path / "progress.json"
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
    progress_path = tmp_path / "progress.json"
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
    progress_path = tmp_path / "progress.json"
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
    progress_path = tmp_path / "progress.json"
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
    progress_path = tmp_path / "progress.json"
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
    progress_path = tmp_path / "progress.json"
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
    assert latest_for_station(tmp_path / "progress.json", "warden") is None


def test_list_records_filters_by_station(tmp_path: Path):
    progress_path = tmp_path / "progress.json"
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
    progress_path = tmp_path / "progress.json"
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
    progress_path = tmp_path / "progress.json"
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


def test_read_of_invalid_json_raises_herald_error(tmp_path: Path):
    progress_path = tmp_path / "progress.json"
    progress_path.write_text("{not valid json")
    with pytest.raises(HeraldError, match=str(progress_path)):
        read_all(progress_path)


def test_read_of_a_non_array_top_level_document_raises_herald_error(tmp_path: Path):
    progress_path = tmp_path / "progress.json"
    progress_path.write_text('{"a": 1}')
    with pytest.raises(HeraldError, match=str(progress_path)):
        read_all(progress_path)


def test_read_of_a_record_missing_a_field_raises_herald_error(tmp_path: Path):
    progress_path = tmp_path / "progress.json"
    progress_path.write_text('[{"id": "x", "station": "warden", "date": "2026-08-08"}]')
    with pytest.raises(HeraldError, match="missing field"):
        read_all(progress_path)


def test_read_of_a_record_with_an_unknown_field_raises_herald_error(tmp_path: Path):
    progress_path = tmp_path / "progress.json"
    record = Progress(
        id="x",
        station="warden",
        date="2026-08-08",
        shipped_capabilities=[],
        compute_hours=0,
        token_spend=0,
        wall_clock_hours=0,
        unblock_narrative="",
        created_at="t",
        updated_at="t",
    )
    write_all(progress_path, [record])
    document = progress_path.read_text()
    corrupted = document.replace('"id": "x"', '"id": "x", "bogus": 1')
    progress_path.write_text(corrupted)
    with pytest.raises(HeraldError, match="unknown field"):
        read_all(progress_path)


def test_write_all_creates_the_parent_directory(tmp_path: Path):
    progress_path = tmp_path / "nested" / "dir" / "progress.json"
    write_all(progress_path, [])
    assert progress_path.exists()


def test_write_all_round_trips_field_for_field(tmp_path: Path):
    progress_path = tmp_path / "progress.json"
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
