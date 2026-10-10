"""Story 87.3: herald webhook on mcp-host sidecar and host forward."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import importlib
import json
import logging
import sys
import time
from http import HTTPStatus
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django_pyforge.flags import evaluate_boolean
from django_pyforge.sidecar_forward import HERALD_WEBHOOK_SIDECAR_FLAG
from django_pyforge.sidecar_forward import dispatch_herald_webhook_forward
from starlette.testclient import TestClient

_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLATFORM_ROOT))

from mcp_host.app import app as mcp_host_app  # noqa: E402

_ON_SHIP_PATH = "/stations/herald/api/v1/webhooks/on-ship"


def _herald_modules():
    webhook = importlib.import_module("pyforge.herald.webhook")
    webhook_host = importlib.import_module("pyforge.herald.webhook_host")
    return webhook, webhook_host


def _sign(secret: bytes, timestamp: str, body: bytes) -> str:
    return (
        "sha256="
        + hmac.new(
            secret,
            timestamp.encode("ascii") + b"." + body,
            hashlib.sha256,
        ).hexdigest()
    )


def _timestamp() -> str:
    return str(int(time.time()))


def _signed_headers(secret: bytes, body: bytes) -> dict[str, str]:
    ts = _timestamp()
    return {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": _sign(secret, ts, body),
        "X-Hub-Timestamp": ts,
    }


@pytest.fixture(autouse=True)
def _reset_herald_application_cache():
    _, webhook_host = _herald_modules()
    webhook_host._application = None  # noqa: SLF001
    yield
    webhook_host._application = None  # noqa: SLF001


@pytest.fixture(scope="module")
def mcp_client():
    with TestClient(mcp_host_app) as client:
        yield client


def test_mcp_host_sidecar_webhook_signed_on_ship(
    mcp_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    webhook, webhook_host = _herald_modules()
    monkeypatch.setenv(webhook_host.REPO_ROOT_ENV_VAR, str(tmp_path))
    monkeypatch.setenv(webhook.SECRET_ENV_VAR, "shared-secret")
    body = json.dumps({"station": "warden"}).encode("utf-8")
    response = mcp_client.post(
        webhook.ON_SHIP_PATH,
        content=body,
        headers=_signed_headers(b"shared-secret", body),
    )
    assert response.status_code == HTTPStatus.CREATED


def test_mcp_host_sidecar_webhook_bad_signature(
    mcp_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    webhook, webhook_host = _herald_modules()
    monkeypatch.setenv(webhook_host.REPO_ROOT_ENV_VAR, str(tmp_path))
    monkeypatch.setenv(webhook.SECRET_ENV_VAR, "shared-secret")
    body = json.dumps({"station": "warden"}).encode("utf-8")
    headers = _signed_headers(b"shared-secret", body)
    headers["X-Hub-Signature-256"] = "sha256=deadbeef"
    response = mcp_client.post(webhook.ON_SHIP_PATH, content=body, headers=headers)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_mcp_host_sidecar_webhook_get_is_405(
    mcp_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    webhook, webhook_host = _herald_modules()
    monkeypatch.setenv(webhook_host.REPO_ROOT_ENV_VAR, str(tmp_path))
    monkeypatch.setenv(webhook.SECRET_ENV_VAR, "shared-secret")
    response = mcp_client.get(webhook.ON_SHIP_PATH)
    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


def test_mcp_host_health_and_unknown_path_unchanged(mcp_client: TestClient) -> None:
    assert mcp_client.get("/health").status_code == HTTPStatus.OK
    assert mcp_client.get("/stations/nope/mcp").status_code == HTTPStatus.NOT_FOUND


def test_mcp_host_sidecar_herald_absent_returns_404_json(
    mcp_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = importlib.import_module

    def _import(name: str, *args, **kwargs):
        if name == "pyforge.herald.webhook_host":
            msg = "pyforge.herald.webhook_host"
            raise ModuleNotFoundError(msg)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", _import)
    response = mcp_client.post(_ON_SHIP_PATH, content=b"{}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "pyforge.herald" in response.json()["detail"]
    assert mcp_client.get("/health").status_code == HTTPStatus.OK
    init = mcp_client.post(
        "/stations/atlas/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "t", "version": "0"},
            },
        },
        headers={"content-type": "application/json"},
    )
    assert init.status_code < HTTPStatus.INTERNAL_SERVER_ERROR


def test_mcp_host_sidecar_missing_secret_503(
    mcp_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    webhook, webhook_host = _herald_modules()
    monkeypatch.setenv(webhook_host.REPO_ROOT_ENV_VAR, str(tmp_path))
    monkeypatch.delenv(webhook.SECRET_ENV_VAR, raising=False)
    response = mcp_client.post(webhook.ON_SHIP_PATH, content=b"{}")
    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert webhook.SECRET_ENV_VAR in response.json()["detail"]
    assert mcp_client.get("/health").status_code == HTTPStatus.OK


def test_mcp_host_sidecar_missing_repo_root_503(
    mcp_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    webhook, webhook_host = _herald_modules()
    monkeypatch.setenv(webhook.SECRET_ENV_VAR, "shared-secret")
    monkeypatch.delenv(webhook_host.REPO_ROOT_ENV_VAR, raising=False)
    response = mcp_client.post(webhook.ON_SHIP_PATH, content=b"{}")
    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert webhook_host.REPO_ROOT_ENV_VAR in response.json()["detail"]


class _CaptureClient:
    last: dict | None = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def request(self, method, url, *, content, headers):
        _CaptureClient.last = {
            "method": method,
            "url": url,
            "content": content,
            "headers": headers,
        }
        response = MagicMock()
        response.status_code = 201
        response.content = b'{"forwarded":true}'
        response.headers = {"content-type": "application/json"}
        return response


def _webhook_scope(body: bytes, extra_headers: list[tuple[bytes, bytes]] | None = None):
    headers = [
        (b"content-type", b"application/json"),
        (b"x-hub-signature-256", b"sha256=abc"),
        (b"x-hub-timestamp", b"1"),
        (b"authorization", b"Bearer secret"),
        (b"cookie", b"s=1"),
    ]
    if extra_headers:
        headers.extend(extra_headers)
    return {
        "type": "http",
        "path": "/stations/herald/api/v1/webhooks/on-ship",
        "raw_path": b"/stations/herald/api/v1/webhooks/on-ship",
        "query_string": b"x=1",
        "method": "POST",
        "headers": headers,
    }


def test_host_forwards_webhook_to_sidecar(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_HOST_SIDECAR_BASE_URL", "http://127.0.0.1:8090")
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    body = b"payload-bytes"
    sent: list[dict] = []

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        sent.append(message)

    async def _run():
        with patch("httpx.AsyncClient", return_value=_CaptureClient()):
            return await dispatch_herald_webhook_forward(
                _webhook_scope(body),
                receive,
                send,
            )

    assert asyncio.run(_run()) is True
    assert _CaptureClient.last is not None
    assert _CaptureClient.last["method"] == "POST"
    assert _CaptureClient.last["url"] == (
        "http://127.0.0.1:8090/stations/herald/api/v1/webhooks/on-ship?x=1"
    )
    assert _CaptureClient.last["content"] == body
    lowered = {k.lower(): v for k, v in _CaptureClient.last["headers"].items()}
    assert lowered["content-type"] == "application/json"
    assert lowered["x-hub-signature-256"] == "sha256=abc"
    assert lowered["x-hub-timestamp"] == "1"
    assert "authorization" not in lowered
    assert "cookie" not in lowered
    start = next(m for m in sent if m["type"] == "http.response.start")
    assert start["status"] == HTTPStatus.CREATED


def test_host_forward_sidecar_down_one_error_log(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("MCP_HOST_SIDECAR_BASE_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    sent: list[dict] = []

    async def receive():
        return {"type": "http.request", "body": b"x", "more_body": False}

    async def send(message):
        sent.append(message)

    async def _run():
        with caplog.at_level(logging.ERROR):
            await dispatch_herald_webhook_forward(_webhook_scope(b"x"), receive, send)

    asyncio.run(_run())
    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(errors) == 1
    assert "http://127.0.0.1:1" in errors[0].getMessage()
    start = next(m for m in sent if m["type"] == "http.response.start")
    assert start["status"] == HTTPStatus.BAD_GATEWAY


def test_host_does_not_forward_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_HOST_SIDECAR_BASE_URL", "http://127.0.0.1:8090")
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "production")
    monkeypatch.setattr(
        "django_pyforge.sidecar_forward.evaluate_boolean",
        lambda key, default=False: False,
    )

    async def receive():
        return {"type": "http.request", "body": b"x", "more_body": False}

    async def send(message):
        msg = "should not forward"
        raise AssertionError(msg)

    async def _run():
        return await dispatch_herald_webhook_forward(
            _webhook_scope(b"x"),
            receive,
            send,
        )

    assert asyncio.run(_run()) is False


def test_host_skips_forward_for_non_webhook_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_HOST_SIDECAR_BASE_URL", "http://127.0.0.1:8090")
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    scope = {
        "type": "http",
        "path": "/stations/herald/api/v1/health",
        "method": "GET",
        "headers": [],
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        msg = "should not forward health"
        raise AssertionError(msg)

    async def _run():
        return await dispatch_herald_webhook_forward(scope, receive, send)

    assert asyncio.run(_run()) is False


def test_sidecar_forward_does_not_import_pyforge_in_platform() -> None:
    asgi_source = (_PLATFORM_ROOT / "config" / "asgi.py").read_text(encoding="utf-8")
    assert "import pyforge" not in asgi_source
    assert "from pyforge" not in asgi_source
    mcp_source = (_PLATFORM_ROOT / "mcp_host" / "app.py").read_text(encoding="utf-8")
    assert "import pyforge" not in mcp_source
    assert "from pyforge" not in mcp_source


def test_herald_webhook_sidecar_flag_registered() -> None:
    assert HERALD_WEBHOOK_SIDECAR_FLAG == "pyforge.steward.herald_webhook_sidecar"
    assert isinstance(
        evaluate_boolean(HERALD_WEBHOOK_SIDECAR_FLAG, default=False),
        bool,
    )
