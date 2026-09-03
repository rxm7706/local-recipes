"""Host MCP Streamable HTTP helpers (canopy AD-5 / FR-11).

Mount pattern is ``POST /stations/<name>/mcp``. Dual-era logic lives in
``mcp_dual_era`` (Django-free). This module discovers in-process faces or
proxies to the mcp-host sidecar when ``MCP_HOST_SIDECAR_BASE_URL`` is set.

Story 42.1 (CAP-4, red-team T-4/T-5/X-5): the assertion is verified HERE,
before either route is taken, because this dispatch runs ahead of every Django
middleware; and the sidecar hop streams, carries only a header allowlist whose
credential is the assertion this host verified, and budgets at least the Celery
hard limit instead of five seconds.

Story 42.2 (CAP-11, red-team A-6): the verified ``sub`` is then charged a token
in ``rate_limit``, so a looping agent meets 429 here rather than filling
PostgreSQL and the broker behind it. The limiter runs after the gate on
purpose — an unverified caller has no subject to charge, and charging one it
merely claimed would let any client drain another's allowance.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import math
import os
from collections.abc import Iterator
from http import HTTPStatus
from typing import Any

from django_pyforge.assertion.schema import CLAIM_SUB
from django_pyforge.discovery import iter_portal_configs
from django_pyforge.mcp_auth import TransportRefusal
from django_pyforge.mcp_auth import authorize_station_scope
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
from django_pyforge.rate_limit import MCP_SCOPE
from django_pyforge.rate_limit import consume

logger = logging.getLogger(__name__)

MCP_HOST_SIDECAR_URL_ENV = "MCP_HOST_SIDECAR_BASE_URL"
MCP_PROXY_TIMEOUT_ENV = "MCP_PROXY_TIMEOUT_SECONDS"

# A tool call may run as long as Celery lets its task run; anything shorter
# turns a legitimate long call into a 502 (red-team T-5). This floor is the
# shipped ``CELERY_TASK_TIME_LIMIT`` and applies even when Django is not
# importable, so the sidecar hop can never regress to a five-second budget.
CELERY_HARD_LIMIT_SECONDS = 300.0
CONNECT_TIMEOUT_SECONDS = 5.0
# Well under the 30s ingress client timeout that governs an idle stream
# (BS-2 revised: the documented OpenShift case fails at 30s and works at 15s).
KEEPALIVE_INTERVAL_SECONDS = 15.0
KEEPALIVE_FRAME = b": keep-alive\n\n"
EVENT_STREAM_MEDIA_TYPE = "text/event-stream"

# An ALLOWLIST, never a scrub list: only these inbound headers cross to the
# sidecar, so no credential the platform has not named can ride along, and the
# inbound Authorization is replaced by the assertion this host verified.
FORWARDED_REQUEST_HEADERS = frozenset(
    {
        b"content-type",
        b"accept",
        b"mcp-protocol-version",
        b"traceparent",
        b"tracestate",
    },
)
# Hop-by-hop plus the framing/encoding headers that describe the sidecar's own
# wire form, not the decoded bytes this proxy re-frames.
DROPPED_RESPONSE_HEADERS = frozenset(
    {
        b"connection",
        b"content-encoding",
        b"content-length",
        b"keep-alive",
        b"proxy-authenticate",
        b"set-cookie",
        b"trailer",
        b"transfer-encoding",
        b"upgrade",
        b"x-accel-buffering",
    },
)

_UPSTREAM_DONE = object()

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


def station_rate_refusal(claims: dict[str, Any]) -> TransportRefusal | None:
    """Charge this call to its verified ``sub``; ``None`` when it may proceed.

    Every refusal here is 429 with a ``Retry-After``, including the one raised
    because the limiter's own store did not answer: an agent that cannot be
    counted must not be admitted (the fail-closed clause), and telling it when
    to come back is the difference between backpressure and a black hole.
    """
    subject = claims.get(CLAIM_SUB)
    subject = subject if isinstance(subject, str) else ""
    decision = consume(MCP_SCOPE, subject)
    if decision.allowed:
        return None
    return TransportRefusal(
        HTTPStatus.TOO_MANY_REQUESTS,
        "rate limited",
        decision.reason,
        retry_after=decision.retry_after,
    )


async def _refuse(send: Any, station: str, refusal: TransportRefusal) -> None:
    """Log the refusal structurally, then send it. One shape for every gate."""
    logger.warning(
        "mcp.transport_refused",
        extra={
            "event": "mcp.transport_refused",
            "station": station,
            "status": int(refusal.status),
            "reason": refusal.reason,
        },
    )
    await send_http(
        send,
        refusal.status,
        refusal.body(),
        extra_headers=refusal.headers() or None,
    )


async def dispatch_station_mcp(scope: dict[str, Any], receive: Any, send: Any) -> bool:
    """Authorize, rate-limit, then route to the sidecar proxy or the app.

    The gate is here rather than in a middleware because nothing downstream of
    this call is a middleware: this dispatch runs first. It reads headers only,
    so every JSON-RPC method -- ``initialize`` and ``tools/list`` included --
    passes through it (red-team T-4), and the request body reaches the station
    unread.

    The limiter runs between the two, so a refused subject costs neither a
    sidecar hop nor a station call (red-team A-6), and an unverified caller
    never gets to spend a subject's allowance.
    """
    station = match_station_mcp(scope["path"])
    if station is None:
        return False
    if scope.get("method", "POST") != "POST":
        # Streamable HTTP is a single POST endpoint; a method that can never
        # carry a JSON-RPC call is refused here, so it needs no assertion and
        # never reaches a station or the sidecar.
        await send_http(
            send,
            HTTPStatus.METHOD_NOT_ALLOWED,
            b"Method Not Allowed",
            extra_headers=[(b"allow", b"POST")],
            content_type=b"text/plain; charset=utf-8",
        )
        return True
    authorized = authorize_station_scope(scope, station)
    if isinstance(authorized, TransportRefusal):
        await _refuse(send, station, authorized)
        return True
    limited = station_rate_refusal(authorized.claims)
    if limited is not None:
        await _refuse(send, station, limited)
        return True
    base = sidecar_base_url()
    if base:
        await proxy_station_mcp(
            base,
            station,
            scope,
            receive,
            send,
            assertion=authorized.token,
        )
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


def proxy_timeout_seconds() -> float:
    """Per-call budget for the sidecar hop: never below the Celery hard limit.

    ``float()`` accepts ``nan`` and ``inf``, and neither survives ``max()`` as a
    budget: ``max(nan, floor)`` IS ``nan``, and ``inf`` removes the budget
    outright, so a hung sidecar would pin the worker forever -- exactly what the
    floor exists to prevent. Anything not a finite positive number falls back to
    the floor.
    """
    raw = os.environ.get(MCP_PROXY_TIMEOUT_ENV, "").strip()
    try:
        configured = float(raw) if raw else 0.0
    except ValueError:
        configured = 0.0
    if not math.isfinite(configured) or configured <= 0.0:
        configured = 0.0
    return max(configured, CELERY_HARD_LIMIT_SECONDS)


def forwarded_request_headers(scope: dict[str, Any], assertion: str) -> dict[str, str]:
    """The allowlisted inbound headers plus the VERIFIED assertion.

    The inbound credential never crosses this hop: whatever arrived in
    Authorization was either this assertion (verified above) or a refusal, so
    what the sidecar sees is only what this host itself vouched for.
    """
    headers: dict[str, str] = {}
    for key, value in scope.get("headers") or ():
        name = bytes(key).lower()
        if name in FORWARDED_REQUEST_HEADERS:
            headers[name.decode("latin-1")] = bytes(value).decode("latin-1")
    headers["authorization"] = f"Bearer {assertion}"
    return headers


def proxied_response_headers(headers: Any) -> list[tuple[bytes, bytes]]:
    """Sidecar response headers, re-framed for a streamed ASGI body."""
    out: list[tuple[bytes, bytes]] = []
    for key, value in headers.items():
        name = str(key).lower().encode("latin-1")
        if name in DROPPED_RESPONSE_HEADERS:
            continue
        out.append((name, str(value).encode("latin-1")))
    # Nothing between here and the client may sit on the stream.
    out.append((b"x-accel-buffering", b"no"))
    return out


def _keepalive_frame(headers: Any) -> bytes | None:
    """A comment frame for an event stream; ``None`` for any other body.

    Injecting bytes into a JSON body would corrupt it, so the idle keep-alive
    exists only for the media type that defines comment frames.
    """
    media_type = str(headers.get("content-type", "") or "")
    if media_type.split(";", 1)[0].strip().lower() == EVENT_STREAM_MEDIA_TYPE:
        return KEEPALIVE_FRAME
    return None


async def _drain_upstream(response: Any, queue: asyncio.Queue) -> None:
    """Read upstream into ``queue``, reporting ANY failure as a queued item.

    Narrowing this to a family of exceptions is a liveness bug, not a style
    choice: whatever escapes here puts nothing on the queue, and the relay's
    only exits are a queued item -- so an unreported failure leaves it waiting
    on a queue nothing will ever fill. ``httpx.StreamError`` alone would do it
    (it subclasses ``RuntimeError``, not ``HTTPError``).
    """
    try:
        async for chunk in response.aiter_bytes():
            if chunk:
                await queue.put(chunk)
    except asyncio.CancelledError:
        # Our own teardown cancels this task; never report that as a failure.
        raise
    except BaseException as exc:  # noqa: BLE001 -- reported to the relay, not swallowed
        await queue.put(exc)
        return
    await queue.put(_UPSTREAM_DONE)


def _log_dead_pump(pump: asyncio.Task) -> None:
    """Log why the pump ended, retrieving its exception so it is not orphaned."""
    if pump.cancelled():
        logger.error("mcp-host sidecar stream ended: the upstream read was cancelled")
        return
    exc = pump.exception()
    logger.error("mcp-host sidecar stream ended without a result: %s", exc)


async def _stream_upstream_body(response: Any, send: Any) -> None:
    """Relay the sidecar's body chunk by chunk, keeping an idle stream alive.

    Reading upstream in a task and waiting on a queue (rather than timing out
    the upstream read itself) means the keep-alive clock never cancels a read
    that is mid-flight. The cost of that indirection is that the relay must not
    trust the pump to always report: a pump that died without queuing anything
    is a dead end, so the idle branch checks for it and stops instead of
    spinning (endless keep-alive frames, a response that never closes).
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=1)
    keepalive = _keepalive_frame(response.headers)
    pump = asyncio.create_task(_drain_upstream(response, queue))
    try:
        while True:
            try:
                item = await asyncio.wait_for(
                    queue.get(),
                    timeout=KEEPALIVE_INTERVAL_SECONDS,
                )
            except TimeoutError:
                if pump.done() and queue.empty():
                    _log_dead_pump(pump)
                    break
                if keepalive is not None:
                    await send(
                        {
                            "type": "http.response.body",
                            "body": keepalive,
                            "more_body": True,
                        },
                    )
                continue
            if item is _UPSTREAM_DONE:
                break
            if isinstance(item, BaseException):
                # The response head is already sent, so the only way to signal
                # a mid-stream failure is to log it and close the body.
                logger.error("mcp-host sidecar stream failed: %s", item)
                break
            await send(
                {"type": "http.response.body", "body": item, "more_body": True},
            )
    finally:
        pump.cancel()
        # A pump that already failed re-raises on await; that must not escape
        # and leave the body unclosed. Every such failure has already been
        # reported -- through the queue, or by `_log_dead_pump`.
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await pump
    await send({"type": "http.response.body", "body": b"", "more_body": False})


