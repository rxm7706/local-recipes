"""Dispatch session completion judgment (Story 22.2, FR-193 CAP-2, AD-33).

Pure functions only: git facts (commits on the story branch, merge refs)
plus process facts judge whether a dispatched session is live, completed,
or failed. Harness notifications and self-reports are never verdict inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from ..ports.vcs import VcsPort
from .dispatch_harness_done import FollowupReview


class DispatchSessionVerdict(StrEnum):
    """Terminal and non-terminal completion states for a dispatch session."""

    LIVE = "live"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED_EXTERNALLY = "stopped_externally"
    #: Story 51.11 (CAP-258): the session halted on its own tracked spec's
    #: ``status: blocked`` (with an Auto Run Result matching this run's own
    #: baseline) but exited before committing that halt -- distinct from
    #: ``STOPPED_EXTERNALLY``, which never inspects spec content.
    BLOCKED = "blocked"


@dataclass(frozen=True)
class DispatchGitFacts:
    """Repository facts gathered at judgment time (AD-33)."""

    baseline_head_sha: str
    current_head_sha: str
    changed_paths: tuple[str, ...]
    branch_merged: bool
    story_merged_on_main: bool


@dataclass(frozen=True)
class DispatchCompletionInput:
    """Inputs to the completion judge — process facts plus git facts."""

    session_alive: bool
    git: DispatchGitFacts
    # Harness notification/self-report — recorded for diagnostics only, never
    # used as a verdict input (CAP-2 Always bullet).
    harness_reported_failure: bool = False


def is_spec_only_narration(changed_paths: tuple[str, ...], spec_relative_path: str | None) -> bool:
    """True when the ENTIRE diff is the tracked story spec file itself.

    A session that only rewrites its own spec's frontmatter (a status flip,
    a hand-written Auto Run Result, a revert-to-baseline plus ``blocked:``)
    has produced narration, not work (Story 51.4, spec-pyforge-marshal
    CAP-252). ``spec_relative_path`` is the worktree-relative path of the
    story's tracked spec; ``None`` (spec not resolvable) or an empty diff
    never counts as narration-only.
    """
    if spec_relative_path is None or not changed_paths:
        return False
    return set(changed_paths) == {spec_relative_path}


def merge_subject_ref(ref: str, *, followup_review: FollowupReview | None) -> str | None:
    """The git revision whose commit subjects a run's merge reads are scoped to (Story 73.1, CAP-281), or
    ``None`` when there is nothing to read.

    A normal run (``followup_review is None``) reads every subject reachable from ``ref``
    (``origin/main``), exactly as before. A follow-up review run runs on a story that already landed
    once, so the story's own merge subject is on ``ref`` before the run exists; it counts only what
    reached ``ref`` after ``origin/main``'s tip at launch -- ``<launch_origin_main_sha>..<ref>``. Never
    the run's ``baseline_head_sha``: ``_ensure_dispatch_worktree`` reuses a story's surviving dispatch
    worktree, so the baseline can be the pre-merge tip, and ``<baseline>..<ref>`` would still hold the
    story's first merge. A follow-up marker that recorded no tip counts nothing (``None``) -- the run's
    own landing is still seen through ``branch_merged``."""
    if followup_review is None:
        return ref
    tip = followup_review.launch_origin_main_sha
    return f"{tip}..{ref}" if tip else None


def narration_spec_path(spec_relative_path: str | None, *, followup_review: FollowupReview | None) -> str | None:
    """The spec path a narration check (``is_spec_only_narration`` / ``has_git_progress``) is given
    (Story 73.1, CAP-281): ``spec_relative_path`` for a normal run, ``None`` for a follow-up review run.

    A review that patches nothing changes only its own story spec -- the flag, ``review_loop_iteration``,
    its review log -- and for that run that diff is its record, not narration (Story 51.4's rule is for a
    harness that only rewrote its spec instead of doing the work). ``None`` makes both checks read a
    spec-only diff as progress."""
    return None if followup_review is not None else spec_relative_path


def run_head_reached_ref(vcs: VcsPort, repo_root: Path, head_sha: str, ref: str) -> bool:
    """True when ``head_sha`` is an ancestor of ``ref`` (inclusive) — the run's own head is on ``ref``.

    Story 83.14: a corroborated merge subject on ``origin/main`` from an *earlier* branch tip must not
    count as this run's merge while the session's current head is still ahead of ``origin/main``.
    """
    try:
        return vcs.merge_base(repo_root, head_sha, ref) == head_sha
    except Exception:
        # ``merge_base`` raises ``VcsCommandError`` from the git adapter on unreadable refs.
        return False


def has_git_progress(git: DispatchGitFacts, *, spec_relative_path: str | None = None) -> bool:
    """True when git shows work beyond the launch baseline.

    A revert-to-baseline plus a spec-only status flip is not progress
    (Story 51.4): when the whole diff collapses to the tracked spec file
    itself, this returns ``False`` even though the head SHA moved. Existing
    callers that omit ``spec_relative_path`` keep today's behavior exactly.
    """
    if is_spec_only_narration(git.changed_paths, spec_relative_path):
        return False
    if git.current_head_sha != git.baseline_head_sha:
        return True
    return bool(git.changed_paths)


def judge_dispatch_completion(inp: DispatchCompletionInput) -> DispatchSessionVerdict:
    """Judge completion from git + process facts only."""
    if inp.git.branch_merged or inp.git.story_merged_on_main:
        return DispatchSessionVerdict.COMPLETED
    if inp.session_alive or has_git_progress(inp.git):
        return DispatchSessionVerdict.LIVE
    return DispatchSessionVerdict.FAILED


def zombie_redispatch_evidence(
    *,
    story_key: str,
    verdict: DispatchSessionVerdict,
    git: DispatchGitFacts,
    session_alive: bool,
    harness_reported_failure: bool,
) -> str | None:
    """When redispatch must be refused, return human-readable evidence."""
    if verdict != DispatchSessionVerdict.LIVE:
        return None
    if session_alive:
        return f"story {story_key!r} already has a live dispatch session (session process alive)"
    parts = [
        f"story {story_key!r} dispatch session is still live by git facts",
        f"baseline {git.baseline_head_sha[:12]} -> current {git.current_head_sha[:12]}",
    ]
    if git.changed_paths:
        parts.append(f"{len(git.changed_paths)} changed path(s) since baseline")
    if harness_reported_failure:
        parts.append("harness reported failure/killed but git progress contradicts")
    return "; ".join(parts)
