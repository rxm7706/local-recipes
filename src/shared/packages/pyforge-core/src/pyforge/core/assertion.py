"""Host-mint service assertion client (stdlib only).

The CLI never signs locally. It POSTs the caller's IdP bearer to the host
mint view; django-pyforge signs RS256. Tests inject an in-process transport.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable

ALG = "RS256"
AUDIENCE_PREFIX = "mcp:"
CLAIM_AUD = "aud"
CLAIM_DELEGATED_BY = "delegated_by"
CLAIM_EXP = "exp"
CLAIM_IAT = "iat"
CLAIM_ROLES = "roles"
CLAIM_SUB = "sub"
DELEGATED_BY = "pyforge-host"
MAX_TTL_SECONDS = 300

Transport = Callable[[str, dict[str, str], bytes], bytes]


class HostMintError(Exception):
    """Host mint HTTP call failed or returned an unusable body."""


class HostMintClient:
    """Obtain a service assertion by authenticating to the host mint URL."""

    def __init__(self, mint_url: str, *, transport: Transport | None = None) -> None:
        self._mint_url = mint_url
        self._transport = transport

    def emit(self, *, idp_bearer: str, station: str) -> str:
        if "\r" in idp_bearer or "\n" in idp_bearer:
            raise HostMintError
        body = json.dumps({"station": station}).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {idp_bearer}",
            "Content-Type": "application/json",
        }
        raw = (
            self._transport(self._mint_url, headers, body)
            if self._transport is not None
            else self._urllib(headers, body)
        )
        try:
            payload = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
            token = payload["assertion"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise HostMintError from exc
        if not isinstance(token, str) or not token:
            raise HostMintError
        return token

    def _urllib(self, headers: dict[str, str], body: bytes) -> bytes:
        request = urllib.request.Request(  # noqa: S310 -- mint URL is caller-configured
            self._mint_url,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
                payload: bytes = response.read()
                return payload
        except urllib.error.URLError as exc:
            raise HostMintError from exc
