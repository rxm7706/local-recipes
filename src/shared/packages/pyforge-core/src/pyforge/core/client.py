"""Host-relative station API client (stdlib only, CAP-6 / Story 43.2).

Portals reach this through ``django-pyforge``; the CLI and tests may call it
directly. HTTP is performed via an injectable transport so ``pyforge-core``
stays a zero third-party runtime dependency (``tests/meta/test_leaf_constraint``).
Callers that want ``httpx`` supply a transport that uses it.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

API_VERSION_HEADER = "X-PyForge-API-Version"

Transport = Callable[[str, str, dict[str, str], bytes | None], bytes]


class StationClientError(Exception):
    """Station API HTTP call failed or returned an unusable body."""


class PyForgeStationClient:
    """Type-safe host-relative client for ``/stations/<name>/api/v<N>/`` routes."""

    def __init__(
        self,
        *,
        station: str,
        version: int = 1,
        base_url: str = "",
        assertion: str = "",
        transport: Transport | None = None,
    ) -> None:
        self._station = station.strip()
        self._version = version
        self._base_url = base_url.rstrip("/")
        self._assertion = assertion
        self._transport = transport

    @property
    def station(self) -> str:
        return self._station

    @property
    def version(self) -> int:
        return self._version

    def prefix(self) -> str:
        return f"/stations/{self._station}/api/v{self._version}"

    def build_url(self, path: str) -> str:
        """Build an absolute URL for a route relative to the station API root."""
        relative = path if path.startswith("/") else f"/{path}"
        if not relative.startswith(self.prefix()):
            relative = f"{self.prefix()}{relative}"
        return f"{self._base_url}{relative}"

    def build_headers(self, *, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            API_VERSION_HEADER: str(self._version),
            "Accept": "application/json",
        }
        if self._assertion:
            headers["Authorization"] = f"Bearer {self._assertion}"
        if extra:
            headers.update(extra)
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> bytes:
        url = self.build_url(path)
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = self.build_headers(extra=extra_headers)
        if body is not None:
            headers.setdefault("Content-Type", "application/json")
        if self._transport is not None:
            return self._transport(method, url, headers, body)
        return self._urllib(method, url, headers, body)

    def get(self, path: str, *, extra_headers: dict[str, str] | None = None) -> bytes:
        return self.request("GET", path, extra_headers=extra_headers)

    def post(
        self,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> bytes:
        return self.request("POST", path, payload=payload, extra_headers=extra_headers)

    def _urllib(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
    ) -> bytes:
        request = urllib.request.Request(  # noqa: S310 -- URL is caller-configured
            url,
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
                payload: bytes = response.read()
                return payload
        except urllib.error.URLError as exc:
            raise StationClientError from exc


def urllib_request(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes | None,
) -> bytes:
    """Perform one stdlib HTTP request (Story 33.14 shared transport)."""
    request = urllib.request.Request(  # noqa: S310 -- URL is caller-configured
        url,
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            payload: bytes = response.read()
            return payload
    except urllib.error.URLError as exc:
        raise StationClientError from exc


def form_urlencode(params: dict[str, str]) -> str:
    """URL-encode form fields for OIDC token exchange."""
    return urllib.parse.urlencode(params)


def parse_request_path(path: str) -> tuple[str, dict[str, list[str]]]:
    """Split an HTTP path into its pathname and query parameters."""
    parsed = urllib.parse.urlparse(path)
    return parsed.path, urllib.parse.parse_qs(parsed.query)
