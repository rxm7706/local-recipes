"""Story 33.12 CAP-1 — held-run publish, heartbeat, sweep, and bound override."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from django.utils import timezone
from django_pyforge.assertion.crypto import mint_assertion
from django_pyforge.models import McpHandle
from django_pyforge.models import RunState
from django_pyforge.roles import prefixed_station
from django_pyforge.supervisor import HEARTBEAT_LOST_REASON
from django_pyforge.supervisor import HELD_CELERY_TASK_ID
from django_pyforge.supervisor import LOOP_PUBLISH_TOOL
from django_pyforge.supervisor import RunBoundExceeded
from django_pyforge.supervisor import complete_held_run
from django_pyforge.supervisor import enforce_run_bounds
from django_pyforge.supervisor import heartbeat_held_run
from django_pyforge.supervisor import list_published_story_tasks
from django_pyforge.supervisor import publish_held_run
from django_pyforge.supervisor import sweep_lost_runs


def _marshal_assertion(sub: str = "held-operator") -> str:
    return mint_assertion(
        sub=sub,
        roles=[prefixed_station("marshal")],
        station="marshal",
    )


@pytest.mark.django_db
def test_publish_held_run_creates_empty_celery_task_id_row() -> None:
    handle = publish_held_run(
        station="marshal",
        assertion=_marshal_assertion(),
        payload={
            "station": "pyforge-marshal",
            "harness_run_id": "20260101-120000",
            "story_key": "33-12-held",
            "phase": "running",
        },
    )
    assert handle
    run = McpHandle.objects.get(handle=handle).run
    assert run.celery_task_id == HELD_CELERY_TASK_ID
    assert run.status == RunState.Status.RUNNING


@pytest.mark.django_db
def test_heartbeat_bumps_held_run_and_sweep_marks_heartbeat_lost(monkeypatch) -> None:
    handle = publish_held_run(
        station="marshal",
        assertion=_marshal_assertion(),
        payload={"station": "pyforge-marshal", "harness_run_id": "run-a"},
    )
    run = McpHandle.objects.get(handle=handle).run
    stale_moment = timezone.now() + timedelta(hours=2)
    RunState.objects.filter(pk=run.pk).update(
        heartbeat_at=stale_moment - timedelta(hours=1),
        started_at=stale_moment - timedelta(hours=1),
    )
    inspect = MagicMock()
    report = sweep_lost_runs(now=stale_moment, inspector=inspect)
    inspect.assert_not_called()
    run.refresh_from_db()
    assert report["swept"] == 1
    assert run.status == RunState.Status.FAILED
    assert isinstance(run.result, dict)
    assert run.result.get("reason") == HEARTBEAT_LOST_REASON


@pytest.mark.django_db
def test_terminal_held_heartbeat_opens_new_attempt_linked_by_harness_run_id() -> None:
    handle = publish_held_run(
        station="marshal",
        assertion=_marshal_assertion(),
        payload={
            "station": "pyforge-marshal",
            "harness_run_id": "linked-run",
            "story_key": "33-12-terminal",
        },
    )
    complete_held_run(handle, status=RunState.Status.SUCCEEDED, result={"ok": True})
    terminal = McpHandle.objects.get(handle=handle).run
    terminal_id = terminal.pk
    heartbeat_held_run(handle)
    handle_row = McpHandle.objects.get(handle=handle)
    new_run = handle_row.run
    assert new_run.pk != terminal_id
    terminal.refresh_from_db()
    assert terminal.status == RunState.Status.SUCCEEDED
    assert new_run.status == RunState.Status.RUNNING
    assert isinstance(new_run.result, dict)
    assert new_run.result.get("harness_run_id") == "linked-run"


@pytest.mark.django_db
def test_loop_publish_bound_override_allows_more_than_default_five() -> None:
    subject = "fanout-operator"
    assertion = _marshal_assertion(subject)
    for _ in range(6):
        publish_held_run(
            station="marshal",
            assertion=assertion,
            payload={"station": "pyforge-marshal", "harness_run_id": "wave"},
            tool=LOOP_PUBLISH_TOOL,
        )
    with pytest.raises(RunBoundExceeded):
        enforce_run_bounds(station="marshal", subject=subject)


@pytest.mark.django_db
def test_list_published_story_tasks_returns_merged_tasks() -> None:
    publish_held_run(
        station="marshal",
        assertion=_marshal_assertion(),
        payload={
            "station": "pyforge-marshal",
            "story_key": "33-12-list",
            "phase": "running",
            "commit_sha": "abc123",
        },
    )
    tasks = list_published_story_tasks(station="marshal", project_slug="marshal")
    assert tasks["33-12-list"]["commit_sha"] == "abc123"
