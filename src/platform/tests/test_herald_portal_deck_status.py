"""Story 17.2: authenticated herald home renders one slug via PortalClient."""

from __future__ import annotations

from http import HTTPStatus

from django.test import RequestFactory
from django_herald_portal import views as herald_views
from django_herald_portal.views import PORTAL_DECK_SLUG
from django_pyforge.assertion.client import PortalClient


def _herald_request() -> object:
    request = RequestFactory().get("/stations/herald/")
    request.idp_token_claims = {"sub": "herald-operator", "groups": ["herald"]}
    request.idp_roles = ["pyforge:station:herald"]
    return request


def test_herald_home_renders_one_slug_via_portal_client() -> None:
    response = herald_views.chrome_home(_herald_request())
    assert response.status_code == HTTPStatus.OK
    body = response.content.decode()
    assert PORTAL_DECK_SLUG in body
    assert 'id="herald-deck-status"' in body
    assert "herald deck status" in body
    assert 'id="herald-deck-slug"' in body


def test_herald_home_invoke_uses_deck_status_argv(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_invoke(self, sub, roles, station, argv, **kwargs):
        seen["sub"] = sub
        seen["roles"] = list(roles)
        seen["station"] = station
        seen["argv"] = list(argv)
        return {
            "slug": PORTAL_DECK_SLUG,
            "linked": True,
            "project_id": "proj-1",
            "sync": "unchanged",
            "last_pull": None,
            "stale_mirror": True,
        }

    monkeypatch.setattr(
        "django_herald_portal.views.PortalClient.invoke",
        fake_invoke,
    )
    response = herald_views.chrome_home(_herald_request())
    assert response.status_code == HTTPStatus.OK
    assert seen["station"] == "herald"
    assert seen["argv"] == ["deck", "status", PORTAL_DECK_SLUG]
    assert seen["sub"] == "herald-operator"
    assert b"herald-stale-mirror" in response.content
    assert b"True" in response.content


def test_portal_client_invoke_signs_then_projects() -> None:
    row = PortalClient().invoke(
        "herald-operator",
        ["herald"],
        "herald",
        ["deck", "status", PORTAL_DECK_SLUG],
    )
    assert row["slug"] == PORTAL_DECK_SLUG
    assert row["stale_mirror"] is False


def test_herald_home_without_role_is_forbidden() -> None:
    denied = RequestFactory().get("/stations/herald/")
    denied.idp_roles = ["pyforge:station:steward"]
    response = herald_views.chrome_home(denied)
    assert response.status_code == HTTPStatus.FORBIDDEN
