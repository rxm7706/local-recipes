"""Service-assertion claim names and bounds (canopy AD-7)."""

from __future__ import annotations

ALG = "RS256"
AUDIENCE_PREFIX = "mcp:"
EVENTS_AUDIENCE = "mcp:events"
CLAIM_AUD = "aud"
CLAIM_DELEGATED_BY = "delegated_by"
CLAIM_EXP = "exp"
CLAIM_IAT = "iat"
CLAIM_ROLES = "roles"
CLAIM_SUB = "sub"
DELEGATED_BY = "pyforge-host"
MAX_TTL_SECONDS = 300


def audience_for(station: str) -> str:
    name = station.strip()
    if not name:
        msg = "station is empty"
        raise ValueError(msg)
    return f"{AUDIENCE_PREFIX}{name}"
