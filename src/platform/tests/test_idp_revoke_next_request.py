"""Story 26.1 / 49.6: IdP revoke takes effect on the next request (FR-31 / CAP-12)."""

from __future__ import annotations

import importlib
import inspect
import json
import os
import threading
import time
from datetime import timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
from types import ModuleType
from types import SimpleNamespace
from urllib.parse import parse_qs

import pytest
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.models import SocialLogin
from allauth.socialaccount.models import SocialToken
from django.conf import settings as django_settings
from django.http import HttpRequest
from django.http import HttpResponse
from django.test import Client
from django.test import RequestFactory
from django.utils import timezone
from django_pyforge.context_processors import chrome
from django_pyforge.middleware import TokenRolesMiddleware
from django_pyforge.probe_portal import views as probe_views
from django_pyforge.roles import IDP_TOKEN_CLAIMS_SESSION_KEY
from django_pyforge.roles import IDP_TOKEN_ROLES_SESSION_KEY
from django_pyforge.roles import prefixed_station
from django_pyforge.roles import roles_from_request
from django_warden_fabric import views as warden_views

from config.authorization import idp_userinfo
from config.authorization.adapters import OIDCSocialAccountAdapter
from config.authorization.current_claims import fetch_current_idp_claims
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
    "LANGFLOW_SUPERUSER_PASSWORD": "unit-test-langflow-password",
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


# ---------------------------------------------------------------------------
# Story 78.1 / CAP-86 / unifying-strategy CAP-12: revocation on the NEXT request,
# end to end. A real SocialToken (stored through allauth's own SocialLogin.save,
# driven by the OIDC adapter) against a local HTTP stand-in for the IdP's userinfo
# and token endpoints, requested through the real middleware stack. Nothing the
# fix owns is mocked: `_access_token_for`, `_fetch_userinfo_http` and the refresh
# run for real. The mocked predecessor of these tests passed while production
# failed open, because allauth's SOCIALACCOUNT_STORE_TOKENS was never set.
# ---------------------------------------------------------------------------

_STATION = "chrome-probe"
_STATION_ROLE = prefixed_station(_STATION)
_STATION_URL = f"/stations/{_STATION}/"
_USERINFO_PATH = "/realms/platform/protocol/openid-connect/userinfo"
_TOKEN_PATH = "/realms/platform/protocol/openid-connect/token"  # noqa: S105
_CLIENT_ID = "platform-web"
_CLIENT_SECRET = "stub-client-secret"  # noqa: S105
_SUB = "idp-user-78-1"
_LOGIN_TIME_GROUPS = [_STATION_ROLE]


class _IdPStub:
    """What the IdP answers: userinfo per access token, refresh grants."""

    def __init__(self) -> None:
        self.claims_by_access_token: dict[str, dict[str, object]] = {}
        # refresh token -> (new access token, rotated refresh token); single use.
        self.refresh_grants: dict[str, tuple[str, str | None]] = {}
        self.userinfo_status: int | None = None
        self.token_status: int | None = None
        self.delay_seconds = 0.0
        self.userinfo_calls: list[str] = []
        self.token_calls: list[dict[str, str]] = []

    def grant_role(self, access_token: str, groups: list[str]) -> None:
        self.claims_by_access_token[access_token] = {"sub": _SUB, "groups": groups}


