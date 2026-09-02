"""Verify IdP bearer JWTs before minting service assertions."""

from __future__ import annotations

from urllib.parse import urlparse

import jwt
from django.conf import settings
from jwt.exceptions import PyJWTError

from django_pyforge.assertion.exceptions import AssertionRefusedError
from django_pyforge.assertion.exceptions import VerifierNotConfiguredError
from django_pyforge.assertion.jwks import get_jwks_key_set
from django_pyforge.assertion.schema import CLAIM_SUB

_ALLOWED_JWKS_SCHEMES = frozenset({"https", "file"})
_JWT_COMPACT_SEGMENTS = 3


def _jwks_url_is_usable(url: str) -> bool:
    cleaned = url.strip()
    if not cleaned:
        return False
    return urlparse(cleaned).scheme in _ALLOWED_JWKS_SCHEMES


def _require_verifier_settings() -> tuple[str, str, str, list[str], float]:
    jwks_url = getattr(settings, "OIDC_JWKS_URL", "")
    jwks_url = jwks_url.strip() if isinstance(jwks_url, str) else ""
    issuer = getattr(settings, "OIDC_ISSUER", "")
    issuer = issuer.strip() if isinstance(issuer, str) else ""
    audience = getattr(settings, "OIDC_AUDIENCE", "")
    audience = audience.strip() if isinstance(audience, str) else ""
    algorithms = getattr(settings, "OIDC_ALGORITHMS", ["RS256"])
    leeway = getattr(settings, "OIDC_LEEWAY_SECONDS", 0.0)
    if (
        not _jwks_url_is_usable(jwks_url)
        or not issuer
        or not audience
        or not isinstance(algorithms, list)
        or not algorithms
    ):
        msg = "OIDC verifier is not configured"
        raise VerifierNotConfiguredError(msg)
    return jwks_url, issuer, audience, list(algorithms), float(leeway)


def _roles_from_claim(payload: dict[str, object], group_claim: str) -> list[str]:
    if group_claim not in payload:
        msg = "IdP bearer is missing group claim"
        raise AssertionRefusedError(msg)
    raw_roles = payload[group_claim]
    if isinstance(raw_roles, str):
        return [raw_roles]
    if isinstance(raw_roles, list):
        if not all(isinstance(item, str) for item in raw_roles):
            msg = "IdP bearer roles are unusable"
            raise AssertionRefusedError(msg)
        return list(raw_roles)
    msg = "IdP bearer roles are unusable"
    raise AssertionRefusedError(msg)


def verify_idp_bearer(token: str) -> tuple[str, list[str]]:
    """Validate an IdP bearer and return verified ``(sub, roles)``."""
    parts = token.split(".")
    if len(parts) != _JWT_COMPACT_SEGMENTS:
        msg = "IdP bearer is not a compact JWT"
        raise AssertionRefusedError(msg)

    jwks_url, issuer, audience, algorithms, leeway = _require_verifier_settings()
    group_claim = getattr(settings, "DJANGO_PYFORGE_GROUP_CLAIM", "groups")
    if not isinstance(group_claim, str) or not group_claim:
        msg = "group claim is not configured"
        raise VerifierNotConfiguredError(msg)

    key = get_jwks_key_set(jwks_url).resolve_key(token)
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            issuer=issuer,
            audience=audience,
            leeway=leeway,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
    except PyJWTError as exc:
        raise AssertionRefusedError from exc

    if not isinstance(payload, dict):
        msg = "IdP bearer payload is not JSON"
        raise AssertionRefusedError(msg)
    sub = payload.get(CLAIM_SUB)
    if not isinstance(sub, str) or not sub:
        msg = "IdP bearer is missing sub"
        raise AssertionRefusedError(msg)
    roles = _roles_from_claim(payload, group_claim)
    return sub, roles
