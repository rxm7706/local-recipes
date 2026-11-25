"""spec-mcp-era-isolation slice 1: mcp-host proxy and identity face."""

from __future__ import annotations

import asyncio
import os
import sys
from http import HTTPStatus
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django_pyforge.assertion.crypto import mint_assertion
from django_pyforge.mcp_dual_era import SUPPORTED_MCP_REVISIONS
from django_pyforge.mcp_dual_era import UNSUPPORTED_PROTOCOL_VERSION
from django_pyforge.mcp_http import dispatch_station_mcp
from django_pyforge.mcp_http import sidecar_base_url
from starlette.testclient import TestClient

os.environ.setdefault("MCP_HOST_STATIONS", "atlas")
_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLATFORM_ROOT))
import mcp_host.app as mcp_host_app_module  # noqa: E402
from mcp_host.app import app as mcp_host_app  # noqa: E402


def _tools_list() -> dict:
    return {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}


def _initialize(revision: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": revision,
            "capabilities": {},
            "clientInfo": {"name": "fixture-client", "version": "0"},
        },
    }


def _bearer(station: str = "atlas") -> dict[str, str]:
    """The header the host forwards: the assertion it verified for ``station``."""
    assertion = mint_assertion(
        sub="agent-sidecar", roles=[f"pyforge:station:{station}"], station=station
    )
    return {"authorization": f"Bearer {assertion}"}


def test_sidecar_base_url_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_HOST_SIDECAR_BASE_URL", raising=False)
    assert sidecar_base_url() is None


def test_sidecar_base_url_strips_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_HOST_SIDECAR_BASE_URL", "http://mcp-host:8090/")
    assert sidecar_base_url() == "http://mcp-host:8090"


@pytest.fixture(scope="module")
def mcp_client():
    with TestClient(mcp_host_app) as client:
        yield client


def test_mcp_host_health(mcp_client: TestClient) -> None:
    response = mcp_client.get("/health")
    assert response.status_code == HTTPStatus.OK
    assert response.json()["status"] == "ok"


def test_mcp_host_initialize_echoes_handshake(mcp_client: TestClient) -> None:
    response = mcp_client.post(
        "/stations/atlas/mcp",
        json=_initialize("2025-06-18"),
        headers={
            "accept": "application/json, text/event-stream",
            "content-type": "application/json",
            **_bearer(),
        },
    )
    assert response.status_code == HTTPStatus.OK
    result = response.json().get("result") or {}
    assert result.get("protocolVersion") == "2025-06-18"


