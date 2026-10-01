"""OIDC userinfo fetch with bounded cache (Story 49.6 / CAP-12; Story 78.1).

Production deployments wire ``fetch_current_userinfo`` as ``IDP_USERINFO`` so
``fetch_current_idp_claims`` re-reads IdP roles within a short cache window
instead of trusting the login-time session claims document for the full session.

The access token comes from the ``SocialToken`` row allauth stores at login
(``SOCIALACCOUNT_STORE_TOKENS``). Every way of failing to confirm the claims
answers ``None`` and ``fetch_current_idp_claims`` treats that as "no claims"
(Story 78.1): a missing token, an expired token whose refresh fails, a userinfo
error. Nothing here ever falls back to the claims stored in the session at login.
"""

from __future__ import annotations

import http.client
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING
from typing import Any

import structlog
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

if TYPE_CHECKING:
    from allauth.socialaccount.models import SocialToken
    from django.http import HttpRequest

__all__ = [
    "DEFAULT_CLAIMS_CACHE_SECONDS",
    "fetch_current_userinfo",
    "token_endpoint_url",
    "userinfo_endpoint_url",
]

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_CACHE_KEY_PREFIX = "idp-userinfo:"
DEFAULT_CLAIMS_CACHE_SECONDS = 30
_HTTP_TIMEOUT_SECONDS = 5


class _AccessTokenRejectedError(Exception):
    """The IdP answered 401: the access token is expired or revoked."""


def _issuer_endpoint(suffix: str) -> str:
    issuer = getattr(settings, "OIDC_ISSUER", "").rstrip("/")
    if not issuer:
        return ""
    return f"{issuer}/protocol/openid-connect/{suffix}"


def userinfo_endpoint_url() -> str:
    return _issuer_endpoint("userinfo")


def token_endpoint_url() -> str:
    """The IdP's token endpoint -- the ``/token`` sibling of the userinfo URL."""
    return _issuer_endpoint("token")


def _cache_key(user_id: int) -> str:
    return f"{_CACHE_KEY_PREFIX}{user_id}"


def _cache_timeout() -> int:
    configured = getattr(
        settings,
        "IDP_CLAIMS_CACHE_SECONDS",
        DEFAULT_CLAIMS_CACHE_SECONDS,
    )
    return max(0, int(configured))


def _authenticated_user(request: HttpRequest) -> Any | None:
    """The authenticated user of this request, or None.

    ``TokenRolesMiddleware`` asks for the claims *before*
    ``AuthenticationMiddleware`` has set ``request.user`` (it sits right after
    ``SessionMiddleware`` so a session claims document is readable). Without
    resolving the user from the session here, that first call would always see
    "no user", and ``request.idp_roles`` -- which some views read directly --
    would be empty on every request. ``get_user`` caches on the request, so
    ``AuthenticationMiddleware`` reuses the lookup instead of repeating it.
    """
    user = getattr(request, "user", None)
    if user is None:
        if getattr(request, "session", None) is None:
            return None
        # Deferred for the same reason as ``_latest_token_row``: this module is
        # imported at settings-load time and ``auth.middleware`` pulls in models.
        from django.contrib.auth.middleware import get_user  # noqa: PLC0415

        user = get_user(request)
    if not getattr(user, "is_authenticated", False):
        return None
    return user


def _latest_token_row(user: object) -> SocialToken | None:
    # Deferred: a module-level import of a Django model here makes this module
    # (imported by production.py at settings-load time) crash with
    # AppRegistryNotReady whenever settings load before django.setup() runs
    # (e.g. a subprocess entrypoint check) -- this function only ever runs
    # after the app registry is ready (an authenticated request exists).
    from allauth.socialaccount.models import SocialToken  # noqa: PLC0415

    return (
        SocialToken.objects.filter(account__user_id=getattr(user, "pk", None))
        .order_by("-expires_at", "-id")
        .first()
    )


def _access_token_for(user: object) -> str | None:
    row = _latest_token_row(user)
    if row is None or not row.token:
        return None
    return row.token


