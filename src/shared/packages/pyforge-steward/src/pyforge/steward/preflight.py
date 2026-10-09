"""Concurrent ``pr-preflight`` runner with per-lane journaling (Stories 71.1–71.3, CAP-159).

Reads ``pr-preflight-lanes`` from ``pixi.toml``, flattens nested ``depends-on``
graphs into leaf lanes, selects the lanes CI would run for the diff (Story 71.2,
``preflight_ci``: read from ``.github/workflows/*.yml`` at run time), installs
each needed environment serially, runs selected lanes in a pool bounded by
``--jobs``, and appends JSON lines to ``.steward/preflight-runs.jsonl``.
Not a steward CLI duty — ``main()`` owns the exit code (AD-8).
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
import uuid
from collections.abc import Callable, Sequence
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pyforge.steward import preflight_ci, preflight_suite_reduction, preflight_xdist

ROOT_AGGREGATE = "pr-preflight-lanes"
DEFAULT_INVOKING_ENV = "pyforge-guild"
JOURNAL_RELATIVE = Path(".steward") / "preflight-runs.jsonl"
SCRATCH_DIR_PREFIX = "pyforge-preflight-"

EXIT_OK = 0
EXIT_LANE_RED = 1
EXIT_CONFIG = 2
EXIT_INTERRUPT = 130


@dataclass(frozen=True)
class Lane:
    task: str
    environment: str


@dataclass(frozen=True)
class LaneRunContext:
    lane: Lane
    scratch_dir: Path
    log_path: Path
    env: dict[str, str]


@dataclass(frozen=True)
class LaneResult:
    task: str
    environment: str
    seconds: float
    exit_code: int
    status: str  # ok | red | cancelled | not-run
    start_offset: float = 0.0
    journal_extra: dict[str, Any] | None = None


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


def _mk_scratch_root(scratch_parent: Path | None) -> Path:
    kwargs: dict[str, str] = {"prefix": SCRATCH_DIR_PREFIX}
    if scratch_parent is not None:
        scratch_parent.mkdir(parents=True, exist_ok=True)
        kwargs["dir"] = str(scratch_parent)
    return Path(tempfile.mkdtemp(**kwargs))


def _scratch_inside_repo(scratch_root: Path, repo_root: Path) -> bool:
    try:
        return scratch_root.resolve().is_relative_to(repo_root.resolve())
    except ValueError:
        return False


def _remove_scratch(scratch_root: Path) -> None:
    try:
        shutil.rmtree(scratch_root)
    except OSError as exc:
        print(f"preflight: could not remove scratch at {scratch_root}: {exc}", file=sys.stderr)


def _announce_scratch_kept(scratch_root: Path) -> None:
    print(f"preflight: lane logs and scratch kept at {scratch_root}", file=sys.stderr)


def _lane_scratch_env(scratch_dir: Path) -> dict[str, str]:
    scratch_dir.mkdir(parents=True, exist_ok=True)
    basetemp = scratch_dir / "pytest-basetemp"
    cache_dir = scratch_dir / "pytest-cache"
    coverage = scratch_dir / ".coverage"
    env = os.environ.copy()
    env["TMPDIR"] = str(scratch_dir)
    env["COVERAGE_FILE"] = str(coverage)
    prior = env.get("PYTEST_ADDOPTS", "").strip()
    extra = f"--basetemp={basetemp} -o cache_dir={cache_dir}"
    env["PYTEST_ADDOPTS"] = f"{prior} {extra}".strip() if prior else extra
    return env


def _default_install(repo_root: Path, environment: str) -> int:
    proc = subprocess.run(
        ["pixi", "install", "--frozen", "-e", environment],
        cwd=repo_root,
    )
    return int(proc.returncode)


@dataclass
class _RunCoordinator:
    repo_root: Path
    run_id: str
    run_start: float
    jobs: int
    keep_going: bool
    cancel: threading.Event = field(default_factory=threading.Event)
    stop_on_red: threading.Event = field(default_factory=threading.Event)
    service_locks: dict[str, threading.Lock] = field(default_factory=dict)
    active_procs: list[tuple[subprocess.Popen[Any], int]] = field(default_factory=list)
    proc_lock: threading.Lock = field(default_factory=threading.Lock)
    red_lanes: list[str] = field(default_factory=list)
    suite_lane_plan: dict[str, preflight_suite_reduction.SuiteLaneOverride | dict[str, Any]] = field(
        default_factory=dict
    )
    suite_reduction_runtime_journal: dict[str, dict[str, Any]] = field(default_factory=dict)
    xdist_workers: dict[str, int] = field(default_factory=dict)

    def service_lock(self, key: str | None) -> threading.Lock | None:
        if key is None:
            return None
        if key not in self.service_locks:
            self.service_locks[key] = threading.Lock()
        return self.service_locks[key]

    def register_proc(self, proc: subprocess.Popen[Any]) -> None:
        with self.proc_lock:
            self.active_procs.append((proc, proc.pid))

    def unregister_proc(self, proc: subprocess.Popen[Any]) -> None:
        with self.proc_lock:
            self.active_procs = [(p, pid) for p, pid in self.active_procs if p is not proc]

    def terminate_children(self) -> None:
        with self.proc_lock:
            procs = list(self.active_procs)
        for proc, _pid in procs:
            if proc.poll() is not None:
                continue
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError, PermissionError:
                proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError, PermissionError:
                    proc.kill()


def _segment_outcome(exit_code: int) -> str:
    if exit_code == 0:
        return "passed"
    if exit_code == preflight_suite_reduction.PYTEST_EXIT_NO_TESTS_COLLECTED:
        return "no-tests-selected"
    return "failed"


def _run_pixi_argv(
    coord: _RunCoordinator,
    ctx: LaneRunContext,
    argv: list[str],
    log_handle: Any,
) -> int:
    proc = subprocess.Popen(
        argv,
        cwd=coord.repo_root,
        env=ctx.env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    coord.register_proc(proc)
    try:
        return int(proc.wait())
    finally:
        coord.unregister_proc(proc)


def _subprocess_reduced_suite_lane(
    coord: _RunCoordinator,
    ctx: LaneRunContext,
    override: preflight_suite_reduction.SuiteLaneOverride,
) -> int:
    ctx.log_path.parent.mkdir(parents=True, exist_ok=True)
    segment_rows: list[dict[str, Any]] = []
    task_collect_exit: int | None = None
    lane_exit = 0
    prefix = ["pixi", "run", "--frozen", "-e", ctx.lane.environment, "--"]
    with ctx.log_path.open("wb") as log_handle:
        for index, segment in enumerate(override.segments):
            if coord.cancel.is_set():
                for pending in override.segments[index:]:
                    segment_rows.append(
                        {
                            "label": pending.label,
                            "command": shlex.join(pending.argv),
                            "exit_code": None,
                            "outcome": "not-run",
                        }
                    )
                break
            cmd = [*prefix, *segment.argv]
            code = _run_pixi_argv(coord, ctx, cmd, log_handle)
            outcome = _segment_outcome(code)
            segment_rows.append(
                {
                    "label": segment.label,
                    "command": shlex.join(segment.argv),
                    "exit_code": code,
                    "outcome": outcome,
                }
            )
            if outcome == "failed":
                lane_exit = code
                for pending in override.segments[index + 1 :]:
                    segment_rows.append(
                        {
                            "label": pending.label,
                            "command": shlex.join(pending.argv),
                            "exit_code": None,
                            "outcome": "not-run",
                        }
                    )
                break
        else:
            if segment_rows and all(row["outcome"] == "no-tests-selected" for row in segment_rows):
                collect_argv = [
                    "pixi",
                    "run",
                    "--frozen",
                    "-e",
                    ctx.lane.environment,
                    ctx.lane.task,
                    "--collect-only",
                ]
                task_collect_exit = _run_pixi_argv(coord, ctx, collect_argv, log_handle)
                lane_exit = task_collect_exit
            else:
                lane_exit = 0

    journal_extra = dict(override.journal)
    journal_extra["suite_reduction_segments"] = segment_rows
    if task_collect_exit is not None:
        journal_extra["suite_reduction_task_collect_exit"] = task_collect_exit
    coord.suite_reduction_runtime_journal[ctx.lane.task] = journal_extra
    return lane_exit


def _subprocess_lane(coord: _RunCoordinator, ctx: LaneRunContext) -> int:
    ctx.log_path.parent.mkdir(parents=True, exist_ok=True)
    plan_entry = coord.suite_lane_plan.get(ctx.lane.task)
    if isinstance(plan_entry, preflight_suite_reduction.SuiteLaneOverride):
        return _subprocess_reduced_suite_lane(coord, ctx, plan_entry)
    argv = ["pixi", "run", "--frozen", "-e", ctx.lane.environment, ctx.lane.task]
    with ctx.log_path.open("wb") as log_handle:
        return _run_pixi_argv(coord, ctx, argv, log_handle)


def _default_run_lane_ctx(coord: _RunCoordinator, ctx: LaneRunContext) -> int:
    return _subprocess_lane(coord, ctx)


def _append_journal(repo_root: Path, record: dict[str, Any]) -> None:
    path = repo_root / JOURNAL_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _print_lane_log(log_path: Path) -> None:
    if not log_path.is_file():
        return
    text = log_path.read_text(encoding="utf-8", errors="replace")
    if text:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()


def _lane_journal_extra(coord: _RunCoordinator, task: str) -> dict[str, Any] | None:
    runtime = coord.suite_reduction_runtime_journal.get(task)
    if runtime is not None:
        return dict(runtime)
    entry = coord.suite_lane_plan.get(task)
    if isinstance(entry, preflight_suite_reduction.SuiteLaneOverride):
        return dict(entry.journal)
    if isinstance(entry, dict):
        return dict(entry)
    return None


def _lane_result_dict(result: LaneResult) -> dict[str, Any]:
    payload = asdict(result)
    extra = payload.pop("journal_extra", None)
    if extra:
        payload.update(extra)
    return payload


def _run_lane_in_pool(
    coord: _RunCoordinator,
    lane: Lane,
    scratch_root: Path,
    service_key: str | None,
    runner: Callable[[LaneRunContext], int],
    use_subprocess: bool,
) -> LaneResult:
    if coord.cancel.is_set():
        return LaneResult(lane.task, lane.environment, 0.0, 0, "cancelled", 0.0)
    if coord.stop_on_red.is_set() and not coord.keep_going:
        return LaneResult(lane.task, lane.environment, 0.0, 0, "cancelled", 0.0)

    service_lock = coord.service_lock(service_key)
    if service_lock is not None:
        service_lock.acquire()
    try:
        if coord.cancel.is_set() or (coord.stop_on_red.is_set() and not coord.keep_going):
            return LaneResult(lane.task, lane.environment, 0.0, 0, "cancelled", 0.0)

        lane_dir = scratch_root / lane.task
        log_path = scratch_root / f"{lane.task}.log"
        env = _lane_scratch_env(lane_dir)
        workers = coord.xdist_workers.get(lane.task)
        if workers is not None:
            env["PYTEST_XDIST_AUTO_NUM_WORKERS"] = str(workers)
        ctx = LaneRunContext(lane=lane, scratch_dir=lane_dir, log_path=log_path, env=env)
        start_offset = time.monotonic() - coord.run_start
        lane_start = time.monotonic()

        if use_subprocess:
            code = _subprocess_lane(coord, ctx)
        else:
            code = runner(ctx)

        elapsed = time.monotonic() - lane_start
        _print_lane_log(log_path)

        journal_extra = _lane_journal_extra(coord, lane.task)
        if code == 0:
            return LaneResult(lane.task, lane.environment, elapsed, 0, "ok", start_offset, journal_extra)
        coord.red_lanes.append(lane.task)
        if not coord.keep_going:
            coord.stop_on_red.set()
            coord.terminate_children()
        return LaneResult(lane.task, lane.environment, elapsed, code, "red", start_offset, journal_extra)
    finally:
        if service_lock is not None:
            service_lock.release()


def run_preflight(
    repo_root: Path,
    *,
    pixi_path: Path | None = None,
    invoking_env: str | None = None,
    run_lane: Callable[[Lane], int] | None = None,
    run_lane_ctx: Callable[[LaneRunContext], int] | None = None,
    jobs: int | None = None,
    keep_going: bool = False,
    install_environment: Callable[[str], int] | None = None,
    scratch_parent: Path | None = None,
) -> int:
    """Run CI-selected lanes; return exit code 0 / 1 / 2 / 130."""
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

    worker_count = jobs if jobs is not None else _logical_core_count()
    if worker_count < 1:
        worker_count = 1

    mutex_keys = preflight_ci.static_service_mutex_keys(repo_root, lanes, pixi_data)
    suite_lane_plan = preflight_suite_reduction.build_suite_lane_overrides(
        repo_root,
        selected_task_names={lane.task for lane in lanes},
        pixi_data=pixi_data,
    )

    use_subprocess = run_lane_ctx is None and run_lane is None
    injected_runner: Callable[[LaneRunContext], int] | None
    if run_lane_ctx is not None:
        injected_runner = run_lane_ctx
    elif run_lane is not None:
        legacy_run_lane = run_lane

        def injected_runner(ctx: LaneRunContext) -> int:
            return legacy_run_lane(ctx.lane)

    else:
        injected_runner = None

    install_fn = install_environment or (lambda environment: _default_install(repo_root, environment))
    run_id = str(uuid.uuid4())
    started = datetime.now(tz=UTC)
    head_sha, branch = _git_head(repo_root)
    run_start = time.monotonic()
    t0 = run_start

    unique_envs = list(dict.fromkeys(lane.environment for lane in lanes))
    install_t0 = time.monotonic()
    for environment in unique_envs:
        code = install_fn(environment)
        if code != 0:
            install_seconds = time.monotonic() - install_t0
            _append_journal(
                repo_root,
                {
                    "phase": "install",
                    "run_id": run_id,
                    "started_at": started.isoformat(),
                    "seconds": install_seconds,
                    "environment": environment,
                    "exit_code": code,
                    "verdict": "red",
                },
            )
            print(f"preflight: pixi install for {environment!r} exited {code}", file=sys.stderr)
            return EXIT_LANE_RED
    install_seconds = time.monotonic() - install_t0
    _append_journal(
        repo_root,
        {
            "phase": "install",
            "run_id": run_id,
            "started_at": started.isoformat(),
            "seconds": install_seconds,
            "environments": unique_envs,
            "verdict": "ok",
        },
    )

    scratch_root = _mk_scratch_root(scratch_parent)
    if _scratch_inside_repo(scratch_root, repo_root):
        _remove_scratch(scratch_root)
        print(
            f"preflight: scratch root must not live inside the checkout: {scratch_root}",
            file=sys.stderr,
        )
        return EXIT_CONFIG

    xdist_workers = preflight_xdist.lane_xdist_worker_map(
        lane_tasks=[lane.task for lane in lanes],
        pixi_data=pixi_data,
        logical_cores=_logical_core_count(),
        pool_jobs=worker_count,
    )
    coord = _RunCoordinator(
        repo_root=repo_root,
        run_id=run_id,
        run_start=run_start,
        jobs=worker_count,
        keep_going=keep_going,
        suite_lane_plan=suite_lane_plan,
        xdist_workers=xdist_workers,
    )
    if injected_runner is not None:
        runner = injected_runner
    else:

        def runner(ctx: LaneRunContext) -> int:
            return _default_run_lane_ctx(coord, ctx)

    prior_sigint = signal.getsignal(signal.SIGINT)

    def _on_sigint(_signum: int, _frame: object | None) -> None:
        coord.cancel.set()
        coord.terminate_children()

    signal.signal(signal.SIGINT, _on_sigint)

    results_by_task: dict[str, LaneResult] = {}
    try:
        with ThreadPoolExecutor(max_workers=worker_count) as pool:
            futures: dict[Future[LaneResult], Lane] = {}
            lane_iter = iter(lanes)

            while True:
                if coord.cancel.is_set():
                    break
                while len(futures) < worker_count and not (coord.stop_on_red.is_set() and not coord.keep_going):
                    try:
                        lane = next(lane_iter)
                    except StopIteration:
                        break
                    fut = pool.submit(
                        _run_lane_in_pool,
                        coord,
                        lane,
                        scratch_root,
                        mutex_keys.get((lane.task, lane.environment)),
                        runner,
                        use_subprocess,
                    )
                    futures[fut] = lane
                if not futures:
                    break
                done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
                for fut in done:
                    lane = futures.pop(fut)
                    try:
                        result = fut.result()
                    except Exception:  # noqa: BLE001
                        result = LaneResult(lane.task, lane.environment, 0.0, 1, "red", 0.0)
                    results_by_task[lane.task] = result
                if coord.stop_on_red.is_set() and not coord.keep_going:
                    for fut in list(futures):
                        fut.cancel()
                    futures.clear()
                    break
    finally:
        signal.signal(signal.SIGINT, prior_sigint)
        coord.terminate_children()

    if coord.cancel.is_set():
        total_seconds = time.monotonic() - t0
        ordered: list[LaneResult] = []
        for lane in lanes:
            if lane.task in results_by_task:
                ordered.append(results_by_task[lane.task])
            else:
                ordered.append(LaneResult(lane.task, lane.environment, 0.0, 0, "cancelled", 0.0))
        _append_journal(
            repo_root,
            {
                "run_id": run_id,
                "started_at": started.isoformat(),
                "head_sha": head_sha,
                "branch": branch,
                "logical_cores": _logical_core_count(),
                "jobs": worker_count,
                "keep_going": keep_going,
                "total_seconds": total_seconds,
                "verdict": "interrupted",
                "invoking_environment": env,
                "selection": selection.to_journal(),
                "lanes": [_lane_result_dict(r) for r in ordered],
            },
        )
        _announce_scratch_kept(scratch_root)
        return EXIT_INTERRUPT

    ordered_results: list[LaneResult] = []
    exit_code = EXIT_OK
    for lane in lanes:
        if lane.task in results_by_task:
            result = results_by_task[lane.task]
        elif coord.stop_on_red.is_set() and not coord.keep_going:
            result = LaneResult(lane.task, lane.environment, 0.0, 0, "cancelled", 0.0)
        else:
            result = LaneResult(lane.task, lane.environment, 0.0, 0, "not-run", 0.0)
        ordered_results.append(result)
        if result.status == "red":
            exit_code = EXIT_LANE_RED
            lane_log = scratch_root / f"{lane.task}.log"
            print(
                f"preflight: lane {lane.task!r} in environment {lane.environment!r} "
                f"exited {result.exit_code} (log: {lane_log})",
                file=sys.stderr,
            )

    if keep_going and coord.red_lanes:
        exit_code = EXIT_LANE_RED
        for name in coord.red_lanes:
            lane_log = scratch_root / f"{name}.log"
            print(f"preflight: red lane {name!r} (log: {lane_log})", file=sys.stderr)

    total_seconds = time.monotonic() - t0
    verdict = "ok" if exit_code == EXIT_OK else "red"
    _append_journal(
        repo_root,
        {
            "run_id": run_id,
            "started_at": started.isoformat(),
            "head_sha": head_sha,
            "branch": branch,
            "logical_cores": _logical_core_count(),
            "jobs": worker_count,
            "keep_going": keep_going,
            "total_seconds": total_seconds,
            "verdict": verdict,
            "invoking_environment": env,
            "selection": selection.to_journal(),
            "lanes": [_lane_result_dict(r) for r in ordered_results],
        },
    )
    if exit_code == EXIT_OK:
        _remove_scratch(scratch_root)
    else:
        _announce_scratch_kept(scratch_root)
    return exit_code


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    if argv and ("--budget" in argv or argv[0] == "--budget"):
        from pyforge.steward import preflight_budget

        return preflight_budget._parse_args(argv)  # noqa: SLF001 — shared CLI surface

    parser = argparse.ArgumentParser(prog="pyforge.steward.preflight")
    parser.add_argument(
        "--jobs",
        type=int,
        default=None,
        help="maximum concurrent lanes (default: logical CPU count)",
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="run every selected lane even when one exits non-zero",
    )
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    argv_list = list(argv or [])
    if argv_list and ("--budget" in argv_list or argv_list[0] == "--budget"):
        from pyforge.steward import preflight_budget

        return preflight_budget.main(argv_list)
    args = _parse_args(argv_list)
    repo_root = Path(os.environ.get("PIXI_PROJECT_ROOT", ".")).resolve()
    return run_preflight(
        repo_root,
        jobs=args.jobs,
        keep_going=args.keep_going,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
