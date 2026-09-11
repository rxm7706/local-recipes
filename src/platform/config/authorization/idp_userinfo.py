"""OIDC userinfo fetch with bounded cache (Story 49.6 / CAP-12).

Production deployments wire ``fetch_current_userinfo`` as ``IDP_USERINFO`` so
``fetch_current_idp_claims`` re-reads IdP roles within a short cache window
instead of trusting the login-time session claims document for the full session.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import TYPE_CHECKING
from typing import Any

import structlog
from allauth.socialaccount.models import SocialToken
from django.conf import settings
from django.core.cache import cache

if TYPE_CHECKING:
    from django.http import HttpRequest

__all__ = [
    "DEFAULT_CLAIMS_CACHE_SECONDS",
    "fetch_current_userinfo",
    "userinfo_endpoint_url",
]

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_CACHE_KEY_PREFIX = "idp-userinfo:"
DEFAULT_CLAIMS_CACHE_SECONDS = 30


def userinfo_endpoint_url() -> str:
    issuer = getattr(settings, "OIDC_ISSUER", "").rstrip("/")
    if not issuer:
        return ""
    return f"{issuer}/protocol/openid-connect/userinfo"


def _cache_key(user_id: int) -> str:
    return f"{_CACHE_KEY_PREFIX}{user_id}"


def _cache_timeout() -> int:
    configured = getattr(
        settings,
        "IDP_CLAIMS_CACHE_SECONDS",
        DEFAULT_CLAIMS_CACHE_SECONDS,
    )
    return max(0, int(configured))


def _access_token_for(user: object) -> str | None:
    row = (
        SocialToken.objects.filter(account__user_id=getattr(user, "pk", None))
        .order_by("-expires_at", "-id")
        .first()
    )
    if row is None or not row.token:
        return None
    return row.token


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
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310
            body = response.read().decode()
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError) as exc:
        logger.warning("authorization.userinfo_fetch_failed", error=str(exc))
        return None
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.warning("authorization.userinfo_invalid_json")
        return None
    if isinstance(payload, dict):
        return payload
    return None


def fetch_current_userinfo(request: HttpRequest) -> dict[str, Any] | None:
    """Return cached-or-fresh IdP userinfo claims for this authenticated request."""
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return None

    cache_key = _cache_key(user.pk)
    cached = cache.get(cache_key)
    if isinstance(cached, dict):
        return dict(cached)

    token = _access_token_for(user)
    if token is None:
        return None

    claims = _fetch_userinfo_http(token)
    if claims is None:
        return None

    timeout = _cache_timeout()
    if timeout > 0:
        cache.set(cache_key, claims, timeout=timeout)
    return dict(claims)
