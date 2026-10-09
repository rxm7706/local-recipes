"""Unit tests for pytest-xdist worker sharing in pr-preflight (Story 71.6, CAP-159)."""

from __future__ import annotations

import tomllib

from pyforge.steward import preflight, preflight_xdist


def test_allocate_three_lanes_on_sixteen_cores_sums_to_at_most_sixteen() -> None:
    shares = preflight_xdist.allocate_xdist_worker_counts(lane_count=3, logical_cores=16)
    assert len(shares) == 3
    assert all(s >= 1 for s in shares)
    assert sum(shares) <= 16


def test_allocate_zero_lanes_returns_empty() -> None:
    assert preflight_xdist.allocate_xdist_worker_counts(lane_count=0, logical_cores=16) == []


def test_task_cmd_uses_xdist_auto() -> None:
    pixi = tomllib.loads(
        """
[feature.x.tasks.with-xdist]
cmd = "pytest t -n auto"

[feature.x.tasks.without-xdist]
cmd = "pytest t -q"
"""
    )
    assert preflight_xdist.task_cmd_uses_xdist_auto(pixi, "no-such-task") is False
    assert preflight_xdist.task_cmd_uses_xdist_auto(pixi, "without-xdist") is False
    assert preflight_xdist.task_cmd_uses_xdist_auto(pixi, "with-xdist") is True
    pixi_trailing = tomllib.loads(
        """
[feature.x.tasks.mixed]
cmd = "true && pytest t -n auto && "
"""
    )
    assert preflight_xdist.task_cmd_uses_xdist_auto(pixi_trailing, "mixed") is True


def test_lane_xdist_worker_map_empty_when_no_xdist_tasks() -> None:
    pixi = tomllib.loads(
        """
[feature.x.tasks.plain]
cmd = "pytest t -q"
"""
    )
    assert (
        preflight_xdist.lane_xdist_worker_map(
            lane_tasks=["plain"],
            pixi_data=pixi,
            logical_cores=8,
            pool_jobs=2,
        )
        == {}
    )


def test_pytest_xdist_argv_from_cmd_and_station_task() -> None:
    assert preflight_xdist.pytest_xdist_argv_from_cmd(
        "pytest pkg -n auto --dist loadgroup"
    ) == ["-n", "auto", "--dist", "loadgroup"]
    assert preflight_xdist.pytest_xdist_argv_from_cmd("true && echo hi") == []

    pixi = tomllib.loads(
        """
[feature.pyforge-steward.tasks.pyforge-steward-test]
cmd = "pytest pkg -n auto --dist worksteal"
"""
    )
    assert preflight_xdist.pytest_xdist_argv_for_station_test_task(pixi, "steward") == [
        "-n",
        "auto",
        "--dist",
        "worksteal",
    ]
    assert preflight_xdist.pytest_xdist_argv_for_station_test_task(pixi, "missing") == []


def test_lane_xdist_worker_map_uses_minimum_share() -> None:
    pixi = tomllib.loads(
        """
[feature.pyforge-marshal.tasks.pyforge-marshal-test]
cmd = "pytest pkg/tests -q -n auto --dist loadgroup"

[feature.pyforge-doctor.tasks.pyforge-doctor-test]
cmd = "pytest pkg/tests -q -n auto --dist loadgroup"

[feature.pyforge-warden.tasks.pyforge-warden-test]
cmd = "pytest pkg/tests -q -n auto --dist loadgroup"
"""
    )
    mapping = preflight_xdist.lane_xdist_worker_map(
        lane_tasks=[
            "pyforge-marshal-test",
            "pyforge-doctor-test",
            "pyforge-warden-test",
        ],
        pixi_data=pixi,
        logical_cores=16,
        pool_jobs=3,
    )
    assert set(mapping) == {
        "pyforge-marshal-test",
        "pyforge-doctor-test",
        "pyforge-warden-test",
    }
    assert sum(mapping.values()) <= 16
    assert all(v >= 1 for v in mapping.values())


def test_lane_without_n_auto_gets_no_worker_cap(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pixi.toml").write_text(
        "[feature.guild-tasks.tasks.pr-preflight-lanes]\n"
        'depends-on = ["a", "b"]\n'
        '[feature.guild-tasks.tasks.a]\ncmd = "true"\n'
        "[feature.guild-tasks.tasks.b]\n"
        'cmd = "pytest pkg/tests -q -n auto --dist loadgroup"\n',
        encoding="utf-8",
    )

    seen: dict[str, str | None] = {}

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        seen[ctx.lane.task] = ctx.env.get("PYTEST_XDIST_AUTO_NUM_WORKERS")
        return 0

    code = preflight.run_preflight(
        repo,
        jobs=2,
        install_environment=lambda _e: 0,
        run_lane_ctx=run_ctx,
    )
    assert code == preflight.EXIT_OK
    assert seen["a"] is None
    assert seen["b"] is not None
