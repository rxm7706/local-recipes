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
"""

from __future__ import annotations

from typing import Any

from celery import shared_task

from django_pyforge.models import RunState
from django_pyforge.supervisor import complete_run
from django_pyforge.supervisor import lookup_runner
from django_pyforge.supervisor import prune_run_state

SUBJECT_HEADER = "sub"


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
    """Publish one supervised run, tagged with the subject that asked for it."""
    return execute_supervised_run.apply_async(
        args=[run_id, station, tool, payload],
        task_id=task_id,
        headers={SUBJECT_HEADER: subject},
    )


@shared_task
def prune_run_state_task() -> dict[str, int]:
    """Retention sweep over ``run_state`` (Story 42.2 / red-team B-7)."""
    return prune_run_state()
