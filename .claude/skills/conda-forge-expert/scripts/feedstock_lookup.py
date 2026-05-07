#!/usr/bin/env python3
"""Look up an existing conda-forge/<pkg>-feedstock and return its parsed recipe.

Shared primitive used by v6.4 feedstock-aware generation:
  - 3a maintainer carry-over (recipe_generator post-processing)
  - 3b metadata carry-over (about-fields, license_file, etc.)
  - 3c issue review surface (separate tool, same lookup)

Caches GitHub API responses for 1 hour to avoid rate-limiting and to make
generation feel snappy when the agent looks up the same feedstock multiple
times in one session.

CLI:
    feedstock_lookup.py <pkg_name>           # JSON output
    feedstock_lookup.py --no-cache <pkg>     # bypass cache
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

# Local data directory (per CLAUDE.md three-tier layout)
_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "conda-forge-expert"
_CACHE_DIR = _DATA_DIR / "feedstock_cache"
_CACHE_TTL_SECONDS = 3600  # 1 hour

# Files we look for inside the feedstock's recipe/ directory, in priority order.
# recipe.yaml (v1) wins over meta.yaml (v0) when both are present (rare during
# active migration windows).
_RECIPE_CANDIDATES = ("recipe.yaml", "meta.yaml")


@dataclass
class FeedstockLookupResult:
    """Structured feedstock lookup result. JSON-serializable via asdict()."""

    pkg_name: str
    exists: bool
    feedstock_repo: Optional[str] = None  # "conda-forge/<pkg>-feedstock"
    format: Optional[str] = None  # "recipe.yaml" | "meta.yaml" | None
    recipe_path_in_repo: Optional[str] = None  # e.g. "recipe/recipe.yaml"
    raw_text: Optional[str] = None  # raw recipe contents
    parsed: Optional[dict] = None  # YAML-parsed dict (None if parse failed)
    cached: bool = False  # True if served from cache
    error: Optional[str] = None  # populated when lookup failed


def _cache_path(pkg_name: str) -> Path:
    safe = pkg_name.replace("/", "_").replace(" ", "_")
    return _CACHE_DIR / f"{safe}.json"


def _load_cache(pkg_name: str) -> Optional[dict]:
    cache = _cache_path(pkg_name)
    if not cache.exists():
        return None
    try:
        age = time.time() - cache.stat().st_mtime
        if age > _CACHE_TTL_SECONDS:
            return None
        return json.loads(cache.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _store_cache(pkg_name: str, data: dict) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(pkg_name).write_text(json.dumps(data, indent=2))
    except OSError:
        # Cache failures are non-fatal; the lookup result is still returned.
        pass


def _gh_api(path: str) -> Optional[dict]:
    """Call `gh api <path>` and return parsed JSON, or None on any error.

    Uses gh CLI rather than direct HTTP so it picks up the user's existing
    auth token. Network/auth failures return None — caller treats that as
    "feedstock not found" gracefully.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["gh", "api", path],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _decode_contents_response(api_json: dict) -> Optional[str]:
    """Decode the `content` field from a GitHub Contents API response."""
    import base64

    content = api_json.get("content")
    encoding = api_json.get("encoding")
    if not content or encoding != "base64":
        return None
    try:
        return base64.b64decode(content).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def _parse_yaml(text: str) -> Optional[dict]:
    """Parse YAML text; tolerate v0 meta.yaml's Jinja2 templating by stripping
    common patterns before parsing. Returns None on failure rather than raising
    so callers can degrade gracefully when the feedstock has unusual syntax.
    """
    try:
        from ruamel.yaml import YAML
    except ImportError:
        try:
            import yaml  # type: ignore[import-not-found]
            return yaml.safe_load(text)  # type: ignore[no-any-return]
        except (ImportError, Exception):
            return None

    # Strip Jinja2 directives that ruamel.yaml chokes on. v0 meta.yaml uses
    # `{% set name = "..." %}` and `{{ name|lower }}`; we replace the latter
    # with a bare token (no quotes) so multi-token YAML scalars like
    # `{{ PYTHON }} -m pip install` continue to parse as a plain string.
    # We only need structure, not rendered values.
    import re as _re

    cleaned = _re.sub(r"\{%[^%]*%\}", "", text)
    cleaned = _re.sub(r"\{\{[^}]*\}\}", "JINJA_PLACEHOLDER", cleaned)
    yaml = YAML(typ="safe")
    try:
        return yaml.load(cleaned)
    except Exception:
        return None


def feedstock_lookup(pkg_name: str, *, use_cache: bool = True) -> FeedstockLookupResult:
    """Look up `conda-forge/<pkg_name>-feedstock` and return parsed recipe data.

    Returns a FeedstockLookupResult with `exists=False` and `error=None` when
    the feedstock simply doesn't exist (the common case for new packages).
    Returns `error="..."` only for unexpected failures.
    """
    if not pkg_name or "/" in pkg_name:
        return FeedstockLookupResult(
            pkg_name=pkg_name, exists=False, error="invalid package name"
        )

    if use_cache:
        cached = _load_cache(pkg_name)
        if cached is not None:
            cached["cached"] = True
            return FeedstockLookupResult(**cached)

    feedstock_repo = f"conda-forge/{pkg_name}-feedstock"

    # Quick existence check first — avoids two failed contents calls if the
    # repo doesn't exist at all.
    repo_info = _gh_api(f"/repos/{feedstock_repo}")
    if repo_info is None or "name" not in repo_info:
        result = FeedstockLookupResult(pkg_name=pkg_name, exists=False)
        _store_cache(pkg_name, asdict(result))
        return result

    # Try recipe.yaml first, fall back to meta.yaml.
    for candidate in _RECIPE_CANDIDATES:
        path_in_repo = f"recipe/{candidate}"
        api_path = f"/repos/{feedstock_repo}/contents/{path_in_repo}"
        api_json = _gh_api(api_path)
        if api_json is None:
            continue
        text = _decode_contents_response(api_json)
        if text is None:
            continue

        result = FeedstockLookupResult(
            pkg_name=pkg_name,
            exists=True,
            feedstock_repo=feedstock_repo,
            format=candidate,
            recipe_path_in_repo=path_in_repo,
            raw_text=text,
            parsed=_parse_yaml(text),
        )
        _store_cache(pkg_name, asdict(result))
        return result

    # Repo exists but neither recipe file was findable — surface as error so
    # the caller knows something's off rather than silently returning exists=False.
    result = FeedstockLookupResult(
        pkg_name=pkg_name,
        exists=True,
        feedstock_repo=feedstock_repo,
        error=f"feedstock {feedstock_repo} exists but neither recipe/recipe.yaml nor recipe/meta.yaml was readable",
    )
    _store_cache(pkg_name, asdict(result))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "feedstock_lookup").split("\n")[0]
    )
    parser.add_argument("pkg_name", help="Package name (e.g. 'numpy')")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass the local cache and force a fresh GitHub API lookup",
    )
    parser.add_argument(
        "--no-raw",
        action="store_true",
        help="Omit raw_text from output (useful when piping to a parser that only needs `parsed`)",
    )
    args = parser.parse_args()

    result = feedstock_lookup(args.pkg_name, use_cache=not args.no_cache)
    out = asdict(result)
    if args.no_raw:
        out.pop("raw_text", None)
    print(json.dumps(out, indent=2))
    return 0 if result.error is None else 1


if __name__ == "__main__":
    sys.exit(main())
