"""Concurrent ``pr-preflight`` runner with per-lane journaling (Stories 71.1–71.3, CAP-159).

Reads ``pr-preflight-lanes`` from ``pixi.toml``, builds one lane per
``(task, environment)`` with a ``cmd`` and dependency edges from ``depends-on``,
selects the lanes CI would run for the diff (Story 71.2,
``preflight_ci``: read from ``.github/workflows/*.yml`` at run time), installs
each needed environment serially, runs selected lanes in a pool bounded by
``--jobs``, and appends JSON lines to ``.steward/preflight-runs.jsonl``.
Lanes that share a CI service container, or the ``docs-site/`` tree, share a mutex and never run at once
(Stories 71.3, 105.1; :func:`lane_mutex_keys`). A lane whose task is in :data:`ALONE_TAIL_TASKS` runs its command's
last ``&&`` segment with no other lane in flight (Story 117.30).
A lane is its task and its environment wherever the runner keeps per-lane state —
results, scratch, logs, stop marks, journal extras, worker shares (Story 103.5):
one task may run in two environments.
A run has a scope (Story 103.6): ``full`` runs every selected lane; ``touched`` runs only the lanes the diff
changes, the five fast-core detectors in place of ``detectors-ci`` and lint and types when Python under ``src/``
changed, and journals every other lane as deferred: CI arbitrates it. ``PYFORGE_PREFLIGHT_SCOPE`` chooses the
scope, or, unset, the flag ``pyforge.steward.preflight_ci_arbitrates``; ``main`` resolves it, so
``run_preflight`` defaults to ``full``. ``steward preflight verify-deferred`` is the catch-up.
A run in which a lane depends on a lane outside it refuses before any install (Story 107.1;
:func:`stranded_dependencies`): such a lane would never start, and nothing in CI runs it with that dependency.
Not a steward CLI duty — ``main()`` owns the exit code (AD-8).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shlex
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
import uuid
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from pyforge.core.flags import FlagConfigError, read_boolean

try:  # the CPU a lane used is read from this process's children total; Windows has no ``resource`` module
    import resource
except ImportError:  # pragma: no cover
    resource = None  # type: ignore[assignment]

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
#: Story 117.3 (spec-pyforge-steward CAP-175): ON, ready lanes are admitted longest-expected first and by the cores
#: they will use (an xdist lane takes a share of the free cores at admission); OFF, declaration order and the static
#: per-lane share of Story 71.6. A kill switch: on everywhere.
CRITICAL_PATH_FLAG_KEY = "pyforge.steward.preflight_critical_path"
#: Story 117.3: what a lane with no journal history weighs to the scheduler, in seconds, and how many of its last
#: green runs feed its expected seconds.
UNKNOWN_LANE_SECONDS = 30.0
LANE_MEDIAN_RUNS = 5
#: Story 117.15: an xdist lane is given the workers that finish its expected work in this fraction of the run's ideal
#: length (the expected work of every selected lane over the machine's cores). Half: a heavy lane ends by the middle
#: of the run and its cores go to the lanes behind it (:func:`preflight_xdist.xdist_share_at_admission`).
LANE_TARGET_FRACTION = 0.5
#: The tracked per-lane budgets (Story 117.5). ``preflight-budget`` judges against them after a run and never changes
#: its exit code; since Story 117.15 the run itself reads the ``[lanes]`` table (seconds) and the ``[work]`` table
#: (seconds times workers, for the xdist lanes), and only to order and size lanes its journal has no green run of.
BUDGETS_RELATIVE = Path("docs/governance/preflight-budgets.toml")
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
# Herald Story 45.1: the install every other docs-site lane reads. A touched run keeps it beside any kept docs-site lane
# (touched_cut), because pyforge-herald-test declares no dependency on it: pyforge-station-tests and the SBOM laptop
# gate run that task and stay npm-free (fnd:CAP-13). pr-preflight-lanes declares it before the station suites, so it
# takes the docs-site lanes' first turn (_next_lane).
DOCS_SITE_INSTALL_TASK = "docs-site-install"
DOCS_SITE_TASKS = frozenset(
    {
        "docs-site-install",  # npm ci: deletes docs-site/node_modules and installs it again
        "docs-site-build",  # astro build: rewrites docs-site/public/ and writes docs-site/build/site/
        "pages-build",  # the same build, through docs-site/scripts/pages.mts
        "pages-check",  # pages.mts check: reads docs-site/build/site/, which the builds write
        "docs-site-validate-sidebar",  # nav-check.mts imports the yaml package from docs-site/node_modules
        "pyforge-herald-test",  # herald's package half: the derivation takes every run of herald's suite
        "pyforge-herald-live-test",  # its built-site tests run astro build in docs-site/ (pages_astro.astro_build)
        "pyforge-herald-coverage-gate",  # herald's unit suite under coverage, its built-site test included
        "pyforge-herald-test-coverage",  # herald's whole suite under coverage
    }
)

# Story 117.30 (spec-pyforge-steward CAP-175, a fix under CAP-159: a lane's verdict never depends on the other lanes'
# load): the tasks whose command ends in a segment that measures its own CPU time. Such a lane runs the segments
# before its last ``&&`` beside the other lanes; its last segment, the "alone tail", runs once no other lane is in
# flight or ready, and no lane starts while it runs. Doctor's five-second budget test spends more CPU when other lanes
# share the cores (a median of 5.03 s against 5.0 s at a load average of 13.7, 2026-11-27), and passes alone.
# tests/meta/test_preflight_alone_tail_tasks.py holds each named task to a command with a serial tail.
ALONE_TAIL_TASKS = frozenset({"pyforge-doctor-live-test"})
PART_WHOLE = "whole"
PART_HEAD = "head"
PART_TAIL = "tail"
# A segment is run as one argv through ``pixi run -- <argv>``, so it may hold no shell syntax for a shell to read.
_SHELL_TOKENS = frozenset({"|", "||", "&", ";", "<", ">", ">>", "2>&1"})


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
    # Story 117.30: PART_WHOLE runs the task; an alone-tail lane runs as PART_HEAD, then PART_TAIL.
    part: str = PART_WHOLE


@dataclass(frozen=True)
class AloneTail:
    """An :data:`ALONE_TAIL_TASKS` task's command split at ``&&`` (Story 117.30): each segment an argv for
    ``pixi run -- <argv>``, and the task's own ``env``, which ``pixi run <task>`` would have set."""

    head: tuple[tuple[str, ...], ...]
    tail: tuple[str, ...]
    env: Mapping[str, str]


