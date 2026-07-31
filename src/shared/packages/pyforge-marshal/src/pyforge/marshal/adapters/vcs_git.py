"""``GitVcs`` -- the sole implementation of ``ports.VcsPort`` (Story 1.4,
AD-4/AD-11): every ``git`` invocation this package makes lives here, via the
stdlib ``subprocess`` module. Directly ports ``scripts/bmad-loop-worktree``'s
git calls (that script's own docstring/comments carry the hard-won
rationale -- see this module's own docstrings for the specific mapping).

No new runtime dependency: ``git`` is invoked as an external process exactly
like the reference script does, never via a Python git library.

Story 1.6 adds ``list_worktrees`` (FR-8's full-enumeration primitive), which
shares ``worktree_path_for_branch``'s own ``git worktree list --porcelain``
block parser (``_iter_worktree_blocks``) rather than duplicating it -- the
two methods differ only in whether they stop at the first matching block or
return every block.

Story 1.8 (``marshal teardown``, NFR-6/AD-29) adds four more methods:
``has_uncommitted_changes`` (``git status --porcelain``),
``is_branch_merged`` (ancestry first, then a ``commit-tree``+``git cherry``
patch-CONTENT fallback -- see that method's own docstring for the full
rationale, live-verified during planning against a throwaway repo
reproducing this repo's own squash-merge convention), and the two writes
``remove_worktree``/``delete_branch``. ``is_branch_merged``'s internal
``commit-tree`` call pins its own ``user.name``/``user.email`` and disables
``commit.gpgsign`` via ``-c`` flags (never the operator's global git
config) -- the resulting object is never referenced by any ref and is
eligible for garbage collection the moment this process exits; its identity
has no lasting effect beyond this one comparison.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from pathlib import Path

from ..ports.vcs import WorktreeEntry


class VcsCommandError(Exception):
    """Raised when a ``git`` invocation fails: a non-zero exit (locked
    index, a permission error, an ambiguous ref, ``start``/``repo_root`` not
    being inside a git repository, a worktree conflict), a missing ``git``
    executable, or a hung process exceeding its timeout tier
    (``_GIT_TIMEOUT_S`` for queries, ``_GIT_CHECKOUT_TIMEOUT_S`` for the
    tree-populating ``worktree add``). Carries the
    command's stderr (or the underlying exception) in the message; never
    lets a raw ``subprocess.CalledProcessError``, ``FileNotFoundError``, any
    other launch ``OSError`` (EACCES on a non-executable shim, ENOEXEC on a
    corrupt binary), or ``subprocess.TimeoutExpired`` escape this module
    (review finding: ``_run`` previously let all but the first propagate
    raw)."""


# Two tiers, not one flat value (review finding): a quick ref/worktree
# query hanging past 30s is a hung git, but `git worktree add` populates a
# FULL working tree -- on a large repo (this one is a staged-recipes fork)
# a cold-cache checkout can legitimately exceed 30s, and a timeout there
# SIGKILLs git mid-checkout, leaving a registered-but-partial worktree.
_GIT_TIMEOUT_S = 30.0
_GIT_CHECKOUT_TIMEOUT_S = 600.0


def _run(
    args: list[str], *, timeout_s: float = _GIT_TIMEOUT_S
) -> subprocess.CompletedProcess[str]:
    try:
        # encoding="utf-8" pins the decode: git emits paths as raw bytes,
        # and decoding with the process LOCALE would mangle a valid UTF-8
        # path under a non-UTF-8 locale (cron/systemd -- Marshal's own
        # unattended context), corrupting the reconcile comparison (review
        # finding). errors="replace": output undecodable even as UTF-8 must
        # degrade to replacement characters, not escape as a raw
        # UnicodeDecodeError (review finding).
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
        )
    except FileNotFoundError as exc:
        raise VcsCommandError(f"git executable not found: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise VcsCommandError(
            f"git command timed out after {timeout_s}s: {' '.join(args)}"
        ) from exc
    except OSError as exc:
        # Launching git can fail with more than absence: EACCES on a
        # non-executable shim, ENOEXEC on a corrupt binary -- all must land
        # in the envelope, not escape raw (review finding).
        raise VcsCommandError(f"cannot launch git: {exc}") from exc


def _iter_worktree_blocks(stdout: str) -> Iterator[dict[str, str]]:
    """Parses ``git worktree list --porcelain``'s blank-line-delimited
    blocks of ``key value`` lines into per-worktree dicts. A valueless
    marker line (``detached``, ``bare`` -- no space, so no value) normalizes
    to ``"true"`` rather than being dropped, keeping every porcelain fact a
    block carries available to callers -- today's callers key off the
    ``branch``/``worktree`` lines only (``list_worktrees`` derives
    detached-HEAD purely from the ABSENT ``branch`` line and never reads the
    ``detached`` key -- review finding: an earlier version of this docstring
    overclaimed that it did). Shared by ``worktree_path_for_branch`` (Story
    1.4, the first caller, single-branch lookup) and ``list_worktrees``
    (Story 1.6, the full-enumeration generalization) so this parse lives in
    exactly one place."""
    for block in stdout.split("\n\n"):
        lines: dict[str, str] = {}
        for line in block.splitlines():
            if " " in line:
                key, value = line.split(" ", 1)
                lines[key] = value
            elif line:
                lines[line] = "true"
        if lines:
            yield lines


class GitVcs:
    """``ports.VcsPort``'s sole implementation."""

    def repo_common_root(self, start: Path) -> Path:
        """Mirrors ``scripts/bmad-loop-worktree``'s ``repo_root()``: the
        ``--git-common-dir`` is shared by every linked worktree of one repo
        (it always resolves to the MAIN checkout's ``.git``, regardless of
        which worktree ``start`` sits inside), so its parent is the one
        stable root every loop home provisions against."""
        result = _run(
            [
                "git",
                "-C",
                str(start),
                "rev-parse",
                "--path-format=absolute",
                "--git-common-dir",
            ]
        )
        if result.returncode != 0:
            raise VcsCommandError(
                f"not inside a git repository: {start} ({result.stderr.strip()})"
            )
        return Path(result.stdout.strip()).parent

    def branch_exists(self, repo_root: Path, branch: str) -> bool:
        """Mirrors the reference script's ``has_branch`` check. Verifies
        against ``refs/heads/<branch>`` explicitly, not a bare ``<branch>``
        (review finding: a bare name lets ``rev-parse`` resolve a same-named
        TAG instead, which would make ``add_worktree`` attach in detached
        HEAD rather than create/use the intended branch)."""
        result = _run(
            [
                "git",
                "-C",
                str(repo_root),
                "rev-parse",
                "--verify",
                "--quiet",
                f"refs/heads/{branch}",
            ]
        )
        if result.returncode == 0:
            return True
        # --verify --quiet exits 1 for "ref does not exist" specifically;
        # any OTHER exit (128: not a repository, corrupt/unreadable refs, a
        # held lock) is a real failure, not absence -- conflating them made
        # add_worktree take the mint-new-branch path against an existing
        # branch, masking the real cause (review finding).
        if result.returncode == 1:
            return False
        raise VcsCommandError(
            f"git rev-parse --verify failed for refs/heads/{branch} "
            f"(exit {result.returncode}): {result.stderr.strip()}"
        )

    def worktree_path_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        """Mirrors the reference script's ``cmd_list``: parses
        ``git worktree list --porcelain`` (via ``_iter_worktree_blocks``) for
        the block whose ``branch`` line is exactly ``refs/heads/<branch>``."""
        result = _run(["git", "-C", str(repo_root), "worktree", "list", "--porcelain"])
        if result.returncode != 0:
            raise VcsCommandError(
                f"git worktree list failed: {result.stderr.strip()}"
            )
        wanted = f"refs/heads/{branch}"
        for lines in _iter_worktree_blocks(result.stdout):
            if lines.get("branch") == wanted:
                worktree = lines.get("worktree")
                if worktree is None:
                    # A matching block with no `worktree` line (a path
                    # containing a blank line splits one block in two) must
                    # surface as the port's error, not a raw KeyError
                    # (review finding).
                    raise VcsCommandError(
                        f"unparseable 'git worktree list --porcelain' block "
                        f"for {wanted}: no worktree line"
                    )
                return Path(worktree)
        return None

    def list_worktrees(self, repo_root: Path) -> tuple[WorktreeEntry, ...]:
        """Story 1.6, FR-8: generalizes ``worktree_path_for_branch``'s
        single-branch lookup (same ``_iter_worktree_blocks`` parse) to return
        EVERY block instead of stopping at the first match -- the main
        working tree (always listed first by real ``git worktree list``)
        plus every linked worktree, ``loop/<slug>`` or otherwise.
        ``branch`` is stripped back to its bare name (porcelain always
        qualifies it ``refs/heads/<branch>``); ``None`` for a detached-HEAD
        block, which carries no ``branch`` line at all."""
        result = _run(["git", "-C", str(repo_root), "worktree", "list", "--porcelain"])
        if result.returncode != 0:
            raise VcsCommandError(
                f"git worktree list failed: {result.stderr.strip()}"
            )
        entries: list[WorktreeEntry] = []
        for lines in _iter_worktree_blocks(result.stdout):
            worktree = lines.get("worktree")
            if worktree is None:
                # Same "no worktree line" defect class as
                # worktree_path_for_branch above -- surfaced here without a
                # specific wanted branch to name, since this method has none.
                raise VcsCommandError(
                    "unparseable 'git worktree list --porcelain' block: "
                    "no worktree line"
                )
            branch_ref = lines.get("branch")
            branch = branch_ref.removeprefix("refs/heads/") if branch_ref is not None else None
            entries.append(WorktreeEntry(path=Path(worktree), branch=branch))
        return tuple(entries)

    def add_worktree(self, repo_root: Path, home: Path, branch: str, *, base: str) -> None:
        """Mirrors the reference script's ``has_branch``-gated
        ``git worktree add`` call: a NEW branch is always minted FROM
        ``base`` (``-b branch home base``); an EXISTING branch attaches via
        the bare name (``add home branch``, no ``-b``) -- deliberately NOT
        the fully-qualified ``refs/heads/<branch>`` form: empirically,
        ``git worktree add`` recognizes a bare name matching a local branch
        and checks it out non-detached (with only a warning) even when a
        same-named tag also exists, while a fully-qualified ref is instead
        treated as an arbitrary commit-ish and checked out DETACHED --
        confirmed live (`git worktree add <path> refs/heads/<branch>` on a
        branch/tag collision produces detached HEAD; the bare form does
        not). ``branch_exists`` (the DETECTION step, not this write) is what
        needs the ``refs/heads/`` qualification, to avoid a same-named tag
        being mistaken for the branch's existence in the first place."""
        if self.branch_exists(repo_root, branch):
            args = ["git", "-C", str(repo_root), "worktree", "add", str(home), branch]
        else:
            args = [
                "git",
                "-C",
                str(repo_root),
                "worktree",
                "add",
                "-b",
                branch,
                str(home),
                base,
            ]
        try:
            result = _run(args, timeout_s=_GIT_CHECKOUT_TIMEOUT_S)
        except VcsCommandError as exc:
            if isinstance(exc.__cause__, subprocess.TimeoutExpired):
                # The kill can land mid-checkout, leaving a registered
                # worktree with a partial tree. Per the spec's own edge-case
                # matrix, partial state is left as-is and NEVER auto-cleaned
                # -- the operator instruction rides in the message instead.
                raise VcsCommandError(
                    f"{exc} -- if a partial worktree remains at {home}, "
                    f"remove it with 'git worktree remove --force {home}' "
                    "and 'git worktree prune' before re-running"
                ) from exc.__cause__
            raise
        if result.returncode != 0:
            raise VcsCommandError(f"git worktree add failed: {result.stderr.strip()}")

    def has_uncommitted_changes(self, worktree_path: Path) -> bool:
        """``git status --porcelain`` against ``worktree_path`` -- its
        output already covers untracked files, so no separate check is
        needed (Story 1.8's own Boundaries & Constraints). ``-c
        status.showUntrackedFiles=normal`` pins the setting explicitly
        (review finding: an operator's global/local config setting it to
        ``no`` would otherwise hide untracked files from this exact check,
        silently defeating the refusal this method exists to drive) --
        mirrors ``is_branch_merged``'s own explicit-config-pin discipline
        below."""
        result = _run(
            [
                "git",
                "-C",
                str(worktree_path),
                "-c",
                "status.showUntrackedFiles=normal",
                "status",
                "--porcelain",
            ]
        )
        if result.returncode != 0:
            raise VcsCommandError(
                f"git status --porcelain failed in {worktree_path}: {result.stderr.strip()}"
            )
        return bool(result.stdout.strip())

    def is_branch_merged(self, repo_root: Path, branch: str, *, into: str) -> bool:
        """Tries cheap ancestry first (``git merge-base --is-ancestor``,
        exactly ``branch_exists``'s own exit-code discipline: only exit 1
        means "not an ancestor" specifically, any other non-zero exit is a
        real failure) -- covers plain fast-forward/real-merge workflows for
        free. Falls back to patch-CONTENT equivalence only when ancestry
        says no: builds a detached virtual commit (``branch``'s own tree,
        reparented onto ``merge-base(into, branch)`` via ``commit-tree``)
        and compares it against ``into`` via ``git cherry``'s patch-id
        matching -- confirmed live to correctly read this repo's own
        single-parent SQUASH-merge convention as merged, even after
        ``into`` has since advanced further (see this story's spec Design
        Notes for the live-verified walkthrough)."""
        branch_ref = f"refs/heads/{branch}"
        into_ref = f"refs/heads/{into}"

        ancestry = _run(
            ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", branch_ref, into_ref]
        )
        if ancestry.returncode == 0:
            return True
        if ancestry.returncode != 1:
            raise VcsCommandError(
                f"git merge-base --is-ancestor failed for {branch_ref}..{into_ref} "
                f"(exit {ancestry.returncode}): {ancestry.stderr.strip()}"
            )

        merge_base_result = _run(
            ["git", "-C", str(repo_root), "merge-base", branch_ref, into_ref]
        )
        if merge_base_result.returncode != 0:
            raise VcsCommandError(
                f"cannot find a merge base for {branch_ref} and {into_ref}: "
                f"{merge_base_result.stderr.strip()}"
            )
        merge_base = merge_base_result.stdout.strip()

        tree_result = _run(
            ["git", "-C", str(repo_root), "rev-parse", f"{branch_ref}^{{tree}}"]
        )
        if tree_result.returncode != 0:
            raise VcsCommandError(
                f"cannot resolve the tree of {branch_ref}: {tree_result.stderr.strip()}"
            )
        tree = tree_result.stdout.strip()

        base_tree_result = _run(
            ["git", "-C", str(repo_root), "rev-parse", f"{merge_base}^{{tree}}"]
        )
        if base_tree_result.returncode != 0:
            raise VcsCommandError(
                f"cannot resolve the tree of the merge base {merge_base}: "
                f"{base_tree_result.stderr.strip()}"
            )
        if tree == base_tree_result.stdout.strip():
            # A net-zero branch (e.g. a change and its revert): the branch's
            # tree is IDENTICAL to the merge base's, so `into` already
            # reaches every byte the branch carries. The virtual-commit path
            # below cannot answer this case -- its commit would carry an
            # EMPTY diff, and `git cherry` reports an empty-diff commit as
            # "+" (no equivalent patch on `into`; live-verified), which
            # would spuriously refuse a branch with nothing to lose (review
            # finding). Answer by tree equality first.
            return True

        # -c user.name/user.email/commit.gpgsign=false: pinned explicitly so
        # this NEVER depends on (or blocks on) the operator's global git
        # config in an unattended context (Story 1.8's own Boundaries &
        # Constraints) -- the resulting object is never referenced by any
        # ref, so its identity has no lasting effect beyond this comparison.
        commit_tree_result = _run(
            [
                "git",
                "-C",
                str(repo_root),
                "-c",
                "user.name=marshal-teardown",
                "-c",
                "user.email=marshal-teardown@localhost",
                "-c",
                "commit.gpgsign=false",
                "commit-tree",
                tree,
                "-p",
                merge_base,
                "-m",
                "marshal teardown merged-check (not a real commit)",
            ]
        )
        if commit_tree_result.returncode != 0:
            raise VcsCommandError(
                f"cannot build the virtual merged-check commit for {branch_ref}: "
                f"{commit_tree_result.stderr.strip()}"
            )
        virtual_commit = commit_tree_result.stdout.strip()

        # _GIT_CHECKOUT_TIMEOUT_S, not the default query timeout: `git
        # cherry` computes a patch-id (a full diff) for every commit on
        # `into` since the merge base -- history-proportional work, and loop
        # homes routinely fork long before teardown, so on a large repo a
        # cold-cache scan can exceed 30s (review finding: the same
        # large-repo reasoning remove_worktree's own extended timeout
        # already applies).
        cherry_result = _run(
            ["git", "-C", str(repo_root), "cherry", into_ref, virtual_commit],
            timeout_s=_GIT_CHECKOUT_TIMEOUT_S,
        )
        if cherry_result.returncode != 0:
            raise VcsCommandError(
                f"git cherry failed comparing {branch_ref} against {into_ref}: "
                f"{cherry_result.stderr.strip()}"
            )
        # "-" = a commit on `into` already carries an equivalent patch
        # (merged); "+" = no equivalent found on `into` (genuinely
        # unmerged). Every live trial during planning produced exactly one
        # line (the single virtual commit is never itself reachable from
        # `into`, by construction) -- an EMPTY result is therefore an
        # unproven shape, not a confirmed-safe one, so this fails loud
        # (review finding: `all()` over an empty sequence is vacuously
        # True, which would make a safety gate default to "safe to delete"
        # on input nobody has ever observed) rather than silently reporting
        # "merged".
        lines = [line for line in cherry_result.stdout.splitlines() if line.strip()]
        if not lines:
            raise VcsCommandError(
                f"git cherry produced no output comparing the virtual commit "
                f"for {branch_ref} against {into_ref} -- expected exactly one "
                "line for the one virtual commit; refusing to guess"
            )
        return all(line.startswith("-") for line in lines)

    def remove_worktree(self, repo_root: Path, home: Path, *, force: bool = False) -> None:
        """``git worktree remove``, optionally ``--force``. ``force`` is the
        caller's decision (``run_teardown``'s own refusal logic), never
        inferred here. Uses ``_GIT_CHECKOUT_TIMEOUT_S`` (review finding:
        removing a worktree deletes the SAME full tree ``add_worktree``
        populates -- this repo's own large-tree cold-cache rationale for
        that method's extended timeout applies symmetrically here; the
        default query timeout could SIGKILL a large removal mid-delete,
        leaving a partial worktree)."""
        args = ["git", "-C", str(repo_root), "worktree", "remove"]
        if force:
            args.append("--force")
        args.append(str(home))
        result = _run(args, timeout_s=_GIT_CHECKOUT_TIMEOUT_S)
        if result.returncode != 0:
            raise VcsCommandError(
                f"git worktree remove failed for {home}: {result.stderr.strip()}"
            )

    def delete_branch(self, repo_root: Path, branch: str, *, force: bool = False) -> None:
        """``git branch -d``/``-D``, selected by ``force``. See the port's
        own docstring for why a caller that already ran ``is_branch_merged``
        passes ``force=True`` rather than relying on git's own
        ancestry-only ``-d`` heuristic."""
        flag = "-D" if force else "-d"
        result = _run(["git", "-C", str(repo_root), "branch", flag, branch])
        if result.returncode != 0:
            raise VcsCommandError(
                f"git branch {flag} failed for {branch}: {result.stderr.strip()}"
            )
