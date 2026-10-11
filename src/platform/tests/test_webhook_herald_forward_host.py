"""Story 87.4 — host webhook forward hardening through config.asgi.application."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import importlib
import json
import os
import sys
import time
import tomllib
from http import HTTPStatus
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django_pyforge.flags import ENV_FLAGD_PATH
from django_pyforge.flags import ENV_FLAGS_PATH
from django_pyforge.flags import configure_file_provider
from django_pyforge.sidecar_forward import HERALD_WEBHOOK_ON_PR_CLOSE_PATH
from django_pyforge.sidecar_forward import HERALD_WEBHOOK_ON_SHIP_PATH
from django_pyforge.sidecar_forward import MAX_BODY_BYTES
from django_pyforge.sidecar_forward import MAX_BODY_MESSAGES
from httpx import ASGITransport
from httpx import AsyncClient
from openfeature import api

_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _PLATFORM_ROOT.parents[1]

_langflow_asgi_app = MagicMock()
_langflow_pkg = MagicMock()
_langflow_pkg.main.create_app.return_value = _langflow_asgi_app
sys.modules.setdefault("langflow", _langflow_pkg)
sys.modules.setdefault("langflow.main", _langflow_pkg.main)

from config.asgi import application  # noqa: E402


class _FakeSidecarClient:
    requests: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def request(self, method, url, *, content, headers):
        _FakeSidecarClient.requests.append(
            {
                "method": method,
                "url": url,
                "content": content,
                "headers": headers,
            },
        )
        response = MagicMock()
        response.status_code = 201
        response.content = b'{"forwarded":true}'
        response.headers = {"content-type": "application/json"}
        return response


def _herald_webhook_module():
    return importlib.import_module("pyforge.herald.webhook")


def _sign(secret: bytes, timestamp: str, body: bytes) -> str:
    return (
        "sha256="
        + hmac.new(
            secret,
            timestamp.encode("ascii") + b"." + body,
            hashlib.sha256,
        ).hexdigest()
    )


def _signed_post_headers(
    body: bytes,
    secret: bytes = b"shared-secret",
) -> dict[str, str]:
    ts = str(int(time.time()))
    return {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": _sign(secret, ts, body),
        "X-Hub-Timestamp": ts,
        "Authorization": "Bearer secret",
        "Cookie": "s=1",
    }


def _sidecar_flag_tree(*, on: bool) -> bytes:
    return json.dumps(
        {
            "flags": {
                "pyforge.steward.herald_webhook_sidecar": {
                    "state": "ENABLED",
                    "variants": {"on": True, "off": False},
                    "defaultVariant": "on" if on else "off",
                },
            },
        },
    ).encode()


_OTHER_WEBHOOK_PATH = "/stations/herald/api/v1/webhooks/other"
_DISCONNECT_RECEIVE_CALLS = 2


@pytest.fixture
def reset_herald_webhook_host_app(monkeypatch: pytest.MonkeyPatch):
    webhook_host = importlib.import_module("pyforge.herald.webhook_host")
    monkeypatch.setattr(webhook_host, "_application", None, raising=False)
    yield
    monkeypatch.setattr(webhook_host, "_application", None, raising=False)


@pytest.fixture
def forward_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _FakeSidecarClient.requests = []
    monkeypatch.setenv("MCP_HOST_SIDECAR_BASE_URL", "http://127.0.0.1:8090")
    monkeypatch.setenv(ENV_FLAGS_PATH, str(tmp_path / "unused.json"))
    monkeypatch.setenv(ENV_FLAGD_PATH, str(tmp_path / "unused.json"))
    tree = tmp_path / "on.json"
    tree.write_bytes(_sidecar_flag_tree(on=True))
    configure_file_provider(tree)
    yield
    api.clear_providers()


async def _asgi_request(
    path: str,
    *,
    method: str = "POST",
    content: bytes = b"",
    headers: dict[str, str] | None = None,
    query_string: bytes = b"",
) -> tuple[int, bytes, dict[str, str]]:
    hdrs = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    sent: list[dict] = []

    async def receive():
        return {"type": "http.request", "body": content, "more_body": False}

    async def send(message):
        sent.append(message)

    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"spec_version": "2.3", "version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode("latin-1"),
        "query_string": query_string,
        "headers": hdrs,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    await application(scope, receive, send)
    start = next(m for m in sent if m["type"] == "http.response.start")
    body_msg = next(m for m in sent if m["type"] == "http.response.body")
    resp_headers = {
        k.decode("latin-1").lower(): v.decode("latin-1")
        for k, v in start.get("headers", [])
    }
    return start["status"], body_msg["body"], resp_headers


def test_forwarder_literals_match_herald_constants() -> None:
    webhook = _herald_webhook_module()
    assert HERALD_WEBHOOK_ON_SHIP_PATH == webhook.ON_SHIP_PATH
    assert HERALD_WEBHOOK_ON_PR_CLOSE_PATH == webhook.ON_PR_CLOSE_PATH
    assert MAX_BODY_BYTES == webhook.MAX_BODY_BYTES
    assert MAX_BODY_MESSAGES == webhook.MAX_BODY_MESSAGES


@pytest.mark.parametrize(
    "path",
    [
        "/stations/herald/api/v1/webhooks/../../../../marshal/mcp",
        "/stations/herald/api/v1/webhooks/%2e%2e/%2e%2e/%2e%2e/%2e%2e/marshal/mcp",
        "/stations/herald/api/v1/webhooks/on-ship%3Fx=1",
        "/stations/herald/api/v1/webhooks/on-ship%23frag",
        "/stations/herald/api/v1/webhooks/on-ship%0d%0aInjected: 1",
        "/stations/herald/api/v1/webhooks/",
        "/stations/herald/api/v1/webhooks/other",
    ],
)
def test_host_rejects_non_allowlisted_webhook_paths(
    forward_env,
    path: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def _run():
        with (
            patch("httpx.AsyncClient", return_value=_FakeSidecarClient()),
            caplog.at_level("ERROR"),
        ):
            status, body, _ = await _asgi_request(path, content=b"x")
        return status, body

    status, body = asyncio.run(_run())
    assert status == HTTPStatus.NOT_FOUND
    assert json.loads(body) == {"detail": "Not Found"}
    assert _FakeSidecarClient.requests == []
    for record in caplog.records:
        assert path not in record.getMessage()


async def _post_via_transport(
    path: str,
    *,
    content: bytes,
    headers: dict[str, str],
    params: dict[str, str] | None = None,
) -> Any:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.post(path, content=content, headers=headers, params=params)


def test_host_forwards_only_literal_paths_no_query(forward_env) -> None:
    body = b'{"x":1}'
    headers = _signed_post_headers(body)

    async def _run():
        with patch("httpx.AsyncClient", return_value=_FakeSidecarClient()):
            return await _post_via_transport(
                HERALD_WEBHOOK_ON_SHIP_PATH,
                content=body,
                headers=headers,
                params={"x": "1"},
            )

    response = asyncio.run(_run())
    assert response.status_code == HTTPStatus.CREATED
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"forwarded": True}
    assert len(_FakeSidecarClient.requests) == 1
    assert _FakeSidecarClient.requests[0]["url"] == (
        "http://127.0.0.1:8090/stations/herald/api/v1/webhooks/on-ship"
    )
    assert _FakeSidecarClient.requests[0]["content"] == body
    req_headers = _FakeSidecarClient.requests[0]["headers"]
    assert set(req_headers.keys()) == {
        "content-type",
        "x-hub-signature-256",
        "x-hub-timestamp",
    }
    assert req_headers["content-type"] == headers["Content-Type"]
    assert req_headers["x-hub-signature-256"] == headers["X-Hub-Signature-256"]
    assert req_headers["x-hub-timestamp"] == headers["X-Hub-Timestamp"]


def test_host_forwards_on_pr_close(forward_env) -> None:
    body = b"{}"
    headers = _signed_post_headers(body)

    async def _run():
        with patch("httpx.AsyncClient", return_value=_FakeSidecarClient()):
            return await _post_via_transport(
                HERALD_WEBHOOK_ON_PR_CLOSE_PATH,
                content=body,
                headers=headers,
            )

    response = asyncio.run(_run())
    assert response.status_code == HTTPStatus.CREATED
    assert response.json() == {"forwarded": True}
    assert _FakeSidecarClient.requests[0]["url"].endswith("/on-pr-close")
    req_headers = _FakeSidecarClient.requests[0]["headers"]
    assert set(req_headers.keys()) == {
        "content-type",
        "x-hub-signature-256",
        "x-hub-timestamp",
    }


def test_host_body_byte_cap_returns_413(forward_env) -> None:
    over = b"x" * (MAX_BODY_BYTES + 1)

    async def _run():
        with patch("httpx.AsyncClient", return_value=_FakeSidecarClient()):
            return await _asgi_request(HERALD_WEBHOOK_ON_SHIP_PATH, content=over)

    status, body, _ = asyncio.run(_run())
    assert status == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    assert str(MAX_BODY_BYTES) in json.loads(body)["error"]
    assert _FakeSidecarClient.requests == []


def test_host_body_message_cap_returns_413(forward_env) -> None:
    messages = [
        {"type": "http.request", "body": b"", "more_body": True}
        for _ in range(MAX_BODY_MESSAGES)
    ]
    messages.append({"type": "http.request", "body": b"", "more_body": False})
    index = 0

    async def _run():
        nonlocal index

        async def receive():
            nonlocal index
            msg = messages[index]
            index += 1
            return msg

        sent: list[dict] = []

        async def send(message):
            sent.append(message)

        scope = {
            "type": "http",
            "method": "POST",
            "path": HERALD_WEBHOOK_ON_SHIP_PATH,
            "query_string": b"",
            "headers": [],
        }
        with patch("httpx.AsyncClient", return_value=_FakeSidecarClient()):
            await application(scope, receive, send)
        start = next(m for m in sent if m["type"] == "http.response.start")
        body_msg = next(m for m in sent if m["type"] == "http.response.body")
        return start["status"], body_msg["body"]

    status, body = asyncio.run(_run())
    assert status == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    assert str(MAX_BODY_MESSAGES) in json.loads(body)["error"]


def test_host_forwards_exactly_max_body_bytes(forward_env) -> None:
    body = b"x" * MAX_BODY_BYTES

    async def _run():
        with patch("httpx.AsyncClient", return_value=_FakeSidecarClient()):
            return await _asgi_request(HERALD_WEBHOOK_ON_SHIP_PATH, content=body)

    status, _, _ = asyncio.run(_run())
    assert status == HTTPStatus.CREATED
    assert len(_FakeSidecarClient.requests) == 1


def test_client_disconnect_after_partial_body_ends_read(forward_env) -> None:
    receive_count = 0

    async def _run():
        nonlocal receive_count

        async def receive():
            nonlocal receive_count
            receive_count += 1
            if receive_count == 1:
                return {
                    "type": "http.request",
                    "body": b"x",
                    "more_body": True,
                }
            return {"type": "http.disconnect"}

        sent: list[dict] = []

        async def send(message):
            sent.append(message)

        scope = {
            "type": "http",
            "method": "POST",
            "path": HERALD_WEBHOOK_ON_SHIP_PATH,
            "query_string": b"",
            "headers": [],
        }
        with patch("httpx.AsyncClient", return_value=_FakeSidecarClient()):
            await asyncio.wait_for(application(scope, receive, send), timeout=1.0)
        return sent, receive_count

    sent, count = asyncio.run(_run())
    assert count == _DISCONNECT_RECEIVE_CALLS
    assert _FakeSidecarClient.requests == []
    assert not any(m["type"] == "http.response.start" for m in sent)


def test_non_request_message_ends_body_read(forward_env) -> None:
    receive_count = 0

    async def _run():
        nonlocal receive_count

        async def receive():
            nonlocal receive_count
            receive_count += 1
            if receive_count == 1:
                return {
                    "type": "http.request",
                    "body": b"x",
                    "more_body": True,
                }
            return {"type": "lifespan.startup"}

        sent: list[dict] = []

        async def send(message):
            sent.append(message)

        scope = {
            "type": "http",
            "method": "POST",
            "path": HERALD_WEBHOOK_ON_SHIP_PATH,
            "query_string": b"",
            "headers": [],
        }
        with patch("httpx.AsyncClient", return_value=_FakeSidecarClient()):
            await asyncio.wait_for(application(scope, receive, send), timeout=1.0)
        return sent, receive_count

    sent, count = asyncio.run(_run())
    assert count == _DISCONNECT_RECEIVE_CALLS
    assert _FakeSidecarClient.requests == []
    assert not any(m["type"] == "http.response.start" for m in sent)


def test_forward_inactive_unknown_path_reaches_in_process_herald(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    reset_herald_webhook_host_app,
) -> None:
    _FakeSidecarClient.requests = []
    monkeypatch.setenv("MCP_HOST_SIDECAR_BASE_URL", "http://127.0.0.1:8090")
    monkeypatch.setenv(ENV_FLAGS_PATH, str(tmp_path / "unused.json"))
    monkeypatch.setenv(ENV_FLAGD_PATH, str(tmp_path / "unused.json"))
    tree = tmp_path / "off.json"
    tree.write_bytes(_sidecar_flag_tree(on=False))
    configure_file_provider(tree)
    webhook, webhook_host = (
        importlib.import_module("pyforge.herald.webhook"),
        importlib.import_module("pyforge.herald.webhook_host"),
    )
    monkeypatch.setenv(webhook_host.REPO_ROOT_ENV_VAR, str(tmp_path))
    monkeypatch.setenv(webhook.SECRET_ENV_VAR, "shared-secret")

    async def _run():
        with patch("httpx.AsyncClient", return_value=_FakeSidecarClient()):
            return await _post_via_transport(
                _OTHER_WEBHOOK_PATH,
                content=b"{}",
                headers={},
            )

    response = asyncio.run(_run())
    api.clear_providers()
    assert _FakeSidecarClient.requests == []
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "no such webhook route" in response.json()["error"]


def test_forward_inactive_unknown_path_herald_absent_uses_story_87_1(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _FakeSidecarClient.requests = []
    monkeypatch.delenv("MCP_HOST_SIDECAR_BASE_URL", raising=False)
    monkeypatch.setenv(ENV_FLAGS_PATH, str(tmp_path / "unused.json"))
    monkeypatch.setenv(ENV_FLAGD_PATH, str(tmp_path / "unused.json"))
    tree = tmp_path / "on.json"
    tree.write_bytes(_sidecar_flag_tree(on=True))
    configure_file_provider(tree)

    class _HeraldAbsentFinder:
        def find_spec(self, fullname, path, target=None):
            if fullname == "pyforge.herald" or fullname.startswith("pyforge.herald."):
                raise ModuleNotFoundError(name=fullname)

    finder = _HeraldAbsentFinder()
    sys.meta_path.insert(0, finder)
    try:

        async def _run():
            with patch("httpx.AsyncClient", return_value=_FakeSidecarClient()):
                return await _post_via_transport(
                    _OTHER_WEBHOOK_PATH,
                    content=b"{}",
                    headers={},
                )

        response = asyncio.run(_run())
    finally:
        sys.meta_path.remove(finder)
        api.clear_providers()
    assert _FakeSidecarClient.requests == []
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "pyforge.herald" in response.json()["detail"]


def test_flag_off_reaches_in_process_herald(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    reset_herald_webhook_host_app,
) -> None:
    _FakeSidecarClient.requests = []
    monkeypatch.setenv("MCP_HOST_SIDECAR_BASE_URL", "http://127.0.0.1:8090")
    monkeypatch.setenv(ENV_FLAGS_PATH, str(tmp_path / "unused.json"))
    monkeypatch.setenv(ENV_FLAGD_PATH, str(tmp_path / "unused.json"))
    tree = tmp_path / "off.json"
    tree.write_bytes(_sidecar_flag_tree(on=False))
    configure_file_provider(tree)
    webhook, webhook_host = (
        importlib.import_module("pyforge.herald.webhook"),
        importlib.import_module("pyforge.herald.webhook_host"),
    )
    monkeypatch.setenv(webhook_host.REPO_ROOT_ENV_VAR, str(tmp_path))
    monkeypatch.setenv(webhook.SECRET_ENV_VAR, "shared-secret")
    body = json.dumps({"station": "warden"}).encode()
    headers = _signed_post_headers(body)

    async def _run():
        transport = ASGITransport(app=application)
        base = "http://testserver"
        async with AsyncClient(transport=transport, base_url=base) as client:
            with patch("httpx.AsyncClient", return_value=_FakeSidecarClient()):
                return await client.post(
                    webhook.ON_SHIP_PATH,
                    content=body,
                    headers=headers,
                )

    response = asyncio.run(_run())
    api.clear_providers()
    assert _FakeSidecarClient.requests == []
    assert response.status_code == HTTPStatus.CREATED


def test_host_unset_sidecar_url_does_not_forward(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    reset_herald_webhook_host_app,
) -> None:
    _FakeSidecarClient.requests = []
    monkeypatch.delenv("MCP_HOST_SIDECAR_BASE_URL", raising=False)
    monkeypatch.setenv(ENV_FLAGS_PATH, str(tmp_path / "unused.json"))
    monkeypatch.setenv(ENV_FLAGD_PATH, str(tmp_path / "unused.json"))
    tree = tmp_path / "on.json"
    tree.write_bytes(_sidecar_flag_tree(on=True))
    configure_file_provider(tree)
    webhook, webhook_host = (
        importlib.import_module("pyforge.herald.webhook"),
        importlib.import_module("pyforge.herald.webhook_host"),
    )
    monkeypatch.setenv(webhook_host.REPO_ROOT_ENV_VAR, str(tmp_path))
    monkeypatch.setenv(webhook.SECRET_ENV_VAR, "shared-secret")
    body = json.dumps({"station": "warden"}).encode()
    headers = _signed_post_headers(body)

    async def _run():
        with patch("httpx.AsyncClient", return_value=_FakeSidecarClient()):
            return await _post_via_transport(
                webhook.ON_SHIP_PATH,
                content=body,
                headers=headers,
            )

    response = asyncio.run(_run())
    api.clear_providers()
    assert _FakeSidecarClient.requests == []
    assert response.status_code == HTTPStatus.CREATED


def test_flag_on_skips_openapi_and_health(forward_env) -> None:
    async def _run():
        transport = ASGITransport(app=application)
        base = "http://testserver"
        async with AsyncClient(transport=transport, base_url=base) as client:
            with patch("httpx.AsyncClient", return_value=_FakeSidecarClient()):
                o = await client.get("/stations/herald/api/v1/openapi.json")
                h = await client.get("/stations/herald/api/v1/health")
        return o, h

    openapi, health = asyncio.run(_run())
    assert openapi.status_code == HTTPStatus.OK
    assert health.status_code == HTTPStatus.OK
    assert _FakeSidecarClient.requests == []


def test_mcp_host_serve_task_pythonpath_and_bind() -> None:
    pixi_path = _REPO_ROOT / "pixi.toml"
    data = tomllib.loads(pixi_path.read_text(encoding="utf-8"))
    task = data["feature"]["mcp-host"]["tasks"]["mcp-host-serve"]
    assert "--host 127.0.0.1 --port 8090" in task["cmd"]
    cwd = _REPO_ROOT / task["cwd"]
    raw_path = task["env"]["PYTHONPATH"]
    project_root = Path(os.environ.get("PIXI_PROJECT_ROOT", str(_REPO_ROOT)))
    entries = [
        Path(p.replace("$PIXI_PROJECT_ROOT", str(project_root)))
        for p in raw_path.split(":")
    ]
    for entry in entries:
        assert entry.is_dir(), entry
    assert (entries[0] / "mcp_host").is_dir()
    assert (entries[1] / "django_pyforge").is_dir()
    assert (entries[2] / "django_marshal_portal").is_dir()
    assert cwd == project_root / "src" / "platform"
