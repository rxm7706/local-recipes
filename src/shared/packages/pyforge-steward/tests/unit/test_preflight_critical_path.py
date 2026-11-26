"""Story 117.3 (spec-pyforge-steward CAP-175): the preflight admits lanes longest-first by the cores they will use.

Behind ``pyforge.steward.preflight_critical_path`` (a kill switch, ON): ready lanes start longest-expected first, where a
lane's expected seconds are its journal median over its last green runs and a lane with no history weighs
``preflight.UNKNOWN_LANE_SECONDS``; a serial lane holds one core, an xdist lane the share of the free cores it is given at
admission (never below ``MIN_XDIST_WORKERS``), and admitted weights never exceed the logical cores. OFF reproduces
declaration order and Story 71.6's static share.
"""

from __future__ import annotations

import json
import threading
import time
import tomllib
from pathlib import Path

import pytest
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states, flagd_tree

from pyforge.steward import preflight, preflight_xdist

INV = "pyforge-guild"
_NOOP_INSTALL = lambda _env: 0  # noqa: E731
flag_provider = make_flag_provider_fixture()


@pytest.fixture(autouse=True)
def _no_inherited_share(monkeypatch: pytest.MonkeyPatch) -> None:
    # Under pr-preflight this suite is itself an xdist lane and inherits the variable the tests read back.
    monkeypatch.delenv("PYTEST_XDIST_AUTO_NUM_WORKERS", raising=False)


def _pixi(lanes: dict[str, str]) -> str:
    """``pr-preflight-lanes`` over ``lanes`` (task -> cmd), every lane in ``INV``."""
    body = "\n".join(f'[feature.guild-tasks.tasks.{name}]\ncmd = "{cmd}"\n' for name, cmd in lanes.items())
    deps = ", ".join(f'"{name}"' for name in lanes)
    return f"[feature.guild-tasks.tasks.pr-preflight-lanes]\ndepends-on = [{deps}]\n\n{body}"


def _journal(repo: Path, medians: dict[str, float], *, runs: int = 5) -> None:
    """``runs`` green journal runs in which each lane took its median seconds."""
    rows = []
    for index in range(runs):
        lanes = [
            {"task": task, "environment": INV, "seconds": seconds, "start_offset": 0.0, "status": "ok", "exit_code": 0}
            for task, seconds in medians.items()
        ]
        rows.append({"run_id": f"r{index}", "lanes": lanes, "verdict": "ok", "total_seconds": max(medians.values())})
    path = repo / preflight.JOURNAL_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


FIVE = {
    "xdist-suite": "pytest pkg/tests -q -n auto --dist loadgroup",
    "serial-a": "pytest a -q",
    "serial-b": "pytest b -q",
    "serial-c": "pytest c -q",
    "serial-d": "pytest d -q",
}
MEDIANS = {"serial-c": 100.0, "xdist-suite": 80.0, "serial-a": 10.0, "serial-b": 5.0}  # serial-d: no history


def _run(
    repo: Path, *, jobs: int, cores: int, critical: bool | None, sleep: float = 0.0
) -> tuple[list[str], dict[str, str | None], int]:
    order: list[str] = []
    workers: dict[str, str | None] = {}
    lock = threading.Lock()

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        with lock:
            order.append(ctx.lane.task)
            workers[ctx.lane.task] = ctx.env.get("PYTEST_XDIST_AUTO_NUM_WORKERS")
        time.sleep(sleep)
        return 0

    code = preflight.run_preflight(
        repo,
        invoking_env=INV,
        jobs=jobs,
        logical_cores=cores,
        critical_path=critical,
        install_environment=_NOOP_INSTALL,
        run_lane_ctx=run_ctx,
        scratch_parent=repo.parent,
    )
    return order, workers, code


