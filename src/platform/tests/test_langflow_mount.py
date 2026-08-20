"""Story 11.1 -- exercises config.asgi.application's Langflow routing rules.

Mirrors test_asgi_seam.py's pattern: talks to the composed ASGI callable
itself (not Django's test Client), so a regression in the dispatch order
(AD-4) is caught here rather than only by manual inspection. Covers the 5
I/O & Edge-Case Matrix rows from spec-11-1: `/api/v1/*` and bare `/health`
forward unchanged, `/langflow/*` forwards prefix-stripped, `/api/health`
stays on the platform's own stub, and everything else still falls through
to Django.

Requires the `langflow` package (the `python-agent-platform` conda env, not
the pip-only `requirements/local.txt` the CI `test` job installs -- Langflow
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

from config.asgi import application


def _get(path: str):
    async def _call():
        transport = ASGITransport(app=application)
        base_url = "http://testserver"
        async with AsyncClient(transport=transport, base_url=base_url) as client:
            return await client.get(path)

    return asyncio.run(_call())


def test_api_v1_forwards_to_langflow_unchanged():
    # Langflow's own `/api/v1/flows` route (trailing-slash required) issues
    # Starlette's default redirect -- a real Langflow-specific response
    # shape the platform's own FastAPI stub (only `/api/health`) could never
    # produce, so this proves the request reached Langflow's app, not just
    # "some" app.
    response = _get("/api/v1/flows")

    assert response.status_code == HTTPStatus.TEMPORARY_REDIRECT
    assert response.headers["location"] == "http://testserver/api/v1/flows/"


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
    # /langflow/ alias -- the Location header carries no /langflow segment,
    # proving the scope was actually rewritten before Langflow's router saw
    # it (a bare unstripped forward would 404 instead: Langflow has no
    # `/langflow/...` route of its own).
    response = _get("/langflow/api/v1/flows")

    assert response.status_code == HTTPStatus.TEMPORARY_REDIRECT
    assert response.headers["location"] == "http://testserver/api/v1/flows/"


def test_unknown_non_api_path_falls_through_to_django():
    response = _get("/this-path-does-not-exist")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers["content-type"].startswith("text/html")
