"""Celery runner for the in-tree django-tasks backend (steward 20.2)."""

from __future__ import annotations

from typing import Any

from celery import shared_task
from django.utils.module_loading import import_string
from django_tasks import task as django_task


def echo_payload(value: str) -> str:
    """Module-level callable used by tests and by run_django_task."""
    return f"echoed:{value}"


@django_task()
def tagged_echo(value: str) -> str:
    """django_tasks Task wrapper so run_django_task exercises Task.call()."""
    return f"tagged:{value}"


@shared_task(name="platformapp.front_door.run_django_task")
def run_django_task(module_path: str, args: list[Any], kwargs: dict[str, Any]) -> Any:
    target = import_string(module_path)
    call = getattr(target, "call", None)
    if callable(call) and getattr(target, "func", None) is not None:
        return call(*args, **kwargs)
    return target(*args, **kwargs)
