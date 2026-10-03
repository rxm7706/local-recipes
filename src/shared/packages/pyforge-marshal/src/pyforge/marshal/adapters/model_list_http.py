"""HTTP GET for operator-run model-list refresh (Story 84.1, AD-20).

Uses ``http.client`` directly (no redirect following, credentials never
sent to a redirect target). Separate from ``oidc_pkce`` (PKCE login transport).
"""

from __future__ import annotations

import http.client
import ssl
from collections.abc import Mapping

from ..ports.model_list_fetch import HttpGetResult


def _parse_https_url(url: str) -> tuple[str, int, str] | None:
    if not url.startswith("https://"):
        return None
    rest = url.removeprefix("https://")
    host_part, sep, path_part = rest.partition("/")
    path = "/" + path_part if sep else "/"
    if not host_part:
        return None
    if ":" in host_part:
        host, port_text = host_part.rsplit(":", 1)
        try:
            port = int(port_text)
        except ValueError:
            return None
    else:
        host = host_part
        port = 443
    if not host:
        return None
    return host, port, path


def http_get_for_model_list(
    url: str,
    headers: Mapping[str, str],
    *,
    timeout_s: float,
) -> HttpGetResult:
    """One HTTPS GET with explicit status; never raises to the caller."""
    try:
        parsed = _parse_https_url(url)
        if parsed is None:
            return HttpGetResult(status_code=0, body=b"invalid url scheme")
        host, port, path = parsed
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
