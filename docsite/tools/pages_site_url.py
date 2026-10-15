"""The Pages build's site URL: the deploying host's, from ``actions/configure-pages``.

Story 31.1 (CAP-56) made the build take the deploying host's site URL and base path; Story 42.3
(CAP-60) makes ``configure-pages`` authoritative on every host. When both ``PAGES_HOST_BASE_URL`` and
``PAGES_HOST_BASE_PATH`` reach the build (``pages.yml`` sets them from the ``configure-pages`` step's
outputs) they are the site URL; otherwise the build uses the public github.io URL (Story 27.2). No
flag decides it, and nothing here reads one. ``site_origin`` is the input of ``pages-check``'s
cross-origin check.
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
    """The ``SITE_URL`` Astro and ``pages-check`` use: the host's when both values are given, else public."""
    base_url = (configured_base_url or "").strip()
    base_path = (configured_base_path or "").strip()
    if base_url and base_path:
        return combine_pages_host(base_url, base_path)
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
