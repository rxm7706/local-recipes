#!/usr/bin/env python3
"""
GitHub release version checker for conda-forge recipes.

Complements recipe_updater.py (which covers PyPI packages) by fetching the
latest release from a GitHub repository — useful for packages that are not on
PyPI or whose canonical source is GitHub rather than PyPI.

Queries the GitHub REST API:
  GET /repos/{owner}/{repo}/releases/latest
  GET /repos/{owner}/{repo}/tags            (fallback when no formal release)

Usage:
    python github_version_checker.py recipes/apple-fm-sdk
    python github_version_checker.py --repo apple/python-apple-fm-sdk
    python github_version_checker.py --json recipes/apple-fm-sdk
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    yaml = None  # type: ignore[assignment]
    YAML_AVAILABLE = False

# Enterprise HTTP helpers (truststore + .netrc auth)
sys.path.insert(0, str(Path(__file__).parent))
try:
    from _http import inject_ssl_truststore, make_request as _http_make_request  # type: ignore[import-not-found]
    inject_ssl_truststore()
    _HTTP_AVAILABLE = True
except ImportError:
    _HTTP_AVAILABLE = False

GITHUB_API = os.environ.get("GITHUB_API_BASE", "https://api.github.com")
REQUEST_TIMEOUT = 15  # seconds


# ── GitHub API helpers ────────────────────────────────────────────────────────

def _api_get(path: str) -> Any:
    """GET a GitHub API endpoint; returns parsed JSON."""
    url = f"{GITHUB_API}{path}"
    if _HTTP_AVAILABLE:
        req = _http_make_request(
            url,
            extra_headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
    else:
        # Fallback: env-var only token auth
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as exc:
        raise RuntimeError(f"GitHub API {exc.code}: {path}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc


def _strip_prefix(tag: str) -> str:
    """Strip leading 'v' or 'V' from version tags."""
    return tag.lstrip("vV")


def get_latest_github_release(owner: str, repo: str) -> dict[str, Any]:
    """
    Return the latest release version for a GitHub repo.

    Tries /releases/latest first; falls back to the most recent tag if the
    project doesn't use GitHub Releases.
    """
    try:
        data = _api_get(f"/repos/{owner}/{repo}/releases/latest")
        tag = data.get("tag_name", "")
        return {
            "source": "releases/latest",
            "tag": tag,
            "version": _strip_prefix(tag),
            "published_at": data.get("published_at"),
            "html_url": data.get("html_url"),
            "prerelease": data.get("prerelease", False),
        }
    except RuntimeError as exc:
        if "404" not in str(exc):
            raise
        # No formal releases — fall back to tags
        tags = _api_get(f"/repos/{owner}/{repo}/tags")
        if not tags:
            raise RuntimeError(f"No releases or tags found for {owner}/{repo}") from None
        tag = tags[0]["name"]
        return {
            "source": "tags",
            "tag": tag,
            "version": _strip_prefix(tag),
            "published_at": None,
            "html_url": f"https://github.com/{owner}/{repo}/releases/tag/{tag}",
            "prerelease": False,
        }


# ── Recipe parsing ────────────────────────────────────────────────────────────

_GITHUB_URL_RE = re.compile(
    r"github\.com[/:](?P<owner>[^/]+)/(?P<repo>[^/.\s#]+)", re.IGNORECASE
)


def _find_recipe(path: Path) -> Path:
    if path.is_file():
        return path
    for name in ("recipe.yaml", "meta.yaml"):
        candidate = path / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"No recipe.yaml or meta.yaml found in {path}")


def _parse_recipe(recipe_file: Path) -> dict[str, Any]:
    """Parse a recipe file; returns {} on any failure."""
    if not YAML_AVAILABLE:
        return {}
    assert yaml is not None
    raw = recipe_file.read_text(encoding="utf-8")
    raw = re.sub(r"\$\{\{[^}]*\}\}", "TEMPLATE", raw)
    raw = re.sub(r"\{\{[^}]*\}\}", "TEMPLATE", raw)
    try:
        data = yaml.safe_load(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def extract_github_repo(recipe_file: Path) -> tuple[str, str] | None:
    """
    Scan a recipe for a GitHub URL and return (owner, repo), or None.

    Checks (in order): context.*, source.url, about.home.
    """
    data = _parse_recipe(recipe_file)

    # Collect candidate URLs
    candidates: list[str] = []
    for v in (data.get("context") or {}).values():
        candidates.append(str(v))
    for src in ([data.get("source")] if isinstance(data.get("source"), dict) else data.get("source", [])):
        if isinstance(src, dict):
            candidates.append(str(src.get("url", "")))
    candidates.append(str((data.get("about") or {}).get("home", "")))

    for text in candidates:
        m = _GITHUB_URL_RE.search(text)
        if m:
            repo = m.group("repo")
            # Strip .git suffix if present
            repo = repo.removesuffix(".git")
            return m.group("owner"), repo
    return None


def get_current_version(recipe_file: Path) -> str | None:
    """Return the version declared in a recipe's context or package section."""
    data = _parse_recipe(recipe_file)
    ctx = data.get("context") or {}
    v = ctx.get("version") or (data.get("package") or {}).get("version")
    if v and v != "TEMPLATE":
        return str(v)
    return None


