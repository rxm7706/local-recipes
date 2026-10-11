"""Forward Herald webhook requests to the mcp-host sidecar (Story 87.3 / CAP-69).

Mirrors ``mcp_http.proxy_station_mcp`` for herald's two webhook paths only:
byte-identical body (within herald's caps), header allowlist, no MCP assertion
or rate limit.
"""

from __future__ import annotations

import json
import logging
from http import HTTPStatus
from typing import Any

from django_pyforge.flags import evaluate_boolean
from django_pyforge.mcp_dual_era import send_http
from django_pyforge.mcp_http import (
    CONNECT_TIMEOUT_SECONDS,
    proxied_response_headers,
    proxy_timeout_seconds,
    sidecar_base_url,
)

logger = logging.getLogger(__name__)

HERALD_WEBHOOK_PATH_PREFIX = "/stations/herald/api/v1/webhooks/"
HERALD_WEBHOOK_SIDECAR_FLAG = "pyforge.steward.herald_webhook_sidecar"

# Literals (pap:AD-2 — no pyforge.herald import in django_pyforge); drift-checked in platform-ci.
HERALD_WEBHOOK_ON_SHIP_PATH = "/stations/herald/api/v1/webhooks/on-ship"
HERALD_WEBHOOK_ON_PR_CLOSE_PATH = "/stations/herald/api/v1/webhooks/on-pr-close"
HERALD_WEBHOOK_ALLOWED_PATHS = frozenset(
    {
        HERALD_WEBHOOK_ON_SHIP_PATH,
        HERALD_WEBHOOK_ON_PR_CLOSE_PATH,
    },
)

MAX_BODY_BYTES = 1_000_000
MAX_BODY_MESSAGES = 10_000

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


def is_allowed_herald_webhook_path(path: str) -> bool:
    return path in HERALD_WEBHOOK_ALLOWED_PATHS


def _forwarded_webhook_headers(scope: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in scope.get("headers") or ():
        name = bytes(key).lower()
        if name in HERALD_WEBHOOK_FORWARD_HEADERS:
            headers[name.decode("latin-1")] = bytes(value).decode("latin-1")
    return headers


def _sidecar_url(base: str, allowed_path: str) -> str:
    return f"{base}{allowed_path}"


class _ClientDisconnected(Exception):
    pass


async def _read_webhook_body(receive: Any) -> bytes:
    chunks: list[bytes] = []
    size = 0
    messages = 0
    while True:
        message = await receive()
        if message["type"] != "http.request":
            raise _ClientDisconnected()
        messages += 1
        if messages > MAX_BODY_MESSAGES:
            msg = f"request body arrived in more than {MAX_BODY_MESSAGES} chunks"
            raise _BodyTooLarge(msg)
        body = message.get("body", b"")
        size += len(body)
        if size > MAX_BODY_BYTES:
            msg = f"request body exceeds {MAX_BODY_BYTES} bytes"
            raise _BodyTooLarge(msg)
        if body:
            chunks.append(body)
        if not message.get("more_body", False):
            break
    return b"".join(chunks)


class _BodyTooLarge(Exception):
    pass


async def _send_host_not_found(send: Any) -> None:
    body = json.dumps({"detail": "Not Found"}).encode("utf-8")
    await send_http(send, HTTPStatus.NOT_FOUND, body)


async def _send_body_too_large(send: Any, exc: _BodyTooLarge) -> None:
    body = json.dumps({"error": str(exc)}).encode("utf-8")
    await send_http(send, HTTPStatus.REQUEST_ENTITY_TOO_LARGE, body)


async def dispatch_herald_webhook_forward(
    scope: dict[str, Any],
    receive: Any,
    send: Any,
) -> bool:
    """Return True when this request was handled (forwarded or refused here)."""
    if scope.get("type") != "http":
        return False
    path = scope.get("path", "")
    if not is_herald_webhook_path(path):
        return False
    base = sidecar_base_url()
    if not base:
        return False
    if not evaluate_boolean(HERALD_WEBHOOK_SIDECAR_FLAG, default=False):
        return False
    if not is_allowed_herald_webhook_path(path):
        await _send_host_not_found(send)
        return True
    await proxy_herald_webhook(base, path, scope, receive, send)
    return True


async def proxy_herald_webhook(
    base: str,
    allowed_path: str,
    scope: dict[str, Any],
    receive: Any,
    send: Any,
) -> None:
    """Stream the webhook to the sidecar. Unreachable sidecar → 502 + error log."""
    import httpx

    hop_failures = (httpx.RequestError, httpx.StreamError, httpx.InvalidURL)
    try:
        body = await _read_webhook_body(receive)
    except _ClientDisconnected:
        return
    except _BodyTooLarge as exc:
        await _send_body_too_large(send, exc)
        return
    url = _sidecar_url(base, allowed_path)
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
    "HERALD_WEBHOOK_ALLOWED_PATHS",
    "HERALD_WEBHOOK_FORWARD_HEADERS",
    "HERALD_WEBHOOK_ON_PR_CLOSE_PATH",
    "HERALD_WEBHOOK_ON_SHIP_PATH",
    "HERALD_WEBHOOK_PATH_PREFIX",
    "HERALD_WEBHOOK_SIDECAR_FLAG",
    "MAX_BODY_BYTES",
    "MAX_BODY_MESSAGES",
    "dispatch_herald_webhook_forward",
    "is_allowed_herald_webhook_path",
    "is_herald_webhook_path",
    "proxy_herald_webhook",
]
