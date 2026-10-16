"""Concurrent ``pr-preflight`` runner with per-lane journaling (Stories 71.1–71.3, CAP-159).

Reads ``pr-preflight-lanes`` from ``pixi.toml``, builds one lane per
``(task, environment)`` with a ``cmd`` and dependency edges from ``depends-on``,
selects the lanes CI would run for the diff (Story 71.2,
``preflight_ci``: read from ``.github/workflows/*.yml`` at run time), installs
each needed environment serially, runs selected lanes in a pool bounded by
``--jobs``, and appends JSON lines to ``.steward/preflight-runs.jsonl``.
Lanes that share a CI service container, or the ``docs-site/`` tree, share a mutex and never run at once
(Stories 71.3, 105.1; :func:`lane_mutex_keys`).
A lane is its task and its environment wherever the runner keeps per-lane state —
results, scratch, logs, stop marks, journal extras, worker shares (Story 103.5):
one task may run in two environments.
A run has a scope (Story 103.6): ``full`` runs every selected lane; ``touched`` runs only the lanes the diff
changes, the five fast-core detectors in place of ``detectors-ci`` and lint and types when Python under ``src/``
changed, and journals every other lane as deferred: CI arbitrates it. ``PYFORGE_PREFLIGHT_SCOPE`` chooses the
scope, or, unset, the flag ``pyforge.steward.preflight_ci_arbitrates``; ``main`` resolves it, so
``run_preflight`` defaults to ``full``. ``steward preflight verify-deferred`` is the catch-up.
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
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pyforge.core.flags import FlagConfigError, read_boolean

from pyforge.steward import preflight_ci, preflight_suite_reduction, preflight_xdist

ROOT_AGGREGATE = "pr-preflight-lanes"
DEFAULT_INVOKING_ENV = "pyforge-guild"
JOURNAL_RELATIVE = Path(".steward") / "preflight-runs.jsonl"
SCRATCH_DIR_PREFIX = "pyforge-preflight-"

EXIT_OK = 0
EXIT_LANE_RED = 1
EXIT_CONFIG = 2
EXIT_INTERRUPT = 130

# Story 103.6: the scope of one run. The variable wins; unset, the flag decides (on = touched).
SCOPE_ENV = "PYFORGE_PREFLIGHT_SCOPE"
SCOPE_FULL = "full"
SCOPE_TOUCHED = "touched"
SCOPES = (SCOPE_FULL, SCOPE_TOUCHED)
SCOPE_FLAG_KEY = "pyforge.steward.preflight_ci_arbitrates"
DEFERRED_REASON = "CI arbitrates"
# The cheap planning detectors a touched run keeps, each a guild task of its own, in place of the
# detectors-ci lane that runs them among the rest.
FAST_CORE_TASKS = (
    "spec-surface-check",
    "flag-gate-check",
    "story-status-check",
    "ledger-regression-check",
    "chain-completeness-check",
)
FAST_CORE_REPLACES = "detectors-ci"

# Story 105.1 (a fix under CAP-159: concurrent lanes share no mutable state): the tasks that install into, read from
# or build in the one ``docs-site/`` tree. Each lane of one holds DOCS_SITE_MUTEX_KEY while it runs, so no two of them
# overlap; every other lane keeps its concurrency. Declared once, here: tests/meta/test_preflight_docs_site_lanes.py
# derives the same set from pixi.toml, the docs-site scripts' imports and herald's tests, and fails when they differ.
DOCS_SITE_MUTEX_KEY = "tree:docs-site"
DOCS_SITE_TASKS = frozenset(
    {
        "docs-site-install",  # npm ci: deletes docs-site/node_modules and installs it again
        "docs-site-build",  # astro build: rewrites docs-site/public/ and writes docs-site/build/site/
        "pages-build",  # the same build, through docs-site/scripts/pages.mts
        "pages-check",  # pages.mts check: reads docs-site/build/site/, which the builds write
        "docs-site-validate-sidebar",  # nav-check.mts imports the yaml package from docs-site/node_modules
        "pyforge-herald-test",  # herald's built-site tests run astro build in docs-site/ (pages_astro.astro_build)
        "pyforge-herald-coverage-gate",  # herald's unit suite under coverage, its built-site test included
        "pyforge-herald-test-coverage",  # herald's whole suite under coverage
    }
)


LaneKey = tuple[str, str]


@dataclass(frozen=True)
class Lane:
    task: str
    environment: str
    depends_on: tuple[LaneKey, ...] = ()


def lane_label(task: str, environment: str) -> str:
    """A lane's name in its scratch directory, its log and the budget lines: ``<task>@<environment>``.

    Pixi environment names hold only lowercase letters, digits and hyphens, so the label is unique per
    lane even when ``pr-preflight-lanes`` names one task in two environments (Story 103.5).
    """
    return f"{task}@{environment}"


def lane_mutex_keys(
    lanes: Sequence[Lane],
    service_keys: Mapping[LaneKey, str | None],
) -> dict[LaneKey, tuple[str, ...]]:
    """Every mutex each lane holds while it runs, sorted: the one order every lane takes them in (Story 105.1).

    A lane holds its CI job's service key when it has one (Story 71.3; ``preflight_ci.static_service_mutex_keys``)
    and, when its task is in :data:`DOCS_SITE_TASKS`, :data:`DOCS_SITE_MUTEX_KEY`. Two lanes that share a key never
    run at once; a lane with no key holds nothing.
    """
    keys: dict[LaneKey, tuple[str, ...]] = {}
    for lane in lanes:
        held = {DOCS_SITE_MUTEX_KEY} if lane.task in DOCS_SITE_TASKS else set()
        service = service_keys.get(_lane_key(lane))
        if service is not None:
            held.add(service)
        keys[_lane_key(lane)] = tuple(sorted(held))
    return keys


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
    cancelled_by: str | None = None
    blocked_by: str | None = None
    # The environment of the lane named by ``cancelled_by`` / ``blocked_by``; ``None`` when the cause is
    # not a lane (``interrupt``). Journaled only when set: additive to the record (Story 103.5).
    cancelled_by_environment: str | None = None
    blocked_by_environment: str | None = None


class PreflightConfigError(Exception):
    """Lane list could not be derived from pixi.toml."""


class PreflightScopeError(Exception):
    """``PYFORGE_PREFLIGHT_SCOPE`` holds a value that is not a scope; the run refuses, it never falls back."""


@dataclass(frozen=True)
class ScopeChoice:
    """The scope of one run and what chose it: the variable, or the flag's value."""

    scope: str
    source: str


