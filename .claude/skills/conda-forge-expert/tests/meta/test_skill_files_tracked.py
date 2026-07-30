"""Meta: every source file in the skill tree must be tracked by git.

On 2026-07-26 someone added `/.claude/skills` to `.git/info/exclude`. 919 files
under that path were already tracked, so the exclude changed nothing visible --
it only hid *new* files. Two load-bearing additions were then written, never
appeared in `git status`, and were never committed:

  * `scripts/_path_guard.py` -- the AUD-CFE-001/002/006 path-confinement helper
    that `submit_pr.py`, `recipe_editor.py` and `conda_forge_server.py` import.
    The branch that added those imports shipped without the module, so a fresh
    checkout of it raises ImportError on three recipe-facing surfaces.
  * `tests/meta/test_dashboard_renders.py` -- the correctness assertion that
    discharged half of the atlas A3 retro action.

Neither `git status` nor any doc detector could see the gap, because the tool
you would use to detect it was the tool being suppressed.

This test does NOT use `git status` / `git check-ignore`: both honour
`.git/info/exclude`, so a re-added exclude line would make them report clean.
It walks the filesystem itself and diffs against `git ls-files`.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# .claude/skills/<skill>/tests/meta/<file> -> the skill dir.
SKILL_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = SKILL_DIR.parents[2]

# Source extensions worth guarding. A new reference doc or CLI script that
# silently never lands is the same failure as an untracked .py.
GUARDED_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".json", ".sh", ".toml"}

# Directories that legitimately hold untracked content. Kept deliberately
# short -- everything else in the tree is expected to be committed.
#   data/         -- mutable runtime state, gitignored (.gitignore)
#   __pycache__/  -- bytecode
#   .pytest_cache/-- pytest run state, gitignored
TRANSIENT_DIR_NAMES = {"__pycache__", ".pytest_cache", "data"}


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout


def _is_transient(path: Path) -> bool:
    return any(part in TRANSIENT_DIR_NAMES for part in path.parts)


@pytest.mark.meta
def test_every_skill_source_file_is_tracked():
    """Filesystem walk minus `git ls-files` must be empty."""
    rel_skill = SKILL_DIR.relative_to(REPO_ROOT)
    tracked = {
        line for line in _git("ls-files", "-z", str(rel_skill)).split("\0") if line
    }

    on_disk = {
        str(p.relative_to(REPO_ROOT))
        for p in SKILL_DIR.rglob("*")
        if p.is_file()
        and p.suffix in GUARDED_SUFFIXES
        and not _is_transient(p.relative_to(REPO_ROOT))
    }

    untracked = sorted(on_disk - tracked)
    assert not untracked, (
        "source files in the skill tree are NOT tracked by git -- they will be "
        "lost on a fresh checkout and any code importing them breaks:\n  "
        + "\n  ".join(untracked)
        + "\n\nIf a path is genuinely transient, add its directory to "
        "TRANSIENT_DIR_NAMES with a reason. Otherwise `git add` it. Check "
        ".git/info/exclude and .gitignore for a rule that is hiding it from "
        "`git status`."
    )


@pytest.mark.meta
def test_git_info_exclude_does_not_suppress_the_skill_tree():
    """Direct regression guard on the root cause.

    An exclude entry covering the skill tree is invisible in every other
    signal, so name it explicitly here.
    """
    exclude = REPO_ROOT / ".git" / "info" / "exclude"
    if not exclude.is_file():
        pytest.skip("no .git/info/exclude in this checkout")

    offenders = [
        line
        for raw in exclude.read_text(encoding="utf-8").splitlines()
        if (line := raw.strip())
        and not line.startswith("#")
        and line.rstrip("/") in {"/.claude/skills", ".claude/skills", "/.claude", ".claude"}
    ]
    assert not offenders, (
        ".git/info/exclude suppresses the skill tree, so newly added skill "
        f"files never show up in `git status`: {offenders}. Remove the entry -- "
        "the tree is tracked, and this rule only hides additions."
    )
