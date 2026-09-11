"""Story 26.1 / 49.6: IdP revoke takes effect on the next request (FR-31 / CAP-12)."""

from __future__ import annotations

import importlib
import inspect
import os
from http import HTTPStatus
from types import ModuleType
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

from config.authorization import idp_userinfo
from config.authorization.idp_userinfo import DEFAULT_CLAIMS_CACHE_SECONDS
from config.authorization.idp_userinfo import fetch_current_userinfo

_DEPLOYED_REQUIRED_ENV = {
    "DJANGO_SETTINGS_MODULE": "config.settings.production",
    "DJANGO_SECRET_KEY": "story-49-6-test-secret-key-not-for-production-use",
    "DJANGO_ADMIN_URL": "secret-admin/",
    "MCP_HOST_SIDECAR_BASE_URL": "http://platform-mcp-host:8090",
    "COMPONENT_OIDC_ISSUER": "https://idp.invalid/realms/platform",
    "COMPONENT_OIDC_JWKS_URL": "https://idp.invalid/realms/platform/certs",
    "COMPONENT_OIDC_AUDIENCE": "platform-web",
}


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


def test_login_time_session_claims_hide_idp_revoke(settings) -> None:
    """Regression guard (49.6): None/None reads session until the next login."""
    settings.IDP_CLAIMS_SNAPSHOT = None
    settings.IDP_USERINFO = None
    request = RequestFactory().get("/stations/warden/")
    request.session = {
        IDP_TOKEN_ROLES_SESSION_KEY: [prefixed_station("warden")],
        IDP_TOKEN_CLAIMS_SESSION_KEY: {"groups": [prefixed_station("warden")]},
    }
    request.user = SimpleNamespace(groups=BoomGroups())
    still_allowed = TokenRolesMiddleware(warden_views.chrome_home)(request)
    assert still_allowed.status_code == HTTPStatus.OK


def _load_production_settings_module() -> ModuleType:
    saved = {key: os.environ.get(key) for key in _DEPLOYED_REQUIRED_ENV}
    os.environ.update(_DEPLOYED_REQUIRED_ENV)
    try:
        return importlib.import_module("config.settings.production")
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_production_default_wires_bounded_userinfo_claims_source() -> None:
    production = _load_production_settings_module()
    assert production.IDP_CLAIMS_SNAPSHOT is None
    assert production.IDP_USERINFO is fetch_current_userinfo
    assert production.IDP_CLAIMS_CACHE_SECONDS == DEFAULT_CLAIMS_CACHE_SECONDS


def test_userinfo_fetch_reflects_idp_revoke_on_next_request(
    settings,
    monkeypatch,
) -> None:
    settings.IDP_CLAIMS_SNAPSHOT = None
    settings.IDP_CLAIMS_CACHE_SECONDS = 0
    settings.IDP_USERINFO = fetch_current_userinfo
    settings.OIDC_ISSUER = "https://idp.invalid/realms/platform"

    sequence = [
        {"groups": [prefixed_station("warden")]},
        {"groups": []},
    ]

    def fake_fetch(_token: str) -> dict[str, list[str]]:
        return sequence.pop(0)

    monkeypatch.setattr(idp_userinfo, "_fetch_userinfo_http", fake_fetch)
    monkeypatch.setattr(idp_userinfo, "_access_token_for", lambda _user: "token")

    allowed = RequestFactory().get("/stations/warden/")
    allowed.session = {
        IDP_TOKEN_ROLES_SESSION_KEY: [prefixed_station("warden")],
        IDP_TOKEN_CLAIMS_SESSION_KEY: {"groups": [prefixed_station("warden")]},
    }
    allowed.user = SimpleNamespace(is_authenticated=True, pk=1, groups=BoomGroups())
    first = TokenRolesMiddleware(warden_views.chrome_home)(allowed)
    assert first.status_code == HTTPStatus.OK

    denied = RequestFactory().get("/stations/warden/")
    denied.session = allowed.session
    denied.user = allowed.user
    second = TokenRolesMiddleware(warden_views.chrome_home)(denied)
    assert second.status_code == HTTPStatus.FORBIDDEN
