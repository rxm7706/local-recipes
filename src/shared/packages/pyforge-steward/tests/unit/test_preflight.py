"""Unit tests for pyforge.steward.preflight (Story 71.1)."""

from __future__ import annotations

import json
import threading
import time
import tomllib
from pathlib import Path

import pytest

from pyforge.steward import preflight

REPO_ROOT = Path(__file__).resolve().parents[6]

_NOOP_INSTALL = lambda _env: 0  # noqa: E731
_SERIAL = {"jobs": 1, "install_environment": _NOOP_INSTALL}


def _run_journal_record(repo: Path) -> dict:
    lines = (repo / preflight.JOURNAL_RELATIVE).read_text(encoding="utf-8").strip().splitlines()
    records = [json.loads(line) for line in lines if line.strip()]
    return next(record for record in reversed(records) if "lanes" in record)


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

[feature.guild-tasks.tasks.combo-dep]
cmd = "echo dep"

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


def _lane_map(pixi: dict) -> dict[str, preflight.Lane]:
    lanes = preflight.list_preflight_lanes(pixi, invoking_env="pyforge-guild")
    return {lane.task: lane for lane in lanes}


def test_real_pixi_lists_every_leaf_once() -> None:
    pixi = tomllib.loads((REPO_ROOT / "pixi.toml").read_text(encoding="utf-8"))
    lanes = preflight.list_preflight_lanes(pixi, invoking_env="pyforge-guild")
    keys = [(lane.task, lane.environment) for lane in lanes]
    assert len(keys) == len(set(keys))
    assert "pyforge-station-tests" not in {k[0] for k in keys}
    assert ("pyforge-core-test", "pyforge-core") in keys
    assert ("detectors-ci", "pyforge-guild") in keys
    assert ("ruff", "pyforge-guild") in keys
    by_task = _lane_map(pixi)
    assert by_task["pages-check"].depends_on == (("pages-build", "site"),)
    # herald Story 43.7: the sidebar is computed at build from docs/map.yaml (no docs-site-sidebar task), and the map
    # check reads YAML with docs-site's npm packages.
    assert set(by_task["pages-build"].depends_on) == {("docs-site-install", "site")}
    assert set(by_task["docs-site-validate-sidebar"].depends_on) == {
        ("docs-site-install", "site"),
        ("docs-site-validate-sidebar-order", "site"),
    }


def test_missing_aggregate_exits_2(tmp_path: Path) -> None:
    pixi_path = tmp_path / "pixi.toml"
    pixi_path.write_text("[feature.guild-tasks.tasks.other]\ncmd = 'true'\n", encoding="utf-8")
    assert preflight.run_preflight(tmp_path, pixi_path=pixi_path, **_SERIAL) == preflight.EXIT_CONFIG


def test_unknown_task_exits_2(tmp_path: Path) -> None:
    pixi_path = tmp_path / "pixi.toml"
    pixi_path.write_text(
        '[feature.guild-tasks.tasks.pr-preflight-lanes]\ndepends-on = ["missing-task"]\n',
        encoding="utf-8",
    )
    assert preflight.run_preflight(tmp_path, pixi_path=pixi_path, **_SERIAL) == preflight.EXIT_CONFIG


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

    code = preflight.run_preflight(tmp_path, pixi_path=pixi_path, run_lane=fake_run, **_SERIAL)
    assert code == preflight.EXIT_LANE_RED
    assert calls == ["a", "b", "c"]
    record = _run_journal_record(tmp_path)
    assert record["verdict"] == "red"
    statuses = [entry["status"] for entry in record["lanes"]]
    assert statuses == ["ok", "ok", "red", "cancelled"]


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
        **_SERIAL,
    )
    assert code == preflight.EXIT_OK
    record = _run_journal_record(tmp_path)
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


