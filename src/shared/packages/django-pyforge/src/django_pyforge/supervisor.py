"""Supervisor publish API — the only writer of run_state / mcp_handles (AD-12).

Story 42.2 (CAP-11 / CAP-17, red-team A-6) makes ``publish_start`` bounded.
Before this, every call created a row and a task unconditionally, so one
looping agent could fill PostgreSQL and the ``noeviction`` broker until
Channels, Celery and the event bus died together. Three bounds now stand in
front of the write, and all three are checked *before* the transaction opens so
a refusal leaves no row behind:

1. a per-subject token bucket (``rate_limit``, on redis-cache),
2. a per-station ceiling on live runs — the queue depth, refused with 429,
3. a per-subject ceiling on live runs — refused with 409 naming the live ids,
   because the caller's remedy is to wait for or revoke its *own* runs.

The counts are read outside a lock, so under genuinely simultaneous starts a
subject can momentarily exceed its ceiling by the number of racing requests.
That is a ceiling, not a semaphore: the failure it exists to stop is an agent
loop issuing thousands of starts, and an off-by-a-few at the boundary does not
restore that failure. Making it exact would need a lock on a row that does not
exist yet, and that cost buys nothing here.

Story 42.4 (CAP-11 / CAP-17, red-team S-2 / T-6, directive R-10) closes the
other half of the ledger: a worker killed mid-task used to leave its row
``RUNNING`` forever, because the task's ``except`` never ran and nothing else
wrote. Two things now stand behind a live row:

* ``begin_attempt`` -- the worker's first act on a delivery. It refuses to run
  a run whose row is already terminal (revoked, swept or finished), bumps
  ``heartbeat_at`` so the sweep measures from the latest attempt, and lets a
  message the broker re-delivered (``acks_late`` + ``reject_on_worker_lost``
  put a lost worker's message back) run exactly once more -- a second
  re-delivery is the message loop that setting is documented to cause, and is
  terminalised here instead of re-run.
* ``sweep_lost_runs`` -- BS-8, partial: a live row whose last sign of life is
  older than its pool's hard limit, and whose task no worker reports holding,
  is marked ``FAILED`` with reason ``worker_lost``. The limit is per station
  (``queues.station_time_limit``) so a builds-pool run is not failed at 300 s.
"""

from __future__ import annotations

import json
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from http import HTTPStatus
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.db import transaction
from django.db.models import F
from django.db.models import Q
from django.db.utils import DatabaseError
from django.utils import timezone

from django_pyforge.assertion.crypto import verify_assertion
from django_pyforge.assertion.exceptions import AssertionRefusedError
from django_pyforge.assertion.schema import CLAIM_ROLES
from django_pyforge.assertion.schema import CLAIM_SUB
from django_pyforge.assertion.schema import audience_for
from django_pyforge.events.constants import EVENT_SCHEMAS
from django_pyforge.events.constants import EXT_GIT_SHA
from django_pyforge.events.constants import EXT_SBOM_PURL
from django_pyforge.events.constants import EXT_SPEC_ID
from django_pyforge.events.constants import EXT_TENANT
from django_pyforge.events.fabric import EventBrokerConfigError
from django_pyforge.events.fabric import connect_event_broker
from django_pyforge.models import McpHandle
from django_pyforge.models import RunState
from django_pyforge.queues import station_time_limit
from django_pyforge.rate_limit import START_SCOPE
from django_pyforge.rate_limit import consume
from django_pyforge.rate_limit import int_setting
from django_pyforge.roles import unique_tenant_from_raw

HANDLE_ENTROPY_BYTES = 32
# Story 42.4: the reason a swept (or re-delivered-twice) run is FAILED with.
WORKER_LOST_REASON = "worker_lost"
# Marker kept in a LIVE row's `result` once the broker has re-delivered its
# task. `complete_run` overwrites `result` on completion, so it never survives
# into a terminal row's payload except inside the worker_lost report.
REDELIVERED_KEY = "redelivered"
# How long the sweep waits for workers to answer an inspect broadcast.
INSPECT_TIMEOUT_SECONDS = 2.0
HANDLE_TTL = timedelta(hours=24)
ATLAS_STATION = "atlas"
RUN_PIPELINE_TOOL = "run_pipeline"
QUERY_BUDGET_SECONDS = 0.5
LAST_OK_CACHE_KEY = "django_pyforge:supervisor:last_ok"

