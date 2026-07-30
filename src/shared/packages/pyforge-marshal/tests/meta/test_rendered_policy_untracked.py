"""Meta test -- Story 1.10's untracked-artifact guarantee (AD-10/AD-12/AD-35,
closing F-1). ``.bmad-loop/policy.toml`` is now a DERIVED artifact, rendered
whole from the canonical ``EffectivePolicy`` by
``adapters/harness_bmadloop.py``. It must never be git-tracked again -- a
tracked copy is exactly what let one loop home's hand-edit ride
``git push origin HEAD:main`` onto every other project (the F-1 bleed this
story's Design Notes describe). This asserts both halves of the fix:
``git ls-files`` no longer lists the file, and ``.gitignore`` covers it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _repo_root() -> Path:
    """Walk up from this test file until a ``.git`` entry (an ordinary repo's
    directory, or a linked worktree's pointer file) is found -- never a
    hardcoded parents-index count, so this keeps working regardless of how
    deep this file lives in the tree or whether it runs inside a bmad-loop
    run worktree."""
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise AssertionError(f"no .git found walking up from {current}")


def test_policy_toml_is_untracked():
    repo_root = _repo_root()
    result = subprocess.run(
        ["git", "ls-files", ".bmad-loop/policy.toml"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "", (
        ".bmad-loop/policy.toml must be untracked (git rm --cached it) -- "
        f"git ls-files still reports: {result.stdout!r}"
    )


def test_gitignore_covers_policy_toml():
    repo_root = _repo_root()
    gitignore_lines = {
        line.strip() for line in (repo_root / ".gitignore").read_text(encoding="utf-8").splitlines()
    }
    assert ".bmad-loop/policy.toml" in gitignore_lines, (
        ".gitignore must contain a literal '.bmad-loop/policy.toml' line"
    )


def test_git_check_ignore_covers_policy_toml():
    """The literal-line test above pins the spec's required .gitignore entry;
    this one asserts the effective BEHAVIOR -- a later negation pattern
    elsewhere in the ~750-line .gitignore would pass the literal check while
    silently un-ignoring the file."""
    repo_root = _repo_root()
    result = subprocess.run(
        ["git", "check-ignore", "-q", ".bmad-loop/policy.toml"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        "git check-ignore says .bmad-loop/policy.toml is NOT effectively "
        f"ignored (rc={result.returncode}): {result.stderr!r}"
    )
