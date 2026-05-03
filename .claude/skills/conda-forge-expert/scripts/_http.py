#!/usr/bin/env python3
"""
Enterprise-safe HTTP helpers for conda-forge-expert scripts.

Designed for air-gapped / enterprise environments running JFrog Artifactory
where Python's SSL trust store may be stricter than the OS/curl trust store.

SSL trust priority chain (applied once at process start via inject_ssl_truststore):
  1. REQUESTS_CA_BUNDLE / SSL_CERT_FILE env vars  — explicit enterprise CA bundle
  2. truststore package injection                  — system OS trust anchors (macOS/Windows/Linux)
  3. Python default (certifi bundle)               — bundled Mozilla CA store

Authentication priority chain (per-request via make_request / netrc_credentials):
  1. JFROG_API_KEY env var      → X-JFrog-Art-Api header
  2. JFROG_USERNAME + PASSWORD  → Basic auth header
  3. ~/.netrc (or $NETRC)       → Basic auth from netrc entry for the host
  4. GITHUB_TOKEN / GH_TOKEN    → Bearer auth (for github.com)
  5. Unauthenticated

Usage in scripts (lazy, safe to call multiple times):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from _http import inject_ssl_truststore, make_request, open_url

    inject_ssl_truststore()   # call once near script top-level

    req = make_request(url)   # builds urllib.request.Request with auth headers
    with open_url(req, timeout=30) as resp:
        data = resp.read()
"""
from __future__ import annotations

import netrc as _netrc_mod
import os
import ssl
import sys
import urllib.request
from base64 import b64encode
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# ── SSL / truststore injection ───────────────────────────────────────────────

_TRUSTSTORE_INJECTED = False


def inject_ssl_truststore() -> bool:
    """
    Inject the system OS trust store into Python's ssl module.

    Priority:
      1. REQUESTS_CA_BUNDLE / SSL_CERT_FILE — already handled by urllib automatically
         if set, so only need to notify.
      2. truststore.inject_into_ssl() — hooks system trust into ssl.create_default_context()
      3. No-op if truststore is not installed.

    Returns True if truststore injection was performed, False if skipped.
    Safe to call multiple times (idempotent).
    """
    global _TRUSTSTORE_INJECTED
    if _TRUSTSTORE_INJECTED:
        return True

    # Explicit CA bundle env vars — urllib/ssl picks these up automatically;
    # just log so users know it's active.
    for var in ("REQUESTS_CA_BUNDLE", "SSL_CERT_FILE"):
        if os.environ.get(var):
            _log(f"_http: using CA bundle from ${var}={os.environ[var]}")

    try:
        import truststore  # type: ignore[import-not-found]
        truststore.inject_into_ssl()
        _TRUSTSTORE_INJECTED = True
        _log("_http: truststore injected system SSL trust anchors")
        return True
    except ImportError:
        _log(
            "_http: truststore not available — using default certifi bundle "
            "(set REQUESTS_CA_BUNDLE for enterprise CA, or: pip install truststore)"
        )
        return False
    except Exception as exc:
        _log(f"_http: truststore injection failed ({exc}) — continuing without it")
        return False


# ── .netrc credential lookup ─────────────────────────────────────────────────

def netrc_credentials(url: str) -> tuple[str, str] | None:
    """
    Look up (username, password) for the given URL's hostname in ~/.netrc.

    Respects the $NETRC environment variable for non-default netrc file path.
    Returns None if no entry is found or netrc cannot be read.
    """
    host = urlparse(url).netloc.split(":")[0]  # strip port number, keep hostname
    if not host:
        return None

    netrc_path = os.environ.get("NETRC") or Path.home() / ".netrc"
    try:
        nrc = _netrc_mod.netrc(str(netrc_path))
        entry = nrc.authenticators(host)
        if entry:
            login, _, password = entry
            if login and password:
                return (login, password)
    except FileNotFoundError:
        pass  # no .netrc file — normal in many environments
    except _netrc_mod.NetrcParseError as exc:
        _log(f"_http: .netrc parse error ({exc}) — skipping credential lookup")
    except OSError as exc:
        _log(f"_http: .netrc read error ({exc}) — skipping credential lookup")
    return None


# ── Request builder with enterprise auth ─────────────────────────────────────

def make_request(
    url: str,
    extra_headers: dict[str, str] | None = None,
    user_agent: str = "conda-forge-expert/1.0",
) -> urllib.request.Request:
    """
    Build a urllib.request.Request with enterprise authentication headers.

    Auth priority (first match wins):
      1. JFROG_API_KEY       → X-JFrog-Art-Api header
      2. JFROG_USERNAME+PWD  → Basic auth header
      3. GITHUB_TOKEN/GH_TOKEN (github.com) → Bearer header
      4. ~/.netrc lookup     → Basic auth header
      5. Unauthenticated
    """
    headers: dict[str, str] = {"User-Agent": user_agent}
    if extra_headers:
        headers.update(extra_headers)

    parsed = urlparse(url)
    host = parsed.netloc.lower()

    # JFrog Artifactory auth (env vars take precedence over .netrc)
    if os.environ.get("JFROG_API_KEY"):
        headers["X-JFrog-Art-Api"] = os.environ["JFROG_API_KEY"]
    elif os.environ.get("JFROG_USERNAME") and os.environ.get("JFROG_PASSWORD"):
        creds = f"{os.environ['JFROG_USERNAME']}:{os.environ['JFROG_PASSWORD']}"
        headers["Authorization"] = "Basic " + b64encode(creds.encode()).decode()
    # GitHub API auth
    elif "github.com" in host or "api.github.com" in host:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif (creds_tuple := netrc_credentials(url)):
            login, password = creds_tuple
            creds_str = f"{login}:{password}"
            headers["Authorization"] = "Basic " + b64encode(creds_str.encode()).decode()
    # Generic .netrc fallback (covers Artifactory, Nexus, GitLab, etc.)
    elif "Authorization" not in headers:
        if (creds_tuple := netrc_credentials(url)):
            login, password = creds_tuple
            creds_str = f"{login}:{password}"
            headers["Authorization"] = "Basic " + b64encode(creds_str.encode()).decode()

    return urllib.request.Request(url, headers=headers)


def open_url(request: urllib.request.Request, timeout: int = 30) -> Any:
    """
    Wrapper around urllib.request.urlopen that injects truststore automatically.

    Always calls inject_ssl_truststore() before opening — safe to call repeatedly
    (idempotent). Returns the http.client.HTTPResponse context manager.
    """
    inject_ssl_truststore()
    return urllib.request.urlopen(request, timeout=timeout)


# ── Logging (stderr, non-intrusive) ─────────────────────────────────────────

def _log(msg: str) -> None:
    """Write a diagnostic message to stderr. Only emitted in verbose/debug mode."""
    if os.environ.get("CFE_DEBUG") or os.environ.get("CONDA_FORGE_EXPERT_DEBUG"):
        print(msg, file=sys.stderr)