# ── Main logic ────────────────────────────────────────────────────────────────

def check_version(
    recipe_path: Path | None = None,
    github_repo: str | None = None,
) -> dict[str, Any]:
    """
    Check latest GitHub release vs. the version in a recipe.

    Provide either recipe_path (auto-detects GitHub repo from the recipe) or
    github_repo in 'owner/repo' format (or a full GitHub URL).
    """
    owner: str
    repo: str
    recipe_file: Path | None = None
    current_version: str | None = None

    if recipe_path is not None:
        recipe_file = _find_recipe(recipe_path)
        current_version = get_current_version(recipe_file)
        found = extract_github_repo(recipe_file)
        if found is None:
            return {
                "success": False,
                "error": "No GitHub URL found in recipe. Use --repo owner/repo to specify manually.",
                "recipe": str(recipe_file),
            }
        owner, repo = found
    elif github_repo is not None:
        # Accept 'owner/repo' or full github.com URL
        m = _GITHUB_URL_RE.search(github_repo) or re.match(r"^([^/]+)/([^/]+)$", github_repo)
        if not m:
            return {"success": False, "error": f"Cannot parse GitHub repo from: {github_repo!r}"}
        owner = m.group(1) if hasattr(m, "group") else m.group("owner")
        repo = m.group(2) if hasattr(m, "group") else m.group("repo")
        repo = repo.removesuffix(".git")
    else:
        return {"success": False, "error": "Provide either recipe_path or github_repo."}

    try:
        latest = get_latest_github_release(owner, repo)
    except RuntimeError as exc:
        return {"success": False, "error": str(exc), "owner": owner, "repo": repo}

    result: dict[str, Any] = {
        "success": True,
        "owner": owner,
        "repo": repo,
        "latest_version": latest["version"],
        "latest_tag": latest["tag"],
        "source": latest["source"],
        "published_at": latest["published_at"],
        "html_url": latest["html_url"],
        "prerelease": latest["prerelease"],
    }

    if recipe_file is not None:
        result["recipe"] = str(recipe_file)
        result["current_version"] = current_version
        if current_version and latest["version"]:
            result["update_available"] = latest["version"] != current_version
        else:
            result["update_available"] = None

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check the latest GitHub release for a conda recipe.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Set GITHUB_TOKEN or GH_TOKEN env var to avoid rate limiting.\n"
            "Exit: 0 = current or no update, 2 = update available, 1 = error."
        ),
    )
    parser.add_argument("recipe_path", type=Path, nargs="?",
                        help="Recipe file or directory (auto-detects GitHub URL).")
    parser.add_argument("--repo", default=None,
                        help="GitHub repo in 'owner/repo' format (overrides auto-detect).")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="Output JSON (used by MCP server).")
    args = parser.parse_args()

    if args.recipe_path is None and args.repo is None:
        parser.error("Provide a recipe_path or --repo owner/repo.")

    result = check_version(
        recipe_path=args.recipe_path,
        github_repo=args.repo,
    )

    if args.as_json:
        print(json.dumps(result, indent=2))
    else:
        if not result["success"]:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)
        owner, repo = result["owner"], result["repo"]
        latest = result["latest_version"]
        current = result.get("current_version")
        update = result.get("update_available")
        print(f"\nGitHub Version Check — {owner}/{repo}")
        print("=" * 50)
        if current:
            print(f"  Recipe version : {current}")
        print(f"  Latest release : {latest}  [{result['source']}]")
        if result.get("published_at"):
            print(f"  Published      : {result['published_at'][:10]}")
        if result.get("prerelease"):
            print(f"  ⚠  Pre-release")
        if update is True:
            print(f"\n  → Update available: {current} → {latest}")
            print(f"    {result['html_url']}")
        elif update is False:
            print(f"\n  ✓ Up to date.")
        print("=" * 50)

    if not result["success"]:
        sys.exit(1)
    sys.exit(2 if result.get("update_available") else 0)


if __name__ == "__main__":
    main()
