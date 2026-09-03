"""Story 42.2 — agent rate limits and run bounds.

Red-team A-6 (nothing rate-limited ``POST /stations/<name>/mcp`` or supervisor
``start``, so an agent loop was a platform-wide DoS with no backpressure) and
B-7 (no queue-depth limit, no per-subject limit, no retention on
``RunState``). Directive **R-8**.

Every bound here is keyed on the verified ``sub`` claim, never a client name,
and every test proves that by exercising two subjects rather than one: a
limiter that throttled a *route* rather than a *subject* passes a
single-subject test and fails the platform.
"""

from __future__ import annotations

import ast
import asyncio
import json
import logging
from datetime import timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest
from django.core.cache import caches
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone
from django_pyforge import rate_limit
from django_pyforge.assertion.crypto import mint_assertion
from django_pyforge.mcp_http import dispatch_station_mcp
from django_pyforge.models import McpHandle
from django_pyforge.models import RunState
from django_pyforge.rate_limit import MCP_SCOPE
from django_pyforge.rate_limit import START_SCOPE
from django_pyforge.rate_limit import Bucket
from django_pyforge.rate_limit import consume
from django_pyforge.supervisor import StationQueueFull
from django_pyforge.supervisor import SubjectRateLimited
from django_pyforge.supervisor import TooManyRunningForSubject
from django_pyforge.supervisor import live_runs_for_subject
from django_pyforge.supervisor import prune_run_state
from django_pyforge.supervisor import publish_start
from django_pyforge.supervisor import register_runner
from django_pyforge.supervisor import revoke_subject
from django_pyforge.tasks import SUBJECT_HEADER
from django_pyforge.tasks import execute_supervised_run

from platformapp.front_door.lane1_runtime import channel_layers_for_broker
from platformapp.front_door.lane1_runtime import django_cache_aliases

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLATFORM_ROOT.parents[1]
BASE_SETTINGS_PATH = PLATFORM_ROOT / "config" / "settings" / "base.py"

STATION = "atlas"
AGENT = "agent-42-2"
OTHER_AGENT = "agent-42-2-bystander"


def _assertion(sub: str, station: str = STATION) -> str:
    return mint_assertion(sub=sub, roles=[f"pyforge:station:{station}"], station=station)


def _scope(assertion: str, station: str = STATION) -> dict[str, Any]:
    return {
        "type": "http",
        "path": f"/stations/{station}/mcp",
        "method": "POST",
        "headers": [
            (b"content-type", b"application/json"),
            (b"authorization", f"Bearer {assertion}".encode("latin-1")),
        ],
    }


async def _receive() -> dict[str, Any]:
    return {"type": "http.request", "body": b"{}", "more_body": False}


@pytest.fixture(autouse=True)
def _station_app_behind_the_gate():
    """Put a trivial app behind the route, and restore whatever was there.

    ``mcp_http`` caches station apps in a process-global dict, so what an
    ALLOWED call lands on depends on which other test module ran first -- a
    real ``MCPServer`` mounted by another test raises "Task group is not
    initialized" when driven outside its lifespan. Pinning the app makes
    "allowed" mean one thing here, and restoring the previous binding keeps
    that choice from leaking into the modules that mount the real servers.
    """
    from django_pyforge import mcp_http  # noqa: PLC0415

    previous = mcp_http.station_mcp_app(STATION)

    async def stub(_scope: Any, _receive: Any, send: Any) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": int(HTTPStatus.OK),
                "headers": [(b"content-type", b"application/json")],
            },
        )
        await send({"type": "http.response.body", "body": b"{}"})

    mcp_http.register_station_mcp_app(STATION, stub)
    yield
    if previous is None:
        mcp_http._mcp_apps.pop(STATION, None)  # noqa: SLF001 -- restore, not reach-in
    else:
        mcp_http.register_station_mcp_app(STATION, previous)


def _dispatch(scope: dict[str, Any]) -> list[dict[str, Any]]:
    """Drive the route and return the ASGI messages the gate produced."""
    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    async def _go() -> bool:
        return await dispatch_station_mcp(scope, _receive, send)

    asyncio.run(_go())
    return sent


