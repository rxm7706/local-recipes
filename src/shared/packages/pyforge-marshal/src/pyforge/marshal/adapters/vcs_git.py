"""``GitVcs`` -- the sole implementation of ``ports.VcsPort`` (Story 1.4,
AD-4/AD-11): every ``git`` invocation this package makes lives here, via the
stdlib ``subprocess`` module. Directly ports ``scripts/bmad-loop-worktree``'s
git calls (that script's own docstring/comments carry the hard-won
rationale -- see this module's own docstrings for the specific mapping).

No new runtime dependency: ``git`` is invoked as an external process exactly
like the reference script does, never via a Python git library.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


class VcsCommandError(Exception):
    """Raised when a ``git`` invocation fails: a non-zero exit (locked
    index, a permission error, an ambiguous ref, ``start``/``repo_root`` not
    being inside a git repository, a worktree conflict), a missing ``git``
    executable, or a hung process exceeding ``_GIT_TIMEOUT_S``. Carries the
    command's stderr (or the underlying exception) in the message; never
    lets a raw ``subprocess.CalledProcessError``, ``FileNotFoundError``, or
    ``subprocess.TimeoutExpired`` escape this module (review finding:
    ``_run`` previously let both of the latter two propagate raw)."""


_GIT_TIMEOUT_S = 30.0


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args, capture_output=True, text=True, timeout=_GIT_TIMEOUT_S
        )
    except FileNotFoundError as exc:
        raise VcsCommandError(f"git executable not found: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise VcsCommandError(
            f"git command timed out after {_GIT_TIMEOUT_S}s: {' '.join(args)}"
        ) from exc


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
        return result.returncode == 0

    def worktree_path_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        """Mirrors the reference script's ``cmd_list``: parses
        ``git worktree list --porcelain`` (blank-line-delimited blocks of
        ``key value`` lines) for the block whose ``branch`` line is exactly
        ``refs/heads/<branch>``."""
        result = _run(["git", "-C", str(repo_root), "worktree", "list", "--porcelain"])
        if result.returncode != 0:
            raise VcsCommandError(
                f"git worktree list failed: {result.stderr.strip()}"
            )
        wanted = f"refs/heads/{branch}"
        for block in result.stdout.split("\n\n"):
            lines = dict(line.split(" ", 1) for line in block.splitlines() if " " in line)
            if lines.get("branch") == wanted:
                return Path(lines["worktree"])
        return None

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
        result = _run(args)
        if result.returncode != 0:
            raise VcsCommandError(f"git worktree add failed: {result.stderr.strip()}")
