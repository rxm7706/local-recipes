"""Celery queue topology (Story 42.4, red-team S-2 / T-6, directive R-10).

Before this module every station's work shared Celery's one default queue on
one pool with one 300 s limit, so a Mason build flood starved Doctor remedies
and supervisor housekeeping, and nothing longer than five minutes could run at
all. The topology is declared HERE, in the chrome, so the settings module, the
Helm chart and the tests all read one table rather than three:

* ``default`` -- work that names no station (front-door refreshes, DB-GPT
  reads, Langflow proofs).
* one queue per station token -- ``execute_supervised_run`` lands on the
  queue of the station it runs for, so a flood on one station is visible as
  one queue's depth and can be given its own pool with ``-Q``.
* ``priority`` -- Doctor remedies and the supervisor's own housekeeping
  (retention, the worker-lost sweep). Listed FIRST in the general pool's
  ``-Q`` so, under ``queue_order_strategy=priority``, a backlog elsewhere
  never delays them.
* ``builds`` -- Mason builds: hours-scale work on its own Deployment with its
  own hard limit. The general pool never consumes it (the chart refuses a
  ``worker.queues`` that lists it), so a build cannot be cut off at 300 s
  and cannot occupy the pool that answers everything else.

The router below is what ``CELERY_TASK_ROUTES`` points at. A task named in
``TASK_ROUTES`` goes where the table says; the supervised-run task is routed
by the ``(station, tool)`` it carries; everything else falls through to
Celery's default queue. Adding a long-running tool means adding its
``(station, tool)`` row here -- a story-local ``queue=`` at a call site would
be a second routing table.
"""

from __future__ import annotations

import logging
from typing import Any

from django_pyforge.events.constants import STATION_TOKENS

logger = logging.getLogger(__name__)

DEFAULT_QUEUE = "default"
PRIORITY_QUEUE = "priority"
BUILDS_QUEUE = "builds"
#: One queue per station token, in a stable order (the chart's ``-Q`` and
#: the tests both derive from this tuple).
STATION_QUEUES: tuple[str, ...] = tuple(sorted(STATION_TOKENS))
#: The general pool's queues, in consumption-priority order.
WORKER_QUEUES: tuple[str, ...] = (PRIORITY_QUEUE, DEFAULT_QUEUE, *STATION_QUEUES)
#: The builds pool consumes exactly this.
BUILDS_WORKER_QUEUES: tuple[str, ...] = (BUILDS_QUEUE,)
#: Every queue the broker carries; ``CELERY_TASK_QUEUES`` declares these so a
#: worker started with no ``-Q`` (compose, a laptop) consumes all of them.
ALL_QUEUES: tuple[str, ...] = (*WORKER_QUEUES, BUILDS_QUEUE)

SUPERVISED_RUN_TASK = "django_pyforge.tasks.execute_supervised_run"
PRUNE_RUN_STATE_TASK = "django_pyforge.tasks.prune_run_state_task"
SWEEP_LOST_RUNS_TASK = "django_pyforge.tasks.sweep_lost_runs_task"

MASON_STATION = "mason"
DOCTOR_STATION = "doctor"
#: Mason tools that run rattler-build (or equivalent) and need the builds pool.
MASON_BUILD_TOOL = "build"
MASON_REBUILD_TOOL = "rebuild"
#: The Doctor tool that applies a remedy -- the work a build flood must not delay.
DOCTOR_REMEDY_TOOL = "remedy"

#: ``(station, tool)`` -> queue, for supervised runs that must NOT land on
#: their station's queue. Everything not listed lands on ``<station>``.
TOOL_ROUTES: dict[tuple[str, str], str] = {
    (MASON_STATION, MASON_BUILD_TOOL): BUILDS_QUEUE,
    (MASON_STATION, MASON_REBUILD_TOOL): BUILDS_QUEUE,
    (DOCTOR_STATION, DOCTOR_REMEDY_TOOL): PRIORITY_QUEUE,
}