def _status(sent: list[dict[str, Any]]) -> int | None:
    for message in sent:
        if message["type"] == "http.response.start":
            return int(message["status"])
    return None


def _header(sent: list[dict[str, Any]], name: bytes) -> bytes | None:
    for message in sent:
        if message["type"] != "http.response.start":
            continue
        for key, value in message["headers"]:
            if key.lower() == name:
                return value
    return None


def _body(sent: list[dict[str, Any]]) -> dict[str, Any]:
    raw = b"".join(
        message.get("body", b"")
        for message in sent
        if message["type"] == "http.response.body"
    )
    return json.loads(raw) if raw else {}


@pytest.fixture
def _one_per_minute(settings) -> None:
    """A bucket of one, so the second call in a test is the refused one."""
    settings.MCP_RATE_LIMIT_PER_MINUTE = 1
    settings.MCP_RATE_LIMIT_BURST = 1
    settings.SUPERVISOR_START_RATE_PER_MINUTE = 1
    settings.SUPERVISOR_START_BURST = 1


class _DeadCache:
    """django_redis with IGNORE_EXCEPTIONS: a failure comes back as ``None``.

    This is the shape that makes a naive limiter fail OPEN — ``get`` answers
    ``None``, a naive reader calls that "no bucket yet", and every request is
    then a fresh full bucket. Reproduced here rather than described.
    """

    def get(self, _key: str, _default: Any = None) -> Any:
        return None

    def set(self, *args: Any, **kwargs: Any) -> None:
        return None

    def delete(self, *args: Any, **kwargs: Any) -> None:
        return None


class _RaisingCache:
    """A backend configured to raise instead of swallow."""

    def get(self, *args: Any, **kwargs: Any) -> Any:
        msg = "connection refused"
        raise ConnectionError(msg)

    def set(self, *args: Any, **kwargs: Any) -> None:
        msg = "connection refused"
        raise ConnectionError(msg)


class _StubControl:
    """Celery's control face, reduced to what revoke uses."""

    def __init__(self) -> None:
        self.revoked: list[list[str]] = []

    def revoke(self, task_ids: list[str], **_kwargs: Any) -> None:
        self.revoked.append(list(task_ids))


# ---------------------------------------------------------------------------
# AC 1 -- the MCP route throttles per subject
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_one_per_minute")
def test_over_rate_subject_gets_429_with_retry_after_and_others_do_not(
    caplog,
) -> None:
    """AC: over the rate → 429 + `Retry-After` + a structured log; another
    subject calling the same route in the same window is untouched.
    """
    agent = _assertion(AGENT)
    bystander = _assertion(OTHER_AGENT)

    first = _dispatch(_scope(agent))
    with caplog.at_level(logging.WARNING):
        refused = _dispatch(_scope(agent))
    unaffected = _dispatch(_scope(bystander))

    assert _status(first) != HTTPStatus.TOO_MANY_REQUESTS
    assert _status(refused) == HTTPStatus.TOO_MANY_REQUESTS
    retry_after = _header(refused, b"retry-after")
    assert retry_after is not None
    assert int(retry_after) >= 1
    assert _body(refused)["error"] == "rate limited"
    assert _body(refused)["retry_after"] == int(retry_after)
    assert _status(unaffected) != HTTPStatus.TOO_MANY_REQUESTS

    events = {record.__dict__.get("event") for record in caplog.records}
    assert "ratelimit.refused" in events
    assert "mcp.transport_refused" in events
    refusal = next(
        record
        for record in caplog.records
        if record.__dict__.get("event") == "ratelimit.refused"
    )
    assert refusal.__dict__["sub"] == AGENT
    assert refusal.__dict__["scope"] == MCP_SCOPE


def test_an_unauthorized_call_is_never_charged_to_the_subject_it_claims(
    settings,
) -> None:
    """A caller that fails the gate must not be able to spend someone else's
    allowance -- which is exactly what charging before verifying would allow.
    """
    settings.MCP_RATE_LIMIT_PER_MINUTE = 1
    settings.MCP_RATE_LIMIT_BURST = 1
    forged = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJhZ2VudC00Mi0yIn0.not-a-signature"

    refused = _dispatch(_scope(forged))
    allowed = _dispatch(_scope(_assertion(AGENT)))

    assert _status(refused) == HTTPStatus.UNAUTHORIZED
    assert _status(allowed) != HTTPStatus.TOO_MANY_REQUESTS


