"""Pure dispatch retry / block classification (dispatch hotfix 2026-09-01).

Fleet drain must not treat every ``failed`` dispatch as a permanent block.
Transient harness quota/auth failures and retriable verify failures should
allow the next cycle (or explicit re-dispatch) to proceed.
"""

from __future__ import annotations

from enum import StrEnum

from .harness_session import (
    classify_session_log,
    is_transient_harness_session_outcome,
)


class DispatchBlockKind(StrEnum):
    TRANSIENT = "transient"
    TERMINAL = "terminal"


# Dispatch verification refusal gates (Story 83.10): after a session finished
# its work, a refusal at independent verify must park or land-only — never a
# fresh bmad-build-auto session or a Story 33.6 floor-raise.
_VERIFY_REFUSAL_GATES: frozenset[str] = frozenset(
    {
        "MRS-GATE-001",
        "MRS-GATE-002",
        "MRS-GATE-003",
        "MRS-GATE-004",
        "MRS-GATE-005",
        "MRS-GATE-006",
        "MRS-GATE-010",
        "MRS-GATE-011",
        "MRS-GATE-015",  # Story 22.12: cross-surface gate fail — retriable like 001
        "MRS-GATE-018",  # Story 83.2: pre-verification deferred-work intake refused
        "MRS-GATE-020",  # Story 83.19: CFE surface outside sanctioned retro
    }
)

# Legacy alias: pre-83.10 transient set equaled verify gates; session failures
# that never reached verify still use terminal classification below.
_TRANSIENT_FAILED_GATES: frozenset[str] = _VERIFY_REFUSAL_GATES

_TERMINAL_FAILED_GATES: frozenset[str] = frozenset(
    {
        "MRS-GATE-007",
        "MRS-GATE-008",
        "MRS-GATE-014",  # Story 28.22: pre-existing-gate WARN — no transient retry
        "MRS-DISP-005",
        "MRS-DISP-030",
    }
)


def is_verify_refusal_gate(failed_gate: str | None) -> bool:
    """True when ``failed_gate`` names an independent verification refusal."""
    return failed_gate in _VERIFY_REFUSAL_GATES


def is_dispatch_verification_refusal(
    *,
    completion_verdict: str | None,
    verification_verdict: str | None,
    verification_failed_gate: str | None,
) -> bool:
    """True when the session finished and independent verify refused (Story 83.10)."""
    from .dispatch_completion import DispatchSessionVerdict
    from .dispatch_verification import DispatchVerificationVerdict

    if completion_verdict != DispatchSessionVerdict.FAILED.value:
        return False
    if verification_verdict != DispatchVerificationVerdict.REFUSED.value:
        return False
    return is_verify_refusal_gate(verification_failed_gate) or verification_failed_gate in {
        "MRS-GATE-012",
        "MRS-GATE-013",
    }


def verification_refusal_head_unchanged(
    *,
    refusal_head_sha: str | None,
    current_head_sha: str | None,
) -> bool:
    """True when the worktree head still matches the refused verification tip."""
    if not refusal_head_sha or not current_head_sha:
        return True
    return refusal_head_sha == current_head_sha


def format_verification_refusal_park_reason(
    *,
    story_key: str,
    run_id: str,
    failed_gate: str | None,
    failed_command: str | None = None,
) -> str:
    """Operator-facing park reason naming the failed verification command."""
    gate = failed_gate or "unknown gate"
    if failed_command:
        cmd = f" ({failed_command!r})"
    else:
        cmd = ""
    return (
        f"dispatch verification refused for {story_key!r} (run {run_id!r}): "
        f"{gate}{cmd} -- branch unchanged since refusal; parked for operator fix "
        "(no fresh session; Story 83.10)"
    )


def classify_dispatch_block(
    *,
    session_log: str | None,
    failed_gate: str | None,
    changed_path_count: int,
) -> DispatchBlockKind:
    """Classify whether a failed dispatch should block fleet retry."""
    outcome = classify_session_log(session_log)
    if changed_path_count == 0 and is_transient_harness_session_outcome(outcome):
        return DispatchBlockKind.TRANSIENT
    if failed_gate in _TERMINAL_FAILED_GATES:
        return DispatchBlockKind.TERMINAL
    # Story 83.10: a verify refusal after real git progress parks — never
    # TRANSIENT (which would relaunch bmad-build-auto and feed floor-raise).
    if is_verify_refusal_gate(failed_gate) and changed_path_count > 0:
        return DispatchBlockKind.TERMINAL
    if failed_gate in _TRANSIENT_FAILED_GATES:
        return DispatchBlockKind.TRANSIENT
    if failed_gate in {"MRS-GATE-012", "MRS-GATE-013"}:
        if changed_path_count > 0:
            return DispatchBlockKind.TERMINAL
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
    return {story: reason for story, reason in blocked.items() if story not in merged_story_keys}


def should_dispatch_retry_escalate(prior_failed_attempts: int, max_dev_attempts: int) -> bool:
    """Pure: ``True`` when prior dispatch failures reached the dev ceiling.

    Mirrors ``core.supervise.evaluate_retry_escalation``'s
    ``attempt >= max_dev_attempts`` axis for the dispatch retry path (Story
    33.6, spec-adaptive-model-tiering CAP-2 on factory dispatch).
    """
    if (
        not isinstance(prior_failed_attempts, int)
        or isinstance(prior_failed_attempts, bool)
        or not isinstance(max_dev_attempts, int)
        or isinstance(max_dev_attempts, bool)
    ):
        return False
    if max_dev_attempts < 1:
        return False
    return prior_failed_attempts >= max_dev_attempts


def apply_dispatch_retry_floor_raise(
    from_model: str | None, review_model: str | None
) -> tuple[str | None, bool, str | None, str | None]:
    """Floor-raise a dispatch launch model from dev to review tier.

    Returns ``(model, escalated, from_model, to_model)`` -- detail fields
    are populated only when ``escalated`` is ``True``, matching spin resume's
    journal shape (Story 3.12 / Story 33.6).
    """
    if not isinstance(from_model, str) or not from_model:
        return from_model, False, None, None
    if not isinstance(review_model, str) or not review_model:
        return from_model, False, None, None
    if from_model == review_model:
        return from_model, False, None, None
    return review_model, True, from_model, review_model
