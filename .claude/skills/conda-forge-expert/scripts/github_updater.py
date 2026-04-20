#!/usr/bin/env python3
"""
GitHub Release Autotick Bot.

Mirrors recipe_updater.py but fetches the latest version from GitHub Releases
instead of PyPI. Intended for packages whose canonical release channel is
GitHub (e.g. apple-fm-sdk, which tags on GitHub before or instead of PyPI).

Workflow:
  1. Parse the recipe's context for current name/version.
  2. Auto-detect the GitHub repo from the recipe's source URL, context vars,
     or about.home — or accept --repo owner/repo to override.
  3. Fetch the latest release (or tag fallback) from the GitHub REST API.
  4. Compare using PEP 440 semantics; fall back to string equality.
  5. If newer: call recipe_editor.py to update context.version, reset
     build.number to 0, and recalculate the source SHA256.

Pre-releases are skipped by default (pass --pre to include them).

Usage:
    python github_updater.py recipes/apple-fm-sdk/recipe.yaml
    python github_updater.py --repo apple/python-apple-fm-sdk recipes/apple-fm-sdk/recipe.yaml
    python github_updater.py --dry-run recipes/apple-fm-sdk/recipe.yaml
    python github_updater.py --pre  recipes/apple-fm-sdk/recipe.yaml
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# ── Optional deps ─────────────────────────────────────────────────────────────

try:
    from ruamel.yaml import YAML
    RUAMEL_AVAILABLE = True
except ImportError:
    YAML = None  # type: ignore[assignment,misc]
    RUAMEL_AVAILABLE = False

try:
    from packaging.version import Version as PkgVersion
    PACKAGING_AVAILABLE = True
except ImportError:
    PkgVersion = None  # type: ignore[assignment,misc]
    PACKAGING_AVAILABLE = False

# ── Sibling imports ───────────────────────────────────────────────────────────
# Import the two helpers from github_version_checker.py without subprocess
# overhead. Both scripts live in the same directory.

_SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPTS_DIR))

try:
    from github_version_checker import (  # type: ignore[import]
        extract_github_repo,
        get_latest_github_release,
    )
    _CHECKER_AVAILABLE = True
except ImportError as _e:
    extract_github_repo = None  # type: ignore[assignment]
    get_latest_github_release = None  # type: ignore[assignment]
    _CHECKER_AVAILABLE = False
    _CHECKER_IMPORT_ERROR = str(_e)

RECIPE_EDITOR_SCRIPT = _SCRIPTS_DIR / "recipe_editor.py"

_GITHUB_RE = re.compile(
    r"github\.com[/:](?P<owner>[^/]+)/(?P<repo>[^/.\s#]+)", re.IGNORECASE
)


# ── Recipe helpers ────────────────────────────────────────────────────────────

def _get_recipe_context(recipe_path: Path) -> dict[str, Any]:
    """Return the recipe's context section, or {} on failure."""
    if not RUAMEL_AVAILABLE:
        raise ImportError("ruamel.yaml is required to parse the recipe.")
    assert YAML is not None
    yaml_parser = YAML()
    with open(recipe_path) as f:
        data = yaml_parser.load(f)
    return {"context": data.get("context") or {}, "source": data.get("source")}


def _detect_source_path(recipe_path: Path) -> str:
    """Return 'source' (dict) or 'source.0' (list) based on the recipe's source type."""
    if not RUAMEL_AVAILABLE:
        return "source.0"
    assert YAML is not None
    yaml_parser = YAML()
    try:
        with open(recipe_path) as f:
            data = yaml_parser.load(f)
        return "source" if isinstance(data.get("source"), dict) else "source.0"
    except Exception:
        return "source.0"


def _parse_github_repo(spec: str) -> tuple[str, str] | None:
    """Parse 'owner/repo' or a full github.com URL into (owner, repo)."""
    m = _GITHUB_RE.search(spec)
    if m:
        return m.group("owner"), m.group("repo").removesuffix(".git")
    m2 = re.match(r"^([^/\s]+)/([^/\s]+)$", spec)
    if m2:
        return m2.group(1), m2.group(2).removesuffix(".git")
    return None


# ── Version helpers ───────────────────────────────────────────────────────────

def _is_newer(latest: str, current: str) -> bool:
    if PACKAGING_AVAILABLE:
        assert PkgVersion is not None
        try:
            return PkgVersion(latest) > PkgVersion(current)
        except Exception:
            pass
    return latest != current


# ── Core update logic ─────────────────────────────────────────────────────────