def _scope_flag_on() -> bool:
    return read_boolean(SCOPE_FLAG_KEY, default=False)


def resolve_scope(
    environ: Mapping[str, str] | None = None,
    *,
    flag_on: Callable[[], bool] | None = None,
) -> ScopeChoice:
    """``PYFORGE_PREFLIGHT_SCOPE`` when it is set, else the flag (Story 103.6).

    ``full`` and ``touched`` are the scopes. Any other value of the variable, the empty string included, raises
    :class:`PreflightScopeError`. The flag is read only when the variable is unset. ``PYFORGE_PREFLIGHT_SKIP`` is
    the pre-push hook's, and it is read before this ever runs.
    """
    env = os.environ if environ is None else environ
    if SCOPE_ENV in env:
        value = env[SCOPE_ENV]
        if value not in SCOPES:
            raise PreflightScopeError(
                f"{SCOPE_ENV}={value!r} is not a scope: set {SCOPE_FULL} or {SCOPE_TOUCHED}, "
                f"or unset it to follow the flag {SCOPE_FLAG_KEY}"
            )
        return ScopeChoice(value, f"{SCOPE_ENV}={value}")
    on = (flag_on or _scope_flag_on)()
    return ScopeChoice(SCOPE_TOUCHED if on else SCOPE_FULL, f"flag {SCOPE_FLAG_KEY} {'on' if on else 'off'}")


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


def _immediate_lane_dep_keys(
    pixi_data: dict[str, Any],
    task_name: str,
    environment: str,
) -> list[LaneKey]:
    """Lane keys this task depends on, expanding aggregates without a ``cmd``."""
    task = _find_task(pixi_data, task_name)
    if task is None:
        raise PreflightConfigError(f"unknown task {task_name!r}")
    keys: list[LaneKey] = []
    for dep in task.get("depends-on", []):
        child_task, child_env = _resolve_dep(dep, environment)
        child = _find_task(pixi_data, child_task)
        if child is None:
            raise PreflightConfigError(f"unknown task {child_task!r}")
        if "cmd" in child:
            keys.append((child_task, child_env))
        else:
            keys.extend(_immediate_lane_dep_keys(pixi_data, child_task, child_env))
    return keys


def _ensure_lane(
    pixi_data: dict[str, Any],
    task_name: str,
    environment: str,
    stack: list[str],
    lanes_by_key: dict[LaneKey, Lane],
    order: list[LaneKey],
) -> None:
    key = (task_name, environment)
    if key in lanes_by_key:
        return
    if task_name in stack:
        raise PreflightConfigError(f"depends-on cycle at task {task_name!r}")
    task = _find_task(pixi_data, task_name)
    if task is None:
        raise PreflightConfigError(f"unknown task {task_name!r}")
    stack.append(task_name)
    try:
        dep_keys = _immediate_lane_dep_keys(pixi_data, task_name, environment)
        for dep_key in dep_keys:
            _ensure_lane(pixi_data, dep_key[0], dep_key[1], stack, lanes_by_key, order)
        if "cmd" not in task:
            return
        lane = Lane(task=task_name, environment=environment, depends_on=tuple(dep_keys))
        lanes_by_key[key] = lane
        order.append(key)
    finally:
        stack.pop()


def _visit_preflight_root(
    pixi_data: dict[str, Any],
    task_name: str,
    environment: str,
    lanes_by_key: dict[LaneKey, Lane],
    order: list[LaneKey],
) -> None:
    task = _find_task(pixi_data, task_name)
    if task is None:
        raise PreflightConfigError(f"unknown task {task_name!r}")
    if "cmd" in task:
        _ensure_lane(pixi_data, task_name, environment, [], lanes_by_key, order)
    else:
        for dep in task.get("depends-on", []):
            child_task, child_env = _resolve_dep(dep, environment)
            _visit_preflight_root(pixi_data, child_task, child_env, lanes_by_key, order)


