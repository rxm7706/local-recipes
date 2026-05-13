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

import contextlib as _contextlib
import netrc as _netrc_mod
import os
import sys
import urllib.request
from base64 import b64encode
from pathlib import Path
from typing import Any
from urllib.parse import quote as _url_quote, urlparse

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


# ── Atomic file writes ──────────────────────────────────────────────────────

@_contextlib.contextmanager
def atomic_writer(path: str | Path, mode: str = "w", **kwargs: Any):
    """Context manager for crash-safe file writes.

    Writes to a `.tmp` sibling of `path`, fsyncs, then atomically renames into
    place via `os.replace`. An interrupt (SIGINT, OOM, power loss) during the
    write leaves the prior contents of `path` intact rather than truncating
    it — a problem we'd hit when `json.dump` was writing directly to the
    final path and a partial JSON file would then fail to load on next run.

    On exception inside the `with` block, the `.tmp` file is unlinked and
    `path` is untouched.

    Usage:
        with atomic_writer(cache_path) as f:
            json.dump(obj, f)

        with atomic_writer(cache_path, "wb") as f:
            f.write(payload_bytes)

    The parent directory is created if missing.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Use a sibling .tmp file so os.replace is on the same filesystem (atomic).
    tmp = p.with_suffix(p.suffix + ".tmp")
    f = open(tmp, mode, **kwargs)
    try:
        yield f
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            # fsync isn't supported on every backing FS (e.g. some tmpfs
            # / network mounts); the rename still happens, just without
            # the durability guarantee.
            pass
        f.close()
        os.replace(tmp, p)
    except Exception:
        try:
            f.close()
        except Exception:
            pass
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise


def atomic_write_bytes(path: str | Path, data: bytes) -> None:
    """Atomic equivalent of `Path(path).write_bytes(data)`."""
    with atomic_writer(path, "wb") as f:
        f.write(data)


def atomic_write_text(path: str | Path, text: str, *, encoding: str = "utf-8") -> None:
    """Atomic equivalent of `Path(path).write_text(text)`."""
    with atomic_writer(path, "w", encoding=encoding) as f:
        f.write(text)


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

def auth_headers_for(url: str) -> dict[str, str]:
    """Build the enterprise auth headers for `url`.

    Auth priority (first match wins):
      1. JFROG_API_KEY       → X-JFrog-Art-Api header
      2. JFROG_USERNAME+PWD  → Basic auth header
      3. GITHUB_TOKEN/GH_TOKEN (github.com) → Bearer header
      4. ~/.netrc lookup     → Basic auth header
      5. Unauthenticated     → empty dict

    Pure function — no User-Agent, no extra headers, no urllib coupling.
    Use this for `requests`-based callers; `make_request` wraps it for the
    urllib path. Both paths share the same auth-resolution semantics.
    """
    headers: dict[str, str] = {}
    host = urlparse(url).netloc.lower()

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
    else:
        if (creds_tuple := netrc_credentials(url)):
            login, password = creds_tuple
            creds_str = f"{login}:{password}"
            headers["Authorization"] = "Basic " + b64encode(creds_str.encode()).decode()

    return headers


def make_request(
    url: str,
    extra_headers: dict[str, str] | None = None,
    user_agent: str = "conda-forge-expert/1.0",
) -> urllib.request.Request:
    """
    Build a urllib.request.Request with enterprise authentication headers.

    Auth chain delegated to `auth_headers_for(url)` so the urllib and
    `requests` paths share the same semantics.
    """
    headers: dict[str, str] = {"User-Agent": user_agent}
    if extra_headers:
        headers.update(extra_headers)
    # Caller-supplied Authorization wins over the auto-resolved one.
    auto = auth_headers_for(url)
    for k, v in auto.items():
        headers.setdefault(k, v)
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

_DEFAULT_NPM_FALLBACKS: tuple[str, ...] = (
    "https://registry.npmjs.org",
)

_DEFAULT_CRAN_FALLBACKS: tuple[str, ...] = (
    "https://crandb.r-pkg.org",
)

_DEFAULT_CPAN_FALLBACKS: tuple[str, ...] = (
    "https://fastapi.metacpan.org",
)

_DEFAULT_LUAROCKS_FALLBACKS: tuple[str, ...] = (
    "https://luarocks.org",
)

_DEFAULT_CRATES_FALLBACKS: tuple[str, ...] = (
    "https://crates.io",
)

_DEFAULT_RUBYGEMS_FALLBACKS: tuple[str, ...] = (
    "https://rubygems.org",
)

_DEFAULT_MAVEN_FALLBACKS: tuple[str, ...] = (
    "https://search.maven.org",
)

_DEFAULT_NUGET_FALLBACKS: tuple[str, ...] = (
    "https://api.nuget.org",
)

_DEFAULT_GITHUB_API_FALLBACKS: tuple[str, ...] = (
    "https://api.github.com",
)

_DEFAULT_GITLAB_API_FALLBACKS: tuple[str, ...] = (
    "https://gitlab.com/api/v4",
)

_DEFAULT_CODEBERG_API_FALLBACKS: tuple[str, ...] = (
    "https://codeberg.org/api/v1",
)

_DEFAULT_S3_PARQUET_BASE: str = "https://anaconda-package-data.s3.amazonaws.com"
_S3_PARQUET_PREFIX: str = "conda/monthly"
_S3_PARQUET_KEY_RE = _re.compile(
    r"^" + _re.escape(_S3_PARQUET_PREFIX) + r"/(\d{4})/(\d{4}-\d{2})\.parquet$"
)
_S3_MONTH_RE = _re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


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


def resolve_npm_urls(package_name: str) -> list[str]:
    """Ordered chain of fully-qualified URLs for npm registry metadata.

    Priority:
      1. NPM_BASE_URL env var (project convention; matches GITHUB_BASE_URL /
         PYPI_BASE_URL style — e.g. a JFrog Artifactory npm Remote Repo:
         `https://artifactory.example.com/artifactory/api/npm/npm/`)
      2. npm_config_registry / NPM_CONFIG_REGISTRY env var — the standard
         npm CLI override (set by `npm config set registry <url>` or exported
         by enterprise dotfiles)
      3. https://registry.npmjs.org (public fallback)

    `package_name` is appended verbatim (caller pre-encodes scoped names as
    needed — e.g. `@scope%2Fname`). Returns full URLs ready to fetch.
    """
    bases: list[str | None] = [
        os.environ.get("NPM_BASE_URL"),
        os.environ.get("npm_config_registry"),
        os.environ.get("NPM_CONFIG_REGISTRY"),
    ]
    bases.extend(_DEFAULT_NPM_FALLBACKS)
    base_list = _dedup_strip(bases)
    return [f"{b}/{package_name}" for b in base_list]


def resolve_cran_urls(name: str) -> list[str]:
    """CRAN package metadata via crandb.r-pkg.org (JSON facade).

    Priority: CRAN_BASE_URL env → public crandb. Returns `<base>/<name>`.
    """
    bases: list[str | None] = [os.environ.get("CRAN_BASE_URL")]
    bases.extend(_DEFAULT_CRAN_FALLBACKS)
    base_list = _dedup_strip(bases)
    return [f"{b}/{name}" for b in base_list]


def resolve_cpan_urls(dist: str) -> list[str]:
    """CPAN release metadata via fastapi.metacpan.org.

    Priority: CPAN_BASE_URL env → public fastapi.metacpan.org.
    Returns `<base>/v1/release/<dist>`.
    """
    bases: list[str | None] = [os.environ.get("CPAN_BASE_URL")]
    bases.extend(_DEFAULT_CPAN_FALLBACKS)
    base_list = _dedup_strip(bases)
    return [f"{b}/v1/release/{dist}" for b in base_list]


def resolve_luarocks_urls(name: str) -> list[str]:
    """LuaRocks module page (HTML, not JSON).

    Priority: LUAROCKS_BASE_URL env → public luarocks.org.
    Returns `<base>/m/<name>`.
    """
    bases: list[str | None] = [os.environ.get("LUAROCKS_BASE_URL")]
    bases.extend(_DEFAULT_LUAROCKS_FALLBACKS)
    base_list = _dedup_strip(bases)
    return [f"{b}/m/{name}" for b in base_list]


def resolve_crates_urls(name: str) -> list[str]:
    """crates.io crate metadata.

    Priority: CRATES_BASE_URL env → public crates.io.
    Returns `<base>/api/v1/crates/<name>`. crates.io documents a 1 req/sec
    rate limit — phase callers should keep concurrency at 1.
    """
    bases: list[str | None] = [os.environ.get("CRATES_BASE_URL")]
    bases.extend(_DEFAULT_CRATES_FALLBACKS)
    base_list = _dedup_strip(bases)
    return [f"{b}/api/v1/crates/{name}" for b in base_list]


def resolve_rubygems_urls(name: str) -> list[str]:
    """RubyGems gem metadata.

    Priority: RUBYGEMS_BASE_URL env → public rubygems.org.
    Returns `<base>/api/v1/gems/<name>.json`. RubyGems documents a
    ~1 req/sec rate limit — phase callers should keep concurrency at 1.
    """
    bases: list[str | None] = [os.environ.get("RUBYGEMS_BASE_URL")]
    bases.extend(_DEFAULT_RUBYGEMS_FALLBACKS)
    base_list = _dedup_strip(bases)
    return [f"{b}/api/v1/gems/{name}.json" for b in base_list]


def resolve_maven_urls(query_path: str) -> list[str]:
    """Maven Central search (Solr).

    Priority: MAVEN_BASE_URL env → public search.maven.org. `query_path`
    is everything after the base (e.g. `solrsearch/select?q=...&wt=json`)
    so callers retain control of query string composition.
    """
    bases: list[str | None] = [os.environ.get("MAVEN_BASE_URL")]
    bases.extend(_DEFAULT_MAVEN_FALLBACKS)
    base_list = _dedup_strip(bases)
    return [f"{b}/{query_path}" for b in base_list]


def resolve_nuget_urls(package_name: str) -> list[str]:
    """NuGet flat-container index (CDN-backed; lowercase package id).

    Priority: NUGET_BASE_URL env → public api.nuget.org.
    Returns `<base>/v3-flatcontainer/<name-lowercase>/index.json`.
    """
    bases: list[str | None] = [os.environ.get("NUGET_BASE_URL")]
    bases.extend(_DEFAULT_NUGET_FALLBACKS)
    base_list = _dedup_strip(bases)
    suffix = f"v3-flatcontainer/{package_name.lower()}/index.json"
    return [f"{b}/{suffix}" for b in base_list]


def resolve_github_api_urls(path_suffix: str = "") -> list[str]:
    """GitHub API host (`api.github.com`) — both REST and GraphQL.

    Priority: GITHUB_API_BASE_URL env → public api.github.com. For
    GitHub Enterprise Server, set the env to ``https://<ghes>/api`` (the
    `/graphql` endpoint lands under the same root). `path_suffix` is
    appended verbatim — pass `"graphql"` for GraphQL or
    `"repos/<o>/<r>/releases/latest"` for REST.

    Note: `resolve_github_urls` (existing) covers archive/tarball URLs
    on github.com proper — distinct concern from this API host resolver.
    """
    bases: list[str | None] = [os.environ.get("GITHUB_API_BASE_URL")]
    bases.extend(_DEFAULT_GITHUB_API_FALLBACKS)
    base_list = _dedup_strip(bases)
    if not path_suffix:
        return base_list
    return [f"{b}/{path_suffix.lstrip('/')}" for b in base_list]


def resolve_gitlab_api_urls(path_suffix: str = "") -> list[str]:
    """GitLab API (REST v4).

    Priority: GITLAB_API_BASE_URL env → public `gitlab.com/api/v4`. For
    self-hosted GitLab CE/EE set the env to
    ``https://<your-gitlab>/api/v4`` — the path layout is identical.
    `path_suffix` is appended verbatim (e.g. ``projects/<urlencoded>/releases?per_page=1``).
    """
    bases: list[str | None] = [os.environ.get("GITLAB_API_BASE_URL")]
    bases.extend(_DEFAULT_GITLAB_API_FALLBACKS)
    base_list = _dedup_strip(bases)
    if not path_suffix:
        return base_list
    return [f"{b}/{path_suffix.lstrip('/')}" for b in base_list]


def resolve_codeberg_api_urls(path_suffix: str = "") -> list[str]:
    """Codeberg API (Gitea-compatible v1).

    Priority: CODEBERG_API_BASE_URL env → public `codeberg.org/api/v1`.
    Other Gitea-compatible instances (Forgejo, self-hosted Gitea) use
    the same `/api/v1/repos/...` path layout; set the env to point at
    them. `path_suffix` is appended verbatim.
    """
    bases: list[str | None] = [os.environ.get("CODEBERG_API_BASE_URL")]
    bases.extend(_DEFAULT_CODEBERG_API_FALLBACKS)
    base_list = _dedup_strip(bases)
    if not path_suffix:
        return base_list
    return [f"{b}/{path_suffix.lstrip('/')}" for b in base_list]


def resolve_s3_parquet_urls(month: str) -> list[str]:
    """Ordered chain for `anaconda-package-data` S3 monthly parquet files.

    month: 'YYYY-MM' (e.g. '2026-04'). The parquet layout is
    `conda/monthly/<YYYY>/<YYYY-MM>.parquet`.

    Priority:
      1. S3_PARQUET_BASE_URL env var (e.g. a JFrog Generic Remote mirroring the bucket)
      2. https://anaconda-package-data.s3.amazonaws.com  (public S3 HTTPS)

    JFrog auth headers attach automatically via `make_request` when the
    resolved host matches an env-var-configured mirror; no per-resolver
    auth wiring is required.
    """
    if not _S3_MONTH_RE.match(month):
        raise ValueError(f"resolve_s3_parquet_urls: invalid month {month!r} (expected 'YYYY-MM')")
    year = month.split("-", 1)[0]
    bases: list[str | None] = [os.environ.get("S3_PARQUET_BASE_URL")]
    bases.append(_DEFAULT_S3_PARQUET_BASE)
    base_list = _dedup_strip(bases)
    return [f"{b}/{_S3_PARQUET_PREFIX}/{year}/{month}.parquet" for b in base_list]


def _parse_s3_list_objects_v2(xml_bytes: bytes) -> tuple[list[str] | None, str | None]:
    """Parse one ListObjectsV2 page.

    Returns `(months, next_token)`:
      - `(None, None)`     — malformed XML; caller should fall through to next base.
      - `([], None)`       — legitimate empty / end-of-listing for this base.
      - `([...], None)`    — single-page result.
      - `([...], "tok")`   — more pages available; resume with `continuation-token=tok`.
    """
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        _log(f"_http: S3 list-objects parse error ({exc})")
        return (None, None)
    months: set[str] = set()
    next_token: str | None = None
    is_truncated = False
    for elem in root.iter():
        tag = elem.tag.rsplit("}", 1)[-1]
        if tag == "Key" and elem.text:
            m = _S3_PARQUET_KEY_RE.match(elem.text.strip())
            if m:
                months.add(m.group(2))
        elif tag == "IsTruncated" and elem.text and elem.text.strip().lower() == "true":
            is_truncated = True
        elif tag == "NextContinuationToken" and elem.text:
            next_token = elem.text.strip()
    return (sorted(months), next_token if is_truncated else None)


def list_s3_parquet_months() -> list[str]:
    """List available `YYYY-MM` parquet months from the S3 bucket.

    Issues paginated ListObjectsV2 GETs against the first base in
    `resolve_s3_parquet_urls`'s priority chain. Follows `NextContinuationToken`
    until `IsTruncated=false`. Returns sorted unique months; raises
    `RuntimeError` if every base fails. An empty-but-parseable response is
    a legitimate `[]`, not a fallthrough trigger.
    """
    bases: list[str | None] = [os.environ.get("S3_PARQUET_BASE_URL")]
    bases.append(_DEFAULT_S3_PARQUET_BASE)
    base_list = _dedup_strip(bases)

    last_err: Exception | None = None
    for base in base_list:
        try:
            collected: set[str] = set()
            token: str | None = None
            for _page in range(50):  # hard cap: ~50k keys; bucket has ~110 today
                url = f"{base}/?list-type=2&prefix={_S3_PARQUET_PREFIX}/"
                if token:
                    url += f"&continuation-token={_url_quote(token, safe='')}"
                req = make_request(url)
                with open_url(req, timeout=30) as resp:
                    body = resp.read()
                page_months, next_token = _parse_s3_list_objects_v2(body)
                if page_months is None:
                    raise RuntimeError(f"malformed list-objects body from {base}")
                collected.update(page_months)
                if not next_token:
                    break
                token = next_token
            else:
                _log(f"_http: {base} listing exceeded 50-page cap; results may be incomplete")
            return sorted(collected)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            _log(f"_http: list-objects {base} → {exc}; trying next source")
            continue
    raise RuntimeError(
        f"All {len(base_list)} S3 list-objects source(s) failed; last error: {last_err}"
    )


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


# ── Resumable streaming downloads ──────────────────────────────────────────

def fetch_to_file_resumable(
    target: str | Path,
    urls: list[str] | str,
    *,
    chunk_size: int = 1024 * 1024,  # 1 MB
    timeout: int = 600,
    user_agent: str = "conda-forge-expert/1.0",
    extra_headers: dict[str, str] | None = None,
    max_retries: int = 3,
) -> Path:
    """Stream-download to a file with Range/resume + atomic rename.

    Writes to a `.part` sibling of `target`. If a `.part` already exists
    from a previous interrupted run, sets ``Range: bytes=<existing-size>-``
    so the server can resume from where we left off. On 206 Partial
    Content we append; on 200 OK (server ignored Range) we restart; on
    416 Range Not Satisfiable (our `.part` is already ≥ server size) we
    discard and restart from 0. On success: `os.replace(.part, target)`
    so consumers never see a half-written final file.

    Designed for large artifacts where re-downloading from byte 0 is
    expensive — primary case is `cve_manager.py` (4 GB OSV `all.zip`).
    For smaller artifacts that fit in RAM, `fetch_with_fallback` is
    simpler.

    Returns the final `target` Path on success. Raises `RuntimeError`
    if every URL in the chain is exhausted.
    """
    if isinstance(urls, str):
        urls = [urls]
    if not urls:
        raise ValueError("fetch_to_file_resumable requires at least one URL")

    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + ".part")

    last_err: Exception | None = None
    for url in urls:
        for attempt in range(max_retries):
            existing = part.stat().st_size if part.exists() else 0
            headers = dict(extra_headers or {})
            if existing > 0:
                headers["Range"] = f"bytes={existing}-"

            try:
                req = make_request(url, extra_headers=headers, user_agent=user_agent)
                with open_url(req, timeout=timeout) as resp:
                    # Python 3.10+ exposes .status on HTTPResponse; fall back
                    # to .getcode() for older runtimes.
                    status = getattr(resp, "status", None) or resp.getcode()
                    if existing > 0 and status == 200:
                        # Server ignored our Range header — restart from 0.
                        _log(f"_http: {url} returned 200 to Range request; restarting download")
                        part.unlink(missing_ok=True)
                        existing = 0
                        mode = "wb"
                    elif status == 206:
                        _log(f"_http: {url} resuming from byte {existing}")
                        mode = "ab"
                    elif status == 200:
                        mode = "wb"
                    else:
                        # 2xx but not 200/206 — treat as full body.
                        mode = "wb"
                        existing = 0

                    with open(part, mode) as f:
                        while True:
                            chunk = resp.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                        f.flush()
                        try:
                            os.fsync(f.fileno())
                        except OSError:
                            pass

                # Atomic finalize.
                os.replace(part, target)
                return target

            except urllib.error.HTTPError as e:
                last_err = e
                if e.code == 416:
                    # Range Not Satisfiable: our .part is ≥ server size.
                    # Most likely we already finished a previous run, or
                    # the part file is corrupt. Discard and retry from 0
                    # so the next attempt does a clean full download.
                    _log(f"_http: {url} returned 416; discarding stale .part and restarting")
                    part.unlink(missing_ok=True)
                    continue
                if 400 <= e.code < 500 and e.code not in (408, 429):
                    # Hard 4xx — no point retrying this URL, try the next.
                    _log(f"_http: {url} → HTTP {e.code}; moving to next source")
                    break
                _log(f"_http: {url} attempt {attempt + 1} → HTTP {e.code}; backing off")
                _time.sleep(2 ** attempt)
            except Exception as e:
                last_err = e
                _log(f"_http: {url} attempt {attempt + 1} → {e}; backing off")
                _time.sleep(2 ** attempt)

    raise RuntimeError(
        f"fetch_to_file_resumable: all {len(urls)} source(s) exhausted; last error: {last_err}"
    )


# ── Logging (stderr, non-intrusive) ─────────────────────────────────────────

def _log(msg: str) -> None:
    """Write a diagnostic message to stderr. Only emitted in verbose/debug mode."""
    if os.environ.get("CFE_DEBUG") or os.environ.get("CONDA_FORGE_EXPERT_DEBUG"):
        print(msg, file=sys.stderr)

