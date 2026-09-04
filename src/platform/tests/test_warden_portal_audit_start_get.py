"""Story 10.2 — HTMX start/get one audit through PortalClient (FR-10 / FR-12)."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import uuid
from http import HTTPStatus
from pathlib import Path

import pytest
from django.test import Client
from django.utils import timezone
from django_pyforge.assertion.crypto import mint_assertion
from django_pyforge.mcp_http import dispatch_station_mcp
from django_pyforge.mcp_http import register_station_mcp_app
from django_pyforge.models import McpHandle
from django_pyforge.models import RunState
from django_pyforge.roles import IDP_TOKEN_CLAIMS_SESSION_KEY
from django_pyforge.tasks import execute_supervised_run
from django_warden_fabric.mcp_asgi import build_warden_mcp_asgi
from starlette.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
HANDLE_RE = re.compile(r'id="warden-audit-handle">([^<]+)</')


def _claims(sub: str, *roles: str) -> dict[str, object]:
    return {"sub": sub, "groups": list(roles)}


# Story 42.5: group claims carry the prefixed namespace; a bare "warden" is no station role.
def _authed(
    client: Client,
    settings,
    *,
    sub: str = "op-1",
    role: str = "pyforge:station:warden",
) -> Client:
    settings.IDP_CLAIMS_SNAPSHOT = _claims(sub, role)
    session = client.session
    session[IDP_TOKEN_CLAIMS_SESSION_KEY] = _claims(sub, role)
    session.save()
    return client


def _handle(html: str) -> str:
    match = HANDLE_RE.search(html)
    assert match is not None, html
    return match.group(1)


@pytest.mark.django_db
def test_start_then_get_after_disconnect_does_not_recompute(client, monkeypatch, settings):
    calls = {"n": 0}
    delayed: list[tuple] = []

    def counting_runner(payload: dict) -> dict:
        calls["n"] += 1
        return {"target": payload.get("target"), "seq": calls["n"]}

    monkeypatch.setattr(
        "django_warden_fabric.mcp_asgi.run_audit",
        counting_runner,
    )
    monkeypatch.setattr(
        "django_pyforge.supervisor._runners",
        {("warden", "run_audit"): counting_runner},
    )

    def capture_delay(*args: object, **kwargs: object) -> None:
        delayed.append((args, kwargs))

    monkeypatch.setattr(execute_supervised_run, "apply_async", capture_delay)
    _authed(client, settings)
    started = client.post("/stations/warden/audits/start/", {"target": "."})
    assert started.status_code == HTTPStatus.OK, started.content
    handle = _handle(started.content.decode())
    row = McpHandle.objects.select_related("run").get(handle=handle)
    assert row.run.status == RunState.Status.RUNNING
    assert calls["n"] == 0
    assert delayed

    _args, kwargs = delayed[0]
    # Story 42.2: the enqueue is `apply_async` (it carries the `sub` header and
    # the pre-minted task id), so the positional args live under `args=`.
    execute_supervised_run(*kwargs["args"])
    disconnected = Client()
    _authed(disconnected, settings, sub="op-1")
    first = disconnected.get("/stations/warden/audits/", {"handle": handle})
    second = disconnected.get("/stations/warden/audits/", {"handle": handle})
    assert first.status_code == HTTPStatus.OK
    assert second.status_code == HTTPStatus.OK
    assert b"succeeded" in first.content
    assert first.content == second.content
    assert calls["n"] == 1
    fetched = McpHandle.objects.select_related("run").get(handle=handle)
    assert fetched.run.result == {"target": ".", "seq": 1}


@pytest.mark.django_db
def test_chrome_home_exposes_htmx_start_form(client, settings):
    _authed(client, settings)
    home = client.get("/stations/warden/")
    assert home.status_code == HTTPStatus.OK
    body = home.content.decode()
    assert 'id="warden-audit-start"' in body
    assert 'hx-post="/stations/warden/audits/start/"' in body


@pytest.mark.django_db
def test_get_unknown_handle_is_not_found(client, settings):
    _authed(client, settings)
    missing = client.get("/stations/warden/audits/", {"handle": "no-such-handle"})
    assert missing.status_code == HTTPStatus.NOT_FOUND


def _warden_mcp_host():
    mcp_app = build_warden_mcp_asgi()

    async def application(scope, receive, send):
        register_station_mcp_app("warden", mcp_app)
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
def test_mcp_start_audit_returns_handle(monkeypatch):
    monkeypatch.setattr(execute_supervised_run, "apply_async", lambda *a, **k: None)
    assertion = mint_assertion(sub="agent-10-2", roles=["pyforge:station:warden"], station="warden")
    with TestClient(_warden_mcp_host()) as mcp_client:
        response = mcp_client.post(
            "/stations/warden/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "start_audit",
                    "arguments": {"target": ".", "assertion": assertion},
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
                "mcp-name": "start_audit",
                # Story 42.1: the transport gate verifies before it routes.
                "authorization": f"Bearer {assertion}",
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


@pytest.mark.django_db
def test_start_is_forbidden_without_warden_role(client, settings):
    _authed(client, settings, role="pyforge:station:atlas")
    response = client.post("/stations/warden/audits/start/", {"target": "."})
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.django_db
def test_get_without_matching_sub_is_refused(client, monkeypatch, settings):
    monkeypatch.setattr(execute_supervised_run, "apply_async", lambda *a, **k: None)
    _authed(client, settings, sub="op-1")
    started = client.post("/stations/warden/audits/start/", {"target": "."})
    handle = _handle(started.content.decode())
    other = Client()
    _authed(other, settings, sub="someone-else")
    refused = other.get("/stations/warden/audits/", {"handle": handle})
    assert refused.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.django_db
def test_start_over_the_station_ceiling_is_429_with_retry_after(
    client,
    monkeypatch,
    settings,
):
    """Story 42.2 AC: the portal face refuses a run bound with the SAME status
    the bound declares -- the view does not get to invent its own.
    """
    monkeypatch.setattr(execute_supervised_run, "apply_async", lambda *a, **k: None)
    settings.MAX_QUEUE_DEPTH_PER_STATION = 1
    now = timezone.now()
    RunState.objects.create(
        status=RunState.Status.RUNNING,
        station="warden",
        subject="another-agent",
        started_at=now,
        heartbeat_at=now,
    )
    before = RunState.objects.count()
    _authed(client, settings)

    response = client.post("/stations/warden/audits/start/", {"target": "."})

    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert int(response.headers["Retry-After"]) > 0
    assert RunState.objects.count() == before


@pytest.mark.django_db
def test_start_at_the_per_sub_ceiling_is_409_naming_the_live_runs(
    client,
    monkeypatch,
    settings,
):
    """Story 42.2 AC: 409 with the live run ids, so the operator's next move
    (wait, or `steward revoke --sub`) is in the response.
    """
    monkeypatch.setattr(execute_supervised_run, "apply_async", lambda *a, **k: None)
    settings.MAX_RUNNING_PER_SUB = 1
    settings.MAX_QUEUE_DEPTH_PER_STATION = 100
    _authed(client, settings, sub="op-1")
    started = client.post("/stations/warden/audits/start/", {"target": "."})
    assert started.status_code == HTTPStatus.OK
    live = McpHandle.objects.select_related("run").get(
        handle=_handle(started.content.decode()),
    )

    refused = client.post("/stations/warden/audits/start/", {"target": "."})

    assert refused.status_code == HTTPStatus.CONFLICT
    assert json.loads(refused.content)["run_ids"] == [str(live.run_id)]


def _fresh_subject(prefix: str) -> str:
    """A subject no previous run can have used.

    `TestClient` drives the app through a worker thread whose connection is in
    autocommit, so a row the tool creates is committed OUTSIDE the test's
    transaction and survives every rollback -- this file's
    `test_mcp_start_audit_returns_handle` has always leaked one per run. Story
    42.2's bounds count live rows, so a fixed subject would count those
    leftovers and make the assertion depend on how many times the suite has
    been run against this database. A unique subject makes the count this
    test's own.
    """
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _tool_error_payload(response) -> dict:
    """The projected bound, dug out of the SDK's flattened tool error.

    The SDK answers HTTP 200 with `isError=True` and one text block, and some
    versions prefix it ("Error executing tool ..."), so the JSON is located
    rather than assumed to be the whole string. Locating it is the point of the
    test: if the tool raised a bare `RunBoundExceeded` there would be no JSON
    here at all, only a sentence.
    """
    body = response.json()
    result = body.get("result") or {}
    assert result.get("isError") is True, body
    text = result["content"][0]["text"]
    assert "{" in text, text
    return json.loads(text[text.index("{") :])


def _call_start_audit(mcp_client, assertion: str, call_id: int):
    """One real `tools/call` of `start_audit` through the host dispatch."""
    return mcp_client.post(
        "/stations/warden/mcp",
        json={
            "jsonrpc": "2.0",
            "id": call_id,
            "method": "tools/call",
            "params": {
                "name": "start_audit",
                "arguments": {"target": ".", "assertion": assertion},
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
            "mcp-name": "start_audit",
            "authorization": f"Bearer {assertion}",
        },
    )


def _handle_from_tool_result(response) -> str:
    body = response.json()
    result = body.get("result") or {}
    assert result.get("isError") is False, body
    structured = result.get("structuredContent") or {}
    handle = structured.get("handle")
    if handle is None:
        handle = json.loads(result["content"][0]["text"])["handle"]
    assert handle, body
    return handle


@pytest.mark.django_db
def test_mcp_start_at_the_per_sub_ceiling_projects_the_409_and_run_ids(
    monkeypatch,
    settings,
):
    """Story 42.2 AC 3 on the AGENT surface, which is the surface it exists for.

    A bare `publish_start` here would reach the agent as `Error executing tool
    start_audit` and nothing else: the SDK withholds the text of any exception
    that is not its own `ToolError`. So this drives two real `tools/call`s -- an
    agent looping at its ceiling -- and asserts the projection the portal
    renders is what comes back.

    The bound is reached by the tool's OWN first call rather than by a row this
    test writes: `TestClient` runs the app in a worker thread on its own
    connection, which cannot see a row held open in the test's transaction, so
    a pre-seeded row would leave the ceiling untripped and the test would pass
    for the wrong reason. A fresh subject keeps the count this test's own --
    the worker thread commits outside the test transaction, so rows it creates
    survive rollback (as this file's `test_mcp_start_audit_returns_handle` has
    always done).
    """
    monkeypatch.setattr(execute_supervised_run, "apply_async", lambda *a, **k: None)
    settings.MAX_RUNNING_PER_SUB = 1
    settings.MAX_QUEUE_DEPTH_PER_STATION = 10_000
    subject = _fresh_subject("agent-42-2")
    assertion = mint_assertion(sub=subject, roles=["pyforge:station:warden"], station="warden")

    with TestClient(_warden_mcp_host()) as mcp_client:
        first = _call_start_audit(mcp_client, assertion, 4)
        refused = _call_start_audit(mcp_client, assertion, 5)

    live_run_id = McpHandle.objects.get(handle=_handle_from_tool_result(first)).run_id
    payload = _tool_error_payload(refused)
    assert payload["status"] == int(HTTPStatus.CONFLICT)
    assert payload["error"] == "too many running"
    assert payload["run_ids"] == [str(live_run_id)]
    assert payload["limit"] == 1


@pytest.mark.django_db
def test_mcp_start_at_the_station_ceiling_projects_the_429_and_retry_after(
    monkeypatch,
    settings,
):
    """The 429 bound projects too -- `retry_after` reaches the agent as data,
    and the refusal costs no row.

    The ceiling drops between the two calls so the second is refused whatever
    the station's existing depth: seeding a row instead would be invisible to
    the tool's own connection (see the test above).
    """
    monkeypatch.setattr(execute_supervised_run, "apply_async", lambda *a, **k: None)
    settings.MAX_QUEUE_DEPTH_PER_STATION = 10_000
    settings.MAX_RUNNING_PER_SUB = 10_000
    assertion = mint_assertion(
        sub=_fresh_subject("agent-42-2-b"),
        roles=["pyforge:station:warden"],
        station="warden",
    )

    with TestClient(_warden_mcp_host()) as mcp_client:
        _handle_from_tool_result(_call_start_audit(mcp_client, assertion, 6))
        before = RunState.objects.count()
        settings.MAX_QUEUE_DEPTH_PER_STATION = 1
        refused = _call_start_audit(mcp_client, assertion, 7)

    payload = _tool_error_payload(refused)
    assert payload["status"] == int(HTTPStatus.TOO_MANY_REQUESTS)
    assert payload["error"] == "station queue full"
    assert payload["retry_after"] > 0
    assert RunState.objects.count() == before, "a refused start wrote a row"


def _platform_python_rels() -> list[str]:
    tracked = subprocess.check_output(
        ["git", "diff", "--name-only", "origin/main", "--", "src/platform"],
        cwd=REPO_ROOT,
        text=True,
    )
    untracked = subprocess.check_output(
        [
            "git",
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            "src/platform",
        ],
        cwd=REPO_ROOT,
        text=True,
    )
    rels = {line for line in f"{tracked}\n{untracked}".splitlines() if line.strip()}
    rels.add("src/platform/tests/test_warden_portal_audit_start_get.py")
    return sorted(rels)


def test_platform_diff_has_no_pyforge_import():
    offenders: list[str] = []
    for rel in _platform_python_rels():
        path = REPO_ROOT / rel
        if path.suffix != ".py" or not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            if "pyforge" in names:
                offenders.append(f"{rel}:{node.lineno}")
    assert not offenders