def list_preflight_lanes(
    pixi_data: dict[str, Any],
    *,
    invoking_env: str | None = None,
) -> list[Lane]:
    """Return one lane per ``(task, environment)`` with a ``cmd``, in declaration order."""
    env = invoking_env if invoking_env is not None else _invoking_environment()
    guild_tasks = pixi_data.get("feature", {}).get("guild-tasks", {}).get("tasks", {})
    if ROOT_AGGREGATE not in guild_tasks:
        raise PreflightConfigError(f"no {ROOT_AGGREGATE!r} task in pixi.toml")
    aggregate = guild_tasks[ROOT_AGGREGATE]
    deps = aggregate.get("depends-on")
    if not deps:
        raise PreflightConfigError(f"{ROOT_AGGREGATE!r} has no depends-on")
    lanes_by_key: dict[LaneKey, Lane] = {}
    order: list[LaneKey] = []
    for dep in deps:
        task_name, lane_env = _resolve_dep(dep, env)
        _visit_preflight_root(pixi_data, task_name, lane_env, lanes_by_key, order)
    return [lanes_by_key[key] for key in order]


@dataclass(frozen=True)
class TouchedCut:
    """What a touched run runs and what it leaves to CI (Story 103.6)."""

    lanes: tuple[Lane, ...]  # what runs, in run order
    deferred: tuple[Lane, ...]  # what CI arbitrates
    reasons: tuple[tuple[LaneKey, str], ...] = ()  # why each lane of ``lanes`` runs
    fast_core: tuple[Lane, ...] = ()  # the detectors that run in place of detectors-ci
    note: str | None = None  # why nothing was cut


def _fast_core_lanes(pixi_data: dict[str, Any], environment: str) -> list[Lane]:
    lanes_by_key: dict[LaneKey, Lane] = {}
    order: list[LaneKey] = []
    for task_name in FAST_CORE_TASKS:
        task = _find_task(pixi_data, task_name)
        if task is None or "cmd" not in task:
            raise PreflightConfigError(f"fast-core task {task_name!r} is not a pixi task with a cmd")
        _ensure_lane(pixi_data, task_name, environment, [], lanes_by_key, order)
    return [lanes_by_key[key] for key in order]


def touched_cut(
    repo_root: Path,
    lanes: Sequence[Lane],
    pixi_data: dict[str, Any],
    selection: preflight_ci.Selection,
) -> TouchedCut:
    """Keep the lanes the diff touches and defer the rest: CI arbitrates them (Story 103.6).

    ``lanes`` are what a full run would run (the selection, after the CI pause filter), in run order. A lane is
    kept when ``preflight_ci.touch_verdict`` says the diff changes its station package, a path its command
    names, or Python under ``src/`` for a lint-and-types lane; a kept lane brings the lanes it depends on.
    ``detectors-ci``, unless kept itself, gives its place and its environment to the fast core. Nothing is cut
    when the selection could not read the diff. Raises :class:`PreflightConfigError` for a missing fast-core task.
    """
    if selection.all_reason:
        return TouchedCut(
            lanes=tuple(lanes),
            deferred=(),
            note=f"the diff cannot be read ({selection.all_reason}), so every selected lane runs",
        )
    changed = preflight_ci.touched_paths(selection)
    lint_tasks = preflight_ci.lint_types_tasks(pixi_data)
    by_key = {_lane_key(lane): lane for lane in lanes}
    reasons: dict[LaneKey, str] = {}
    for lane in lanes:
        verdict = preflight_ci.touch_verdict(repo_root, lane, pixi_data, changed, lint_tasks=lint_tasks)
        if verdict.touched:
            reasons[_lane_key(lane)] = verdict.reason
    pending = list(reasons)
    while pending:
        key = pending.pop()
        for dep_key in by_key[key].depends_on:
            if dep_key in by_key and dep_key not in reasons:
                reasons[dep_key] = f"{lane_label(*key)} depends on it"
                pending.append(dep_key)
    run: list[Lane] = []
    fast_core: list[Lane] = []
    for lane in lanes:
        if _lane_key(lane) in reasons:
            run.append(lane)
        elif lane.task == FAST_CORE_REPLACES and not fast_core:
            fast_core = [
                extra for extra in _fast_core_lanes(pixi_data, lane.environment) if _lane_key(extra) not in by_key
            ]
            for extra in fast_core:
                reasons[_lane_key(extra)] = f"fast core, in place of {lane_label(lane.task, lane.environment)}"
            run.extend(fast_core)
    return TouchedCut(
        lanes=tuple(run),
        deferred=tuple(lane for lane in lanes if _lane_key(lane) not in reasons),
        reasons=tuple((_lane_key(lane), reasons[_lane_key(lane)]) for lane in run),
        fast_core=tuple(fast_core),
    )


def _deferred_journal(deferred: Sequence[Lane]) -> list[dict[str, str]]:
    return [{"lane": lane.task, "environment": lane.environment, "reason": DEFERRED_REASON} for lane in deferred]


