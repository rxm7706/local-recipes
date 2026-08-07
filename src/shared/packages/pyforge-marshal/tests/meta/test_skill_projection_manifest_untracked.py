"""Meta test -- Story 6.2's untracked-artifact guarantee (AD-12/AD-36),
mirroring ``test_rendered_policy_untracked.py``'s exact three-part shape
for a second derived artifact: ``.bmad-loop/skill-projection.json``
(``cli/adapters.py::run_adapters_sync``'s manifest) and the projected
skill tree(s) themselves under ``.agents/``. Both are DERIVED (AD-12):
regenerable from the canonical ``.claude/skills`` tree, never hand-edited,
and must never ride a loop-home's own ``git push origin HEAD:main`` onto
every other project -- the same F-1-class bleed
``test_rendered_policy_untracked.py`` already guards for
``.bmad-loop/policy.toml``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise AssertionError(f"no .git found walking up from {current}")


def test_skill_projection_manifest_is_untracked():
    repo_root = _repo_root()
    result = subprocess.run(
        ["git", "ls-files", ".bmad-loop/skill-projection.json"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "", (
        ".bmad-loop/skill-projection.json must be untracked -- git ls-files "
        f"still reports: {result.stdout!r}"
    )


def test_gitignore_covers_skill_projection_manifest():
    repo_root = _repo_root()
    gitignore_lines = {
        line.strip() for line in (repo_root / ".gitignore").read_text(encoding="utf-8").splitlines()
    }
    assert ".bmad-loop/skill-projection.json" in gitignore_lines, (
        ".gitignore must contain a literal '.bmad-loop/skill-projection.json' line"
    )


def test_git_check_ignore_covers_skill_projection_manifest():
    repo_root = _repo_root()
    result = subprocess.run(
        ["git", "check-ignore", "-q", ".bmad-loop/skill-projection.json"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        "git check-ignore says .bmad-loop/skill-projection.json is NOT "
        f"effectively ignored (rc={result.returncode}): {result.stderr!r}"
    )


def test_gitignore_covers_projected_agents_tree():
    repo_root = _repo_root()
    gitignore_lines = {
        line.strip() for line in (repo_root / ".gitignore").read_text(encoding="utf-8").splitlines()
    }
    assert "/.agents/" in gitignore_lines, ".gitignore must contain a literal '/.agents/' line"


def test_git_check_ignore_covers_projected_agents_tree():
    repo_root = _repo_root()
    result = subprocess.run(
        ["git", "check-ignore", "-q", ".agents/skills"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        "git check-ignore says .agents/skills is NOT effectively ignored "
        f"(rc={result.returncode}): {result.stderr!r}"
    )