def test_mcp_host_refuses_a_call_with_no_assertion(mcp_client: TestClient) -> None:
    """Steward Story 133.4: the sidecar verifies the assertion itself.

    The network policy was the only thing between the namespace and a
    station's tools; a call that reaches the port without an assertion is
    refused here too.
    """
    for body in (_initialize("2025-06-18"), _tools_list()):
        response = mcp_client.post(
            "/stations/atlas/mcp",
            json=body,
            headers={
                "accept": "application/json, text/event-stream",
                "content-type": "application/json",
            },
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json() == {"error": "assertion required"}


def test_mcp_host_refuses_an_assertion_minted_for_another_station(
    mcp_client: TestClient,
) -> None:
    """A call outside the caller's station scope: 403, never routed."""
    response = mcp_client.post(
        "/stations/atlas/mcp",
        json=_tools_list(),
        headers={
            "accept": "application/json, text/event-stream",
            "content-type": "application/json",
            **_bearer("steward"),
        },
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {"error": "wrong audience"}


def test_mcp_host_refuses_when_no_verifier_key_resolves(
    mcp_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No public key is a 503, never a pass."""
    headers = {"content-type": "application/json", **_bearer()}
    monkeypatch.setattr("django_pyforge.mcp_auth.resolve_public_pem", lambda: "")
    response = mcp_client.post(
        "/stations/atlas/mcp", json=_tools_list(), headers=headers
    )
    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE


def test_mcp_host_modern_header_accepted(mcp_client: TestClient) -> None:
    response = mcp_client.post(
        "/stations/atlas/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        },
        headers={
            "accept": "application/json, text/event-stream",
            "content-type": "application/json",
            "mcp-protocol-version": "2026-07-28",
            **_bearer(),
        },
    )
    assert response.status_code < HTTPStatus.INTERNAL_SERVER_ERROR
    body = response.json()
    assert (
        "error" not in body or body["error"].get("code") != UNSUPPORTED_PROTOCOL_VERSION
    )


def test_mcp_host_unsupported_revision(mcp_client: TestClient) -> None:
    response = mcp_client.post(
        "/stations/atlas/mcp",
        json=_initialize("2099-01-01"),
        headers={"content-type": "application/json", **_bearer()},
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    error = response.json()["error"]
    assert error["code"] == UNSUPPORTED_PROTOCOL_VERSION
    assert list(error["data"]["supported"]) == list(SUPPORTED_MCP_REVISIONS)


def test_mcp_host_get_is_405(mcp_client: TestClient) -> None:
    response = mcp_client.get("/stations/atlas/mcp")
    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response.headers.get("allow") == "POST"


def _atlas_scope(assertion: str) -> dict:
    """Story 42.1: the proxy path is behind the transport gate, so a dispatch
    fixture now carries the assertion it verifies before it proxies.
    """
    return {
        "type": "http",
        "path": "/stations/atlas/mcp",
        "method": "POST",
        "headers": [
            (b"content-type", b"application/json"),
            (b"authorization", f"Bearer {assertion}".encode("latin-1")),
        ],
    }


def test_dispatch_proxies_when_url_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_HOST_SIDECAR_BASE_URL", "http://mcp-host:8090")
    assertion = mint_assertion(
        sub="agent-sidecar", roles=["pyforge:station:atlas"], station="atlas"
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}

    async def _aiter_bytes():
        yield b'{"jsonrpc":"2.0","id":1,"result":{"ok":true}}'

    mock_response.aiter_bytes = _aiter_bytes

    class _StreamContext:
        async def __aenter__(self):
            return mock_response

        async def __aexit__(self, *args):
            return None

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def stream(self, *args, **kwargs):
            return _StreamContext()

    sent: list[dict] = []

    async def receive():
        return {"type": "http.request", "body": b"{}", "more_body": False}

    async def send(message):
        sent.append(message)

    async def _run() -> bool:
        with patch("httpx.AsyncClient", return_value=_Client()):
            return await dispatch_station_mcp(_atlas_scope(assertion), receive, send)

    assert asyncio.run(_run()) is True
    start = next(m for m in sent if m["type"] == "http.response.start")
    assert start["status"] == 200
    body = b"".join(
        m.get("body", b"") for m in sent if m["type"] == "http.response.body"
    )
    assert body == b'{"jsonrpc":"2.0","id":1,"result":{"ok":true}}'


def test_dispatch_502_when_sidecar_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_HOST_SIDECAR_BASE_URL", "http://127.0.0.1:1")
    assertion = mint_assertion(
        sub="agent-sidecar", roles=["pyforge:station:atlas"], station="atlas"
    )
    sent: list[dict] = []

    async def receive():
        return {"type": "http.request", "body": b"{}", "more_body": False}

    async def send(message):
        sent.append(message)

    async def _run() -> bool:
        return await dispatch_station_mcp(_atlas_scope(assertion), receive, send)

    assert asyncio.run(_run()) is True
    start = next(m for m in sent if m["type"] == "http.response.start")
    assert start["status"] == HTTPStatus.BAD_GATEWAY


def test_dispatch_does_not_import_mcpserver_when_proxying() -> None:
    source = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "shared"
        / "packages"
        / "django-pyforge"
        / "src"
        / "django_pyforge"
        / "mcp_http.py"
    ).read_text(encoding="utf-8")
    assert "MCP_HOST_SIDECAR_BASE_URL" in source
    assert "proxy_station_mcp" in source
    assert "from mcp.server.mcpserver import MCPServer" not in source


def test_real_station_apps_falls_back_empty_when_django_setup_fails() -> None:
    """spec-mcp-host-real-station-tools CAP-2: a Django setup failure (bad
    settings, unreachable config -- anything) must never break a station
    that only needs the generic identity stub. `_real_station_apps()` is the
    isolation seam: it must swallow any exception and return {}, never
    raise, so `_apps` falls back to `asgi_for_station` for every station.
    """
    with patch("django.setup", side_effect=RuntimeError("boom")):
        assert mcp_host_app_module._real_station_apps() == {}  # noqa: SLF001 -- testing the isolation seam itself
