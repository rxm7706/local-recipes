"""Unit tests for ``pyforge.herald.station_api`` (Story 19.1 / 29.2 wiring)."""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

import pytest

from pyforge.herald import station_api


class _RecordingApp:
    def __init__(self) -> None:
        self.mounted: list[tuple[str, Any]] = []

    def mount(self, path: str, asgi: Any) -> None:
        self.mounted.append((path, asgi))


def test_attach_webhook_asgi_wires_deck_exports_and_mounts_webhook(monkeypatch: pytest.MonkeyPatch) -> None:
    wired: list[Any] = []

    deck_routes = ModuleType("django_herald_portal.deck_export_routes")

    def wire_deck_export_routes(app: Any) -> None:
        wired.append(app)

    deck_routes.wire_deck_export_routes = wire_deck_export_routes  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "django_herald_portal.deck_export_routes", deck_routes)

    app = _RecordingApp()
    station_api.attach_webhook_asgi(app)
    assert wired == [app]
    assert len(app.mounted) == 1
    assert app.mounted[0][0] == "/"
    assert isinstance(app.mounted[0][1], station_api._LazyWebhookASGI)


def test_lazy_webhook_builds_application_once(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    build_calls = 0

    class _Inner:
        async def __call__(self, scope, receive, send) -> None:
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})

    def fake_build(*_args, **_kwargs):
        nonlocal build_calls
        build_calls += 1
        return _Inner()

    import pyforge.herald.webhook as webhook_mod
    import pyforge.herald.webhook_host as webhook_host_mod

    monkeypatch.setattr(webhook_host_mod, "build_application", fake_build)
    monkeypatch.setattr(webhook_host_mod, "_resolve_repo_root", lambda: "/tmp/repo")
    monkeypatch.setattr(webhook_mod, "resolve_webhook_secret", lambda: "secret")

    lazy = station_api._LazyWebhookASGI()
    scope = {"type": "http", "method": "GET", "path": "/"}

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    sent: list[dict] = []

    async def send(message):
        sent.append(message)

    async def _run() -> None:
        await lazy(scope, receive, send)
        await lazy(scope, receive, send)

    asyncio.run(_run())
    assert build_calls == 1
    assert sent[0]["status"] == 204
