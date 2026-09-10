"""Story 43.2 — host ASGI dispatch for versioned station APIs (langflow-free).

Runs in ``platform-ci-test`` where ``langflow`` is intentionally absent (CAP-5).
Stubs Langflow at import time so ``config.asgi.application`` can be exercised
without the factory conda package.
"""

from __future__ import annotations

import asyncio
import sys
from http import HTTPStatus
from unittest.mock import MagicMock

# Stub Langflow before langflow_integration.asgi imports it.
_langflow_asgi_app = MagicMock()
_langflow_pkg = MagicMock()
_langflow_pkg.main.create_app.return_value = _langflow_asgi_app
sys.modules.setdefault("langflow", _langflow_pkg)
sys.modules.setdefault("langflow.main", _langflow_pkg.main)

from httpx import ASGITransport  # noqa: E402
from httpx import AsyncClient  # noqa: E402

from config.asgi import application  # noqa: E402


def _get(path: str):
    async def _call():
        transport = ASGITransport(app=application)
        base_url = "http://testserver"
        async with AsyncClient(transport=transport, base_url=base_url) as client:
            return await client.get(path)

    return asyncio.run(_call())


def test_host_dispatches_station_openapi():
    response = _get("/stations/warden/api/v1/openapi.json")

    assert response.status_code == HTTPStatus.OK
    paths = response.json().get("paths", {})
    assert "/stations/warden/api/v1/health" in paths


def test_host_dispatches_station_health():
    response = _get("/stations/warden/api/v1/health")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "ok", "station": "warden"}


def test_bare_api_v1_does_not_reach_langflow_stub():
    response = _get("/api/v1/flows")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {"detail": "Not Found"}
    _langflow_asgi_app.assert_not_called()


def test_unknown_station_api_returns_404_not_500():
    response = _get("/stations/unknown/api/v1/health")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_unknown_station_api_version_returns_404_not_500():
    response = _get("/stations/warden/api/v99/health")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_host_dispatches_herald_openapi():
    response = _get("/stations/herald/api/v1/openapi.json")

    assert response.status_code == HTTPStatus.OK
    paths = response.json().get("paths", {})
    assert "/stations/herald/api/v1/health" in paths


def test_host_dispatches_herald_health():
    response = _get("/stations/herald/api/v1/health")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "ok", "station": "herald"}


def test_legacy_bare_api_herald_webhook_does_not_reach_station_handler():
    async def _call():
        transport = ASGITransport(app=application)
        base_url = "http://testserver"
        async with AsyncClient(transport=transport, base_url=base_url) as client:
            return await client.post(
                "/api/herald/webhooks/on-ship",
                json={"station": "warden"},
            )

    response = asyncio.run(_call())

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {"detail": "Not Found"}


def test_host_dispatches_herald_webhook_unsigned_returns_401(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("HERALD_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("HERALD_WEBHOOK_SECRET", "test-secret")

    async def _call():
        transport = ASGITransport(app=application)
        base_url = "http://testserver"
        async with AsyncClient(transport=transport, base_url=base_url) as client:
            return await client.post(
                "/stations/herald/api/v1/webhooks/on-ship",
                json={"station": "warden"},
            )

    response = asyncio.run(_call())

    assert response.status_code == HTTPStatus.UNAUTHORIZED