def test_the_route_fails_closed_when_the_cache_is_down(monkeypatch, caplog) -> None:
    """AC (Never): a limiter that fails open when the cache is down is not a
    limiter. Refuse, with a loud log.
    """
    monkeypatch.setattr(rate_limit, "limiter_cache", _DeadCache)

    with caplog.at_level(logging.ERROR):
        sent = _dispatch(_scope(_assertion(AGENT)))

    assert _status(sent) == HTTPStatus.TOO_MANY_REQUESTS
    assert _header(sent, b"retry-after") is not None
    errors = [
        record
        for record in caplog.records
        if record.__dict__.get("event") == "ratelimit.cache_unavailable"
    ]
    assert errors, "a limiter that cannot count must say so"
    assert errors[0].levelno == logging.ERROR


@pytest.mark.parametrize(
    "store",
    [_DeadCache(), _RaisingCache()],
    ids=["swallowed-into-none", "raises"],
)
def test_consume_never_allows_when_the_store_does_not_answer(store: Any) -> None:
    """Both backend shapes -- swallowed into None, or raised -- are refusals.

    The `None` case is the subtle one: it is indistinguishable from a cache
    miss unless the read passes a non-`None` default, which is why it does.
    """
    decision = consume(MCP_SCOPE, AGENT, cache=store)

    assert decision.allowed is False
    assert decision.reason == rate_limit.REASON_CACHE_UNAVAILABLE
    assert decision.retry_after > 0


def test_a_corrupt_negative_bucket_cannot_lock_a_subject_out() -> None:
    """A negative stored reading would flow into `ceil((1 - tokens) / rate)` and
    advertise an unbounded `Retry-After`. The store is shared and evictable, so
    the bucket clamps what it reads rather than trusting it.
    """
    cache = caches[rate_limit.CACHE_ALIAS]
    bucket = Bucket(scope=MCP_SCOPE, rate_per_minute=60, burst=2)
    subject = "poisoned-subject"
    cache.set(
        rate_limit.bucket_key(MCP_SCOPE, subject),
        {"tokens": -1_000_000.0, "at": 1_000_000.0},
        timeout=None,
    )

    decision = consume(
        MCP_SCOPE,
        subject,
        bucket=bucket,
        cache=cache,
        now=1_000_000.0,
    )

    assert decision.allowed is False
    assert 1 <= decision.retry_after <= rate_limit.MAX_RETRY_AFTER_SECONDS
    assert decision.remaining >= 0.0
    # ...and a stored value ABOVE burst cannot mint free allowance either.
    cache.set(
        rate_limit.bucket_key(MCP_SCOPE, subject),
        {"tokens": 10_000.0, "at": 1_000_000.0},
        timeout=None,
    )
    inflated = consume(
        MCP_SCOPE,
        subject,
        bucket=bucket,
        cache=cache,
        now=1_000_000.0,
    )
    assert inflated.remaining <= bucket.burst


def test_a_token_bucket_refills_over_time() -> None:
    """It is a bucket, not a fixed window: a caller that waits gets tokens back
    without waiting for a window boundary.
    """
    cache = caches[rate_limit.CACHE_ALIAS]
    bucket = Bucket(scope=MCP_SCOPE, rate_per_minute=60, burst=2)
    subject = "refill-subject"
    rate_limit.reset(MCP_SCOPE, subject, cache=cache)
    start = 1_000_000.0

    first = consume(MCP_SCOPE, subject, bucket=bucket, cache=cache, now=start)
    second = consume(MCP_SCOPE, subject, bucket=bucket, cache=cache, now=start)
    third = consume(MCP_SCOPE, subject, bucket=bucket, cache=cache, now=start)
    later = consume(
        MCP_SCOPE,
        subject,
        bucket=bucket,
        cache=cache,
        now=start + 1.0,
    )

    assert [first.allowed, second.allowed, third.allowed] == [True, True, False]
    assert third.retry_after >= 1
    assert later.allowed is True, "a second of refill at 60/min is one token"


