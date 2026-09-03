"""Story 26.1: IdP revoke takes effect on the next request (FR-31)."""

from __future__ import annotations

import inspect
from http import HTTPStatus
from types import SimpleNamespace

from django.http import HttpResponse
from django.test import RequestFactory
from django_pyforge.context_processors import chrome
from django_pyforge.middleware import TokenRolesMiddleware
from django_pyforge.probe_portal import views as probe_views
from django_pyforge.roles import IDP_TOKEN_CLAIMS_SESSION_KEY
from django_pyforge.roles import IDP_TOKEN_ROLES_SESSION_KEY
from django_pyforge.roles import prefixed_station
from django_pyforge.roles import roles_from_request
from django_warden_fabric import views as warden_views


class BoomGroups:
    def __contains__(self, item: object) -> bool:
        raise AssertionError

    def __iter__(self):
        raise AssertionError

    def all(self) -> list[object]:
        raise AssertionError

    def values_list(self, *args: object, **kwargs: object) -> list[object]:
        raise AssertionError

    def filter(self, *args: object, **kwargs: object) -> object:
        raise AssertionError


def test_next_request_after_idp_revoke_is_denied(settings) -> None:
    settings.IDP_CLAIMS_SNAPSHOT = {"groups": [prefixed_station("warden")]}
    allowed = RequestFactory().get("/stations/warden/")
    allowed.session = {
        IDP_TOKEN_ROLES_SESSION_KEY: [prefixed_station("warden")],
        IDP_TOKEN_CLAIMS_SESSION_KEY: {"groups": [prefixed_station("warden")]},
    }
    allowed.user = SimpleNamespace(groups=BoomGroups())
    first = TokenRolesMiddleware(warden_views.chrome_home)(allowed)
    assert first.status_code == HTTPStatus.OK

    settings.IDP_CLAIMS_SNAPSHOT = {"groups": []}
    denied = RequestFactory().get("/stations/warden/")
    denied.session = allowed.session
    denied.user = allowed.user
    second = TokenRolesMiddleware(warden_views.chrome_home)(denied)
    assert second.status_code == HTTPStatus.FORBIDDEN
    assert list(chrome(denied)["pyforge_portals"]) == []


def test_django_groups_are_not_the_authority(settings) -> None:
    settings.IDP_CLAIMS_SNAPSHOT = {"groups": []}
    request = RequestFactory().get("/stations/warden/")
    request.session = {IDP_TOKEN_ROLES_SESSION_KEY: ["warden"]}
    request.user = SimpleNamespace(groups=BoomGroups())
    denied = TokenRolesMiddleware(warden_views.chrome_home)(request)
    assert denied.status_code == HTTPStatus.FORBIDDEN


def test_session_role_list_is_not_the_authority(settings) -> None:
    settings.IDP_CLAIMS_SNAPSHOT = {"groups": []}
    request = RequestFactory().get("/stations/chrome-probe/")
    request.session = {
        IDP_TOKEN_ROLES_SESSION_KEY: ["chrome-probe"],
        IDP_TOKEN_CLAIMS_SESSION_KEY: {"groups": [prefixed_station("chrome-probe")]},
    }
    TokenRolesMiddleware(lambda req: HttpResponse())(request)
    response = probe_views.chrome_home(request)
    assert response.status_code == HTTPStatus.FORBIDDEN


def test_station_role_check_is_present_on_portal_views() -> None:
    assert "require_station_role" in inspect.getsource(warden_views)
    assert "require_station_role" in inspect.getsource(probe_views)


def test_roles_from_request_ignores_session_role_list() -> None:
    request = RequestFactory().get("/stations/warden/")
    request.session = {IDP_TOKEN_ROLES_SESSION_KEY: ["warden"]}
    assert roles_from_request(request) == frozenset()


def test_userinfo_hook_revokes_without_relogin(settings) -> None:
    settings.IDP_CLAIMS_SNAPSHOT = None
    settings.IDP_USERINFO = lambda request: {"groups": []}
    request = RequestFactory().get("/stations/warden/")
    request.session = {
        IDP_TOKEN_ROLES_SESSION_KEY: ["warden"],
        IDP_TOKEN_CLAIMS_SESSION_KEY: {"groups": [prefixed_station("warden")]},
    }
    denied = TokenRolesMiddleware(warden_views.chrome_home)(request)
    assert denied.status_code == HTTPStatus.FORBIDDEN
