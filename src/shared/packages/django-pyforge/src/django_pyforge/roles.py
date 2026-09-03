"""Request-scoped IdP roles for chrome reachability (canopy AD-15).

Roles are re-read from this request's token claims. Django ``User.groups``
and the login-time session role list are never the authority.

Story 42.5 (red-team X-3 / B-6 / R-13): capability, tenant and admin values
live in one configurable group claim under prefixed namespaces:

* ``pyforge:station:<name>`` — reachability for that station slug
* ``pyforge:tenant:<id>`` — Lane 3 row-slicing tenant (never a station slug)
* ``pyforge:admin`` — platform administrator (all stations)

Bare station slugs are refused unless ``DJANGO_PYFORGE_LEGACY_BARE_ROLES=1``,
which logs a one-release deprecation warning per distinct bare name.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.http import HttpRequest
from django.utils.module_loading import import_string

from django_pyforge.events.constants import STATION_TOKENS

IDP_TOKEN_ROLES_SESSION_KEY = "idp_token_roles"
IDP_TOKEN_CLAIMS_SESSION_KEY = "idp_token_claims"
IDP_TOKEN_CLAIMS_ATTR = "idp_token_claims"

_GROUP_CLAIM_SETTING = "DJANGO_PYFORGE_GROUP_CLAIM"
_CLAIMS_GETTER_SETTING = "DJANGO_PYFORGE_IDP_CLAIMS_GETTER"
_LEGACY_BARE_ROLES_SETTING = "DJANGO_PYFORGE_LEGACY_BARE_ROLES"

PREFIX_STATION = "pyforge:station:"
PREFIX_TENANT = "pyforge:tenant:"
ROLE_ADMIN = "pyforge:admin"

# Station slugs that must never be accepted bare once legacy mode is off.
_KNOWN_STATION_SLUGS = STATION_TOKENS | frozenset({"chrome-probe", "infra-probe", "flags"})

_logger = logging.getLogger(__name__)
_legacy_bare_logged: set[str] = set()


@dataclass(frozen=True)
class ParsedRoles:
    """Structured view of one token's group-claim values."""

    stations: frozenset[str]
    tenants: frozenset[str]
    is_admin: bool


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


def prefixed_station(name: str) -> str:
    """Return the canonical capability prefix for a station slug."""
    return f"{PREFIX_STATION}{name}"


def prefixed_tenant(tenant_id: str) -> str:
    """Return the canonical tenant prefix for a row-slicing tenant id."""
    return f"{PREFIX_TENANT}{tenant_id}"


def legacy_bare_roles_enabled() -> bool:
    """True when bare station slugs are still accepted (one-release migration)."""
    env = os.environ.get("DJANGO_PYFORGE_LEGACY_BARE_ROLES", "").strip()
    if env == "1":
        return True
    return bool(getattr(settings, _LEGACY_BARE_ROLES_SETTING, False))


def parse_role_claims(raw_roles: Iterable[str]) -> ParsedRoles:
    """Parse prefixed group-claim values; refuse bare station slugs by default."""
    stations: set[str] = set()
    tenants: set[str] = set()
    is_admin = False
    legacy = legacy_bare_roles_enabled()
    for raw in raw_roles:
        role = raw.strip()
        if not role:
            continue
        if role == ROLE_ADMIN:
            is_admin = True
            continue
        if role.startswith(PREFIX_STATION):
            stations.add(role.removeprefix(PREFIX_STATION))
            continue
        if role.startswith(PREFIX_TENANT):
            tenants.add(role.removeprefix(PREFIX_TENANT))
            continue
        if role in _KNOWN_STATION_SLUGS:
            if legacy:
                if role not in _legacy_bare_logged:
                    _legacy_bare_logged.add(role)
                    _logger.warning(
                        "roles.legacy_bare_station",
                        extra={
                            "event": "roles.legacy_bare_station",
                            "station": role,
                        },
                    )
                stations.add(role)
            continue
    return ParsedRoles(
        stations=frozenset(stations),
        tenants=frozenset(tenants),
        is_admin=is_admin,
    )


def station_roles_from_parsed(parsed: ParsedRoles) -> frozenset[str]:
    """Station slugs this parsed token may reach."""
    if parsed.is_admin:
        return _KNOWN_STATION_SLUGS
    return parsed.stations


def station_granted(station: str, raw_roles: Iterable[str]) -> bool:
    """True when ``raw_roles`` grants reachability for ``station``."""
    parsed = parse_role_claims(role_names(raw_roles))
    if parsed.is_admin:
        return True
    return station in parsed.stations


def unique_tenant_from_raw(raw_roles: Iterable[str]) -> str:
    """The sole tenant id, or ``""`` when zero or multiple tenants are asserted."""
    parsed = parse_role_claims(role_names(raw_roles))
    if len(parsed.tenants) != 1:
        return ""
    return next(iter(parsed.tenants))


def group_claim_name() -> str:
    name = getattr(settings, _GROUP_CLAIM_SETTING, None)
    return name if isinstance(name, str) and name else "groups"


def roles_from_claims(claims: Mapping[str, Any]) -> list[str]:
    """Return raw group-claim names from a token claims mapping."""
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


def _raw_roles_from_request(request: HttpRequest) -> list[str]:
    claims = claims_from_request(request)
    if claims is not None:
        return roles_from_claims(claims)
    raw: Any = getattr(request, "idp_roles", None)
    return role_names(raw)


def roles_from_request(request: HttpRequest) -> frozenset[str]:
    """Return station-name roles asserted on this request's token."""
    return station_roles_from_parsed(parse_role_claims(_raw_roles_from_request(request)))


def tenant_from_request(request: HttpRequest) -> str | None:
    """Return the unique tenant id on this request, or None when ambiguous."""
    parsed = parse_role_claims(_raw_roles_from_request(request))
    if len(parsed.tenants) != 1:
        return None
    return next(iter(parsed.tenants))
