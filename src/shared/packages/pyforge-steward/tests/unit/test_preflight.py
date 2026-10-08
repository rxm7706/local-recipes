"""Unit tests for pyforge.steward.preflight (Story 71.1)."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from pyforge.steward import preflight

REPO_ROOT = Path(__file__).resolve().parents[5]


FIXTURE_TOML = """
[feature.guild-tasks.tasks.pr-preflight-lanes]
depends-on = ["outer-aggregate"]

[feature.guild-tasks.tasks.outer-aggregate]
depends-on = ["inner-a", { task = "pinned", environment = "other-env" }, "combo"]

[feature.guild-tasks.tasks.inner-a]
depends-on = ["leaf-bare"]
cmd = "true"

[feature.guild-tasks.tasks.leaf-bare]
cmd = "echo bare"

[feature.guild-tasks.tasks.pinned]
cmd = "echo pinned"

[feature.guild-tasks.tasks.combo]
depends-on = ["combo-dep"]
cmd = "echo combo"
"""


def _pixi(text: str) -> dict:
    return tomllib.loads(text)


def test_fixture_lists_leaves_in_declaration_order() -> None:
    lanes = preflight.list_preflight_lanes(_pixi(FIXTURE_TOML), invoking_env="pyforge-guild")
    assert [(lane.task, lane.environment) for lane in lanes] == [
        ("leaf-bare", "pyforge-guild"),
        ("inner-a", "pyforge-guild"),
        ("pinned", "other-env"),
        ("combo-dep", "pyforge-guild"),
        ("combo", "pyforge-guild"),
    ]


def test_real_pixi_lists_every_leaf_once() -> None:
    pixi = tomllib.loads((REPO_ROOT / "pixi.toml").read_text(encoding="utf-8"))
    lanes = preflight.list_preflight_lanes(pixi, invoking_env="pyforge-guild")
    keys = [(lane.task, lane.environment) for lane in lanes]
    assert len(keys) == len(set(keys))
    assert "pyforge-station-tests" not in {k[0] for k in keys}
    assert ("pyforge-core-test", "pyforge-core") in keys
    assert ("detectors-ci", "pyforge-guild") in keys
    assert ("ruff", "pyforge-guild") in keys


def test_missing_aggregate_exits_2(tmp_path: Path) -> None:
    pixi_path = tmp_path / "pixi.toml"
    pixi_path.write_text("[feature.guild-tasks.tasks.other]\ncmd = 'true'\n", encoding="utf-8")
    assert preflight.run_preflight(tmp_path, pixi_path=pixi_path) == preflight.EXIT_CONFIG


def test_unknown_task_exits_2(tmp_path: Path) -> None:
    pixi_path = tmp_path / "pixi.toml"
    pixi_path.write_text(
        "[feature.guild-tasks.tasks.pr-preflight-lanes]\n"
        'depends-on = ["missing-task"]\n',
        encoding="utf-8",
    )
    assert preflight.run_preflight(tmp_path, pixi_path=pixi_path) == preflight.EXIT_CONFIG


def test_third_lane_red_stops_and_journals(tmp_path: Path) -> None:
    pixi_path = tmp_path / "pixi.toml"
    pixi_path.write_text(
        "[feature.guild-tasks.tasks.pr-preflight-lanes]\n"
        'depends-on = ["a", "b", "c", "d"]\n'
        "[feature.guild-tasks.tasks.a]\ncmd = 'true'\n"
        "[feature.guild-tasks.tasks.b]\ncmd = 'true'\n"
        "[feature.guild-tasks.tasks.c]\ncmd = 'true'\n"
        "[feature.guild-tasks.tasks.d]\ncmd = 'true'\n",
        encoding="utf-8",
    )
    calls: list[str] = []

    def fake_run(lane: preflight.Lane) -> int:
        calls.append(lane.task)
        return 1 if lane.task == "c" else 0

    code = preflight.run_preflight(tmp_path, pixi_path=pixi_path, run_lane=fake_run)
    assert code == preflight.EXIT_LANE_RED
    assert calls == ["a", "b", "c"]
    journal = tmp_path / preflight.JOURNAL_RELATIVE
    lines = journal.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["verdict"] == "red"
    statuses = [entry["status"] for entry in record["lanes"]]
    assert statuses == ["ok", "ok", "red", "not-run"]


def test_all_green_journals_ok(tmp_path: Path) -> None:
    pixi_path = tmp_path / "pixi.toml"
    pixi_path.write_text(
        "[feature.guild-tasks.tasks.pr-preflight-lanes]\n"
        'depends-on = ["a", "b"]\n'
        "[feature.guild-tasks.tasks.a]\ncmd = 'true'\n"
        "[feature.guild-tasks.tasks.b]\ncmd = 'true'\n",
        encoding="utf-8",
    )
    code = preflight.run_preflight(
        tmp_path,
        pixi_path=pixi_path,
        run_lane=lambda _lane: 0,
    )
    assert code == preflight.EXIT_OK
    record = json.loads((tmp_path / preflight.JOURNAL_RELATIVE).read_text(encoding="utf-8").strip())
    assert record["verdict"] == "ok"
    assert record["logical_cores"] >= 1
    assert record["total_seconds"] >= 0
    assert all(entry["status"] == "ok" for entry in record["lanes"])


def test_cycle_is_config_error() -> None:
    text = """
[feature.guild-tasks.tasks.pr-preflight-lanes]
depends-on = ["a"]

[feature.guild-tasks.tasks.a]
depends-on = ["b"]
cmd = "true"

[feature.guild-tasks.tasks.b]
depends-on = ["a"]
cmd = "true"
"""
    with pytest.raises(preflight.PreflightConfigError, match="cycle"):
        preflight.list_preflight_lanes(_pixi(text))