def test_limiter_state_lives_on_redis_cache_not_the_broker() -> None:
    """AD-10: the alias the limiter names is the cache one in the deployed
    composition. Putting buckets on the `noeviction` broker would make the
    limiter a writer to the instance whose exhaustion it exists to prevent.
    """
    cache_url = "redis://redis-cache:6379/1"
    broker_url = "redis://redis-broker:6379/0"
    aliases = django_cache_aliases(cache_url)

    assert rate_limit.CACHE_ALIAS in aliases
    assert aliases[rate_limit.CACHE_ALIAS]["LOCATION"] == cache_url
    assert channel_layers_for_broker(broker_url)["default"]["CONFIG"]["hosts"] == [
        broker_url,
    ]


def _env_int_settings(text: str) -> set[str]:
    """Settings assigned from ``env.int("<same name>", default=...)``.

    Read from the source rather than from ``settings``, and required to be
    self-named, so a knob that exists only as a hardcoded literal -- or one
    whose environment variable silently drifts from its setting name -- fails
    here instead of at 3am.
    """
    names: set[str] = set()
    for node in ast.walk(ast.parse(text)):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        func = node.value.func
        if not (isinstance(func, ast.Attribute) and func.attr == "int"):
            continue
        args = node.value.args
        if not args or not isinstance(args[0], ast.Constant):
            continue
        targets = {t.id for t in node.targets if isinstance(t, ast.Name)}
        names |= {name for name in targets if name == args[0].value}
    return names


def test_every_bound_is_a_documented_setting(settings) -> None:
    """"Numbers are settings with documented defaults" -- and each default is
    a positive integer, so a knob cannot ship as an unusable zero.
    """
    declared = _env_int_settings(BASE_SETTINGS_PATH.read_text(encoding="utf-8"))
    for name in (
        "MCP_RATE_LIMIT_PER_MINUTE",
        "MCP_RATE_LIMIT_BURST",
        "SUPERVISOR_START_RATE_PER_MINUTE",
        "SUPERVISOR_START_BURST",
        "MAX_RUNNING_PER_SUB",
        "MAX_QUEUE_DEPTH_PER_STATION",
        "RUN_STATE_RETENTION_DAYS",
        "RUN_STATE_MAX_ROWS",
        "RUN_STATE_PRUNE_BATCH",
        "RUN_STATE_PRUNE_INTERVAL_SECONDS",
    ):
        assert name in declared, f"{name} is not an env-overridable setting"
        assert getattr(settings, name) > 0, name


# ---------------------------------------------------------------------------
# AC 2 / AC 3 -- supervisor start ceilings
# ---------------------------------------------------------------------------


def _live_run(*, station: str = STATION, subject: str = AGENT) -> RunState:
    now = timezone.now()
    return RunState.objects.create(
        status=RunState.Status.RUNNING,
        station=station,
        subject=subject,
        celery_task_id=f"task-{subject}-{now.timestamp()}",
        started_at=now,
        heartbeat_at=now,
    )


@pytest.fixture
def _no_enqueue(monkeypatch) -> None:
    monkeypatch.setattr(
        execute_supervised_run,
        "apply_async",
        lambda *a, **k: None,
    )
    register_runner(STATION, "run_pipeline", lambda payload: dict(payload or {}))


@pytest.mark.django_db
@pytest.mark.usefixtures("_no_enqueue")
def test_station_queue_ceiling_refuses_with_429_and_writes_no_row(
    settings,
) -> None:
    """AC: at the per-station ceiling, `start` is 429 and NO RunState row is
    written -- the refusal happens before the transaction, so this is a
    property of ordering rather than of a rollback.
    """
    settings.MAX_QUEUE_DEPTH_PER_STATION = 1
    _live_run(subject="someone-else")
    before = RunState.objects.count()

    with pytest.raises(StationQueueFull) as caught:
        publish_start(
            station=STATION,
            assertion=_assertion(AGENT),
            payload={"name": "core"},
        )

    assert RunState.objects.count() == before
    assert McpHandle.objects.count() == 0
    assert caught.value.status == HTTPStatus.TOO_MANY_REQUESTS
    assert caught.value.retry_after > 0
    assert caught.value.headers()["Retry-After"] == str(caught.value.retry_after)
    assert caught.value.payload()["station"] == STATION


