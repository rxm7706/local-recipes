"""Supervisor publish API — the only writer of run_state / mcp_handles (AD-12)."""

from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from django_pyforge.assertion.crypto import verify_assertion
from django_pyforge.assertion.exceptions import AssertionRefusedError
from django_pyforge.assertion.schema import CLAIM_SUB
from django_pyforge.assertion.schema import audience_for
from django_pyforge.models import McpHandle
from django_pyforge.models import RunState

HANDLE_ENTROPY_BYTES = 32
HANDLE_TTL = timedelta(hours=24)
ATLAS_STATION = "atlas"
RUN_PIPELINE_TOOL = "run_pipeline"

_runners: dict[tuple[str, str], Any] = {}


class HandleRefusedError(Exception):
    """Handle presented without a valid matching assertion."""


class HandleExpiredError(Exception):
    """Handle TTL has elapsed."""


class HandleNotFoundError(Exception):
    """No mcp_handles row for this token."""


def register_runner(station: str, tool: str, fn: Any) -> None:
    _runners[(station, tool)] = fn


def lookup_runner(station: str, tool: str) -> Any:
    try:
        return _runners[(station, tool)]
    except KeyError as exc:
        msg = f"no runner for {station}/{tool}"
        raise HandleNotFoundError(msg) from exc


def mint_handle() -> str:
    return secrets.token_urlsafe(HANDLE_ENTROPY_BYTES)


def publish_start(
    *,
    station: str,
    assertion: str,
    tool: str = RUN_PIPELINE_TOOL,
    payload: dict[str, Any] | None = None,
) -> str:
    """Commit a running row + handle, then enqueue. Never a second ledger."""
    if not assertion:
        raise HandleRefusedError
    claims = verify_assertion(assertion, audience=audience_for(station))
    subject = claims.get(CLAIM_SUB)
    if not isinstance(subject, str) or not subject:
        raise HandleRefusedError
    token = mint_handle()
    if len(token) < HANDLE_ENTROPY_BYTES:
        msg = "handle entropy below contract"
        raise RuntimeError(msg)
    with transaction.atomic():
        run = RunState.objects.create(status=RunState.Status.RUNNING)
        McpHandle.objects.create(
            handle=token,
            run=run,
            expires_at=timezone.now() + HANDLE_TTL,
            subject=subject,
        )
        run_id = str(run.id)
    from django_pyforge.tasks import execute_supervised_run  # noqa: PLC0415

    execute_supervised_run.delay(run_id, station, tool, payload or {})
    return token


def complete_run(run_id: str, *, status: str, result: Any) -> None:
    RunState.objects.filter(pk=run_id).update(status=status, result=result)


def get_run(*, station: str, handle: str, assertion: str) -> dict[str, Any]:
    if not assertion:
        raise HandleRefusedError
    try:
        claims = verify_assertion(assertion, audience=audience_for(station))
    except AssertionRefusedError as exc:
        raise HandleRefusedError from exc
    subject = claims.get(CLAIM_SUB)
    try:
        row = McpHandle.objects.select_related("run").get(handle=handle)
    except McpHandle.DoesNotExist as exc:
        raise HandleNotFoundError from exc
    if timezone.now() >= row.expires_at:
        raise HandleExpiredError
    if row.subject != subject:
        raise HandleRefusedError
    run = row.run
    return {
        "status": run.status,
        "result": run.result,
        "run_id": str(run.id),
    }
