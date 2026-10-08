"""Story 30.2 — herald portal deck list, viewer, twin route, and flag gating."""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import json
from datetime import UTC
from datetime import datetime
from http import HTTPStatus
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import pytest
from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from django.db import connections
from django.http import Http404
from django.test import RequestFactory
from django.test import override_settings
from django_herald_portal import views as herald_views
from django_herald_portal.models import DeckExport
from django_pyforge.assertion.client import PortalClient
from django_pyforge.assertion.golden import GOLDEN_PRIVATE_PEM
from django_pyforge.assertion.golden import GOLDEN_PUBLIC_PEM
from django_pyforge.roles import IDP_TOKEN_CLAIMS_SESSION_KEY
from django_pyforge.roles import prefixed_station
from httpx import ASGITransport
from httpx import AsyncClient

from config.station_api import station_application

if TYPE_CHECKING:
    from pathlib import Path

DECK_VIEWER_FLAG = "pyforge.herald.deck_viewer"

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def _herald_repo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The herald station API builds its webhook host on first request.
    monkeypatch.setenv("HERALD_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("HERALD_WEBHOOK_SECRET", "test-secret")


def _viewer_flag_tree(tmp_path: Path, *, enabled: bool) -> Path:
    variant = "on" if enabled else "off"
    payload = {
        "flags": {
            DECK_VIEWER_FLAG: {
                "state": "ENABLED",
                "variants": {"on": True, "off": False},
                "defaultVariant": variant,
            }
        }
    }
    path = tmp_path / "flags.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _herald_request(path: str = "/stations/herald/decks/") -> object:
    request = RequestFactory().get(path)
    request.idp_token_claims = {  # type: ignore[attr-defined]
        "sub": "herald-operator",
        "groups": [prefixed_station("herald")],
    }
    request.idp_roles = [prefixed_station("herald")]  # type: ignore[attr-defined]
    return request


def _session_cookies(*, sub: str, groups: list[str]) -> dict[str, str]:
    store = SessionStore()
    store[IDP_TOKEN_CLAIMS_SESSION_KEY] = {"sub": sub, "groups": groups}
    store.save()
    session_key = store.session_key
    assert session_key is not None
    name = getattr(settings, "SESSION_COOKIE_NAME", "sessionid")
    return {str(name): session_key}


def _herald_get(
    path: str,
    *,
    headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
):
    async def _call():
        app = station_application("herald", 1)
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            return await client.get(path, headers=headers or {}, cookies=cookies or {})

    try:
        return asyncio.run(_call())
    finally:
        connections.close_all()


def _seed_store(
    monkeypatch: pytest.MonkeyPatch,
    slug: str,
    *,
    standalone: bytes | None = None,
    bundle: dict[str, bytes] | None = None,
) -> None:
    deck_store = importlib.import_module("pyforge.herald.deck_store")
    mem = deck_store.MemoryDeckStore()
    twins: dict[str, object] = {}
    if standalone is not None:
        sha = "a" * 64
        mem.put_bytes(f"sha256/{sha}", standalone, content_type="text/html")
        twins["standalone"] = {
            "sha256": sha,
            "content_type": "text/html",
            "size": len(standalone),
            "path": f"presentations/{slug}/x.html",
        }
    if bundle is not None:
        files: dict[str, str] = {}
        for rel, body in bundle.items():
            # stable 64-hex per rel for tests
            digest = hashlib.sha256(body).hexdigest()
            mem.put_bytes(
                f"sha256/{digest}",
                body,
                content_type="application/javascript"
                if rel.endswith(".js")
                else "text/html",
            )
            files[rel] = digest
        twins["bundle"] = {"files": files}
    manifest = {"exports": [], "twins": twins}
    mem.put_bytes(
        f"manifests/{slug}.json",
        (json.dumps(manifest, indent=2) + "\n").encode(),
        content_type="application/json",
    )
    monkeypatch.setattr(deck_store, "open_deck_store", lambda **_: mem)


@pytest.fixture
def deck_rows(db) -> None:
    DeckExport.objects.create(
        slug="demo-standalone",
        topic="Demo Standalone",
        kind="html",
        export_date="2026-09-28",
        size=5,
        content_type="text/html",
        sha256="d" * 64,
        source_commit="deadbeef",
        published_at=datetime(2026, 9, 28, tzinfo=UTC),
    )
    DeckExport.objects.create(
        slug="demo-bundle",
        topic="Demo Bundle",
        kind="pptx",
        export_date="2026-09-28",
        size=9,
        content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        sha256="e" * 64,
        source_commit="deadbeef",
        published_at=datetime(2026, 9, 28, tzinfo=UTC),
    )


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_deck_list_shows_published_slugs(
    deck_rows,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "PYFORGE_FLAGS_PATH", str(_viewer_flag_tree(tmp_path, enabled=True))
    )
    monkeypatch.setattr(
        "django_herald_portal.views.evaluate_boolean",
        lambda _key, default=False: True,
    )
    response = herald_views.deck_list(_herald_request("/stations/herald/decks/"))
    assert response.status_code == HTTPStatus.OK
    body = response.content.decode()
    assert "demo-standalone" in body
    assert "demo-bundle" in body


def test_deck_list_404_when_flag_off(
    deck_rows, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "PYFORGE_FLAGS_PATH", str(_viewer_flag_tree(tmp_path, enabled=False))
    )
    monkeypatch.setattr(
        "django_herald_portal.views.evaluate_boolean",
        lambda _key, default=False: False,
    )
    with pytest.raises(Http404):
        herald_views.deck_list(_herald_request())


def test_deck_list_forbidden_without_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "django_herald_portal.views.evaluate_boolean",
        lambda _key, default=False: True,
    )
    denied = RequestFactory().get("/stations/herald/decks/")
    denied.idp_roles = [prefixed_station("steward")]  # type: ignore[attr-defined]
    response = herald_views.deck_list(denied)
    assert response.status_code == HTTPStatus.FORBIDDEN


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_viewer_renders_iframe_and_pptx_link(
    deck_rows,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slug = "demo-standalone"
    monkeypatch.setenv(
        "PYFORGE_FLAGS_PATH", str(_viewer_flag_tree(tmp_path, enabled=True))
    )
    monkeypatch.setattr(
        "django_herald_portal.views.evaluate_boolean",
        lambda _key, default=False: True,
    )
    _seed_store(
        monkeypatch,
        slug,
        standalone=b"<html><body>standalone twin</body></html>",
    )
    response = herald_views.deck_view(
        _herald_request(f"/stations/herald/decks/{slug}/view/"),
        slug=slug,
    )
    body = response.content.decode()
    assert 'id="herald-deck-twin-frame"' in body
    assert f"/stations/herald/api/v1/deck-twins/{slug}" in body
    assert "Download current .pptx" not in body


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_home_unchanged_when_flag_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "PYFORGE_FLAGS_PATH", str(_viewer_flag_tree(tmp_path, enabled=False))
    )
    monkeypatch.setattr(
        "django_herald_portal.views.evaluate_boolean",
        lambda _key, default=False: False,
    )
    monkeypatch.setattr(
        "django_herald_portal.views.PortalClient.invoke",
        lambda self, **kwargs: {
            "slug": "pyforge-herald",
            "linked": True,
            "sync": "ok",
            "stale_mirror": False,
        },
    )
    response = herald_views.chrome_home(_herald_request("/stations/herald/"))
    body = response.content.decode()
    assert "herald-pitch-deck-list" not in body
    assert 'data-console-home="pitch"' in body


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_twin_routes_require_herald_role(
    deck_rows, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "PYFORGE_FLAGS_PATH", str(_viewer_flag_tree(tmp_path, enabled=True))
    )
    _seed_store(monkeypatch, "demo-standalone", standalone=b"<html></html>")
    assert (
        _herald_get("/stations/herald/api/v1/deck-twins/demo-standalone").status_code
        == HTTPStatus.UNAUTHORIZED
    )


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_twin_stream_sets_csp_and_no_cors(
    deck_rows, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "PYFORGE_FLAGS_PATH", str(_viewer_flag_tree(tmp_path, enabled=True))
    )
    _seed_store(monkeypatch, "demo-standalone", standalone=b"<html></html>")
    token = PortalClient().emit(
        "herald-operator",
        [prefixed_station("herald")],
        "herald",
        private_pem=GOLDEN_PRIVATE_PEM,
    )
    response = _herald_get(
        "/stations/herald/api/v1/deck-twins/demo-standalone",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == HTTPStatus.OK
    csp = response.headers.get("content-security-policy", "")
    assert "'self'" in csp
    assert "access-control-allow-origin" not in {k.lower() for k in response.headers}


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_twin_routes_404_when_flag_off(
    deck_rows, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "PYFORGE_FLAGS_PATH", str(_viewer_flag_tree(tmp_path, enabled=False))
    )
    _seed_store(monkeypatch, "demo-standalone", standalone=b"<html></html>")
    token = PortalClient().emit(
        "herald-operator",
        [prefixed_station("herald")],
        "herald",
        private_pem=GOLDEN_PRIVATE_PEM,
    )
    headers = {"Authorization": f"Bearer {token}"}
    assert (
        _herald_get(
            "/stations/herald/api/v1/deck-twins/demo-standalone", headers=headers
        ).status_code
        == HTTPStatus.NOT_FOUND
    )


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_portal_routes_404_when_flag_off(
    deck_rows, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "PYFORGE_FLAGS_PATH", str(_viewer_flag_tree(tmp_path, enabled=False))
    )
    monkeypatch.setattr(
        "django_herald_portal.views.evaluate_boolean",
        lambda _key, default=False: False,
    )
    with pytest.raises(Http404):
        herald_views.deck_list(_herald_request())
    with pytest.raises(Http404):
        herald_views.deck_view(_herald_request(), slug="demo-standalone")


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_unknown_twin_path_is_not_found(
    deck_rows, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "PYFORGE_FLAGS_PATH", str(_viewer_flag_tree(tmp_path, enabled=True))
    )
    _seed_store(
        monkeypatch,
        "demo-bundle",
        bundle={
            "index.html": b"<html><script src='assets/app.js'></script></html>",
            "assets/app.js": b"console.log('local');",
        },
    )
    token = PortalClient().emit(
        "herald-operator",
        [prefixed_station("herald")],
        "herald",
        private_pem=GOLDEN_PRIVATE_PEM,
    )
    headers = {"Authorization": f"Bearer {token}"}
    ok = _herald_get(
        "/stations/herald/api/v1/deck-twins/demo-bundle/index.html",
        headers=headers,
    )
    assert ok.status_code == HTTPStatus.OK
    missing = _herald_get(
        "/stations/herald/api/v1/deck-twins/demo-bundle/nosuch.js",
        headers=headers,
    )
    assert missing.status_code == HTTPStatus.NOT_FOUND
    traversal = _herald_get(
        "/stations/herald/api/v1/deck-twins/demo-bundle/../../x",
        headers=headers,
    )
    assert traversal.status_code in (HTTPStatus.NOT_FOUND, HTTPStatus.BAD_REQUEST)


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_playwright_records_zero_foreign_origin_requests(
    live_server,
    deck_rows,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sync_playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="playwright bindings required for herald browser check",
    ).sync_playwright

    slug_standalone = "demo-standalone"
    slug_bundle = "demo-bundle"
    monkeypatch.setenv(
        "PYFORGE_FLAGS_PATH", str(_viewer_flag_tree(tmp_path, enabled=True))
    )
    _seed_store(
        monkeypatch,
        slug_standalone,
        standalone=b"<html><body>only self</body></html>",
    )
    _seed_store(
        monkeypatch,
        slug_bundle,
        bundle={
            "index.html": b"<html><script src='assets/app.js'></script></html>",
            "assets/app.js": b"// local bundle asset",
        },
    )
    cookies = _session_cookies(
        sub="herald-operator",
        groups=[prefixed_station("herald")],
    )
    base = live_server.url.rstrip("/")
    cookie_name = next(iter(cookies))
    cookie_value = cookies[cookie_name]
    parsed = urlparse(base)
    foreign: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context()
        context.add_cookies(
            [
                {
                    "name": cookie_name,
                    "value": cookie_value,
                    "domain": parsed.hostname or "localhost",
                    "path": "/",
                }
            ]
        )
        page = context.new_page()

        def _track(request) -> None:
            url = urlparse(request.url)
            if url.scheme in ("http", "https") and url.netloc != parsed.netloc:
                foreign.append(request.url)

        page.on("request", _track)
        for slug in (slug_standalone, slug_bundle):
            page.goto(f"{base}/stations/herald/decks/{slug}/view/")
            page.wait_for_load_state("networkidle")
        browser.close()

    assert foreign == []
