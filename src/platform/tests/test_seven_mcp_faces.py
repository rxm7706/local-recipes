"""Story 21.4 — remaining station MCP faces, dual-era (FR-11 / canopy AD-5)."""

from __future__ import annotations

import ast
from http import HTTPStatus
from pathlib import Path

import pytest
from django_pyforge.discovery import iter_portal_configs
from django_pyforge.mcp_http import SUPPORTED_MCP_REVISIONS
from django_pyforge.mcp_http import UNSUPPORTED_PROTOCOL_VERSION
from django_pyforge.mcp_http import dispatch_station_mcp
from django_pyforge.mcp_http import register_station_mcp_app
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
SHARED_PACKAGES = REPO_ROOT / "src" / "shared" / "packages"

REMAINING_STATIONS = (
    "doctor",
    "herald",
    "marshal",
    "mason",
    "scribe",
    "steward",
    "warden",
)
PROBE_STATIONS = ("chrome-probe", "infra-probe")
_UA_MARKERS = ("user-agent", "user_agent", "User-Agent", "client_name", "clientName")
_SSE_DUAL = ("SseServerTransport", "/sse", "message_path")


def _apps_py(station: str) -> Path:
    if station == "warden":
        return (
            SHARED_PACKAGES
            / "django-warden"
            / "src"
            / "django_warden_fabric"
            / "apps.py"
        )
    return (
        SHARED_PACKAGES
        / f"django-{station}"
        / "src"
        / f"django_{station}_portal"
        / "apps.py"
    )


def _mcp_app_from_portal(station: str):
    by_name = {portal.station_name: portal for portal in iter_portal_configs()}
    app = by_name[station].mcp_asgi_app()
    assert app is not None
    return app


def _host_app(station: str):
    mcp_app = _mcp_app_from_portal(station)

    async def application(scope, receive, send):
        register_station_mcp_app(station, mcp_app)
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


def _post(station: str, payload: dict, headers: dict | None = None):
    with TestClient(_host_app(station)) as client:
        return client.post(
            f"/stations/{station}/mcp",
            json=payload,
            headers={
                "accept": "application/json, text/event-stream",
                "content-type": "application/json",
                **(headers or {}),
            },
        )


def _get(station: str):
    with TestClient(_host_app(station)) as client:
        return client.get(f"/stations/{station}/mcp")


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


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _face_sources() -> list[Path]:
    return [
        ASGI_PATH,
        MCP_HTTP_PATH,
        *(_apps_py(station) for station in REMAINING_STATIONS),
    ]


@pytest.mark.parametrize("station", REMAINING_STATIONS)
@pytest.mark.parametrize("revision", ["2025-03-26", "2025-06-18", "2025-11-25"])
def test_initialize_echoes_requested_handshake_revision(station: str, revision: str):
    response = _post(station, _initialize(revision))
    assert response.status_code == HTTPStatus.OK
    result = response.json().get("result") or {}
    assert result.get("protocolVersion") == revision


@pytest.mark.parametrize("station", REMAINING_STATIONS)
def test_modern_revision_header_is_accepted_on_the_same_post_path(station: str):
    response = _post(
        station,
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
    unsupported = UNSUPPORTED_PROTOCOL_VERSION
    assert "error" not in body or body["error"].get("code") != unsupported


@pytest.mark.parametrize("station", REMAINING_STATIONS)
@pytest.mark.parametrize("revision", ["2024-11-05", "2099-01-01"])
def test_unsupported_initialize_returns_32022_with_supported_list(
    station: str, revision: str,
):
    response = _post(station, _initialize(revision))
    assert response.status_code == HTTPStatus.BAD_REQUEST
    error = response.json()["error"]
    assert error["code"] == UNSUPPORTED_PROTOCOL_VERSION
    assert list(error["data"]["supported"]) == list(SUPPORTED_MCP_REVISIONS)
    assert error["data"]["requested"] == revision


@pytest.mark.parametrize("station", REMAINING_STATIONS)
def test_unsupported_header_returns_32022_with_supported_list(station: str):
    response = _post(
        station,
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/list",
            "params": {},
        },
        headers={"mcp-protocol-version": "2024-11-05"},
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    error = response.json()["error"]
    assert error["code"] == UNSUPPORTED_PROTOCOL_VERSION
    assert list(error["data"]["supported"]) == list(SUPPORTED_MCP_REVISIONS)
    assert error["data"]["requested"] == "2024-11-05"


@pytest.mark.parametrize("station", REMAINING_STATIONS)
def test_get_is_405_and_does_not_serve_sse(station: str):
    response = _get(station)
    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response.headers.get("allow") == "POST"
    content_type = response.headers.get("content-type", "")
    assert "text/event-stream" not in content_type
    assert "event:" not in response.text


def test_seven_portals_register_mcp_tokens_and_apps():
    by_name = {portal.station_name: portal for portal in iter_portal_configs()}
    for station in REMAINING_STATIONS:
        portal = by_name[station]
        assert portal.mcp_token == f"mcp:{station}"
        assert portal.mcp_asgi_app() is not None
    for probe in PROBE_STATIONS:
        assert by_name[probe].mcp_asgi_app() is None


def test_asgi_dispatch_has_no_seven_station_roster():
    tree = _tree(ASGI_PATH)
    roster = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and node.value in REMAINING_STATIONS
    ]
    assert roster == []
    source = _source(ASGI_PATH)
    assert "dispatch_station_mcp" in source
    assert "loaded_station_mcp_apps" in source


def test_no_user_agent_or_client_name_branch():
    for path in _face_sources():
        text = _source(path)
        for marker in _UA_MARKERS:
            assert marker not in text, f"{path} mentions {marker}"


def test_deprecated_dual_endpoint_sse_is_not_served():
    text = "".join(_source(path) for path in _face_sources())
    for marker in _SSE_DUAL:
        assert marker not in text, f"dual-endpoint SSE marker {marker} present"
