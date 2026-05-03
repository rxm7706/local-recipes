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


# ── URL resolvers — JFrog/mirror discovery from env + pixi config ──────────
#
# Design: produce an ordered list of candidate base URLs for each upstream
# (conda-forge channel, PyPI Simple, PyPI JSON, GitHub archive, GitHub raw).
# Air-gapped enterprise users (JFrog) get their mirror first; external
# clones fall through to the public default.

import json as _json
import re as _re
import time as _time
import urllib.error
from typing import Iterable

# Public fallback base URLs. The order is fixed: prefix.dev (CDN-backed
# mirror) before anaconda.org (often blocked in air-gapped enterprise
# networks). Note: bare prefix.dev/conda-forge does NOT serve
# current_repodata.json — only repo.prefix.dev/conda-forge does.
_DEFAULT_CONDA_FORGE_FALLBACKS: tuple[str, ...] = (
    "https://repo.prefix.dev/conda-forge",
    "https://conda.anaconda.org/conda-forge",
)

_DEFAULT_PYPI_SIMPLE_FALLBACKS: tuple[str, ...] = (
    "https://pypi.org/simple",
)

_DEFAULT_PYPI_JSON_FALLBACKS: tuple[str, ...] = (
    "https://pypi.org",  # /pypi/<pkg>/json appended by caller
)

_DEFAULT_GITHUB_FALLBACKS: tuple[str, ...] = (
    "https://github.com",
)

_DEFAULT_GITHUB_RAW_FALLBACKS: tuple[str, ...] = (
    "https://raw.githubusercontent.com",
)


def read_pixi_config() -> dict:
    """Read pixi config — first existing file in pixi's own priority order wins.

    Pixi resolves config in this order: project-local → user → system. We
    follow the same chain so this helper honors whatever the developer set.
    Silent-on-error: a malformed config doesn't break callers; we return {}
    and let the public-default fallback paths handle routing.
    """
    try:
        import tomllib
    except ImportError:
        return {}
    candidates = [
        Path(".pixi") / "config.toml",
        Path.home() / ".pixi" / "config.toml",
        Path("/etc/pixi/config.toml"),
    ]
    for p in candidates:
        try:
            if p.is_file():
                with open(p, "rb") as f:
                    return tomllib.load(f)
        except Exception as e:
            _log(f"_http: skipping malformed pixi config at {p}: {e}")
            continue
    return {}


def _dedup_strip(urls: Iterable[str | None]) -> list[str]:
    """De-dup + strip trailing slashes; preserves first-seen order."""
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if not u:
            continue
        u = u.rstrip("/")
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def resolve_conda_forge_urls(config: dict | None = None) -> list[str]:
    """Ordered chain for the conda-forge channel.

    Priority:
      1. CONDA_FORGE_BASE_URL env var
      2. Pixi `mirrors["https://conda.anaconda.org/conda-forge"][*]`
      3. Pixi `default-channels` entries containing "conda-forge"
      4. https://repo.prefix.dev/conda-forge      (public CDN mirror)
      5. https://conda.anaconda.org/conda-forge   (last resort)

    `config` lets callers inject a pre-loaded pixi config (test/mock-friendly);
    if None, calls `read_pixi_config()`.
    """
    cfg = read_pixi_config() if config is None else config
    candidates: list[str | None] = [os.environ.get("CONDA_FORGE_BASE_URL")]

    mirrors = cfg.get("mirrors") if isinstance(cfg, dict) else None
    if isinstance(mirrors, dict):
        for src, targets in mirrors.items():
            if not isinstance(src, str) or not isinstance(targets, list):
                continue
            if src.rstrip("/").endswith("conda.anaconda.org/conda-forge"):
                for t in targets:
                    if isinstance(t, str):
                        candidates.append(t)

    chans = cfg.get("default-channels") if isinstance(cfg, dict) else None
    if isinstance(chans, list):
        for c in chans:
            if isinstance(c, str) and "conda-forge" in c:
                candidates.append(c)

    candidates.extend(_DEFAULT_CONDA_FORGE_FALLBACKS)
    return _dedup_strip(candidates)


def resolve_pypi_simple_urls(config: dict | None = None) -> list[str]:
    """Ordered chain for PyPI Simple v1 index.

    Priority:
      1. PYPI_BASE_URL env var (treated as a Simple-index base, e.g.
         `https://artifactory.example.com/artifactory/api/pypi/pypi/simple`)
      2. Pixi `pypi-config.index-url`
      3. https://pypi.org/simple
    """
    cfg = read_pixi_config() if config is None else config
    candidates: list[str | None] = [os.environ.get("PYPI_BASE_URL")]

    pcfg = cfg.get("pypi-config") if isinstance(cfg, dict) else None
    if isinstance(pcfg, dict):
        idx = pcfg.get("index-url")
        if isinstance(idx, str):
            candidates.append(idx)
        extras = pcfg.get("extra-index-urls")
        if isinstance(extras, list):
            for e in extras:
                if isinstance(e, str):
                    candidates.append(e)

    candidates.extend(_DEFAULT_PYPI_SIMPLE_FALLBACKS)
    return _dedup_strip(candidates)


