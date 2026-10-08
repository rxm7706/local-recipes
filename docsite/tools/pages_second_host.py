"""Resolve GitHub Pages host inputs for Story 31.1 (CAP-56).

The flag is read only through ``pyforge.herald.pages_host`` (which calls
``pyforge.core.flags.read_boolean``, steward 75.1). Callers in the ``site`` pixi env
invoke :func:`export_host_env_for_ci` from the Guild env; unit tests import this
module from ``pyforge-herald`` tests directly.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

ENV_APPLY_HOST = "PYFORGE_PAGES_APPLY_HOST"
ENV_CONFIGURED_BASE_URL = "PAGES_HOST_BASE_URL"
ENV_CONFIGURED_BASE_PATH = "PAGES_HOST_BASE_PATH"
ENV_SITE_URL = "SITE_URL"

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


def second_host_enabled() -> bool:
    from pyforge.herald.pages_host import pages_second_host_enabled

    return pages_second_host_enabled()


def resolve_build_site_url(
    *,
    configured_base_url: str | None,
    configured_base_path: str | None,
    apply_second_host: bool,
) -> str:
    """Return the ``SITE_URL`` Astro and ``pages-check`` should use for this build."""
    if apply_second_host and configured_base_url:
        base_path = configured_base_path or "/"
        return combine_pages_host(configured_base_url, base_path)
    return public_site_url()


def resolve_from_process_environment() -> str:
    """Resolve the site URL from env set by :func:`export_host_env_for_ci` or public defaults."""
    if os.environ.get(ENV_APPLY_HOST, "").lower() in ("1", "true", "yes"):
        explicit = os.environ.get(ENV_SITE_URL, "").strip()
        if explicit:
            return explicit.rstrip("/")
        base_url = os.environ.get(ENV_CONFIGURED_BASE_URL, "").strip()
        base_path = os.environ.get(ENV_CONFIGURED_BASE_PATH, "/").strip() or "/"
        if base_url:
            return combine_pages_host(base_url, base_path)
    return public_site_url()


def export_host_env_for_ci() -> dict[str, str]:
    """Compute env vars for ``dashboard.yml`` (Guild env only — reads the flag tree)."""
    configured_base_url = os.environ.get(ENV_CONFIGURED_BASE_URL, "").strip() or None
    configured_base_path = os.environ.get(ENV_CONFIGURED_BASE_PATH, "").strip() or None
    apply = second_host_enabled()
    site_url = resolve_build_site_url(
        configured_base_url=configured_base_url,
        configured_base_path=configured_base_path,
        apply_second_host=apply,
    )
    out: dict[str, str] = {ENV_APPLY_HOST: "1" if apply else "0", ENV_SITE_URL: site_url}
    if configured_base_url:
        out[ENV_CONFIGURED_BASE_URL] = configured_base_url
    if configured_base_path:
        out[ENV_CONFIGURED_BASE_PATH] = configured_base_path
    return out


def site_origin(site_url: str) -> str:
    """Normalized origin (scheme + host + port) for cross-origin checks."""
    parsed = urlparse(site_url.rstrip("/") + "/")
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{parsed.hostname}{port}".lower()


def is_navigation_link(href: str) -> bool:
    """Plain off-site navigation (allowed by CAP-56)."""
    return href.startswith(("https://github.com/", "http://github.com/"))