def test_lane_medians_read_the_last_green_runs_only(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _journal(repo, {"serial-a": 10.0}, runs=7)
    path = repo / preflight.JOURNAL_RELATIVE
    red = {
        "run_id": "red",
        "verdict": "red",
        "total_seconds": 9.0,
        "lanes": [{"task": "serial-a", "environment": INV, "seconds": 999.0, "status": "red", "exit_code": 1}],
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(red) + "\n")
    medians = preflight.lane_medians(path)
    assert medians == {("serial-a", INV): 10.0}
    assert preflight.lane_medians(tmp_path / "missing.jsonl") == {}


def test_xdist_share_at_admission_splits_the_free_cores_and_waits_below_two() -> None:
    share = preflight_xdist.xdist_share_at_admission
    assert share(free_cores=15, pending_xdist=1, logical_cores=16) == 15
    assert share(free_cores=15, pending_xdist=3, logical_cores=16) == 5
    assert share(free_cores=3, pending_xdist=4, logical_cores=16) == 2  # never below MIN_XDIST_WORKERS
    assert share(free_cores=1, pending_xdist=1, logical_cores=16) == 0  # waits
    assert share(free_cores=40, pending_xdist=1, logical_cores=16) == 16  # never above the machine


def test_on_the_longest_expected_lane_goes_first_and_the_xdist_lane_takes_its_share(tmp_path: Path) -> None:
    """AC1: five lanes, one xdist; at one slot the order is by expected seconds, unknown lanes weigh 30 s."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pixi.toml").write_text(_pixi(FIVE), encoding="utf-8")
    _journal(repo, MEDIANS)
    order, workers, code = _run(repo, jobs=1, cores=16, critical=True)
    assert code == preflight.EXIT_OK
    assert order == ["serial-c", "xdist-suite", "serial-d", "serial-a", "serial-b"]
    # the xdist lane found 16 free cores and was the only xdist lane pending: it got them all, not the static minimum
    assert workers["xdist-suite"] == "16"
    assert workers["serial-c"] is None


def test_off_keeps_declaration_order_and_the_static_share(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pixi.toml").write_text(_pixi(FIVE), encoding="utf-8")
    _journal(repo, MEDIANS)
    order, workers, code = _run(repo, jobs=1, cores=16, critical=False)
    assert code == preflight.EXIT_OK
    assert order == list(FIVE)
    # Story 71.6's static share, computed the way the OFF path computes it: from the fixture's own task table on the
    # injected core count (CI's four cores and a laptop's sixteen must agree; PR #2332 caught the 16 assumed here).
    static = preflight_xdist.lane_xdist_worker_map(
        lanes=[(task, INV) for task in FIVE], pixi_data=tomllib.loads(_pixi(FIVE)), logical_cores=16, pool_jobs=1
    )
    assert ("xdist-suite", INV) in static
    assert workers["xdist-suite"] == str(static[("xdist-suite", INV)])
    assert workers["serial-a"] is None


def test_on_admitted_weights_never_exceed_the_cores_and_jobs_still_caps_lanes(tmp_path: Path) -> None:
    """AC2: two xdist lanes on four cores take two workers each and the serial lanes wait; --jobs 1 runs one at a time."""
    repo = tmp_path / "repo"
    repo.mkdir()
    lanes = {"x1": "pytest x1 -q -n auto", "x2": "pytest x2 -q -n auto", "s1": "pytest s1 -q", "s2": "pytest s2 -q"}
    (repo / "pixi.toml").write_text(_pixi(lanes), encoding="utf-8")
    _journal(repo, {"x1": 50.0, "x2": 40.0, "s1": 30.0, "s2": 20.0})
    in_flight = 0
    peak = 0
    lock = threading.Lock()
    workers: dict[str, int] = {}

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        nonlocal in_flight, peak
        weight = int(ctx.env.get("PYTEST_XDIST_AUTO_NUM_WORKERS", "1"))
        with lock:
            workers[ctx.lane.task] = weight
            in_flight += weight
            peak = max(peak, in_flight)
        time.sleep(0.05)
        with lock:
            in_flight -= weight
        return 0

    code = preflight.run_preflight(
        repo,
        invoking_env=INV,
        jobs=8,
        logical_cores=4,
        critical_path=True,
        install_environment=_NOOP_INSTALL,
        run_lane_ctx=run_ctx,
        scratch_parent=tmp_path,
    )
    assert code == preflight.EXIT_OK
    assert peak <= 4, workers
    assert workers["x1"] == 2 and workers["x2"] == 2
    order, _workers, code = _run(repo, jobs=1, cores=4, critical=True, sleep=0.0)
    assert code == preflight.EXIT_OK
    assert order == ["x1", "x2", "s1", "s2"]


def test_a_lane_with_no_history_weighs_thirty_seconds(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pixi.toml").write_text(
        _pixi({"known-fast": "pytest a -q", "unknown": "pytest u -q", "known-slow": "pytest b -q"}), encoding="utf-8"
    )
    _journal(repo, {"known-fast": 5.0, "known-slow": 40.0})
    order, _workers, code = _run(repo, jobs=1, cores=2, critical=True)
    assert code == preflight.EXIT_OK
    assert order == ["known-slow", "unknown", "known-fast"]


@flag_states("pyforge.steward.preflight_critical_path")
def test_the_flag_switches_the_scheduler(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC4: ON orders by expected seconds, OFF by declaration; the key is read through the flag tree."""
    on = flag_provider["pyforge.steward.preflight_critical_path"]
    tree = flagd_tree(tmp_path, {"pyforge.steward.preflight_critical_path": "on" if on else "off"})
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pixi.toml").write_text(_pixi(FIVE), encoding="utf-8")
    _journal(repo, MEDIANS)
    order, _workers, code = _run(repo, jobs=1, cores=16, critical=None)
    assert code == preflight.EXIT_OK
    assert order == (["serial-c", "xdist-suite", "serial-d", "serial-a", "serial-b"] if on else list(FIVE))


# ---------------------------------------------------------------------------
# Story 117.15: a fresh worktree is ordered from the tracked budgets, and an xdist lane's share follows its work
# ---------------------------------------------------------------------------


def _budgets(repo: Path, lanes: dict[str, float]) -> None:
    path = repo / preflight.BUDGETS_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f'"{task}@{INV}" = {seconds}' for task, seconds in lanes.items())
    path.write_text(f"[defaults]\nsingle_station = 90\nfull = 240\n\n[lanes]\n{body}\n", encoding="utf-8")


