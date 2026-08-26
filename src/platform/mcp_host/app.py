"""Official-SDK MCP faces for the isolated mcp-host process.

No Langflow. No FastMCP. Imports ``django_pyforge.mcp_dual_era`` only.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from http import HTTPStatus
from typing import Self

from django_pyforge.mcp_dual_era import asgi_for_station
from django_pyforge.mcp_dual_era import match_station_mcp
from django_pyforge.mcp_dual_era import mcp_child_scope
from django_pyforge.mcp_dual_era import send_http

DEFAULT_STATIONS = (
    "atlas",
    "doctor",
    "herald",
    "marshal",
    "mason",
    "scribe",
    "steward",
    "warden",
    "flags",
)


def _stations() -> tuple[str, ...]:
    raw = os.environ.get("MCP_HOST_STATIONS", "").strip()
    if not raw:
        return DEFAULT_STATIONS
    return tuple(part.strip() for part in raw.split(",") if part.strip())


_apps = {name: asgi_for_station(name) for name in _stations()}


class _LifespanManager:
    """Queue-driven lifespan for one Streamable HTTP app (Starlette calls receive twice)."""

    def __init__(self, app) -> None:
        self._app = app
        self._receive_queue: asyncio.Queue = asyncio.Queue()
        self._send_queue: asyncio.Queue = asyncio.Queue()
        self._task: asyncio.Task | None = None

    async def _receive(self):
        return await self._receive_queue.get()

    async def _send(self, message) -> None:
        await self._send_queue.put(message)

    async def __aenter__(self) -> Self:
        self._task = asyncio.create_task(
            self._app({"type": "lifespan"}, self._receive, self._send),
        )
        await self._receive_queue.put({"type": "lifespan.startup"})
        message = await self._send_queue.get()
        if message["type"] == "lifespan.startup.failed":
            with contextlib.suppress(BaseException):
                assert self._task is not None
                await self._task
            msg = f"startup failed: {message.get('message')}"
            raise RuntimeError(msg)
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self._receive_queue.put({"type": "lifespan.shutdown"})
        message = await self._send_queue.get()
        if message["type"] == "lifespan.shutdown.failed":
            with contextlib.suppress(BaseException):
                assert self._task is not None
                await self._task
            msg = f"shutdown failed: {message.get('message')}"
            raise RuntimeError(msg)
        assert self._task is not None
        await self._task


async def _dispatch_lifespan(receive, send) -> None:
    event = await receive()
    if event["type"] != "lifespan.startup":
        await send(
            {
                "type": "lifespan.startup.failed",
                "message": f"unexpected {event['type']}",
            }
        )
        return
    started = False
    try:
        async with contextlib.AsyncExitStack() as stack:
            for child in _apps.values():
                await stack.enter_async_context(_LifespanManager(child))
            started = True
            await send({"type": "lifespan.startup.complete"})
            event = await receive()
            if event["type"] != "lifespan.shutdown":
                await send(
                    {
                        "type": "lifespan.shutdown.failed",
                        "message": f"unexpected {event['type']}",
                    }
                )
                return
    except Exception as exc:  # noqa: BLE001
        failed = "shutdown" if started else "startup"
        await send({"type": f"lifespan.{failed}.failed", "message": str(exc)})
        return
    await send({"type": "lifespan.shutdown.complete"})


async def app(scope: dict, receive, send) -> None:
    if scope["type"] == "lifespan":
        await _dispatch_lifespan(receive, send)
        return
    if scope["type"] != "http":
        await send_http(send, HTTPStatus.NOT_FOUND, b"not found")
        return
    path = scope.get("path", "")
    if path in {"/health", "/api/health"}:
        await send_http(send, HTTPStatus.OK, b'{"status":"ok"}')
        return
    station = match_station_mcp(path)
    if station is None or station not in _apps:
        await send_http(send, HTTPStatus.NOT_FOUND, b"unknown station mcp path")
        return
    await _apps[station](mcp_child_scope(scope, station), receive, send)
