"""HTTP GET for operator-run model-list refresh (Story 84.1, AD-20).

Uses ``http.client`` directly (no redirect following, credentials never
sent to a redirect target). Separate from ``oidc_pkce`` (PKCE login transport).
"""

from __future__ import annotations

import http.client
import ssl
from collections.abc import Mapping
from urllib.parse import urlparse

from ..ports.model_list_fetch import HttpGetResult


def http_get_for_model_list(
    url: str,
    headers: Mapping[str, str],
    *,
    timeout_s: float,
) -> HttpGetResult:
    """One HTTPS GET with explicit status; never raises to the caller."""
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            return HttpGetResult(status_code=0, body=b"invalid url scheme")
        host = parsed.hostname
        if not host:
            return HttpGetResult(status_code=0, body=b"invalid url")
        port = parsed.port if parsed.port is not None else 443
        path = parsed.path or "/"
        if parsed.query:
            path = path + "?" + parsed.query
        context = ssl.create_default_context()
        conn = http.client.HTTPSConnection(host, port, timeout=timeout_s, context=context)
        try:
            conn.request("GET", path, headers=dict(headers))
            response = conn.getresponse()
            status = int(response.status)
            body = response.read()
        finally:
            conn.close()
        if 300 <= status < 400:
            return HttpGetResult(status_code=0, body=b"redirect not followed")
        return HttpGetResult(status_code=status, body=body)
    except TimeoutError:
        return HttpGetResult(status_code=0, body=b"timeout")
    except (OSError, http.client.HTTPException, ValueError):
        return HttpGetResult(status_code=0, body=b"network error")
