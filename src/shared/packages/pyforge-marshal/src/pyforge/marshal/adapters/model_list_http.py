"""HTTP GET for operator-run model-list refresh (Story 84.1, AD-20).

Separate from ``oidc_pkce`` (PKCE login transport) so listing timeouts and
status mapping stay owned here.
"""

from __future__ import annotations

from collections.abc import Mapping

from pyforge.core.client import StationClientError, urllib_http_get

from ..ports.model_list_fetch import HttpGetResult


def http_get_for_model_list(
    url: str,
    headers: Mapping[str, str],
    *,
    timeout_s: float,
) -> HttpGetResult:
    """One GET with explicit status; never raises to the caller."""
    try:
        response = urllib_http_get(url, dict(headers), timeout_s=timeout_s)
    except (ValueError, StationClientError) as exc:
        detail = str(exc).strip() or "request failed"
        if "timeout" in detail.lower():
            return HttpGetResult(status_code=0, body=b"timeout")
        return HttpGetResult(status_code=0, body=detail.encode("utf-8"))
    return HttpGetResult(status_code=response.status_code, body=response.body)
