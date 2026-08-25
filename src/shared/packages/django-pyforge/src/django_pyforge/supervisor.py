"""Supervisor publish API — the only writer of run_state / mcp_handles (AD-12)."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from typing import Any

from django.core.cache import cache
from django.db import connection
from django.db import transaction
from django.db.utils import DatabaseError
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
QUERY_BUDGET_SECONDS = 0.5
LAST_OK_CACHE_KEY = "django_pyforge:supervisor:last_ok"

_runners: dict[tuple[str, str], Any] = {}


class HandleRefusedError(Exception):
    """Handle presented without a valid matching assertion."""


class HandleExpiredError(Exception):
    """Handle TTL has elapsed."""


class HandleNotFoundError(Exception):
    """No mcp_handles row for this token."""


class SupervisorUnavailableError(Exception):
    """Supervisor query failed or exceeded the FR-26 budget."""

    def __init__(self, last_ok_at: datetime | None = None) -> None:
        super().__init__("supervisor unavailable")
        self.last_ok_at = last_ok_at


@dataclass(frozen=True)
class BoardSnapshot:
    queried_at: datetime
    last_ok_at: datetime | None
    live: tuple[dict[str, Any], ...]
    timing: tuple[dict[str, Any], ...]


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
    started = timezone.now()
    with transaction.atomic():
        run = RunState.objects.create(
            status=RunState.Status.RUNNING,
            station=station,
            started_at=started,
            heartbeat_at=started,
        )
        McpHandle.objects.create(
            handle=token,
            run=run,
            expires_at=started + HANDLE_TTL,
            subject=subject,
        )
        run_id = str(run.id)
    from django_pyforge.tasks import execute_supervised_run  # noqa: PLC0415

    execute_supervised_run.delay(run_id, station, tool, payload or {})
    return token


def complete_run(run_id: str, *, status: str, result: Any) -> None:
    now = timezone.now()
    run = RunState.objects.filter(pk=run_id).first()
    started = run.started_at if run is not None and run.started_at is not None else now
    duration_ms = max(0, int((now - started).total_seconds() * 1000))
    RunState.objects.filter(pk=run_id).update(
        status=status,
        result=result,
        completed_at=now,
        heartbeat_at=now,
        duration_ms=duration_ms,
    )


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


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _coerce_dt(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed
    return None


def _row_payload(row: RunState) -> dict[str, Any]:
    return {
        "run_id": str(row.id),
        "station": row.station,
        "status": row.status,
        "started_at": _iso(row.started_at),
        "heartbeat_at": _iso(row.heartbeat_at),
        "completed_at": _iso(row.completed_at),
        "duration_ms": row.duration_ms,
    }


def load_board_rows() -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    live_statuses = (RunState.Status.PENDING, RunState.Status.RUNNING)
    done_statuses = (RunState.Status.SUCCEEDED, RunState.Status.FAILED)
    live = tuple(
        _row_payload(row)
        for row in RunState.objects.filter(status__in=live_statuses).order_by(
            "started_at",
        )
    )
    timing = tuple(
        _row_payload(row)
        for row in RunState.objects.filter(status__in=done_statuses).order_by(
            "-completed_at",
        )
    )
    return live, timing


def query_board() -> BoardSnapshot:
    """Read live runs and completed timing. Never a filesystem scrape."""
    queried_at = timezone.now()
    last_ok_at = _coerce_dt(cache.get(LAST_OK_CACHE_KEY))
    try:
        with transaction.atomic():
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SET LOCAL statement_timeout = %s",
                        [f"{int(QUERY_BUDGET_SECONDS * 1000)}ms"],
                    )
            live, timing = load_board_rows()
    except (TimeoutError, DatabaseError) as exc:
        raise SupervisorUnavailableError(last_ok_at=last_ok_at) from exc
    cache.set(LAST_OK_CACHE_KEY, queried_at, timeout=None)
    return BoardSnapshot(
        queried_at=queried_at,
        last_ok_at=queried_at,
        live=live,
        timing=timing,
    )