class _IdPHandler(BaseHTTPRequestHandler):
    stub: _IdPStub  # bound per test by the `idp` fixture's subclass

    def log_message(self, *args: object) -> None:  # silence the test run
        pass

    def _answer(self, status: int, body: dict[str, object]) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # http.server dispatches on this name
        stub = self.stub
        time.sleep(stub.delay_seconds)
        bearer = self.headers.get("Authorization", "").removeprefix("Bearer ")
        stub.userinfo_calls.append(bearer)
        if self.path != _USERINFO_PATH:
            self._answer(HTTPStatus.NOT_FOUND, {})
        elif stub.userinfo_status is not None:
            self._answer(stub.userinfo_status, {"error": "forced"})
        elif bearer in stub.claims_by_access_token:
            self._answer(HTTPStatus.OK, stub.claims_by_access_token[bearer])
        else:
            self._answer(HTTPStatus.UNAUTHORIZED, {"error": "invalid_token"})

    def do_POST(self) -> None:  # http.server dispatches on this name
        stub = self.stub
        length = int(self.headers.get("Content-Length", "0"))
        raw = parse_qs(self.rfile.read(length).decode())
        form = {key: values[0] for key, values in raw.items()}
        stub.token_calls.append(form)
        grant = stub.refresh_grants.pop(form.get("refresh_token", ""), None)
        if self.path != _TOKEN_PATH:
            self._answer(HTTPStatus.NOT_FOUND, {})
        elif stub.token_status is not None:
            self._answer(stub.token_status, {"error": "forced"})
        elif not _refresh_request_is_valid(form, grant):
            self._answer(HTTPStatus.BAD_REQUEST, {"error": "invalid_grant"})
        else:
            assert grant is not None
            new_access, new_refresh = grant
            body: dict[str, object] = {"access_token": new_access, "expires_in": 300}
            if new_refresh:
                body["refresh_token"] = new_refresh
            self._answer(HTTPStatus.OK, body)


def _refresh_request_is_valid(
    form: dict[str, str],
    grant: tuple[str, str | None] | None,
) -> bool:
    """A refresh_token grant from the configured client, for a live refresh token."""
    return (
        grant is not None
        and form.get("grant_type") == "refresh_token"
        and form.get("client_id") == _CLIENT_ID
        and form.get("client_secret") == _CLIENT_SECRET
    )


