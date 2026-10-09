"""Dispatch run work preservation (Story 22.6, FR-193 CAP-6; Story 87.5, FR-234).

Pure path helpers for the ``changes.patch`` analog under a dispatch run dir.
Git capture lives on ``VcsPort.worktree_unified_patch`` (``adapters/vcs_git``).
When ``pyforge.marshal.preserve_refs`` is on, the supervisor also writes a
``preserve/…/dispatch-<sha8>`` tag through ``pyforge.core.preserve_refs``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pyforge.core.flags import read_boolean
from pyforge.core.preserve_refs import (
    PreserveGitError,
    PreserveRefError,
    PreserveTrailers,
    push_preserve_ref,
    render_preserve_ref,
    short_ref_name,
    snapshot_worktree_commit,
    tag_preserve,
)

from ..ports.vcs import VcsPort
from .dispatch_completion import DispatchSessionVerdict
from .identity import MalformedStoryKeyError, normalize, render_feed_key

PRESERVE_REFS_FLAG_KEY = "pyforge.marshal.preserve_refs"

_TERMINAL_PRESERVE_VERDICTS = frozenset(
    {
        DispatchSessionVerdict.FAILED,
        DispatchSessionVerdict.STOPPED_EXTERNALLY,
        DispatchSessionVerdict.BLOCKED,
    }
)


def _safe_segment(story_key: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", story_key).strip("-")
    return cleaned or "story"


def failed_patch_path(run_dir: Path, story_key: str) -> Path:
    """``run_dir/failed/<story>/changes.patch`` — dispatch's recovery ref."""
    return run_dir / "failed" / _safe_segment(story_key) / "changes.patch"


@dataclass(frozen=True)
class DispatchPreserveResult:
    """Outcome of parking recoverable dispatch work."""

    patch_path: Path | None
    patch_relative: str | None
    had_commits: bool
    had_uncommitted: bool


@dataclass(frozen=True)
class DispatchPreserveTagOutcome:
    """Local tag + optional push for a dispatch preserve (Story 87.5)."""

    refname: str
    preserve_tag: str
    pushed: bool
    noop: bool


def relative_preserve_ref(run_dir: Path, patch_path: Path) -> str:
    """Repo-neutral ref string for journal / status (posix relative to run_dir)."""
    return patch_path.relative_to(run_dir).as_posix()


def preserve_refs_flag_on(*, flags_path: Path | None = None) -> bool:
    return read_boolean(PRESERVE_REFS_FLAG_KEY, default=False, flags_path=flags_path)


def should_journal_dispatch_preserve(
    *,
    flag_on: bool,
    verdict: DispatchSessionVerdict,
    has_progress: bool,
) -> bool:
    """Whether this run should write a patch (and maybe a tag)."""
    if not has_progress:
        return False
    if flag_on:
        return verdict in _TERMINAL_PRESERVE_VERDICTS
    return verdict is DispatchSessionVerdict.FAILED


def _preserve_story_key_for_tag(story_key: str) -> str:
    try:
        return render_feed_key(normalize(story_key))
    except MalformedStoryKeyError:
        return story_key


def tag_dispatch_worktree_preserve(
    *,
    vcs: VcsPort,
    repo_root: Path,
    worktree: Path,
    project_slug: str,
    story_key: str,
    run_id: str,
    journal_path: str,
    reason: str,
    push: bool = True,
) -> DispatchPreserveTagOutcome | None:
    """Snapshot, tag locally, push one refspec through the content gate."""
    try:
        commit = snapshot_worktree_commit(worktree)
    except PreserveGitError:
        return None
    if commit is None:
        try:
            commit = vcs.worktree_head_sha(worktree)
        except Exception:
            return None
    feed_story = _preserve_story_key_for_tag(story_key)
    refname = render_preserve_ref(
        commit_sha=commit,
        producer="dispatch",
        project_slug=project_slug,
        story_key=feed_story,
    )
    trailers = PreserveTrailers(
        producer="dispatch",
        provenance="machine",
        reason=reason,
        source=str(worktree),
        run=run_id,
        journal=journal_path,
        commit=commit,
    )
    try:
        tagged = tag_preserve(worktree, refname=refname, commit=commit, trailers=trailers)
    except (PreserveRefError, PreserveGitError):
        return None
    preserve_tag = short_ref_name(tagged.refname)
    pushed = False
    if push:
        try:
            push_result = push_preserve_ref(repo_root, tagged.refname)
            pushed = push_result.pushed
        except PreserveGitError:
            pushed = False
    return DispatchPreserveTagOutcome(
        refname=tagged.refname,
        preserve_tag=preserve_tag,
        pushed=pushed,
        noop=tagged.noop,
    )


def dispatch_preserve_outcome_payload(
    *,
    preserve_ref: str = "",
    preserve_tag: str | None = None,
    preserve_pushed: bool | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"ok": True}
    if preserve_ref:
        payload["preserve_ref"] = preserve_ref
    if preserve_tag is not None:
        payload["preserve_tag"] = preserve_tag
    if preserve_pushed is not None:
        payload["preserve_pushed"] = preserve_pushed
    return payload