def test_dependency_graph_runs_each_task_once_in_order(tmp_path: Path) -> None:
    pixi_path = tmp_path / "pixi.toml"
    pixi_path.write_text(
        "[feature.guild-tasks.tasks.pr-preflight-lanes]\n"
        'depends-on = ["a", "e"]\n'
        "[feature.guild-tasks.tasks.a]\n"
        'depends-on = ["b", "c"]\n'
        'cmd = "true"\n'
        "[feature.guild-tasks.tasks.b]\n"
        'depends-on = ["d"]\n'
        'cmd = "true"\n'
        "[feature.guild-tasks.tasks.c]\n"
        'cmd = "true"\n'
        "[feature.guild-tasks.tasks.d]\n"
        'cmd = "true"\n'
        "[feature.guild-tasks.tasks.e]\n"
        'cmd = "true"\n',
        encoding="utf-8",
    )
    order: list[str] = []
    finish_times: dict[str, float] = {}
    start_times: dict[str, float] = {}
    lock = threading.Lock()

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        with lock:
            start_times[ctx.lane.task] = time.monotonic()
        time.sleep(0.05)
        with lock:
            finish_times[ctx.lane.task] = time.monotonic()
            order.append(ctx.lane.task)
        return 0

    code = preflight.run_preflight(
        tmp_path,
        pixi_path=pixi_path,
        jobs=4,
        install_environment=_NOOP_INSTALL,
        run_lane_ctx=run_ctx,
    )
    assert code == preflight.EXIT_OK
    assert set(order) == {"a", "b", "c", "d", "e"}
    assert len(order) == len(set(order))
    assert finish_times["d"] <= start_times["b"]
    assert finish_times["b"] <= start_times["a"]
    assert finish_times["c"] <= start_times["a"]
    record = _run_journal_record(tmp_path)
    assert {entry["task"] for entry in record["lanes"]} == set(order)
    assert len(record["lanes"]) == 5


# Story 88.1's fixture: ``a`` depends on ``b`` and ``c``, ``b`` on ``d``; ``e`` stands alone; ``d`` goes red.
RED_DEPENDENCY_TOML = (
    "[feature.guild-tasks.tasks.pr-preflight-lanes]\n"
    'depends-on = ["a", "e"]\n'
    "[feature.guild-tasks.tasks.a]\n"
    'depends-on = ["b", "c"]\n'
    'cmd = "true"\n'
    "[feature.guild-tasks.tasks.b]\n"
    'depends-on = ["d"]\n'
    'cmd = "true"\n'
    "[feature.guild-tasks.tasks.c]\n"
    'cmd = "true"\n'
    "[feature.guild-tasks.tasks.d]\n"
    'cmd = "true"\n'
    "[feature.guild-tasks.tasks.e]\n"
    'cmd = "true"\n'
)


def _assert_cancelled_by_d(by_task: dict[str, dict], task: str) -> None:
    entry = by_task[task]
    assert entry["status"] == "cancelled", task
    assert entry["cancelled_by"] == "d", task
    assert entry["cancelled_by_environment"] == by_task["d"]["environment"], task


def test_red_dependency_cancels_dependents(tmp_path: Path) -> None:
    pixi_path = tmp_path / "pixi.toml"
    pixi_path.write_text(RED_DEPENDENCY_TOML, encoding="utf-8")
    started: set[str] = set()

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        started.add(ctx.lane.task)
        return 1 if ctx.lane.task == "d" else 0

    code = preflight.run_preflight(
        tmp_path,
        pixi_path=pixi_path,
        jobs=4,
        install_environment=_NOOP_INSTALL,
        run_lane_ctx=run_ctx,
    )
    assert code == preflight.EXIT_LANE_RED
    # d's dependents never start. c and e have no dependencies, so with jobs=4 they may
    # start before d's failure registers, or be cancelled by the stop; either is correct.
    assert "d" in started
    assert started.isdisjoint({"a", "b"})
    record = _run_journal_record(tmp_path)
    by_task = {entry["task"]: entry for entry in record["lanes"]}
    assert by_task["d"]["status"] == "red"
    assert "cancelled_by" not in by_task["d"]
    _assert_cancelled_by_d(by_task, "b")
    _assert_cancelled_by_d(by_task, "a")
    for independent in ("c", "e"):
        if independent in started:
            assert by_task[independent]["status"] == "ok"
        else:
            # Story 71.12: cancelled whether the pool turned it away or the scheduler never submitted it.
            _assert_cancelled_by_d(by_task, independent)


