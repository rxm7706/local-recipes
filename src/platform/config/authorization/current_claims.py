"""Current IdP token claims for this request (FR-31 / canopy AD-15).

Live authority is the token on the request: a test snapshot, a userinfo hook,
or the claims document stored at login. The login-time role *list* is not used.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing import Any

from django.conf import settings
from django_pyforge.roles import IDP_TOKEN_CLAIMS_SESSION_KEY

if TYPE_CHECKING:
    from django.http import HttpRequest

__all__ = ["fetch_current_idp_claims"]


def fetch_current_idp_claims(request: HttpRequest) -> dict[str, Any] | None:
    """Return IdP claims for this request, or None when none are presented."""
    snapshot = getattr(settings, "IDP_CLAIMS_SNAPSHOT", None)
    if isinstance(snapshot, Mapping):
        return dict(snapshot)
    userinfo = getattr(settings, "IDP_USERINFO", None)
    if callable(userinfo):
        got = userinfo(request)
        if isinstance(got, Mapping):
            return dict(got)
    session = getattr(request, "session", None)
    if session is not None:
        stored = session.get(IDP_TOKEN_CLAIMS_SESSION_KEY)
        if isinstance(stored, Mapping):
            return dict(stored)
    return None
