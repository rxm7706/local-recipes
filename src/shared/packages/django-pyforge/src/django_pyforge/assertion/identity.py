"""Read IdP identity from a bearer payload. Live token-exchange is deferred."""

from __future__ import annotations

import base64
import json

from django_pyforge.assertion.exceptions import AssertionRefusedError
from django_pyforge.assertion.schema import CLAIM_ROLES
from django_pyforge.assertion.schema import CLAIM_SUB

_JWT_COMPACT_SEGMENTS = 3


def identity_from_idp_bearer(token: str) -> tuple[str, list[str]]:
    parts = token.split(".")
    if len(parts) != _JWT_COMPACT_SEGMENTS:
        msg = "IdP bearer is not a compact JWT"
        raise AssertionRefusedError(msg)
    padded = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, json.JSONDecodeError) as exc:
        msg = "IdP bearer payload is not JSON"
        raise AssertionRefusedError(msg) from exc
    if not isinstance(payload, dict):
        msg = "IdP bearer payload is not JSON"
        raise AssertionRefusedError(msg)
    sub = payload.get(CLAIM_SUB)
    if not isinstance(sub, str) or not sub:
        msg = "IdP bearer is missing sub"
        raise AssertionRefusedError(msg)
    raw_roles = payload.get(CLAIM_ROLES, payload.get("groups", []))
    if isinstance(raw_roles, str):
        roles = [raw_roles]
    elif isinstance(raw_roles, list):
        if not all(isinstance(item, str) for item in raw_roles):
            msg = "IdP bearer roles are unusable"
            raise AssertionRefusedError(msg)
        roles = list(raw_roles)
    else:
        msg = "IdP bearer roles are unusable"
        raise AssertionRefusedError(msg)
    return sub, roles
