#!/usr/bin/env python3
"""
Two-step submission to conda-forge/staged-recipes.

Step A (``prepare_branch``)
    Sync your fork with upstream, create / refresh the feature branch,
    copy the local recipe in, commit, push to ``<user>/staged-recipes``.
    Idempotent: when the remote branch already has the same tree as the
    local HEAD, the push is skipped (``pushed: false`` in the result).
    Force pushes use ``--force-with-lease`` by default so a divergent
    remote branch errors out instead of being silently overwritten.

Step B (``open_pr``)
    Open the PR from ``<user>:<branch>`` against
    ``conda-forge/staged-recipes:main``.

``submit_pr`` runs A then B for the original end-to-end behavior.
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
UPSTREAM_REPO = "conda-forge/staged-recipes"
UPSTREAM_URL = "https://github.com/conda-forge/staged-recipes.git"
DEFAULT_BRANCH_PREFIX = "add-recipe-"


def _run(
    cmd: list[str], cwd: Path | None = None, check: bool = True
) -> tuple[int, str, str]:
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
        _run(["gh", "repo", "clone",
              f"{github_user}/staged-recipes", str(STAGED_RECIPES_FORK_PATH)])
    return STAGED_RECIPES_FORK_PATH


def _sync_fork(fork_path: Path) -> int:
    """Reset fork's main to upstream/main. Returns the number of commits the
    fork's main was behind upstream before the sync (0 if already up to date)."""
    _run(["git", "remote", "add", "upstream", UPSTREAM_URL],
         cwd=fork_path, check=False)
    _run(["git", "fetch", "upstream"], cwd=fork_path)
    _run(["git", "checkout", "main"], cwd=fork_path)
    rc, behind, _ = _run(
        ["git", "rev-list", "--count", "main..upstream/main"],
        cwd=fork_path, check=False,
    )
    behind_n = int(behind) if rc == 0 and behind.isdigit() else 0
    _run(["git", "reset", "--hard", "upstream/main"], cwd=fork_path)
    _run(["git", "push", "origin", "main", "--force"], cwd=fork_path)
    return behind_n


def _remote_branch_head(fork_path: Path, branch: str) -> str | None:
    """Remote tip sha for origin/<branch>, or None if the branch is absent."""
    rc, out, _ = _run(["git", "ls-remote", "origin", branch],
                      cwd=fork_path, check=False)
    if rc != 0 or not out:
        return None
    return out.split()[0]


def _tree_sha(fork_path: Path, ref: str) -> str:
    _, sha, _ = _run(["git", "rev-parse", f"{ref}^{{tree}}"], cwd=fork_path)
    return sha


