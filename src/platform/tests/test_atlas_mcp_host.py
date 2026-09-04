"""Story 21.2 — Atlas MCP on the host, dual-era (FR-11 / canopy AD-5)."""

from __future__ import annotations

import ast
from http import HTTPStatus
from pathlib import Path

import pytest
from django_pyforge.assertion.crypto import mint_assertion
from django_pyforge.mcp_http import SUPPORTED_MCP_REVISIONS
from django_pyforge.mcp_http import UNSUPPORTED_PROTOCOL_VERSION
from django_pyforge.mcp_http import asgi_for_server
from django_pyforge.mcp_http import dispatch_station_mcp
from django_pyforge.mcp_http import match_station_mcp
from django_pyforge.mcp_http import register_station_mcp_app
from django_pyforge.portals import PortalConfig
from mcp.server.mcpserver import MCPServer
from starlette.testclient import TestClient

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLATFORM_ROOT.parents[1]
ASGI_PATH = PLATFORM_ROOT / "config" / "asgi.py"
MCP_HTTP_PATH = (
    REPO_ROOT
    / "src"
    / "shared"
    / "packages"
    / "django-pyforge"
    / "src"
    / "django_pyforge"
    / "mcp_http.py"
)
ATLAS_MCP_ASGI_PATH = (
    REPO_ROOT
    / "src"
    / "shared"
    / "packages"
    / "django-atlas"
    / "src"
    / "django_atlas_portal"
    / "mcp_asgi.py"
)
ATLAS_SERVER_PATH = (
    REPO_ROOT
    / "src"
    / "shared"
    / "packages"
    / "pyforge-atlas"
    / "src"
    / "pyforge"
    / "atlas"
    / "mcp"
    / "server.py"
)

_UA_MARKERS = ("user-agent", "user_agent", "User-Agent", "client_name", "clientName")
_SSE_DUAL = ("SseServerTransport", "/sse", "message_path")


def _dummy_server() -> MCPServer:
    server = MCPServer("pyforge-atlas-atlas")

    @server.tool()
    def list_atlas_pipelines() -> list[str]:
        return ["core"]

    return server


def _host_app():
    mcp_app = asgi_for_server(_dummy_server())

    async def application(scope, receive, send):
        register_station_mcp_app("atlas", mcp_app)
        if scope["type"] == "lifespan":
            await mcp_app(scope, receive, send)
            return
        if await dispatch_station_mcp(scope, receive, send):
            return
        await send(
            {
                "type": "http.response.start",
                "status": 404,
                "headers": [(b"content-type", b"text/plain")],
            },
        )
        await send({"type": "http.response.body", "body": b"not mcp"})

    return application


def _authorization(station: str = "atlas") -> str:
    """Story 42.1: the transport gate verifies before it routes, so every POST
    through ``dispatch_station_mcp`` carries an assertion for its station.
    """
    token = mint_assertion(sub="fixture-21-2", roles=[f"pyforge:station:{station}"], station=station)
    return f"Bearer {token}"


def _post(path: str, payload: dict, headers: dict | None = None):
    with TestClient(_host_app()) as client:
        return client.post(
            path,
            json=payload,
            headers={
                "accept": "application/json, text/event-stream",
                "content-type": "application/json",
                "authorization": _authorization(),
                **(headers or {}),
            },
        )


def _get(path: str):
    with TestClient(_host_app()) as client:
        return client.get(path)


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


def test_match_station_mcp_is_a_pattern_not_a_roster():
    assert match_station_mcp("/stations/atlas/mcp") == "atlas"
    assert match_station_mcp("/stations/warden/mcp") == "warden"
    assert match_station_mcp("/stations/atlas/mcp/sse") is None
    assert match_station_mcp("/stations/atlas/") is None


@pytest.mark.parametrize("revision", ["2025-03-26", "2025-06-18", "2025-11-25"])
def test_initialize_echoes_requested_handshake_revision(revision: str):
    response = _post("/stations/atlas/mcp", _initialize(revision))
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    result = body.get("result") or {}
    assert result.get("protocolVersion") == revision


def test_modern_revision_header_is_accepted_on_the_same_post_path():
    response = _post(
        "/stations/atlas/mcp",
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        },
        headers={"mcp-protocol-version": "2026-07-28"},
    )
    assert response.status_code < HTTPStatus.INTERNAL_SERVER_ERROR
    body = response.json()
    assert "error" not in body or body["error"].get("code") != UNSUPPORTED_PROTOCOL_VERSION


@pytest.mark.parametrize("revision", ["2024-11-05", "2099-01-01"])
def test_unsupported_revision_returns_32022_with_supported_list(revision: str):
    response = _post("/stations/atlas/mcp", _initialize(revision))
    assert response.status_code == HTTPStatus.BAD_REQUEST
    error = response.json()["error"]
    assert error["code"] == UNSUPPORTED_PROTOCOL_VERSION
    assert list(error["data"]["supported"]) == list(SUPPORTED_MCP_REVISIONS)
    assert error["data"]["requested"] == revision


def test_get_is_405_and_does_not_serve_sse():
    response = _get("/stations/atlas/mcp")
    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response.headers.get("allow") == "POST"
    content_type = response.headers.get("content-type", "")
    assert "text/event-stream" not in content_type
    assert "event:" not in response.text


def test_portal_default_has_no_mcp_asgi_app():
    assert PortalConfig.mcp_asgi_app(None) is None


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_no_user_agent_or_client_name_branch():
    for path in (ASGI_PATH, MCP_HTTP_PATH, ATLAS_MCP_ASGI_PATH, ATLAS_SERVER_PATH):
        text = _source(path)
        for marker in _UA_MARKERS:
            assert marker not in text, f"{path} mentions {marker}"


def test_deprecated_dual_endpoint_sse_is_not_served():
    text = _source(MCP_HTTP_PATH) + _source(ASGI_PATH) + _source(ATLAS_MCP_ASGI_PATH)
    for marker in _SSE_DUAL:
        assert marker not in text, f"dual-endpoint SSE marker {marker} present"


def test_asgi_dispatch_has_no_atlas_roster_literal():
    tree = _tree(ASGI_PATH)
    literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and node.value == "atlas"
    ]
    assert literals == []
    source = _source(ASGI_PATH)
    assert "dispatch_station_mcp" in source
    assert "loaded_station_mcp_apps" in source


def test_atlas_portal_brings_existing_build_server():
    source = _source(ATLAS_MCP_ASGI_PATH)
    assert "pyforge.atlas.mcp.server" in source
    assert "build_server" in source
    assert "FastMCP" not in source


def test_atlas_server_registers_official_sdk():
    source = _source(ATLAS_SERVER_PATH)
    assert "mcp.server.mcpserver" in source
    assert "importlib.import_module" in source
    assert "from fastmcp import FastMCP" not in source
    assert "tools.run_pipeline" in source
    assert "tools.read_dataset" in source