@pytest.mark.django_db
@pytest.mark.usefixtures("_no_enqueue")
def test_max_running_per_sub_refuses_with_409_and_the_live_run_ids(
    settings,
) -> None:
    """AC: at MAX_RUNNING_PER_SUB, `start` is 409 naming the live run ids --
    409 rather than 429 because the conflict is the caller's own runs, and the
    ids are what it needs to wait on or revoke them.
    """
    settings.MAX_RUNNING_PER_SUB = 2
    settings.MAX_QUEUE_DEPTH_PER_STATION = 100
    mine = [_live_run(), _live_run()]
    _live_run(subject=OTHER_AGENT)
    before = RunState.objects.count()

    with pytest.raises(TooManyRunningForSubject) as caught:
        publish_start(
            station=STATION,
            assertion=_assertion(AGENT),
            payload={"name": "core"},
        )

    assert RunState.objects.count() == before
    assert caught.value.status == HTTPStatus.CONFLICT
    assert set(caught.value.payload()["run_ids"]) == {str(run.id) for run in mine}
    assert caught.value.payload()["limit"] == 2  # noqa: PLR2004 -- the setting above


@pytest.mark.django_db
@pytest.mark.usefixtures("_no_enqueue")
def test_another_subject_still_starts_at_the_per_sub_ceiling(settings) -> None:
    """The per-subject ceiling must not be a per-station one in disguise."""
    settings.MAX_RUNNING_PER_SUB = 1
    settings.MAX_QUEUE_DEPTH_PER_STATION = 100
    _live_run(subject=AGENT)

    handle = publish_start(
        station=STATION,
        assertion=_assertion(OTHER_AGENT),
        payload={"name": "core"},
    )

    assert McpHandle.objects.get(handle=handle).run.subject == OTHER_AGENT


@pytest.mark.django_db
@pytest.mark.usefixtures("_no_enqueue", "_one_per_minute")
def test_start_is_rate_limited_per_subject_before_any_row_exists() -> None:
    """AC: the `start` bucket is a second, narrower gate -- a subject under
    both ceilings is still throttled, and the refusal costs no row.
    """
    publish_start(
        station=STATION,
        assertion=_assertion(AGENT),
        payload={"name": "core"},
    )
    after_first = RunState.objects.count()

    with pytest.raises(SubjectRateLimited) as caught:
        publish_start(
            station=STATION,
            assertion=_assertion(AGENT),
            payload={"name": "core"},
        )

    assert RunState.objects.count() == after_first
    assert caught.value.status == HTTPStatus.TOO_MANY_REQUESTS
    assert caught.value.retry_after > 0
    # ...and a different subject is unaffected by it.
    publish_start(
        station=STATION,
        assertion=_assertion(OTHER_AGENT),
        payload={"name": "core"},
    )
    assert RunState.objects.count() == after_first + 1


# ---------------------------------------------------------------------------
# AC 4 -- revoke by subject, and the `sub` tag that makes it possible
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_every_enqueue_carries_the_subject_and_a_pre_minted_task_id(
    monkeypatch,
) -> None:
    """The row must name the task BEFORE the task is sent, or a queued task is
    unrevocable; the message carries `sub` so the broker is attributable too.
    """
    published: list[dict[str, Any]] = []

    def capture(*_args: Any, **kwargs: Any) -> None:
        published.append(kwargs)

    monkeypatch.setattr(execute_supervised_run, "apply_async", capture)
    register_runner(STATION, "run_pipeline", lambda payload: dict(payload or {}))

    handle = publish_start(
        station=STATION,
        assertion=_assertion(AGENT),
        payload={"name": "core"},
    )

    run = McpHandle.objects.select_related("run").get(handle=handle).run
    assert published[0]["headers"] == {SUBJECT_HEADER: AGENT}
    assert published[0]["task_id"] == run.celery_task_id
    assert run.celery_task_id
    assert run.subject == AGENT


