"""Unit tests for dispatch supervisor tick helpers."""

from __future__ import annotations

from pyforge.marshal.core.dispatch_completion import (
    DispatchGitFacts,
    DispatchSessionVerdict,
)
from pyforge.marshal.core.dispatch_supervisor_state import (
    landing_journal_indicates_complete,
    should_terminalize_verify_refusal,
    supervisor_should_exit,
)


def test_landing_journal_indicates_complete_for_landed_and_already_landed() -> None:
    assert landing_journal_indicates_complete("landed")
    assert landing_journal_indicates_complete("already_landed")
    assert not landing_journal_indicates_complete("refused")
    assert not landing_journal_indicates_complete(None)


def test_supervisor_should_exit_after_successful_land_journal() -> None:
    assert supervisor_should_exit(
        completion_verdict=DispatchSessionVerdict.LIVE.value,
        story_merged_on_main=False,
        landing_verdict="landed",
    )


def test_supervisor_should_exit_still_waits_without_land_or_merge() -> None:
    assert not supervisor_should_exit(
        completion_verdict=DispatchSessionVerdict.LIVE.value,
        story_merged_on_main=False,
        landing_verdict=None,
    )


def test_terminalize_verify_refusal_unchanged() -> None:
    git = DispatchGitFacts(
        baseline_head_sha="aaa",
        current_head_sha="bbb",
        changed_paths=("src/x.py",),
        branch_merged=False,
        story_merged_on_main=False,
    )
    assert should_terminalize_verify_refusal(
        session_alive=False,
        verification_verdict="refused",
        git=git,
    )
