"""Unit tests for concurrent pr-preflight (Story 71.3, spec-pyforge-steward CAP-159)."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from pyforge.steward import preflight
from pyforge.steward import preflight_suite_reduction as psr

_NOOP_INSTALL = lambda _env: 0  # noqa: E731


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _git(repo: Path, *args: str) -> None:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    for leaked in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(leaked, None)
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
        cwd=repo,
        env=env,
        check=True,
        capture_output=True,
    )


def _mini_pixi(*tasks: str) -> str:
    body = "[feature.guild-tasks.tasks.pr-preflight-lanes]\ndepends-on = [\n"
    body += ",\n".join(f'  "{name}"' for name in tasks)
    body += "\n]\n\n"
    for name in tasks:
        body += f'[feature.guild-tasks.tasks.{name}]\ncmd = "true"\n\n'
    return body


def _run_records(repo: Path) -> list[dict]:
    path = repo / preflight.JOURNAL_RELATIVE
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _run_record(repo: Path) -> dict:
    return next(record for record in reversed(_run_records(repo)) if "lanes" in record)


def _key(task: str) -> preflight.LaneKey:
    """A bare lane's ``(task, environment)``: it runs in the invoking environment (Story 103.5)."""
    return (task, preflight._invoking_environment())  # noqa: SLF001


def _lane_dir(task: str) -> str:
    """A bare lane's scratch directory name, ``<task>@<environment>`` (Story 103.5)."""
    return preflight.lane_label(*_key(task))


def test_three_sleeping_lanes_finish_under_two_seconds_with_overlapping_offsets(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("a", "b", "c"))

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        time.sleep(1)
        ctx.log_path.write_text(f"lane {ctx.lane.task}\n", encoding="utf-8")
        return 0

    t0 = time.monotonic()
    code = preflight.run_preflight(
        repo,
        jobs=3,
        install_environment=_NOOP_INSTALL,
        run_lane_ctx=run_ctx,
    )
    elapsed = time.monotonic() - t0
    assert code == preflight.EXIT_OK
    assert elapsed < 2.0
    record = _run_record(repo)
    offsets = [entry["start_offset"] for entry in record["lanes"] if entry["status"] == "ok"]
    assert len(offsets) == 3
    assert max(offsets) - min(offsets) < 0.5


def test_each_lane_gets_isolated_scratch_env(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("a", "b"))

    seen: dict[str, dict[str, str]] = {}

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        seen[ctx.lane.task] = {
            "TMPDIR": ctx.env["TMPDIR"],
            "COVERAGE_FILE": ctx.env["COVERAGE_FILE"],
            "PYTEST_ADDOPTS": ctx.env["PYTEST_ADDOPTS"],
        }
        assert ctx.scratch_dir.is_dir() or ctx.scratch_dir.parent.exists()
        return 0

    assert (
        preflight.run_preflight(repo, jobs=2, install_environment=_NOOP_INSTALL, run_lane_ctx=run_ctx)
        == preflight.EXIT_OK
    )
    assert len(seen) == 2
    values = list(seen.values())
    assert values[0]["TMPDIR"] != values[1]["TMPDIR"]
    assert values[0]["COVERAGE_FILE"] != values[1]["COVERAGE_FILE"]
    repo_resolved = repo.resolve()
    roots = {Path(values[0]["TMPDIR"]).resolve().parent, Path(values[1]["TMPDIR"]).resolve().parent}
    assert len(roots) == 1
    shared_root = next(iter(roots))
    assert not shared_root.is_relative_to(repo_resolved)
    assert not (repo / ".steward" / "preflight").exists()


