"""Host MCP Streamable HTTP helpers (canopy AD-5 / FR-11).

Mount pattern is ``POST /stations/<name>/mcp``. Dual-era logic lives in
``mcp_dual_era`` (Django-free). This module discovers in-process faces or
proxies to the mcp-host sidecar when ``MCP_HOST_SIDECAR_BASE_URL`` is set.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from http import HTTPStatus
from typing import Any

from django_pyforge.discovery import iter_portal_configs
from django_pyforge.mcp_dual_era import (  # noqa: F401
    HANDSHAKE_MCP_REVISIONS,
    MCP_PROTOCOL_VERSION_HEADER,
    MODERN_MCP_REVISION,
    SUPPORTED_MCP_REVISIONS,
    UNSUPPORTED_PROTOCOL_VERSION,
    DualEraPostOnlyASGI,
    asgi_for_server,
    asgi_for_station,
    match_station_mcp,
    mcp_child_scope,
    read_body,
    send_http,
)

logger = logging.getLogger(__name__)

MCP_HOST_SIDECAR_URL_ENV = "MCP_HOST_SIDECAR_BASE_URL"

_mcp_apps: dict[str, Any] = {}
_import_skip_logged = False


def sidecar_base_url() -> str | None:
    raw = os.environ.get(MCP_HOST_SIDECAR_URL_ENV, "").strip()
    return raw.rstrip("/") or None


def _log_import_skip(where: str) -> None:
    global _import_skip_logged
    if _import_skip_logged:
        return
    _import_skip_logged = True
    logger.warning(
        "MCP face skipped (%s): mcp 2.x MCPServer unavailable in this interpreter; "
        "set %s to reach the mcp-host sidecar (spec-mcp-era-isolation retire-skip.md)",
        where,
        MCP_HOST_SIDECAR_URL_ENV,
    )


def _install_flags_mcp() -> None:
    if "flags" in _mcp_apps:
        return
    from django_pyforge.flags import flags_asgi_app

    try:
        _mcp_apps["flags"] = flags_asgi_app()
    except ImportError:
        _log_import_skip("flags")
        return


def register_station_mcp_app(station: str, app: Any) -> None:
    """Bind a Streamable HTTP app for ``/stations/<station>/mcp``."""
    _mcp_apps[station] = app


def station_mcp_app(station: str) -> Any | None:
    if station in _mcp_apps:
        return _mcp_apps[station]
    _mcp_apps.update(dict(iter_station_mcp_apps()))
    _install_flags_mcp()
    return _mcp_apps.get(station)


def loaded_station_mcp_apps() -> dict[str, Any]:
    """Ensure discovery has run; return the bound MCP ASGI apps."""
    if not _mcp_apps:
        _mcp_apps.update(dict(iter_station_mcp_apps()))
    _install_flags_mcp()
    return _mcp_apps


async def dispatch_station_mcp(scope: dict[str, Any], receive: Any, send: Any) -> bool:
    """Handle ``/stations/<name>/mcp`` via sidecar proxy or in-process app."""
    station = match_station_mcp(scope["path"])
    if station is None:
        return False
    base = sidecar_base_url()
    if base:
        await proxy_station_mcp(base, station, scope, receive, send)
        return True
    app = station_mcp_app(station)
    if app is None:
        return False
    await app(mcp_child_scope(scope, station), receive, send)
    return True


def iter_station_mcp_apps() -> Iterator[tuple[str, Any]]:
    """Yield ``(station_name, asgi_app)`` from portal AppConfigs that supply MCP."""
    for portal in iter_portal_configs():
        factory = getattr(portal, "mcp_asgi_app", None)
        if not callable(factory):
            continue
        try:
            app = factory()
        except ImportError:
            _log_import_skip(portal.station_name)
            continue
        if app is not None:
            yield portal.station_name, app


async def proxy_station_mcp(
    base: str,
    station: str,
    scope: dict[str, Any],
    receive: Any,
    send: Any,
) -> None:
    """Forward the request to the mcp-host sidecar. Unreachable → 502 + error log."""
    import httpx

    body, _replay = await read_body(receive)
    url = f"{base}/stations/{station}/mcp"
    headers: dict[str, str] = {}
    for key, value in scope.get("headers") or ():
        name = key.decode("latin-1")
        if name.lower() in {"host", "content-length", "transfer-encoding"}:
            continue
        headers[name] = value.decode("latin-1")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.request(
                scope.get("method", "POST"),
                url,
                content=body,
                headers=headers,
            )
    except httpx.RequestError as exc:
        logger.error("mcp-host sidecar unreachable at %s: %s", base, exc)
        await send_http(
            send,
            HTTPStatus.BAD_GATEWAY,
            b"mcp-host sidecar unreachable",
            content_type=b"text/plain; charset=utf-8",
        )
        return
    out_headers: list[tuple[bytes, bytes]] = []
    for key, value in response.headers.items():
        if key.lower() in {"transfer-encoding", "connection"}:
            continue
        out_headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))
    await send(
        {
            "type": "http.response.start",
            "status": response.status_code,
            "headers": out_headers,
        }
    )
    await send({"type": "http.response.body", "body": response.content})
