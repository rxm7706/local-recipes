"""Steward 21.3 — start/get survives disconnect (FR-12 / canopy AD-6, AD-12)."""

from __future__ import annotations

import ast
import json
from datetime import timedelta
from http import HTTPStatus
from pathlib import Path

import pytest
from django.db import connections
from django.utils import timezone
from django_pyforge.assertion.crypto import mint_assertion
from django_pyforge.mcp_http import asgi_for_server
from django_pyforge.mcp_http import dispatch_station_mcp
from django_pyforge.mcp_http import register_station_mcp_app
from django_pyforge.mcp_start_get import attach_start_get
from django_pyforge.models import McpHandle
from django_pyforge.models import RunState
from django_pyforge.supervisor import HANDLE_ENTROPY_BYTES
from django_pyforge.supervisor import HandleExpiredError
from django_pyforge.supervisor import HandleRefusedError
from django_pyforge.supervisor import complete_run
from django_pyforge.supervisor import get_run
from django_pyforge.supervisor import mint_handle
from django_pyforge.supervisor import publish_start
from django_pyforge.supervisor import register_runner
from django_pyforge.tasks import execute_supervised_run
from mcp.server.mcpserver import MCPServer
from starlette.testclient import TestClient

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLATFORM_ROOT.parents[1]
CHROME_ROOT = (
    REPO_ROOT
    / "src"
    / "shared"
    / "packages"
    / "django-pyforge"
    / "src"
    / "django_pyforge"
)
MCP_HTTP_PATH = CHROME_ROOT / "mcp_http.py"
SUPERVISOR_PATH = CHROME_ROOT / "supervisor.py"
START_GET_PATH = CHROME_ROOT / "mcp_start_get.py"
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

_SURVIVAL_FORBIDDEN = (
    "progress notification",
    "sticky session",
    "stream replay",
    "SseServerTransport",
)


@pytest.fixture
def atlas_assertion() -> str:
    return mint_assertion(sub="agent-21-3", roles=["pyforge:station:atlas"], station="atlas")


def _register_counting_runner(calls: dict[str, int]) -> None:
    def runner(payload: dict) -> dict:
        calls["n"] = calls.get("n", 0) + 1
        return {"pipeline": payload.get("name"), "seq": calls["n"]}

    register_runner("atlas", "run_pipeline", runner)


@pytest.mark.django_db
def test_start_returns_before_work_finishes(monkeypatch, atlas_assertion: str) -> None:
    calls: dict[str, int] = {"n": 0}
    _register_counting_runner(calls)
    delayed: list[tuple] = []

    def capture_delay(*args: object, **kwargs: object) -> None:
        delayed.append((args, kwargs))

    monkeypatch.setattr(execute_supervised_run, "apply_async", capture_delay)
    handle = publish_start(
        station="atlas",
        assertion=atlas_assertion,
        payload={"name": "core"},
    )
    assert len(handle) >= HANDLE_ENTROPY_BYTES
    row = McpHandle.objects.select_related("run").get(handle=handle)
    assert row.run.status == RunState.Status.RUNNING
    assert row.run.result is None
    assert calls["n"] == 0
    assert delayed


@pytest.mark.django_db
def test_disconnect_then_get_does_not_recompute(
    monkeypatch,
    atlas_assertion: str,
) -> None:
    calls: dict[str, int] = {"n": 0}
    _register_counting_runner(calls)
    delayed: list[tuple] = []

    def capture_delay(*args: object, **kwargs: object) -> None:
        delayed.append((args, kwargs))

    monkeypatch.setattr(execute_supervised_run, "apply_async", capture_delay)
    handle = publish_start(
        station="atlas",
        assertion=atlas_assertion,
        payload={"name": "core"},
    )
    _args, kwargs = delayed[0]
    # Story 42.2: the enqueue is `apply_async` (it carries the `sub` header and
    # the pre-minted task id), so the positional args live under `args=`.
    execute_supervised_run(*kwargs["args"])
    first = get_run(station="atlas", handle=handle, assertion=atlas_assertion)
    second = get_run(station="atlas", handle=handle, assertion=atlas_assertion)
    assert first["status"] == RunState.Status.SUCCEEDED
    assert first["result"] == {"pipeline": "core", "seq": 1}
    assert second["result"] == first["result"]
    assert calls["n"] == 1


@pytest.mark.django_db(transaction=True)
def test_get_succeeds_on_a_second_connection(monkeypatch, atlas_assertion: str) -> None:
    calls: dict[str, int] = {"n": 0}
    _register_counting_runner(calls)
    monkeypatch.setattr(execute_supervised_run, "apply_async", lambda *a, **k: None)
    handle = publish_start(
        station="atlas",
        assertion=atlas_assertion,
        payload={"name": "core"},
    )
    run = McpHandle.objects.get(handle=handle).run
    complete_run(str(run.id), status=RunState.Status.SUCCEEDED, result={"v": 7})
    replica = connections.create_connection("default")
    try:
        handles = replica.ops.quote_name("mcp_handles")
        runs = replica.ops.quote_name("run_state")
        with replica.cursor() as cursor:
            cursor.execute(
                f"SELECT handle FROM {handles} WHERE handle = %s",  # noqa: S608
                [handle],
            )
            assert cursor.fetchone() is not None
            cursor.execute(
                f"SELECT status FROM {runs} WHERE id = %s",  # noqa: S608
                [run.id],
            )
            status_row = cursor.fetchone()
        assert status_row is not None
        assert status_row[0] == RunState.Status.SUCCEEDED
    finally:
        replica.close()
    fetched = get_run(station="atlas", handle=handle, assertion=atlas_assertion)
    assert fetched["result"] == {"v": 7}