def test_install_phase_runs_before_lanes_and_is_journaled(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(
        repo / "pixi.toml",
        "[feature.guild-tasks.tasks.pr-preflight-lanes]\n"
        'depends-on = ["a", { task = "b", environment = "other-env" }]\n'
        '[feature.guild-tasks.tasks.a]\ncmd = "true"\n'
        '[feature.other-env.tasks.b]\ncmd = "true"\n',
    )
    order: list[str] = []

    def install(env: str) -> int:
        order.append(f"install:{env}")
        return 0

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        order.append(f"lane:{ctx.lane.task}")
        return 0

    assert (
        preflight.run_preflight(
            repo,
            jobs=2,
            invoking_env="pyforge-guild",
            install_environment=install,
            run_lane_ctx=run_ctx,
        )
        == 0
    )
    assert order.index("install:pyforge-guild") < order.index("lane:a")
    assert order.index("install:other-env") < order.index("lane:b")
    install_calls = [item for item in order if item.startswith("install:")]
    assert install_calls == ["install:pyforge-guild", "install:other-env"]
    install_record = next(r for r in _run_records(repo) if r.get("phase") == "install")
    assert install_record["verdict"] == "ok"
    assert set(install_record["environments"]) == {"pyforge-guild", "other-env"}


def test_red_lane_cancels_others(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("a", "b", "c"))
    started = threading.Event()
    release = threading.Event()

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        if ctx.lane.task == "a":
            return 1
        if ctx.lane.task == "b":
            started.set()
            release.wait(timeout=5)
        time.sleep(0.2)
        return 0

    # Two workers, so `c` is still queued when `a` stops the run (Story 71.10 journals every lane
    # that started from its own result; with three workers `c` could start and finish `ok`).
    code = preflight.run_preflight(
        repo,
        jobs=2,
        install_environment=_NOOP_INSTALL,
        run_lane_ctx=run_ctx,
        scratch_parent=tmp_path / "scratch",
    )
    assert code == preflight.EXIT_LANE_RED
    record = _run_record(repo)
    statuses = {entry["task"]: entry["status"] for entry in record["lanes"]}
    assert statuses["a"] == "red"
    assert statuses["c"] in {"cancelled", "not-run"}


def test_keep_going_runs_every_lane_and_names_reds(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("a", "b", "c"))

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        return 1 if ctx.lane.task in {"a", "c"} else 0

    code = preflight.run_preflight(
        repo,
        jobs=3,
        keep_going=True,
        install_environment=_NOOP_INSTALL,
        run_lane_ctx=run_ctx,
        scratch_parent=tmp_path / "scratch",
    )
    assert code == preflight.EXIT_LANE_RED
    record = _run_record(repo)
    assert all(entry["status"] in {"ok", "red"} for entry in record["lanes"])
    err = capsys.readouterr().err
    assert "red lane 'a'" in err
    assert "red lane 'c'" in err
    assert "lane logs and scratch kept at" in err


def test_lane_logs_are_contiguous_blocks(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("a", "b"))

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        ctx.log_path.write_text("\n".join(f"{ctx.lane.task}-line-{i}" for i in range(5)) + "\n", encoding="utf-8")
        return 0

    assert preflight.run_preflight(repo, jobs=2, install_environment=_NOOP_INSTALL, run_lane_ctx=run_ctx) == 0
    out = capsys.readouterr().out
    assert "a-line-0" in out and "a-line-4" in out
    assert "b-line-0" in out and "b-line-4" in out
    assert out.index("a-line-4") < out.index("b-line-0") or out.index("b-line-4") < out.index("a-line-0")


def test_service_lanes_never_overlap(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _write(
        repo / ".github/workflows/w.yml",
        "on:\n  pull_request:\n    paths: ['**']\n"
        "jobs:\n"
        "  svc-a:\n    services:\n      postgres:\n        image: pgvector/pgvector:pg17\n"
        "    steps:\n      - run: pixi run --frozen -e pyforge-guild lane-a\n"
        "  svc-b:\n    services:\n      postgres:\n        image: pgvector/pgvector:pg17\n"
        "    steps:\n      - run: pixi run --frozen -e pyforge-guild lane-b\n",
    )
    _write(
        repo / "pixi.toml",
        "[feature.guild-tasks.tasks.pr-preflight-lanes]\n"
        'depends-on = ["lane-a", "lane-b"]\n'
        '[feature.guild-tasks.tasks.lane-a]\ncmd = "true"\n'
        '[feature.guild-tasks.tasks.lane-b]\ncmd = "true"\n',
    )
    _write(repo / "touch.txt", "x\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(repo, "checkout", "-q", "-b", "feature")
    _write(repo / "touch.txt", "y\n")
    _git(repo, "add", "touch.txt")
    _git(repo, "commit", "-q", "-m", "branch")

    intervals: list[tuple[str, float, float]] = []
    lock = threading.Lock()

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        start = time.monotonic()
        time.sleep(0.4)
        end = time.monotonic()
        with lock:
            intervals.append((ctx.lane.task, start, end))
        return 0

    assert preflight.run_preflight(repo, jobs=4, install_environment=_NOOP_INSTALL, run_lane_ctx=run_ctx) == 0
    assert len(intervals) == 2
    (_, a0, a1), (_, b0, b1) = sorted(intervals, key=lambda row: row[0])
    assert a1 <= b0 or b1 <= a0


def test_install_failure_short_circuits_before_lanes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("a"))

    def install(_env: str) -> int:
        return 42

    code = preflight.run_preflight(repo, install_environment=install)
    assert code == preflight.EXIT_LANE_RED
    install_record = next(r for r in _run_records(repo) if r.get("phase") == "install")
    assert install_record["verdict"] == "red"
    assert install_record["exit_code"] == 42
    assert not (repo / preflight.JOURNAL_RELATIVE).read_text(encoding="utf-8").count('"lanes"')


def test_lane_runner_exception_counts_as_red(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("a"))

    def run_ctx(_ctx: preflight.LaneRunContext) -> int:
        raise RuntimeError("boom")

    code = preflight.run_preflight(
        repo,
        jobs=1,
        install_environment=_NOOP_INSTALL,
        run_lane_ctx=run_ctx,
        scratch_parent=tmp_path / "scratch",
    )
    assert code == preflight.EXIT_LANE_RED
    record = _run_record(repo)
    assert record["lanes"][0]["status"] == "red"


def _capture_coordinators(monkeypatch: pytest.MonkeyPatch) -> list[preflight._RunCoordinator]:
    """Record each run's coordinator, so a test can read `red_lanes` and the terminated marks."""
    created: list[preflight._RunCoordinator] = []
    real = preflight._RunCoordinator  # noqa: SLF001

    def make(*args: Any, **kwargs: Any) -> preflight._RunCoordinator:
        coord = real(*args, **kwargs)
        created.append(coord)
        return coord

    monkeypatch.setattr(preflight, "_RunCoordinator", make)
    return created


def _started_then(then: str, *, setup: str = "") -> str:
    """A lane script: run `setup`, write its process group id and a `started` marker in its
    scratch dir (TMPDIR), then run `then`."""
    return (
        "import os, signal, sys, time\n"
        f"{setup}\n"
        "tmp = os.environ['TMPDIR']\n"
        "with open(os.path.join(tmp, 'pgid'), 'w') as handle:\n"
        "    handle.write(str(os.getpgrp()))\n"
        "with open(os.path.join(tmp, 'started'), 'w') as handle:\n"
        "    handle.write('1')\n"
        f"{then}\n"
    )


def _after_peer_started(peer: str, then: str) -> str:
    """A lane script: wait (10 s at most) for lane `peer`'s `started` marker, then run `then`."""
    return (
        "import os, sys, time\n"
        f"marker = os.path.join(os.path.dirname(os.environ['TMPDIR']), {_lane_dir(peer)!r}, 'started')\n"
        "deadline = time.monotonic() + 10\n"
        "while not os.path.exists(marker) and time.monotonic() < deadline:\n"
        "    time.sleep(0.02)\n"
        f"{then}\n"
    )


_SLEEP_30 = _started_then("time.sleep(30)")
_FAIL_HALF_SECOND_LATER = "time.sleep(0.5)\nsys.exit(1)"


def _argv_from(scripts: dict[str, str]) -> Callable[[preflight.Lane], list[str]]:
    return lambda lane: [sys.executable, "-c", scripts[lane.task]]


def _scratch_root(tmp_path: Path) -> Path:
    roots = list((tmp_path / "scratch").glob("pyforge-preflight-*"))
    assert len(roots) == 1
    return roots[0]


def _assert_group_gone(scratch_root: Path, task: str) -> None:
    pgid = int((scratch_root / _lane_dir(task) / "pgid").read_text(encoding="utf-8"))
    with pytest.raises(ProcessLookupError):
        os.killpg(pgid, 0)


def _send_sigint_once_started(scratch_parent: Path, tasks: tuple[str, ...]) -> threading.Thread:
    def interrupt() -> None:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            roots = list(scratch_parent.glob("pyforge-preflight-*"))
            if roots and all((roots[0] / _lane_dir(task) / "started").is_file() for task in tasks):
                os.kill(os.getpid(), signal.SIGINT)
                return
            time.sleep(0.05)

    thread = threading.Thread(target=interrupt, daemon=True)
    thread.start()
    return thread


def test_real_subprocess_red_lane_cancels_running_peer(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC (1): the lane that failed is red; the lane its stop terminated is cancelled."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("fail", "sleep"))
    coords = _capture_coordinators(monkeypatch)
    scripts = {"fail": _after_peer_started("sleep", _FAIL_HALF_SECOND_LATER), "sleep": _SLEEP_30}
    t0 = time.monotonic()
    code = preflight.run_preflight(
        repo,
        jobs=2,
        install_environment=_NOOP_INSTALL,
        scratch_parent=tmp_path / "scratch",
        subprocess_argv_for_lane=_argv_from(scripts),
    )
    elapsed = time.monotonic() - t0
    assert code == preflight.EXIT_LANE_RED
    assert elapsed < 10.0
    record = _run_record(repo)
    assert record["verdict"] == "red"
    by_task = {entry["task"]: entry for entry in record["lanes"]}
    assert by_task["fail"]["status"] == "red"
    assert by_task["fail"]["exit_code"] == 1
    assert by_task["fail"]["seconds"] > 0
    assert "cancelled_by" not in by_task["fail"]
    assert by_task["sleep"]["status"] == "cancelled"
    assert by_task["sleep"]["exit_code"] < 0
    assert by_task["sleep"]["seconds"] > 0
    assert by_task["sleep"]["cancelled_by"] == "fail"
    assert by_task["sleep"]["cancelled_by_environment"] == _key("fail")[1]  # the red lane's environment (Story 103.5)
    (coord,) = coords
    assert coord.red_lanes == [_key("fail")]
    assert coord.terminated_lanes == {_key("sleep")}
    assert coord.stop_trigger == "fail"
    assert coord.stop_cause == _key("fail")
    err = capsys.readouterr().err
    assert "lane 'fail' in environment" in err
    assert "lane 'sleep'" not in err
    _assert_group_gone(_scratch_root(tmp_path), "sleep")


def test_terminated_lane_that_exits_zero_is_cancelled_not_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A lane the stop signalled is `cancelled` whatever it exits with -- here 0 from its own SIGTERM handler."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("fail", "graceful"))
    coords = _capture_coordinators(monkeypatch)
    scripts = {
        "fail": _after_peer_started("graceful", _FAIL_HALF_SECOND_LATER),
        "graceful": _started_then(
            "time.sleep(30)",
            setup="signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))",
        ),
    }
    code = preflight.run_preflight(
        repo,
        jobs=2,
        install_environment=_NOOP_INSTALL,
        scratch_parent=tmp_path / "scratch",
        subprocess_argv_for_lane=_argv_from(scripts),
    )
    assert code == preflight.EXIT_LANE_RED
    by_task = {entry["task"]: entry for entry in _run_record(repo)["lanes"]}
    assert by_task["fail"]["status"] == "red"
    assert by_task["graceful"]["status"] == "cancelled"
    assert by_task["graceful"]["exit_code"] == 0
    assert by_task["graceful"]["seconds"] > 0
    assert by_task["graceful"]["cancelled_by"] == "fail"
    (coord,) = coords
    assert coord.red_lanes == [_key("fail")]


def test_lane_that_exits_on_its_own_during_a_stop_stays_red(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC (3): a lane process already exited 2 when the stop polls it is not marked, and stays red."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("fail", "own"))
    coords = _capture_coordinators(monkeypatch)
    real_run = preflight._run_pixi_argv  # noqa: SLF001
    own_exited = threading.Event()

    def run_argv(coord: Any, ctx: preflight.LaneRunContext, argv: list[str], log_handle: Any) -> int:
        if ctx.lane.task == "fail":
            assert own_exited.wait(timeout=10)
            return real_run(coord, ctx, argv, log_handle)
        proc = subprocess.Popen(
            argv,
            cwd=coord.repo_root,
            env=ctx.env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        coord.register_proc(proc, preflight._lane_key(ctx.lane))  # noqa: SLF001
        try:
            code = proc.wait()
            own_exited.set()
            # Hand the exit back only once the culprit has stopped the run, so its
            # terminate_children() finds this process registered and already exited.
            assert coord.stop_on_red.wait(timeout=10)
            return code
        finally:
            coord.unregister_proc(proc)

    monkeypatch.setattr(preflight, "_run_pixi_argv", run_argv)
    code = preflight.run_preflight(
        repo,
        jobs=2,
        install_environment=_NOOP_INSTALL,
        scratch_parent=tmp_path / "scratch",
        subprocess_argv_for_lane=_argv_from({"fail": "raise SystemExit(1)", "own": "raise SystemExit(2)"}),
    )
    assert code == preflight.EXIT_LANE_RED
    by_task = {entry["task"]: entry for entry in _run_record(repo)["lanes"]}
    assert by_task["fail"]["status"] == "red"
    assert by_task["fail"]["exit_code"] == 1
    assert by_task["own"]["status"] == "red"
    assert by_task["own"]["exit_code"] == 2
    assert "cancelled_by" not in by_task["fail"]
    assert "cancelled_by" not in by_task["own"]
    (coord,) = coords
    assert coord.red_lanes == [_key("fail"), _key("own")]
    assert coord.terminated_lanes == set()
    assert coord.stop_trigger == "fail"
    err = capsys.readouterr().err
    assert "lane 'fail' in environment" in err
    assert "lane 'own' in environment" in err


def test_lanes_running_at_a_stop_are_journaled_from_their_own_results(tmp_path: Path) -> None:
    """With no process to terminate, a lane that was running when the run stopped keeps its own outcome."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("a", "b", "c"))
    started = {"b": threading.Event(), "c": threading.Event()}

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        if ctx.lane.task == "a":
            assert started["b"].wait(timeout=5)
            assert started["c"].wait(timeout=5)
            return 1
        started[ctx.lane.task].set()
        time.sleep(0.3)
        if ctx.lane.task == "c":
            raise RuntimeError("c failed on its own")
        return 0

    code = preflight.run_preflight(
        repo,
        jobs=3,
        install_environment=_NOOP_INSTALL,
        run_lane_ctx=run_ctx,
        scratch_parent=tmp_path / "scratch",
    )
    assert code == preflight.EXIT_LANE_RED
    by_task = {entry["task"]: entry for entry in _run_record(repo)["lanes"]}
    assert by_task["a"]["status"] == "red"
    assert by_task["b"]["status"] == "ok"
    assert by_task["b"]["seconds"] >= 0.3
    assert by_task["c"]["status"] == "red"
    assert by_task["c"]["exit_code"] == 1
    assert all("cancelled_by" not in entry for entry in by_task.values())


@pytest.mark.skipif(not hasattr(signal, "SIGINT"), reason="SIGINT required")
def test_sigint_cancels_real_subprocess_lanes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC (2): an interrupt cancels every running lane, `cancelled_by: interrupt`, and exits 130."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("sleep-a", "sleep-b"))
    coords = _capture_coordinators(monkeypatch)
    sender = _send_sigint_once_started(tmp_path / "scratch", ("sleep-a", "sleep-b"))
    code = preflight.run_preflight(
        repo,
        jobs=2,
        install_environment=_NOOP_INSTALL,
        scratch_parent=tmp_path / "scratch",
        subprocess_argv_for_lane=_argv_from({"sleep-a": _SLEEP_30, "sleep-b": _SLEEP_30}),
    )
    sender.join(timeout=5)
    assert code == preflight.EXIT_INTERRUPT
    record = _run_record(repo)
    assert record["verdict"] == "interrupted"
    assert {entry["task"] for entry in record["lanes"]} == {"sleep-a", "sleep-b"}
    for entry in record["lanes"]:
        assert entry["status"] == "cancelled"
        assert entry["exit_code"] < 0
        assert entry["seconds"] > 0
        assert entry["cancelled_by"] == "interrupt"
        assert "cancelled_by_environment" not in entry  # an interrupt is no lane (Story 103.5 AC4)
    (coord,) = coords
    assert coord.red_lanes == []
    assert coord.stop_trigger == "interrupt"
    assert coord.stop_cause == ("interrupt", None)
    scratch_root = _scratch_root(tmp_path)
    _assert_group_gone(scratch_root, "sleep-a")
    _assert_group_gone(scratch_root, "sleep-b")


@pytest.mark.skipif(not hasattr(signal, "SIGINT"), reason="SIGINT required")
def test_sigint_names_interrupt_on_a_never_started_lane(tmp_path: Path) -> None:
    """An interrupted run journals the lane it terminated `cancelled_by: interrupt`, and a lane that
    never started `cancelled`, exit 0, 0 s, also `cancelled_by: interrupt` (Story 71.12, replacing
    Story 71.10 AC (4)'s no `cancelled_by`)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("first", "second"))
    sender = _send_sigint_once_started(tmp_path / "scratch", ("first",))
    code = preflight.run_preflight(
        repo,
        jobs=1,
        install_environment=_NOOP_INSTALL,
        scratch_parent=tmp_path / "scratch",
        subprocess_argv_for_lane=_argv_from({"first": _SLEEP_30, "second": _SLEEP_30}),
    )
    sender.join(timeout=5)
    assert code == preflight.EXIT_INTERRUPT
    record = _run_record(repo)
    assert record["verdict"] == "interrupted"
    by_task = {entry["task"]: entry for entry in record["lanes"]}
    assert by_task["first"]["status"] == "cancelled"
    assert by_task["first"]["exit_code"] < 0
    assert by_task["first"]["cancelled_by"] == "interrupt"
    assert by_task["second"]["status"] == "cancelled"
    assert by_task["second"]["exit_code"] == 0
    assert by_task["second"]["seconds"] == 0.0
    assert by_task["second"]["cancelled_by"] == "interrupt"
    assert "cancelled_by_environment" not in by_task["second"]  # an interrupt is no lane (Story 103.5 AC4)
    _assert_group_gone(_scratch_root(tmp_path), "first")


def test_terminate_children_marks_only_a_process_it_signals(tmp_path: Path) -> None:
    """AC (3) at the coordinator: an already-exited process is skipped; a live one is marked and killed."""
    repo = tmp_path / "repo"
    repo.mkdir()
    exited = subprocess.Popen(
        [sys.executable, "-c", "raise SystemExit(2)"],
        start_new_session=True,
    )
    exited.wait(timeout=5)
    assert exited.returncode == 2
    running = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        start_new_session=True,
    )
    coord = preflight._RunCoordinator(  # noqa: SLF001
        repo_root=repo,
        run_id="t",
        run_start=0.0,
        jobs=1,
        keep_going=False,
    )
    coord.register_proc(exited, ("culprit", "env"))
    coord.register_proc(running, ("running", "env"))
    try:
        coord.terminate_children()
        assert running.wait(timeout=5) < 0
    finally:
        if running.poll() is None:
            running.kill()
            running.wait(timeout=5)
    assert coord.terminated_lanes == {("running", "env")}
    assert exited.returncode == 2


def test_jobs_one_never_started_lanes_name_the_red_lane(tmp_path: Path) -> None:
    """AC (4): with one worker, the lanes the stop kept from starting stay `cancelled`, exit 0, 0 s, and
    name the red lane (Story 71.12 replaced 71.10's no `cancelled_by`)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("fail", "b", "c"))
    scripts = {"fail": "raise SystemExit(1)", "b": "import time; time.sleep(30)", "c": "import time; time.sleep(30)"}
    code = preflight.run_preflight(
        repo,
        jobs=1,
        install_environment=_NOOP_INSTALL,
        scratch_parent=tmp_path / "scratch",
        subprocess_argv_for_lane=_argv_from(scripts),
    )
    assert code == preflight.EXIT_LANE_RED
    record = _run_record(repo)
    by_task = {entry["task"]: entry for entry in record["lanes"]}
    assert by_task["fail"]["status"] == "red"
    for name in ("b", "c"):
        assert by_task[name]["status"] == "cancelled"
        assert by_task[name]["exit_code"] == 0
        assert by_task[name]["seconds"] == 0.0
        assert by_task[name]["cancelled_by"] == "fail"
        assert by_task[name]["cancelled_by_environment"] == by_task["fail"]["environment"]


def _bare_coordinator(repo: Path) -> preflight._RunCoordinator:  # noqa: SLF001
    return preflight._RunCoordinator(  # noqa: SLF001
        repo_root=repo,
        run_id="t",
        run_start=0.0,
        jobs=1,
        keep_going=False,
    )


@pytest.mark.parametrize(
    ("recorded", "expected"),
    [(None, ("interrupt", None)), (("interrupt", None), ("interrupt", None)), (("fail", "env"), ("fail", "env"))],
)
def test_a_lane_the_pool_turns_away_on_an_interrupt_names_the_cause(
    tmp_path: Path, recorded: tuple[str, str | None] | None, expected: tuple[str, str | None]
) -> None:
    """Story 71.12 AC (3): the pool's first interrupt check names the first recorded cause, `interrupt` before one."""
    coord = _bare_coordinator(tmp_path)
    if recorded is not None:
        coord.set_stop_cause(recorded)
    coord.cancel.set()
    ran: list[preflight.LaneRunContext] = []
    result = preflight._run_lane_in_pool(  # noqa: SLF001
        coord, preflight.Lane("late", "env"), tmp_path / "scratch", (), lambda ctx: ran.append(ctx) or 0, False
    )
    assert ran == []
    assert (result.status, result.exit_code, result.seconds) == ("cancelled", 0, 0.0)
    assert (result.cancelled_by, result.cancelled_by_environment) == expected


class _InterruptOnAcquire:
    """A service lock whose acquisition is where SIGINT lands: the lane passed the first check, then waited."""

    def __init__(self, coord: preflight._RunCoordinator, recorded: tuple[str, str | None] | None) -> None:  # noqa: SLF001
        self.coord = coord
        self.recorded = recorded

    def acquire(self) -> bool:
        if self.recorded is not None:
            self.coord.set_stop_cause(self.recorded)
        self.coord.cancel.set()
        return True

    def release(self) -> None:
        pass


@pytest.mark.parametrize(
    ("recorded", "expected"),
    [(None, ("interrupt", None)), (("interrupt", None), ("interrupt", None)), (("fail", "env"), ("fail", "env"))],
)
def test_a_lane_interrupted_while_it_waits_for_its_service_names_the_cause(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    recorded: tuple[str, str | None] | None,
    expected: tuple[str, str | None],
) -> None:
    """Story 71.12 AC (3): the pool's second interrupt check, after the service lock, names the first recorded
    cause, `interrupt` before one."""
    coord = _bare_coordinator(tmp_path)
    monkeypatch.setattr(coord, "mutex_lock", lambda _key: _InterruptOnAcquire(coord, recorded))
    ran: list[preflight.LaneRunContext] = []
    result = preflight._run_lane_in_pool(  # noqa: SLF001
        coord,
        preflight.Lane("late", "env"),
        tmp_path / "scratch",
        ("services:postgres",),
        lambda ctx: ran.append(ctx) or 0,
        False,
    )
    assert ran == []
    assert (result.status, result.exit_code, result.seconds) == ("cancelled", 0, 0.0)
    assert (result.cancelled_by, result.cancelled_by_environment) == expected


@pytest.mark.skipif(not hasattr(signal, "SIGINT"), reason="SIGINT required")
@pytest.mark.parametrize(
    ("keep_going", "status", "field"),
    [(False, "cancelled", "cancelled_by"), (True, "not-run", "blocked_by")],
)
def test_a_dependent_of_a_lane_turned_away_on_an_interrupt_names_interrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, keep_going: bool, status: str, field: str
) -> None:
    """Story 71.12 (review finding 2): after SIGINT the scheduler still submits ready lanes and the pool turns
    them away naming `interrupt`, so a dependent `_mark_dependency_blocked` reaches names `interrupt` too, with no
    environment, where it used to name the dependency itself.

    `x` holds its worker until `z` is journaled; `w` runs the installed SIGINT handler itself, so the interrupt is
    recorded before `w` returns (a real signal waits for the main thread's next bytecode check, which a loaded host
    can hold off past any timeout: the round-2 review); `y` is then submitted and turned away; `z` depends on `y`.
    Every step waits on an event, never on time.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(
        repo / "pixi.toml",
        "[feature.guild-tasks.tasks.pr-preflight-lanes]\n"
        'depends-on = ["x", "w", "z"]\n'
        '[feature.guild-tasks.tasks.x]\ncmd = "true"\n'
        '[feature.guild-tasks.tasks.w]\ncmd = "true"\n'
        '[feature.guild-tasks.tasks.y]\ncmd = "true"\n'
        '[feature.guild-tasks.tasks.z]\ndepends-on = ["y"]\ncmd = "true"\n',
    )
    z_journaled = threading.Event()
    real_blocked = preflight._blocked_lane_result  # noqa: SLF001

    def blocked_lane_result(lane: preflight.Lane, *args: Any, **kwargs: Any) -> preflight.LaneResult:
        result = real_blocked(lane, *args, **kwargs)
        if lane.task == "z":
            z_journaled.set()
        return result

    monkeypatch.setattr(preflight, "_blocked_lane_result", blocked_lane_result)
    ran: list[str] = []

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        ran.append(ctx.lane.task)
        if ctx.lane.task == "x":
            assert z_journaled.wait(timeout=10)
        elif ctx.lane.task == "w":
            handler = signal.getsignal(signal.SIGINT)
            # run_preflight's own handler, never Python's default, whose KeyboardInterrupt would end the session.
            assert callable(handler) and handler.__qualname__.endswith("_on_sigint")
            handler(signal.SIGINT, None)
        return 0

    code = preflight.run_preflight(
        repo,
        jobs=2,
        keep_going=keep_going,
        install_environment=_NOOP_INSTALL,
        run_lane_ctx=run_ctx,
        scratch_parent=tmp_path / "scratch",
    )
    assert code == preflight.EXIT_INTERRUPT
    assert z_journaled.is_set()
    assert sorted(ran) == ["w", "x"]
    by_task = {entry["task"]: entry for entry in _run_record(repo)["lanes"]}
    # A failed wait inside a runner becomes a red lane, not a failed test; these keep a timeout from passing.
    assert (by_task["x"]["status"], by_task["w"]["status"]) == ("ok", "ok")
    assert (by_task["y"]["status"], by_task["y"]["cancelled_by"]) == ("cancelled", "interrupt")
    assert "cancelled_by_environment" not in by_task["y"]
    assert (by_task["z"]["status"], by_task["z"][field]) == (status, "interrupt")
    assert f"{field}_environment" not in by_task["z"]


def test_reduced_lane_cancelled_mid_segment(tmp_path: Path) -> None:
    """AC (5): the running segment of a reduced lane is `cancelled`, the later ones `not-run`."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("fail", "slow"))
    segments = (
        psr.ReducedSuiteSegment("rest-of-task", [sys.executable, "-c", _SLEEP_30]),
        psr.ReducedSuiteSegment("gate-dirs-complement", [sys.executable, "-c", "pass"]),
    )
    override = psr.SuiteLaneOverride(segments=segments, journal={"suite_reduction": True})
    plan = {"slow": override}

    def run_seg(coord: Any, ctx: preflight.LaneRunContext, argv: list[str], log_handle: Any) -> int:
        seg = argv[argv.index("--") + 1 :] if "--" in argv else argv
        proc = subprocess.Popen(
            seg,
            cwd=coord.repo_root,
            env=ctx.env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        coord.register_proc(proc, preflight._lane_key(ctx.lane))  # noqa: SLF001
        try:
            return int(proc.wait())
        finally:
            coord.unregister_proc(proc)

    with patch.object(psr, "build_suite_lane_overrides", return_value=plan):
        with patch.object(preflight, "_run_pixi_argv", side_effect=run_seg):
            code = preflight.run_preflight(
                repo,
                jobs=2,
                install_environment=_NOOP_INSTALL,
                scratch_parent=tmp_path / "scratch",
                subprocess_argv_for_lane=lambda lane: [
                    sys.executable,
                    "-c",
                    _after_peer_started("slow", _FAIL_HALF_SECOND_LATER),
                ],
            )
    assert code == preflight.EXIT_LANE_RED
    record = _run_record(repo)
    slow = next(entry for entry in record["lanes"] if entry["task"] == "slow")
    assert slow["status"] == "cancelled"
    assert slow["cancelled_by"] == "fail"
    rows = {row["label"]: row for row in slow["suite_reduction_segments"]}
    assert rows["rest-of-task"]["outcome"] == "cancelled"
    assert rows["rest-of-task"]["exit_code"] < 0
    assert rows["gate-dirs-complement"]["outcome"] == "not-run"
    assert rows["gate-dirs-complement"]["exit_code"] is None
    _assert_group_gone(_scratch_root(tmp_path), "slow")


def _patch_terminate_children_returned(monkeypatch: pytest.MonkeyPatch) -> threading.Event:
    """Fire after ``terminate_children`` returns (Story 71.11 late-registration tests)."""
    returned = threading.Event()
    coord_cls = preflight._RunCoordinator  # noqa: SLF001 — patch before ``_capture_coordinators`` replaces the class
    real = coord_cls.terminate_children

    def wrapped(self: preflight._RunCoordinator) -> None:
        real(self)
        returned.set()

    monkeypatch.setattr(coord_cls, "terminate_children", wrapped)
    return returned


def _run_pixi_argv_after_dash(coord: Any, ctx: preflight.LaneRunContext, argv: list[str], log_handle: Any) -> int:
    """Run reduced-suite segment argv directly (no pixi in unit tests)."""
    seg = argv[argv.index("--") + 1 :] if "--" in argv else argv
    proc = subprocess.Popen(
        seg,
        cwd=coord.repo_root,
        env=ctx.env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    coord.register_proc(proc, preflight._lane_key(ctx.lane))  # noqa: SLF001
    try:
        return int(proc.wait())
    finally:
        coord.unregister_proc(proc)


def test_late_lane_killed_at_registration_after_stop_on_red(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC (1): a lane past the pool stop check is killed when it registers after ``terminate_children``."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("fail", "peer", "late"))
    terminate_returned = _patch_terminate_children_returned(monkeypatch)
    coords = _capture_coordinators(monkeypatch)
    scripts = {
        "fail": _after_peer_started("peer", _FAIL_HALF_SECOND_LATER),
        "peer": _SLEEP_30,
        "late": _SLEEP_30,
    }

    def before_popen(ctx: preflight.LaneRunContext) -> None:
        if ctx.lane.task == "late":
            assert terminate_returned.wait(timeout=10)

    t0 = time.monotonic()
    code = preflight.run_preflight(
        repo,
        jobs=3,
        install_environment=_NOOP_INSTALL,
        scratch_parent=tmp_path / "scratch",
        subprocess_argv_for_lane=_argv_from(scripts),
        before_popen=before_popen,
    )
    elapsed = time.monotonic() - t0
    assert code == preflight.EXIT_LANE_RED
    assert elapsed < 10.0
    by_task = {entry["task"]: entry for entry in _run_record(repo)["lanes"]}
    assert by_task["late"]["status"] == "cancelled"
    assert by_task["late"]["exit_code"] < 0
    assert by_task["late"]["cancelled_by"] == "fail"
    (coord,) = coords
    assert coord.red_lanes == [_key("fail")]
    _assert_group_gone(_scratch_root(tmp_path), "peer")
    late_pgid = _scratch_root(tmp_path) / _lane_dir("late") / "pgid"
    if late_pgid.is_file():
        _assert_group_gone(_scratch_root(tmp_path), "late")


@pytest.mark.skipif(not hasattr(signal, "SIGINT"), reason="SIGINT required")
def test_late_lane_killed_at_registration_after_sigint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC (2): SIGINT reaches a lane that registers after the interrupt handler ran."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("fail", "peer", "late"))
    coords = _capture_coordinators(monkeypatch)
    scripts = {
        "fail": _after_peer_started("peer", _FAIL_HALF_SECOND_LATER),
        "peer": _SLEEP_30,
        "late": _SLEEP_30,
    }
    sender = _send_sigint_once_started(tmp_path / "scratch", ("peer",))

    def before_popen(ctx: preflight.LaneRunContext) -> None:
        if ctx.lane.task == "late":
            (coord,) = coords
            assert coord.cancel.wait(timeout=10)

    code = preflight.run_preflight(
        repo,
        jobs=3,
        install_environment=_NOOP_INSTALL,
        scratch_parent=tmp_path / "scratch",
        subprocess_argv_for_lane=_argv_from(scripts),
        before_popen=before_popen,
    )
    sender.join(timeout=5)
    assert code == preflight.EXIT_INTERRUPT
    record = _run_record(repo)
    assert record["verdict"] == "interrupted"
    late = next(entry for entry in record["lanes"] if entry["task"] == "late")
    assert late["status"] == "cancelled"
    assert late["cancelled_by"] == "interrupt"
    late_pgid = _scratch_root(tmp_path) / _lane_dir("late") / "pgid"
    if late_pgid.is_file():
        _assert_group_gone(_scratch_root(tmp_path), "late")


def _two_segment_reduced_plan(*, second_body: str = "print('seg-two')") -> dict[str, psr.SuiteLaneOverride]:
    segments = (
        psr.ReducedSuiteSegment("seg-one", [sys.executable, "-c", "pass"]),
        psr.ReducedSuiteSegment("seg-two", [sys.executable, "-c", second_body]),
    )
    override = psr.SuiteLaneOverride(segments=segments, journal={"suite_reduction": True})
    return {"reduced": override}


def test_stop_on_red_prevents_next_reduced_segment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC (3): after a red lane stops the run, the next reduced segment never starts."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("fail", "reduced"))
    terminate_returned = _patch_terminate_children_returned(monkeypatch)
    plan = _two_segment_reduced_plan()
    segment_two_started = threading.Event()
    between_marker = tmp_path / "between_segments"

    def between_segments(_ctx: preflight.LaneRunContext, index: int) -> None:
        if index == 1:
            between_marker.write_text("1", encoding="utf-8")
            assert terminate_returned.wait(timeout=10)

    real_run = _run_pixi_argv_after_dash

    def run_argv(coord: Any, ctx: preflight.LaneRunContext, argv: list[str], log_handle: Any) -> int:
        if ctx.lane.task == "reduced" and "--" in argv:
            seg_argv = argv[argv.index("--") + 1 :]
            if seg_argv == list(plan["reduced"].segments[1].argv):
                segment_two_started.set()
        return real_run(coord, ctx, argv, log_handle)

    monkeypatch.setattr(preflight, "_run_pixi_argv", run_argv)
    fail_script = (
        "import os, sys, time\n"
        f"marker = {str(between_marker)!r}\n"
        "deadline = time.monotonic() + 10\n"
        "while not os.path.isfile(marker) and time.monotonic() < deadline:\n"
        "    time.sleep(0.02)\n"
        "time.sleep(0.5)\n"
        "sys.exit(1)\n"
    )
    with patch.object(psr, "build_suite_lane_overrides", return_value=plan):
        code = preflight.run_preflight(
            repo,
            jobs=2,
            install_environment=_NOOP_INSTALL,
            scratch_parent=tmp_path / "scratch",
            subprocess_argv_for_lane=_argv_from({"fail": fail_script, "reduced": "pass"}),
            between_segments=between_segments,
        )
    assert code == preflight.EXIT_LANE_RED
    assert not segment_two_started.is_set()
    reduced = next(entry for entry in _run_record(repo)["lanes"] if entry["task"] == "reduced")
    assert reduced["status"] == "cancelled"
    assert reduced["cancelled_by"] == "fail"
    rows = {row["label"]: row for row in reduced["suite_reduction_segments"]}
    assert rows["seg-one"]["outcome"] == "passed"
    assert rows["seg-two"]["outcome"] == "not-run"
    assert rows["seg-two"]["exit_code"] is None


@pytest.mark.skipif(not hasattr(signal, "SIGINT"), reason="SIGINT required")
def test_sigint_between_reduced_segments_cancels_lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC (4): SIGINT between segments journals the reduced lane cancelled, never ok."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("hold", "reduced"))
    coords = _capture_coordinators(monkeypatch)
    plan = _two_segment_reduced_plan()
    interrupt_sent = threading.Event()

    def between_segments(_ctx: preflight.LaneRunContext, index: int) -> None:
        if index == 1:
            os.kill(os.getpid(), signal.SIGINT)
            (coord,) = coords
            assert coord.cancel.wait(timeout=10)
            interrupt_sent.set()

    monkeypatch.setattr(preflight, "_run_pixi_argv", _run_pixi_argv_after_dash)
    with patch.object(psr, "build_suite_lane_overrides", return_value=plan):
        code = preflight.run_preflight(
            repo,
            jobs=2,
            install_environment=_NOOP_INSTALL,
            scratch_parent=tmp_path / "scratch",
            subprocess_argv_for_lane=lambda lane: [
                sys.executable,
                "-c",
                _started_then("time.sleep(30)") if lane.task == "hold" else "pass",
            ],
            between_segments=between_segments,
        )
    assert interrupt_sent.is_set()
    assert code == preflight.EXIT_INTERRUPT
    record = _run_record(repo)
    assert record["verdict"] == "interrupted"
    reduced = next(entry for entry in record["lanes"] if entry["task"] == "reduced")
    assert reduced["status"] == "cancelled"
    assert reduced["cancelled_by"] == "interrupt"
    rows = {row["label"]: row for row in reduced["suite_reduction_segments"]}
    assert rows["seg-one"]["outcome"] == "passed"
    assert rows["seg-two"]["outcome"] == "not-run"


def test_keep_going_reduced_lane_runs_every_segment(tmp_path: Path) -> None:
    """AC (5): with ``--keep-going``, a reduced lane still runs every segment after a red peer."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("fail", "reduced"))
    plan = _two_segment_reduced_plan()
    with patch.object(psr, "build_suite_lane_overrides", return_value=plan):
        with patch.object(preflight, "_run_pixi_argv", side_effect=_run_pixi_argv_after_dash):
            code = preflight.run_preflight(
                repo,
                jobs=2,
                keep_going=True,
                install_environment=_NOOP_INSTALL,
                scratch_parent=tmp_path / "scratch",
                subprocess_argv_for_lane=_argv_from({"fail": "raise SystemExit(1)", "reduced": "pass"}),
            )
    assert code == preflight.EXIT_LANE_RED
    reduced = next(entry for entry in _run_record(repo)["lanes"] if entry["task"] == "reduced")
    assert reduced["status"] == "ok"
    rows = {row["label"]: row for row in reduced["suite_reduction_segments"]}
    assert rows["seg-one"]["outcome"] == "passed"
    assert rows["seg-two"]["outcome"] == "passed"


def _sigint_handler_after_a_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Callable[[int, Any], None], preflight._RunCoordinator]:  # noqa: SLF001
    """Story 71.13: run one green lane and keep the SIGINT handler the run installed, with its coordinator.

    The handler closes over the coordinator, so a test can call it after the run, with a lock swapped in that lets a
    nested call land while the outer one holds it -- a second SIGINT, delivered by no real signal and no timing.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("only"))
    coords = _capture_coordinators(monkeypatch)
    installed: list[Callable[[int, Any], None]] = []
    real_signal = signal.signal

    def record(signum: int, handler: Any) -> Any:
        if signum == signal.SIGINT and callable(handler) and handler.__qualname__.endswith("_on_sigint"):
            installed.append(handler)
        return real_signal(signum, handler)

    monkeypatch.setattr(preflight.signal, "signal", record)
    code = preflight.run_preflight(
        repo,
        jobs=1,
        install_environment=_NOOP_INSTALL,
        run_lane_ctx=lambda _ctx: 0,
        scratch_parent=tmp_path / "scratch",
    )
    assert code == preflight.EXIT_OK
    (handler,) = installed
    (coord,) = coords
    return handler, coord


def _returns_within(target: Callable[[], None], seconds: float) -> bool:
    """Run ``target`` on a daemon thread; whether it returned in time. A deadlocked call leaves only that thread."""
    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(timeout=seconds)
    return not worker.is_alive()


class _NestedSigintEvent(threading.Event):
    """``cancel`` whose ``set()`` takes its own lock and, holding it, takes a second SIGINT: the window of the defect."""

    def __init__(self, nested: Callable[[], None]) -> None:
        super().__init__()
        self.nested = nested
        self.fired = False

    def set(self) -> None:
        with self._cond:  # the non-reentrant Lock threading.Event.set holds
            if not self.fired:
                self.fired = True
                self.nested()
            self._flag = True
            self._cond.notify_all()


class _NestedSigintLock:
    """``proc_lock`` that, once armed, takes a second SIGINT while held."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.nested: Callable[[], None] | None = None

    def __enter__(self) -> _NestedSigintLock:
        self.lock.acquire()
        nested, self.nested = self.nested, None
        if nested is not None:
            nested()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.lock.release()


@pytest.mark.skipif(not hasattr(signal, "SIGINT"), reason="SIGINT required")
def test_a_second_sigint_inside_cancel_set_returns_and_the_first_completes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story 71.13 AC (1): a SIGINT that lands while the handler holds `cancel`'s lock does not deadlock it."""
    handler, coord = _sigint_handler_after_a_run(tmp_path, monkeypatch)
    coord.cancel = _NestedSigintEvent(lambda: handler(signal.SIGINT, None))
    assert _returns_within(lambda: handler(signal.SIGINT, None), 10)
    assert coord.cancel.is_set()
    assert coord.stop_cause == ("interrupt", None)
    # A later SIGINT, once the first has returned, runs the handler again as before.
    assert _returns_within(lambda: handler(signal.SIGINT, None), 10)
    assert coord.stop_cause == ("interrupt", None)


@pytest.mark.skipif(not hasattr(signal, "SIGINT"), reason="SIGINT required")
def test_a_second_sigint_while_proc_lock_is_held_returns_and_the_first_terminates_the_lane(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story 71.13 AC (2): a SIGINT that lands while `terminate_children` holds `proc_lock` does not deadlock it."""
    handler, coord = _sigint_handler_after_a_run(tmp_path, monkeypatch)
    proc_lock = _NestedSigintLock()
    coord.proc_lock = proc_lock  # type: ignore[assignment]
    running = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True)
    try:
        coord.register_proc(running, ("sleeper", "env"))
        proc_lock.nested = lambda: handler(signal.SIGINT, None)
        assert _returns_within(lambda: handler(signal.SIGINT, None), 20)
        assert proc_lock.nested is None  # the nested SIGINT did land inside the lock
        assert running.wait(timeout=10) < 0
        assert coord.terminated_lanes == {("sleeper", "env")}
        assert coord.stop_cause == ("interrupt", None)
    finally:
        if running.poll() is None:
            running.kill()
            running.wait(timeout=5)