def _json_request(
    request: urllib.request.Request,
    *,
    event: str,
) -> dict[str, Any] | None:
    """Send ``request``; the JSON object it answers, or None on any failure.

    Raises ``_AccessTokenRejectedError`` for HTTP 401 alone -- the one answer
    that is not just "the IdP is unwell" -- so the caller can try a refresh.
    Every other failure (4xx/5xx, a refused or timed-out connection, a truncated
    or non-JSON body) is None, and the caller denies.
    """
    try:
        with urllib.request.urlopen(  # noqa: S310
            request, timeout=_HTTP_TIMEOUT_SECONDS
        ) as response:
            body = response.read().decode()
    except urllib.error.HTTPError as exc:
        if exc.code == HTTPStatus.UNAUTHORIZED:
            raise _AccessTokenRejectedError from exc
        logger.warning(f"{event}_failed", error=str(exc))
        return None
    except (OSError, http.client.HTTPException, ValueError) as exc:
        logger.warning(f"{event}_failed", error=str(exc))
        return None
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.warning(f"{event}_invalid_json")
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _fetch_userinfo_http(access_token: str) -> dict[str, Any] | None:
    url = userinfo_endpoint_url()
    if not url.startswith(("http://", "https://")):
        return None
    request = urllib.request.Request(  # noqa: S310
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        method="GET",
    )
    return _json_request(request, event="authorization.userinfo_fetch")


def _oidc_client() -> tuple[str, str] | None:
    """The configured OIDC app's ``(client_id, secret)``, or None."""
    provider_id = getattr(settings, "OIDC_PROVIDER_ID", "oidc")
    apps = getattr(settings, "SOCIALACCOUNT_PROVIDERS", {}).get("openid_connect", {})
    for app in apps.get("APPS", []):
        if app.get("provider_id") == provider_id and app.get("client_id"):
            return app["client_id"], app.get("secret") or ""
    return None


def _refresh_access_token(user: object) -> str | None:
    """Renew the user's stored access token with the stored refresh token.

    Returns the fresh access token, or None when no refresh is possible or the
    IdP refuses it (a revoked grant, a disabled user). The row is updated in
    place: the rotated refresh token when the IdP issues one, else the old one
    stays. Called at most once per request. Two requests racing a *rotating*
    refresh token can see the loser refused -- it is denied this once and the
    stored (winner's) token serves the next request.
    """
    row = _latest_token_row(user)
    if row is None or not row.token_secret:
        logger.warning("authorization.token_refresh_unavailable")
        return None
    client = _oidc_client()
    url = token_endpoint_url()
    if client is None or not url.startswith(("http://", "https://")):
        logger.warning("authorization.token_refresh_unconfigured")
        return None
    client_id, client_secret = client
    form = {
        "grant_type": "refresh_token",
        "refresh_token": row.token_secret,
        "client_id": client_id,
    }
    if client_secret:
        form["client_secret"] = client_secret
    request = urllib.request.Request(  # noqa: S310
        url,
        data=urllib.parse.urlencode(form).encode(),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        payload = _json_request(request, event="authorization.token_refresh")
    except _AccessTokenRejectedError:
        # The IdP refused the client or the grant outright: a failed refresh.
        logger.warning("authorization.token_refresh_refused")
        return None
    if payload is None:
        return None
    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        return None
    row.token = access_token
    refresh_token = payload.get("refresh_token")
    if isinstance(refresh_token, str) and refresh_token:
        row.token_secret = refresh_token
    expires_in = payload.get("expires_in")
    row.expires_at = (
        timezone.now() + timedelta(seconds=expires_in)
        if isinstance(expires_in, int) and expires_in > 0
        else None
    )
    row.save(update_fields=["token", "token_secret", "expires_at"])
    return access_token


def _confirm_claims(user: object) -> dict[str, Any] | None:
    """Ask the IdP for this user's claims; None whenever it cannot be confirmed."""
    token = _access_token_for(user)
    if token is None:
        logger.warning("authorization.userinfo_no_stored_token")
        return None
    try:
        return _fetch_userinfo_http(token)
    except _AccessTokenRejectedError:
        pass
    # Expired or revoked access token: renew it once and retry once.
    token = _refresh_access_token(user)
    if token is None:
        return None
    try:
        return _fetch_userinfo_http(token)
    except _AccessTokenRejectedError:
        logger.warning("authorization.userinfo_rejected_after_refresh")
        return None


def fetch_current_userinfo(request: HttpRequest) -> dict[str, Any] | None:
    """Return cached-or-fresh IdP userinfo claims for this authenticated request.

    None means the claims could not be confirmed, and the caller must treat that
    as "no claims" -- never as a cue to read the login-time session claims.
    """
    user = _authenticated_user(request)
    if user is None:
        return None

    cache_key = _cache_key(user.pk)
    cached = cache.get(cache_key)
    if isinstance(cached, dict):
        return dict(cached)

    claims = _confirm_claims(user)
    if claims is None:
        return None

    timeout = _cache_timeout()
    if timeout > 0:
        cache.set(cache_key, claims, timeout=timeout)
    return dict(claims)
