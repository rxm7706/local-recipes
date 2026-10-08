"""Serial ``pr-preflight`` runner with per-lane journaling (Story 71.1, CAP-159).

Reads ``pr-preflight-lanes`` from ``pixi.toml``, flattens nested ``depends-on``
graphs into leaf lanes, selects the lanes CI would run for the diff (Story 71.2,
``preflight_ci``: read from ``.github/workflows/*.yml`` at run time), runs each
selected lane as ``pixi run --frozen -e <env> <task>``, stops on the first non-zero
exit, and appends one JSON line to ``.steward/preflight-runs.jsonl`` carrying the
selection and the workflow rule that skipped each skipped lane.
Not a steward CLI duty — ``main()`` owns the exit code (AD-8).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import tomllib
import uuid
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pyforge.steward import preflight_ci

ROOT_AGGREGATE = "pr-preflight-lanes"
DEFAULT_INVOKING_ENV = "pyforge-guild"
JOURNAL_RELATIVE = Path(".steward") / "preflight-runs.jsonl"

EXIT_OK = 0
EXIT_LANE_RED = 1
EXIT_CONFIG = 2


@dataclass(frozen=True)
class Lane:
    task: str
    environment: str


@dataclass(frozen=True)
class LaneResult:
    task: str
    environment: str
    seconds: float
    exit_code: int
    status: str  # ok | red | not-run


class PreflightConfigError(Exception):
    """Lane list could not be derived from pixi.toml."""


def _invoking_environment() -> str:
    return os.environ.get("PIXI_ENVIRONMENT_NAME", DEFAULT_INVOKING_ENV)


def _find_task(pixi_data: dict[str, Any], task_name: str) -> dict[str, Any] | None:
    for feature in pixi_data.get("feature", {}).values():
        tasks = feature.get("tasks")
        if isinstance(tasks, dict) and task_name in tasks:
            return tasks[task_name]
    return None


def _resolve_dep(dep: str | dict[str, Any], invoking_env: str) -> tuple[str, str]:
    if isinstance(dep, str):
        return dep, invoking_env
    task = dep["task"]
    env = dep.get("environment", invoking_env)
    return task, env


def _expand_task(
    pixi_data: dict[str, Any],
    task_name: str,
    environment: str,
    stack: list[str],
) -> list[Lane]:
    if task_name in stack:
        raise PreflightConfigError(f"depends-on cycle at task {task_name!r}")
    task = _find_task(pixi_data, task_name)
    if task is None:
        raise PreflightConfigError(f"unknown task {task_name!r}")
    stack.append(task_name)
    lanes: list[Lane] = []
    try:
        for dep in task.get("depends-on", []):
            child_task, child_env = _resolve_dep(dep, environment)
            lanes.extend(_expand_task(pixi_data, child_task, child_env, stack))
        if "cmd" in task:
            lanes.append(Lane(task=task_name, environment=environment))
    finally:
        stack.pop()
    return lanes


def list_preflight_lanes(
    pixi_data: dict[str, Any],
    *,
    invoking_env: str | None = None,
) -> list[Lane]:
    """Return every leaf lane for ``pr-preflight-lanes`` in declaration order."""
    env = invoking_env if invoking_env is not None else _invoking_environment()
    guild_tasks = pixi_data.get("feature", {}).get("guild-tasks", {}).get("tasks", {})
    if ROOT_AGGREGATE not in guild_tasks:
        raise PreflightConfigError(f"no {ROOT_AGGREGATE!r} task in pixi.toml")
    aggregate = guild_tasks[ROOT_AGGREGATE]
    deps = aggregate.get("depends-on")
    if not deps:
        raise PreflightConfigError(f"{ROOT_AGGREGATE!r} has no depends-on")
    lanes: list[Lane] = []
    for dep in deps:
        task_name, lane_env = _resolve_dep(dep, env)
        lanes.extend(_expand_task(pixi_data, task_name, lane_env, []))
    return lanes


def _logical_core_count() -> int:
    try:
        return len(os.sched_getaffinity(0))
    except AttributeError, NotImplementedError:
        return os.cpu_count() or 1


def _git_head(repo_root: Path) -> tuple[str, str]:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return sha, branch or "(detached)"
    except subprocess.CalledProcessError, FileNotFoundError:
        return "unknown", "unknown"


def _default_run_lane(repo_root: Path, lane: Lane) -> int:
    proc = subprocess.run(
        ["pixi", "run", "--frozen", "-e", lane.environment, lane.task],
        cwd=repo_root,
    )
    return int(proc.returncode)


def _append_journal(repo_root: Path, record: dict[str, Any]) -> None:
    path = repo_root / JOURNAL_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def run_preflight(
    repo_root: Path,
    *,
    pixi_path: Path | None = None,
    invoking_env: str | None = None,
    run_lane: Callable[[Lane], int] | None = None,
) -> int:
    """Run CI-selected lanes; return exit code 0 / 1 / 2."""
    repo_root = repo_root.resolve()
    pixi_file = pixi_path or (repo_root / "pixi.toml")
    if not pixi_file.is_file():
        print(f"preflight: no pixi.toml at {pixi_file}", file=sys.stderr)
        return EXIT_CONFIG
    pixi_data = tomllib.loads(pixi_file.read_text(encoding="utf-8"))
    env = invoking_env if invoking_env is not None else _invoking_environment()
    try:
        lanes = list_preflight_lanes(pixi_data, invoking_env=env)
    except PreflightConfigError as exc:
        print(f"preflight: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    selection = preflight_ci.select_lanes(repo_root, lanes, pixi_data)
    lanes = [lane for lane in lanes if selection.is_selected(lane)]
    skipped_count = len(selection.verdicts) - len(lanes)
    note = f" ({selection.all_reason})" if selection.all_reason else ""
    print(
        f"preflight: running {len(lanes)} of {len(selection.verdicts)} lanes, "
        f"{skipped_count} skipped by their workflow's own rules{note}",
        file=sys.stderr,
    )

    lane_runner = run_lane or (lambda lane: _default_run_lane(repo_root, lane))
    run_id = str(uuid.uuid4())
    started = datetime.now(tz=UTC)
    head_sha, branch = _git_head(repo_root)
    t0 = time.monotonic()
    results: list[LaneResult] = []
    exit_code = EXIT_OK

    for index, lane in enumerate(lanes):
        if exit_code != EXIT_OK:
            results.append(
                LaneResult(
                    task=lane.task,
                    environment=lane.environment,
                    seconds=0.0,
                    exit_code=0,
                    status="not-run",
                )
            )
            continue
        lane_start = time.monotonic()
        code = lane_runner(lane)
        elapsed = time.monotonic() - lane_start
        if code == 0:
            results.append(
                LaneResult(
                    task=lane.task,
                    environment=lane.environment,
                    seconds=elapsed,
                    exit_code=0,
                    status="ok",
                )
            )
        else:
            results.append(
                LaneResult(
                    task=lane.task,
                    environment=lane.environment,
                    seconds=elapsed,
                    exit_code=code,
                    status="red",
                )
            )
            print(
                f"preflight: lane {lane.task!r} in environment {lane.environment!r} exited {code}",
                file=sys.stderr,
            )
            exit_code = EXIT_LANE_RED
            for rest in lanes[index + 1 :]:
                results.append(
                    LaneResult(
                        task=rest.task,
                        environment=rest.environment,
                        seconds=0.0,
                        exit_code=0,
                        status="not-run",
                    )
                )
            break

    total_seconds = time.monotonic() - t0
    verdict = "ok" if exit_code == EXIT_OK else "red"
    record = {
        "run_id": run_id,
        "started_at": started.isoformat(),
        "head_sha": head_sha,
        "branch": branch,
        "logical_cores": _logical_core_count(),
        "total_seconds": total_seconds,
        "verdict": verdict,
        "invoking_environment": env,
        "selection": selection.to_journal(),
        "lanes": [asdict(r) for r in results],
    }
    _append_journal(repo_root, record)
    return exit_code


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv
    repo_root = Path(os.environ.get("PIXI_PROJECT_ROOT", ".")).resolve()
    return run_preflight(repo_root)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