# Story 42.2 run bounds. Documented defaults; each is a Django setting.
SETTING_MAX_RUNNING_PER_SUB = "MAX_RUNNING_PER_SUB"
SETTING_MAX_QUEUE_DEPTH = "MAX_QUEUE_DEPTH_PER_STATION"
SETTING_RETENTION_DAYS = "RUN_STATE_RETENTION_DAYS"
SETTING_MAX_ROWS = "RUN_STATE_MAX_ROWS"
DEFAULT_MAX_RUNNING_PER_SUB = 5
DEFAULT_MAX_QUEUE_DEPTH_PER_STATION = 100
DEFAULT_RETENTION_DAYS = 14
DEFAULT_MAX_ROWS = 100_000
# A full station drains at whatever pace its workers manage; this is the
# "come back later" a caller is told, not a promise about that pace.
QUEUE_FULL_RETRY_AFTER_SECONDS = 30
SETTING_PRUNE_BATCH = "RUN_STATE_PRUNE_BATCH"
DEFAULT_PRUNE_BATCH = 5_000

logger = logging.getLogger(__name__)

_runners: dict[tuple[str, str], Any] = {}
_tool_error_fallback_logged = False


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


class RunBoundExceeded(Exception):
    """A ``start`` refused by a run bound, carrying its own HTTP shape.

    The status lives on the exception rather than being decided by each caller
    so that the portal face, the MCP tool and any future face refuse a bound
    identically -- three call sites cannot drift into three different codes for
    the same condition.
    """

    status: HTTPStatus = HTTPStatus.TOO_MANY_REQUESTS
    error: str = "refused"

    def __init__(
        self,
        message: str,
        *,
        retry_after: int = 0,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after = int(retry_after)
        self.details = dict(details or {})

    def payload(self) -> dict[str, Any]:
        body: dict[str, Any] = {"error": self.error, "detail": str(self)}
        if self.retry_after > 0:
            body["retry_after"] = self.retry_after
        body.update(self.details)
        return body

    def headers(self) -> dict[str, str]:
        if self.retry_after <= 0:
            return {}
        return {"Retry-After": str(self.retry_after)}


class SubjectRateLimited(RunBoundExceeded):
    """The subject spent its ``start`` allowance (or could not be counted)."""

    status = HTTPStatus.TOO_MANY_REQUESTS
    error = "rate limited"


class StationQueueFull(RunBoundExceeded):
    """The station is already at its live-run ceiling — nothing is written."""

    status = HTTPStatus.TOO_MANY_REQUESTS
    error = "station queue full"


class TooManyRunningForSubject(RunBoundExceeded):
    """The subject holds its maximum concurrent runs. 409, with their ids.

    409 rather than 429 because retrying later is not the only remedy and the
    caller can act now: the conflicting resources are its OWN live runs, so the
    ids are the response's most useful content.
    """

    status = HTTPStatus.CONFLICT
    error = "too many running"


class BoundedStartRefused(Exception):
    """A run bound projected for a tool face, when the MCP SDK is absent.

    The payload IS the message: a transport that can only carry ``str(exc)``
    must still deliver the status, the ``Retry-After`` and -- for the 409 --
    the ``run_ids``, which are the whole point of that refusal.
    """

    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__(json.dumps(payload, sort_keys=True))
        self.payload = dict(payload)


def bound_refusal_payload(exc: RunBoundExceeded) -> dict[str, Any]:
    """The one projection of a run bound. Every face renders THIS.

    Shared rather than re-derived per face so the portal, the MCP tools and
    anything added later cannot drift into three descriptions of one condition
    -- the drift `views.py` already claims not to have.
    """
    return {"status": int(exc.status), **exc.payload()}


def _log_tool_error_fallback() -> None:
    """Say so, once, when a bound has to cross without the SDK's ``ToolError``.

    Silent, this fallback would hide the exact regression it exists to survive:
    an SDK release that moved ``ToolError`` would quietly turn every projected
    refusal back into the withheld-text crash, with nothing in the log to say
    why agents had stopped seeing ``run_ids``.
    """
    global _tool_error_fallback_logged
    if _tool_error_fallback_logged:
        return
    _tool_error_fallback_logged = True
    logger.warning(
        "supervisor.tool_error_unavailable",
        extra={"event": "supervisor.tool_error_unavailable"},
    )


def _tool_refusal(payload: dict[str, Any]) -> Exception:
    """The exception an MCP tool must raise for its message to survive.

    Not defensiveness -- a contract. The SDK divides tool failures in two:
    ``ToolError`` is "a failure you anticipated" and its text reaches the model
    inside ``is_error`` content, while **anything else is a crash whose text is
    withheld**, reaching the agent as the bare string ``Error executing tool
    start_audit``. A run bound raised as a plain exception therefore arrives
    with no status, no ``retry_after`` and no ``run_ids`` -- present in the
    server log, absent from the answer. Imported lazily, like
    ``celery_control`` above, because the supervisor must stay importable in an
    interpreter with no MCP SDK (see ``mcp_http._log_import_skip``).
    """
    try:
        from mcp.server.mcpserver.exceptions import ToolError  # noqa: PLC0415
    except ImportError:
        _log_tool_error_fallback()
        return BoundedStartRefused(payload)
    refusal = ToolError(json.dumps(payload, sort_keys=True))
    refusal.payload = dict(payload)
    return refusal


def start_bounded(
    *,
    station: str,
    assertion: str,
    tool: str,
    payload: dict[str, Any] | None = None,
) -> str:
    """``publish_start`` for a tool face: a bound becomes a legible refusal.

    Used by every MCP ``start`` tool. Nothing else about ``publish_start``
    changes -- this only decides how a bound crosses a transport that cannot
    carry an exception.
    """
    try:
        return publish_start(
            station=station,
            assertion=assertion,
            tool=tool,
            payload=payload,
        )
    except RunBoundExceeded as exc:
        raise _tool_refusal(bound_refusal_payload(exc)) from exc


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


def live_runs_for_subject(subject: str) -> list[str]:
    """Run ids this subject currently holds in a non-terminal state."""
    return [
        str(run_id)
        for run_id in RunState.objects.filter(
            subject=subject,
            status__in=RunState.LIVE_STATUSES,
        ).values_list("id", flat=True)
    ]


def station_queue_depth(station: str) -> int:
    """Live runs published for ``station``, whoever published them."""
    return RunState.objects.filter(
        station=station,
        status__in=RunState.LIVE_STATUSES,
    ).count()


def enforce_run_bounds(*, station: str, subject: str) -> None:
    """Raise the matching ``RunBoundExceeded`` when a bound is reached.

    Called before the transaction opens, so every refusal leaves the ledger
    exactly as it found it -- "429 and no ``RunState`` row" is a property of
    where this runs, not of a rollback.
    """
    decision = consume(START_SCOPE, subject)
    if not decision.allowed:
        msg = f"start rate exceeded for {subject}"
        raise SubjectRateLimited(
            msg,
            retry_after=decision.retry_after,
            details={"reason": decision.reason},
        )
    ceiling = int_setting(
        SETTING_MAX_QUEUE_DEPTH,
        DEFAULT_MAX_QUEUE_DEPTH_PER_STATION,
    )
    depth = station_queue_depth(station)
    if depth >= ceiling:
        msg = f"{station} is at its live-run ceiling ({depth}/{ceiling})"
        raise StationQueueFull(
            msg,
            retry_after=QUEUE_FULL_RETRY_AFTER_SECONDS,
            details={"station": station, "queue_depth": depth, "limit": ceiling},
        )
    max_running = int_setting(
        SETTING_MAX_RUNNING_PER_SUB,
        DEFAULT_MAX_RUNNING_PER_SUB,
    )
    live = live_runs_for_subject(subject)
    if len(live) >= max_running:
        msg = f"{subject} already holds {len(live)} live runs (max {max_running})"
        raise TooManyRunningForSubject(
            msg,
            details={"run_ids": live, "limit": max_running},
        )


def _tenant_from_assertion_claims(claims: dict[str, object]) -> str:
    raw_roles = claims.get(CLAIM_ROLES)
    if not isinstance(raw_roles, list):
        return ""
    return unique_tenant_from_raw(raw_roles)


def _publish_run_started_event(
    *,
    run_id: str,
    station: str,
    subject: str,
    tenant: str,
) -> None:
    """Best-effort ``run.started`` on the event bus (Story 42.5)."""
    broker_url = getattr(settings, "REDIS_BROKER_URL", "") or getattr(
        settings,
        "CELERY_BROKER_URL",
        "",
    )
    cache_url = getattr(settings, "REDIS_CACHE_URL", "") or getattr(
        settings,
        "REDIS_URL",
        "",
    )
    if not isinstance(broker_url, str) or not broker_url.strip():
        return
    if not isinstance(cache_url, str) or not cache_url.strip():
        return
    try:
        fabric = connect_event_broker(broker_url.strip(), cache_url.strip())
    except EventBrokerConfigError:
        logger.warning(
            "supervisor.run_started_event_skipped",
            extra={
                "event": "supervisor.run_started_event_skipped",
                "run_id": run_id,
                "reason": "broker/cache URLs must differ",
            },
        )
        return
    envelope: dict[str, Any] = {
        "type": "run.started",
        "source": f"/stations/{station}",
        "dataschema": EVENT_SCHEMAS["run.started"],
        EXT_SPEC_ID: "spec-42-5-role-namespaces-and-the-tenant-claim",
        EXT_GIT_SHA: "local",
        EXT_SBOM_PURL: "pkg:pypi/django-pyforge@0.1.0",
        "data": {"run_id": run_id, "station": station, "subject": subject},
    }
    if tenant:
        envelope[EXT_TENANT] = tenant
    try:
        fabric.publish(envelope)
    except Exception as exc:
        logger.warning(
            "supervisor.run_started_event_failed",
            extra={
                "event": "supervisor.run_started_event_failed",
                "run_id": run_id,
                "reason": str(exc),
            },
        )


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
    tenant = _tenant_from_assertion_claims(claims)
    enforce_run_bounds(station=station, subject=subject)
    token = mint_handle()
    if len(token) < HANDLE_ENTROPY_BYTES:
        msg = "handle entropy below contract"
        raise RuntimeError(msg)
    # Minted here rather than read back from the enqueue: the row must already
    # name the task when the task becomes revocable, and `apply_async` returns
    # only after the message is on the broker.
    task_id = str(uuid.uuid4())
    started = timezone.now()
    with transaction.atomic():
        run = RunState.objects.create(
            status=RunState.Status.RUNNING,
            station=station,
            subject=subject,
            tenant=tenant,
            celery_task_id=task_id,
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
    from django_pyforge.tasks import enqueue_supervised_run  # noqa: PLC0415

    try:
        enqueue_supervised_run(
            run_id,
            station,
            tool,
            payload or {},
            subject=subject,
            task_id=task_id,
        )
    except Exception as exc:
        # A live row whose task was never published is immortal: `prune_run_state`
        # never touches live rows, so it counts against MAX_RUNNING_PER_SUB and the
        # station ceiling forever. With this story's bounds in place that turns a
        # broker outage into a permanent lockout -- five failures and the subject
        # can never start again. Terminalise before re-raising, so the bounds
        # release and the caller still learns the enqueue failed.
        logger.error(
            "supervisor.enqueue_failed",
            extra={
                "event": "supervisor.enqueue_failed",
                "run_id": run_id,
                "station": station,
                "sub": subject,
            },
        )
        complete_run(
            run_id,
            status=RunState.Status.FAILED,
            result={"error": f"enqueue failed: {exc}"},
        )
        raise
    _publish_run_started_event(
        run_id=run_id,
        station=station,
        subject=subject,
        tenant=tenant,
    )
    return token


def complete_run(run_id: str, *, status: str, result: Any) -> None:
    """Move a live run to a terminal state. A terminal row is never rewritten.

    ``revoke`` can land while a worker is already executing the task, and
    ``control.revoke`` cannot recall a task that has started. An unconditional
    update would then let the finishing worker overwrite the operator's
    CANCELLED with ``succeeded``/``failed`` -- destroying the very record the
    revoke created, and re-introducing exactly the conflation the CANCELLED
    status exists to prevent. Terminal wins; the later write is dropped and
    logged.
    """
    now = timezone.now()
    run = RunState.objects.filter(pk=run_id).first()
    started = run.started_at if run is not None and run.started_at is not None else now
    duration_ms = max(0, int((now - started).total_seconds() * 1000))
    updated = (
        RunState.objects.filter(pk=run_id)
        .exclude(status__in=RunState.TERMINAL_STATUSES)
        .update(
            status=status,
            result=result,
            completed_at=now,
            heartbeat_at=now,
            duration_ms=duration_ms,
        )
    )
    if not updated and run is not None:
        logger.warning(
            "supervisor.terminal_write_ignored",
            extra={
                "event": "supervisor.terminal_write_ignored",
                "run_id": run_id,
                "existing_status": run.status,
                "attempted_status": status,
            },
        )


def celery_control() -> Any:
    """Celery's broadcast control face, or ``None`` when Celery is absent."""
    try:
        from celery import current_app  # noqa: PLC0415
    except ImportError:
        return None
    return current_app.control


def begin_attempt(run_id: str, *, redelivered: bool = False) -> bool:
    """The worker's first act on a delivery: may this run execute now?

    ``False`` means "do not run" -- and the row already says why:

    * the row is terminal: revoked, swept as ``worker_lost``, or a re-delivery
      of a run that already finished. Running it would do work the ledger has
      already closed the book on.
    * the row is gone: an unsupervised task is not a supervised run (AD-12).
    * the message was re-delivered and the row already records a re-delivery.
      ``acks_late`` + ``reject_on_worker_lost`` put a lost worker's message
      back exactly so it runs again; a task that loses its worker twice is the
      message loop that setting is documented to cause (a build that OOM-kills
      every pool it lands on), so the second re-delivery terminalises the run
      as ``worker_lost`` instead of running it a third time.

    ``True`` bumps ``heartbeat_at`` first, so ``sweep_lost_runs`` measures the
    limit from the latest attempt rather than from the original start.
    """
    row = RunState.objects.filter(pk=run_id).values("status", "result").first()
    if row is None:
        logger.warning(
            "supervisor.attempt_without_row",
            extra={"event": "supervisor.attempt_without_row", "run_id": run_id},
        )
        return False
    if row["status"] in RunState.TERMINAL_STATUSES:
        logger.info(
            "supervisor.attempt_on_terminal_run",
            extra={
                "event": "supervisor.attempt_on_terminal_run",
                "run_id": run_id,
                "status": row["status"],
                "redelivered": redelivered,
            },
        )
        return False
    now = timezone.now()
    live = RunState.objects.filter(pk=run_id).exclude(
        status__in=RunState.TERMINAL_STATUSES,
    )
    if not redelivered:
        live.update(heartbeat_at=now)
        return True
    prior = row["result"] if isinstance(row["result"], dict) else {}
    if prior.get(REDELIVERED_KEY):
        logger.error(
            "supervisor.redelivered_twice",
            extra={"event": "supervisor.redelivered_twice", "run_id": run_id},
        )
        complete_run(
            run_id,
            status=RunState.Status.FAILED,
            result={
                "error": "worker lost twice; not re-running a third time",
                "reason": WORKER_LOST_REASON,
                REDELIVERED_KEY: True,
                "attempts": 2,
            },
        )
        return False
    logger.warning(
        "supervisor.redelivered",
        extra={"event": "supervisor.redelivered", "run_id": run_id},
    )
    live.update(heartbeat_at=now, result={**prior, REDELIVERED_KEY: True})
    return True


def _celery_inspector() -> Any:
    control = celery_control()
    if control is None:
        return None
    return control.inspect(timeout=INSPECT_TIMEOUT_SECONDS)


class InspectUnavailableError(Exception):
    """The workers could not be asked what they hold (broker unreachable)."""


def live_task_ids(inspector: Any | None = None) -> frozenset[str]:
    """Task ids some worker reports holding -- active, reserved or scheduled.

    An EMPTY answer (no worker replied to the broadcast) means no worker holds
    anything, and is a valid answer. A broadcast that RAISES is not: the
    broker could not be reached, so nothing is known, and the caller must not
    treat silence as absence.
    """
    face = inspector if inspector is not None else _celery_inspector()
    if face is None:
        return frozenset()
    held: set[str] = set()
    for probe in ("active", "reserved", "scheduled"):
        method = getattr(face, probe, None)
        if method is None:
            continue
        try:
            replies = method()
        except Exception as exc:
            msg = f"inspect.{probe} failed: {exc!r}"
            raise InspectUnavailableError(msg) from exc
        for tasks in (replies or {}).values():
            for item in tasks or []:
                if not isinstance(item, dict):
                    continue
                # `scheduled` nests the request under "request"; the others
                # are the request itself.
                nested = item.get("request")
                request = nested if isinstance(nested, dict) else item
                task_id = request.get("id")
                if isinstance(task_id, str) and task_id:
                    held.add(task_id)
    return frozenset(held)


def sweep_lost_runs(
    *,
    now: datetime | None = None,
    inspector: Any | None = None,
) -> dict[str, Any]:
    """Mark live runs whose worker is gone as FAILED / ``worker_lost`` (BS-8, partial).

    A row is a candidate when its last sign of life (``heartbeat_at``, else
    ``started_at``) is older than the hard limit of the pool its station's
    work can land on -- past that limit the task has either been killed by
    Celery's own hard limit (whose SIGKILL runs no ``except`` in the child)
    or its worker was lost. Candidates whose task id a worker still reports
    holding are left alone: a re-delivered task legitimately runs past the
    original start. When the workers cannot be asked at all, nothing is
    swept and the report says so; silence from a dead broker is not proof
    that a task is dead.
    """
    moment = now if now is not None else timezone.now()
    live_rows = list(
        RunState.objects.filter(status__in=RunState.LIVE_STATUSES).values(
            "id",
            "station",
            "celery_task_id",
            "started_at",
            "heartbeat_at",
        ),
    )
    stale: list[tuple[dict[str, Any], int, datetime]] = []
    for row in live_rows:
        last_seen = row["heartbeat_at"] or row["started_at"]
        if last_seen is None:
            continue
        limit = station_time_limit(row["station"])
        if moment - last_seen > timedelta(seconds=limit):
            stale.append((row, limit, last_seen))
    report: dict[str, Any] = {
        "live": len(live_rows),
        "stale": len(stale),
        "swept": 0,
        "still_held": 0,
        "inspected": False,
        "run_ids": [],
    }
    if not stale:
        return report
    try:
        held = live_task_ids(inspector)
    except InspectUnavailableError as exc:
        logger.exception(
            "supervisor.sweep_inspect_unavailable",
            extra={
                "event": "supervisor.sweep_inspect_unavailable",
                "stale": len(stale),
                "error": str(exc),
            },
        )
        report["error"] = str(exc)
        return report
    report["inspected"] = True
    for row, limit, last_seen in stale:
        task_id = row["celery_task_id"]
        if task_id and task_id in held:
            report["still_held"] += 1
            continue
        run_id = str(row["id"])
        idle = int((moment - last_seen).total_seconds())
        logger.error(
            "supervisor.worker_lost",
            extra={
                "event": "supervisor.worker_lost",
                "run_id": run_id,
                "station": row["station"],
                "task_id": task_id,
                "idle_seconds": idle,
                "limit_seconds": limit,
            },
        )
        complete_run(
            run_id,
            status=RunState.Status.FAILED,
            result={
                "error": f"worker lost: no live task for {idle}s (limit {limit}s)",
                "reason": WORKER_LOST_REASON,
                "task_id": task_id,
                "last_seen_at": _iso(last_seen),
                "limit_seconds": limit,
            },
        )
        report["swept"] += 1
        report["run_ids"].append(run_id)
    return report


def revoke_subject(
    subject: str,
    *,
    control: Any | None = None,
    reason: str = "revoked by operator",
) -> dict[str, Any]:
    """Revoke one subject's queued tasks and cancel its live runs.

    The Celery revoke goes first: a task revoked while the row still says
    RUNNING is merely a run that will never start, whereas a row cancelled
    before the revoke lands leaves a task the ledger has stopped tracking. Both
    halves are reported so an operator can see when only one succeeded.

    Rows are marked CANCELLED, never deleted -- a caller still holding a handle
    gets a terminal answer instead of a 404, and the retention task removes the
    row on the normal schedule.

    An empty subject is refused HERE, in the single writer (AD-12), not in one
    of its callers: migration 0004 defaults ``subject`` to ``""`` on every row
    that predates it, so ``revoke_subject("")`` would cancel the entire legacy
    estate in one command. A guard that lives in only one caller is a guard the
    next caller does not have.
    """
    subject = subject.strip() if isinstance(subject, str) else ""
    if not subject:
        msg = (
            "revoke_subject requires a non-empty subject: pre-0004 rows carry "
            "subject='' and would all be cancelled"
        )
        raise ValueError(msg)
    rows = list(
        RunState.objects.filter(
            subject=subject,
            status__in=RunState.LIVE_STATUSES,
        ).values("id", "celery_task_id"),
    )
    run_ids = [str(row["id"]) for row in rows]
    task_ids = [row["celery_task_id"] for row in rows if row["celery_task_id"]]
    revoked_tasks: list[str] = []
    revoke_error: str | None = None
    if task_ids:
        face = control if control is not None else celery_control()
        if face is None:
            revoke_error = "celery control unavailable"
        else:
            try:
                # `terminate=True` because a queued revoke only stops a task
                # that has not started; without it, a task already executing
                # runs to completion and its `complete_run` races the CANCELLED
                # this function is about to write.
                face.revoke(task_ids, terminate=True)
            except Exception as exc:  # noqa: BLE001 -- reported, not swallowed
                revoke_error = repr(exc)
            else:
                revoked_tasks = list(task_ids)
    now = timezone.now()
    cancelled = 0
    if run_ids:
        # Live rows only, re-checked inside the UPDATE itself: a run that
        # finished between the SELECT above and this write is already terminal,
        # and the rule `complete_run` enforces holds in this direction too --
        # terminal wins. A `succeeded` row and its result are not replaced by a
        # cancellation that arrived too late to mean anything, and
        # `cancelled_runs` reports what was actually cancelled.
        cancelled = RunState.objects.filter(
            pk__in=run_ids,
            status__in=RunState.LIVE_STATUSES,
        ).update(
            status=RunState.Status.CANCELLED,
            completed_at=now,
            heartbeat_at=now,
            result={"cancelled": True, "reason": reason},
        )
    return {
        "subject": subject,
        "cancelled_runs": cancelled,
        "run_ids": run_ids,
        "revoked_tasks": revoked_tasks,
        "revoke_error": revoke_error,
        "ok": revoke_error is None,
    }


def _deleted(outcome: tuple[int, dict[str, int]], model: Any) -> int:
    """Rows of ``model`` removed by a ``delete()``, excluding its cascades.

    ``QuerySet.delete()`` reports a grand total across every cascaded model, so
    reading element 0 counts each run twice over whenever it had a handle and
    makes the report a fiction. Every count in the sweep goes through here --
    one read, so a second caller cannot reintroduce the fiction.
    """
    _total, per_model = outcome
    return int(per_model.get(model._meta.label, 0))  # noqa: SLF001


def _delete_by_ids(manager: Any, ids: list[Any], model: Any) -> int:
    if not ids:
        return 0
    return _deleted(manager.filter(pk__in=ids).delete(), model)


def prune_run_state(*, now: datetime | None = None) -> dict[str, Any]:
    """Retention + a hard ceiling on ``run_state``. Terminal rows only.

    Two passes, because age alone does not bound anything: a burst inside the
    retention window is exactly the shape that fills the table. The age pass is
    the policy; the cap pass is the guarantee. Live rows are never touched by
    either -- pruning a RUNNING row would orphan a task that is still working.

    ``McpHandle`` rows cascade with their run; expired handles for runs still
    inside the window are deleted separately, since the capability is dead the
    moment it expires.

    **Every pass is batched.** The first sweep after this story deploys runs
    over a table that grew for the life of the deployment, and one unbounded
    ``pk__in`` DELETE across it can exceed ``CELERY_TASK_SOFT_TIME_LIMIT`` (60s)
    and never complete -- a retention task that can never finish bounds nothing.
    So a sweep removes at most ``RUN_STATE_PRUNE_BATCH`` rows per pass and says
    so: ``truncated`` is the report telling the operator (and the schedule) that
    work remains, rather than a count that implies the table is now in policy.
    """
    moment = now if now is not None else timezone.now()
    retention_days = int_setting(SETTING_RETENTION_DAYS, DEFAULT_RETENTION_DAYS)
    max_rows = int_setting(SETTING_MAX_ROWS, DEFAULT_MAX_ROWS)
    batch = int_setting(SETTING_PRUNE_BATCH, DEFAULT_PRUNE_BATCH)
    cutoff = moment - timedelta(days=retention_days)

    # A terminal row with no `completed_at` cannot show it is inside the
    # window, so it is not: `complete_run` and `revoke` always stamp one, and
    # the rows without it predate the timing columns (0003) -- older than any
    # retention window, and otherwise exempt from it forever.
    aged_ids = list(
        RunState.objects.filter(status__in=RunState.TERMINAL_STATUSES)
        .filter(Q(completed_at__lt=cutoff) | Q(completed_at__isnull=True))
        .values_list("id", flat=True)[:batch],
    )
    aged_out = _delete_by_ids(RunState.objects, aged_ids, RunState)

    handle_ids = list(
        McpHandle.objects.filter(expires_at__lt=moment).values_list(
            "id",
            flat=True,
        )[:batch],
    )
    expired_handles = _delete_by_ids(McpHandle.objects, handle_ids, McpHandle)

    # The cap pass spends what the age pass left, so one sweep's total work is
    # bounded by `batch` rather than by twice it.
    budget = max(0, batch - len(aged_ids))
    surplus = RunState.objects.count() - max_rows
    over_cap = 0
    if surplus > 0 and budget > 0:
        oldest = list(
            RunState.objects.filter(status__in=RunState.TERMINAL_STATUSES)
            .order_by(
                F("completed_at").asc(nulls_first=True),
                F("started_at").asc(nulls_first=True),
            )
            .values_list("id", flat=True)[: min(surplus, budget)],
        )
        over_cap = _delete_by_ids(RunState.objects, oldest, RunState)

    remaining = RunState.objects.count()
    # Over the cap is only "work remains" while something is still prunable:
    # live rows alone above `max_rows` are the ceilings' business, and a sweep
    # reporting `truncated` with nothing it may delete would send an operator
    # -- or the self-rescheduling task -- round forever.
    over_cap_left = remaining > max_rows and (
        RunState.objects.filter(status__in=RunState.TERMINAL_STATUSES).exists()
    )
    truncated = len(aged_ids) >= batch or len(handle_ids) >= batch or over_cap_left
    return {
        "aged_out": int(aged_out),
        "over_cap": int(over_cap),
        "expired_handles": int(expired_handles),
        "remaining": remaining,
        "retention_days": retention_days,
        "max_rows": max_rows,
        "batch_limit": batch,
        "truncated": truncated,
    }


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
    live_statuses = RunState.LIVE_STATUSES
    # CANCELLED is done, not live: a revoked run must leave the live board or
    # `revoke` would look like it did nothing (Story 42.2).
    done_statuses = RunState.TERMINAL_STATUSES
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
