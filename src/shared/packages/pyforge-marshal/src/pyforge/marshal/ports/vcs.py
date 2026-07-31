"""``VcsPort`` -- the git-worktree seam ``cli/init.py`` depends on (Story
1.4, architecture spine AD-11). A Protocol definition only (Structural
Seed: ``ports/`` declares shapes, never implementations); implemented
solely by ``adapters/vcs_git.py`` (AD-4). Not an egress port: nothing here
ever leaves the local git repository.

Four methods, each a direct port of one piece of ``scripts/bmad-loop-worktree``'s
``provision()`` logic (the design reference named by this story's spec) --
ported rather than shelled out to, so ``cli/init.py`` observes and classifies
every git operation instead of treating the script as an opaque write:

- ``repo_common_root`` -- mirrors the script's own ``repo_root()``: resolve
  the MAIN checkout's root via ``git rev-parse --git-common-dir`` from any
  starting path, so a ``marshal init`` invoked from inside another linked
  worktree still finds the one shared ``.git``.
- ``branch_exists`` -- mirrors the script's ``has_branch`` check
  (``git rev-parse --verify --quiet <branch>``).
- ``worktree_path_for_branch`` -- the git-truthful "is this branch already
  provisioned, and where" query (parses ``git worktree list --porcelain``,
  like the script's own ``cmd_list``): reconciliation compares this against
  the computed home path rather than trusting a bare directory's existence,
  which could be any unrelated directory squatting on the same name.
- ``add_worktree`` -- the one write: creates the worktree, choosing whether
  to mint a new branch (always FROM ``base``, never checking ``base`` itself
  out a second time) or attach to an already-existing one, exactly like the
  script's ``has_branch``-gated ``git worktree add`` call.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class VcsPort(Protocol):
    def repo_common_root(self, start: Path) -> Path:
        """The main checkout's root, resolved from ``start`` (which may
        itself be inside a linked worktree). Raises ``VcsCommandError`` if
        ``start`` is not inside a git repository."""
        ...

    def branch_exists(self, repo_root: Path, branch: str) -> bool:
        """``True`` if ``branch`` already exists as a ref in the repo rooted
        at ``repo_root``."""
        ...

    def worktree_path_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        """The path of the worktree git already has checked out for
        ``branch``, or ``None`` if no worktree holds it."""
        ...

    def add_worktree(self, repo_root: Path, home: Path, branch: str, *, base: str) -> None:
        """Create a worktree at ``home`` on ``branch``. If ``branch`` does
        not yet exist it is created FROM ``base`` (``base`` itself is never
        checked out into ``home``); if it already exists, ``home`` attaches
        to it directly. Raises ``VcsCommandError`` on any git failure."""
        ...
