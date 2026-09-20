"""Story 18.2 — FR-156 per-station tool-surface coverage is a measured number.

Coverage is published, not hard-asserted to 100%. Tests lock the report
shape and that ``coverage`` is a float in range — never ``coverage == 1.0``.
"""

from __future__ import annotations

import json
from pathlib import Path

from pyforge.marshal.mcp.coverage import (
    DREAM_STATIONS,
    format_coverage_report,
    resolve_repo_root,
    station_governed_surface,
    tool_surface_coverage_report,
)


def test_dream_stations_are_the_historical_six():
    assert DREAM_STATIONS == (
        "mason",
        "atlas",
        "warden",
        "herald",
        "steward",
        "marshal",
    )


def test_tool_surface_coverage_report_is_a_number():
    report = tool_surface_coverage_report()
    assert report["ok"] is True
    assert report["total"] == len(DREAM_STATIONS)
    assert isinstance(report["covered"], int)
    assert 0 <= report["covered"] <= report["total"]
    assert isinstance(report["coverage"], float)
    assert 0.0 <= report["coverage"] <= 1.0
    assert report["coverage"] == report["covered"] / report["total"]
    assert report["ratio"] == f"{report['covered']}/{report['total']}"
    assert len(report["stations"]) == report["total"]
    for row in report["stations"]:
        assert set(row) >= {"name", "covered", "evidence"}
        assert isinstance(row["covered"], bool)
        assert isinstance(row["evidence"], str)


def test_coverage_is_published_not_gated_on_one():
    """FR-156: publish the number; never assert coverage == 1.0 as a gate.

    Live tree may be partial or complete — either is a valid measurement.
    Shape + range are the contract; 100% is not required to pass.
    """
    report = tool_surface_coverage_report()
    assert isinstance(report["coverage"], float)
    assert 0.0 <= report["coverage"] <= 1.0
    # Explicitly do NOT assert report["coverage"] == 1.0 (or < 1.0).
    assert "coverage" in report and "ratio" in report


def test_live_dream_six_includes_atlas():
    """Regression lock: atlas stays on the governed surface (historical 2-of-6)."""
    root = resolve_repo_root()
    atlas = station_governed_surface("atlas", repo_root=root)
    assert atlas.covered is True
    assert "mcp" in atlas.evidence


def test_mason_and_marshal_surfaces_detectable():
    root = resolve_repo_root()
    mason = station_governed_surface("mason", repo_root=root)
    marshal = station_governed_surface("marshal", repo_root=root)
    assert mason.covered is True
    assert "conda_forge_server.py" in mason.evidence
    assert marshal.covered is True
    assert "mcp" in marshal.evidence


def test_format_coverage_report_is_json():
    text = format_coverage_report()
    payload = json.loads(text)
    assert "coverage" in payload
    assert isinstance(payload["coverage"], (int, float))


def test_fixture_all_uncovered_reports_zero(tmp_path: Path):
    """Inject an empty tree so covered/total is computable as 0.0."""
    (tmp_path / "pixi.toml").write_text("[workspace]\n", encoding="utf-8")
    (tmp_path / ".claude").mkdir()
    report = tool_surface_coverage_report(
        stations=("herald", "steward"),
        repo_root=tmp_path,
    )
    assert report["total"] == 2
    assert report["covered"] == 0
    assert report["coverage"] == 0.0
    assert report["ratio"] == "0/2"


def test_fixture_mason_craft_server_counts(tmp_path: Path):
    (tmp_path / "pixi.toml").write_text("[workspace]\n", encoding="utf-8")
    craft = tmp_path / ".claude" / "tools" / "conda_forge_server.py"
    craft.parent.mkdir(parents=True)
    craft.write_text("# fixture\n", encoding="utf-8")
    report = tool_surface_coverage_report(stations=("mason",), repo_root=tmp_path)
    assert report["covered"] == 1
    assert report["coverage"] == 1.0


def test_fixture_mason_missing_craft_is_uncovered(tmp_path: Path):
    (tmp_path / "pixi.toml").write_text("[workspace]\n", encoding="utf-8")
    (tmp_path / ".claude").mkdir()
    report = tool_surface_coverage_report(stations=("mason",), repo_root=tmp_path)
    assert report["covered"] == 0
    assert report["coverage"] == 0.0
    assert report["stations"][0]["covered"] is False


def test_fixture_non_mason_package_mcp_counts(tmp_path: Path):
    (tmp_path / "pixi.toml").write_text("[workspace]\n", encoding="utf-8")
    (tmp_path / ".claude").mkdir()
    server = (
        tmp_path / "src" / "shared" / "packages" / "pyforge-herald" / "src" / "pyforge" / "herald" / "mcp" / "server.py"
    )
    server.parent.mkdir(parents=True)
    server.write_text("# fixture\n", encoding="utf-8")
    report = tool_surface_coverage_report(stations=("herald",), repo_root=tmp_path)
    assert report["covered"] == 1
    assert report["coverage"] == 1.0


def test_duplicate_stations_do_not_inflate_total(tmp_path: Path):
    (tmp_path / "pixi.toml").write_text("[workspace]\n", encoding="utf-8")
    (tmp_path / ".claude").mkdir()
    report = tool_surface_coverage_report(
        stations=("herald", "herald", "steward"),
        repo_root=tmp_path,
    )
    assert report["total"] == 2
    assert report["ratio"] == "0/2"
