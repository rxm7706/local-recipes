"""Story 28.16 (CAP-3): wave id + multi-story in-flight status visibility."""

from __future__ import annotations

from pathlib import Path

from pyforge.marshal.cli import dispatch as dispatch_cli
from pyforge.marshal.cli import status as status_cli
from pyforge.marshal.core import status


def test_latest_dispatch_wave_id_returns_most_recent(tmp_path: Path) -> None:
    slug = "pyforge-marshal"
    waves = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs/waves"
    (waves / "wave-aaa").mkdir(parents=True)
    (waves / "wave-bbb").mkdir(parents=True)

    assert status_cli.latest_dispatch_wave_id(tmp_path, slug) == "wave-bbb"


def test_latest_dispatch_run_dir_skips_waves_container(tmp_path: Path) -> None:
    """``waves/`` must not win lexicographic 'latest' over a live story run.

    Regression for the 2026-09-18 marshal 46.4 blind spot: with
    ``max_parallel`` waves present, ``latest_dispatch_run_dir`` returned the
    ``waves`` directory (no journal) and status/fleet-picture reported
    STOPPED while Claude/headroom was still building.
    """
    slug = "pyforge-marshal"
    runs = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs"
    story_run = runs / "pyforge-marshal-20260918T074634825Z-6f4a14f0"
    story_run.mkdir(parents=True)
    (story_run / "journal.jsonl").write_text("{}\n", encoding="utf-8")
    (runs / "waves" / "wave-bbb").mkdir(parents=True)

    assert dispatch_cli.latest_dispatch_run_dir(tmp_path, slug) == story_run
    assert "waves" not in {p.name for p in dispatch_cli.iter_dispatch_run_dirs(tmp_path, slug)}


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
