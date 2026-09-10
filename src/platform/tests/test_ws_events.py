"""Story 48.6 — host ASGI routing and auth for ``/ws/events/``.

Runs in ``platform-ci-test`` where ``langflow`` is intentionally absent (CAP-5).
Stubs Langflow at import time so ``config.asgi.application`` can be exercised
without the factory conda package.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PLATFORM_ROOT = _REPO_ROOT / "src" / "platform"
_SHARED = _REPO_ROOT / "src" / "shared" / "packages"
for _segment in (
    str(_PLATFORM_ROOT),
    str(_SHARED / "django-pyforge" / "src"),
    str(_SHARED / "pyforge-core" / "src"),
    str(_SHARED / "pyforge-steward" / "src"),
):
    if _segment not in sys.path:
        sys.path.insert(0, _segment)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
os.environ.setdefault("COMPONENT_RUNTIME", "local")

# Stub Langflow before langflow_integration.asgi imports it.
_langflow_asgi_app = MagicMock()
_langflow_pkg = MagicMock()
_langflow_pkg.main.create_app.return_value = _langflow_asgi_app
sys.modules.setdefault("langflow", _langflow_pkg)
sys.modules.setdefault("langflow.main", _langflow_pkg.main)

import jwt  # noqa: E402
import pytest  # noqa: E402

pytest.importorskip("channels")

from django_pyforge.assertion.golden import GOLDEN_PRIVATE_PEM  # noqa: E402
from django_pyforge.assertion.schema import ALG  # noqa: E402
from django_pyforge.assertion.schema import CLAIM_AUD  # noqa: E402
from django_pyforge.assertion.schema import CLAIM_DELEGATED_BY  # noqa: E402
from django_pyforge.assertion.schema import CLAIM_EXP  # noqa: E402
from django_pyforge.assertion.schema import CLAIM_IAT  # noqa: E402
from django_pyforge.assertion.schema import CLAIM_ROLES  # noqa: E402
from django_pyforge.assertion.schema import CLAIM_SUB  # noqa: E402
from django_pyforge.assertion.schema import DELEGATED_BY  # noqa: E402
from django_pyforge.assertion.schema import EVENTS_AUDIENCE  # noqa: E402
from django_pyforge.assertion.schema import MAX_TTL_SECONDS  # noqa: E402

import config.asgi as asgi_module  # noqa: E402
from config.asgi import application  # noqa: E402

_CLOSE_UNAUTHORIZED = 4401
_CLOSE_DASHBOARD_MISSING = 4403


class _WsRecorder:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def __call__(self, message: dict) -> None:
        self.messages.append(message)


def _events_token(*, sub: str = "alice") -> str:
    issued = int(datetime.now(tz=UTC).timestamp())
    claims = {
        CLAIM_SUB: sub,
        CLAIM_ROLES: ["pyforge:station:warden"],
        CLAIM_AUD: EVENTS_AUDIENCE,
        CLAIM_IAT: issued,
        CLAIM_EXP: issued + MAX_TTL_SECONDS,
        CLAIM_DELEGATED_BY: DELEGATED_BY,
    }
    return jwt.encode(claims, GOLDEN_PRIVATE_PEM, algorithm=ALG)


async def _drive_websocket(
    path: str,
    *,
    incoming: list[dict] | None = None,
) -> _WsRecorder:
    recorder = _WsRecorder()
    queue = list(incoming or [{"type": "websocket.connect"}])

    async def receive() -> dict:
        if not queue:
            return {"type": "websocket.disconnect", "code": 1000}
        return queue.pop(0)

    scope = {
        "type": "websocket",
        "path": path,
        "query_string": b"",
        "headers": [],
    }
    await application(scope, receive, recorder)
    return recorder


def test_ping_websocket_still_returns_pong():
    async def _run() -> list[dict]:
        recorder = _WsRecorder()
        steps: list[dict] = [
            {"type": "websocket.connect"},
            {"type": "websocket.receive", "text": "ping"},
            {"type": "websocket.disconnect", "code": 1000},
        ]

        async def receive_wrapper() -> dict:
            return steps.pop(0)

        scope = {"type": "websocket", "path": "/ws/ping", "headers": []}
        await application(scope, receive_wrapper, recorder)
        return recorder.messages

    messages = asyncio.run(_run())
    assert any(
        msg.get("type") == "websocket.send" and msg.get("text") == "pong!"
        for msg in messages
    )


def test_events_websocket_rejects_invalid_token():
    recorder = asyncio.run(
        _drive_websocket(
            "/ws/events/",
            incoming=[{"type": "websocket.connect"}],
        ),
    )
    assert any(
        msg.get("type") == "websocket.close" and msg.get("code") == _CLOSE_UNAUTHORIZED
        for msg in recorder.messages
    )


def test_events_websocket_accepts_with_valid_token():
    token = _events_token()
    scope_path = "/ws/events/"

    async def _run() -> _WsRecorder:
        recorder = _WsRecorder()
        steps: list[dict] = [
            {"type": "websocket.connect"},
            {"type": "websocket.disconnect", "code": 1000},
        ]

        async def receive() -> dict:
            return steps.pop(0)

        scope = {
            "type": "websocket",
            "path": scope_path,
            "query_string": f"token={token}".encode(),
            "headers": [],
        }
        await application(scope, receive, recorder)
        return recorder

    recorder = asyncio.run(_run())
    assert any(msg.get("type") == "websocket.accept" for msg in recorder.messages)
    assert not any(
        msg.get("type") == "websocket.close"
        and msg.get("code") in {_CLOSE_UNAUTHORIZED, _CLOSE_DASHBOARD_MISSING}
        for msg in recorder.messages
    )


def test_events_websocket_closes_4403_when_dashboard_extra_missing(monkeypatch):
    def _missing_events_app():
        msg = "dashboard extra absent"
        raise ImportError(msg)

    monkeypatch.setattr(asgi_module, "_load_events_ws_application", _missing_events_app)
    recorder = asyncio.run(
        _drive_websocket(
            "/ws/events/",
            incoming=[{"type": "websocket.connect"}],
        ),
    )
    assert any(
        msg.get("type") == "websocket.close"
        and msg.get("code") == _CLOSE_DASHBOARD_MISSING
        for msg in recorder.messages
    )