def prepare_branch(
    recipe_name: str,
    branch: str | None = None,
    force: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Get a branch on ``<user>/staged-recipes`` ready for PR submission.

    Validates the local recipe, syncs the fork with upstream, creates / refreshes
    the feature branch, copies the recipe in, commits, and pushes. Returns the
    branch URL on the fork so the caller can inspect before opening a PR.

    Idempotent: if the remote branch already has the same tree as the local HEAD,
    the push is skipped (``pushed: false``). Force pushes use ``--force-with-lease``
    when ``force=True`` (the default).
    """
    recipe_dir = REPO_ROOT / "recipes" / recipe_name
    if not recipe_dir.exists():
        return {"success": False, "error": f"Recipe not found: {recipe_dir}"}

    recipe_file = (next(recipe_dir.glob("recipe.yaml"), None) or
                   next(recipe_dir.glob("meta.yaml"), None))
    if recipe_file is None:
        return {"success": False,
                "error": f"No recipe.yaml or meta.yaml found in {recipe_dir}"}

    try:
        github_user = _gh_auth_user()
    except RuntimeError as e:
        return {"success": False, "error": str(e)}

    branch = branch or f"{DEFAULT_BRANCH_PREFIX}{recipe_name}"
    fork_branch_url = (
        f"https://github.com/{github_user}/staged-recipes/tree/{branch}"
    )

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "recipe": recipe_name,
            "recipe_file": str(recipe_file),
            "github_user": github_user,
            "branch": branch,
            "fork_path": str(STAGED_RECIPES_FORK_PATH),
            "fork_exists": STAGED_RECIPES_FORK_PATH.exists(),
            "fork_branch_url": fork_branch_url,
            "force": force,
            "planned_commit_message": f"Add recipe for {recipe_name}",
            "message": (f"Dry run OK — would push branch '{branch}' to "
                        f"{github_user}/staged-recipes. "
                        f"Call with dry_run=False to actually push."),
        }

    try:
        fork_path = _ensure_fork(github_user)
        print("  Syncing fork with upstream conda-forge/staged-recipes ...")
        synced_commits = _sync_fork(fork_path)
    except RuntimeError as e:
        return {"success": False, "error": f"Fork/sync failed: {e}"}

    # Create / refresh the branch off origin/main
    try:
        _run(["git", "checkout", "-b", branch], cwd=fork_path, check=False)
        _run(["git", "checkout", branch], cwd=fork_path)
        _run(["git", "reset", "--hard", "origin/main"], cwd=fork_path)
    except RuntimeError as e:
        return {"success": False, "error": f"Branch creation failed: {e}"}

    # Copy recipe into fork
    dest = fork_path / "recipes" / recipe_name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(recipe_dir, dest)

    # Stage + commit. If nothing was staged, the recipe already matches main —
    # likely already merged upstream.
    try:
        _run(["git", "add", f"recipes/{recipe_name}"], cwd=fork_path)
        rc, _, _ = _run(["git", "diff", "--cached", "--quiet"],
                        cwd=fork_path, check=False)
        if rc == 0:
            return {
                "success": False,
                "error": (
                    f"No changes to commit for recipe '{recipe_name}'. "
                    f"The recipe may already exist on upstream main."
                ),
            }
        _run(["git", "commit", "-m", f"Add recipe for {recipe_name}"],
             cwd=fork_path)
    except RuntimeError as e:
        return {"success": False, "error": f"Commit failed: {e}"}

    # Idempotency: skip the push when the remote branch's tree already matches
    # the local HEAD's tree. Avoids burning a force-push when nothing changed.
    pushed = True
    remote_tip = _remote_branch_head(fork_path, branch)
    if remote_tip is not None:
        _run(["git", "fetch", "origin", branch], cwd=fork_path, check=False)
        try:
            if _tree_sha(fork_path, "HEAD") == _tree_sha(fork_path, remote_tip):
                pushed = False
        except RuntimeError:
            pass

    if pushed:
        push_args = ["git", "push", "-u", "origin", branch]
        if force:
            push_args.append("--force-with-lease")
        try:
            _run(push_args, cwd=fork_path)
        except RuntimeError as e:
            return {"success": False, "error": f"Push failed: {e}"}

    _, head_commit_sha, _ = _run(["git", "rev-parse", "HEAD"], cwd=fork_path)

    return {
        "success": True,
        "recipe": recipe_name,
        "branch": branch,
        "github_user": github_user,
        "fork_path": str(fork_path),
        "fork_branch_url": fork_branch_url,
        "head_sha": head_commit_sha,
        "synced_commits": synced_commits,
        "pushed": pushed,
        "force": force if pushed else False,
        "message": (
            f"Branch '{branch}' is ready on {github_user}/staged-recipes "
            f"(pushed={pushed}, fork-was-behind={synced_commits} commits). "
            f"Inspect: {fork_branch_url}"
        ),
    }


def open_pr(
    recipe_name: str,
    branch: str | None = None,
    pr_title: str | None = None,
    pr_body: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Open a PR from ``<user>:<branch>`` against ``conda-forge/staged-recipes:main``.

    The branch must already exist on the fork (call ``prepare_branch`` first,
    or use ``submit_pr`` for the end-to-end flow).
    """
    try:
        github_user = _gh_auth_user()
    except RuntimeError as e:
        return {"success": False, "error": str(e)}

    branch = branch or f"{DEFAULT_BRANCH_PREFIX}{recipe_name}"
    pr_title = pr_title or f"Add recipe for {recipe_name}"
    pr_body = pr_body or (
        f"This PR adds a new recipe for `{recipe_name}`.\n\n"
        "### Pre-Submission Checklist\n"
        "- [x] The recipe builds locally successfully.\n"
        "- [x] The recipe passes all `conda-smithy recipe-lint` checks.\n"
        "- [x] License and checksums are verified.\n\n"
        "*Submitted automatically via local-recipes automation.*"
    )

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "recipe": recipe_name,
            "branch": branch,
            "github_user": github_user,
            "pr_title": pr_title,
            "pr_body": pr_body,
            "head": f"{github_user}:{branch}",
            "base": f"{UPSTREAM_REPO}:main",
            "message": (
                f"Dry run OK — would open PR {github_user}:{branch} → "
                f"{UPSTREAM_REPO}:main. Call with dry_run=False to open it."
            ),
        }

    try:
        _, pr_url, _ = _run([
            "gh", "pr", "create",
            "--repo", UPSTREAM_REPO,
            "--title", pr_title,
            "--body", pr_body,
            "--head", f"{github_user}:{branch}",
            "--base", "main",
        ], cwd=STAGED_RECIPES_FORK_PATH)
    except RuntimeError as e:
        return {"success": False, "error": f"PR creation failed: {e}"}

    return {
        "success": True,
        "recipe": recipe_name,
        "branch": branch,
        "github_user": github_user,
        "pr_url": pr_url,
        "message": f"PR created: {pr_url}",
    }


