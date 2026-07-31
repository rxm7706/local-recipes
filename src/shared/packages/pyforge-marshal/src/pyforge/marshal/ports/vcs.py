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

Story 1.8 (``marshal teardown``, NFR-6/AD-29) adds four more methods, the
git-truthful primitives ``run_teardown`` composes its refusal decision from:

- ``has_uncommitted_changes`` -- the dirty-working-tree probe
  (``git status --porcelain``, which already covers untracked files).
- ``is_branch_merged`` -- "is this branch's content already safely captured
  elsewhere", answered by patch-CONTENT equivalence rather than bare
  commit-SHA ancestry (the story's own Design Notes: this repo's own
  bmad-loop landing convention produces single-parent SQUASH commits that
  ancestry alone misreports as unmerged forever).
- ``remove_worktree``/``delete_branch`` -- the two writes, gated by
  ``run_teardown``'s own refusal decision rather than attempted
  unconditionally.
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

    def has_uncommitted_changes(self, worktree_path: Path) -> bool:
        """``True`` if ``worktree_path``'s working tree carries any
        uncommitted change -- staged, unstaged, OR untracked
        (``git status --porcelain`` already reports untracked files, so no
        separate check is needed -- Story 1.8's own Boundaries &
        Constraints). Raises ``VcsCommandError`` on any git failure."""
        ...

    def is_branch_merged(self, repo_root: Path, branch: str, *, into: str) -> bool:
        """``True`` if ``branch``'s content is already safely captured on
        ``into`` -- patch-CONTENT equivalence, never bare commit-SHA
        ancestry (Story 1.8, AD-29's F-14 amendment): tries the cheap
        ``git merge-base --is-ancestor`` check first (covers fast-forward/
        real-merge workflows for free), then falls back to comparing a
        detached virtual commit -- ``branch``'s tree, reparented onto
        ``merge-base(into, branch)`` -- against ``into`` via ``git
        cherry``'s patch-id matching, which correctly reads a SQUASH-merged
        branch (this repo's own landing convention: a single-parent "merge"
        commit whose tip is never an ancestor of ``into``) as merged even
        after ``into`` has since advanced further. Raises
        ``VcsCommandError`` on any git failure."""
        ...

    def remove_worktree(self, repo_root: Path, home: Path, *, force: bool = False) -> None:
        """Remove the worktree at ``home`` (``git worktree remove``).
        ``force`` passes ``--force`` -- reserved for the path where the
        operator's own ``--force`` was needed to authorize a refused
        teardown; a home ``run_teardown`` has already verified safe removes
        with no flag. Raises ``VcsCommandError`` on any git failure."""
        ...

    def delete_branch(self, repo_root: Path, branch: str, *, force: bool = False) -> None:
        """Delete ``branch`` (``git branch -d``/``-D``). ``force`` selects
        ``-D``: git's own ``-d`` uses commit-SHA ancestry and would
        spuriously refuse a branch this port's own ``is_branch_merged``
        already proved safe by CONTENT (the squash-merge case) -- a caller
        that trusts its own merged-check passes ``force=True`` rather than
        relying on git's weaker heuristic. Raises ``VcsCommandError`` on any
        git failure."""
        ...