def _weighted_run(repo: Path, *, cores: int) -> tuple[dict[str, int], int, int]:
    """Run every lane of ``repo`` at once (eight slots); each lane's workers, the peak cores in flight, the exit code."""
    in_flight = 0
    peak = 0
    lock = threading.Lock()
    workers: dict[str, int] = {}

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        nonlocal in_flight, peak
        weight = int(ctx.env.get("PYTEST_XDIST_AUTO_NUM_WORKERS", "1"))
        with lock:
            workers[ctx.lane.task] = weight
            in_flight += weight
            peak = max(peak, in_flight)
        time.sleep(0.2)
        with lock:
            in_flight -= weight
        return 0

    code = preflight.run_preflight(
        repo,
        invoking_env=INV,
        jobs=8,
        logical_cores=cores,
        critical_path=True,
        install_environment=_NOOP_INSTALL,
        run_lane_ctx=run_ctx,
        scratch_parent=repo.parent,
    )
    return workers, peak, code


def test_a_fresh_worktree_orders_lanes_by_the_tracked_budgets(tmp_path: Path) -> None:
    """No journal: a lane's expected seconds are its tracked budget, and a lane in neither weighs thirty seconds."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pixi.toml").write_text(_pixi(FIVE), encoding="utf-8")
    _budgets(repo, {"serial-b": 200.0, "xdist-suite": 80.0, "serial-a": 10.0})
    order, _workers, code = _run(repo, jobs=1, cores=16, critical=True)
    assert code == preflight.EXIT_OK
    assert order == ["serial-b", "xdist-suite", "serial-c", "serial-d", "serial-a"]


def test_a_journal_median_outranks_the_budget_seed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pixi.toml").write_text(_pixi(FIVE), encoding="utf-8")
    _budgets(repo, {"serial-a": 500.0, "serial-b": 1.0})
    _journal(repo, {"serial-a": 2.0})  # the lane's own green runs say two seconds, whatever the budget says
    order, _workers, code = _run(repo, jobs=1, cores=16, critical=True)
    assert code == preflight.EXIT_OK
    assert order == ["xdist-suite", "serial-c", "serial-d", "serial-a", "serial-b"]


def test_off_ignores_the_budget_seed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pixi.toml").write_text(_pixi(FIVE), encoding="utf-8")
    _budgets(repo, {"serial-d": 900.0})
    order, _workers, code = _run(repo, jobs=1, cores=16, critical=False)
    assert code == preflight.EXIT_OK
    assert order == list(FIVE)


def test_a_missing_or_unreadable_budgets_file_seeds_nothing(tmp_path: Path) -> None:
    assert preflight.budget_seed_seconds(tmp_path) == {}
    path = tmp_path / preflight.BUDGETS_RELATIVE
    path.parent.mkdir(parents=True)
    path.write_text("[lanes\n", encoding="utf-8")
    assert preflight.budget_seed_seconds(tmp_path) == {}
    path.write_text('[lanes]\n"no-environment" = 5\n"flag@env" = true\n"task@env" = 7\n', encoding="utf-8")
    assert preflight.budget_seed_seconds(tmp_path) == {("task", "env"): 7.0}


def test_xdist_share_follows_the_expected_work() -> None:
    share = preflight_xdist.xdist_share_at_admission
    assert share(free_cores=16, pending_xdist=4, logical_cores=16, weight=600.0, pending_weight=800.0) == 12
    assert share(free_cores=16, pending_xdist=4, logical_cores=16, weight=20.0, pending_weight=800.0) == 2  # the floor
    assert share(free_cores=1, pending_xdist=4, logical_cores=16, weight=600.0, pending_weight=800.0) == 0  # waits
    assert share(free_cores=8, pending_xdist=1, logical_cores=4, weight=1.0, pending_weight=1.0) == 4  # the machine
    assert (
        share(free_cores=3, pending_xdist=2, logical_cores=16, weight=900.0, pending_weight=1000.0) == 3
    )  # the free cores
    # no work known for the pending lanes: the even split of Story 117.3
    assert share(free_cores=6, pending_xdist=3, logical_cores=16, weight=0.0, pending_weight=0.0) == 2


def test_on_three_xdist_lanes_split_the_cores_by_their_expected_seconds(tmp_path: Path) -> None:
    """With no workers journaled a lane's work is its expected seconds at the minimum share, so shares follow seconds."""
    repo = tmp_path / "repo"
    repo.mkdir()
    lanes = {
        "small": "pytest small -q -n auto",
        "big": "pytest big -q -n auto",
        "mid": "pytest mid -q -n auto",
        "s1": "pytest s1 -q",
    }
    (repo / "pixi.toml").write_text(_pixi(lanes), encoding="utf-8")
    _journal(repo, {"big": 300.0, "mid": 200.0, "small": 100.0, "s1": 5.0})
    workers, peak, code = _weighted_run(repo, cores=16)
    assert code == preflight.EXIT_OK
    # big: 16 * 600/1200 = 8; mid: 8 * 400/600 = 5; small: 3 * 200/200 = 3; the serial lane waits for a core
    assert (workers["big"], workers["mid"], workers["small"]) == (8, 5, 3)
    assert peak <= 16, workers