def alone_tail_plan(pixi_data: dict[str, Any], task_name: str) -> AloneTail | None:
    """The head segments and the tail of ``task_name``'s command, or ``None`` when it has none (Story 117.30).

    ``None`` when the task is missing, its ``cmd`` is not one string, it has no ``&&``, a segment is empty or does
    not parse, a segment holds shell syntax or a ``$`` expansion, or the task's ``env`` does: each segment runs as one
    argv, with no shell to read them.
    """
    task = _find_task(pixi_data, task_name)
    if not isinstance(task, dict):
        return None
    cmd = task.get("cmd")
    if not isinstance(cmd, str):
        return None
    parts = [part.strip() for part in cmd.split("&&")]
    if len(parts) < 2 or not all(parts):
        return None
    try:
        argvs = [tuple(shlex.split(part)) for part in parts]
    except ValueError:
        return None
    if any(token in _SHELL_TOKENS or "$" in token for argv in argvs for token in argv):
        return None
    raw_env = task.get("env", {})
    if not isinstance(raw_env, dict):
        return None
    env = {str(name): str(value) for name, value in raw_env.items()}
    if any("$" in value for value in env.values()):
        return None
    return AloneTail(head=tuple(argvs[:-1]), tail=argvs[-1], env=env)


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


def lane_medians(journal_path: Path, *, last_n: int = LANE_MEDIAN_RUNS) -> dict[LaneKey, float]:
    """Each lane's median wall seconds over its last ``last_n`` green runs in the journal (Story 117.3).

    Keyed by ``(task, environment)``; only runs whose verdict is ``ok`` and lanes whose status is ``ok`` count, newest
    first, so a cancelled or red lane leaves no mark. A lane absent from the result has no history and weighs
    :data:`UNKNOWN_LANE_SECONDS`. Reads the journal this module writes; a missing or malformed line is skipped.
    """
    if not journal_path.is_file():
        return {}
    runs: list[dict[str, Any]] = []
    for line in journal_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and "lanes" in record and record.get("verdict") == "ok":
            runs.append(record)
    samples: dict[LaneKey, list[float]] = {}
    for run in reversed(runs):
        for lane in run.get("lanes") or []:
            if not isinstance(lane, dict) or lane.get("status") != "ok":
                continue
            key = (str(lane.get("task")), str(lane.get("environment")))
            values = samples.setdefault(key, [])
            if len(values) < last_n:
                values.append(float(lane.get("seconds", 0.0)))
    return {key: statistics.median(values) for key, values in samples.items() if values}


def lane_work_medians(journal_path: Path, *, last_n: int = LANE_MEDIAN_RUNS) -> dict[LaneKey, float]:
    """Each lane's median work in core-seconds over its last green runs (Story 117.15).

    The CPU seconds the lane's processes used (``cpu_seconds``, measured when the lane is reaped) where its journal
    entry carries them; else its wall seconds times the workers it ran on (``xdist_workers``); a lane with neither
    is absent. Work, not seconds, sizes a lane's share at admission: seconds fall when a lane is given more workers,
    so a share sized by seconds would swing from run to run. Measured CPU is the better of the two readings: seconds
    times workers grows with every worker a lane is given and cannot use (herald's built-site tests build in one
    worker), which would hand such a lane more workers on each run.
    """
    if not journal_path.is_file():
        return {}
    runs: list[dict[str, Any]] = []
    for line in journal_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and "lanes" in record and record.get("verdict") == "ok":
            runs.append(record)
    samples: dict[LaneKey, list[float]] = {}
    for run in reversed(runs):
        for lane in run.get("lanes") or []:
            if not isinstance(lane, dict) or lane.get("status") != "ok":
                continue
            cpu = lane.get("cpu_seconds")
            workers = lane.get("xdist_workers")
            if isinstance(cpu, int | float) and not isinstance(cpu, bool) and math.isfinite(cpu) and cpu > 0:
                sample = float(cpu)
            elif isinstance(workers, int) and not isinstance(workers, bool) and workers >= 1:
                sample = float(lane.get("seconds", 0.0)) * workers
            else:
                continue
            key = (str(lane.get("task")), str(lane.get("environment")))
            values = samples.setdefault(key, [])
            if len(values) < last_n:
                values.append(sample)
    return {key: statistics.median(values) for key, values in samples.items() if values}


def _budget_table(repo_root: Path, table: str) -> dict[LaneKey, float]:
    """One ``"task@environment" = number`` table of the tracked budgets file, keyed as the journal keys a lane."""
    try:
        data = tomllib.loads((repo_root / BUDGETS_RELATIVE).read_text(encoding="utf-8"))
    except OSError, ValueError:
        return {}
    rows = data.get(table)
    seeds: dict[LaneKey, float] = {}
    for label, number in (rows if isinstance(rows, dict) else {}).items():
        task, sep, environment = str(label).rpartition("@")
        if not (isinstance(number, int | float) and not isinstance(number, bool) and math.isfinite(number)):
            continue
        if sep and task and environment and number >= 0:
            seeds[(task, environment)] = float(number)
    return seeds


def budget_seed_seconds(repo_root: Path) -> dict[LaneKey, float]:
    """Each lane's tracked budget in seconds, keyed as the journal keys it (Story 117.15).

    The expected seconds of a lane the journal has no green run of: a fresh worktree's journal is empty, and it is
    where a full preflight most often runs. A missing or unreadable file, or a row that is not ``task@environment``
    with a number, seeds nothing: the run then orders that lane as before, by :data:`UNKNOWN_LANE_SECONDS`.
    """
    return _budget_table(repo_root, "lanes")


def budget_seed_work(repo_root: Path) -> dict[LaneKey, float]:
    """Each xdist lane's tracked work, its seconds times the workers it ran on (the ``[work]`` table; Story 117.15).

    The seed of a lane's share where the journal has no green run of it: seconds alone do not say how many workers
    took them. A lane with no row is sized from its seconds at the minimum share, as before.
    """
    return _budget_table(repo_root, "work")


#: Story 117.17: ``PYFORGE_PREFLIGHT_REUSE=0`` runs the lanes even when the journal holds a green run of this tree.
REUSE_ENV = "PYFORGE_PREFLIGHT_REUSE"
#: The variables a lane's verdict can depend on besides the tree; a run and the run it reuses must agree on them.
#: ``PYTEST_ADDOPTS`` is one: every pytest lane inherits it, and it can deselect tests (``-k``, ``--splits``).
_REUSE_ENV_PREFIXES = ("PYFORGE_", "HERALD_", "CI", "PYTEST_ADDOPTS")
_REUSE_ENV_IGNORED = frozenset({REUSE_ENV, SCOPE_ENV, "PYFORGE_PREFLIGHT_SKIP", "PYFORGE_PREFLIGHT_SKIP_REASON"})
#: Tokens a detector's GitHub probe reads: whether each is set is part of the state, its value never is (an
#: unauthenticated probe fails open, AGENTS.md § Known pitfalls, so a run without a token is another run).
_REUSE_ENV_PRESENCE = ("GH_TOKEN", "GITHUB_TOKEN")
#: How old a green run may be and still be reused. Some lanes judge more than the tree, the commit and the day: loop
#: homes under the home directory, refs, what GitHub answers. A run cannot hash those, so its verdict stands only for
#: the push that follows it: half an hour, about three times the length of a full run.
REUSE_MAX_AGE_SECONDS = 1800.0