#: Task name -> queue, for tasks that are not supervised runs.
TASK_ROUTES: dict[str, str] = {
    PRUNE_RUN_STATE_TASK: PRIORITY_QUEUE,
    SWEEP_LOST_RUNS_TASK: PRIORITY_QUEUE,
    # Warden's compliance job is station work: it queues behind other warden
    # work, never behind a build.
    "warden_fabric.run_job": "warden",
}

# Settings the per-queue hard limits are read from, with the documented
# defaults a deployment that names neither gets (config/settings/base.py
# declares both; these are the fallbacks for a bare Django project).
SETTING_TASK_TIME_LIMIT = "CELERY_TASK_TIME_LIMIT"
SETTING_BUILDS_TASK_TIME_LIMIT = "CELERY_BUILDS_TASK_TIME_LIMIT"
DEFAULT_TASK_TIME_LIMIT_SECONDS = 5 * 60
DEFAULT_BUILDS_TASK_TIME_LIMIT_SECONDS = 4 * 60 * 60


def queue_for(station: str, tool: str) -> str:
    """The queue a supervised run of ``tool`` on ``station`` lands on."""
    override = TOOL_ROUTES.get((station, tool))
    if override is not None:
        return override
    if station in STATION_TOKENS:
        return station
    return DEFAULT_QUEUE


def _supervised_run_target(args: Any, kwargs: Any) -> tuple[str, str] | None:
    """``(station, tool)`` from a supervised-run publish, however it was called."""
    station: Any = None
    tool: Any = None
    if isinstance(kwargs, dict):
        station = kwargs.get("station")
        tool = kwargs.get("tool")
    positional = list(args or ())
    if station is None and len(positional) > 1:
        station = positional[1]
    if tool is None and len(positional) > 2:  # noqa: PLR2004 -- (run_id, station, tool, ...)
        tool = positional[2]
    if not isinstance(station, str) or not isinstance(tool, str):
        return None
    return station, tool


def route_task(
    name: str,
    args: Any = None,
    kwargs: Any = None,
    options: Any = None,
    task: Any = None,
    **_extra: Any,
) -> dict[str, str] | None:
    """Celery router (``task_routes``): the one routing decision.

    Returns ``None`` -- "no opinion" -- for tasks the table does not name, so
    they fall through to ``task_default_queue``.
    """
    del options, task
    if name == SUPERVISED_RUN_TASK:
        target = _supervised_run_target(args, kwargs)
        if target is None:
            logger.warning(
                "queues.unroutable_supervised_run",
                extra={"event": "queues.unroutable_supervised_run"},
            )
            return {"queue": DEFAULT_QUEUE}
        return {"queue": queue_for(*target)}
    queue = TASK_ROUTES.get(name)
    if queue is None:
        return None
    return {"queue": queue}


def _int_setting(name: str, default: int) -> int:
    """A positive-integer Django setting, or ``default``. Lazy on purpose:
    ``config.settings.base`` imports this module while settings are still
    being assembled, so nothing here may touch ``django.conf`` at import."""
    try:
        from django.conf import settings  # noqa: PLC0415
    except ImportError:  # pragma: no cover -- Django is a declared dependency
        return default
    raw = getattr(settings, name, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def time_limit_for_queue(queue: str) -> int:
    """The hard limit, in seconds, of the pool that consumes ``queue``."""
    if queue == BUILDS_QUEUE:
        return _int_setting(
            SETTING_BUILDS_TASK_TIME_LIMIT,
            DEFAULT_BUILDS_TASK_TIME_LIMIT_SECONDS,
        )
    return _int_setting(SETTING_TASK_TIME_LIMIT, DEFAULT_TASK_TIME_LIMIT_SECONDS)


def station_time_limit(station: str) -> int:
    """The longest a supervised run for ``station`` may legitimately hold a
    worker: the largest limit among the queues its tools can land on.

    ``RunState`` records the station, not the tool, so the sweep has to be
    conservative per station -- a Mason row is given the builds limit even
    if it was a diagnose, because the alternative is failing a live build.
    """
    queues = {queue_for(station, "")}
    for (route_station, _tool), queue in TOOL_ROUTES.items():
        if route_station == station:
            queues.add(queue)
    return max(time_limit_for_queue(queue) for queue in queues)
