"""``VcsPort`` -- the git-worktree seam ``cli/init.py`` depends on (Story
1.4, architecture spine AD-11). A Protocol definition only (Structural
Seed: ``ports/`` declares shapes, never implementations); implemented
solely by ``adapters/vcs_git.py`` (AD-4). Not an egress port: nothing here
ever leaves the local git repository.

Four methods are a direct port of one piece of ``scripts/bmad-loop-worktree``'s
``provision()`` logic (the design reference named by Story 1.4's spec) --
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

A fifth method, ``list_worktrees`` (Story 1.6, FR-8), generalizes
``worktree_path_for_branch``'s single-branch lookup to the FULL enumeration
``marshal homes`` needs to auto-discover every loop home: every block of
``git worktree list --porcelain``'s output, not just the first match for one
branch. It returns ``WorktreeEntry`` -- a small frozen value type, not a
Protocol method -- carrying each worktree's path and branch (``None`` for a
detached HEAD).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class WorktreeEntry:
    """One block of ``git worktree list --porcelain``'s output (Story 1.6):
    a worktree's ``path`` and the bare ``branch`` name checked out there
    (e.g. ``"loop/acme"``, never the fully-qualified ``refs/heads/loop/acme``
    form the porcelain output itself carries) -- ``None`` for a detached-HEAD
    worktree, which has no ``branch`` line at all."""

    path: Path
    branch: str | None


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

    def list_worktrees(self, repo_root: Path) -> tuple[WorktreeEntry, ...]:
        """Every worktree git has registered for the repo rooted at
        ``repo_root`` (Story 1.6, FR-8): the main working tree (always
        present, always listed first by ``git worktree list``) plus every
        linked worktree, ``loop/<slug>`` or otherwise -- the full
        enumeration ``marshal homes`` auto-discovers every loop home from.
        Raises ``VcsCommandError`` on any git failure."""
        ...