def reuse_enabled() -> bool:
    """Whether a run may reuse a green verdict (Story 117.17): on unless :data:`REUSE_ENV` is ``0``."""
    return os.environ.get(REUSE_ENV, "1").strip() != "0"


def _today() -> str:
    """The local date, as the detectors that judge an expiry read it (``date.today()``)."""
    return date.today().isoformat()


@dataclass(frozen=True)
class TreeState:
    """What a verdict was reached on (Story 117.17): the tree, the commit, the base its diff was read against, the
    local day, and the environment variables a lane can read.

    The commit is its own field because some detectors judge history, not content: a squash or a reworded subject
    keeps the tree and changes what they read. The day is one because some judge a date (a flag past its clock, an
    exemption past its expiry). ``clean`` is false when a tracked file differs from ``HEAD`` or an untracked,
    unignored file exists: such a tree has no hash to compare, so its verdict is never reused.
    """

    tree_sha: str
    head_sha: str
    base_sha: str
    env_digest: str
    day: str
    clean: bool

    def to_journal(self) -> dict[str, Any]:
        return {
            "tree_sha": self.tree_sha,
            "head_sha": self.head_sha,
            "base_sha": self.base_sha,
            "env_digest": self.env_digest,
            "day": self.day,
            "clean": self.clean,
        }


def _reuse_env_digest() -> str:
    relevant: list[tuple[str, str | bool]] = sorted(
        (name, value)
        for name, value in os.environ.items()
        if name.startswith(_REUSE_ENV_PREFIXES) and name not in _REUSE_ENV_IGNORED
    )
    relevant.extend((name, name in os.environ) for name in _REUSE_ENV_PRESENCE)
    return hashlib.sha256(json.dumps(relevant).encode("utf-8")).hexdigest()[:16]


def tree_state(repo_root: Path) -> TreeState | None:
    """The state a verdict is tied to, or ``None`` when git cannot say (not a checkout, no base ref)."""

    def git(*args: str) -> str | None:
        try:
            done = subprocess.run(["git", *args], cwd=repo_root, check=False, capture_output=True, text=True)  # noqa: S603, S607
        except OSError:
            return None
        return done.stdout if done.returncode == 0 else None

    tree = git("rev-parse", "--verify", "--quiet", "HEAD^{tree}")
    head = git("rev-parse", "--verify", "--quiet", "HEAD")
    base = git("rev-parse", "--verify", "--quiet", preflight_ci.BASE_REF)
    status = git("status", "--porcelain", "--untracked-files=normal")
    if not tree or not head or not base or status is None:
        return None
    return TreeState(tree.strip(), head.strip(), base.strip(), _reuse_env_digest(), _today(), clean=not status.strip())


def _tree_for_journal(repo_root: Path, at_start: TreeState | None) -> dict[str, Any] | None:
    """The state to journal with a finished run: the one read at its start, when the tree still reads the same.

    A tree that moved while the lanes ran (an edit, a commit, a fetch that moved the base, midnight) has no single
    state the verdict belongs to, and a dirty tree has no hash to compare: both journal ``None``, which nothing reuses.
    """
    if at_start is None or not at_start.clean:
        return None
    return at_start.to_journal() if tree_state(repo_root) == at_start else None


def _finished_seconds_ago(record: Mapping[str, Any], now: datetime) -> float | None:
    """How long ago a journaled run ended, from its ``started_at`` and ``total_seconds``; ``None`` when unreadable."""
    try:
        started = datetime.fromisoformat(str(record.get("started_at")))
        total = float(record.get("total_seconds", 0.0))
    except TypeError, ValueError:
        return None
    if started.tzinfo is None:
        return None
    return (now - started).total_seconds() - total


def reusable_run(
    journal_path: Path,
    state: TreeState | None,
    lanes: Sequence[Lane],
    *,
    stands_for: Mapping[LaneKey, LaneKey] | None = None,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """The newest journaled green run that already judged every lane of this run on this state (Story 117.17).

    A run qualifies when its verdict is ``ok``, it recorded the same clean :class:`TreeState`, it ended no more than
    :data:`REUSE_MAX_AGE_SECONDS` ago, and every lane this run selects ran there with status ``ok``. That makes a
    wider scope cover a narrower one and never the reverse, and a lane that was paused, deferred or cut then is not
    covered now. ``stands_for`` names the lanes another lane judges in full: a touched run's fast-core detectors are
    each run inside ``detectors-ci``, so a green ``detectors-ci`` covers them. A later run of the same state that was
    not green takes the verdict back: the newest word on a state is the one that counts. A ``reuse`` record carries
    no lanes, so a reused verdict is never the proof of another reuse.
    """
    if state is None or not state.clean or not journal_path.is_file():
        return None
    wanted = {_lane_key(lane) for lane in lanes}
    stand_ins = dict(stands_for or {})
    found: dict[str, Any] | None = None
    for line in journal_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict) or "lanes" not in record or record.get("tree") != state.to_journal():
            continue
        if record.get("verdict") != "ok":
            found = None
            continue
        green = {
            (str(lane.get("task")), str(lane.get("environment")))
            for lane in record.get("lanes") or []
            if isinstance(lane, dict) and lane.get("status") == "ok"
        }
        if all(key in green or stand_ins.get(key) in green for key in wanted):
            found = record
    if found is None:
        return None
    age = _finished_seconds_ago(found, now or datetime.now(tz=UTC))
    return found if age is not None and -60.0 <= age <= REUSE_MAX_AGE_SECONDS else None


def _critical_path_flag_on() -> bool:
    return read_boolean(CRITICAL_PATH_FLAG_KEY, default=True)


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


def stranded_dependencies(lanes: Sequence[Lane]) -> tuple[tuple[Lane, tuple[LaneKey, ...]], ...]:
    """Each lane of ``lanes`` that depends on a lane outside them, with those dependencies (Story 107.1).

    Such a lane can never start (it runs only after every dependency is green) and is never blocked (no dependency
    ever gets a result), so ``run_preflight`` refuses the run before any install rather than reach its pool.
    """
    keys = {_lane_key(lane) for lane in lanes}
    stranded: list[tuple[Lane, tuple[LaneKey, ...]]] = []
    for lane in lanes:
        missing = tuple(dep_key for dep_key in lane.depends_on if dep_key not in keys)
        if missing:
            stranded.append((lane, missing))
    return tuple(stranded)