def _print_scope(scope: str, source: str, cut: TouchedCut | None) -> None:
    """Name the run's scope, what chose it and every deferred lane on stdout (Story 103.6)."""
    origin = f" ({source})" if source else ""
    if cut is None:
        print(f"preflight: scope {scope}{origin}", flush=True)
        return
    print(
        f"preflight: scope {scope}{origin}: {len(cut.lanes)} lanes run, "
        f"{len(cut.deferred)} deferred -- {DEFERRED_REASON}",
        flush=True,
    )
    if cut.note:
        print(f"preflight: scope {scope}: {cut.note}", flush=True)
    if cut.fast_core:
        replaced = next((reason for key, reason in cut.reasons if key == _lane_key(cut.fast_core[0])), "")
        names = ", ".join(lane.task for lane in cut.fast_core)
        print(f"preflight: {replaced}: {names}", flush=True)
    for lane in cut.deferred:
        print(f"preflight: deferred ({DEFERRED_REASON}): {lane_label(lane.task, lane.environment)}", flush=True)


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
    if prior:
        prior = preflight_suite_reduction.strip_inherited_pytest_basetemp_and_cache(prior)
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
    # One lock per mutex key (a CI service, or the docs-site tree; Story 105.1), created under mutex_guard so two
    # pool threads never make two locks for one key.
    mutex_locks: dict[str, threading.Lock] = field(default_factory=dict)
    mutex_guard: threading.Lock = field(default_factory=threading.Lock)
    active_procs: list[tuple[subprocess.Popen[Any], int]] = field(default_factory=list)
    proc_lock: threading.Lock = field(default_factory=threading.Lock)
    red_lanes: list[LaneKey] = field(default_factory=list)
    # What stopped the run: the red lane's (task, environment), or ("interrupt", None). One
    # tuple, so a reader never sees a trigger without its environment; set only through
    # set_stop_cause, which checks and sets under stop_lock, so the first cause wins.
    stop_cause: tuple[str, str | None] | None = None
    # Reentrant: the SIGINT handler sets the cause on the main thread and may re-enter itself.
    stop_lock: threading.RLock = field(default_factory=threading.RLock)
    terminated_lanes: set[LaneKey] = field(default_factory=set)
    proc_lane: dict[int, LaneKey] = field(default_factory=dict)
    # Keyed by task, not lane: the plan is derived from the pixi task definition, which has no
    # environment, so every lane of a task reads its task's plan. The reduction is therefore
    # applied by task across environments (build_suite_lane_overrides pairs pyforge-<s>-test
    # with pyforge-<s>-coverage-gate by name). It would matter if one station test ran in two
    # environments while its gate ran in one: the other environment's lane would skip tests
    # the gate never ran there. No lane list does that today; the plan would then need a lane key.
    suite_lane_plan: dict[str, preflight_suite_reduction.SuiteLaneOverride | dict[str, Any]] = field(
        default_factory=dict
    )
    suite_reduction_runtime_journal: dict[LaneKey, dict[str, Any]] = field(default_factory=dict)
    xdist_workers: dict[LaneKey, int] = field(default_factory=dict)
    subprocess_argv_for_lane: Callable[[Lane], list[str]] | None = None
    before_popen: Callable[[LaneRunContext], None] | None = None
    between_segments: Callable[[LaneRunContext, int], None] | None = None

    @property
    def stop_trigger(self) -> str | None:
        """The journaled ``cancelled_by`` of a stop: the red lane's task, or ``interrupt``."""
        cause = self.stop_cause
        return cause[0] if cause is not None else None

    def set_stop_cause(self, cause: tuple[str, str | None]) -> None:
        """Record what stopped the run; the first cause wins (checked and set under ``stop_lock``)."""
        with self.stop_lock:
            if self.stop_cause is None:
                self.stop_cause = cause

    def mutex_lock(self, key: str) -> threading.Lock:
        """The one lock for ``key``, made under ``mutex_guard``: two pool threads never get two locks for one key."""
        with self.mutex_guard:
            return self.mutex_locks.setdefault(key, threading.Lock())

    def register_proc(self, proc: subprocess.Popen[Any], lane: LaneKey) -> None:
        with self.proc_lock:
            if self.cancel.is_set() or (self.stop_on_red.is_set() and not self.keep_going):
                self.terminated_lanes.add(lane)
                late_proc = proc
            else:
                self.active_procs.append((proc, proc.pid))
                self.proc_lane[proc.pid] = lane
                late_proc = None
        if late_proc is not None:
            _terminate_proc_group(late_proc)

    def unregister_proc(self, proc: subprocess.Popen[Any]) -> None:
        with self.proc_lock:
            self.active_procs = [(p, pid) for p, pid in self.active_procs if p is not proc]
            self.proc_lane.pop(proc.pid, None)

    def terminate_children(self) -> None:
        with self.proc_lock:
            procs = list(self.active_procs)
        for proc, _pid in procs:
            if proc.poll() is not None:
                continue
            with self.proc_lock:
                lane = self.proc_lane.get(proc.pid)
                if lane is not None:
                    self.terminated_lanes.add(lane)
            _terminate_proc_group(proc)


def _stop_cause(coord: _RunCoordinator, default: str) -> tuple[str, str | None]:
    """The stop's ``(cancelled_by, cancelled_by_environment)``, or ``(default, None)`` before one is set."""
    cause = coord.stop_cause
    return cause if cause is not None else (default, None)


