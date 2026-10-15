"""The Pages build's site URL: the deploying host's, from ``actions/configure-pages``.

Story 31.1 (CAP-56) made the build take the deploying host's site URL and base path; Story 42.3
(CAP-60) makes ``configure-pages`` authoritative on every host. ``pages.yml`` hands the build the
``configure-pages`` step's outputs as ``PAGES_HOST_BASE_URL`` and ``PAGES_HOST_BASE_PATH``. A base URL
decides it: with one, the site URL is that URL joined with the base path, and an empty or ``/`` base
path is a host served at its root (``configure-pages`` emits ``""`` for a custom domain or a
root-hosted Pages site), so the site URL is the origin alone. With no base URL the build uses the
public github.io URL (Story 27.2), whatever the base path says. No flag decides it, and nothing here
reads one. ``site_origin`` is the input of ``pages-check``'s cross-origin check.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

ENV_CONFIGURED_BASE_URL = "PAGES_HOST_BASE_URL"
ENV_CONFIGURED_BASE_PATH = "PAGES_HOST_BASE_PATH"

SITE_URL_MARKER = ".pages-build-site-url"


def public_site_url(*, github_repository: str | None = None) -> str:
    """Default public github.io site URL (Story 27.2 behaviour)."""
    repo = github_repository or os.environ.get("GITHUB_REPOSITORY", "rxm7706/local-recipes")
    parts = repo.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"invalid GITHUB_REPOSITORY: {repo!r}")
    owner, name = parts
    return f"https://{owner}.github.io/{name}"


def combine_pages_host(base_url: str, base_path: str) -> str:
    """Merge ``configure-pages`` ``base_url`` and ``base_path`` into one site URL."""
    origin = base_url.rstrip("/")
    path = base_path.strip()
    if not path or path == "/":
        return origin
    if not path.startswith("/"):
        path = f"/{path}"
    path = path.rstrip("/")
    parsed = urlparse(origin)
    if parsed.path.rstrip("/") == path:
        return origin
    return f"{origin}{path}"


def resolve_build_site_url(*, configured_base_url: str | None, configured_base_path: str | None) -> str:
    """The ``SITE_URL`` Astro and ``pages-check`` use: the host's whenever a base URL is given (an empty
    base path is a root-hosted site, so the origin alone; 42.3's review), else the public URL."""
    base_url = (configured_base_url or "").strip()
    if base_url:
        return combine_pages_host(base_url, (configured_base_path or "").strip())
    return public_site_url()


def resolve_from_process_environment() -> str:
    """:func:`resolve_build_site_url` over ``PAGES_HOST_BASE_URL`` and ``PAGES_HOST_BASE_PATH``."""
    return resolve_build_site_url(
        configured_base_url=os.environ.get(ENV_CONFIGURED_BASE_URL),
        configured_base_path=os.environ.get(ENV_CONFIGURED_BASE_PATH),
    )


def site_origin(site_url: str) -> str:
    """Normalized origin (scheme + host + port) for cross-origin checks."""
    parsed = urlparse(site_url.rstrip("/") + "/")
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{parsed.hostname}{port}".lower()
