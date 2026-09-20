"""``GitVcs`` -- the sole implementation of ``ports.VcsPort`` (Story 1.4,
AD-4/AD-11): every ``git`` invocation this package makes lives here, via the
stdlib ``subprocess`` module. Directly ports ``scripts/bmad-loop-worktree``'s
git calls (that script's own docstring/comments carry the hard-won
rationale -- see this module's own docstrings for the specific mapping).

No new runtime dependency: ``git`` is invoked as an external process exactly
like the reference script does, never via a Python git library.

Story 4.12 (a landing leaves the loop home current with ``main``, FR-173)
adds ``fetch`` (``git fetch <remote> <ref>``, a network read) and
``fast_forward`` (``git merge --ff-only <ref>``, tree-mutating) --
``cli/land.py``'s own post-merge resync primitives, keeping a loop home's
station branch current with the base branch after a wave lands.

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

Story 4.1 (story-spec promotion, AD-13/AD-24/AD-29/AD-33) adds
``commit_subjects`` (``git log <ref> --format=%s``, read-only) and
``commit_paths`` (the one real, PERSISTENT write this module adds since
``push``: an individual ``git add -- <path>`` per entry, then ``git commit
-m <message> -- <path> ...``, unlike ``is_branch_merged``'s own throwaway
``commit-tree`` object -- this commit is meant to survive, so it uses the
operator's own git identity/signing config, never a pinned fake one).
Story 4.1's own review-fix pass adds one more, ``path_has_uncommitted_changes``
(``git status --porcelain -- <path>``, read-only) -- the per-path
counterpart ``cli/deploy.py``'s "already promoted" check needs, closing a
partial-batch-failure gap the on-disk-existence-only version of that check
had (see ``ports/vcs.py``'s own docstring for the full incident).

Story 4.3 (review-cap landing, FR-27/AD-24) adds ``merge_base``
(``git merge-base a b``, read-only), ``resolve_ref`` (``git rev-parse
--verify refs/heads/<ref>``, read-only), and ``merge_branch`` --
``cli/deploy.py``'s (``marshal deploy land-story``) own primitives. See
``ports/vcs.py``'s own docstring for the full rationale.

Code review (2026-08-06, P1, Blind Hunter + Edge Case Hunter, both
independently) redesigned ``merge_branch``: the ORIGINAL implementation ran
``git checkout into`` directly against ``repo_root`` -- this project's ONE
shared, currently-active working directory, not an isolated worktree, with
no dirty-tree precondition and no restoration of whatever was checked out
before. A ``land-story`` invocation could silently switch the operator's own
currently-checked-out branch, lose uncommitted context, or race with
concurrent work in that same checkout. ``merge_branch`` now NEVER checks out
or otherwise mutates ``repo_root``'s own active working tree: it performs
the merge in a throwaway DETACHED worktree instead (``git worktree add
--detach``), then advances the real ``into`` branch ref via a three-arg
``git update-ref refs/heads/<into> <new> <old>`` compare-and-swap -- which
also closes the P4 TOCTOU gap a blind ref update would leave (``into``
moving between when this method reads its tip and when it advances it) --
and finally removes the temp worktree in a ``finally`` block, on every exit
path, conflict or CAS failure included."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Iterator, Sequence
from pathlib import Path

from pyforge.core.errors import PyforgeError
from pyforge.core.process import PosixProcess, ProcessError, ProcessResult

from ..ports.vcs import WorktreeEntry


class VcsCommandError(PyforgeError, Exception):
    """Story 14.3, SPEC-pyforge-core CAP-5: gains ``PyforgeError`` as an
    additional base -- ``Exception`` stays in the MRO.

    Raised when a ``git`` invocation fails: a non-zero exit (locked
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
# `git push` is a NETWORK call, not a local tree-populating one -- reusing
# `_GIT_CHECKOUT_TIMEOUT_S` (sized for a cold-cache local `worktree add`)
# conflated the two (review finding). A dedicated, larger tier: this
# package's other timeouts are all sub-30s local-process budgets (see
# `_VERSION_TIMEOUT_S`/`_STOP_TIMEOUT_S` in `harness_bmadloop.py`), none of
# which touch a real network round-trip, so there is no existing
# network-call precedent to mirror -- 120s gives a slow/congested push
# plenty of headroom without leaving a hung push indefinitely blocking the
# tick loop's durability watcher.
_GIT_PUSH_TIMEOUT_S = 120.0
# `git fetch` is likewise a network round-trip, not a local query -- mirrors
# `_GIT_PUSH_TIMEOUT_S`'s own reasoning exactly (Story 4.12, FR-173).
_GIT_FETCH_TIMEOUT_S = 120.0


def _run(args: list[str], *, timeout_s: float = _GIT_TIMEOUT_S) -> ProcessResult:
    """Story 14.4, SPEC-pyforge-core CAP-6: delegates the actual launch to
    ``pyforge.core.process.PosixProcess().run(...)`` -- ``cwd=Path.cwd()``
    since every ``args`` list already carries its own ``-C <repo_root>``
    (git argument, never relying on the process's own working directory,
    exactly as this module's calls always have). ``PosixProcess.run`` wraps
    every launch failure (missing executable, timeout, other ``OSError``) in
    ONE ``ProcessError``, carrying the original exception as its own
    ``__cause__`` -- re-derives the SAME three ``VcsCommandError`` messages
    this method has always raised (``__cause__`` set to the ORIGINAL stdlib
    exception, not the intermediate ``ProcessError``, so
    ``add_worktree``'s own ``isinstance(exc.__cause__,
    subprocess.TimeoutExpired)`` branch keeps working unchanged -- this
    story's own I/O matrix)."""
    try:
        return PosixProcess().run(args, cwd=Path.cwd(), timeout_s=timeout_s)
    except ProcessError as exc:
        cause = exc.__cause__
        if isinstance(cause, FileNotFoundError):
            raise VcsCommandError(f"git executable not found: {cause}") from cause
        if isinstance(cause, subprocess.TimeoutExpired):
            raise VcsCommandError(f"git command timed out after {timeout_s}s: {' '.join(args)}") from cause
        # Launching git can fail with more than absence: EACCES on a
        # non-executable shim, ENOEXEC on a corrupt binary, an embedded NUL
        # byte -- all must land in the envelope, not escape raw (review
        # finding, pre-Story-14.4). `cause` is `None` for `PosixProcess`'s own
        # empty-argv guard (it raises with no `from` clause) -- `exc` itself
        # already carries that message, so fall back to it rather than
        # stringifying/chaining from a bare `None` (Story 14.4 review finding).
        raise VcsCommandError(f"cannot launch git: {cause or exc}") from (cause or exc)


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
            raise VcsCommandError(f"not inside a git repository: {start} ({result.stderr.strip()})")
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
            f"git rev-parse --verify failed for refs/heads/{branch} (exit {result.returncode}): {result.stderr.strip()}"
        )

    def worktree_path_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        """Mirrors the reference script's ``cmd_list``: parses
        ``git worktree list --porcelain`` (via ``_iter_worktree_blocks``) for
        the block whose ``branch`` line is exactly ``refs/heads/<branch>``."""
        result = _run(["git", "-C", str(repo_root), "worktree", "list", "--porcelain"])
        if result.returncode != 0:
            raise VcsCommandError(f"git worktree list failed: {result.stderr.strip()}")
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
                        f"unparseable 'git worktree list --porcelain' block for {wanted}: no worktree line"
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
            raise VcsCommandError(f"git worktree list failed: {result.stderr.strip()}")
        entries: list[WorktreeEntry] = []
        for lines in _iter_worktree_blocks(result.stdout):
            worktree = lines.get("worktree")
            if worktree is None:
                # Same "no worktree line" defect class as
                # worktree_path_for_branch above -- surfaced here without a
                # specific wanted branch to name, since this method has none.
                raise VcsCommandError("unparseable 'git worktree list --porcelain' block: no worktree line")
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
        being mistaken for the branch's existence in the first place.

        The mint-new-branch form always passes ``--no-track``: git's own
        ``branch.autoSetupMerge`` default auto-configures the new branch's
        upstream to ``base`` whenever ``base`` is a remote-tracking ref
        (every dispatch/loop-home caller passes ``origin/main`` or similar).
        Left alone, that silently makes ``push()``'s already-has-upstream
        path push ``<branch>:main`` instead of ``<branch>:<branch>`` --
        rejected by the remote as non-fast-forward, and indistinguishable
        from a real landing failure until someone inspects
        ``<branch>@{upstream}`` by hand (confirmed live: three concurrent
        dispatches all silently blocked on exactly this, 2026-08-30/31)."""
        if self.branch_exists(repo_root, branch):
            args = ["git", "-C", str(repo_root), "worktree", "add", str(home), branch]
        else:
            args = [
                "git",
                "-C",
                str(repo_root),
                "worktree",
                "add",
                "--no-track",
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
            raise VcsCommandError(f"git status --porcelain failed in {worktree_path}: {result.stderr.strip()}")
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

        ancestry = _run(["git", "-C", str(repo_root), "merge-base", "--is-ancestor", branch_ref, into_ref])
        if ancestry.returncode == 0:
            return True
        if ancestry.returncode != 1:
            raise VcsCommandError(
                f"git merge-base --is-ancestor failed for {branch_ref}..{into_ref} "
                f"(exit {ancestry.returncode}): {ancestry.stderr.strip()}"
            )

        merge_base_result = _run(["git", "-C", str(repo_root), "merge-base", branch_ref, into_ref])
        if merge_base_result.returncode != 0:
            raise VcsCommandError(
                f"cannot find a merge base for {branch_ref} and {into_ref}: {merge_base_result.stderr.strip()}"
            )
        merge_base = merge_base_result.stdout.strip()

        tree_result = _run(["git", "-C", str(repo_root), "rev-parse", f"{branch_ref}^{{tree}}"])
        if tree_result.returncode != 0:
            raise VcsCommandError(f"cannot resolve the tree of {branch_ref}: {tree_result.stderr.strip()}")
        tree = tree_result.stdout.strip()

        base_tree_result = _run(["git", "-C", str(repo_root), "rev-parse", f"{merge_base}^{{tree}}"])
        if base_tree_result.returncode != 0:
            raise VcsCommandError(
                f"cannot resolve the tree of the merge base {merge_base}: {base_tree_result.stderr.strip()}"
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
                f"cannot build the virtual merged-check commit for {branch_ref}: {commit_tree_result.stderr.strip()}"
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
                f"git cherry failed comparing {branch_ref} against {into_ref}: {cherry_result.stderr.strip()}"
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
            raise VcsCommandError(f"git worktree remove failed for {home}: {result.stderr.strip()}")

    def prune_worktrees(self, repo_root: Path) -> None:
        """``git worktree prune`` -- clears stale worktree registrations
        left behind when a worktree's directory was removed by some means
        other than ``remove_worktree`` (Story 51.1's best-effort cleanup
        fallback, mirroring ``merge_branch``'s own two-stage cleanup)."""
        result = _run(["git", "-C", str(repo_root), "worktree", "prune"])
        if result.returncode != 0:
            raise VcsCommandError(f"git worktree prune failed for {repo_root}: {result.stderr.strip()}")

    def delete_branch(self, repo_root: Path, branch: str, *, force: bool = False) -> None:
        """``git branch -d``/``-D``, selected by ``force``. See the port's
        own docstring for why a caller that already ran ``is_branch_merged``
        passes ``force=True`` rather than relying on git's own
        ancestry-only ``-d`` heuristic."""
        flag = "-D" if force else "-d"
        result = _run(["git", "-C", str(repo_root), "branch", flag, branch])
        if result.returncode != 0:
            raise VcsCommandError(f"git branch {flag} failed for {branch}: {result.stderr.strip()}")

    def tracked_paths_matching(self, repo_root: Path, pathspec: str) -> tuple[str, ...]:
        """Story 1.11 (FR-178): ``git ls-files -- <pathspec>``, read-only.

        A leading ``/`` (gitignore's "anchored at the repo root") is stripped,
        since ls-files pathspecs are already root-relative -- without that,
        every anchored rule would silently match nothing and the check would
        report a clean tree over a shadowed one. A failing invocation returns
        empty rather than raising: this is a diagnostic, and an unreadable
        answer must not turn preflight into a refusal."""
        spec = pathspec.lstrip("/") or "."
        result = _run(["git", "-C", str(repo_root), "ls-files", "--", spec])
        if result.returncode != 0:
            return ()
        return tuple(line for line in result.stdout.splitlines() if line.strip())

    def push(self, repo_root: Path, branch: str) -> None:
        """Story 3.8 (AD-46): resolves whether ``branch`` already has a
        configured upstream via ``git rev-parse --abbrev-ref
        <branch>@{upstream}`` -- exit 0 means one exists (``origin/x``-shaped
        output, split on the first ``/`` into the remote name and the
        remote-side branch name, then pushed EXPLICITLY,
        ``git push <remote> <branch>:<remote_branch>``); a non-zero exit
        whose stderr carries git's own "no upstream configured for branch"
        wording (128, the ordinary case for a brand-new station/per-story
        branch) falls back to ``git push origin <branch>``, the branch's
        first push. Any OTHER non-zero exit (an ambiguous ref, "no such
        branch" because ``branch`` itself does not exist locally, a
        corrupted repo) is NOT treated as "no upstream" -- silently falling
        back there would push to a remote/branch the caller never intended
        (review finding); it is raised as ``VcsCommandError`` instead, same
        as any other real failure. Both push forms name ``branch``
        EXPLICITLY as the source refspec (never a bare ``git push``, whose
        target depends on ``repo_root``'s own currently checked-out HEAD via
        ``push.default``) -- refs are shared across every worktree of one
        repo, so ``repo_root`` need not have ``branch`` checked out at all;
        any worktree of the same repo (typically ``repo_common_root``'s own
        result) resolves the same local ref. Deliberately never
        ``-u``/``--set-upstream``: that would silently rewrite the branch's
        own tracking config, which is the operator's choice to make, not
        this durability watcher's. Never ``--force``/``--force-with-lease``
        (the port's own contract) -- a rejected non-fast-forward push is a
        real failure, surfaced as ``VcsCommandError`` like any other. Uses
        ``_GIT_PUSH_TIMEOUT_S``, not ``_GIT_TIMEOUT_S``/
        ``_GIT_CHECKOUT_TIMEOUT_S`` -- a push is a network round-trip, not a
        local query or tree-populating checkout (review finding)."""
        upstream_check = _run(["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"])
        if upstream_check.returncode == 0:
            upstream = upstream_check.stdout.strip()
            remote, _, remote_branch = upstream.partition("/")
            if not remote or not remote_branch:
                # An upstream ref with no `/` (or an empty remote-side name)
                # is not a shape a real `@{upstream}` resolution produces --
                # refuse to guess rather than push to a malformed target.
                raise VcsCommandError(f"cannot parse upstream {upstream!r} for {branch} into <remote>/<remote_branch>")
            args = ["git", "-C", str(repo_root), "push", remote, f"{branch}:{remote_branch}"]
        elif "no upstream configured for branch" in upstream_check.stderr:
            args = ["git", "-C", str(repo_root), "push", "origin", branch]
        else:
            raise VcsCommandError(
                f"git rev-parse --abbrev-ref {branch}@{{upstream}} failed "
                f"(exit {upstream_check.returncode}), and it is not the "
                f"ordinary no-upstream case: {upstream_check.stderr.strip()}"
            )
        result = _run(args, timeout_s=_GIT_PUSH_TIMEOUT_S)
        if result.returncode != 0:
            raise VcsCommandError(f"git push failed for {branch}: {result.stderr.strip()}")

    def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str) -> tuple[str, ...]:
        """Story 2.3 (AD-27): the union of a committed diff and the
        working-tree's own dirty/untracked state, both run against
        ``worktree_path`` -- see the port's own docstring for why ``HEAD``
        must resolve from ``worktree_path``, never ``repo_root``.
        ``repo_root`` is accepted for interface parity with every other
        ``VcsPort`` method (and for a future caller that wants it echoed
        for provenance) but is not itself used to run either git
        invocation below.

        ``-c core.quotePath=false`` on BOTH invocations (review finding,
        Blind Hunter + Edge Case Hunter, independently): git's own default
        (``core.quotePath=true``) C-escapes/quotes any path containing a
        non-ASCII or otherwise "unusual" byte (e.g. ``"caf\\303\\251.txt"``
        for ``café.txt``) instead of emitting the literal UTF-8 path. Such a
        path would never match its own glob in ``compute_effective_surface``
        /``check_scope``, silently defeating scope/frozen-path checking for
        it -- pinned explicitly, mirroring ``is_branch_merged``'s/
        ``has_uncommitted_changes``'s own explicit-config-pin discipline
        rather than depending on the operator's config."""
        diff_result = _run(
            [
                "git",
                "-C",
                str(worktree_path),
                "-c",
                "core.quotePath=false",
                "diff",
                # -M: rename detection (review finding, Edge Case Hunter).
                # Without it, a committed rename shows up as BOTH the old
                # (now-nonexistent) path and the new path as separate
                # "changed" entries -- the old, no-longer-real path would
                # then be judged against the effective/frozen surfaces
                # alongside the new one. --name-status (not --name-only)
                # is used so a rename's status prefix ("R100") can be
                # detected and only its NEW path kept.
                "-M",
                "--name-status",
                f"{base}...HEAD",
            ]
        )
        if diff_result.returncode != 0:
            raise VcsCommandError(
                f"git diff --name-status -M {base}...HEAD failed in {worktree_path}: {diff_result.stderr.strip()}"
            )
        committed: set[str] = set()
        for line in diff_result.stdout.splitlines():
            if not line.strip():
                continue
            fields = line.split("\t")
            status = fields[0]
            if status.startswith("R") or status.startswith("C"):
                # "R100\told\tnew" (rename) / "C100\told\tnew" (copy) --
                # only the NEW path is currently live.
                if len(fields) < 3:
                    continue
                committed.add(fields[-1])
            elif len(fields) >= 2:
                committed.add(fields[1])

        # -c status.showUntrackedFiles=normal: same explicit-config-pin
        # discipline as has_uncommitted_changes above -- an operator's own
        # config setting it to "no" must not silently hide an untracked
        # change from this scope check.
        #
        # --untracked-files=all (review finding, Blind Hunter + Edge Case
        # Hunter, independently): git's own default
        # (--untracked-files=normal) collapses a wholly-new untracked
        # DIRECTORY into a single "dir/" porcelain line instead of listing
        # each file inside it -- that bare directory path never matches a
        # file-shaped glob (e.g. "recipes/newthing/*.yaml"), silently
        # breaking both the allowlist check and frozen-path protection for
        # every file inside a brand-new untracked directory.
        status_result = _run(
            [
                "git",
                "-C",
                str(worktree_path),
                "-c",
                "status.showUntrackedFiles=normal",
                "-c",
                "core.quotePath=false",
                "status",
                "--porcelain",
                "--untracked-files=all",
            ]
        )
        if status_result.returncode != 0:
            raise VcsCommandError(f"git status --porcelain failed in {worktree_path}: {status_result.stderr.strip()}")
        dirty: set[str] = set()
        for line in status_result.stdout.splitlines():
            if not line.strip():
                continue
            # Porcelain v1 short format: a fixed 2-char status code, one
            # space, then the path -- a rename/copy carries
            # "OLD -> NEW", of which only NEW is a currently-live path.
            entry = line[3:]
            if " -> " in entry:
                entry = entry.split(" -> ", 1)[1]
            dirty.add(entry)

        return tuple(sorted(committed | dirty))

    def worktree_unified_patch(self, worktree_path: Path, *, baseline_sha: str) -> str:
        """Story 22.6: ``git diff baseline..HEAD`` plus dirty overlay vs baseline."""
        diff_result = _run(
            [
                "git",
                "-C",
                str(worktree_path),
                "-c",
                "core.quotePath=false",
                "diff",
                f"{baseline_sha}..HEAD",
            ]
        )
        if diff_result.returncode != 0:
            raise VcsCommandError(
                f"git diff {baseline_sha}..HEAD failed in {worktree_path}: {diff_result.stderr.strip()}"
            )
        parts: list[str] = []
        if diff_result.stdout:
            parts.append(diff_result.stdout)
        dirty_result = _run(
            [
                "git",
                "-C",
                str(worktree_path),
                "-c",
                "core.quotePath=false",
                "diff",
                baseline_sha,
            ]
        )
        if dirty_result.returncode != 0:
            raise VcsCommandError(f"git diff {baseline_sha} failed in {worktree_path}: {dirty_result.stderr.strip()}")
        if dirty_result.stdout:
            parts.append(dirty_result.stdout)
        return "".join(parts)

    def commit_subjects(self, repo_root: Path, ref: str) -> tuple[str, ...]:
        """Story 4.1 (AD-33): ``git log <ref> --format=%s``, read-only.
        ``ref`` is never resolved/validated ahead of time -- an unresolvable
        ref (no ``origin`` remote for ``"origin/main"``, a corrupted repo
        missing ``"main"``) surfaces as an ordinary ``VcsCommandError``,
        which the caller (``cli/deploy.py``) treats differently per route:
        best-effort for the push route, a hard failure for the merge
        route -- a distinction this method itself has no opinion about."""
        result = _run(["git", "-C", str(repo_root), "log", ref, "--format=%s"])
        if result.returncode != 0:
            raise VcsCommandError(f"git log {ref} --format=%s failed: {result.stderr.strip()}")
        return tuple(result.stdout.splitlines())

    def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: str) -> str:
        """Story 4.1 (AD-29): stages exactly ``paths`` (one ``git add --
        <path>`` per entry, never ``git add -A``) then commits ONLY those
        paths (``git commit -m <message> -- <path> ...``, never a bare
        ``git commit`` that would sweep in a pre-existing index), returning
        ``git rev-parse HEAD``'s output. Refuses (``VcsCommandError``,
        before any git invocation) an empty ``paths`` -- a caller with
        nothing to promote must never reach this method; without the guard,
        ``git commit -m <message> --`` with no pathspec after ``--`` would
        either fail ambiguously or, worse, fall back to committing whatever
        happened to already be staged, exactly the "commits a pre-existing
        index" failure AD-29 forbids."""
        if not paths:
            raise VcsCommandError("commit_paths requires at least one path, got none")
        for path in paths:
            add_result = _run(["git", "-C", str(repo_root), "add", "--", str(path)])
            if add_result.returncode != 0:
                raise VcsCommandError(f"git add -- {path} failed: {add_result.stderr.strip()}")
        commit_args = [
            "git",
            "-C",
            str(repo_root),
            "commit",
            "-m",
            message,
            "--",
            *(str(path) for path in paths),
        ]
        commit_result = _run(commit_args)
        if commit_result.returncode != 0:
            raise VcsCommandError(
                f"git commit -- {' '.join(str(p) for p in paths)} failed: {commit_result.stderr.strip()}"
            )
        rev_result = _run(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
        if rev_result.returncode != 0:
            raise VcsCommandError(f"git rev-parse HEAD failed after committing {paths}: {rev_result.stderr.strip()}")
        return rev_result.stdout.strip()

    def path_has_uncommitted_changes(self, repo_root: Path, path: Path) -> bool:
        """Story 4.1's own review-fix pass: ``has_uncommitted_changes``'s
        per-path counterpart -- ``git status --porcelain -- <path>``, same
        explicit ``status.showUntrackedFiles=normal`` config pin (an
        operator's own config setting it to ``no`` must not silently hide
        an untracked file from this check either). Any output line at all
        means ``path`` carries staged, unstaged, or untracked state; no
        output means ``path`` is tracked and matches ``HEAD`` exactly (or
        does not exist -- git reports nothing for either)."""
        result = _run(
            [
                "git",
                "-C",
                str(repo_root),
                "-c",
                "status.showUntrackedFiles=normal",
                "status",
                "--porcelain",
                "--",
                str(path),
            ]
        )
        if result.returncode != 0:
            raise VcsCommandError(f"git status --porcelain -- {path} failed: {result.stderr.strip()}")
        return bool(result.stdout.strip())

    def merge_base(self, repo_root: Path, a: str, b: str) -> str:
        """Story 4.3: ``git merge-base a b``, read-only. Shares its shape
        with ``is_branch_merged``'s own internal merge-base call above but
        is exposed as a standalone primitive here -- ``cli/deploy.py``'s
        ``land-story`` action needs the VALUE itself (its ``--since``
        default), not just a boolean derived from it."""
        result = _run(["git", "-C", str(repo_root), "merge-base", a, b])
        if result.returncode != 0:
            raise VcsCommandError(f"cannot find a merge base for {a} and {b}: {result.stderr.strip()}")
        return result.stdout.strip()

    def resolve_ref(self, repo_root: Path, ref: str) -> str:
        """Story 4.3 (code review, 2026-08-06, P4): ``git rev-parse --verify
        refs/heads/<ref>``, read-only -- resolves a local branch name to its
        current tip commit sha. ``land-story`` uses this to pin a branch's
        tip immediately after the gate evaluates it and to re-verify,
        immediately before merging, that the branch has not moved in the
        meantime (closing the window where a commit landing on the branch
        mid-gate-run would otherwise be merged as if the now-stale gate
        result still applied to it). Raises ``VcsCommandError`` if ``ref``
        does not resolve to a local branch."""
        result = _run(["git", "-C", str(repo_root), "rev-parse", "--verify", f"refs/heads/{ref}"])
        if result.returncode != 0:
            raise VcsCommandError(f"cannot resolve refs/heads/{ref} to a commit: {result.stderr.strip()}")
        return result.stdout.strip()

    def merge_branch(self, repo_root: Path, branch: str, *, into: str, subject: str) -> str:
        """Story 4.3 (FR-27, AD-24). Redesigned by code review (2026-08-06,
        P1, Blind Hunter + Edge Case Hunter, both independently): the
        ORIGINAL implementation ran ``git checkout into`` directly against
        ``repo_root`` -- this project's ONE shared, currently-active working
        directory, not an isolated worktree -- with no dirty-tree
        precondition and no restoration of whatever was checked out before.
        A ``land-story`` invocation could therefore silently switch the
        operator's own currently-checked-out branch, lose uncommitted
        context, or race with concurrent work in that same checkout.

        This method now NEVER checks out or otherwise mutates ``repo_root``'s
        own active working tree. It instead:

        1. Resolves ``into``'s CURRENT tip sha (``old_sha``) via
           ``resolve_ref``.
        2. ``git worktree add --detach <tmp> <old_sha>`` -- an isolated
           checkout at a throwaway path, pinned to the exact sha rather than
           the branch name (a bare branch name would collide with
           ``repo_root``'s own already-checked-out ``into``, since git
           refuses to check out the same branch into two worktrees at once;
           a detached sha checkout has no such restriction).
        3. ``git -C <tmp> merge --no-ff -m subject branch`` -- read-only
           against ``branch`` itself (never checked out, never modified);
           the only write is the merge commit created INSIDE ``<tmp>``.
        4. ``git -C repo_root update-ref refs/heads/<into> <new_sha>
           <old_sha>`` -- the THREE-ARG compare-and-swap form: atomically
           verifies ``into`` has not moved since step 1 before advancing it.
           This closes the P4 TOCTOU gap a blind two-arg ``update-ref``
           would leave open (``into`` moving concurrently between this
           method's own read and write of it). A CAS failure raises
           ``VcsCommandError`` naming the race, never silently overwriting
           a concurrent change.
        5. Removes ``<tmp>`` in a ``finally`` block -- on EVERY exit path,
           including a merge conflict or a failed CAS -- so no worktree
           registration or directory is ever leaked. The removal itself is
           best-effort and NEVER raises (a cleanup failure must not mask the
           real outcome above it): ``git worktree remove --force`` first,
           falling back to a raw ``shutil.rmtree`` plus ``git worktree
           prune`` if that fails.

        Uses ``_GIT_CHECKOUT_TIMEOUT_S`` for the worktree add and the merge
        itself (review precedent: both are tree-proportional work on this
        repo's own large tree, not a bounded metadata query). A merge
        conflict is a hard stop (``VcsCommandError``), never auto-aborted or
        auto-resolved -- the CONFLICT happens inside the throwaway ``<tmp>``
        worktree, which is then removed; ``repo_root``'s own working tree is
        never touched, so there are no conflict markers left behind for the
        operator to find there (they would have existed in ``<tmp>``, which
        no longer exists by the time this raises).

        Returns the new merge commit's sha. Raises ``VcsCommandError`` on
        any conflict, CAS failure, or other git failure -- a caller treats
        that as a hard stop: never retried, never auto-resolved."""
        old_sha = self.resolve_ref(repo_root, into)

        tmp_path = Path(tempfile.mkdtemp(prefix="marshal-land-"))
        # `git worktree add` refuses to reuse a directory it did not create
        # itself -- remove the empty dir `mkdtemp` already made so `add` can
        # create it fresh.
        tmp_path.rmdir()
        try:
            add_result = _run(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "worktree",
                    "add",
                    "--detach",
                    str(tmp_path),
                    old_sha,
                ],
                timeout_s=_GIT_CHECKOUT_TIMEOUT_S,
            )
            if add_result.returncode != 0:
                raise VcsCommandError(
                    f"git worktree add --detach {tmp_path} {old_sha} failed: {add_result.stderr.strip()}"
                )

            merge_result = _run(
                ["git", "-C", str(tmp_path), "merge", "--no-ff", "-m", subject, branch],
                timeout_s=_GIT_CHECKOUT_TIMEOUT_S,
            )
            if merge_result.returncode != 0:
                raise VcsCommandError(
                    f"git merge --no-ff -m {subject!r} {branch} into {into} "
                    f"(isolated detached worktree) failed: {merge_result.stderr.strip()}"
                )

            new_sha_result = _run(["git", "-C", str(tmp_path), "rev-parse", "HEAD"])
            if new_sha_result.returncode != 0:
                # The merge commit exists in <tmp> at this point, but
                # nothing has landed on `into` yet -- the CAS below is what
                # makes it durable -- so this is correctly a hard stop, not
                # a "succeeded but unlogged" landing (unlike a failure
                # AFTER a successful CAS, which this method's own `finally`
                # cleanup is deliberately built to never produce).
                raise VcsCommandError(
                    f"git rev-parse HEAD failed in the detached merge "
                    f"worktree after merging {branch} into {into}: "
                    f"{new_sha_result.stderr.strip()}"
                )
            new_sha = new_sha_result.stdout.strip()

            cas_result = _run(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "update-ref",
                    f"refs/heads/{into}",
                    new_sha,
                    old_sha,
                ]
            )
            if cas_result.returncode != 0:
                raise VcsCommandError(
                    f"refs/heads/{into} moved (or could not be updated) while "
                    f"landing {branch} -- expected it at {old_sha}, refusing "
                    f"to overwrite a concurrent change: {cas_result.stderr.strip()}"
                )
            return new_sha
        finally:
            # Best-effort, and this ENTIRE block is guarded, not just the
            # non-zero-returncode branch below: `_run` itself can raise
            # `VcsCommandError` (a launch failure, a timeout) rather than
            # merely returning a non-zero exit -- letting that escape this
            # `finally` would mask an already-successful merge+CAS above
            # (P5: a cosmetic cleanup failure must never be reported as an
            # unremarked failure of a landing that in fact already happened).
            try:
                remove_result = _run(
                    ["git", "-C", str(repo_root), "worktree", "remove", "--force", str(tmp_path)],
                    timeout_s=_GIT_CHECKOUT_TIMEOUT_S,
                )
                removed = remove_result.returncode == 0
            except VcsCommandError:
                removed = False
            if not removed:
                # Fallback (e.g. `add` above never completed, so there was
                # nothing registered to `remove`): a raw filesystem removal
                # plus `worktree prune`, both swallowing any failure of
                # their own -- nothing from this fallback path may raise
                # either.
                shutil.rmtree(tmp_path, ignore_errors=True)
                try:
                    _run(["git", "-C", str(repo_root), "worktree", "prune"])
                except VcsCommandError:
                    pass

    def worktree_head_sha(self, worktree_path: Path) -> str:
        """Story 4.4 (code review, 2026-08-06, P5): ``git rev-parse HEAD``,
        read-only, run inside ``worktree_path`` -- the commit that specific
        worktree is actually checked out at right now (as opposed to
        ``resolve_ref``'s ``refs/heads/<branch>`` read, a repo-wide ref, not
        a per-worktree fact -- see ``changed_files``'s own docstring for why
        the two can legitimately differ, e.g. a detached HEAD)."""
        result = _run(["git", "-C", str(worktree_path), "rev-parse", "HEAD"])
        if result.returncode != 0:
            raise VcsCommandError(f"git rev-parse HEAD failed in {worktree_path}: {result.stderr.strip()}")
        return result.stdout.strip()

    def fetch(self, repo_root: Path, remote: str, ref: str) -> None:
        """Story 4.12 (FR-173): ``git fetch <remote> <ref>`` against
        ``repo_root`` -- updates ONLY ``refs/remotes/<remote>/<ref>``, never
        any local branch. Uses ``_GIT_FETCH_TIMEOUT_S``, not
        ``_GIT_TIMEOUT_S``/``_GIT_CHECKOUT_TIMEOUT_S`` -- a network
        round-trip, mirroring ``push``'s own identical reasoning."""
        result = _run(
            ["git", "-C", str(repo_root), "fetch", remote, ref],
            timeout_s=_GIT_FETCH_TIMEOUT_S,
        )
        if result.returncode != 0:
            raise VcsCommandError(f"git fetch {remote} {ref} failed: {result.stderr.strip()}")

    def fast_forward(self, worktree_path: Path, ref: str) -> str:
        """Story 4.12 (FR-173): ``git merge --ff-only <ref>`` run inside
        ``worktree_path`` -- advances ``worktree_path``'s own checked-out
        branch to ``ref`` ONLY when it is already an ancestor of ``ref``.
        Never ``--no-ff``, never a rebase, never ``reset --hard`` -- git
        itself refuses cleanly (a real, non-zero exit) the moment the merge
        would not be a fast-forward, which this method surfaces as an
        ordinary ``VcsCommandError`` naming git's own reason (a diverged
        branch, a dirty working tree, a held lock). Uses
        ``_GIT_CHECKOUT_TIMEOUT_S`` -- tree-mutating, the same tier
        ``merge_branch``'s own merge step uses. Returns the new HEAD sha
        (``git rev-parse HEAD`` immediately after)."""
        result = _run(
            ["git", "-C", str(worktree_path), "merge", "--ff-only", ref],
            timeout_s=_GIT_CHECKOUT_TIMEOUT_S,
        )
        if result.returncode != 0:
            raise VcsCommandError(f"git merge --ff-only {ref} failed in {worktree_path}: {result.stderr.strip()}")
        rev_result = _run(["git", "-C", str(worktree_path), "rev-parse", "HEAD"])
        if rev_result.returncode != 0:
            raise VcsCommandError(
                f"git rev-parse HEAD failed in {worktree_path} after "
                f"fast-forwarding to {ref}: {rev_result.stderr.strip()}"
            )
        return rev_result.stdout.strip()

    def commits_behind(self, worktree_path: Path, tip_ref: str) -> int:
        """Story 15.1 (FR-133): ``git rev-list --count HEAD..<tip_ref>``
        inside ``worktree_path`` -- the home's behind-count vs ``tip_ref``
        (typically ``origin/main`` after ``fetch``). Read-only."""
        result = _run(
            ["git", "-C", str(worktree_path), "rev-list", "--count", f"HEAD..{tip_ref}"],
        )
        if result.returncode != 0:
            raise VcsCommandError(
                f"git rev-list --count HEAD..{tip_ref} failed in {worktree_path}: {result.stderr.strip()}"
            )
        raw = result.stdout.strip()
        try:
            return int(raw)
        except ValueError as exc:
            raise VcsCommandError(f"git rev-list --count returned non-integer {raw!r} in {worktree_path}") from exc

    def merge_tree_conflict_paths(self, repo_root: Path, base: str, branch: str) -> tuple[str, ...]:
        """Story 28.20: parse ``git merge-tree`` for conflict paths."""
        merge_base = self.merge_base(repo_root, base, branch)
        result = _run(
            [
                "git",
                "-C",
                str(repo_root),
                "merge-tree",
                merge_base,
                base,
                branch,
            ],
            timeout_s=_GIT_CHECKOUT_TIMEOUT_S,
        )
        if result.returncode != 0 and "CONFLICT" not in result.stdout:
            raise VcsCommandError(
                f"git merge-tree {merge_base} {base} {branch} failed: {result.stderr.strip() or result.stdout.strip()}"
            )
        paths: set[str] = set()
        marker = "Merge conflict in "
        for line in result.stdout.splitlines():
            if marker in line:
                paths.add(line.split(marker, 1)[1].strip())
        return tuple(sorted(paths))

    def file_text_at_ref(self, repo_root: Path, ref: str, path: str) -> str | None:
        """Story 28.20: ``git show ref:path`` read-only."""
        result = _run(["git", "-C", str(repo_root), "show", f"{ref}:{path}"])
        if result.returncode != 0:
            if "exists on disk, but not in" in result.stderr or "does not exist" in result.stderr:
                return None
            raise VcsCommandError(f"git show {ref}:{path} failed: {result.stderr.strip()}")
        return result.stdout

    def merge_tree_write(self, repo_root: Path, base: str, branch: str) -> str | None:
        """Story 51.1: mirrors ``merge_tree_conflict_paths``'s own
        ``_run(... "merge-tree" ...)`` shape and ``"CONFLICT" in
        result.stdout`` disambiguation, but drives the modern two-arg
        ``--write-tree`` form (git computes the merge base itself -- no
        separate ``merge_base`` call needed) and returns the resulting
        tree's oid instead of parsing conflict paths. On a real conflict
        git still exits with the toplevel tree's oid as its first output
        line (a tree carrying literal conflict markers) followed by
        ``"CONFLICT"`` sections -- that oid is not a clean merge result, so
        it is discarded in favor of ``None`` rather than returned."""
        result = _run(
            ["git", "-C", str(repo_root), "merge-tree", "--write-tree", base, branch],
            timeout_s=_GIT_CHECKOUT_TIMEOUT_S,
        )
        if result.returncode != 0 and "CONFLICT" not in result.stdout:
            raise VcsCommandError(
                f"git merge-tree --write-tree {base} {branch} failed: {result.stderr.strip() or result.stdout.strip()}"
            )
        if "CONFLICT" in result.stdout:
            return None
        tree_oid = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
        if not tree_oid:
            raise VcsCommandError(f"git merge-tree --write-tree {base} {branch} produced no tree oid")
        return tree_oid

    def add_worktree_for_tree(self, repo_root: Path, home: Path, tree_oid: str, *, parent: str) -> None:
        """Story 51.1: wraps ``tree_oid`` in a throwaway commit -- pinned
        ``user.name``/``user.email``/``commit.gpgsign=false`` via ``-c``
        flags, mirroring ``is_branch_merged``'s own ``commit-tree``
        discipline exactly -- with ``parent`` as its sole parent, then
        checks it out DETACHED at ``home`` (``git worktree add --detach``,
        mirroring ``add_worktree``'s own invocation style). The synthetic
        commit is never referenced by any branch or tag; it exists solely
        so ``home`` has a commit-ish to check out."""
        commit_result = _run(
            [
                "git",
                "-C",
                str(repo_root),
                "-c",
                "user.name=marshal-land-verify",
                "-c",
                "user.email=marshal-land-verify@localhost",
                "-c",
                "commit.gpgsign=false",
                "commit-tree",
                tree_oid,
                "-p",
                parent,
                "-m",
                "marshal merge-tree preview (not a real commit)",
            ]
        )
        if commit_result.returncode != 0:
            raise VcsCommandError(
                f"cannot build the merge-tree preview commit for tree "
                f"{tree_oid} onto {parent}: {commit_result.stderr.strip()}"
            )
        synthetic_sha = commit_result.stdout.strip()

        add_result = _run(
            ["git", "-C", str(repo_root), "worktree", "add", "--detach", str(home), synthetic_sha],
            timeout_s=_GIT_CHECKOUT_TIMEOUT_S,
        )
        if add_result.returncode != 0:
            raise VcsCommandError(
                f"git worktree add --detach {home} {synthetic_sha} failed: {add_result.stderr.strip()}"
            )

    def commit_paths_onto_remote_tip(
        self,
        repo_root: Path,
        *,
        remote: str,
        ref: str,
        writes: tuple[tuple[str, str], ...],
        message: str,
    ) -> str:
        """CAP-5: publish path writes onto ``origin/<ref>`` from a throwaway
        detached worktree. Never checks out or commits in ``repo_root``."""
        if not writes:
            raise VcsCommandError("commit_paths_onto_remote_tip requires at least one write, got none")
        self.fetch(repo_root, remote, ref)
        tip_result = _run(["git", "-C", str(repo_root), "rev-parse", "--verify", f"{remote}/{ref}"])
        if tip_result.returncode != 0:
            raise VcsCommandError(f"cannot resolve {remote}/{ref} after fetch: {tip_result.stderr.strip()}")
        old_sha = tip_result.stdout.strip()

        tmp_path = Path(tempfile.mkdtemp(prefix="marshal-promote-"))
        tmp_path.rmdir()
        try:
            add_result = _run(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "worktree",
                    "add",
                    "--detach",
                    str(tmp_path),
                    old_sha,
                ],
                timeout_s=_GIT_CHECKOUT_TIMEOUT_S,
            )
            if add_result.returncode != 0:
                raise VcsCommandError(
                    f"git worktree add --detach {tmp_path} {old_sha} failed: {add_result.stderr.strip()}"
                )
            paths: list[Path] = []
            for rel, content in writes:
                dest = tmp_path / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")
                paths.append(dest)
            new_sha = self.commit_paths(tmp_path, tuple(paths), message)
            ancestor = _run(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "merge-base",
                    "--is-ancestor",
                    old_sha,
                    new_sha,
                ]
            )
            if ancestor.returncode != 0:
                raise VcsCommandError(
                    f"{new_sha} is not a descendant of {remote}/{ref} ({old_sha}); refusing to push a non-fast-forward"
                )
            push_result = _run(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "push",
                    remote,
                    f"{new_sha}:refs/heads/{ref}",
                ],
                timeout_s=_GIT_FETCH_TIMEOUT_S,
            )
            if push_result.returncode != 0:
                raise VcsCommandError(
                    f"git push {remote} {new_sha}:refs/heads/{ref} failed: {push_result.stderr.strip()}"
                )
            return new_sha
        finally:
            try:
                remove_result = _run(
                    [
                        "git",
                        "-C",
                        str(repo_root),
                        "worktree",
                        "remove",
                        "--force",
                        str(tmp_path),
                    ],
                    timeout_s=_GIT_CHECKOUT_TIMEOUT_S,
                )
                removed = remove_result.returncode == 0
            except VcsCommandError:
                removed = False
            if not removed:
                shutil.rmtree(tmp_path, ignore_errors=True)
                try:
                    _run(["git", "-C", str(repo_root), "worktree", "prune"])
                except VcsCommandError:
                    pass


def stage_index_paths(
    repo_root: Path,
    paths: Sequence[str],
    update: bool = False,
) -> int:
    """Story 21.4 CAP-4: stage paths into the index without committing.

    ``update=False`` → ``git add -- <paths>`` (new/modified).
    ``update=True`` → ``git add -u -- <paths>`` (tracked deletions/mods).
    Returns the number of path arguments accepted (0 on empty input or
    non-zero git exit). Never runs ``git commit`` / ``git push``.
    """
    if not paths:
        return 0
    cmd = ["git", "-C", str(repo_root), "add"]
    if update:
        cmd.append("-u")
    cmd.append("--")
    cmd.extend(str(p) for p in paths)
    result = _run(cmd)
    if result.returncode != 0:
        return 0
    return len(tuple(paths))
