"""``CommitPort`` -- the git commit-writing seam, an egress port (Story 82.9,
DW-FU-2-6-4, architecture spine AD-34). A Protocol definition only (Structural
Seed: ``ports/`` declares shapes, never implementations); implemented solely
by ``adapters/vcs_git.py::GitVcs`` (AD-4), which serves both this port and
``VcsPort`` -- as ``LocalFs`` serves ``FsPort`` and ``RecordPort``.

AD-34 names "VCS commit and PR text" as egress: a commit message is free text
written to a durable, shareable sink (a repository's history, then a remote).
``VcsPort`` once carried that text as a bare ``str`` on three methods, and its
non-egress classification meant the AD-34 completeness meta-test
(``tests/meta/test_ad34_egress_registry_completeness.py``) never looked at
them -- an unredacted credential could reach a commit message with no test
failing. The three commit-writing methods moved here verbatim, and the port is
classified ``True`` in ``core.egress.EGRESS_PORTS``, so that guard now covers
commit text unchanged: no method of this class accepts a bare ``str``.

- ``message`` (and ``preflight_skip_reason``, which the adapter folds into a
  journaled opt-out line) is ``Redacted`` -- obtained only through
  ``core.egress.to_redacted_text``, the plain-text sibling of the one
  redacting serializer. No call site redacts on its own.
- ``ref``/``remote`` are ``VcsRef`` -- the typed-reference precedent
  (``ports.forge.ForgeRef``): a revision or remote name, never secret and never
  session-derived free text, wrapped only so the guard (which is deliberately
  undiscriminating about a parameter's role, only its type) does not have to
  be defeated.
- ``writes`` (repo-relative path, full file text) and ``resolutions`` (path ->
  resolved text) stay containers: file bodies are repository content, not
  commit text, and the guard recognises no ``str`` buried in a container.

``VcsPort`` keeps every read and ref operation and stays non-egress; the
commit text is the reason this second port exists.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ..core.egress import Redacted


@dataclass(frozen=True)
class VcsRef:
    """One non-secret VCS identifier -- a revision or branch name, or a remote
    name (Story 82.9). Wrapped in a value type rather than passed as a bare
    ``str`` purely to satisfy AD-34's egress-registry-completeness meta-test
    (see this module's docstring), exactly as ``ports.forge.ForgeRef`` does for
    the forge port. None of these values is secret-shaped or session-derived
    free text, so no redaction ever applies to a ``VcsRef``; only the commit
    ``message`` goes through ``Redacted``."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError(f"value must be a non-empty str, got {self.value!r}")


class CommitPort(Protocol):
    def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: Redacted) -> str:
        """Story 4.1 (AD-29): stages exactly ``paths`` -- one ``git add --
        <path>`` per entry, never ``git add -A`` -- then commits ONLY those
        paths (``git commit -m <message> -- <path> <path> ...``, never a
        bare ``git commit`` that would sweep in a pre-existing index) and
        returns the new commit's sha (``git rev-parse HEAD`` immediately
        after). ``repo_root`` need not have any of ``paths`` staged already
        -- this method does the staging itself. ``message`` is ``Redacted``
        (AD-34); a bare ``str`` raises ``TypeError`` before any git
        invocation. Raises ``VcsCommandError`` if ``paths`` is empty (a
        caller with nothing to promote must never reach this method) or on
        any git failure (an unwritable index, a path outside the working
        tree, nothing to commit)."""
        ...

    def merge_ref_resolving(
        self,
        worktree_path: Path,
        ref: VcsRef,
        *,
        resolutions: Mapping[str, str],
        message: Redacted,
    ) -> str:
        """Story 59.1 (CAP-269): merge ``ref`` into ``worktree_path``'s checked-out branch as a
        real two-parent merge commit. Every conflicted path must be a key of ``resolutions``
        (repo-relative POSIX path -> the full resolved text), which is written and staged;
        any other conflicted path aborts the merge -- the worktree back at its previous HEAD,
        nothing committed -- and raises ``VcsCommandError``, as does any git failure. A merge
        already in progress in the worktree is refused, never adopted or aborted. Returns the
        merge commit's sha (HEAD itself when ``ref`` is already merged). Never pushes.
        ``message`` is ``Redacted`` and ``ref`` a ``VcsRef`` (Story 82.9); a bare ``str`` for
        either raises ``TypeError`` before any git invocation."""
        ...

    def commit_paths_onto_remote_tip(
        self,
        repo_root: Path,
        *,
        remote: VcsRef,
        ref: VcsRef,
        writes: tuple[tuple[str, str], ...],
        message: Redacted,
        preflight_skip_reason: Redacted | None = None,
    ) -> str:
        """CAP-5 / land-promote-isolation: fetch ``remote``/``ref``, commit
        ``writes`` (repo-relative POSIX path, full file text) onto that
        remote tip inside a throwaway detached worktree, and
        fast-forward-push the new commit to ``refs/heads/<ref>``.

        NEVER mutates ``repo_root``'s working tree, index, or local
        ``refs/heads/<ref>`` -- git refuses two worktrees on one branch,
        and the operator checkout is typically already on ``main``.
        ``repo_root`` is used only as ``git -C`` for fetch / worktree add /
        push (shared object store). Never ``--force``.

        Story 68.1 (spec-pyforge-marshal CAP-277): ``preflight_skip_reason``
        (keyword-only) is the proof-carrying opt-out from the repository's
        ``pre-push`` preflight (``spec-pyforge-steward:CAP-154``), for a
        landing's bookkeeping publish, which the preflight would otherwise
        run in full and outlast the push's git timeout. A caller passing one
        NAMES THE STORY in it. The adapter then (1) refuses, before any
        write or fetch, a written path that is not a normalized
        ``_bmad-output/projects/<slug>/planning-artifacts/...`` path, and
        (2) refuses, after building the commit and before any push, a commit
        that names any path outside the written set. Only a commit that
        passes both is pushed with the hook's journaled opt-out
        (``PYFORGE_PREFLIGHT_SKIP=1`` and a ``PYFORGE_PREFLIGHT_SKIP_REASON``
        naming the new sha, the paths and the caller's reason), set for that
        one ``git push`` only through the POSIX ``env`` utility, exactly as
        ``VcsPort.push`` does for Story 57.1. Where ``env`` does not exist the
        push runs the preflight. With ``None`` (the default) the push is
        unchanged and the hook runs as it always did.

        Story 82.9: ``message`` and ``preflight_skip_reason`` are ``Redacted``
        (the reason is written into the journaled opt-out line, a durable
        record), ``remote``/``ref`` are ``VcsRef``; a bare ``str`` for any of
        them raises ``TypeError`` before any git invocation.

        Returns the new commit sha. Raises ``VcsCommandError`` if
        ``writes`` is empty, a reason is given for a write outside
        ``planning-artifacts/`` or for a commit naming an unwritten path,
        fetch fails, the push is not a fast-forward, or on any other git
        failure."""
        ...
