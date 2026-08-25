"""Request-scoped IdP roles for chrome reachability (canopy AD-15).

Roles are re-read from this request's token claims. Django ``User.groups``
and the login-time session role list are never the authority.
"""

from __future__ import annotations

from collections.abc import Callable
from collections.abc import Mapping
from typing import Any

from django.conf import settings
from django.http import HttpRequest
from django.utils.module_loading import import_string

IDP_TOKEN_ROLES_SESSION_KEY = "idp_token_roles"
IDP_TOKEN_CLAIMS_SESSION_KEY = "idp_token_claims"
IDP_TOKEN_CLAIMS_ATTR = "idp_token_claims"

_GROUP_CLAIM_SETTING = "DJANGO_PYFORGE_GROUP_CLAIM"
_CLAIMS_GETTER_SETTING = "DJANGO_PYFORGE_IDP_CLAIMS_GETTER"


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


def group_claim_name() -> str:
    name = getattr(settings, _GROUP_CLAIM_SETTING, None)
    return name if isinstance(name, str) and name else "groups"


def roles_from_claims(claims: Mapping[str, Any]) -> list[str]:
    """Return group-claim names from a token claims mapping."""
    return role_names(claims.get(group_claim_name()))


def _claims_getter() -> Callable[[HttpRequest], Any] | None:
    spec = getattr(settings, _CLAIMS_GETTER_SETTING, None)
    if spec is None:
        return None
    if callable(spec):
        return spec
    if isinstance(spec, str) and spec:
        loaded = import_string(spec)
        if callable(loaded):
            return loaded
    return None


def claims_from_request(request: HttpRequest) -> Mapping[str, Any] | None:
    """Return this request's IdP token claims, or None if none were presented."""
    explicit = getattr(request, IDP_TOKEN_CLAIMS_ATTR, None)
    if isinstance(explicit, Mapping):
        return explicit
    getter = _claims_getter()
    if getter is None:
        return None
    got = getter(request)
    if isinstance(got, Mapping):
        return got
    return None


def roles_from_request(request: HttpRequest) -> frozenset[str]:
    """Return station-name roles asserted on this request's token."""
    claims = claims_from_request(request)
    if claims is not None:
        return frozenset(roles_from_claims(claims))
    raw: Any = getattr(request, "idp_roles", None)
    if raw is None:
        return frozenset()
    return frozenset(role_names(raw))