@pytest.mark.django_db
def test_revoke_by_subject_revokes_queued_tasks_and_cancels_its_runs() -> None:
    """AC: one command revokes a subject's queued tasks and marks its RUNNING
    rows CANCELLED -- and touches nobody else's.
    """
    mine = [_live_run(), _live_run()]
    theirs = _live_run(subject=OTHER_AGENT)
    control = _StubControl()

    report = revoke_subject(AGENT, control=control)

    assert report["ok"] is True
    assert report["cancelled_runs"] == 2  # noqa: PLR2004 -- the two rows above
    assert set(control.revoked[0]) == {run.celery_task_id for run in mine}
    for run in mine:
        run.refresh_from_db()
        assert run.status == RunState.Status.CANCELLED
        assert run.completed_at is not None
        assert run.result["cancelled"] is True
    theirs.refresh_from_db()
    assert theirs.status == RunState.Status.RUNNING


@pytest.mark.django_db
def test_a_finishing_worker_cannot_overwrite_a_revoked_run() -> None:
    """`control.revoke` cannot recall a task a worker already started, so the
    task finishes and calls `complete_run`. An unconditional update would then
    replace the operator's CANCELLED with `succeeded` — destroying the record
    AC 4 just created, and re-conflating the two states CANCELLED exists to
    keep apart. Terminal wins.
    """
    run = _live_run()
    revoke_subject(AGENT, control=_StubControl())
    register_runner(STATION, "run_pipeline", lambda payload: dict(payload or {}))

    execute_supervised_run(str(run.id), STATION, "run_pipeline", {"name": "core"})

    run.refresh_from_db()
    assert run.status == RunState.Status.CANCELLED
    assert run.result["cancelled"] is True


@pytest.mark.django_db
def test_revoke_terminates_rather_than_only_dequeuing() -> None:
    """A queued-only revoke leaves an already-running task to finish; the
    terminate flag is what makes `revoke` mean "stop", not "do not start".
    """

    class _Recording:
        def __init__(self) -> None:
            self.kwargs: dict[str, Any] = {}

        def revoke(self, _task_ids: list[str], **kwargs: Any) -> None:
            self.kwargs = kwargs

    _live_run()
    control = _Recording()

    revoke_subject(AGENT, control=control)

    assert control.kwargs.get("terminate") is True


@pytest.mark.django_db
def test_revoke_refuses_an_empty_subject() -> None:
    """Migration 0004 defaults `subject` to '' on every pre-existing row, so an
    empty subject would cancel the entire legacy estate. The guard is in the
    single writer (AD-12), not in one of its callers — proven by calling the
    writer and the management command, neither of which is `RevokeDuty`.
    """
    legacy = RunState.objects.create(
        status=RunState.Status.RUNNING,
        station=STATION,
        started_at=timezone.now(),
    )
    assert legacy.subject == ""

    for empty in ("", "   "):
        with pytest.raises(ValueError, match="non-empty subject"):
            revoke_subject(empty, control=_StubControl())
    with pytest.raises(CommandError):
        call_command("revoke_subject", sub="", control=_StubControl())

    legacy.refresh_from_db()
    assert legacy.status == RunState.Status.RUNNING


@pytest.mark.django_db
def test_a_failed_enqueue_leaves_no_live_row_behind(monkeypatch) -> None:
    """A live row whose task was never published is immortal — retention never
    prunes live rows — so with this story's ceilings in place a broker outage
    would become a permanent lockout for that subject. The row terminalises and
    the caller still learns the enqueue failed.
    """

    def exploding(*_args: Any, **_kwargs: Any) -> None:
        msg = "broker unreachable"
        raise ConnectionError(msg)

    monkeypatch.setattr(execute_supervised_run, "apply_async", exploding)
    register_runner(STATION, "run_pipeline", lambda payload: dict(payload or {}))

    with pytest.raises(ConnectionError):
        publish_start(
            station=STATION,
            assertion=_assertion(AGENT),
            payload={"name": "core"},
        )

    assert live_runs_for_subject(AGENT) == []
    row = RunState.objects.get(subject=AGENT)
    assert row.status == RunState.Status.FAILED
    assert "enqueue failed" in row.result["error"]