def update_recipe(
    recipe_path: Path,
    github_repo: str | None = None,
    dry_run: bool = False,
    allow_prerelease: bool = False,
) -> dict[str, Any]:
    if not _CHECKER_AVAILABLE:
        return {
            "success": False,
            "error": f"github_version_checker.py could not be imported: {_CHECKER_IMPORT_ERROR}",
        }
    assert extract_github_repo is not None
    assert get_latest_github_release is not None

    # 1. Parse recipe
    try:
        recipe_data = _get_recipe_context(recipe_path)
    except (ImportError, FileNotFoundError, Exception) as exc:
        return {"success": False, "error": str(exc)}

    ctx = recipe_data["context"]
    current_version = str(ctx.get("version", "")) if ctx.get("version") else None
    package_name = str(ctx.get("name", recipe_path.parent.name))

    if not current_version:
        return {"success": False, "error": "Cannot read context.version from recipe."}

    # 2. Resolve GitHub owner/repo
    owner: str
    repo: str
    if github_repo:
        parsed = _parse_github_repo(github_repo)
        if parsed is None:
            return {"success": False, "error": f"Cannot parse GitHub repo: {github_repo!r}"}
        owner, repo = parsed
    else:
        found = extract_github_repo(recipe_path)
        if found is None:
            return {
                "success": False,
                "error": (
                    "No GitHub URL detected in this recipe. "
                    "Pass --repo owner/repo to specify it manually, "
                    "or use update_recipe (PyPI autotick) instead."
                ),
                "recipe": str(recipe_path),
            }
        owner, repo = found

    print(f"Checking GitHub releases for {owner}/{repo} "
          f"(current: {package_name} {current_version})…")

    # 3. Fetch latest release
    try:
        latest_info = get_latest_github_release(owner, repo)
    except RuntimeError as exc:
        return {"success": False, "error": str(exc), "owner": owner, "repo": repo}

    latest_version = latest_info.get("version", "")
    if not latest_version:
        return {
            "success": False,
            "error": f"Could not parse a version from tag '{latest_info.get('tag')}'.",
        }

    if latest_info.get("prerelease") and not allow_prerelease:
        return {
            "success": True,
            "updated": False,
            "current_version": current_version,
            "latest_version": latest_version,
            "latest_tag": latest_info["tag"],
            "message": (
                f"Latest release {latest_version} is a pre-release — skipping. "
                "Pass --pre to include pre-releases."
            ),
        }

    # 4. Compare versions
    if not _is_newer(latest_version, current_version):
        return {
            "success": True,
            "updated": False,
            "current_version": current_version,
            "latest_version": latest_version,
            "message": f"Already up-to-date ({current_version}).",
        }

    print(f"New version found: {current_version} → {latest_version}")

    # 5. Build actions — identical contract to recipe_updater.py
    source_path = _detect_source_path(recipe_path)
    actions: list[dict[str, Any]] = [
        {"action": "update", "path": "context.version", "value": latest_version},
        {"action": "update", "path": "build.number", "value": 0},
        {"action": "calculate_hash", "path": source_path},
    ]

    if dry_run:
        return {
            "success": True,
            "updated": True,
            "dry_run": True,
            "current_version": current_version,
            "latest_version": latest_version,
            "latest_tag": latest_info["tag"],
            "source": latest_info["source"],
            "github_url": latest_info.get("html_url"),
            "actions": actions,
            "message": f"Dry run: would update {package_name} {current_version} → {latest_version}.",
        }

    # 6. Apply via recipe_editor.py
    python = os.environ.get("CONDA_PYTHON_EXE") or sys.executable
    cmd = [python, str(RECIPE_EDITOR_SCRIPT), str(recipe_path), json.dumps(actions)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if proc.returncode != 0:
        raw = proc.stderr or proc.stdout
        try:
            detail = json.loads(proc.stdout).get("error", raw)
        except Exception:
            detail = raw
        return {"success": False, "error": f"recipe_editor failed: {detail}"}

    return {
        "success": True,
        "updated": True,
        "current_version": current_version,
        "new_version": latest_version,
        "latest_tag": latest_info["tag"],
        "github_url": latest_info.get("html_url"),
        "message": f"Updated {package_name} {current_version} → {latest_version}.",
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Autotick bot: update a conda recipe to the latest GitHub release.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Auto-detects the GitHub repo from the recipe's source URL or about.home.\n"
            "Set GITHUB_TOKEN or GH_TOKEN to avoid API rate limits (60 req/h unauthenticated).\n\n"
            "Exit: 0 = success (updated or already current), 1 = error."
        ),
    )
    parser.add_argument("recipe_path", type=Path, help="Recipe file or directory.")
    parser.add_argument("--repo", default=None,
                        help="GitHub 'owner/repo' or full URL (overrides auto-detect).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Check for updates but do not write the file.")
    parser.add_argument("--pre", action="store_true",
                        help="Include pre-release versions.")
    args = parser.parse_args()

    recipe_path = args.recipe_path
    if recipe_path.is_dir():
        for name in ("recipe.yaml", "meta.yaml"):
            candidate = recipe_path / name
            if candidate.exists():
                recipe_path = candidate
                break
        else:
            print(json.dumps({"success": False,
                               "error": f"No recipe.yaml or meta.yaml in {args.recipe_path}"}))
            sys.exit(1)

    result = update_recipe(
        recipe_path,
        github_repo=args.repo,
        dry_run=args.dry_run,
        allow_prerelease=args.pre,
    )
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