async def proxy_station_mcp(
    base: str,
    station: str,
    scope: dict[str, Any],
    receive: Any,
    send: Any,
    *,
    assertion: str,
) -> None:
    """Stream the request to the mcp-host sidecar. Unreachable → 502 + error log.

    The RESPONSE is streamed: its head goes out as soon as the sidecar sends it
    and every chunk is relayed as it arrives, so a long tool call reaches the
    client as it runs instead of being buffered to completion (red-team T-5).
    The request body is still read to completion first -- an ASGI request body
    has no length until ``more_body`` is false, and the hop needs one.
    """
    import httpx

    # httpx's failure surface is NOT one tree: StreamError subclasses
    # RuntimeError and InvalidURL subclasses Exception, so neither is a
    # RequestError. Catching RequestError alone lets a teardown failure escape
    # AFTER the head was sent -- the exact case the `started` branch below
    # exists to close -- and turns a malformed sidecar base URL into an
    # unhandled ASGI exception instead of a 502.
    hop_failures = (httpx.RequestError, httpx.StreamError, httpx.InvalidURL)

    body, _replay = await read_body(receive)
    url = f"{base}/stations/{station}/mcp"
    headers = forwarded_request_headers(scope, assertion)
    timeout = httpx.Timeout(proxy_timeout_seconds(), connect=CONNECT_TIMEOUT_SECONDS)
    started = False
    closed = False
    try:
        async with (
            httpx.AsyncClient(timeout=timeout) as client,
            client.stream("POST", url, content=body, headers=headers) as response,
        ):
            await send(
                {
                    "type": "http.response.start",
                    "status": response.status_code,
                    "headers": proxied_response_headers(response.headers),
                },
            )
            started = True
            await _stream_upstream_body(response, send)
            closed = True
    except hop_failures as exc:
        logger.error("mcp-host sidecar unreachable at %s: %s", base, exc)
        if started:
            # A failure raised while unwinding the stream (teardown, not the
            # body) must not emit a SECOND final message: the body is closed.
            if not closed:
                await send(
                    {"type": "http.response.body", "body": b"", "more_body": False},
                )
            return
        await send_http(
            send,
            HTTPStatus.BAD_GATEWAY,
            b"mcp-host sidecar unreachable",
            content_type=b"text/plain; charset=utf-8",
        )
