"""Celery worker that completes a supervisor-published run."""

from __future__ import annotations

from typing import Any

from celery import shared_task

from django_pyforge.models import RunState
from django_pyforge.supervisor import complete_run
from django_pyforge.supervisor import lookup_runner


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
