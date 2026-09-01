"""Unit tests for dispatch hotfix modules (2026-09-01)."""

from __future__ import annotations

from pyforge.marshal.core.dispatch_retry import (
    DispatchBlockKind,
    classify_dispatch_block,
    exclude_harness_profiles_after_transient_failure,
    prune_blocked_stories_merged_on_main,
)
from pyforge.marshal.core.dispatch_supervisor_state import (
    should_retry_stuck_land,
    supervisor_should_exit,
)
from pyforge.marshal.core.gate import widen_effective_surface_with_paths
from pyforge.marshal.core.harness_session import (
    HarnessSessionOutcome,
    classify_session_log,
)


def test_classify_session_log_quota() -> None:
    log = "Error: monthly spend limit reached for this workspace"
    assert classify_session_log(log) is HarnessSessionOutcome.QUOTA_EXCEEDED


def test_classify_session_log_auth() -> None:
    log = "cursor: not logged in — run cursor auth login"
    assert classify_session_log(log) is HarnessSessionOutcome.AUTH_FAILURE


def test_classify_session_log_harness_model_mismatch() -> None:
    log = "Cannot use this model: haiku. Available models: auto, gpt-5.3-codex"
    assert classify_session_log(log) is HarnessSessionOutcome.HARNESS_MISCONFIG


def test_transient_block_on_model_mismatch() -> None:
    kind = classify_dispatch_block(
        session_log="Cannot use this model: haiku",
        failed_gate=None,
        changed_path_count=0,
    )
    assert kind is DispatchBlockKind.TRANSIENT


def test_transient_block_on_quota_with_no_git_progress() -> None:
    kind = classify_dispatch_block(
        session_log="monthly spend limit exceeded",
        failed_gate=None,
        changed_path_count=0,
    )
    assert kind is DispatchBlockKind.TRANSIENT


def test_terminal_block_on_scope_gate() -> None:
    kind = classify_dispatch_block(
        session_log="",
        failed_gate="MRS-GATE-007",
        changed_path_count=3,
    )
    assert kind is DispatchBlockKind.TERMINAL


def test_transient_block_on_verify_gate() -> None:
    kind = classify_dispatch_block(
        session_log="tests failed",
        failed_gate="MRS-GATE-001",
        changed_path_count=5,
    )
    assert kind is DispatchBlockKind.TRANSIENT


def test_exclude_harness_after_quota_failure() -> None:
    preference = ("claude", "cursor", "copilot")
    result = exclude_harness_profiles_after_transient_failure(
        preference, "monthly spend limit hit"
    )
    assert result == ("cursor", "copilot")


def test_exclude_harness_keeps_preference_on_success_log() -> None:
    preference = ("claude", "cursor")
    result = exclude_harness_profiles_after_transient_failure(
        preference, "story complete, all tests green"
    )
    assert result == preference


def test_prune_blocked_stories_merged_on_main() -> None:
    blocked = {
        "28-7-done": "verify failed",
        "28-8-stuck": "verify failed",
    }
    pruned = prune_blocked_stories_merged_on_main(
        blocked,
        merged_story_keys=frozenset({"28-7-done"}),
    )
    assert pruned == {"28-8-stuck": "verify failed"}


def test_should_retry_stuck_land_after_threshold() -> None:
    assert should_retry_stuck_land(
        verification_verdict="verified",
        story_merged_on_main=False,
        landing_journaled=False,
        stuck_land_ticks=5,
    )


def test_should_not_retry_stuck_land_when_merged() -> None:
    assert not should_retry_stuck_land(
        verification_verdict="verified",
        story_merged_on_main=True,
        landing_journaled=False,
        stuck_land_ticks=10,
    )


def test_supervisor_should_exit_on_completed() -> None:
    assert supervisor_should_exit(
        completion_verdict="completed",
        story_merged_on_main=False,
    )


def test_supervisor_should_exit_when_merged() -> None:
    assert supervisor_should_exit(
        completion_verdict="live",
        story_merged_on_main=True,
    )


def test_widen_effective_surface_with_paths() -> None:
    surface = ("src/**",)
    widened = widen_effective_surface_with_paths(
        surface, ("src/foo/bar.py", "docs/readme.md")
    )
    assert "src/foo/bar.py" in widened
    assert "docs/readme.md" in widened
    assert "src/**" in widened