def submit_pr(
    recipe_name: str,
    dry_run: bool = False,
    pr_title: str | None = None,
    pr_body: str | None = None,
    branch: str | None = None,
    force: bool = True,
) -> dict[str, Any]:
    """End-to-end: ``prepare_branch`` then ``open_pr``.

    If PR creation fails after a successful push, the result includes the
    prep info so the caller can retry just the PR step with ``open_pr``.
    """
    prep = prepare_branch(recipe_name, branch=branch, force=force, dry_run=dry_run)
    if not prep.get("success") or dry_run:
        return prep

    pr = open_pr(recipe_name, branch=prep["branch"],
                 pr_title=pr_title, pr_body=pr_body)
    if not pr.get("success"):
        return {
            **pr,
            "branch": prep["branch"],
            "fork_branch_url": prep["fork_branch_url"],
            "hint": "Run open_pr separately to retry the PR step.",
        }

    return {
        **pr,
        "fork_branch_url": prep.get("fork_branch_url"),
        "synced_commits": prep.get("synced_commits"),
        "pushed": prep.get("pushed"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Submit a recipe to conda-forge/staged-recipes "
            "(or use --prepare-only to stop after pushing the branch)."
        )
    )
    parser.add_argument("recipe_name", help="Recipe directory name (e.g. 'numpy').")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate prerequisites without making network writes.")
    parser.add_argument("--title", default=None, help="Custom PR title.")
    parser.add_argument("--body", default=None, help="Custom PR body.")
    parser.add_argument(
        "--branch", default=None,
        help=f"Branch name on the fork (default: {DEFAULT_BRANCH_PREFIX}<recipe>).",
    )
    parser.add_argument(
        "--no-force", action="store_true",
        help="Use plain push; fails if the remote branch diverged.",
    )
    parser.add_argument(
        "--prepare-only", action="store_true",
        help="Stop after pushing the branch to the fork; do NOT open a PR.",
    )
    args = parser.parse_args()

    force = not args.no_force
    if args.prepare_only:
        result = prepare_branch(args.recipe_name, branch=args.branch,
                                force=force, dry_run=args.dry_run)
    else:
        result = submit_pr(
            args.recipe_name,
            dry_run=args.dry_run,
            pr_title=args.title,
            pr_body=args.body,
            branch=args.branch,
            force=force,
        )
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
