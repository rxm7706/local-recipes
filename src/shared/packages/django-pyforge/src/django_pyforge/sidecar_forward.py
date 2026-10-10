"""Forward Herald webhook requests to the mcp-host sidecar (Story 87.3 / CAP-69).

Mirrors ``mcp_http.proxy_station_mcp`` for ``/stations/herald/api/v1/webhooks/*``:
byte-identical body, header allowlist, no MCP assertion or rate limit.
"""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any

from django_pyforge.flags import evaluate_boolean
from django_pyforge.mcp_dual_era import read_body, send_http
from django_pyforge.mcp_http import (
    CONNECT_TIMEOUT_SECONDS,
    proxied_response_headers,
    proxy_timeout_seconds,
    sidecar_base_url,
)

logger = logging.getLogger(__name__)

HERALD_WEBHOOK_PATH_PREFIX = "/stations/herald/api/v1/webhooks/"
HERALD_WEBHOOK_SIDECAR_FLAG = "pyforge.steward.herald_webhook_sidecar"

HERALD_WEBHOOK_FORWARD_HEADERS = frozenset(
    {
        b"content-type",
        b"x-hub-signature-256",
        b"x-hub-timestamp",
        b"traceparent",
        b"tracestate",
    },
)


def is_herald_webhook_path(path: str) -> bool:
    return path.startswith(HERALD_WEBHOOK_PATH_PREFIX)


def _forwarded_webhook_headers(scope: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in scope.get("headers") or ():
        name = bytes(key).lower()
        if name in HERALD_WEBHOOK_FORWARD_HEADERS:
            headers[name.decode("latin-1")] = bytes(value).decode("latin-1")
    return headers


def _sidecar_url(base: str, scope: dict[str, Any]) -> str:
    path = scope["path"]
    qs = scope.get("query_string", b"")
    url = f"{base}{path}"
    if qs:
        url = f"{url}?{qs.decode('latin-1')}"
    return url


async def dispatch_herald_webhook_forward(
    scope: dict[str, Any],
    receive: Any,
    send: Any,
) -> bool:
    """Return True when this request was handled (forwarded or refused here)."""
    if scope.get("type") != "http":
        return False
    if not is_herald_webhook_path(scope.get("path", "")):
        return False
    base = sidecar_base_url()
    if not base:
        return False
    if not evaluate_boolean(HERALD_WEBHOOK_SIDECAR_FLAG, default=False):
        return False
    await proxy_herald_webhook(base, scope, receive, send)
    return True


async def proxy_herald_webhook(
    base: str,
    scope: dict[str, Any],
    receive: Any,
    send: Any,
) -> None:
    """Stream the webhook to the sidecar. Unreachable sidecar → 502 + error log."""
    import httpx

    hop_failures = (httpx.RequestError, httpx.StreamError, httpx.InvalidURL)
    body, _replay = await read_body(receive)
    url = _sidecar_url(base, scope)
    headers = _forwarded_webhook_headers(scope)
    method = scope.get("method", "GET")
    timeout = httpx.Timeout(proxy_timeout_seconds(), connect=CONNECT_TIMEOUT_SECONDS)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, content=body, headers=headers)
        await send(
            {
                "type": "http.response.start",
                "status": response.status_code,
                "headers": proxied_response_headers(response.headers),
            },
        )
        await send(
            {
                "type": "http.response.body",
                "body": response.content,
                "more_body": False,
            },
        )
    except hop_failures as exc:
        logger.error("mcp-host sidecar unreachable at %s: %s", url, exc)
        await send_http(
            send,
            HTTPStatus.BAD_GATEWAY,
            b"mcp-host sidecar unreachable",
            content_type=b"text/plain; charset=utf-8",
        )


__all__ = [
    "HERALD_WEBHOOK_FORWARD_HEADERS",
    "HERALD_WEBHOOK_PATH_PREFIX",
    "HERALD_WEBHOOK_SIDECAR_FLAG",
    "dispatch_herald_webhook_forward",
    "is_herald_webhook_path",
    "proxy_herald_webhook",
]