NO_CI_COUNTERPART = "no CI counterpart"  # how preflight_ci's verdict reason opens for a lane no CI step runs
# Story 107.1: why a stranded lane is in the run, which decides what its refusal says.
STRANDED_SELECTED = "selected"  # CI's selection chose it (by its command line, or as a lane no CI step runs)
STRANDED_FAST_CORE = "fast-core"  # a touched run's fast core, in place of detectors-ci
STRANDED_PAUSE_IGNORED = "pause-ignored"  # paused in CI and re-added by --ignore-ci-pauses


def stranded_lane_message(lane: Lane, missing: Sequence[LaneKey], why: str, *, kind: str) -> list[str]:
    """The refusal's lines for one stranded lane (Story 107.1): the lane, why it runs, each missing dependency, what
    CI does with it, and the fixes.

    The preflight runs each lane with ``pixi run --skip-deps``, so a lane runs with a dependency only when that
    dependency is a lane of the run. It never pulls a missing one in: a CI step that runs ``pixi run <task>`` selects
    every lane of the task's ``depends-on`` closure with it (``preflight_ci._step_matches``), so CI's selection leaves
    a dependency out only when nothing in CI runs it with the lane -- a lane the reader matched by its command line,
    a fast-core detector, a lane no CI step runs -- and running it here could turn CI's red into a local green. The
    fourth way in is ``--ignore-ci-pauses``, which re-adds only the paused lanes ``docs/governance/ci-surfaces.yaml``
    names as a local twin, so a dependency the same pause holds back can stay out.
    """
    name = lane_label(lane.task, lane.environment)
    deps = ", ".join(lane_label(*key) for key in missing)
    lines = [f"{name} runs ({why}) but depends on {deps}, which this run does not run"]
    if kind == STRANDED_FAST_CORE:
        lines.append(
            f"  CI runs {lane.task} inside detectors-ci (scripts/detectors.py), never as `pixi run {lane.task}`, "
            f"so never with {deps}"
        )
        lines.append(f"  fix: drop {lane.task}'s depends-on, or take {lane.task} out of FAST_CORE_TASKS")
    elif kind == STRANDED_PAUSE_IGNORED:
        lines.append(
            f"  {deps} {'is' if len(missing) == 1 else 'are'} held back by the same pause, and --ignore-ci-pauses "
            "re-adds only the lanes docs/governance/ci-surfaces.yaml names as a local twin"
        )
        lines.append(
            f"  fix: name {deps} as the local twin of its surface's docs/governance/ci-surfaces.yaml row, "
            "or run without --ignore-ci-pauses"
        )
    elif why.startswith(NO_CI_COUNTERPART):
        lines.append(f"  no CI step runs {lane.task}, so CI never runs it, with {deps} or without")
        lines.append(f"  fix: add a CI step that runs `pixi run {lane.task}`, or drop {lane.task}'s depends-on")
    else:
        lines.append(
            f"  CI runs {lane.task}'s command without {deps}: the step that selects it runs the command, "
            f"not `pixi run {lane.task}`, which is what runs a task's dependencies"
        )
        lines.append(f"  fix: make the CI step run `pixi run {lane.task}`, or drop {lane.task}'s depends-on")
    return lines


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
    names, or Python under ``src/`` for a lint-and-types lane; a kept lane brings the lanes it depends on, and a kept
    docs-site lane brings a selected ``docs-site-install``, which it reads (herald Story 45.1).
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
    install = next((key for key in by_key if key[0] == DOCS_SITE_INSTALL_TASK), None)
    if install is not None and install not in reasons:
        reader = next((key for key in reasons if key[0] in DOCS_SITE_TASKS), None)
        if reader is not None:
            reasons[install] = f"{lane_label(*reader)} reads its install"
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
    # os.sched_getaffinity is Linux's; a host without it (macOS) answers through os.cpu_count.
    affinity = getattr(os, "sched_getaffinity", None)
    if affinity is not None:
        try:
            return len(affinity(0))
        except NotImplementedError:
            pass
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


#: Story 117.19: a variable no lane inherits. An agent session exports it (Claude Code does; the operator's terminal does
#: not), and with it no ``.pyc`` is written, so every xdist worker of every lane rewrites and compiles each module it
#: loads, on every run: marshal's collection takes 12.8 s that way and 3.4 s with the bytecode a run before wrote.
#: Without it a lane writes bytecode beside its sources, into ``__pycache__/`` directories, which ``.gitignore`` ignores
#: at every depth -- as a run from the operator's terminal does.
NO_BYTECODE_ENV = "PYTHONDONTWRITEBYTECODE"


def _lane_scratch_env(scratch_dir: Path) -> dict[str, str]:
    scratch_dir.mkdir(parents=True, exist_ok=True)
    basetemp = scratch_dir / "pytest-basetemp"
    cache_dir = scratch_dir / "pytest-cache"
    coverage = scratch_dir / ".coverage"
    env = os.environ.copy()
    env.pop(NO_BYTECODE_ENV, None)
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
    # Reentrant, as it always was. Since Story 71.13 a nested SIGINT returns at the handler's guard before it reaches
    # set_stop_cause, and the other callers run on pool threads, so no thread re-enters it today.
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
    #: Story 117.15: the CPU seconds each lane's processes used, summed over its segments as each is reaped.
    lane_cpu: dict[LaneKey, float] = field(default_factory=dict)
    #: Story 117.30: each selected alone-tail task's split command, keyed by task as the suite plan is.
    alone_tails: dict[str, AloneTail] = field(default_factory=dict)
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


def _cancelled_unstarted(coord: _RunCoordinator, lane: Lane, default: str) -> LaneResult:
    """A lane the stop kept from running: ``cancelled``, exit 0, 0 s, naming the stop's cause.

    Story 71.12: every such lane names it, whether the pool turned it away or the scheduler never submitted it, so
    the journal does not depend on how the run interleaved. ``default`` is the cause before one is recorded.
    """
    trigger, trigger_env = _stop_cause(coord, default)
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


#: One reap at a time is measured: the children's CPU total moves by exactly the reaped lane's between two readings.
_REAP_LOCK = threading.Lock()


