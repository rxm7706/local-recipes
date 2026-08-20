"""Story 10.1 -- exercises config.asgi.application's routing seam directly.

Talks to the composed ASGI callable itself (not Django's test Client, which
would bypass the seam entirely), so a regression in the `/api/` routing
predicate is caught here rather than only by manual inspection.
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


def test_api_health_reaches_fastapi_not_django():
    response = _get("/api/health")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "ok"}


def test_unknown_api_path_gets_fastapis_404_not_djangos():
    response = _get("/api/this-does-not-exist")

    assert response.status_code == HTTPStatus.NOT_FOUND
    # FastAPI/Starlette's default 404 is a JSON body with a "detail" key;
    # Django's is an HTML page. This is what actually proves the seam
    # routed the request to FastAPI rather than falling through to Django.
    assert response.json() == {"detail": "Not Found"}


def test_unknown_non_api_path_falls_through_to_django():
    response = _get("/this-path-does-not-exist")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers["content-type"].startswith("text/html")
