"""Story 29.2 — deck export list/stream routes and refresh projection."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC
from datetime import datetime
from http import HTTPStatus
from pathlib import Path

import pytest
from django.test import override_settings
from django_herald_portal.models import DeckExport
from django_pyforge.assertion.client import PortalClient
from django_pyforge.assertion.golden import GOLDEN_PRIVATE_PEM
from django_pyforge.assertion.golden import GOLDEN_PUBLIC_PEM
from django_pyforge.roles import prefixed_station
from httpx import ASGITransport
from httpx import AsyncClient

from config.station_api import station_application

DECK_PUBLISH_FLAG = "pyforge.herald.deck_publish"


def _flag_tree(tmp_path: Path, *, enabled: bool) -> Path:
    variant = "on" if enabled else "off"
    payload = {
        "flags": {
            DECK_PUBLISH_FLAG: {
                "state": "ENABLED",
                "variants": {"on": True, "off": False},
                "defaultVariant": variant,
            }
        }
    }
    path = tmp_path / "flags.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _herald_get(path: str, *, headers: dict[str, str] | None = None, cookies: dict[str, str] | None = None):
    async def _call():
        app = station_application("herald", 1)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get(path, headers=headers or {}, cookies=cookies or {})

    return asyncio.run(_call())


@pytest.fixture
def deck_export_row(db) -> DeckExport:
    return DeckExport.objects.create(
        slug="pyforge-herald",
        topic="pyforge-herald",
        kind="html",
        export_date="2026-09-28",
        size=5,
        content_type="text/html",
        sha256="b" * 64,
        source_commit="deadbeef",
        published_at=datetime(2026, 9, 28, tzinfo=UTC),
    )


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_list_requires_identity(deck_export_row, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(_flag_tree(tmp_path, enabled=True)))
    response = _herald_get("/stations/herald/api/v1/deck-exports")
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_list_forbidden_without_herald_role(deck_export_row, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(_flag_tree(tmp_path, enabled=True)))
    token = PortalClient().emit(
        "other-user",
        [prefixed_station("steward")],
        "herald",
        private_pem=GOLDEN_PRIVATE_PEM,
    )
    response = _herald_get(
        "/stations/herald/api/v1/deck-exports",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_list_returns_projection_with_bearer(
    deck_export_row,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(_flag_tree(tmp_path, enabled=True)))
    token = PortalClient().emit(
        "herald-operator",
        [prefixed_station("herald")],
        "herald",
        private_pem=GOLDEN_PRIVATE_PEM,
    )
    response = _herald_get(
        "/stations/herald/api/v1/deck-exports",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert len(body) == 1
    assert body[0]["sha256"] == "b" * 64
    assert "access-control-allow-origin" not in {k.lower() for k in response.headers}


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_routes_answer_404_when_flag_off(deck_export_row, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(_flag_tree(tmp_path, enabled=False)))
    token = PortalClient().emit(
        "herald-operator",
        [prefixed_station("herald")],
        "herald",
        private_pem=GOLDEN_PRIVATE_PEM,
    )
    headers = {"Authorization": f"Bearer {token}"}
    assert _herald_get("/stations/herald/api/v1/deck-exports", headers=headers).status_code == HTTPStatus.NOT_FOUND
    assert (
        _herald_get(f"/stations/herald/api/v1/deck-exports/{'b' * 64}", headers=headers).status_code
        == HTTPStatus.NOT_FOUND
    )


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_stream_unknown_sha_is_not_found(
    deck_export_row,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(_flag_tree(tmp_path, enabled=True)))
    token = PortalClient().emit(
        "herald-operator",
        [prefixed_station("herald")],
        "herald",
        private_pem=GOLDEN_PRIVATE_PEM,
    )
    response = _herald_get(
        f"/stations/herald/api/v1/deck-exports/{'c' * 64}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_stream_uses_memory_store(
    deck_export_row,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pyforge.herald import deck_store

    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(_flag_tree(tmp_path, enabled=True)))
    mem = deck_store.MemoryDeckStore()
    payload = b"<html>deck</html>"
    mem.put_bytes(f"sha256/{'b' * 64}", payload, content_type="text/html")
    monkeypatch.setattr(deck_store, "open_deck_store", lambda **_: mem)

    token = PortalClient().emit(
        "herald-operator",
        [prefixed_station("herald")],
        "herald",
        private_pem=GOLDEN_PRIVATE_PEM,
    )
    response = _herald_get(
        f"/stations/herald/api/v1/deck-exports/{'b' * 64}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.content == payload
    assert response.headers["content-type"].startswith("text/html")
    assert "filename=" in response.headers.get("content-disposition", "")


def test_refresh_writes_nothing_when_flag_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, db) -> None:
    from django.core.management import call_command

    from django_pyforge.flags import configure_file_provider

    off = _flag_tree(tmp_path, enabled=False)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(off))
    configure_file_provider(off)
    call_command("refresh_deck_exports", slug=["pyforge-herald"])
    assert DeckExport.objects.count() == 0


def test_refresh_upserts_from_portal_runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, db) -> None:
    from django.core.management import call_command

    from django_pyforge.flags import configure_file_provider

    on = _flag_tree(tmp_path, enabled=True)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(on))
    configure_file_provider(on)

    sample = json.dumps(
        [
            {
                "topic": "pyforge-herald",
                "kind": "html",
                "date": "2026-09-28",
                "size": 9,
                "content_type": "text/html",
                "sha256": "d" * 64,
                "source_commit": "abc",
            }
        ]
    )

    def _fake_runner(*, station: str, argv: list[str], token: str, **_: object) -> dict[str, str]:
        assert station == "herald"
        assert argv[:3] == ["deck", "exports", "pyforge-herald"]
        return {"stdout": sample}

    monkeypatch.setattr(
        "django_herald_portal.management.commands.refresh_deck_exports.deck_exports_json_runner",
        _fake_runner,
    )
    call_command("refresh_deck_exports", slug=["pyforge-herald"])
    row = DeckExport.objects.get(sha256="d" * 64)
    assert row.slug == "pyforge-herald"
    assert row.size == 9