@pytest.mark.django_db
def test_revoke_reports_a_failed_broker_instead_of_claiming_success() -> None:
    """A revoke that could not reach the broker is not a revoke. The rows are
    still cancelled (the ledger is the record of fact), but `ok` is False so an
    operator knows a worker may still be holding the task.
    """

    class _Broken:
        def revoke(self, _task_ids: list[str], **_kwargs: Any) -> None:
            msg = "broker unreachable"
            raise ConnectionError(msg)

    _live_run()

    report = revoke_subject(AGENT, control=_Broken())

    assert report["ok"] is False
    assert report["revoked_tasks"] == []
    assert "broker unreachable" in report["revoke_error"]


@pytest.mark.django_db
def test_revoke_subject_management_command_emits_the_report(capsys) -> None:
    """The steward duty shells to this command, so the command is the contract:
    `--json` on stdout, nothing else.
    """
    run = _live_run()
    control = _StubControl()

    call_command("revoke_subject", sub=AGENT, control=control, as_json=True)

    report = json.loads(capsys.readouterr().out)
    assert report["subject"] == AGENT
    assert report["run_ids"] == [str(run.id)]
    assert control.revoked == [[run.celery_task_id]]


@pytest.mark.django_db
def test_a_cancelled_run_leaves_the_live_board() -> None:
    """A revoked run that still showed as live would make `revoke` look inert."""
    from django_pyforge.supervisor import load_board_rows  # noqa: PLC0415

    _live_run()
    revoke_subject(AGENT, control=_StubControl())
    live, timing = load_board_rows()

    assert live == ()
    assert [row["status"] for row in timing] == [RunState.Status.CANCELLED]


# ---------------------------------------------------------------------------
# AC 5 -- retention bounds the table
# ---------------------------------------------------------------------------


def _terminal_run(*, age_days: int, status: str = RunState.Status.SUCCEEDED):
    moment = timezone.now() - timedelta(days=age_days)
    return RunState.objects.create(
        status=status,
        station=STATION,
        subject=AGENT,
        started_at=moment,
        heartbeat_at=moment,
        completed_at=moment,
    )


@pytest.mark.django_db
def test_retention_prunes_aged_rows_and_leaves_live_ones(settings) -> None:
    """AC: rows older than the retention window are pruned. A RUNNING row is
    never pruned however old -- deleting it would orphan a working task.
    """
    settings.RUN_STATE_RETENTION_DAYS = 7
    settings.RUN_STATE_MAX_ROWS = 1000
    old = _terminal_run(age_days=30)
    recent = _terminal_run(age_days=1)
    stale_live = _live_run()
    RunState.objects.filter(pk=stale_live.pk).update(
        started_at=timezone.now() - timedelta(days=90),
    )

    report = prune_run_state()

    assert report["aged_out"] == 1
    assert not RunState.objects.filter(pk=old.pk).exists()
    assert RunState.objects.filter(pk=recent.pk).exists()
    assert RunState.objects.filter(pk=stale_live.pk).exists()


@pytest.mark.django_db
def test_retention_bounds_the_count_even_inside_the_window(settings) -> None:
    """AC: "the count is bounded". Age alone bounds nothing -- a burst inside
    the window is exactly the shape that fills the table -- so the cap is a
    second pass, and it is the one that makes the guarantee.
    """
    settings.RUN_STATE_RETENTION_DAYS = 365
    settings.RUN_STATE_MAX_ROWS = 3
    for _ in range(6):
        _terminal_run(age_days=0)

    report = prune_run_state()

    assert RunState.objects.count() == 3  # noqa: PLR2004 -- the configured cap
    assert report["over_cap"] == 3  # noqa: PLR2004 -- six minus the cap
    assert report["remaining"] == 3  # noqa: PLR2004


@pytest.mark.django_db
def test_retention_drops_expired_handles_and_counts_runs_not_cascades(
    settings,
) -> None:
    """`QuerySet.delete()` reports a grand total across cascaded models, so
    reading element 0 would double-count. BOTH counts go through the same
    per-model read: the aged run below carries two handles, so a grand-total
    read reports 3 aged runs and 1 handle instead of 1 and 1.
    """
    settings.RUN_STATE_RETENTION_DAYS = 7
    settings.RUN_STATE_MAX_ROWS = 1000
    expired = timezone.now() - timedelta(hours=1)
    old = _terminal_run(age_days=30)
    for token in ("x", "z"):
        McpHandle.objects.create(
            handle=token * 40,
            run=old,
            expires_at=expired,
            subject=AGENT,
        )
    live = _live_run()
    McpHandle.objects.create(
        handle="y" * 40,
        run=live,
        expires_at=expired,
        subject=AGENT,
    )

    report = prune_run_state()

    assert report["aged_out"] == 1, "cascaded handles must not be counted as runs"
    assert report["expired_handles"] == 1, "cascaded handles are not this pass's"
    assert McpHandle.objects.count() == 0
    assert RunState.objects.filter(pk=live.pk).exists()


