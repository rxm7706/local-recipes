"""Unit tests for ``pyforge.marshal.supervisor.durability`` (Story 3.8,
architecture spine AD-46/FR-61) -- ``classify_push_triggers``'s full
transition matrix, driven entirely through synthetic
``TaskPhaseSnapshot`` mappings (mirrors ``test_supervise.py``'s own
"every supervisor behaviour has a test that runs in milliseconds"
discipline). No port, no clock, no subprocess, no bmad-loop process
anywhere in this file -- ``classify_push_triggers`` is pure.
"""

from __future__ import annotations

from pyforge.marshal.ports.harness import TaskPhaseSnapshot
from pyforge.marshal.supervisor.durability import PushTrigger, classify_push_triggers


def _task(
    story_key: str,
    phase: str,
    *,
    commit_sha: str | None = None,
    branch: str = "",
) -> TaskPhaseSnapshot:
    return TaskPhaseSnapshot(
        story_key=story_key, phase=phase, commit_sha=commit_sha, branch=branch
    )


# --- no-op shapes --------------------------------------------------------------


def test_empty_mappings_produce_no_triggers():
    assert classify_push_triggers({}, {}) == ()


def test_unchanged_phase_produces_no_trigger():
    previous = {"1.1": _task("1.1", "dev-running")}
    current = {"1.1": _task("1.1", "dev-running")}
    assert classify_push_triggers(previous, current) == ()


def test_a_story_absent_from_current_produces_no_trigger():
    previous = {"1.1": _task("1.1", "review-verify")}
    current: dict[str, TaskPhaseSnapshot] = {}
    assert classify_push_triggers(previous, current) == ()


# --- each boundary, individually ------------------------------------------------


def test_review_verify_newly_reached_fires_review_verdict_recorded():
    previous = {"1.1": _task("1.1", "review-running")}
    current = {"1.1": _task("1.1", "review-verify")}
    assert classify_push_triggers(previous, current) == (
        PushTrigger("1.1", "review-verdict-recorded"),
    )


def test_commit_sha_newly_non_none_fires_dev_commit_landed():
    previous = {"1.1": _task("1.1", "committing", commit_sha=None)}
    current = {"1.1": _task("1.1", "committing", commit_sha="abc123")}
    assert classify_push_triggers(previous, current) == (
        PushTrigger("1.1", "dev-commit-landed"),
    )


def test_done_newly_reached_fires_story_merged():
    previous = {"1.1": _task("1.1", "committing")}
    current = {"1.1": _task("1.1", "done")}
    assert classify_push_triggers(previous, current) == (
        PushTrigger("1.1", "story-merged"),
    )


def test_a_story_missing_from_previous_still_fires_on_first_observation():
    """The first tick this run's state was ever read, or a story added
    since -- ``previous.get(story_key)`` degrades to ``None``, read as
    "not previously in that boundary state" (this module's own docstring):
    better one redundant push than a missed one."""
    previous: dict[str, TaskPhaseSnapshot] = {}
    current = {"1.1": _task("1.1", "done", commit_sha="abc123")}
    triggers = classify_push_triggers(previous, current)
    assert PushTrigger("1.1", "story-merged") in triggers
    assert PushTrigger("1.1", "dev-commit-landed") in triggers


def test_a_story_missing_from_previous_in_a_non_boundary_phase_fires_nothing():
    previous: dict[str, TaskPhaseSnapshot] = {}
    current = {"1.1": _task("1.1", "dev-running")}
    assert classify_push_triggers(previous, current) == ()


# --- two boundaries in one tick --------------------------------------------------


def test_commit_landing_and_story_merging_in_the_same_tick_fires_both():
    """The spec's own edge-case matrix, and the Design Notes' own stated
    common shape against the installed bmad-loop 0.9.0 engine: `commit_sha`
    turning non-None and `Phase.DONE` reached in the SAME diff."""
    previous = {"1.1": _task("1.1", "committing", commit_sha=None)}
    current = {"1.1": _task("1.1", "done", commit_sha="abc123")}
    triggers = classify_push_triggers(previous, current)
    assert set(triggers) == {
        PushTrigger("1.1", "dev-commit-landed"),
        PushTrigger("1.1", "story-merged"),
    }
    assert len(triggers) == 2


def test_review_verify_and_commit_landing_together():
    previous = {"1.1": _task("1.1", "review-running", commit_sha=None)}
    current = {"1.1": _task("1.1", "review-verify", commit_sha="abc123")}
    triggers = classify_push_triggers(previous, current)
    assert set(triggers) == {
        PushTrigger("1.1", "review-verdict-recorded"),
        PushTrigger("1.1", "dev-commit-landed"),
    }


# --- regression is tolerated, never raises --------------------------------------


def test_a_story_regressing_off_done_produces_no_trigger_for_done_again():
    """bmad-loop's own engine never regresses a task's phase, but the
    classifier must not crash on synthetic input that does -- and must not
    re-fire `story-merged` for a phase that is no longer `done`."""
    previous = {"1.1": _task("1.1", "done")}
    current = {"1.1": _task("1.1", "dev-running")}
    assert classify_push_triggers(previous, current) == ()


def test_a_story_leaving_done_and_returning_refires_story_merged():
    """Each diff is independent (per-tick), per this module's own
    docstring -- a phase moving off `done` and back on again re-fires,
    which is the correct reading of "every crossed boundary in the
    interval is reported"."""
    previous = {"1.1": _task("1.1", "dev-running")}
    current = {"1.1": _task("1.1", "done")}
    assert classify_push_triggers(previous, current) == (
        PushTrigger("1.1", "story-merged"),
    )


# --- multiple stories in one diff ------------------------------------------------


def test_multiple_stories_are_each_classified_independently():
    previous = {
        "1.1": _task("1.1", "review-running"),
        "1.2": _task("1.2", "dev-running"),
    }
    current = {
        "1.1": _task("1.1", "review-verify"),
        "1.2": _task("1.2", "done"),
    }
    triggers = classify_push_triggers(previous, current)
    assert set(triggers) == {
        PushTrigger("1.1", "review-verdict-recorded"),
        PushTrigger("1.2", "story-merged"),
    }


def test_push_trigger_carries_the_bare_story_key_unrendered():
    """`classify_push_triggers` never renders through `core.identity` --
    that is the CALLER's own concern (mirrors every other harness-native
    key this package re-spells only at its own journal boundary)."""
    previous: dict[str, TaskPhaseSnapshot] = {}
    current = {"3-8-some-slug": _task("3-8-some-slug", "done")}
    triggers = classify_push_triggers(previous, current)
    assert triggers[0].story_key == "3-8-some-slug"
