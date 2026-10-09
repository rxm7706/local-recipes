"""Unit tests for concurrent pr-preflight (Story 71.3, spec-pyforge-steward CAP-159)."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
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

    code = preflight.run_preflight(
        repo,
        jobs=3,
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


_FAIL_SCRIPT = "import time; time.sleep(0.5); raise SystemExit(1)"
_SLEEP_SCRIPT = (
    "import os, time; open(os.path.join(os.environ['TMPDIR'], 'pgid'), 'w').write(str(os.getpgrp())); "
    "time.sleep(30)"
)


def _subprocess_lane_scripts(lane: preflight.Lane) -> list[str]:
    scripts = {"fail": _FAIL_SCRIPT, "sleep": _SLEEP_SCRIPT}
    return [sys.executable, "-c", scripts[lane.task]]


def test_real_subprocess_red_lane_cancels_running_peer(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("fail", "sleep"))
    t0 = time.monotonic()
    code = preflight.run_preflight(
        repo,
        jobs=2,
        install_environment=_NOOP_INSTALL,
        scratch_parent=tmp_path / "scratch",
        subprocess_argv_for_lane=_subprocess_lane_scripts,
    )
    elapsed = time.monotonic() - t0
    assert code == preflight.EXIT_LANE_RED
    assert elapsed < 10.0
    record = _run_record(repo)
    by_task = {entry["task"]: entry for entry in record["lanes"]}
    assert by_task["fail"]["status"] == "red"
    assert by_task["fail"]["exit_code"] == 1
    assert by_task["fail"]["seconds"] > 0
    assert by_task["sleep"]["status"] == "cancelled"
    assert by_task["sleep"]["exit_code"] != 0
    assert by_task["sleep"]["seconds"] > 0
    assert by_task["sleep"]["cancelled_by"] == "fail"
    err = capsys.readouterr().err
    assert "lane 'fail'" in err
    assert "red lane 'sleep'" not in err
    scratch_roots = list((tmp_path / "scratch").glob("pyforge-preflight-*"))
    assert len(scratch_roots) == 1
    pgid_file = scratch_roots[0] / "sleep" / "pgid"
    assert pgid_file.is_file()
    pgid = int(pgid_file.read_text(encoding="utf-8"))
    with pytest.raises(ProcessLookupError):
        os.killpg(pgid, 0)


@pytest.mark.skipif(not hasattr(signal, "SIGINT"), reason="SIGINT required")
def test_sigint_cancels_real_subprocess_lanes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("sleep-a", "sleep-b"))
    started = threading.Event()
    started_count = {"n": 0}
    lock = threading.Lock()

    def scripts(lane: preflight.Lane) -> list[str]:
        return [
            sys.executable,
            "-c",
            "import threading, time; "
            "started = __import__('threading').Event(); "
            "import os; "
            f"open(os.path.join(os.environ['TMPDIR'], 'started-{lane.task}'), 'w').write('1'); "
            "time.sleep(30)",
        ]

    def poll_started() -> None:
        scratch_roots = list((tmp_path / "scratch").glob("pyforge-preflight-*"))
        if not scratch_roots:
            return
        root = scratch_roots[0]
        if (root / "sleep-a" / "started-sleep-a").is_file() and (root / "sleep-b" / "started-sleep-b").is_file():
            started.set()

    def interrupt() -> None:
        for _ in range(50):
            poll_started()
            if started.is_set():
                os.kill(os.getpid(), signal.SIGINT)
                return
            time.sleep(0.05)

    timer = threading.Timer(0.1, interrupt)
    timer.start()
    try:
        code = preflight.run_preflight(
            repo,
            jobs=2,
            install_environment=_NOOP_INSTALL,
            scratch_parent=tmp_path / "scratch",
            subprocess_argv_for_lane=scripts,
        )
    finally:
        timer.cancel()
    assert code == preflight.EXIT_INTERRUPT
    record = _run_record(repo)
    assert record["verdict"] == "interrupted"
    for entry in record["lanes"]:
        assert entry["status"] == "cancelled"
        assert entry["seconds"] > 0
        assert entry["cancelled_by"] == "interrupt"


def test_terminate_children_skips_already_exited_process(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    proc = subprocess.Popen(
        [sys.executable, "-c", "raise SystemExit(2)"],
        start_new_session=True,
    )
    proc.wait(timeout=5)
    assert proc.returncode == 2
    coord = preflight._RunCoordinator(  # noqa: SLF001
        repo_root=repo,
        run_id="t",
        run_start=0.0,
        jobs=1,
        keep_going=False,
    )
    coord.register_proc(proc, "culprit")
    coord.terminate_children()
    assert "culprit" not in coord.terminated_lane_tasks


def test_jobs_one_never_started_lanes_have_no_cancelled_by(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("fail", "b", "c"))

    def scripts(lane: preflight.Lane) -> list[str]:
        if lane.task == "fail":
            return [sys.executable, "-c", "raise SystemExit(1)"]
        return [sys.executable, "-c", "import time; time.sleep(30)"]

    code = preflight.run_preflight(
        repo,
        jobs=1,
        install_environment=_NOOP_INSTALL,
        scratch_parent=tmp_path / "scratch",
        subprocess_argv_for_lane=scripts,
    )
    assert code == preflight.EXIT_LANE_RED
    record = _run_record(repo)
    by_task = {entry["task"]: entry for entry in record["lanes"]}
    assert by_task["fail"]["status"] == "red"
    for name in ("b", "c"):
        assert by_task[name]["status"] == "cancelled"
        assert by_task[name]["exit_code"] == 0
        assert by_task[name]["seconds"] == 0.0
        assert "cancelled_by" not in by_task[name]


def test_reduced_lane_cancelled_mid_segment(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("fail", "slow"))
    segments = (
        psr.ReducedSuiteSegment("rest-of-task", [sys.executable, "-c", "import time; time.sleep(30)"]),
        psr.ReducedSuiteSegment("gate-dirs-complement", [sys.executable, "-c", "pass"]),
    )
    override = psr.SuiteLaneOverride(segments=segments, journal={"suite_reduction": True})
    plan = {"slow": override}

    def run_seg(coord, ctx, argv, log_handle):
        dash = argv.index("--")
        seg = argv[dash + 1 :]
        proc = subprocess.Popen(
            seg,
            cwd=coord.repo_root,
            env=ctx.env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        coord.register_proc(proc, ctx.lane.task)
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
                subprocess_argv_for_lane=lambda lane: [sys.executable, "-c", _FAIL_SCRIPT],
            )
    assert code == preflight.EXIT_LANE_RED
    record = _run_record(repo)
    slow = next(entry for entry in record["lanes"] if entry["task"] == "slow")
    assert slow["status"] == "cancelled"
    rows = {row["label"]: row for row in slow["suite_reduction_segments"]}
    assert rows["rest-of-task"]["outcome"] == "cancelled"
    assert rows["gate-dirs-complement"]["outcome"] == "not-run"
