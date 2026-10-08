"""Unit tests for concurrent pr-preflight (Story 71.3, spec-pyforge-steward CAP-159)."""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path

from pyforge.steward import preflight

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
    run_id_dirs = list((repo / preflight.RUN_SCRATCH_RELATIVE).iterdir())
    assert len(run_id_dirs) == 1
    scratch = run_id_dirs[0]
    assert all(path.startswith(str(scratch)) for path in (values[0]["TMPDIR"], values[1]["TMPDIR"]))


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

    code = preflight.run_preflight(repo, jobs=3, install_environment=_NOOP_INSTALL, run_lane_ctx=run_ctx)
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
    )
    assert code == preflight.EXIT_LANE_RED
    record = _run_record(repo)
    assert all(entry["status"] in {"ok", "red"} for entry in record["lanes"])
    err = capsys.readouterr().err
    assert "red lane 'a'" in err
    assert "red lane 'c'" in err


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