@pytest.mark.django_db
def test_possession_without_assertion_is_refused(
    monkeypatch,
    atlas_assertion: str,
) -> None:
    monkeypatch.setattr(execute_supervised_run, "apply_async", lambda *a, **k: None)
    handle = publish_start(
        station="atlas",
        assertion=atlas_assertion,
        payload={"name": "core"},
    )
    with pytest.raises(HandleRefusedError):
        get_run(station="atlas", handle=handle, assertion="")
    with pytest.raises(HandleRefusedError):
        get_run(station="atlas", handle=handle, assertion="not-a-jwt")
    other = mint_assertion(sub="someone-else", roles=["pyforge:station:atlas"], station="atlas")
    with pytest.raises(HandleRefusedError):
        get_run(station="atlas", handle=handle, assertion=other)


@pytest.mark.django_db
def test_handles_are_opaque_high_entropy_and_ttl(
    monkeypatch,
    atlas_assertion: str,
) -> None:
    monkeypatch.setattr(execute_supervised_run, "apply_async", lambda *a, **k: None)
    token = mint_handle()
    assert len(token) >= HANDLE_ENTROPY_BYTES
    assert token.isalnum() or "-" in token or "_" in token
    handle = publish_start(
        station="atlas",
        assertion=atlas_assertion,
        payload={"name": "core"},
    )
    row = McpHandle.objects.get(handle=handle)
    assert row.expires_at > timezone.now()
    row.expires_at = timezone.now() - timedelta(seconds=1)
    row.save(update_fields=["expires_at"])
    with pytest.raises(HandleExpiredError):
        get_run(station="atlas", handle=handle, assertion=atlas_assertion)


def _host_app():
    server = MCPServer("pyforge-atlas-atlas")
    attach_start_get(server, station="atlas")
    mcp_app = asgi_for_server(server)

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


@pytest.mark.django_db
def test_mcp_start_returns_handle_without_waiting(
    monkeypatch,
    atlas_assertion: str,
) -> None:
    monkeypatch.setattr(execute_supervised_run, "apply_async", lambda *a, **k: None)
    with TestClient(_host_app()) as client:
        response = client.post(
            "/stations/atlas/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "start_run_pipeline",
                    "arguments": {"name": "core", "assertion": atlas_assertion},
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
                "mcp-name": "start_run_pipeline",
                # Story 42.1: the transport gate verifies before it routes.
                "authorization": f"Bearer {atlas_assertion}",
            },
        )
    assert response.status_code == HTTPStatus.OK, response.text
    body = response.json()
    assert "error" not in body
    structured = (body.get("result") or {}).get("structuredContent") or {}
    text = (body.get("result") or {}).get("content") or []
    handle = structured.get("handle")
    if handle is None and text:
        handle = json.loads(text[0]["text"])["handle"]
    assert handle
    assert McpHandle.objects.filter(handle=handle).exists()
    run = McpHandle.objects.get(handle=handle).run
    assert run.status == RunState.Status.RUNNING


@pytest.mark.django_db
def test_start_is_unreachable_without_a_transport_assertion(
    monkeypatch,
    atlas_assertion: str,
) -> None:
    """Story 42.1 / red-team T-4: an anonymous `tools/call` never reaches the
    supervisor, so no run row is created -- the tool-argument assertion is
    defence in depth BEHIND the transport gate, not the only gate.
    """
    monkeypatch.setattr(execute_supervised_run, "apply_async", lambda *a, **k: None)
    before = RunState.objects.count()
    with TestClient(_host_app()) as client:
        response = client.post(
            "/stations/atlas/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "start_run_pipeline",
                    "arguments": {"name": "core", "assertion": atlas_assertion},
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
            },
        )
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.text
    assert RunState.objects.count() == before


def test_survival_is_not_progress_sticky_or_stream_replay() -> None:
    texts = [
        path.read_text(encoding="utf-8")
        for path in (
            SUPERVISOR_PATH,
            START_GET_PATH,
            MCP_HTTP_PATH,
            ATLAS_MCP_ASGI_PATH,
        )
    ]
    blob = "\n".join(texts).lower()
    for marker in _SURVIVAL_FORBIDDEN:
        assert marker.lower() not in blob, marker
    tree = ast.parse(SUPERVISOR_PATH.read_text(encoding="utf-8"))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert "RunState" in names
    assert "McpHandle" in names