def _wait_measuring_cpu(proc: subprocess.Popen[Any]) -> tuple[int, float | None]:
    """Wait for a lane's process; its exit code, and the CPU seconds it and its descendants used (Story 117.15).

    ``waitid`` with ``WNOWAIT`` returns when the process has exited and leaves it to be reaped; the reap then happens
    under a lock, between two readings of this process's children total, so the difference is this lane's. The exit
    code is ``Popen.wait``'s, as before. ``None`` for the CPU where the platform has no ``waitid`` or ``resource``,
    or when another thread reaped the process first (a stop that terminates the lanes): the code is still returned.
    """
    waitid = getattr(os, "waitid", None)
    if waitid is None or resource is None:
        return int(proc.wait()), None
    try:
        waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOWAIT)
    except OSError:
        return int(proc.wait()), None
    with _REAP_LOCK:
        if proc.returncode is not None:
            return int(proc.returncode), None
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        code = int(proc.wait())
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)
    return code, cpu if cpu > 0 else None


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
        code, cpu = _wait_measuring_cpu(proc)
        if cpu is not None:
            with coord.proc_lock:
                key = _lane_key(ctx.lane)
                coord.lane_cpu[key] = coord.lane_cpu.get(key, 0.0) + cpu
        return code
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
                # --skip-deps, as every lane runs: the lanes it depends on ran as lanes of their own (herald Story 45.1's
                # review: without it the fallback re-ran a task's dependencies, npm ci among them, inside the lane).
                collect_argv = [
                    "pixi",
                    "run",
                    "--frozen",
                    "--skip-deps",
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


def _subprocess_alone_tail_part(coord: _RunCoordinator, ctx: LaneRunContext) -> int:
    """Run an alone-tail lane's head segments in order, or its tail, as ``&&`` would (Story 117.30).

    Each segment is ``pixi run --frozen -e <env> -- <argv>`` with the task's own ``env`` over the lane's; the first
    non-zero exit ends the part. The tail appends to the head's log, so the lane keeps one log.
    """
    plan = coord.alone_tails[ctx.lane.task]
    segments = plan.head if ctx.part == PART_HEAD else (plan.tail,)
    run_ctx = replace(ctx, env={**ctx.env, **plan.env})
    prefix = ["pixi", "run", "--frozen", "-e", ctx.lane.environment, "--"]
    with ctx.log_path.open("ab" if ctx.part == PART_TAIL else "wb") as log_handle:
        for argv in segments:
            code = _run_pixi_argv(coord, run_ctx, [*prefix, *argv], log_handle)
            if code != 0:
                return code
    return 0


def _subprocess_lane(coord: _RunCoordinator, ctx: LaneRunContext) -> int:
    ctx.log_path.parent.mkdir(parents=True, exist_ok=True)
    if ctx.part != PART_WHOLE:
        return _subprocess_alone_tail_part(coord, ctx)
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


def _print_lane_log(log_path: Path, offset: int = 0) -> None:
    """Print the lane's log from byte ``offset``: an alone tail prints only what it appended (Story 117.30)."""
    if not log_path.is_file():
        return
    with log_path.open("rb") as handle:
        handle.seek(offset)
        # Universal newlines, as read_text gave before the offset.
        text = handle.read().decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
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


def _skip_lane_on_red_stop(coord: _RunCoordinator) -> bool:
    """Whether a red stop keeps a lane from starting (Story 88.1 AC4): every lane, once a red lane stopped a run
    without ``--keep-going``.

    After the stop the pool drains what is running and the run ends, so no lane still pending ever starts. A lane
    that pending lanes depend on would only feed dependents that never run (Story 105.1's review: the docs-site
    deferral made this reachable for ``docs-site-install``, which an earlier rule started and then killed at once).
    """
    return coord.stop_on_red.is_set() and not coord.keep_going


def _next_lane(
    ready: Sequence[Lane],
    lanes: Sequence[Lane],
    pending: dict[LaneKey, Lane],
    docs_turn: int | None,
    expected: Mapping[LaneKey, float] | None = None,
) -> Lane:
    """The ready lane that starts next (Story 105.1's review and re-review).

    Every lane outside :data:`DOCS_SITE_TASKS` keeps its declared turn, its index in ``lanes``. The docs-site lanes,
    which run one at a time, trade turns among themselves only: the next docs-site turn (``docs_turn``, the declared
    index of the next docs-site lane in declaration order) goes to ``docs-site-install`` when it is ready, else to the
    ready docs-site lane that pending lanes depend on, else the first one declared. So ``docs-site-install``, then ``pages-build``, take the turns of the docs-site
    lanes declared before them, and herald's built-site tests read this run's install, never a stale one or none at
    all (a fresh worktree). At ``--jobs 1`` every other lane runs at its declared position.

    With ``expected`` (Story 117.3, the flag on), the longest-expected ready lane goes first and the declared turn only
    breaks ties: a lane's expected seconds are its journal median, :data:`UNKNOWN_LANE_SECONDS` when
    it has no history. The docs-site lanes still choose their representative as above; it competes by its own
    expected seconds.
    """

    def rank(lane: Lane, turn: int) -> tuple[float, int]:
        if expected is None:
            return (0.0, turn)
        return (-expected.get(_lane_key(lane), UNKNOWN_LANE_SECONDS), turn)

    turns = [(rank(lane, lanes.index(lane)), lane) for lane in ready if lane.task not in DOCS_SITE_TASKS]
    docs = [lane for lane in ready if lane.task in DOCS_SITE_TASKS]
    if docs:
        # The install every other docs-site lane reads goes first whenever it is ready (herald Story 45.1); then the
        # lane pending docs-site lanes depend on; then declared order. Story 117.2 made the order explicit: the
        # station coverage gates depend on their suites, and herald's suite is itself a docs-site lane, so
        # 'needed by a pending dependent' alone would hand the turn to the suite before the install it reads.
        # Story 117.22: among lanes the 'needed' rule ties, the longest expected goes first, then declared order.
        # herald's coverage gate needs both its halves, and since herald Story 59.1 the live half builds side by side
        # and is the chain's longest lane by far; in declared order it started behind the package half, 78 s in, on
        # the two cores left by then.
        first = min(
            docs,
            key=lambda lane: (
                lane.task != DOCS_SITE_INSTALL_TASK,
                not _needed_by_pending_dependent(lane, pending),
                -(expected or {}).get(_lane_key(lane), 0.0),
                lanes.index(lane),
            ),
        )
        turn = lanes.index(first) if docs_turn is None else docs_turn
        if expected is None:
            turns.append((rank(first, turn), first))
        else:
            # Story 117.15: the docs-site lanes run one at a time, so the lanes behind this one wait for it: it
            # competes by the seconds the whole chain still needs, not by its own. A three-second install in front
            # of herald's built-site tests otherwise waits behind every longer lane, and the chain ends the run.
            # Only seconds the journal or the budgets know count: with no history every lane weighs the same and
            # keeps its declared turn, as before.
            chain = sum(expected.get(key, 0.0) for key, lane in pending.items() if lane.task in DOCS_SITE_TASKS)
            own = expected.get(_lane_key(first), UNKNOWN_LANE_SECONDS)
            turns.append(((-max(chain, own), turn), first))
    return min(turns, key=lambda turn: turn[0])[1]


def _expected_work(key: LaneKey, expected: Mapping[LaneKey, float] | None, work: Mapping[LaneKey, float]) -> float:
    """An xdist lane's expected work in core-seconds (Story 117.15).

    Its journal median of work (:func:`lane_work_medians`) or its tracked work when either is known; else its
    expected seconds (journal median, tracked budget, or :data:`UNKNOWN_LANE_SECONDS`) at the
    :data:`preflight_xdist.MIN_XDIST_WORKERS` workers a lane with no better claim was given.
    """
    known = work.get(key)
    if known is not None and known > 0:
        return known
    seconds = (expected or {}).get(key, UNKNOWN_LANE_SECONDS)
    return max(seconds, 0.0) * preflight_xdist.MIN_XDIST_WORKERS


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


def _joined_alone_tail(head: LaneResult, tail: LaneResult) -> LaneResult:
    """One journal row for an alone-tail lane (Story 117.30): the tail's verdict, the two parts' seconds summed, the
    head's start, both parts' extras (the tail's CPU total wins), and ``alone_tail`` naming the tail's own run."""
    extra = {**(head.journal_extra or {}), **(tail.journal_extra or {})}
    extra["alone_tail"] = {
        "seconds": tail.seconds,
        "start_offset": tail.start_offset,
        "exit_code": tail.exit_code,
        "status": tail.status,
    }
    return replace(tail, seconds=head.seconds + tail.seconds, start_offset=head.start_offset, journal_extra=extra)


def _run_lane_in_pool(
    coord: _RunCoordinator,
    lane: Lane,
    scratch_root: Path,
    mutex_keys: tuple[str, ...],
    runner: Callable[[LaneRunContext], int],
    use_subprocess: bool,
    part: str = PART_WHOLE,
) -> LaneResult:
    key = _lane_key(lane)
    if coord.cancel.is_set():
        return _cancelled_unstarted(coord, lane, "interrupt")
    if _skip_lane_on_red_stop(coord):
        return _cancelled_unstarted(coord, lane, "red")

    # Story 105.1: every mutex the lane holds (its CI service, the docs-site tree), taken in one sorted order, so two
    # lanes that each wait for the other's key cannot exist; released in reverse, whatever the lane did.
    held: list[threading.Lock] = []
    try:
        for name in sorted(set(mutex_keys)):
            lock = coord.mutex_lock(name)
            lock.acquire()
            held.append(lock)
        if coord.cancel.is_set():
            return _cancelled_unstarted(coord, lane, "interrupt")
        if _skip_lane_on_red_stop(coord):
            return _cancelled_unstarted(coord, lane, "red")

        lane_dir = scratch_root / lane_label(lane.task, lane.environment)
        log_path = _lane_log_path(scratch_root, lane.task, lane.environment)
        env = _lane_scratch_env(lane_dir)
        workers = coord.xdist_workers.get(key)
        if workers is not None:
            env["PYTEST_XDIST_AUTO_NUM_WORKERS"] = str(workers)
        ctx = LaneRunContext(lane=lane, scratch_dir=lane_dir, log_path=log_path, env=env, part=part)
        # Story 117.30: an alone tail appends to its head's log and prints only what it added.
        log_offset = log_path.stat().st_size if part == PART_TAIL and log_path.is_file() else 0
        start_offset = time.monotonic() - coord.run_start
        lane_start = time.monotonic()

        if use_subprocess:
            code = _subprocess_lane(coord, ctx)
        else:
            code = runner(ctx)

        elapsed = time.monotonic() - lane_start
        _print_lane_log(log_path, log_offset)

        journal_extra = _lane_journal_extra(coord, lane)
        if workers is not None:
            # Story 117.15: the workers the lane ran on, so the next run can size its share by work done.
            journal_extra = {**(journal_extra or {}), "xdist_workers": workers}
        with coord.proc_lock:
            cpu = coord.lane_cpu.get(key)
        if cpu is not None:
            # The CPU seconds the lane's processes used: its work, whatever workers it was given.
            journal_extra = {**(journal_extra or {}), "cpu_seconds": round(cpu, 1)}
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
    critical_path: bool | None = None,
    logical_cores: int | None = None,
    expected_seconds: Mapping[LaneKey, float] | None = None,
    reuse: bool = False,
    alone_tail_tasks: frozenset[str] = ALONE_TAIL_TASKS,
) -> int:
    """Run CI-selected lanes; return exit code 0 / 1 / 2 / 130.

    ``alone_tail_tasks`` (Story 117.30, injectable for tests): a selected lane of one of these tasks runs its last
    ``&&`` segment once no other lane is in flight or ready, and none starts while it runs; a selected lane whose
    task has no such segment (:func:`alone_tail_plan`) returns ``EXIT_CONFIG`` before any install.

    ``reuse`` (Story 117.17): when true, a run whose every selected lane already passed on this same clean tree,
    base and environment (:func:`reusable_run`) starts no lane: it names the run it reuses, journals a ``reuse``
    record and returns 0. ``main`` passes :func:`reuse_enabled`; a caller that injects its own lane runner leaves it
    off, since an injected runner's verdict proves nothing about the tree.

    ``critical_path`` (Story 117.3): ``None`` reads the flag :data:`CRITICAL_PATH_FLAG_KEY`; ``True`` admits ready
    lanes longest-expected first and by the cores they will use, ``False`` keeps declaration order and the static
    xdist share. ``logical_cores`` and ``expected_seconds`` (journal medians per lane) are injectable for tests.

    ``scope`` is ``full`` (every selected lane) or ``touched`` (Story 103.6: see :func:`touched_cut`);
    ``scope_source`` says what chose it, for the run's stdout. A run in which a lane depends on a lane outside it
    returns ``EXIT_CONFIG`` before any install (Story 107.1: :func:`stranded_dependencies`).
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
        # Story 99.8: advisory only -- the lanes, the verdict and the exit code below never read it.
        preflight_ci.print_main_red_banner(repo_root)
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
    # Story 107.1: a lane whose dependency is not in the run would never start and never be blocked, and the pool would
    # loop with nothing in flight. Nothing in CI runs such a lane with that dependency, so the run is refused, never
    # widened: before any install or lane starts, naming each lane, why it runs, what it misses and the fixes.
    stranded = stranded_dependencies(lanes)
    if stranded:
        selected = {
            (verdict.task, verdict.environment): verdict.reason for verdict in selection.verdicts if verdict.selected
        }
        cut_reasons = dict(cut.reasons) if cut is not None else {}
        fast_core_keys = {_lane_key(lane) for lane in cut.fast_core} if cut is not None else set()
        # The paused lanes --ignore-ci-pauses re-added: unselected with the pause applied, so they have no reason above.
        re_added = {(entry.task, entry.environment): entry for entry in paused_lanes} if ignore_ci_pauses else {}
        for lane, missing in stranded:
            key = _lane_key(lane)
            if key in fast_core_keys:
                kind, why = STRANDED_FAST_CORE, cut_reasons[key]
            elif key in selected:
                kind, why = STRANDED_SELECTED, selected[key]
            else:
                entry = re_added[key]
                kind = STRANDED_PAUSE_IGNORED
                why = (
                    f"paused in CI ({entry.switch} since {entry.since}, review_by {entry.review_by}), "
                    "re-added by --ignore-ci-pauses"
                )
            for line in stranded_lane_message(lane, missing, why, kind=kind):
                print(f"preflight: {line}", file=sys.stderr)
        print("preflight: refusing the run before any install or lane starts", file=sys.stderr)
        return EXIT_CONFIG

    # Story 117.30: each selected alone-tail task's split command. A declared task with no tail is refused, never run
    # whole: run whole, its timing segment would share the cores again and the run would not say so.
    alone_tails: dict[str, AloneTail] = {}
    for lane in lanes:
        if lane.task not in alone_tail_tasks or lane.task in alone_tails:
            continue
        plan = alone_tail_plan(pixi_data, lane.task)
        if plan is None:
            print(
                f"preflight: {lane.task!r} is declared to run its last segment alone (ALONE_TAIL_TASKS), but its cmd "
                "has no '&&' segment that runs as one argv; refusing the run before any install or lane starts",
                file=sys.stderr,
            )
            return EXIT_CONFIG
        alone_tails[lane.task] = plan

    # Story 117.17: the state this run's verdict will be tied to, read before any lane can touch the tree.
    state_at_start = tree_state(repo_root)
    if reuse and lanes:
        # A touched run's fast-core detectors each run inside detectors-ci, so a green full run covers them.
        stands_for = {
            _lane_key(lane): (FAST_CORE_REPLACES, lane.environment) for lane in (cut.fast_core if cut else ())
        }
        earlier = reusable_run(repo_root / JOURNAL_RELATIVE, state_at_start, lanes, stands_for=stands_for)
        if earlier is not None and state_at_start is not None:
            head_sha, branch = _git_head(repo_root)
            print(
                f"preflight: this commit ({state_at_start.head_sha[:12]}, base {state_at_start.base_sha[:12]}) is "
                f"already green: run {earlier.get('run_id')} of {earlier.get('started_at')} "
                f"(scope {earlier.get('mode')}) passed all {len(lanes)} lane(s) this run selects. "
                f"Nothing to run; {REUSE_ENV}=0 runs them again.",
                file=sys.stderr,
            )
            _append_journal(
                repo_root,
                {
                    "phase": "reuse",
                    "run_id": str(uuid.uuid4()),
                    "reused_run_id": earlier.get("run_id"),
                    "started_at": datetime.now(tz=UTC).isoformat(),
                    "head_sha": head_sha,
                    "branch": branch,
                    "mode": scope,
                    "tree": state_at_start.to_journal(),
                    "lanes_covered": sorted(lane_label(lane.task, lane.environment) for lane in lanes),
                    # What this run leaves to CI, as a run that ran its lanes journals it (verify-deferred reads it).
                    "deferred": _deferred_journal(deferred),
                    "verdict": "ok",
                },
            )
            return EXIT_OK

    cores = logical_cores if logical_cores is not None else _logical_core_count()
    worker_count = jobs if jobs is not None else cores
    critical = critical_path if critical_path is not None else _critical_path_flag_on()
    expected: Mapping[LaneKey, float] | None = None
    work: Mapping[LaneKey, float] = {}
    if critical:
        if expected_seconds is not None:
            expected = expected_seconds
        else:
            # Story 117.15: the journal's own medians, and for a lane it has no green run of, the tracked budget.
            expected = {**budget_seed_seconds(repo_root), **lane_medians(repo_root / JOURNAL_RELATIVE)}
            work = {**budget_seed_work(repo_root), **lane_work_medians(repo_root / JOURNAL_RELATIVE)}
    if worker_count < 1:
        worker_count = 1
    # The lanes whose task runs pytest under ``-n auto``, read once: the admission loop asks for every pending lane
    # on every pick, and parsing each task's command there cost a full run half a minute of this thread's time.
    xdist_lanes = frozenset(
        _lane_key(lane) for lane in lanes if preflight_xdist.task_cmd_uses_xdist_auto(pixi_data, lane.task)
    )
    # Story 117.15: the seconds a lane should take, from the expected work of every selected lane (an xdist lane's
    # work, a serial lane's work or seconds) over the machine's cores.
    target_seconds: float | None = None
    if critical and cores > 0:
        run_work = sum(
            _expected_work(_lane_key(lane), expected, work)
            if _lane_key(lane) in xdist_lanes
            else work.get(_lane_key(lane), (expected or {}).get(_lane_key(lane), UNKNOWN_LANE_SECONDS))
            for lane in lanes
        )
        target_seconds = LANE_TARGET_FRACTION * run_work / cores

    # Story 117.15: the docs-site lanes run one at a time, so they share one slot, and the slot is as wide as its
    # widest lane: a serial docs-site lane holds the cores the xdist one behind it will need. With one core held, the
    # install ended and herald's suite then waited 78 s for a second core, on the chain that ended the run.
    docs_slot_cores = (
        preflight_xdist.MIN_XDIST_WORKERS
        if any(lane.task in DOCS_SITE_TASKS and _lane_key(lane) in xdist_lanes for lane in lanes)
        else 1
    )
    # Story 117.22: and as wide as the share its widest xdist lane is planned to take (its expected work over the
    # target seconds), up to half the machine. Two cores held for the slot left herald's live half on two workers for
    # 350 s, though its builds run side by side since herald Story 59.1; held from the start, the cores it will need are
    # free when the install before it ends.
    if target_seconds:
        planned = [
            math.ceil(_expected_work(_lane_key(lane), expected, work) / target_seconds)
            for lane in lanes
            if lane.task in DOCS_SITE_TASKS and _lane_key(lane) in xdist_lanes
        ]
        if planned:
            docs_slot_cores = max(docs_slot_cores, min(max(planned), max(1, cores // 2)))

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
        logical_cores=cores,  # Story 117.3: the one core count, injectable for tests; the machine's otherwise
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
        alone_tails=alone_tails,
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
    # Story 71.13: Python runs the handler on the main thread between bytecodes, so a second SIGINT can land while the
    # first call holds ``cancel``'s own Lock or ``proc_lock``; re-entering would wait forever on its own frame. A call
    # that finds the handler running returns at once; once the handler has returned, a SIGINT runs it again.
    sigint_running = False

    def _on_sigint(_signum: int, _frame: object | None) -> None:
        nonlocal sigint_running
        if sigint_running:
            return
        sigint_running = True
        try:
            # The cause before the flag, as a red lane records it (Story 71.12): a pool thread that sees ``cancel``
            # set always finds the cause that set it.
            coord.set_stop_cause(("interrupt", None))
            coord.cancel.set()
            coord.terminate_children()
        finally:
            sigint_running = False

    signal.signal(signal.SIGINT, _on_sigint)

    results_by_key: dict[LaneKey, LaneResult] = {}
    pending: dict[LaneKey, Lane] = {_lane_key(lane): lane for lane in lanes}
    completed: dict[LaneKey, LaneResult] = {}
    weights: dict[LaneKey, int] = {}  # Story 117.3: cores each in-flight lane holds (1, or its xdist share)
    # Story 105.1: the declared turns of the docs-site lanes, which they trade among themselves (_next_lane).
    docs_turns = [index for index, lane in enumerate(lanes) if lane.task in DOCS_SITE_TASKS]
    docs_started = 0
    try:
        with ThreadPoolExecutor(max_workers=worker_count) as pool:
            futures: dict[Future[LaneResult], Lane] = {}
            # Story 117.30: which part of its lane each future runs, the alone-tail lanes whose head passed and whose
            # tail waits for the machine to itself (in the order their heads finished), and the head result of a tail
            # in flight. A lane is completed only when its tail is, so its dependents wait for the tail.
            parts: dict[Future[LaneResult], str] = {}
            waiting_tails: dict[LaneKey, tuple[Lane, LaneResult]] = {}
            tail_heads: dict[LaneKey, LaneResult] = {}

            def _record_done(lane: Lane, result: LaneResult) -> None:
                completed[_lane_key(lane)] = result
                results_by_key[_lane_key(lane)] = result

            def _settle(fut: Future[LaneResult], lane: Lane) -> None:
                part = parts.pop(fut, PART_WHOLE)
                try:
                    result = fut.result()
                except Exception:  # noqa: BLE001
                    result = LaneResult(lane.task, lane.environment, 0.0, 1, "red", 0.0)
                if part == PART_HEAD and result.status == "ok":
                    waiting_tails[_lane_key(lane)] = (lane, result)
                    return
                if part == PART_TAIL:
                    result = _joined_alone_tail(tail_heads.pop(_lane_key(lane)), result)
                _record_done(lane, result)

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

            while pending or futures or waiting_tails:
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
                        if _skip_lane_on_red_stop(coord):
                            continue
                        if busy.intersection(mutex_keys[key]):
                            continue
                        ready_candidates.append(candidate)
                    if not ready_candidates:
                        break
                    docs_turn = docs_turns[docs_started] if docs_started < len(docs_turns) else None
                    # Story 117.3: the longest-expected ready lane first, admitted only while its weight -- one core
                    # for a serial lane, its xdist share for a parallel one -- fits the cores the in-flight lanes leave.
                    # A parallel lane that cannot get MIN_XDIST_WORKERS yet is set aside this round, not starved: it is
                    # offered again when a lane finishes. --jobs stays the upper bound on lanes in flight.
                    free_cores = cores - sum(weights.get(_lane_key(running), 1) for running in futures.values())
                    ready: Lane | None = None
                    while ready_candidates:
                        pick = _next_lane(ready_candidates, lanes, pending, docs_turn, expected)
                        if not critical:
                            ready = pick
                            break
                        pick_key = _lane_key(pick)
                        if pick_key in xdist_lanes:
                            pending_xdist_keys = [lane_key for lane_key in pending if lane_key in xdist_lanes]
                            # Story 117.15: the share follows the lane's expected work among the xdist lanes still
                            # to start (pick is still pending, so it is in the sum).
                            share = preflight_xdist.xdist_share_at_admission(
                                free_cores=free_cores,
                                pending_xdist=len(pending_xdist_keys),
                                logical_cores=cores,
                                weight=_expected_work(pick_key, expected, work),
                                pending_weight=sum(_expected_work(k, expected, work) for k in pending_xdist_keys),
                                target_seconds=target_seconds,
                            )
                            if share == 0 and not futures:
                                # Nothing is in flight to free a core (a one-core machine): the lane starts on the
                                # minimum, or it would wait for ever.
                                share = preflight_xdist.MIN_XDIST_WORKERS
                            if share == 0:
                                if futures and pick.task in DOCS_SITE_TASKS:
                                    # Story 117.15: the docs-site lanes behind this one wait for it, so its turn is
                                    # held: no shorter lane takes the core it is short of. A lane in flight frees it.
                                    break
                                ready_candidates.remove(pick)
                                continue
                            weights[pick_key] = share
                            coord.xdist_workers[pick_key] = share
                        else:
                            need = docs_slot_cores if pick.task in DOCS_SITE_TASKS else 1
                            if free_cores < need and futures:
                                if pick.task in DOCS_SITE_TASKS:
                                    break
                                ready_candidates.remove(pick)
                                continue
                            weights[pick_key] = need
                        ready = pick
                        break
                    if ready is None:
                        break
                    key = _lane_key(ready)
                    del pending[key]
                    if ready.task in DOCS_SITE_TASKS:
                        docs_started += 1
                    part = PART_HEAD if ready.task in alone_tails else PART_WHOLE
                    fut = pool.submit(
                        _run_lane_in_pool,
                        coord,
                        ready,
                        scratch_root,
                        mutex_keys[key],
                        runner,
                        use_subprocess,
                        part,
                    )
                    futures[fut] = ready
                    parts[fut] = part

                stopped = coord.stop_on_red.is_set() and not coord.keep_going

                # Story 117.30: with nothing in flight after admission, no pending lane can start (one would have, on
                # an idle machine), so the next waiting tail runs now, alone. No lane starts while it runs: only the
                # tail can finish, and until it does no lane's dependencies or mutexes change. A stop leaves it
                # unrun: the lane is journaled cancelled below, as an unstarted lane is.
                if not futures and waiting_tails and not stopped and not coord.cancel.is_set():
                    tail_key = next(iter(waiting_tails))
                    tail_lane, head_result = waiting_tails.pop(tail_key)
                    tail_heads[tail_key] = head_result
                    fut = pool.submit(
                        _run_lane_in_pool,
                        coord,
                        tail_lane,
                        scratch_root,
                        mutex_keys[tail_key],
                        runner,
                        use_subprocess,
                        PART_TAIL,
                    )
                    futures[fut] = tail_lane
                    parts[fut] = PART_TAIL

                if not futures:
                    if not pending or stopped:
                        break
                    continue

                done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
                for fut in done:
                    _settle(fut, futures.pop(fut))

                if stopped:
                    while futures:
                        done_wait, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
                        for fut in done_wait:
                            _settle(fut, futures.pop(fut))
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
                ordered.append(_cancelled_unstarted(coord, lane, "interrupt"))
        _append_journal(
            repo_root,
            {
                "run_id": run_id,
                "started_at": started.isoformat(),
                "head_sha": head_sha,
                "tree": _tree_for_journal(repo_root, state_at_start),
                "branch": branch,
                "logical_cores": cores,
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
            result = _cancelled_unstarted(coord, lane, "red")
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
            "tree": _tree_for_journal(repo_root, state_at_start),
            "branch": branch,
            "logical_cores": cores,
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
        reuse=reuse_enabled(),
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