def _terminate_proc_group(proc: subprocess.Popen[Any]) -> None:
    if proc.poll() is not None:
        return
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
    if coord.before_popen is not None:
        coord.before_popen(ctx)
    proc = subprocess.Popen(
        argv,
        cwd=coord.repo_root,
        env=ctx.env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    coord.register_proc(proc, _lane_key(ctx.lane))
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
    key = _lane_key(ctx.lane)
    segment_rows: list[dict[str, Any]] = []
    task_collect_exit: int | None = None
    lane_exit = 0
    prefix = ["pixi", "run", "--frozen", "-e", ctx.lane.environment, "--"]

    def _append_not_run(from_index: int) -> None:
        for pending in override.segments[from_index:]:
            segment_rows.append(
                {
                    "label": pending.label,
                    "command": shlex.join(pending.argv),
                    "exit_code": None,
                    "outcome": "not-run",
                }
            )

    def _run_stopped_before_segment(index: int) -> bool:
        if coord.cancel.is_set() or (coord.stop_on_red.is_set() and not coord.keep_going):
            _append_not_run(index)
            coord.terminated_lanes.add(key)
            return True
        return False

    with ctx.log_path.open("wb") as log_handle:
        for index, segment in enumerate(override.segments):
            if index >= 1 and coord.between_segments is not None:
                coord.between_segments(ctx, index)
            if _run_stopped_before_segment(index):
                break
            cmd = [*prefix, *segment.argv]
            code = _run_pixi_argv(coord, ctx, cmd, log_handle)
            if key in coord.terminated_lanes:
                segment_rows.append(
                    {
                        "label": segment.label,
                        "command": shlex.join(segment.argv),
                        "exit_code": code,
                        "outcome": "cancelled",
                    }
                )
                for pending in override.segments[index + 1 :]:
                    segment_rows.append(
                        {
                            "label": pending.label,
                            "command": shlex.join(pending.argv),
                            "exit_code": None,
                            "outcome": "not-run",
                        }
                    )
                lane_exit = code
                break
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
            if _run_stopped_before_segment(len(override.segments)):
                pass
            elif segment_rows and all(row["outcome"] == "no-tests-selected" for row in segment_rows):
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
    coord.suite_reduction_runtime_journal[key] = journal_extra
    return lane_exit


def _subprocess_lane(coord: _RunCoordinator, ctx: LaneRunContext) -> int:
    ctx.log_path.parent.mkdir(parents=True, exist_ok=True)
    plan_entry = coord.suite_lane_plan.get(ctx.lane.task)
    if isinstance(plan_entry, preflight_suite_reduction.SuiteLaneOverride):
        return _subprocess_reduced_suite_lane(coord, ctx, plan_entry)
    if coord.subprocess_argv_for_lane is not None:
        argv = coord.subprocess_argv_for_lane(ctx.lane)
    else:
        argv = [
            "pixi",
            "run",
            "--frozen",
            "--skip-deps",
            "-e",
            ctx.lane.environment,
            ctx.lane.task,
        ]
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


def _lane_journal_extra(coord: _RunCoordinator, lane: Lane) -> dict[str, Any] | None:
    runtime = coord.suite_reduction_runtime_journal.get(_lane_key(lane))
    if runtime is not None:
        return dict(runtime)
    entry = coord.suite_lane_plan.get(lane.task)
    if isinstance(entry, preflight_suite_reduction.SuiteLaneOverride):
        return dict(entry.journal)
    if isinstance(entry, dict):
        return dict(entry)
    return None


_OPTIONAL_RESULT_KEYS = ("cancelled_by", "cancelled_by_environment", "blocked_by", "blocked_by_environment")


def _lane_result_dict(result: LaneResult) -> dict[str, Any]:
    payload = asdict(result)
    extra = payload.pop("journal_extra", None)
    for name in _OPTIONAL_RESULT_KEYS:
        value = payload.pop(name, None)
        if value is not None:
            payload[name] = value
    if extra:
        payload.update(extra)
    return payload


def _lane_key(lane: Lane) -> LaneKey:
    return (lane.task, lane.environment)


def _lane_log_path(scratch_root: Path, task: str, environment: str) -> Path:
    return scratch_root / f"{lane_label(task, environment)}.log"


def _dependency_blocker(lane: Lane, completed: dict[LaneKey, LaneResult]) -> tuple[str, str | None] | None:
    """Return the ``(task, environment)`` of the red lane that blocks ``lane`` (environment ``None`` when the
    cause is no lane), or ``None`` when every dependency is ``ok``."""
    for dep_key in lane.depends_on:
        result = completed.get(dep_key)
        if result is None:
            return None
        if result.status == "red":
            return (result.task, result.environment)
        if result.status == "cancelled" and result.cancelled_by is not None:
            return (result.cancelled_by, result.cancelled_by_environment)
        if result.status == "not-run" and result.blocked_by is not None:
            return (result.blocked_by, result.blocked_by_environment)
        if result.status != "ok":
            return (result.task, result.environment)
    return None


def _deps_all_ok(lane: Lane, completed: dict[LaneKey, LaneResult]) -> bool:
    if not lane.depends_on:
        return True
    for dep_key in lane.depends_on:
        result = completed.get(dep_key)
        if result is None or result.status != "ok":
            return False
    return True


def _needed_by_pending_dependent(lane: Lane, pending: dict[LaneKey, Lane]) -> bool:
    """True when some not-yet-finished lane still depends on ``lane``."""
    key = _lane_key(lane)
    return any(key in other.depends_on for other in pending.values())


def _skip_lane_on_red_stop(coord: _RunCoordinator, lane: Lane, pending: dict[LaneKey, Lane]) -> bool:
    """Whether a red stop should prevent ``lane`` from running (Story 88.1 AC4)."""
    if not coord.stop_on_red.is_set() or coord.keep_going:
        return False
    return not _needed_by_pending_dependent(lane, pending)


def _blocked_lane_result(lane: Lane, blocker: tuple[str, str | None], *, keep_going: bool) -> LaneResult:
    name, environment = blocker
    if keep_going:
        return LaneResult(
            lane.task,
            lane.environment,
            0.0,
            0,
            "not-run",
            0.0,
            blocked_by=name,
            blocked_by_environment=environment,
        )
    return LaneResult(
        lane.task,
        lane.environment,
        0.0,
        0,
        "cancelled",
        0.0,
        cancelled_by=name,
        cancelled_by_environment=environment,
    )


def _run_lane_in_pool(
    coord: _RunCoordinator,
    lane: Lane,
    scratch_root: Path,
    mutex_keys: tuple[str, ...],
    runner: Callable[[LaneRunContext], int],
    use_subprocess: bool,
    pending: dict[LaneKey, Lane],
) -> LaneResult:
    key = _lane_key(lane)
    if coord.cancel.is_set():
        return LaneResult(lane.task, lane.environment, 0.0, 0, "cancelled", 0.0)
    if _skip_lane_on_red_stop(coord, lane, pending):
        trigger, trigger_env = _stop_cause(coord, "red")
        return LaneResult(
            lane.task,
            lane.environment,
            0.0,
            0,
            "cancelled",
            0.0,
            cancelled_by=trigger,
            cancelled_by_environment=trigger_env,
        )

    # Story 105.1: every mutex the lane holds (its CI service, the docs-site tree), taken in one sorted order, so two
    # lanes that each wait for the other's key cannot exist; released in reverse, whatever the lane did.
    held: list[threading.Lock] = []
    try:
        for name in sorted(set(mutex_keys)):
            lock = coord.mutex_lock(name)
            lock.acquire()
            held.append(lock)
        if coord.cancel.is_set():
            return LaneResult(lane.task, lane.environment, 0.0, 0, "cancelled", 0.0)
        if _skip_lane_on_red_stop(coord, lane, pending):
            trigger, trigger_env = _stop_cause(coord, "red")
            return LaneResult(
                lane.task,
                lane.environment,
                0.0,
                0,
                "cancelled",
                0.0,
                cancelled_by=trigger,
                cancelled_by_environment=trigger_env,
            )

        lane_dir = scratch_root / lane_label(lane.task, lane.environment)
        log_path = _lane_log_path(scratch_root, lane.task, lane.environment)
        env = _lane_scratch_env(lane_dir)
        workers = coord.xdist_workers.get(key)
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

        journal_extra = _lane_journal_extra(coord, lane)
        if key in coord.terminated_lanes:
            trigger, trigger_env = _stop_cause(coord, "interrupt")
            return LaneResult(
                lane.task,
                lane.environment,
                elapsed,
                code,
                "cancelled",
                start_offset,
                journal_extra,
                cancelled_by=trigger,
                cancelled_by_environment=trigger_env,
            )
        if code == 0:
            return LaneResult(lane.task, lane.environment, elapsed, 0, "ok", start_offset, journal_extra)
        coord.red_lanes.append(key)
        if not coord.keep_going:
            coord.set_stop_cause(key)
            coord.stop_on_red.set()
            coord.terminate_children()
        return LaneResult(lane.task, lane.environment, elapsed, code, "red", start_offset, journal_extra)
    finally:
        for lock in reversed(held):
            lock.release()


def run_preflight(
    repo_root: Path,
    *,
    pixi_path: Path | None = None,
    invoking_env: str | None = None,
    run_lane: Callable[[Lane], int] | None = None,
    run_lane_ctx: Callable[[LaneRunContext], int] | None = None,
    jobs: int | None = None,
    keep_going: bool = False,
    ignore_ci_pauses: bool = False,
    install_environment: Callable[[str], int] | None = None,
    scratch_parent: Path | None = None,
    subprocess_argv_for_lane: Callable[[Lane], list[str]] | None = None,
    before_popen: Callable[[LaneRunContext], None] | None = None,
    between_segments: Callable[[LaneRunContext, int], None] | None = None,
    scope: str = SCOPE_FULL,
    scope_source: str = "",
) -> int:
    """Run CI-selected lanes; return exit code 0 / 1 / 2 / 130.

    ``scope`` is ``full`` (every selected lane) or ``touched`` (Story 103.6: see :func:`touched_cut`);
    ``scope_source`` says what chose it, for the run's stdout.
    """
    if scope not in SCOPES:
        print(f"preflight: scope {scope!r} is not one of {', '.join(SCOPES)}", file=sys.stderr)
        return EXIT_CONFIG
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

    flag_on = preflight_ci._flag_on(repo_root)  # noqa: SLF001 — shared pause gate
    resolution = preflight_ci.resolve_ci_vars(repo_root, flag_on=flag_on)
    var_lookup = resolution.lookup if flag_on else None
    selection = preflight_ci.select_lanes(repo_root, lanes, pixi_data, var_lookup=var_lookup)
    paused_lanes: list[preflight_ci.PausedLane] = []
    paused_results: list[LaneResult] = []
    if flag_on:
        surface_paused = preflight_ci.list_paused_ci_surfaces(repo_root, resolution)
        lane_paused = preflight_ci.discover_paused_lanes(repo_root, lanes, pixi_data, resolution)
        # The banner prints CI surfaces, and a registry row names no environment, so its lines
        # de-duplicate by task; which lanes run is decided per (task, environment) below.
        banner_lines: dict[str, preflight_ci.PausedLane] = {entry.task: entry for entry in surface_paused}
        for entry in lane_paused:
            banner_lines.setdefault(entry.task, entry)
        paused_lanes = list(banner_lines.values())
        if paused_lanes:
            preflight_ci.print_ci_pause_banner(repo_root, paused_lanes, resolution=resolution)
        paused_lanes = lane_paused
        paused_keys = {(entry.task, entry.environment) for entry in paused_lanes}
        run_lanes = [lane for lane in lanes if selection.is_selected(lane)]
        if ignore_ci_pauses and paused_keys:
            for lane in lanes:
                if _lane_key(lane) in paused_keys and lane not in run_lanes:
                    run_lanes.append(lane)
        elif paused_keys:
            for entry in paused_lanes:
                paused_results.append(
                    LaneResult(
                        entry.task,
                        entry.environment,
                        0.0,
                        0,
                        "not-run",
                        0.0,
                        {"verdict": entry.journal_verdict()},
                    )
                )
            run_lanes = [lane for lane in run_lanes if _lane_key(lane) not in paused_keys]
        lanes = run_lanes
    else:
        lanes = [lane for lane in lanes if selection.is_selected(lane)]
    skipped_count = len(selection.verdicts) - len(lanes)
    cut: TouchedCut | None = None
    if scope == SCOPE_TOUCHED:
        try:
            cut = touched_cut(repo_root, lanes, pixi_data, selection)
        except PreflightConfigError as exc:
            print(f"preflight: {exc}", file=sys.stderr)
            return EXIT_CONFIG
        lanes = list(cut.lanes)
    deferred: tuple[Lane, ...] = cut.deferred if cut is not None else ()
    note = f" ({selection.all_reason})" if selection.all_reason else ""
    if cut is None:
        counted = f"running {len(lanes)} of {len(selection.verdicts)} lanes"
    else:
        counted = (
            f"running {len(lanes)} lanes ({len(lanes) - len(cut.fast_core)} of {len(selection.verdicts)} "
            f"and {len(cut.fast_core)} fast-core detectors)"
        )
    deferred_note = f", {len(deferred)} deferred to CI" if cut is not None else ""
    print(
        f"preflight: {counted}, {skipped_count} skipped by their workflow's own rules{deferred_note}{note}",
        file=sys.stderr,
    )
    _print_scope(scope, scope_source, cut)

    worker_count = jobs if jobs is not None else _logical_core_count()
    if worker_count < 1:
        worker_count = 1

    mutex_keys = lane_mutex_keys(lanes, preflight_ci.static_service_mutex_keys(repo_root, lanes, pixi_data))
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
        lanes=[_lane_key(lane) for lane in lanes],
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
        subprocess_argv_for_lane=subprocess_argv_for_lane,
        before_popen=before_popen,
        between_segments=between_segments,
    )
    if injected_runner is not None:
        runner = injected_runner
    else:

        def runner(ctx: LaneRunContext) -> int:
            return _default_run_lane_ctx(coord, ctx)

    prior_sigint = signal.getsignal(signal.SIGINT)

    def _on_sigint(_signum: int, _frame: object | None) -> None:
        coord.cancel.set()
        coord.set_stop_cause(("interrupt", None))
        coord.terminate_children()

    signal.signal(signal.SIGINT, _on_sigint)

    results_by_key: dict[LaneKey, LaneResult] = {}
    pending: dict[LaneKey, Lane] = {_lane_key(lane): lane for lane in lanes}
    completed: dict[LaneKey, LaneResult] = {}
    try:
        with ThreadPoolExecutor(max_workers=worker_count) as pool:
            futures: dict[Future[LaneResult], Lane] = {}

            def _record_done(lane: Lane, result: LaneResult) -> None:
                completed[_lane_key(lane)] = result
                results_by_key[_lane_key(lane)] = result

            def _mark_dependency_blocked() -> None:
                for key in list(pending.keys()):
                    lane = pending[key]
                    if any(completed.get(dep_key) is None for dep_key in lane.depends_on):
                        continue
                    blocker = _dependency_blocker(lane, completed)
                    if blocker is None:
                        continue
                    _record_done(lane, _blocked_lane_result(lane, blocker, keep_going=keep_going))
                    del pending[key]

            while pending or futures:
                if coord.cancel.is_set() and not futures:
                    break

                _mark_dependency_blocked()

                while len(futures) < worker_count:
                    # Story 105.1: a lane whose mutex an in-flight lane holds would only wait in its slot; it stays
                    # pending and is offered again when that lane finishes, so the slot goes to a lane that can run.
                    busy = {name for running in futures.values() for name in mutex_keys[_lane_key(running)]}
                    ready_candidates: list[Lane] = []
                    for candidate in lanes:
                        key = _lane_key(candidate)
                        if key not in pending or not _deps_all_ok(candidate, completed):
                            continue
                        if _skip_lane_on_red_stop(coord, candidate, pending):
                            continue
                        if busy.intersection(mutex_keys[key]):
                            continue
                        ready_candidates.append(candidate)
                    if not ready_candidates:
                        break
                    if coord.stop_on_red.is_set() and not coord.keep_going:
                        ready_candidates.sort(
                            key=lambda lane: (
                                not _needed_by_pending_dependent(lane, pending),
                                lanes.index(lane),
                            )
                        )
                    else:
                        ready_candidates.sort(key=lambda lane: lanes.index(lane))
                    ready = ready_candidates[0]
                    key = _lane_key(ready)
                    del pending[key]
                    fut = pool.submit(
                        _run_lane_in_pool,
                        coord,
                        ready,
                        scratch_root,
                        mutex_keys[key],
                        runner,
                        use_subprocess,
                        pending,
                    )
                    futures[fut] = ready

                stopped = coord.stop_on_red.is_set() and not coord.keep_going

                if not futures:
                    if not pending or stopped:
                        break
                    continue

                done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
                for fut in done:
                    lane = futures.pop(fut)
                    try:
                        result = fut.result()
                    except Exception:  # noqa: BLE001
                        result = LaneResult(lane.task, lane.environment, 0.0, 1, "red", 0.0)
                    _record_done(lane, result)

                if stopped:
                    while futures:
                        done_wait, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
                        for fut in done_wait:
                            lane = futures.pop(fut)
                            try:
                                result = fut.result()
                            except Exception:  # noqa: BLE001
                                result = LaneResult(lane.task, lane.environment, 0.0, 1, "red", 0.0)
                            _record_done(lane, result)
                    _mark_dependency_blocked()
                    break
    finally:
        signal.signal(signal.SIGINT, prior_sigint)
        coord.terminate_children()

    if coord.cancel.is_set():
        total_seconds = time.monotonic() - t0
        ordered: list[LaneResult] = []
        for lane in lanes:
            if _lane_key(lane) in results_by_key:
                ordered.append(results_by_key[_lane_key(lane)])
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
                "mode": scope,
                "deferred": _deferred_journal(deferred),
                "selection": selection.to_journal(),
                "lanes": [_lane_result_dict(r) for r in ordered],
            },
        )
        _announce_scratch_kept(scratch_root)
        return EXIT_INTERRUPT

    ordered_results: list[LaneResult] = []
    exit_code = EXIT_OK
    for lane in lanes:
        if _lane_key(lane) in results_by_key:
            result = results_by_key[_lane_key(lane)]
        elif coord.stop_on_red.is_set() and not coord.keep_going:
            result = LaneResult(lane.task, lane.environment, 0.0, 0, "cancelled", 0.0)
        else:
            result = LaneResult(lane.task, lane.environment, 0.0, 0, "not-run", 0.0)
        ordered_results.append(result)
        if result.status == "red":
            exit_code = EXIT_LANE_RED
            lane_log = _lane_log_path(scratch_root, lane.task, lane.environment)
            print(
                f"preflight: lane {lane.task!r} in environment {lane.environment!r} "
                f"exited {result.exit_code} (log: {lane_log})",
                file=sys.stderr,
            )

    if keep_going and coord.red_lanes:
        exit_code = EXIT_LANE_RED
        for task, environment in coord.red_lanes:
            lane_log = _lane_log_path(scratch_root, task, environment)
            print(
                f"preflight: red lane {task!r} in environment {environment!r} (log: {lane_log})",
                file=sys.stderr,
            )

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
            "mode": scope,
            "deferred": _deferred_journal(deferred),
            "selection": {
                **selection.to_journal(),
                **({"ci_var_source": resolution.source} if flag_on else {}),
                **(
                    {
                        "ci_pause_override": [
                            f"ran despite pause (--ignore-ci-pauses): {entry.journal_verdict()}"
                            for entry in paused_lanes
                        ]
                    }
                    if flag_on and ignore_ci_pauses and paused_lanes
                    else {}
                ),
            },
            "lanes": [_lane_result_dict(r) for r in ordered_results] + [_lane_result_dict(r) for r in paused_results],
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
    parser.add_argument(
        "--ignore-ci-pauses",
        action="store_true",
        help="run lanes paused in CI anyway (Story 99.5)",
    )
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    argv_list = list(argv or [])
    if argv_list and ("--budget" in argv_list or argv_list[0] == "--budget"):
        from pyforge.steward import preflight_budget

        return preflight_budget.main(argv_list)
    args = _parse_args(argv_list)
    try:
        choice = resolve_scope()
    except PreflightScopeError as exc:
        print(f"preflight: {exc}", file=sys.stderr)
        return EXIT_CONFIG
    except FlagConfigError as exc:
        print(f"preflight: cannot read the flag {SCOPE_FLAG_KEY}: {exc}", file=sys.stderr)
        return EXIT_CONFIG
    repo_root = Path(os.environ.get("PIXI_PROJECT_ROOT", ".")).resolve()
    return run_preflight(
        repo_root,
        jobs=args.jobs,
        keep_going=args.keep_going,
        ignore_ci_pauses=args.ignore_ci_pauses,
        scope=choice.scope,
        scope_source=choice.source,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
