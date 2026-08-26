"""Django-free dual-era MCP Streamable HTTP (canopy AD-5).

Importable from the mcp-host sidecar without Django or Langflow.
Constants and DualEra gate stay identical to the host face.
"""

from __future__ import annotations

import json
from collections import deque
from http import HTTPStatus
from typing import Any

SUPPORTED_MCP_REVISIONS: tuple[str, ...] = (
    "2025-03-26",
    "2025-06-18",
    "2025-11-25",
    "2026-07-28",
)
HANDSHAKE_MCP_REVISIONS: tuple[str, ...] = SUPPORTED_MCP_REVISIONS[:-1]
MODERN_MCP_REVISION = "2026-07-28"
UNSUPPORTED_PROTOCOL_VERSION = -32022
MCP_PROTOCOL_VERSION_HEADER = b"mcp-protocol-version"

_station_identity_servers: dict[str, Any] = {}


def match_station_mcp(path: str) -> str | None:
    """Return the station name if ``path`` is ``/stations/<name>/mcp``."""
    stripped = path.strip("/")
    parts = stripped.split("/")
    if len(parts) == 3 and parts[0] == "stations" and parts[2] == "mcp" and parts[1]:
        return parts[1]
    return None


def mcp_child_scope(scope: dict[str, Any], station: str) -> dict[str, Any]:
    """Rewrite path so a Starlette route of ``/`` matches the MCP mount."""
    new_scope = dict(scope)
    prefix = f"/stations/{station}/mcp"
    new_scope["root_path"] = scope.get("root_path", "") + prefix
    new_scope["path"] = "/"
    raw = scope.get("raw_path")
    if isinstance(raw, (bytes, bytearray)):
        new_scope["raw_path"] = b"/"
    return new_scope


def asgi_for_server(server: Any) -> Any:
    """Wrap an official ``MCPServer`` as POST-only dual-era Streamable HTTP."""
    from mcp.server.transport_security import TransportSecuritySettings

    starlette_app = server.streamable_http_app(
        streamable_http_path="/",
        json_response=True,
        stateless_http=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
        ),
    )
    return DualEraPostOnlyASGI(starlette_app)


def asgi_for_station(name: str) -> Any:
    """Cached identity MCP face (``station_face``) wrapped by ``asgi_for_server``."""
    server = _station_identity_servers.get(name)
    if server is None:
        from mcp.server.mcpserver import MCPServer

        server = MCPServer(f"pyforge-{name}")

        @server.tool()
        def station_face() -> str:
            return name

        _station_identity_servers[name] = server
    return asgi_for_server(server)


class DualEraPostOnlyASGI:
    """Reject non-POST; reject unsupported protocol revisions with ``-32022``."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        method = scope.get("method", "")
        if method != "POST":
            await send_http(
                send,
                HTTPStatus.METHOD_NOT_ALLOWED,
                b"Method Not Allowed",
                extra_headers=[(b"allow", b"POST")],
                content_type=b"text/plain; charset=utf-8",
            )
            return

        header_revision = _header_protocol_version(scope)
        if header_revision is not None and header_revision not in SUPPORTED_MCP_REVISIONS:
            await send_jsonrpc_error(
                send,
                None,
                UNSUPPORTED_PROTOCOL_VERSION,
                "Unsupported protocol version",
                {"supported": list(SUPPORTED_MCP_REVISIONS), "requested": header_revision},
            )
            return

        body, replay = await read_body(receive)
        if _is_initialize(body):
            requested = _initialize_revision(body)
            if requested is None or requested not in HANDSHAKE_MCP_REVISIONS:
                await send_jsonrpc_error(
                    send,
                    _jsonrpc_id(body),
                    UNSUPPORTED_PROTOCOL_VERSION,
                    "Unsupported protocol version",
                    {
                        "supported": list(SUPPORTED_MCP_REVISIONS),
                        "requested": requested if requested is not None else "",
                    },
                )
                return
        await self.app(scope, replay, send)


def _header_protocol_version(scope: dict[str, Any]) -> str | None:
    for key, value in scope.get("headers") or ():
        if key == MCP_PROTOCOL_VERSION_HEADER:
            return value.decode("latin-1")
    return None


def _is_initialize(body: bytes) -> bool:
    try:
        payload = json.loads(body.decode("utf-8") or "null")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    if isinstance(payload, dict):
        return payload.get("method") == "initialize"
    if isinstance(payload, list):
        return any(
            isinstance(item, dict) and item.get("method") == "initialize" for item in payload
        )
    return False


def _initialize_revision(body: bytes) -> str | None:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    message = payload
    if isinstance(payload, list):
        message = next(
            (item for item in payload if isinstance(item, dict) and item.get("method") == "initialize"),
            None,
        )
    if not isinstance(message, dict):
        return None
    params = message.get("params") or {}
    if not isinstance(params, dict):
        return None
    revision = params.get("protocolVersion")
    return revision if isinstance(revision, str) else None


def _jsonrpc_id(body: bytes) -> Any:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if isinstance(payload, dict):
        return payload.get("id")
    return None


async def read_body(receive: Any) -> tuple[bytes, Any]:
    chunks = bytearray()
    trailing: deque[dict[str, Any]] = deque()
    while True:
        message = await receive()
        if message["type"] != "http.request":
            trailing.append(message)
            break
        chunks.extend(message.get("body", b""))
        if not message.get("more_body", False):
            break
    body = bytes(chunks)
    cached: deque[dict[str, Any]] = deque()
    cached.append({"type": "http.request", "body": body, "more_body": False})
    cached.extend(trailing)

    async def replay() -> dict[str, Any]:
        if cached:
            return cached.popleft()
        return await receive()

    return body, replay


async def send_http(
    send: Any,
    status: HTTPStatus,
    body: bytes,
    *,
    extra_headers: list[tuple[bytes, bytes]] | None = None,
    content_type: bytes = b"application/json",
) -> None:
    headers = [
        (b"content-type", content_type),
        (b"content-length", str(len(body)).encode("ascii")),
    ]
    if extra_headers:
        headers.extend(extra_headers)
    await send({"type": "http.response.start", "status": int(status), "headers": headers})
    await send({"type": "http.response.body", "body": body})


async def send_jsonrpc_error(
    send: Any,
    request_id: Any,
    code: int,
    message: str,
    data: dict[str, Any],
) -> None:
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message, "data": data},
    }
    await send_http(
        send,
        HTTPStatus.BAD_REQUEST,
        json.dumps(payload).encode("utf-8"),
    )
