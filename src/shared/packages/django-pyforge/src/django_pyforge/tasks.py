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
"""

from __future__ import annotations

from typing import Any

from celery import shared_task

from django_pyforge.events.tracing import bind_structlog_trace
from django_pyforge.events.tracing import trace_headers
from django_pyforge.events.tracing import traceparent_from_task_request
from django_pyforge.models import RunState
from django_pyforge.supervisor import complete_run
from django_pyforge.supervisor import lookup_runner
from django_pyforge.supervisor import prune_run_state

SUBJECT_HEADER = "sub"

try:
    from django_structlog.celery.signals import bind_extra_task_metadata
except ImportError:  # pragma: no cover -- structlog integration is optional
    bind_extra_task_metadata = None

if bind_extra_task_metadata is not None:

    def _bind_task_traceparent(sender: Any = None, task: Any = None, **_kwargs: Any) -> None:
        """django-structlog has just cleared + rebuilt the task's contextvars;
        put the trace the message was published with back on them."""
        traceparent = traceparent_from_task_request(getattr(task, "request", None))
        if traceparent:
            bind_structlog_trace(traceparent)

    bind_extra_task_metadata.connect(_bind_task_traceparent, weak=False, dispatch_uid="django_pyforge.trace")


@shared_task
def execute_supervised_run(
    run_id: str,
    station: str,
    tool: str,
    payload: dict[str, Any],
) -> None:
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
    and the trace it runs under."""
    headers: dict[str, Any] = {SUBJECT_HEADER: subject, **trace_headers()}
    return execute_supervised_run.apply_async(
        args=[run_id, station, tool, payload],
        task_id=task_id,
        headers=headers,
    )


@shared_task
def prune_run_state_task() -> dict[str, int]:
    """Retention sweep over ``run_state`` (Story 42.2 / red-team B-7)."""
    return prune_run_state()