@pytest.fixture
def idp(settings, monkeypatch):
    """A local IdP the platform's userinfo hook talks to over real HTTP."""
    stub = _IdPStub()
    handler = type("Handler", (_IdPHandler,), {"stub": stub})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # A developer or CI shell with an http_proxy must not intercept loopback.
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    settings.OIDC_ISSUER = f"http://127.0.0.1:{server.server_port}/realms/platform"
    settings.SOCIALACCOUNT_PROVIDERS = {
        "openid_connect": {
            "APPS": [
                {
                    "provider_id": settings.OIDC_PROVIDER_ID,
                    "name": "stub",
                    "client_id": _CLIENT_ID,
                    "secret": _CLIENT_SECRET,
                    "settings": {"server_url": settings.OIDC_ISSUER},
                },
            ],
        },
    }
    settings.IDP_CLAIMS_SNAPSHOT = None
    settings.IDP_USERINFO = fetch_current_userinfo
    settings.IDP_CLAIMS_CACHE_SECONDS = 0
    yield stub
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def _login_through_the_idp(
    client: Client,
    stub: _IdPStub,
    *,
    access_token: str = "access-1",  # noqa: S107 -- a stub token, not a credential
    refresh_token: str = "refresh-1",  # noqa: S107
    groups: list[str] | None = None,
) -> SimpleNamespace:
    """What an interactive IdP login leaves behind, via the real adapter.

    ``pre_social_login`` is the one writer of the login-time session claims and
    calls ``sociallogin.connect`` -> allauth's ``SocialLogin.save``, which stores
    the ``SocialToken`` iff ``SOCIALACCOUNT_STORE_TOKENS``.
    """
    groups = _LOGIN_TIME_GROUPS if groups is None else groups
    stub.grant_role(access_token, groups)
    claims = stub.claims_by_access_token[access_token]
    account = SocialAccount(
        provider=django_settings.OIDC_PROVIDER_ID,
        uid=_SUB,
        extra_data={"userinfo": claims},
    )
    token = SocialToken(
        token=access_token,
        token_secret=refresh_token,
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    sociallogin = SocialLogin(account=account)
    sociallogin.token = token  # as allauth's OAuth2 callback sets it
    login_request = HttpRequest()
    login_request.session = {}
    OIDCSocialAccountAdapter().pre_social_login(login_request, sociallogin)

    client.force_login(sociallogin.user)
    session = client.session
    session.update(login_request.session)
    session.save()
    return SimpleNamespace(user=sociallogin.user)


def _stored_token(user: object) -> SocialToken:
    return SocialToken.objects.get(account__user=user)


@pytest.mark.django_db
def test_an_idp_login_stores_the_access_and_refresh_token(idp: _IdPStub) -> None:
    """Without SOCIALACCOUNT_STORE_TOKENS allauth saves no row, and the userinfo
    re-check has nothing to present to the IdP."""
    login = _login_through_the_idp(Client(), idp)

    row = _stored_token(login.user)

    assert row.token == "access-1"  # noqa: S105 -- a stub token
    assert row.token_secret == "refresh-1"  # noqa: S105
    assert row.expires_at is not None


@pytest.mark.django_db
def test_next_request_after_idp_revoke_loses_the_role(idp: _IdPStub) -> None:
    client = Client()
    _login_through_the_idp(client, idp)

    first = client.get(_STATION_URL)
    assert first.status_code == HTTPStatus.OK

    idp.grant_role("access-1", [])  # the IdP stops returning the role

    second = client.get(_STATION_URL)
    assert second.status_code == HTTPStatus.FORBIDDEN
    # The answer came from the IdP over HTTP each time, with the stored token.
    assert idp.userinfo_calls == ["access-1", "access-1"]
    assert idp.token_calls == []


@pytest.mark.django_db
def test_request_roles_come_from_userinfo_before_the_view_runs(
    idp: _IdPStub,
) -> None:
    """``TokenRolesMiddleware`` asks for the claims before
    ``AuthenticationMiddleware`` sets ``request.user``; some views read
    ``request.idp_roles`` directly, so the hook must resolve the user itself."""
    client = Client()
    _login_through_the_idp(client, idp)

    response = client.get(_STATION_URL)

    assert getattr(response.wsgi_request, "idp_roles", None) == [_STATION_ROLE]


@pytest.mark.django_db
def test_an_expired_token_is_refreshed_once_and_the_fresh_claims_are_used(
    idp: _IdPStub,
) -> None:
    client = Client()
    login = _login_through_the_idp(client, idp)
    del idp.claims_by_access_token["access-1"]  # userinfo now answers 401 for it
    idp.refresh_grants["refresh-1"] = ("access-2", "refresh-2")
    idp.grant_role("access-2", _LOGIN_TIME_GROUPS)

    response = client.get(_STATION_URL)

    assert response.status_code == HTTPStatus.OK
    assert idp.userinfo_calls == ["access-1", "access-2"]
    assert len(idp.token_calls) == 1
    assert idp.token_calls[0] == {
        "grant_type": "refresh_token",
        "refresh_token": "refresh-1",
        "client_id": _CLIENT_ID,
        "client_secret": _CLIENT_SECRET,
    }
    row = _stored_token(login.user)
    assert row.token == "access-2"  # noqa: S105 -- a stub token
    assert row.token_secret == "refresh-2"  # noqa: S105
    # The next request presents the renewed token: no second refresh.
    assert client.get(_STATION_URL).status_code == HTTPStatus.OK
    assert idp.userinfo_calls[-1] == "access-2"
    assert len(idp.token_calls) == 1


@pytest.mark.django_db
def test_a_refreshed_token_whose_role_was_revoked_is_denied(idp: _IdPStub) -> None:
    client = Client()
    _login_through_the_idp(client, idp)
    del idp.claims_by_access_token["access-1"]
    idp.refresh_grants["refresh-1"] = ("access-2", None)
    idp.grant_role("access-2", [])

    response = client.get(_STATION_URL)

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert len(idp.token_calls) == 1


@pytest.mark.django_db
def test_a_failed_refresh_denies_and_never_serves_the_login_time_claims(
    idp: _IdPStub,
) -> None:
    client = Client()
    _login_through_the_idp(client, idp)
    del idp.claims_by_access_token["access-1"]
    idp.refresh_grants.clear()  # the IdP no longer honours the refresh token
    # The session still carries the login-time claims granting the role.
    assert client.session[IDP_TOKEN_CLAIMS_SESSION_KEY]["groups"] == _LOGIN_TIME_GROUPS

    response = client.get(_STATION_URL)

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert len(idp.token_calls) == 1  # refreshed once, never retried
    assert getattr(response.wsgi_request, "idp_roles", None) == []


@pytest.mark.django_db
def test_userinfo_still_rejecting_after_a_refresh_denies_without_a_second_refresh(
    idp: _IdPStub,
) -> None:
    client = Client()
    _login_through_the_idp(client, idp)
    del idp.claims_by_access_token["access-1"]
    idp.refresh_grants["refresh-1"] = ("access-2", "refresh-2")  # access-2: no claims

    response = client.get(_STATION_URL)

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert idp.userinfo_calls == ["access-1", "access-2"]
    assert len(idp.token_calls) == 1


@pytest.mark.django_db
def test_an_expired_token_with_no_refresh_token_is_denied(idp: _IdPStub) -> None:
    client = Client()
    _login_through_the_idp(client, idp, refresh_token="")
    del idp.claims_by_access_token["access-1"]

    response = client.get(_STATION_URL)

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert idp.token_calls == []


@pytest.mark.django_db
def test_a_session_with_no_stored_token_is_denied(idp: _IdPStub) -> None:
    """A login from before tokens were stored: the session claims grant the role,
    but nothing can confirm it with the IdP, so it is denied until the next login."""
    client = Client()
    _login_through_the_idp(client, idp)
    SocialToken.objects.all().delete()

    response = client.get(_STATION_URL)

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert idp.userinfo_calls == []


@pytest.mark.django_db
def test_userinfo_server_error_denies_and_does_not_refresh(idp: _IdPStub) -> None:
    client = Client()
    _login_through_the_idp(client, idp)
    idp.userinfo_status = HTTPStatus.SERVICE_UNAVAILABLE

    response = client.get(_STATION_URL)

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert idp.token_calls == []  # only a 401 means "the token is stale"


@pytest.mark.django_db
def test_userinfo_timeout_denies(idp: _IdPStub, monkeypatch) -> None:
    client = Client()
    _login_through_the_idp(client, idp)
    monkeypatch.setattr(idp_userinfo, "_HTTP_TIMEOUT_SECONDS", 0.2)
    idp.delay_seconds = 1.0

    response = client.get(_STATION_URL)

    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.django_db
def test_an_unreachable_idp_denies(idp: _IdPStub, settings) -> None:
    client = Client()
    _login_through_the_idp(client, idp)
    settings.OIDC_ISSUER = "http://127.0.0.1:1/realms/platform"  # nothing listens

    response = client.get(_STATION_URL)

    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.django_db
def test_claims_are_cached_for_the_bounded_window(idp: _IdPStub, settings) -> None:
    settings.IDP_CLAIMS_CACHE_SECONDS = DEFAULT_CLAIMS_CACHE_SECONDS
    client = Client()
    _login_through_the_idp(client, idp)

    assert client.get(_STATION_URL).status_code == HTTPStatus.OK
    assert client.get(_STATION_URL).status_code == HTTPStatus.OK

    assert idp.userinfo_calls == ["access-1"]


def test_a_wired_hook_that_cannot_confirm_never_falls_back_to_the_session(
    settings,
) -> None:
    """The hook is authoritative: ``None`` from it is "no claims", not a cue to
    read the login-time claims the IdP may since have revoked."""
    settings.IDP_CLAIMS_SNAPSHOT = None
    settings.IDP_USERINFO = lambda request: None
    request = RequestFactory().get(_STATION_URL)
    request.session = {
        IDP_TOKEN_CLAIMS_SESSION_KEY: {"groups": [_STATION_ROLE]},
    }

    assert fetch_current_idp_claims(request) is None
