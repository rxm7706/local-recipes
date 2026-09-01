"""Pure dispatch-supervisor tick helpers (hotfix 2026-09-01; Story 28.17)."""

from __future__ import annotations

from .dispatch_completion import DispatchGitFacts, has_git_progress
from .dispatch_verification import DispatchVerificationVerdict

# Default: five supervisor ticks (~5 minutes at 60s) before forcing another
# land attempt when verify already passed but merge has not landed.
DEFAULT_STUCK_LAND_TICK_THRESHOLD = 5


def should_retry_stuck_land(
    *,
    verification_verdict: str | None,
    story_merged_on_main: bool,
    landing_journaled: bool,
    stuck_land_ticks: int,
    threshold: int = DEFAULT_STUCK_LAND_TICK_THRESHOLD,
) -> bool:
    return (
        verification_verdict == "verified"
        and not story_merged_on_main
        and not landing_journaled
        and stuck_land_ticks >= threshold
    )


def supervisor_should_exit(
    *,
    completion_verdict: str,
    story_merged_on_main: bool,
) -> bool:
    """Terminal states where the detached supervisor may stop heartbeating."""
    return story_merged_on_main or completion_verdict in {"completed", "failed"}


def should_terminalize_verify_refusal(
    *,
    session_alive: bool,
    verification_verdict: str | None,
    git: DispatchGitFacts,
) -> bool:
    """Story 28.17: dead session + verify refused + git progress → FAILED exit.

    Without this, ``judge_dispatch_completion`` stays ``LIVE`` (git facts) while
    the supervisor heartbeats forever after ``MRS-GATE-001`` (or any verify
    refuse), freezing ``--stories`` drains overnight.
    """
    if session_alive:
        return False
    if verification_verdict != DispatchVerificationVerdict.REFUSED.value:
        return False
    return has_git_progress(git)