def test_a_lane_the_stop_kept_from_being_submitted_names_the_red_lane(tmp_path: Path) -> None:
    """Story 71.12 AC (1): with one worker the stop always comes before ``c``, ``a`` and ``e`` are submitted.

    ``d`` runs first and goes red; ``c`` is never offered, so ``a`` keeps a dependency with no result and only the
    result assembly journals it. Each of them still names ``d``. On ``9fc4cb1c2b`` they carried no ``cancelled_by``.
    """
    pixi_path = tmp_path / "pixi.toml"
    pixi_path.write_text(RED_DEPENDENCY_TOML, encoding="utf-8")
    started: list[str] = []

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        started.append(ctx.lane.task)
        return 1 if ctx.lane.task == "d" else 0

    code = preflight.run_preflight(tmp_path, pixi_path=pixi_path, run_lane_ctx=run_ctx, **_SERIAL)
    assert code == preflight.EXIT_LANE_RED
    assert started == ["d"]
    by_task = {entry["task"]: entry for entry in _run_journal_record(tmp_path)["lanes"]}
    assert set(by_task) == {"a", "b", "c", "d", "e"}
    assert by_task["d"]["status"] == "red"
    assert "cancelled_by" not in by_task["d"]
    for task in ("b", "c", "a", "e"):
        _assert_cancelled_by_d(by_task, task)
        assert by_task[task]["exit_code"] == 0
        assert by_task[task]["seconds"] == 0.0


def test_red_dependency_keep_going_blocks_dependents_only(tmp_path: Path) -> None:
    pixi_path = tmp_path / "pixi.toml"
    pixi_path.write_text(
        "[feature.guild-tasks.tasks.pr-preflight-lanes]\n"
        'depends-on = ["a", "e"]\n'
        "[feature.guild-tasks.tasks.a]\n"
        'depends-on = ["b", "c"]\n'
        'cmd = "true"\n'
        "[feature.guild-tasks.tasks.b]\n"
        'depends-on = ["d"]\n'
        'cmd = "true"\n'
        "[feature.guild-tasks.tasks.c]\n"
        'cmd = "true"\n'
        "[feature.guild-tasks.tasks.d]\n"
        'cmd = "true"\n'
        "[feature.guild-tasks.tasks.e]\n"
        'cmd = "true"\n',
        encoding="utf-8",
    )

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        return 1 if ctx.lane.task == "d" else 0

    code = preflight.run_preflight(
        tmp_path,
        pixi_path=pixi_path,
        jobs=4,
        keep_going=True,
        install_environment=_NOOP_INSTALL,
        run_lane_ctx=run_ctx,
    )
    assert code == preflight.EXIT_LANE_RED
    record = _run_journal_record(tmp_path)
    by_task = {entry["task"]: entry for entry in record["lanes"]}
    assert by_task["d"]["status"] == "red"
    assert by_task["b"]["status"] == "not-run"
    assert by_task["b"]["blocked_by"] == "d"
    assert by_task["a"]["status"] == "not-run"
    assert by_task["a"]["blocked_by"] == "d"
    assert by_task["c"]["status"] == "ok"
    assert by_task["e"]["status"] == "ok"


def test_default_subprocess_argv_includes_skip_deps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pixi_path = tmp_path / "pixi.toml"
    pixi_path.write_text(
        "[feature.guild-tasks.tasks.pr-preflight-lanes]\n"
        'depends-on = ["a"]\n'
        "[feature.guild-tasks.tasks.a]\n"
        'cmd = "true"\n',
        encoding="utf-8",
    )
    captured: list[list[str]] = []
    real_run = preflight._run_pixi_argv  # noqa: SLF001

    def capture_argv(coord: object, ctx: preflight.LaneRunContext, argv: list[str], log_handle: object) -> int:
        captured.append(list(argv))
        return real_run(coord, ctx, ["true"], log_handle)

    monkeypatch.setattr(preflight, "_run_pixi_argv", capture_argv)
    assert (
        preflight.run_preflight(tmp_path, pixi_path=pixi_path, jobs=1, install_environment=_NOOP_INSTALL)
        == preflight.EXIT_OK
    )
    assert captured
    assert captured[0][:4] == ["pixi", "run", "--frozen", "--skip-deps"]
    assert captured[0][4] == "-e"
    assert captured[0][6] == "a"


