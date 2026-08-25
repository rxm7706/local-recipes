"""Request-scoped IdP roles for chrome reachability (canopy AD-15).

Roles are re-read from this request's token — ``request.idp_roles`` and/or
the session key populated from this request's IdP claims. Django
``User.groups`` is never the switcher's authority.
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest

IDP_TOKEN_ROLES_SESSION_KEY = "idp_token_roles"


def role_names(raw: Any) -> list[str]:
    """Normalize a token-roles payload to a list of role strings."""
    if not raw:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, bytes | bytearray):
        return []
    try:
        return [str(item) for item in raw]
    except TypeError:
        return []


def roles_from_request(request: HttpRequest) -> frozenset[str]:
    """Return station-name roles asserted on this request's token."""
    raw: Any = getattr(request, "idp_roles", None)
    if raw is None:
        session = getattr(request, "session", None)
        if session is not None:
            raw = session.get(IDP_TOKEN_ROLES_SESSION_KEY)
    return frozenset(role_names(raw))
