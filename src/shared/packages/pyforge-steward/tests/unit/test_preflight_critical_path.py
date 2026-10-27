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
    static = preflight_xdist.lane_xdist_worker_map(
        lanes=[(task, INV) for task in FIVE], pixi_data={"feature": {}}, logical_cores=16, pool_jobs=1
    )
    assert workers["xdist-suite"] == str(static.get(("xdist-suite", INV), 16))


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