def test_on_the_share_follows_journaled_work_not_seconds(tmp_path: Path) -> None:
    """Two lanes that took the same seconds, one on eight workers and one on two: the first did four times the work."""
    repo = tmp_path / "repo"
    repo.mkdir()
    lanes = {"wide": "pytest wide -q -n auto", "narrow": "pytest narrow -q -n auto"}
    (repo / "pixi.toml").write_text(_pixi(lanes), encoding="utf-8")
    rows = []
    for index in range(3):
        rows.append(
            {
                "run_id": f"r{index}",
                "verdict": "ok",
                "total_seconds": 100.0,
                "lanes": [
                    {
                        "task": "wide",
                        "environment": INV,
                        "seconds": 100.0,
                        "status": "ok",
                        "exit_code": 0,
                        "xdist_workers": 8,
                    },
                    {
                        "task": "narrow",
                        "environment": INV,
                        "seconds": 100.0,
                        "status": "ok",
                        "exit_code": 0,
                        "xdist_workers": 2,
                    },
                ],
            }
        )
    path = repo / preflight.JOURNAL_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    assert preflight.lane_work_medians(path) == {("wide", INV): 800.0, ("narrow", INV): 200.0}
    workers, peak, code = _weighted_run(repo, cores=16)
    assert code == preflight.EXIT_OK
    assert (workers["wide"], workers["narrow"]) == (13, 3)  # 16 * 800/1000, then the three cores left
    assert peak <= 16


