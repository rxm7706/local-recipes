"""Celery workers behind the supervisor.

Story 42.2 (red-team A-6 / R-8) adds two things to what used to be one task:

* ``enqueue_supervised_run`` publishes with an explicit ``task_id`` and a
  ``sub`` message header. The id is chosen by the caller so the ``RunState``
  row can name the task *before* it exists on the broker — which is what makes
  a merely-queued task revocable. The header carries the subject on the message
  itself, so a worker or an operator inspecting the broker can attribute a task
  without joining back to PostgreSQL.
* ``prune_run_state_task`` is the retention sweep, scheduled by
  ``CELERY_BEAT_SCHEDULE``. It holds no logic: ``run_state`` has exactly one
  writer (AD-12), and that is the supervisor.

Story 42.3 (red-team A-5 / R-9) adds the trace: ``enqueue_supervised_run``
also carries the current ``traceparent`` as a message header, and a task that
was published with one re-binds it into its structlog context on start, so a
request -> event -> consumer -> task chain logs one trace id end to end.

Story 42.4 (red-team S-2 / T-6 / R-10) makes delivery at-least-once and the
ledger honest about it. ``execute_supervised_run`` is bound so it can see
whether the broker re-delivered its message (``acks_late`` +
``reject_on_worker_lost`` put a lost worker's message back), and asks the
supervisor's ``begin_attempt`` before doing anything: a terminal row is not
re-run, a first re-delivery runs exactly once more, a second is terminalised.
``sweep_lost_runs_task`` is the other half -- the beat-scheduled sweep that
fails rows whose task no worker holds any more. Where a task lands is not
decided here: ``django_pyforge.queues.route_task`` is the routing table.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

from django_pyforge.events.tracing import bind_structlog_trace
from django_pyforge.events.tracing import trace_headers
from django_pyforge.events.tracing import traceparent_from_task_request
from django_pyforge.models import RunState
from django_pyforge.supervisor import begin_attempt
from django_pyforge.supervisor import complete_run
from django_pyforge.supervisor import lookup_runner
from django_pyforge.supervisor import prune_run_state
from django_pyforge.supervisor import sweep_lost_runs

logger = logging.getLogger(__name__)

SUBJECT_HEADER = "sub"

# How long a truncated sweep waits before its own follow-up. Small on purpose:
# the point is to yield the worker between batches, not to pace the drain.
PRUNE_CHAIN_COUNTDOWN_SECONDS = 1

try:
    from django_structlog.celery.signals import bind_extra_task_metadata
except ImportError:  # pragma: no cover -- structlog integration is optional
    bind_extra_task_metadata = None

if bind_extra_task_metadata is not None:

    def _bind_task_traceparent(
        sender: Any = None,
        task: Any = None,
        **_kwargs: Any,
    ) -> None:
        """django-structlog has just cleared + rebuilt the task's contextvars;
        put the trace the message was published with back on them."""
        traceparent = traceparent_from_task_request(getattr(task, "request", None))
        if traceparent:
            bind_structlog_trace(traceparent)

    bind_extra_task_metadata.connect(
        _bind_task_traceparent,
        weak=False,
        dispatch_uid="django_pyforge.trace",
    )


def redelivered(request: Any) -> bool:
    """Whether the broker re-delivered this message (kombu sets
    ``delivery_info.redelivered`` when it restores an unacked message)."""
    info = getattr(request, "delivery_info", None)
    if not isinstance(info, dict):
        return False
    return bool(info.get("redelivered"))


@shared_task(bind=True)
def execute_supervised_run(
    self: Any,
    run_id: str,
    station: str,
    tool: str,
    payload: dict[str, Any],
) -> None:
    if RunState.objects.filter(
        pk=run_id,
        status__in=RunState.TERMINAL_STATUSES,
    ).exists():
        # The ledger, not the broker, is the record of a revoke. `control.revoke`
        # is a broadcast held in worker memory: a worker that connected after it
        # was sent (a restart, a rollout, a scale-up) has never heard of the id
        # and would run the task in full, with only its final write dropped. A
        # terminal row means there is nothing left for this task to do.
        logger.info(
            "supervisor.run_skipped_terminal",
            extra={
                "event": "supervisor.run_skipped_terminal",
                "run_id": run_id,
                "station": station,
            },
        )
        return
    if not begin_attempt(run_id, redelivered=redelivered(self.request)):
        return
    try:
        result = lookup_runner(station, tool)(payload)
    except Exception as exc:
        complete_run(
            run_id,
            status=RunState.Status.FAILED,
            result={"error": str(exc)},
        )
        raise
    complete_run(run_id, status=RunState.Status.SUCCEEDED, result=result)


def enqueue_supervised_run(
    run_id: str,
    station: str,
    tool: str,
    payload: dict[str, Any],
    *,
    subject: str,
    task_id: str,
) -> Any:
    """Publish one supervised run, tagged with the subject that asked for it
    and the trace it runs under. The queue is the router's decision
    (``CELERY_TASK_ROUTES`` -> ``queues.route_task``), never a call-site
    literal."""
    headers: dict[str, Any] = {SUBJECT_HEADER: subject, **trace_headers()}
    return execute_supervised_run.apply_async(
        args=[run_id, station, tool, payload],
        task_id=task_id,
        headers=headers,
    )


@shared_task
def prune_run_state_task() -> dict[str, Any]:
    """Retention sweep over ``run_state`` (Story 42.2 / red-team B-7).

    A sweep is batch-bounded, so one beat tick removes at most
    ``RUN_STATE_PRUNE_BATCH`` rows; left there, the drain is one batch per
    interval, which a handful of subjects at the default start rate publish
    faster than. A truncated sweep that made progress therefore enqueues its
    own follow-up, and stops the moment a sweep removes nothing -- so the chain
    terminates whatever ``truncated`` says.
    """
    report = prune_run_state()
    removed = report["aged_out"] + report["over_cap"] + report["expired_handles"]
    rescheduled = bool(report["truncated"] and removed > 0)
    if rescheduled:
        prune_run_state_task.apply_async(countdown=PRUNE_CHAIN_COUNTDOWN_SECONDS)
    return {**report, "rescheduled": rescheduled}


@shared_task
def sweep_lost_runs_task() -> dict[str, Any]:
    """Fail live runs whose worker is gone (Story 42.4 / BS-8 partial)."""
    return sweep_lost_runs()
