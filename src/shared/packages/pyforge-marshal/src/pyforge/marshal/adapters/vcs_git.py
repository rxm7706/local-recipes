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