def test_work_medians_skip_red_runs_and_lanes_without_workers(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    rows = [
        {
            "verdict": "ok",
            "lanes": [{"task": "x", "environment": INV, "seconds": 10.0, "status": "ok", "xdist_workers": 4}],
        },
        {"verdict": "ok", "lanes": [{"task": "serial", "environment": INV, "seconds": 10.0, "status": "ok"}]},
        {
            "verdict": "red",
            "lanes": [{"task": "x", "environment": INV, "seconds": 999.0, "status": "ok", "xdist_workers": 4}],
        },
        {
            "verdict": "ok",
            "lanes": [{"task": "x", "environment": INV, "seconds": 999.0, "status": "red", "xdist_workers": 4}],
        },
        {
            "verdict": "ok",
            "lanes": [{"task": "x", "environment": INV, "seconds": 5.0, "status": "ok", "xdist_workers": True}],
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\nnot json\n", encoding="utf-8")
    assert preflight.lane_work_medians(path) == {("x", INV): 40.0}
    assert preflight.lane_work_medians(tmp_path / "missing.jsonl") == {}


def test_a_run_journals_the_workers_each_xdist_lane_ran_on(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pixi.toml").write_text(_pixi(FIVE), encoding="utf-8")
    _order, _workers, code = _run(repo, jobs=1, cores=16, critical=True)
    assert code == preflight.EXIT_OK
    lines = (repo / preflight.JOURNAL_RELATIVE).read_text(encoding="utf-8").splitlines()
    run = next(row for row in map(json.loads, reversed(lines)) if "lanes" in row)
    by_task = {lane["task"]: lane for lane in run["lanes"]}
    assert by_task["xdist-suite"]["xdist_workers"] == 16
    assert "xdist_workers" not in by_task["serial-a"]


def test_a_crowded_run_sizes_a_heavy_lane_by_the_target_seconds() -> None:
    """Twelve lanes pending on sixteen free cores cannot all start: a heavy lane takes the workers that end its work
    in the target time, not the two a proportional split leaves it. Lanes that all fit keep the proportional split."""
    share = preflight_xdist.xdist_share_at_admission
    crowded = {"free_cores": 16, "pending_xdist": 12, "logical_cores": 16, "pending_weight": 6000.0}
    assert share(**crowded, weight=900.0) == 2
    assert share(**crowded, weight=900.0, target_seconds=200.0) == 5
    assert share(**crowded, weight=100.0, target_seconds=200.0) == 2  # a light lane keeps the floor
    assert share(**crowded, weight=9000.0, target_seconds=200.0) == 16  # never above the free cores
    assert share(**{**crowded, "free_cores": 3}, weight=900.0, target_seconds=200.0) == 3
    fits = {"free_cores": 16, "pending_xdist": 3, "logical_cores": 16, "pending_weight": 1200.0}
    assert share(**fits, weight=600.0, target_seconds=10.0) == 8  # side by side: the proportional split stands


def test_the_docs_site_lanes_compete_by_what_is_left_of_their_chain() -> None:
    """The docs-site lanes run one at a time: a three-second install in front of a five-minute suite goes before a
    hundred-second lane. With no seconds known for any of them, every lane keeps its declared turn."""
    long_lane = preflight.Lane("serial-long", INV)
    install = preflight.Lane("docs-site-install", "site")
    herald = preflight.Lane("pyforge-herald-live-test", "pyforge-herald")
    lanes = [long_lane, install, herald]
    pending = {(lane.task, lane.environment): lane for lane in lanes}
    expected = {
        ("serial-long", INV): 100.0,
        ("docs-site-install", "site"): 3.0,
        herald.task and (herald.task, herald.environment): 300.0,
    }
    assert preflight._next_lane([long_lane, install], lanes, pending, 1, expected) is install
    del pending[(install.task, install.environment)]
    assert preflight._next_lane([long_lane, herald], lanes, pending, 2, expected) is herald
    # The chain's last lane, alone, competes by its own seconds.
    short_tail = {**expected, (herald.task, herald.environment): 40.0}
    assert preflight._next_lane([long_lane, herald], lanes, pending, 2, short_tail) is long_lane
    # No history: equal weights, declared turns.
    pending = {(lane.task, lane.environment): lane for lane in lanes}
    assert preflight._next_lane([long_lane, install], lanes, pending, 1, {}) is long_lane


def test_work_medians_prefer_the_cpu_a_lane_measured(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    lanes = [
        {
            "task": "built",
            "environment": INV,
            "seconds": 300.0,
            "status": "ok",
            "xdist_workers": 8,
            "cpu_seconds": 420.5,
        },
        {"task": "wide", "environment": INV, "seconds": 100.0, "status": "ok", "xdist_workers": 8},
        {"task": "serial", "environment": INV, "seconds": 50.0, "status": "ok", "cpu_seconds": 190.0},
        {"task": "bad", "environment": INV, "seconds": 50.0, "status": "ok", "cpu_seconds": float("nan")},
    ]
    path.write_text(json.dumps({"run_id": "r", "verdict": "ok", "lanes": lanes}) + "\n", encoding="utf-8")
    assert preflight.lane_work_medians(path) == {
        ("built", INV): 420.5,  # not 2400: seven of its eight workers had nothing to build
        ("wide", INV): 800.0,
        ("serial", INV): 190.0,  # a lane that runs its own processes, measured
    }


def test_the_tracked_work_table_seeds_an_xdist_lane_s_share(tmp_path: Path) -> None:
    path = tmp_path / preflight.BUDGETS_RELATIVE
    path.parent.mkdir(parents=True)
    path.write_text(
        '[lanes]\n"a@e" = 10\n[work]\n"a@e" = 640\n"b@e" = inf\n"c@e" = -4\n"d@e" = nan\n"plain" = 3\n',
        encoding="utf-8",
    )
    assert preflight.budget_seed_seconds(tmp_path) == {("a", "e"): 10.0}
    assert preflight.budget_seed_work(tmp_path) == {("a", "e"): 640.0}
    assert preflight.budget_seed_work(tmp_path / "missing") == {}
    assert preflight._expected_work(("a", "e"), {("a", "e"): 10.0}, preflight.budget_seed_work(tmp_path)) == 640.0


def test_a_reaped_lane_reports_its_exit_code_and_the_cpu_it_used() -> None:
    import subprocess
    import sys

    burn = "import time\nend = time.process_time() + 0.3\nwhile time.process_time() < end:\n    pass\n"
    done = subprocess.Popen([sys.executable, "-c", burn])  # noqa: S603
    code, cpu = preflight._wait_measuring_cpu(done)
    assert code == 0
    assert cpu is not None and 0.25 <= cpu < 5.0
    failed = subprocess.Popen([sys.executable, "-c", "import sys; sys.exit(3)"])  # noqa: S603
    code, _cpu = preflight._wait_measuring_cpu(failed)
    assert code == 3
    # Reaped elsewhere first (a stop that terminates the lanes): the code Popen holds is returned, no CPU claimed.
    gone = subprocess.Popen([sys.executable, "-c", "import sys; sys.exit(4)"])  # noqa: S603
    assert gone.wait() == 4
    assert preflight._wait_measuring_cpu(gone) == (4, None)


def test_on_one_core_an_xdist_lane_still_starts(tmp_path: Path) -> None:
    """Fewer free cores than the minimum share and nothing in flight to free one: the lane starts, it does not wait."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pixi.toml").write_text(_pixi({"x1": "pytest x1 -q -n auto", "s1": "pytest s1 -q"}), encoding="utf-8")
    order, workers, code = _run(repo, jobs=1, cores=1, critical=True)
    assert code == preflight.EXIT_OK
    assert sorted(order) == ["s1", "x1"]
    assert workers["x1"] == str(preflight_xdist.MIN_XDIST_WORKERS)
