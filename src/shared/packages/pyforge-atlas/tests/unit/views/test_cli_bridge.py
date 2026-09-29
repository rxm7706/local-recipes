"""Story 14.1 (CAP-1) — the dynamic-import bridge to the conda-forge-expert skill CLIs.

Covers the I/O matrix's HAPPY_PATH and DB_MISSING rows at the level the intent-contract
names explicitly ("cli_bridge catches the SystemExit ... raises CfAtlasDbUnavailableError"),
plus the tuple-return normalization (cve-watcher) that :func:`call_query` documents.
"""

from __future__ import annotations

import pytest

from pyforge.atlas.views import cli_bridge

_STALENESS_KWARGS = {
    "maintainer": None,
    "min_age_days": 0,
    "limit": 25,
    "include_archived": False,
}

_CVE_WATCHER_KWARGS = {
    "maintainer": None,
    "since_days": 7,
    "severity": "C",
    "only_increases": False,
    "limit": 25,
    "epss_threshold": None,
}


def test_default_scripts_dir_resolves_to_the_real_skill_scripts():
    scripts_dir = cli_bridge.default_scripts_dir()
    assert scripts_dir.is_dir()
    for script in (
        "staleness_report",
        "feedstock_health",
        "behind_upstream",
        "cve_watcher",
        "release_cadence",
        "adoption_stage",
    ):
        assert (scripts_dir / f"{script}.py").is_file()


def test_call_query_happy_path(atlas_db_path, monkeypatch):
    module = cli_bridge.load_cli_module("staleness_report", scripts_dir=cli_bridge.default_scripts_dir())
    monkeypatch.setattr(module, "DB_PATH", atlas_db_path)

    rows = cli_bridge.call_query(module, **_STALENESS_KWARGS)

    assert rows
    assert all(isinstance(row, dict) for row in rows)
    assert {row["conda_name"] for row in rows} == {
        "alpha-pkg",
        "beta-pkg",
        "gamma-pkg",
        "delta-pkg",
    }
    # sorted oldest-upload-first (default order_clause) -> alpha-pkg (the oldest) is first.
    assert rows[0]["conda_name"] == "alpha-pkg"


def test_call_query_empty_result(empty_atlas_db_path, monkeypatch):
    module = cli_bridge.load_cli_module("staleness_report", scripts_dir=cli_bridge.default_scripts_dir())
    monkeypatch.setattr(module, "DB_PATH", empty_atlas_db_path)

    rows = cli_bridge.call_query(module, **_STALENESS_KWARGS)

    assert rows == []


def test_call_query_db_missing_raises_a_catchable_error_not_a_killed_process(tmp_path, monkeypatch):
    module = cli_bridge.load_cli_module("staleness_report", scripts_dir=cli_bridge.default_scripts_dir())
    monkeypatch.setattr(module, "DB_PATH", tmp_path / "does-not-exist.db")

    with pytest.raises(cli_bridge.CfAtlasDbUnavailableError):
        cli_bridge.call_query(module, **_STALENESS_KWARGS)


def test_call_query_unwraps_the_rows_meta_tuple_cve_watcher_returns(atlas_db_path, monkeypatch):
    """cve-watcher's query() returns (rows, meta) — call_query normalizes every caller to a
    plain list[dict], dropping meta, so the registry/render layers never special-case it."""
    module = cli_bridge.load_cli_module("cve_watcher", scripts_dir=cli_bridge.default_scripts_dir())
    monkeypatch.setattr(module, "DB_PATH", atlas_db_path)

    rows = cli_bridge.call_query(module, **_CVE_WATCHER_KWARGS)

    assert isinstance(rows, list)
    assert rows and all(isinstance(row, dict) for row in rows)
    assert rows[0]["conda_name"] == "gamma-pkg"
    assert rows[0]["delta"] == 2
