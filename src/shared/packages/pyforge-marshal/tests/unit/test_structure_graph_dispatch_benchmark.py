"""Story 28.31 — structure-graph dispatch provisioning benchmark tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.marshal.core import structure_graph_dispatch_benchmark as sg


def test_measure_navigation_without_graph_counts_manifest(tmp_path: Path):
    rel = "docs/readme.md"
    content = "x" * 400
    (tmp_path / "docs").mkdir()
    (tmp_path / rel).write_text(content, encoding="utf-8")
    nav = sg.measure_navigation_without_graph(tmp_path, paths=(rel,), overhead_factor=1.0)
    assert nav.manifest_bytes == 400
    assert nav.estimated_tokens == 100
    assert len(nav.files) == 1
    assert nav.files[0]["relpath"] == rel


def test_derive_recommendation_prefers_shared_index_when_sync_is_cheap():
    index = sg.IndexBuildMeasurement(
        wall_clock_seconds=19.0,
        index_bytes=232_000_000,
        codegraph_reported_seconds=11.1,
        files_indexed=18460,
        nodes=65363,
        edges=197032,
    )
    nav = sg.NavigationMeasurement(
        manifest_bytes=138_067,
        estimated_tokens=51_000,
        overhead_factor=1.5,
        files=(),
    )
    sync = sg.SyncMeasurement(wall_clock_seconds=4.0)
    rec, rationale = sg.derive_recommendation(index_build=index, navigation=nav, sync_from_base=sync)
    assert rec == "share-repo-level-index"
    assert "sync" in rationale.lower()


def test_derive_recommendation_spin_only_when_navigation_is_trivial():
    index = sg.IndexBuildMeasurement(
        wall_clock_seconds=19.0,
        index_bytes=1000,
        codegraph_reported_seconds=None,
        files_indexed=None,
        nodes=None,
        edges=None,
    )
    nav = sg.NavigationMeasurement(
        manifest_bytes=1000,
        estimated_tokens=2000,
        overhead_factor=1.0,
        files=(),
    )
    rec, _ = sg.derive_recommendation(index_build=index, navigation=nav, sync_from_base=None)
    assert rec == "spin-only"


def test_build_artifact_round_trip_json():
    index = sg.IndexBuildMeasurement(
        wall_clock_seconds=18.92,
        index_bytes=232570880,
        codegraph_reported_seconds=11.1,
        files_indexed=18460,
        nodes=65363,
        edges=197032,
    )
    nav = sg.NavigationMeasurement(
        manifest_bytes=138067,
        estimated_tokens=51775,
        overhead_factor=1.5,
        files=(),
    )
    sync = sg.SyncMeasurement(wall_clock_seconds=4.16)
    env = {"repo_root": "/tmp/repo", "project_slug": "pyforge-marshal"}
    artifact = sg.build_artifact(
        index_build=index,
        navigation=nav,
        sync_from_base=sync,
        environment=env,
    )
    payload = artifact.to_json_dict()
    blob = json.dumps(payload, sort_keys=True)
    loaded = json.loads(blob)
    assert loaded["schema"] == sg.ARTIFACT_SCHEMA
    assert loaded["ledger_key"] == sg.LEDGER_KEY
    assert loaded["recommendation"] in {
        "build-per-worktree",
        "share-repo-level-index",
        "spin-only",
    }


@pytest.mark.parametrize(
    ("init_s", "nav_tokens", "sync_s", "expected"),
    [
        (19.0, 52000, 4.0, "share-repo-level-index"),
        (19.0, 52000, None, "build-per-worktree"),
    ],
)
def test_matrix_recommendation_rows(init_s: float, nav_tokens: int, sync_s: float | None, expected: str):
    """I/O matrix: recommendation reached for measured inputs."""
    index = sg.IndexBuildMeasurement(
        wall_clock_seconds=init_s,
        index_bytes=100_000,
        codegraph_reported_seconds=None,
        files_indexed=None,
        nodes=None,
        edges=None,
    )
    nav = sg.NavigationMeasurement(
        manifest_bytes=nav_tokens * sg.CHARS_PER_TOKEN,
        estimated_tokens=nav_tokens,
        overhead_factor=1.0,
        files=(),
    )
    sync = sg.SyncMeasurement(wall_clock_seconds=sync_s) if sync_s is not None else None
    rec, _ = sg.derive_recommendation(index_build=index, navigation=nav, sync_from_base=sync)
    assert rec == expected
