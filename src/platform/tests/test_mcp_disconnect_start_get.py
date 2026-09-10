"""Story 49.3 — CAP-4 in effect: start/get on all eight, real transport disconnect."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

import pytest
from django_pyforge.assertion.crypto import mint_assertion
from django_pyforge.discovery import iter_portal_configs
from django_pyforge.mcp_http import dispatch_station_mcp
from django_pyforge.mcp_http import register_station_mcp_app
from django_pyforge.models import RunState
from django_pyforge.supervisor import register_runner
from django_pyforge.tasks import execute_supervised_run
from starlette.testclient import TestClient

# Multi-minute ops are simulated with a gate the worker blocks on; the test
# proves transport survival without waiting wall-clock minutes in CI.
_SLOW_GATE = threading.Event()
_SLOW_RESULT: dict[str, Any] = {"target": ".", "completed": True}


@dataclass(frozen=True)
class StationStartGet:
    station: str
    start_tool: str
    get_tool: str
    run_tool: str


ALL_STATIONS: tuple[StationStartGet, ...] = (
    StationStartGet("atlas", "start_run_pipeline", "get_run", "run_pipeline"),
    StationStartGet("warden", "start_audit", "get_audit", "run_audit"),
    StationStartGet("doctor", "start_scan", "get_scan", "run_scan"),
    StationStartGet("herald", "start_notice", "get_notice", "run_notice"),
    StationStartGet("marshal", "start_loop", "get_loop", "run_loop"),
    StationStartGet("mason", "start_build", "get_build", "run_build"),
    StationStartGet("scribe", "start_recall", "get_recall", "run_recall"),
    StationStartGet("steward", "start_duty", "get_duty", "run_duty"),
)


def _slow_runner(_payload: dict[str, Any] | None) -> dict[str, Any]:
    """Block until the test releases the gate — simulates a multi-minute op."""
    assert _SLOW_GATE.wait(timeout=30.0), "slow runner timed out"
    return dict(_SLOW_RESULT)


def _assertion(station: str, sub: str = "agent-49-3") -> str:
    return mint_assertion(
        sub=sub,
        roles=[f"pyforge:station:{station}"],
        station=station,
    )


def _clear_station_mcp_cache(station: str) -> None:
    import django_atlas_portal.mcp_asgi as atlas_mcp  # noqa: PLC0415
    import django_doctor_portal.mcp_asgi as doctor_mcp  # noqa: PLC0415
    import django_herald_portal.mcp_asgi as herald_mcp  # noqa: PLC0415
    import django_marshal_portal.mcp_asgi as marshal_mcp  # noqa: PLC0415
    import django_mason_portal.mcp_asgi as mason_mcp  # noqa: PLC0415
    import django_scribe_portal.mcp_asgi as scribe_mcp  # noqa: PLC0415
    import django_steward_portal.mcp_asgi as steward_mcp  # noqa: PLC0415
    import django_warden_fabric.mcp_asgi as warden_mcp  # noqa: PLC0415

    if station == "atlas":
        atlas_mcp._APP = None  # noqa: SLF001
    elif station == "warden":
        warden_mcp._SERVER = None  # noqa: SLF001
    else:
        mod = {
            "doctor": doctor_mcp,
            "herald": herald_mcp,
            "marshal": marshal_mcp,
            "mason": mason_mcp,
            "scribe": scribe_mcp,
            "steward": steward_mcp,
        }[station]
        mod._CACHE.clear()  # noqa: SLF001


def _mcp_app(station: str):
    _clear_station_mcp_cache(station)
    by_name = {portal.station_name: portal for portal in iter_portal_configs()}
    mcp_app = by_name[station].mcp_asgi_app()
    assert mcp_app is not None

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
                "status": HTTPStatus.NOT_FOUND,
                "headers": [(b"content-type", b"text/plain")],
            },
        )
        await send({"type": "http.response.body", "body": b"not mcp"})

    return application


def _tool_call(
    client: TestClient,
    station: str,
    tool: str,
    arguments: dict[str, Any],
    assertion: str,
    call_id: int,
) -> dict[str, Any]:
    response = client.post(
        f"/stations/{station}/mcp",
        json={
            "jsonrpc": "2.0",
            "id": call_id,
            "method": "tools/call",
            "params": {
                "name": tool,
                "arguments": arguments,
                "_meta": {
                    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                    "io.modelcontextprotocol/clientCapabilities": {},
                },
            },
        },
        headers={
            "accept": "application/json, text/event-stream",
            "content-type": "application/json",
            "mcp-protocol-version": "2026-07-28",
            "mcp-method": "tools/call",
            "mcp-name": tool,
            "authorization": f"Bearer {assertion}",
        },
    )
    assert response.status_code == HTTPStatus.OK, response.text
    return response.json()


def _extract_handle(body: dict[str, Any]) -> str:
    structured = (body.get("result") or {}).get("structuredContent") or {}
    handle = structured.get("handle")
    if handle is None:
        text = (body.get("result") or {}).get("content") or []
        if text:
            handle = json.loads(text[0]["text"])["handle"]
    assert handle
    return handle


def _extract_run_status(body: dict[str, Any]) -> str:
    structured = (body.get("result") or {}).get("structuredContent") or {}
    status = structured.get("status")
    if status is None:
        text = (body.get("result") or {}).get("content") or []
        if text:
            status = json.loads(text[0]["text"]).get("status")
    return status or ""


def _disconnect_on_get_asgi(inner: Callable[..., Awaitable[None]]):
    """Inject ``http.disconnect`` on the first ``get_*`` tools/call — real transport drop."""

    state = {"armed": True}

    async def application(scope, receive, send):
        if scope["type"] != "http":
            await inner(scope, receive, send)
            return

        body_chunks: list[bytes] = []
        disconnected = False

        async def wrapped_receive():
            nonlocal disconnected
            message = await receive()
            if message["type"] == "http.request":
                body_chunks.append(message.get("body", b""))
                if not message.get("more_body", False):
                    payload = json.loads(b"".join(body_chunks).decode("utf-8"))
                    tool = (
                        (payload.get("params") or {}).get("name")
                        or scope.get("headers", {})
                    )
                    # headers arrive as bytes tuples; check mcp-name header too
                    headers = {
                        k.decode("latin-1").lower(): v.decode("latin-1")
                        for k, v in scope.get("headers", [])
                    }
                    tool_name = headers.get("mcp-name") or (
                        (payload.get("params") or {}).get("name")
                    )
                    if (
                        state["armed"]
                        and tool_name
                        and tool_name.startswith("get_")
                    ):
                        state["armed"] = False
                        disconnected = True
                        return {"type": "http.disconnect"}
                return message
            return message

        if state["armed"]:
            try:
                await inner(scope, wrapped_receive, send)
            except Exception:
                if disconnected:
                    return
                raise
        else:
            await inner(scope, receive, send)

    return application


@pytest.fixture(autouse=True)
def _reset_slow_gate():
    _SLOW_GATE.clear()
    yield
    _SLOW_GATE.set()


@pytest.fixture(autouse=True)
def _reset_mcp_app_caches():
    """Each TestClient lifespan needs a fresh StreamableHTTPSessionManager."""
    import django_atlas_portal.mcp_asgi as atlas_mcp  # noqa: PLC0415
    import django_doctor_portal.mcp_asgi as doctor_mcp  # noqa: PLC0415
    import django_herald_portal.mcp_asgi as herald_mcp  # noqa: PLC0415
    import django_marshal_portal.mcp_asgi as marshal_mcp  # noqa: PLC0415
    import django_mason_portal.mcp_asgi as mason_mcp  # noqa: PLC0415
    import django_scribe_portal.mcp_asgi as scribe_mcp  # noqa: PLC0415
    import django_steward_portal.mcp_asgi as steward_mcp  # noqa: PLC0415
    import django_warden_fabric.mcp_asgi as warden_mcp  # noqa: PLC0415

    atlas_mcp._APP = None  # noqa: SLF001
    warden_mcp._SERVER = None  # noqa: SLF001
    for mod in (
        doctor_mcp,
        herald_mcp,
        marshal_mcp,
        mason_mcp,
        scribe_mcp,
        steward_mcp,
    ):
        mod._CACHE.clear()  # noqa: SLF001
    yield


@pytest.mark.django_db
@pytest.mark.parametrize("face", ALL_STATIONS)
def test_start_get_tools_are_listed(face: StationStartGet) -> None:
    assertion = _assertion(face.station)
    with TestClient(_mcp_app(face.station)) as client:
        response = client.post(
            f"/stations/{face.station}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {
                    "_meta": {
                        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                        "io.modelcontextprotocol/clientCapabilities": {},
                    },
                },
            },
            headers={
                "accept": "application/json, text/event-stream",
                "content-type": "application/json",
                "mcp-protocol-version": "2026-07-28",
                "mcp-method": "tools/list",
                "authorization": f"Bearer {assertion}",
            },
        )
    assert response.status_code == HTTPStatus.OK, response.text
    tools = response.json().get("result", {}).get("tools", [])
    names = {tool["name"] for tool in tools}
    assert face.start_tool in names, names
    assert face.get_tool in names, names


@pytest.mark.django_db
@pytest.mark.parametrize("face", ALL_STATIONS)
def test_mcp_disconnect_then_get_retrieves_result(
    face: StationStartGet,
    monkeypatch,
) -> None:
    """Drop transport mid-get while the op runs, then reconnect and retrieve."""
    calls = {"n": 0}
    delayed: list[tuple] = []

    def counting_slow_runner(payload: dict[str, Any] | None) -> dict[str, Any]:
        calls["n"] += 1
        assert _SLOW_GATE.wait(timeout=30.0)
        target = "."
        if isinstance(payload, dict) and isinstance(payload.get("target"), str):
            target = payload["target"]
        return {"target": target, "seq": calls["n"], "completed": True}

    register_runner(face.station, face.run_tool, counting_slow_runner)

    def capture_delay(*args: object, **kwargs: object) -> None:
        delayed.append((args, kwargs))

    monkeypatch.setattr(execute_supervised_run, "apply_async", capture_delay)
    assertion = _assertion(face.station)

    with TestClient(_mcp_app(face.station)) as client:
        start_args = (
            {"name": "core", "assertion": assertion}
            if face.station == "atlas"
            else {"target": ".", "assertion": assertion}
        )
        started = _tool_call(
            client,
            face.station,
            face.start_tool,
            start_args,
            assertion,
            10,
        )
        handle = _extract_handle(started)
        assert delayed
        assert calls["n"] == 0

        worker = threading.Thread(
            target=lambda: execute_supervised_run(*delayed[0][1]["args"]),
            daemon=True,
        )
        worker.start()

        # Attempt get while worker is blocked — transport disconnect injected.
        disconnect_app = _disconnect_on_get_asgi(_mcp_app(face.station))
        with TestClient(disconnect_app) as drop_client:
            try:
                _tool_call(
                    drop_client,
                    face.station,
                    face.get_tool,
                    {"handle": handle, "assertion": assertion},
                    assertion,
                    11,
                )
            except Exception:
                pass

        time.sleep(0.05)
        _SLOW_GATE.set()
        worker.join(timeout=10.0)
        assert not worker.is_alive()

        with TestClient(_mcp_app(face.station)) as reconnect:
            fetched = _tool_call(
                reconnect,
                face.station,
                face.get_tool,
                {"handle": handle, "assertion": assertion},
                assertion,
                12,
            )

    assert _extract_run_status(fetched) == RunState.Status.SUCCEEDED
    assert calls["n"] == 1
