"""Story 34.2: local-only worktree auto-checkpoints for dispatch/spin sessions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .commit_vcs import CommittingVcs
from .dispatch_cfe_commit import non_retro_commit_paths
from .egress import to_redacted_text

_AUTO_CHECKPOINT_MARKER = "(auto-checkpoint)"


def auto_checkpoint_message(story_key: str) -> str:
    """Return the canonical auto-checkpoint commit subject for ``story_key``."""
    return f"wip: {story_key} {_AUTO_CHECKPOINT_MARKER}"


def is_auto_checkpoint_subject(subject: str) -> bool:
    return _AUTO_CHECKPOINT_MARKER in subject


@dataclass(frozen=True)
class WorktreeCheckpointResult:
    committed: bool
    head_sha: str | None = None
    skipped_reason: str | None = None


def should_checkpoint_on_idle(
    *,
    idle_elapsed_s: float,
    threshold_s: float,
    has_uncommitted_changes: bool,
) -> bool:
    """True when the worktree is dirty and idle time meets the threshold."""
    if not has_uncommitted_changes:
        return False
    if threshold_s <= 0:
        return False
    return idle_elapsed_s >= threshold_s


def commit_worktree_checkpoint(
    vcs: CommittingVcs,
    *,
    repo_root: Path,
    worktree: Path,
    story_key: str,
    base: str = "HEAD",
) -> WorktreeCheckpointResult:
    """Commit all uncommitted paths in ``worktree`` as a local-only checkpoint."""
    try:
        if not vcs.has_uncommitted_changes(worktree):
            return WorktreeCheckpointResult(committed=False, skipped_reason="clean worktree")
        changed = vcs.changed_files(repo_root, worktree, base=base)
        if not changed:
            return WorktreeCheckpointResult(committed=False, skipped_reason="clean worktree")
        to_commit = non_retro_commit_paths(vcs, worktree=worktree, repo_root=repo_root)
        if not to_commit:
            return WorktreeCheckpointResult(committed=False, skipped_reason="only CFE surface dirty")
        head_sha = vcs.commit_paths(
            worktree,
            to_commit,
            to_redacted_text(auto_checkpoint_message(story_key)),
        )
    except Exception as exc:
        return WorktreeCheckpointResult(committed=False, skipped_reason=str(exc))
    return WorktreeCheckpointResult(committed=True, head_sha=head_sha)
