"""Unit tests for ``pyforge.marshal.core.landing_checks`` (Story 80.1, CAP-284): the pure
classification of the check runs a forge reports on a commit -- green / red / pending / empty."""

from __future__ import annotations

import pytest

from pyforge.marshal.core.landing_checks import (
    GREEN_CONCLUSIONS,
    CheckRun,
    CheckState,
    CheckVerdict,
    classify_check_runs,
)


def _done(name: str, conclusion: str | None) -> CheckRun:
    return CheckRun(name=name, status="completed", conclusion=conclusion)


def _running(name: str, status: str = "in_progress") -> CheckRun:
    return CheckRun(name=name, status=status)


def test_no_runs_is_empty_never_green() -> None:
    assert classify_check_runs(()) == CheckVerdict(state=CheckState.EMPTY)


@pytest.mark.parametrize("conclusion", ["success", "skipped", "neutral"])
def test_a_run_concluded_success_skipped_or_neutral_is_green(conclusion: str) -> None:
    assert classify_check_runs((_done("ci", conclusion),)).state is CheckState.GREEN


def test_the_green_conclusions_are_exactly_the_three() -> None:
    assert GREEN_CONCLUSIONS == frozenset({"success", "skipped", "neutral"})


def test_all_runs_green_is_green_with_nothing_to_name() -> None:
    verdict = classify_check_runs((_done("lint", "success"), _done("docs", "skipped"), _done("e2e", "neutral")))
    assert verdict == CheckVerdict(state=CheckState.GREEN)


@pytest.mark.parametrize(
    "conclusion",
    ["failure", "cancelled", "timed_out", "action_required", "stale", "startup_failure", "something-new"],
)
def test_any_other_conclusion_is_red_and_names_the_run(conclusion: str) -> None:
    bad = _done("Detectors / scripts-suite", conclusion)
    verdict = classify_check_runs((_done("lint", "success"), bad))
    assert verdict.state is CheckState.RED
    assert verdict.red == (bad,)
    assert verdict.pending == ()


def test_a_completed_run_with_no_conclusion_is_red_not_green() -> None:
    """AD-8: a signal that cannot be read as a pass is not a pass."""
    run = _done("ci", None)
    verdict = classify_check_runs((run,))
    assert verdict.state is CheckState.RED
    assert verdict.red == (run,)


@pytest.mark.parametrize("status", ["queued", "in_progress", "waiting", "requested", "pending"])
def test_a_run_not_completed_is_pending_whatever_its_status(status: str) -> None:
    run = _running("ci", status)
    verdict = classify_check_runs((_done("lint", "success"), run))
    assert verdict.state is CheckState.PENDING
    assert verdict.pending == (run,)
    assert verdict.red == ()


def test_a_pending_run_that_already_carries_a_green_looking_conclusion_is_still_pending() -> None:
    """Only ``completed`` carries a verdict: an in-progress run is pending even if a conclusion is present."""
    run = CheckRun(name="ci", status="in_progress", conclusion="success")
    assert classify_check_runs((run,)).state is CheckState.PENDING


def test_red_beats_pending_and_both_are_named() -> None:
    red = _done("tests", "failure")
    pending = _running("e2e")
    verdict = classify_check_runs((pending, _done("lint", "success"), red))
    assert verdict.state is CheckState.RED
    assert verdict.red == (red,)
    assert verdict.pending == (pending,)


def test_every_red_run_is_named_in_order() -> None:
    first, second = _done("a", "failure"), _done("b", "cancelled")
    assert classify_check_runs((first, _done("c", "success"), second)).red == (first, second)


def test_accepts_any_iterable_once() -> None:
    runs = iter((_done("a", "success"), _done("b", "success")))
    assert classify_check_runs(runs).state is CheckState.GREEN


def test_check_run_is_frozen_and_serialises_to_plain_json() -> None:
    run = _done("ci", "success")
    with pytest.raises(AttributeError):
        run.name = "other"  # type: ignore[misc]
    assert run.to_json_dict() == {"name": "ci", "status": "completed", "conclusion": "success"}
    assert _running("ci").to_json_dict() == {"name": "ci", "status": "in_progress", "conclusion": None}


@pytest.mark.parametrize(
    ("name", "status", "conclusion"),
    [("", "completed", "success"), (None, "completed", "success"), ("ci", "", None), ("ci", "completed", 3)],
)
def test_check_run_refuses_a_malformed_field(name: object, status: object, conclusion: object) -> None:
    with pytest.raises(ValueError):
        CheckRun(name=name, status=status, conclusion=conclusion)  # type: ignore[arg-type]
