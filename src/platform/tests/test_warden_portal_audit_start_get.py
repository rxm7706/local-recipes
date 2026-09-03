"""Story 10.2 — HTMX start/get one audit through PortalClient (FR-10 / FR-12)."""

from __future__ import annotations

import ast
import json
import re
import subprocess
from http import HTTPStatus
from pathlib import Path

import pytest
from django.test import Client
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


def _authed(client: Client, settings, *, sub: str = "op-1", role: str = "warden") -> Client:
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

    monkeypatch.setattr(execute_supervised_run, "delay", capture_delay)
    _authed(client, settings)
    started = client.post("/stations/warden/audits/start/", {"target": "."})
    assert started.status_code == HTTPStatus.OK, started.content
    handle = _handle(started.content.decode())
    row = McpHandle.objects.select_related("run").get(handle=handle)
    assert row.run.status == RunState.Status.RUNNING
    assert calls["n"] == 0
    assert delayed

    args, _kwargs = delayed[0]
    execute_supervised_run(*args)
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
    monkeypatch.setattr(execute_supervised_run, "delay", lambda *a, **k: None)
    assertion = mint_assertion(sub="agent-10-2", roles=["warden"], station="warden")
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
    _authed(client, settings, role="atlas")
    response = client.post("/stations/warden/audits/start/", {"target": "."})
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.django_db
def test_get_without_matching_sub_is_refused(client, monkeypatch, settings):
    monkeypatch.setattr(execute_supervised_run, "delay", lambda *a, **k: None)
    _authed(client, settings, sub="op-1")
    started = client.post("/stations/warden/audits/start/", {"target": "."})
    handle = _handle(started.content.decode())
    other = Client()
    _authed(other, settings, sub="someone-else")
    refused = other.get("/stations/warden/audits/", {"handle": handle})
    assert refused.status_code == HTTPStatus.FORBIDDEN


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
