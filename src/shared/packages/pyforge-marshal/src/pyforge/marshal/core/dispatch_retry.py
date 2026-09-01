"""Pure dispatch retry / block classification (dispatch hotfix 2026-09-01).

Fleet drain must not treat every ``failed`` dispatch as a permanent block.
Transient harness quota/auth failures and retriable verify failures should
allow the next cycle (or explicit re-dispatch) to proceed.
"""

from __future__ import annotations

from enum import StrEnum

from .harness_session import (
    HarnessSessionOutcome,
    classify_session_log,
    is_transient_harness_session_outcome,
)


class DispatchBlockKind(StrEnum):
    TRANSIENT = "transient"
    TERMINAL = "terminal"


# Verify/test failures are retriable once WIP is committed or code fixed.
_TRANSIENT_FAILED_GATES: frozenset[str] = frozenset(
    {
        "MRS-GATE-001",
        "MRS-GATE-002",
        "MRS-GATE-003",
        "MRS-GATE-004",
        "MRS-GATE-005",
        "MRS-GATE-006",
        "MRS-GATE-010",
        "MRS-GATE-011",
    }
)

_TERMINAL_FAILED_GATES: frozenset[str] = frozenset(
    {
        "MRS-GATE-007",
        "MRS-GATE-008",
        "MRS-DISP-005",
        "MRS-DISP-030",
    }
)


def classify_dispatch_block(
    *,
    session_log: str | None,
    failed_gate: str | None,
    changed_path_count: int,
) -> DispatchBlockKind:
    """Classify whether a failed dispatch should block fleet retry."""
    outcome = classify_session_log(session_log)
    if (
        changed_path_count == 0
        and is_transient_harness_session_outcome(outcome)
    ):
        return DispatchBlockKind.TRANSIENT
    if failed_gate in _TERMINAL_FAILED_GATES:
        return DispatchBlockKind.TERMINAL
    if failed_gate in _TRANSIENT_FAILED_GATES:
        return DispatchBlockKind.TRANSIENT
    if failed_gate in {"MRS-GATE-012", "MRS-GATE-013"}:
        return DispatchBlockKind.TRANSIENT
    return DispatchBlockKind.TERMINAL


def exclude_harness_profiles_after_transient_failure(
    preference: tuple[str, ...],
    session_log: str | None,
) -> tuple[str, ...]:
    """Drop the first preference entry when its session log shows quota/auth."""
    if not preference:
        return preference
    outcome = classify_session_log(session_log)
    if is_transient_harness_session_outcome(outcome):
        return preference[1:]
    return preference


def prune_blocked_stories_merged_on_main(
    blocked: dict[str, str],
    *,
    merged_story_keys: frozenset[str],
) -> dict[str, str]:
    """Remove blocked entries for stories already landed on main."""
    if not blocked or not merged_story_keys:
        return blocked
    return {
        story: reason
        for story, reason in blocked.items()
        if story not in merged_story_keys
    }
