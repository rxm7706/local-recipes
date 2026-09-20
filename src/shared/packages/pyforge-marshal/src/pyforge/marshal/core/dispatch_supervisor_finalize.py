"""Supervisor finalization when the harness cannot run shell (Story 28.24, CAP-7).

Pure decision helpers only — commit/push/verify I/O lives in the dispatch
supervisor subprocess.
"""

from __future__ import annotations

from enum import StrEnum

from .dispatch_completion import DispatchGitFacts, has_git_progress
from .dispatch_verification import DispatchVerificationVerdict

_SHELL_UNAVAILABLE_MARKERS: tuple[str, ...] = (
    "shell unavailable",
    "cannot run shell",
    "rejected in-session",
    "shell rejected",
    "pixi rejected",
    "git rejected",
)

_HARNESS_DONE_MARKERS: tuple[str, ...] = (
    "implementation done",
    "implementation complete",
    "story complete",
    "all acceptance criteria",
    "bmad-build-auto",
)


class FinalizeTrigger(StrEnum):
    HARNESS_DONE = "harness-done"
    SHELL_UNAVAILABLE = "shell-unavailable"
    COMMITABLE_DIRTY = "commitable-dirty"


def session_harness_reported_done_or_shell_unavailable(
    session_log: str | None,
) -> bool:
    """True when the session log claims done or could not invoke shell."""
    if not session_log or not session_log.strip():
        return False
    lowered = session_log.lower()
    if any(marker in lowered for marker in _SHELL_UNAVAILABLE_MARKERS):
        return True
    return any(marker in lowered for marker in _HARNESS_DONE_MARKERS)


def classify_finalize_trigger(session_log: str | None) -> FinalizeTrigger:
    if session_harness_reported_done_or_shell_unavailable(session_log):
        if session_log and any(marker in session_log.lower() for marker in _SHELL_UNAVAILABLE_MARKERS):
            return FinalizeTrigger.SHELL_UNAVAILABLE
        return FinalizeTrigger.HARNESS_DONE
    return FinalizeTrigger.COMMITABLE_DIRTY


def supervisor_should_finalize_harness_work(
    *,
    session_alive: bool,
    git: DispatchGitFacts,
    session_log: str | None,
    verification_verdict: str | None,
    landing_complete: bool,
) -> bool:
    """True when the supervisor must commit/push/verify before terminalizing."""
    if session_alive or landing_complete:
        return False
    if git.branch_merged or git.story_merged_on_main:
        return False
    if not has_git_progress(git):
        return False
    if verification_verdict == DispatchVerificationVerdict.VERIFIED.value:
        return False
    return True


def finalize_attempt_journaled(folded, run_id: str) -> bool:
    from . import dispatch as dispatch_core
    from .journal import Phase

    return any(
        entry.run_id == run_id and entry.phase == Phase.OUTCOME
        for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_FINALIZE)
    )


def finalize_attempt_failed(folded, run_id: str) -> bool:
    from . import dispatch as dispatch_core
    from .journal import Phase

    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_FINALIZE):
        if entry.run_id != run_id or entry.phase != Phase.OUTCOME:
            continue
        if entry.payload.get("ok") is False:
            return True
    return False


def finalize_failure_worktree_path(folded, run_id: str) -> str | None:
    from . import dispatch as dispatch_core
    from .journal import Phase

    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_FINALIZE):
        if entry.run_id != run_id or entry.phase != Phase.OUTCOME:
            continue
        if entry.payload.get("ok") is not False:
            continue
        raw = entry.payload.get("worktree_path")
        return raw if isinstance(raw, str) else None
    return None