def resolve_pypi_json_urls(
    package_name: str,
    version: str | None = None,
    config: dict | None = None,
) -> list[str]:
    """Ordered chain of fully-qualified URLs for PyPI JSON metadata.

    Priority for the *base*:
      1. PYPI_JSON_BASE_URL env var (used as `<base>/<pkg>/json`)
      2. Pixi `pypi-config.index-url` with `/simple` stripped — works for
         JFrog setups whose PyPI Remote Repo also serves the JSON metadata
         API at the same parent path.
      3. https://pypi.org

    The path appended is `pypi/<pkg>/json` or `pypi/<pkg>/<version>/json`.
    Returns full URLs ready to fetch.
    """
    cfg = read_pixi_config() if config is None else config
    bases: list[str | None] = [os.environ.get("PYPI_JSON_BASE_URL")]

    pcfg = cfg.get("pypi-config") if isinstance(cfg, dict) else None
    if isinstance(pcfg, dict):
        idx = pcfg.get("index-url")
        if isinstance(idx, str):
            # Strip trailing /simple or /simple/ to derive the API root.
            bases.append(_re.sub(r"/simple/?$", "", idx))

    bases.extend(_DEFAULT_PYPI_JSON_FALLBACKS)
    base_list = _dedup_strip(bases)

    suffix = f"pypi/{package_name}/{version}/json" if version else f"pypi/{package_name}/json"
    return [f"{b}/{suffix}" for b in base_list]


def resolve_github_urls(repo: str, path: str = "") -> list[str]:
    """Ordered chain for github.com archive/tarball/zip URLs.

    repo: 'conda-forge/feedstock-outputs'
    path: '/archive/refs/heads/main.zip' or similar.

    Priority:
      1. GITHUB_BASE_URL env var (e.g., a JFrog Generic Remote pointed at
         github.com)
      2. https://github.com
    """
    bases: list[str | None] = [os.environ.get("GITHUB_BASE_URL")]
    bases.extend(_DEFAULT_GITHUB_FALLBACKS)
    base_list = _dedup_strip(bases)
    return [f"{b}/{repo}{path}" for b in base_list]


def resolve_github_raw_urls(repo: str, ref: str, path: str) -> list[str]:
    """Ordered chain for raw.githubusercontent.com files.

    repo: 'regro/cf-graph-countyfair'
    ref: 'master', 'main', or commit SHA
    path: 'mappings/pypi/name_mapping.yaml'

    Priority:
      1. GITHUB_RAW_BASE_URL env var (JFrog Generic Remote → raw.githubusercontent.com)
      2. https://raw.githubusercontent.com
    """
    bases: list[str | None] = [os.environ.get("GITHUB_RAW_BASE_URL")]
    bases.extend(_DEFAULT_GITHUB_RAW_FALLBACKS)
    base_list = _dedup_strip(bases)
    return [f"{b}/{repo}/{ref}/{path}" for b in base_list]


# ── Generic fetch with fallback chain + retry ──────────────────────────────

def fetch_with_fallback(
    urls: list[str] | str,
    *,
    extra_headers: dict[str, str] | None = None,
    user_agent: str = "conda-forge-expert/1.0",
    timeout: int = 60,
    retries: int = 2,
    return_json: bool = False,
) -> Any:
    """Fetch a URL with fallback chain + retry.

    Iterates through `urls` (a list, or a single string):
      - 4xx (except 408/429): falls through to next URL immediately. The URL
        is wrong, not transiently flaky.
      - 5xx, network errors, timeouts: retries `retries` times with
        exponential backoff, then falls through.

    Returns raw bytes (or parsed JSON if return_json=True). Raises
    RuntimeError if all URLs are exhausted with the last error attached.

    Per-URL chain composition is the caller's job — pair this with
    `resolve_*_urls()` helpers.
    """
    if isinstance(urls, str):
        urls = [urls]
    if not urls:
        raise ValueError("fetch_with_fallback requires at least one URL")

    last_err: Exception | None = None
    for url in urls:
        for attempt in range(retries):
            try:
                req = make_request(url, extra_headers=extra_headers, user_agent=user_agent)
                with open_url(req, timeout=timeout) as resp:
                    data = resp.read()
                    return _json.loads(data) if return_json else data
            except urllib.error.HTTPError as e:
                last_err = e
                if 400 <= e.code < 500 and e.code not in (408, 429):
                    _log(f"_http: {url} → HTTP {e.code}; trying next source")
                    break
                _log(f"_http: {url} attempt {attempt + 1} → {e}; retrying")
                _time.sleep(2 ** attempt)
            except Exception as e:
                last_err = e
                _log(f"_http: {url} attempt {attempt + 1} → {e}; retrying")
                _time.sleep(2 ** attempt)

    raise RuntimeError(
        f"All {len(urls)} source(s) failed; last error: {last_err}"
    )


# ── Logging (stderr, non-intrusive) ─────────────────────────────────────────

def _log(msg: str) -> None:
    """Write a diagnostic message to stderr. Only emitted in verbose/debug mode."""
    if os.environ.get("CFE_DEBUG") or os.environ.get("CONDA_FORGE_EXPERT_DEBUG"):
        print(msg, file=sys.stderr)

