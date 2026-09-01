"""Story 28.16 (CAP-3): wave id + multi-story in-flight status visibility."""

from __future__ import annotations

from pathlib import Path

from pyforge.marshal.cli import status as status_cli
from pyforge.marshal.core import status


def test_latest_dispatch_wave_id_returns_most_recent(tmp_path: Path) -> None:
    slug = "pyforge-marshal"
    waves = (
        tmp_path
        / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs/waves"
    )
    (waves / "wave-aaa").mkdir(parents=True)
    (waves / "wave-bbb").mkdir(parents=True)

    assert status_cli.latest_dispatch_wave_id(tmp_path, slug) == "wave-bbb"


def test_fleet_row_surfaces_wave_id_and_in_flight_stories() -> None:
    facts = status.FleetHomeFacts(
        slug="pyforge-marshal",
        branch="loop/pyforge-marshal",
        has_run=False,
        dispatch_story="28.10-a",
        dispatch_engine_alive=True,
        dispatch_wave_id="wave-20260901-abc",
        dispatch_in_flight_stories=("28.10-a", "28.11-b"),
    )
    row, finding = status.build_fleet_row(facts)
    assert finding is None
    assert row["dispatch_wave_id"] == "wave-20260901-abc"
    assert row["dispatch_in_flight_stories"] == ["28.10-a", "28.11-b"]
