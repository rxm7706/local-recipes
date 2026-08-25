"""In-tree Celery BaseTaskBackend for Wagtail django-tasks (NFR-C7)."""

from __future__ import annotations

from typing import TypeVar

from django.utils import timezone
from django_tasks.backends.base import BaseTaskBackend
from django_tasks.base import Task
from django_tasks.base import TaskResult
from django_tasks.base import TaskResultStatus
from django_tasks.signals import task_enqueued
from django_tasks.utils import get_random_id
from typing_extensions import ParamSpec

T = TypeVar("T")
P = ParamSpec("P")


class CeleryTaskBackend(BaseTaskBackend):
    """Enqueue django-tasks onto Celery; never DB, RQ, or django-tasks-celery."""

    def enqueue(
        self,
        task: Task[P, T],
        args: P.args,  # type: ignore[valid-type]
        kwargs: P.kwargs,  # type: ignore[valid-type]
    ) -> TaskResult[T]:
        self.validate_task(task)
        result: TaskResult[T] = TaskResult(
            task=task,
            id=get_random_id(),
            status=TaskResultStatus.READY,
            enqueued_at=timezone.now(),
            started_at=None,
            last_attempted_at=None,
            finished_at=None,
            args=list(args),
            kwargs=dict(kwargs),
            backend=self.alias,
            errors=[],
            worker_ids=[],
        )
        from platformapp.front_door.tasks import run_django_task  # noqa: PLC0415

        run_django_task.delay(task.module_path, list(args), dict(kwargs))
        task_enqueued.send(type(self), task_result=result)
        return result
