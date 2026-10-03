"""Story 83.10: verification refusal park / land-only / floor-raise."""

from __future__ import annotations

from pyforge.marshal.core.dispatch_completion import DispatchSessionVerdict
from pyforge.marshal.core.dispatch_harness_done import should_take_verification_refusal_land_only
from pyforge.marshal.core.dispatch_retry import (
    DispatchBlockKind,
    classify_dispatch_block,
    format_verification_refusal_park_reason,
    is_dispatch_verification_refusal,
    is_verify_refusal_gate,
)
from pyforge.marshal.core.dispatch_verification import DispatchVerificationVerdict


def test_mrs_gate_018_is_a_verification_refusal_gate() -> None:
    assert is_verify_refusal_gate("MRS-GATE-018")


def test_is_dispatch_verification_refusal_for_gate_018() -> None:
    assert is_dispatch_verification_refusal(
        completion_verdict=DispatchSessionVerdict.FAILED.value,
        verification_verdict=DispatchVerificationVerdict.REFUSED.value,
        verification_failed_gate="MRS-GATE-018",
    )


def test_park_reason_names_the_failed_verification_message() -> None:
    reason = format_verification_refusal_park_reason(
        story_key="83.10",
        run_id="run-1",
        failed_gate="MRS-GATE-010",
        failed_command="pixi run -e pyforge-guild lint-types",
    )
    assert "MRS-GATE-010" in reason
    assert "pixi run -e pyforge-guild lint-types" in reason


def test_is_dispatch_verification_refusal() -> None:
    assert is_dispatch_verification_refusal(
        completion_verdict=DispatchSessionVerdict.FAILED.value,
        verification_verdict=DispatchVerificationVerdict.REFUSED.value,
        verification_failed_gate="MRS-GATE-001",
    )
    assert not is_dispatch_verification_refusal(
        completion_verdict=DispatchSessionVerdict.FAILED.value,
        verification_verdict=DispatchVerificationVerdict.REFUSED.value,
        verification_failed_gate="MRS-GATE-007",
    )
    assert not is_dispatch_verification_refusal(
        completion_verdict=DispatchSessionVerdict.STOPPED_EXTERNALLY.value,
        verification_verdict=DispatchVerificationVerdict.REFUSED.value,
        verification_failed_gate="MRS-GATE-001",
    )


def test_should_take_verification_refusal_land_only_when_head_moved() -> None:
    assert should_take_verification_refusal_land_only(
        "in-review",
        False,
        completion_verdict=DispatchSessionVerdict.FAILED.value,
        verification_verdict=DispatchVerificationVerdict.REFUSED.value,
        verification_failed_gate="MRS-GATE-010",
        refusal_head_sha="aaa",
        current_head_sha="bbb",
    )


def test_should_not_take_verification_refusal_land_only_when_head_unchanged() -> None:
    assert not should_take_verification_refusal_land_only(
        "in-review",
        False,
        completion_verdict=DispatchSessionVerdict.FAILED.value,
        verification_verdict=DispatchVerificationVerdict.REFUSED.value,
        verification_failed_gate="MRS-GATE-010",
        refusal_head_sha="aaa",
        current_head_sha="aaa",
    )


def test_should_not_take_verification_refusal_land_only_after_send_back_to_ready() -> None:
    assert not should_take_verification_refusal_land_only(
        "ready-for-dev",
        False,
        completion_verdict=DispatchSessionVerdict.FAILED.value,
        verification_verdict=DispatchVerificationVerdict.REFUSED.value,
        verification_failed_gate="MRS-GATE-001",
        refusal_head_sha="aaa",
        current_head_sha="bbb",
    )


def test_park_rule_mutation_terminal_on_verify_with_progress() -> None:
    """Removing Story 83.10's progress rule makes this assertion fail (was TRANSIENT)."""
    assert (
        classify_dispatch_block(
            session_log="session finished",
            failed_gate="MRS-GATE-001",
            changed_path_count=2,
        )
        is DispatchBlockKind.TERMINAL
    )
