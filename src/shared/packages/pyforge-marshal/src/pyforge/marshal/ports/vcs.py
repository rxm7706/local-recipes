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

Story 3.8 (stage-bound durability, AD-46) adds one more write, ``push`` --
a plain ``git push`` against a branch's already-configured upstream (or
``origin <branch>`` for a brand-new branch's first push), never ``--force``
and never a ``push -u`` that would silently rewrite a remote branch's
tracking config. This is the durability watcher's one write primitive:
``supervisor/__main__.py`` calls it at the three named stage boundaries
(after the dev commit, after the review verdict, after the merge) plus an
interval-watcher fallback, never against ``main``/the repo's primary
branch -- only the loop-home's own station branch and per-story branches,
the same scope ``remove_worktree``/``delete_branch`` already confine
themselves to. Still not an egress port (``core/egress.py``): the payload
is git objects a story's own dev/review process already produced, never
session-derived free text this port itself forwards.

Story 4.1 (story-spec promotion, AD-13/AD-24/AD-29/AD-33) adds two more
methods, ``cli/deploy.py``'s (``marshal deploy promote``) own two
primitives:

- ``commit_subjects`` -- ``git log <ref> --format=%s``, read-only: every
  commit subject reachable from ``ref``, newest-first (``git log``'s own
  default order). ``cli/deploy.py`` feeds this into
  ``core.promotion.merged_story_keys`` (AD-33: git is the sole authority
  for "merged or not"; this method is that authority's one read
  primitive) to answer AD-29's "pushed to the remote" route
  (``ref="origin/main"``) and "merged to the integration branch" route
  (``ref="main"``) -- the caller decides which ``ref`` each route needs;
  this method has no branch-name opinion of its own.
- ``commit_paths`` -- the one write: stages EXACTLY ``paths`` (an
  individual ``git add -- <path>`` per entry, never ``git add -A``) and
  commits ONLY those paths (``git commit -m <message> -- <path> <path>
  ...``, never a bare ``git commit`` that would sweep in a pre-existing
  index) -- the literal AD-29 requirement that a promotion commit contain
  only promotion paths. Returns the new commit's sha
  (``git rev-parse HEAD`` immediately after). Raises ``VcsCommandError``
  if ``paths`` is empty (a caller with nothing to promote must never call
  this) or on any git failure.

Story 4.1's own review-fix pass adds one more read-only method,
``path_has_uncommitted_changes``: ``has_uncommitted_changes`` above answers
"does the WHOLE worktree carry any uncommitted change", which is the wrong
granularity for ``cli/deploy.py``'s "already promoted" check -- that check
needs to know whether one SPECIFIC tracked file is a real, safely-committed
promotion, not whether the worktree happens to be dirty somewhere else
entirely. Motivating defect: a partial-batch failure (a ``copy_file``
succeeding into ``specs_dir`` immediately before ``commit_paths`` fails)
left a promoted file's BYTES on disk with no commit behind them; the prior
"already promoted" check only asked the filesystem "does this path exist",
so a retried run silently treated that orphaned, uncommitted file as
already-durable and never re-attempted its commit. Scoping the check to one
path (``git status --porcelain -- <path>``) fixes this without a new
whole-worktree scan.
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

    def push(self, repo_root: Path, branch: str) -> None:
        """A plain ``git push`` of ``branch`` (Story 3.8, AD-46), naming
        ``branch`` explicitly rather than relying on ``repo_root``'s own
        checked-out HEAD: if ``branch`` already has a configured upstream,
        ``git push <remote> <branch>:<remote_branch>``; otherwise
        ``git push origin <branch>`` (the branch's first push, no ``-u`` --
        this never rewrites the caller's own tracking config). ``repo_root``
        need not have ``branch`` checked out (refs are shared across every
        worktree of one repo). Never ``--force``/``--force-with-lease``,
        never a rewrite -- the durability watcher's push is read-only
        against the working tree and additive against the remote by
        construction (the only write is the remote-tracking ref update a
        push performs). Raises ``VcsCommandError`` on any git failure
        (rejected non-fast-forward, no network, no configured remote) -- the
        caller treats that as a registered ``WARN``, never a run-halting
        condition."""
        ...

    def changed_files(
        self, repo_root: Path, worktree_path: Path, *, base: str
    ) -> tuple[str, ...]:
        """Story 2.3's frozen-surface scope check (AD-27): every repo-
        relative POSIX path ``worktree_path`` has touched relative to
        ``base`` -- the UNION of (a) ``git diff --name-only
        <base>...HEAD`` run against ``worktree_path`` (committed changes
        since the merge-base, three-dot per this port's own
        ``is_branch_merged`` merge-base convention -- run against
        ``worktree_path``, not ``repo_root``, since ``HEAD`` is per-
        worktree and ``base``/refs are shared across every worktree of one
        repo) and (b) ``git status --porcelain`` in ``worktree_path``
        (uncommitted/untracked -- a story's changes are not necessarily
        committed yet at gate-evaluation time). Deduplicated, sorted.

        Read-only. Raises ``VcsCommandError`` on any git failure (an
        unresolvable ``base``, ``worktree_path`` not inside a git
        repository, a corrupted repo)."""
        ...

    def commit_subjects(self, repo_root: Path, ref: str) -> tuple[str, ...]:
        """Every commit subject line reachable from ``ref`` (Story 4.1,
        AD-33), newest-first (``git log <ref> --format=%s``'s own default
        order) -- read-only, and deliberately not deduplicated or filtered:
        the caller (``core.promotion.merged_story_keys``) tolerates a
        subject that isn't a story-merge subject at all, so this method's
        job is exhaustive enumeration, not classification. Raises
        ``VcsCommandError`` if ``ref`` does not resolve (e.g. no ``origin``
        remote configured for ``ref="origin/main"``, or a corrupted repo
        with no ``main``) or on any other git failure."""
        ...

    def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: str) -> str:
        """Story 4.1 (AD-29): stages exactly ``paths`` -- one ``git add --
        <path>`` per entry, never ``git add -A`` -- then commits ONLY those
        paths (``git commit -m <message> -- <path> <path> ...``, never a
        bare ``git commit`` that would sweep in a pre-existing index) and
        returns the new commit's sha (``git rev-parse HEAD`` immediately
        after). ``repo_root`` need not have any of ``paths`` staged already
        -- this method does the staging itself. Raises ``VcsCommandError``
        if ``paths`` is empty (a caller with nothing to promote must never
        reach this method) or on any git failure (an unwritable index, a
        path outside the working tree, nothing to commit)."""
        ...

    def path_has_uncommitted_changes(self, repo_root: Path, path: Path) -> bool:
        """``True`` if ``path`` carries ANY uncommitted state -- staged,
        unstaged, or untracked (``git status --porcelain -- <path>``,
        which already covers all three) -- ``False`` only when ``path`` is
        tracked and byte-identical to ``HEAD`` (a genuinely, safely
        committed file), which is also what this method reports for a path
        that does not exist at all (no status line, nothing to report) --
        callers that care about existence check that separately first.
        Story 4.1's own review-fix pass: the per-path counterpart to
        ``has_uncommitted_changes`` above, for ``cli/deploy.py``'s
        "already promoted" check, which must not trust a file's mere
        on-disk EXISTENCE as proof it survived a real commit. Raises
        ``VcsCommandError`` on any git failure."""
        ...