@pytest.mark.django_db
def test_one_sweep_is_bounded_and_says_so(settings) -> None:
    """AC 5's guarantee must be reachable. The first sweep after this story
    deploys runs over a table that has never been pruned, and one unbounded
    DELETE across it can exceed CELERY_TASK_SOFT_TIME_LIMIT and never complete
    — a retention task that cannot finish bounds nothing. So a sweep is capped,
    reports `truncated`, and the schedule catches up.
    """
    settings.RUN_STATE_RETENTION_DAYS = 7
    settings.RUN_STATE_MAX_ROWS = 1000
    settings.RUN_STATE_PRUNE_BATCH = 2
    for _ in range(5):
        _terminal_run(age_days=30)

    first = prune_run_state()

    assert first["aged_out"] == 2, "the sweep must honour its batch limit"  # noqa: PLR2004
    assert first["truncated"] is True
    assert first["batch_limit"] == 2  # noqa: PLR2004
    assert RunState.objects.count() == 3  # noqa: PLR2004

    second = prune_run_state()
    third = prune_run_state()

    assert second["aged_out"] == 2  # noqa: PLR2004
    assert third["aged_out"] == 1
    assert third["truncated"] is False
    assert RunState.objects.count() == 0


@pytest.mark.django_db
def test_the_cap_pass_spends_what_the_age_pass_left(settings) -> None:
    """One sweep's TOTAL work is bounded by the batch, not by twice it — the
    two passes share one budget.
    """
    settings.RUN_STATE_RETENTION_DAYS = 7
    settings.RUN_STATE_MAX_ROWS = 1
    settings.RUN_STATE_PRUNE_BATCH = 3
    for _ in range(2):
        _terminal_run(age_days=30)
    for _ in range(4):
        _terminal_run(age_days=0)

    report = prune_run_state()

    assert report["aged_out"] == 2  # noqa: PLR2004 -- both aged rows fit the budget
    assert report["over_cap"] == 1, "only the leftover budget is spent"
    assert report["truncated"] is True


@pytest.mark.django_db
def test_the_retention_task_is_scheduled_and_runnable_by_hand(
    settings,
    capsys,
) -> None:
    """A retention function nothing calls bounds nothing.

    Two runners: the schedule declares the cadence with the code (Story 42.4
    deploys the `beat` Deployment that ticks it), and the management command
    is what an operator can run without waiting for the next tick.
    """
    entry = settings.CELERY_BEAT_SCHEDULE["prune-run-state"]

    assert entry["task"] == "django_pyforge.tasks.prune_run_state_task"
    assert entry["schedule"] > 0

    from django_pyforge.tasks import prune_run_state_task  # noqa: PLC0415

    settings.RUN_STATE_RETENTION_DAYS = 1
    _terminal_run(age_days=9999)
    assert prune_run_state_task()["aged_out"] == 1

    _terminal_run(age_days=9999)
    call_command("prune_run_state", as_json=True)
    assert json.loads(capsys.readouterr().out)["aged_out"] == 1


@pytest.mark.django_db
def test_start_scope_and_mcp_scope_are_separate_buckets(settings) -> None:
    """Spending the MCP allowance must not spend the `start` allowance: they
    are different costs and the keys must not collide.
    """
    settings.MCP_RATE_LIMIT_PER_MINUTE = 1
    settings.MCP_RATE_LIMIT_BURST = 1
    settings.SUPERVISOR_START_RATE_PER_MINUTE = 1
    settings.SUPERVISOR_START_BURST = 1

    assert consume(MCP_SCOPE, AGENT).allowed is True
    assert consume(MCP_SCOPE, AGENT).allowed is False
    assert consume(START_SCOPE, AGENT).allowed is True
