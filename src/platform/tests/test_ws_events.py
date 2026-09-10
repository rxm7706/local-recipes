"""Story 48.6 — host ASGI routing and auth for ``/ws/events/``."""

from __future__ import annotations

import asyncio
from datetime import UTC
from datetime import datetime

import jwt
import pytest
from django_pyforge.assertion.golden import GOLDEN_PRIVATE_PEM
from django_pyforge.assertion.golden import GOLDEN_PUBLIC_PEM
from django_pyforge.assertion.schema import ALG
from django_pyforge.assertion.schema import CLAIM_AUD
from django_pyforge.assertion.schema import CLAIM_DELEGATED_BY
from django_pyforge.assertion.schema import CLAIM_EXP
from django_pyforge.assertion.schema import CLAIM_IAT
from django_pyforge.assertion.schema import CLAIM_ROLES
from django_pyforge.assertion.schema import CLAIM_SUB
from django_pyforge.assertion.schema import DELEGATED_BY
from django_pyforge.assertion.schema import EVENTS_AUDIENCE
from django_pyforge.assertion.schema import MAX_TTL_SECONDS

from config.asgi import application


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
    async def receive() -> dict:
        return {"type": "websocket.receive", "text": "ping"}

    async def _run() -> list[dict]:
        recorder = _WsRecorder()
        connect_seen = False

        async def receive_wrapper() -> dict:
            nonlocal connect_seen
            if not connect_seen:
                connect_seen = True
                return {"type": "websocket.connect"}
            return await receive()

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
        msg.get("type") == "websocket.close" and msg.get("code") == 4401
        for msg in recorder.messages
    )


def test_events_websocket_accepts_with_valid_token():
    token = _events_token()
    scope_path = "/ws/events/"

    async def _run() -> _WsRecorder:
        recorder = _WsRecorder()
        steps = [{"type": "websocket.connect"}, {"type": "websocket.disconnect", "code": 1000}]

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
        msg.get("type") == "websocket.close" and msg.get("code") in {4401, 4403}
        for msg in recorder.messages
    )


def test_events_websocket_closes_4403_when_dashboard_extra_missing(monkeypatch):
    import config.asgi as asgi_module

    def _missing_events_app():
        raise ImportError("dashboard extra absent")

    monkeypatch.setattr(asgi_module, "_load_events_ws_application", _missing_events_app)
    recorder = asyncio.run(
        _drive_websocket(
            "/ws/events/",
            incoming=[{"type": "websocket.connect"}],
        ),
    )
    assert any(
        msg.get("type") == "websocket.close" and msg.get("code") == 4403
        for msg in recorder.messages
    )