def test_pages_lanes_with_dependency_scheduler_avoid_write_overlap(tmp_path: Path) -> None:
    pixi_path = tmp_path / "pixi.toml"
    pixi_path.write_text(
        "[feature.guild-tasks.tasks.pr-preflight-lanes]\n"
        'depends-on = [{ task = "pages-check", environment = "site" }]\n'
        "[feature.site.tasks.docs-site-install]\n"
        'cmd = "true"\n'
        "[feature.site.tasks.docs-site-sidebar]\n"
        'cmd = "true"\n'
        "[feature.site.tasks.pages-build]\n"
        'depends-on = ["docs-site-install", "docs-site-sidebar"]\n'
        'cmd = "true"\n'
        "[feature.site.tasks.pages-check]\n"
        'depends-on = ["pages-build"]\n'
        'cmd = "true"\n',
        encoding="utf-8",
    )
    active: set[str] = set()
    peak = 0
    lock = threading.Lock()

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        nonlocal peak
        with lock:
            active.add(ctx.lane.task)
            peak = max(peak, len(active))
            if len(active) >= 3:
                return 1
        time.sleep(0.03)
        with lock:
            active.discard(ctx.lane.task)
        return 0

    code = preflight.run_preflight(
        tmp_path,
        pixi_path=pixi_path,
        invoking_env="pyforge-guild",
        jobs=4,
        install_environment=_NOOP_INSTALL,
        run_lane_ctx=run_ctx,
    )
    assert code == preflight.EXIT_OK
    assert peak <= 2


# ---- Story 99.8: the red-main banner is advisory ----------------------------------------------------


def _red_main_snapshot(root: Path, raw: bytes | None = None) -> None:
    from datetime import UTC, datetime

    path = root / ".steward" / "ci-status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if raw is not None:
        path.write_bytes(raw)
        return
    doc = {
        "fetched_at": datetime.now(tz=UTC).isoformat(),
        "rows": [
            {
                "id": "kedro-viz-publish.vizro",
                "latest_main_run": {"conclusion": "failure", "created_at": None, "run_id": 5},
            }
        ],
    }
    path.write_text(json.dumps(doc), encoding="utf-8")


@pytest.mark.parametrize(
    ("flag_on", "snapshot"),
    [
        (True, None),
        (False, None),
        (True, b"\xff not json"),
        (True, b'{"fetched_at": "2026-10-25T00:00:00", "rows": [{"id": []}]}'),
    ],
)
def test_the_red_main_banner_never_changes_the_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    flag_on: bool,
    snapshot: bytes | None,
) -> None:
    from pyforge.steward import preflight_ci

    pixi_path = tmp_path / "pixi.toml"
    pixi_path.write_text(
        "[feature.guild-tasks.tasks.pr-preflight-lanes]\n"
        'depends-on = ["a", "b"]\n'
        "[feature.guild-tasks.tasks.a]\ncmd = 'true'\n"
        "[feature.guild-tasks.tasks.b]\ncmd = 'true'\n",
        encoding="utf-8",
    )
    _red_main_snapshot(tmp_path, snapshot)
    monkeypatch.setattr(preflight_ci, "_flag_on", lambda _root: flag_on)
    calls: list[str] = []

    def fake_run(lane: preflight.Lane) -> int:
        calls.append(lane.task)
        return 1 if lane.task == "b" else 0

    code = preflight.run_preflight(tmp_path, pixi_path=pixi_path, run_lane=fake_run, **_SERIAL)
    err = capsys.readouterr().err
    assert code == preflight.EXIT_LANE_RED
    assert calls == ["a", "b"]
    assert ("preflight: main is red on kedro-viz-publish.vizro: failure, run 5" in err) is (
        flag_on and snapshot is None
    )
    assert ("main CI state unknown" in err) is (flag_on and snapshot is not None)
    if not flag_on:
        assert "main is red" not in err and "main CI state" not in err
