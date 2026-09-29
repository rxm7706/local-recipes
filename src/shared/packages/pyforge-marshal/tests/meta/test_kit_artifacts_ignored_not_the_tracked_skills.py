"""Meta test -- Story 28.3 (SPEC-marshal-token-economy CAP-3/CAP-4): every
token-economy kit artifact Genesis provisions is git-ignored, and the
TRACKED skill tree around one of them is not.

The same collision Story 28.2's ``.marshal/wire/`` rule had, one directory
over and sharper. Genesis deploys the caveman skill to
``.claude/skills/caveman/SKILL.md`` inside a live loop home, and this repo
TRACKS ``.claude/skills/**`` -- the conda-forge-expert skill, the pyforge-*
station skills, `.claude/settings.json`. So:

- the kit's own artifacts must be ignored, for exactly the two reasons the
  CCR store is: ``bmad-loop run`` refuses to start on a dirty worktree, and
  the loop's own ``git add -A`` would otherwise sweep tool-deployed files
  into a merge commit;
- everything else under ``.claude/`` must stay visible, or an ignore rule
  written for the kit would quietly stop tracking real source.

Paths are DERIVED from ``seed/model/kit.py``'s own constants rather than
re-spelled here -- the gap Story 28.2's review left open on its own ignore
meta test ("the path is a module-level literal ... so relocating the store
in the TOML would leave the test passing against a path nothing uses").
Relocating a kit item now fails this test instead.

Effective BEHAVIOR via ``git check-ignore``, never a literal grep of
``.gitignore``: a negation pattern later in the ~880-line file would pass a
literal check while silently changing the outcome
(``test_rendered_policy_untracked.py``'s own reasoning).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.seed.model.kit import (
    CAVEMAN_SKILL_RELPATH,
    CCR_STORE_RELPATH,
    CODEGRAPH_INDEX_RELPATH,
)

#: Each kit artifact at a worktree root AND one directory deeper -- a loop
#: home is normally its own worktree root, but an anchored rule would
#: silently stop ignoring the moment a home sat below one.
_IGNORED = tuple(
    prefix + relpath
    for relpath in (
        CAVEMAN_SKILL_RELPATH,
        CODEGRAPH_INDEX_RELPATH,
        f"{CCR_STORE_RELPATH}/ccr_store.db",
    )
    for prefix in ("", "homes/acme/")
) + (
    # codegraph's own self-ignoring `.gitignore` is deliberately VISIBLE to
    # git ("ignore everything here except this file"), so the index bytes
    # were already covered while the directory still showed up untracked --
    # the concrete `?? .codegraph/` a live `marshal seed kit --apply` left
    # behind before the rule existed.
    ".codegraph/.gitignore",
)

#: Tracked source in the same namespace the caveman rule has to thread.
_NOT_IGNORED = (
    ".claude/skills/conda-forge-expert/SKILL.md",
    ".claude/skills/pyforge-marshal/SKILL.md",
    ".claude/settings.json",
    ".claude/memory/MEMORY.md",
)


def _repo_root() -> Path:
    """Walk up until a ``.git`` entry (an ordinary repo's directory, or a
    linked worktree's pointer file) -- never a hardcoded parents index, so
    this keeps working inside a dispatch/bmad-loop run worktree."""
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise AssertionError(f"no .git found walking up from {current}")


def _check_ignore(path: str) -> subprocess.CompletedProcess[str]:
    # `--no-index` so the answer is about the RULES, not about whether the
    # path happens to exist or be tracked in this particular checkout.
    return subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", "--", path],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.mark.parametrize("path", _IGNORED)
def test_every_kit_artifact_is_ignored(path: str) -> None:
    result = _check_ignore(path)
    assert result.returncode == 0, (
        f"{path} must be git-ignored -- a Genesis-provisioned kit artifact "
        "would otherwise dirty a loop worktree (blocking `bmad-loop run`) "
        f"and be swept into a commit by `git add -A` (rc={result.returncode})"
    )


@pytest.mark.parametrize("path", _NOT_IGNORED)
def test_the_tracked_claude_tree_is_not_shadowed(path: str) -> None:
    result = _check_ignore(path)
    assert result.returncode == 1, (
        f"{path} must NOT be git-ignored: it is tracked source. The caveman "
        "deployment rule has to be scoped to `.claude/skills/caveman/`, "
        "never to `.claude/` or `.claude/skills/` "
        f"(rc={result.returncode}, matched: {result.stdout.strip()!r})"
    )
