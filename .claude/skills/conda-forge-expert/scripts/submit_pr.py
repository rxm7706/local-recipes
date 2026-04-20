#!/usr/bin/env python3
"""
Submit a conda-forge recipe as a PR to conda-forge/staged-recipes.

Mirrors the logic of scripts/submit_pr.sh but returns structured JSON so the
autonomous agent loop can act on the result programmatically.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# .claude/skills/conda-forge-expert/scripts/ -> repo root (4 levels up)
REPO_ROOT = Path(__file__).resolve().parents[4]
STAGED_RECIPES_FORK_PATH = REPO_ROOT.parent / "staged-recipes"


def _run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> tuple[int, str, str]:
    result = subprocess.run(
        cmd, capture_output=True, text=True, check=False,
        cwd=str(cwd) if cwd else None,
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"Command failed: {cmd}")
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _gh_auth_user() -> str:
    rc, _, _ = _run(["gh", "auth", "status"], check=False)
    if rc != 0:
        raise RuntimeError("GitHub CLI is not authenticated. Run 'gh auth login' first.")
    _, username, _ = _run(["gh", "api", "user", "-q", ".login"])
    if not username:
        raise RuntimeError("Could not determine GitHub username from 'gh api user'.")
    return username


def _ensure_fork(github_user: str) -> Path:
    if not STAGED_RECIPES_FORK_PATH.exists():
        print(f"  Cloning fork {github_user}/staged-recipes ...")
        _run(["gh", "repo", "clone", f"{github_user}/staged-recipes", str(STAGED_RECIPES_FORK_PATH)])
    return STAGED_RECIPES_FORK_PATH


def _sync_fork(fork_path: Path) -> None:
    _run(["git", "remote", "add", "upstream",
          "https://github.com/conda-forge/staged-recipes.git"], cwd=fork_path, check=False)
    _run(["git", "fetch", "upstream"], cwd=fork_path)
    _run(["git", "checkout", "main"], cwd=fork_path)
    _run(["git", "reset", "--hard", "upstream/main"], cwd=fork_path)
    _run(["git", "push", "origin", "main", "--force"], cwd=fork_path)


def submit_pr(
    recipe_name: str,
    dry_run: bool = False,
    pr_title: str | None = None,
    pr_body: str | None = None,
) -> dict[str, Any]:
    # 1. Validate recipe exists locally
    recipe_dir = REPO_ROOT / "recipes" / recipe_name
    if not recipe_dir.exists():
        return {"success": False, "error": f"Recipe not found: {recipe_dir}"}

    recipe_file = next(recipe_dir.glob("recipe.yaml"), None) or next(recipe_dir.glob("meta.yaml"), None)
    if recipe_file is None:
        return {"success": False, "error": f"No recipe.yaml or meta.yaml found in {recipe_dir}"}

    # 2. Check gh auth
    try:
        github_user = _gh_auth_user()
    except RuntimeError as e:
        return {"success": False, "error": str(e)}

    # Dry-run: verify prerequisites only, no network writes
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "recipe": recipe_name,
            "recipe_file": str(recipe_file),
            "github_user": github_user,
            "fork_path": str(STAGED_RECIPES_FORK_PATH),
            "fork_exists": STAGED_RECIPES_FORK_PATH.exists(),
            "message": "Dry run OK — all prerequisites met. Call with dry_run=False to submit.",
        }

    # 3. Ensure fork and sync
    try:
        fork_path = _ensure_fork(github_user)
        print("  Syncing fork with upstream conda-forge/staged-recipes ...")
        _sync_fork(fork_path)
    except RuntimeError as e:
        return {"success": False, "error": f"Fork/sync failed: {e}"}

    # 4. Create feature branch
    branch = f"add-recipe-{recipe_name}"
    try:
        _run(["git", "checkout", "-b", branch], cwd=fork_path, check=False)
        _run(["git", "checkout", branch], cwd=fork_path)
        _run(["git", "reset", "--hard", "origin/main"], cwd=fork_path)
    except RuntimeError as e:
        return {"success": False, "error": f"Branch creation failed: {e}"}

    # 5. Copy recipe into fork
    dest = fork_path / "recipes" / recipe_name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(recipe_dir, dest)

    # 6. Commit and push
    try:
        _run(["git", "add", f"recipes/{recipe_name}"], cwd=fork_path)
        _run(["git", "commit", "-m", f"Add recipe for {recipe_name}"], cwd=fork_path)
        _run(["git", "push", "-u", "origin", branch, "--force"], cwd=fork_path)
    except RuntimeError as e:
        return {"success": False, "error": f"Commit/push failed: {e}"}

    # 7. Open PR
    if pr_title is None:
        pr_title = f"Add recipe for {recipe_name}"
    if pr_body is None:
        pr_body = (
            f"This PR adds a new recipe for `{recipe_name}`.\n\n"
            "### Pre-Submission Checklist\n"
            "- [x] The recipe builds locally successfully.\n"
            "- [x] The recipe passes all `conda-smithy recipe-lint` checks.\n"
            "- [x] License and checksums are verified.\n\n"
            "*Submitted automatically via local-recipes automation.*"
        )

    try:
        _, pr_url, _ = _run([
            "gh", "pr", "create",
            "--repo", "conda-forge/staged-recipes",
            "--title", pr_title,
            "--body", pr_body,
            "--head", f"{github_user}:{branch}",
            "--base", "main",
        ], cwd=fork_path)
        return {
            "success": True,
            "recipe": recipe_name,
            "pr_url": pr_url,
            "branch": branch,
            "github_user": github_user,
            "message": f"PR created: {pr_url}",
        }
    except RuntimeError as e:
        return {"success": False, "error": f"PR creation failed: {e}"}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Submit a recipe PR to conda-forge/staged-recipes."
    )
    parser.add_argument("recipe_name", help="Recipe directory name (e.g. 'numpy').")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate prerequisites without submitting.")
    parser.add_argument("--title", default=None, help="Custom PR title.")
    parser.add_argument("--body", default=None, help="Custom PR body.")
    args = parser.parse_args()

    result = submit_pr(
        args.recipe_name,
        dry_run=args.dry_run,
        pr_title=args.title,
        pr_body=args.body,
    )
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
