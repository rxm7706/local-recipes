"""Story 11.1 -- exercises config.asgi.application's Langflow routing rules.

Mirrors test_asgi_seam.py's pattern: talks to the composed ASGI callable
itself (not Django's test Client), so a regression in the dispatch order
(AD-4) is caught here rather than only by manual inspection. Covers the 5
I/O & Edge-Case Matrix rows from spec-11-1: `/api/v1/*` and bare `/health`
forward unchanged, `/langflow/*` forwards prefix-stripped, `/api/health`
stays on the platform's own stub, and everything else still falls through
to Django.

Requires the `langflow` package (the `python-agent-platform` conda env, not
the pixi env `platform-ci-test` the CI `test` job installs -- Langflow
is factory-sourced conda-only, CAP-5) plus a real, reachable `DATABASE_URL`/
`REDIS_URL`: `langflow_integration.asgi` builds Langflow's app at import
time, and `create_app()` constructs its settings service (validating
`LANGFLOW_DATABASE_URL`) even though these particular routes never open a
DB connection. `pytest.importorskip` keeps this file a clean skip rather
than a collection error wherever `langflow` isn't installed.
"""

from __future__ import annotations

import asyncio
from http import HTTPStatus

import pytest

pytest.importorskip("langflow")

from httpx import ASGITransport
from httpx import AsyncClient

import config.asgi as asgi_module
from config.asgi import application


def _get(path: str):
    async def _call():
        transport = ASGITransport(app=application)
        base_url = "http://testserver"
        async with AsyncClient(transport=transport, base_url=base_url) as client:
            return await client.get(path)

    return asyncio.run(_call())


def test_bare_api_v1_does_not_forward_to_langflow():
    # Langflow's own `/api/v1/flows` route (trailing-slash required) issues
    # Starlette's default redirect — a response shape the platform's own
    # FastAPI stub could never produce. Story 43.2 moved Langflow off bare
    # `/api/v1/*`; only `/langflow/api/v1/...` still reaches Langflow.
    response = _get("/api/v1/flows")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_bare_health_forwards_to_langflow():
    response = _get("/health")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "ok"}


def test_platform_api_health_unaffected():
    response = _get("/api/health")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "ok"}


def test_langflow_prefixed_path_forwards_with_prefix_stripped():
    # Same redirect proof as the /api/v1/ case, but reached via the
    # /langflow/ alias. `path`/`raw_path` are rewritten to drop /langflow
    # before Langflow's router sees them (a bare unstripped forward would
    # 404 instead: Langflow has no `/langflow/...` route of its own), while
    # `root_path` is extended by /langflow so Langflow's own redirect
    # (built from `scope["root_path"] + scope["path"]`, real Starlette
    # `Mount` semantics) still carries the alias in its Location -- proving
    # the scope rewrite mirrors `Mount`, not just a naive path substitution.
    response = _get("/langflow/api/v1/flows")

    assert response.status_code == HTTPStatus.TEMPORARY_REDIRECT
    assert response.headers["location"] == "http://testserver/langflow/api/v1/flows/"


def test_unknown_non_api_path_falls_through_to_django():
    response = _get("/this-path-does-not-exist")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers["content-type"].startswith("text/html")


def test_lifespan_keeps_langflow_services_live_across_requests():
    """Reproduces + proves the fix for the HIGH bug closed 2026-08-20 (see
    the spec's Spec Change Log): drives `config.asgi.application`'s actual
    `lifespan` scope directly -- send `lifespan.startup`, make two real HTTP
    requests through the full dispatcher to a service-backed Langflow route,
    then send `lifespan.shutdown` -- proving Langflow's DB/cache services
    stay live for the whole session instead of being torn down immediately
    after boot (the old single-shot `_run_lifespan` replay's bug).

    Neither existing test file drove this exact path: `test_api_v1_...`
    above bypasses the lifespan scope entirely (`ASGITransport` never sends
    `lifespan.startup`, so `langflow_integration.asgi`'s module-level
    `create_app()` app object just serves the request unstarted), and
    `langflow_integration/tests.py` drives `langflow_application`'s lifespan
    directly, never through `config.asgi.application`'s own dispatch.

    `/health_check` (unlike bare `/health`, an unconditional no-dependency
    liveness ping) actually queries Postgres and calls the Redis-backed chat
    service, so it fails loudly the way the bug did in production: a torn-
    down `DATABASE_SERVICE` surfaces as a 500, not a false-positive 200.
    """
    from langflow_integration.asgi import _LifespanManager  # noqa: PLC0415

    async def _call():
        async with _LifespanManager(application):
            transport = ASGITransport(app=application)
            base_url = "http://testserver"
            async with AsyncClient(transport=transport, base_url=base_url) as client:
                first = await client.get("/health_check")
                second = await client.get("/health_check")
                return first, second

    first, second = asyncio.run(_call())

    assert first.status_code == HTTPStatus.OK, first.text
    assert first.json()["status"] == "ok"
    # The second call is the actual proof: under the old bug, Langflow's
    # startup-then-shutdown-in-one-call already tore its DB/cache services
    # down before this request ever landed, so both calls would fail.
    assert second.status_code == HTTPStatus.OK, second.text
    assert second.json()["status"] == "ok"


def test_lifespan_startup_failure_rolls_back_already_started_subapp(monkeypatch):
    """Closes a coverage gap named in `config.asgi._dispatch_lifespan`'s own
    docstring: a startup failure on either sub-app is claimed to roll back
    the other sub-app's already-completed startup via the `AsyncExitStack`
    unwind, but nothing exercised that path. Proven here with two fake ASGI
    apps (no real Langflow/Postgres/Redis needed for this one) standing in
    for the platform stub and Langflow: the stub starts fine, Langflow's
    startup fails, and the stub's shutdown must still fire before the
    dispatcher reports `lifespan.startup.failed` to the real server.
    """
    events: list[str] = []

    async def fake_fastapi_app(scope, receive, send):
        assert scope["type"] == "lifespan"
        message = await receive()
        assert message["type"] == "lifespan.startup"
        events.append("fastapi.started")
        await send({"type": "lifespan.startup.complete"})
        message = await receive()
        assert message["type"] == "lifespan.shutdown"
        events.append("fastapi.stopped")
        await send({"type": "lifespan.shutdown.complete"})

    async def failing_langflow_app(scope, receive, send):
        assert scope["type"] == "lifespan"
        message = await receive()
        assert message["type"] == "lifespan.startup"
        events.append("langflow.startup.failed")
        await send({"type": "lifespan.startup.failed", "message": "boom"})

    monkeypatch.setattr(asgi_module, "fastapi_application", fake_fastapi_app)
    monkeypatch.setattr(asgi_module, "langflow_application", failing_langflow_app)

    async def _run():
        receive_queue: asyncio.Queue = asyncio.Queue()
        sent: list[dict] = []

        async def receive():
            return await receive_queue.get()

        async def send(message):
            sent.append(message)

        await receive_queue.put({"type": "lifespan.startup"})
        await asgi_module.application({"type": "lifespan"}, receive, send)
        return sent

    sent = asyncio.run(_run())

    assert events == ["fastapi.started", "langflow.startup.failed", "fastapi.stopped"]
    assert sent[-1]["type"] == "lifespan.startup.failed"
