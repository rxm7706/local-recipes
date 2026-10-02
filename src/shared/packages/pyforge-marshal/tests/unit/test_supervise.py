"""Unit tests for ``pyforge.marshal.core.supervise`` (Story 3.5,
architecture spine AD-9/AD-20) -- ``evaluate_idle``'s full ladder-transition
matrix, driven entirely through synthetic ``Sample`` sequences with
millisecond-scale ``datetime`` deltas (AD-20's own "every supervisor
behaviour has a test that runs in milliseconds"). No port, no clock, no
subprocess anywhere in this file -- ``evaluate_idle`` is pure.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta, timezone

import pytest

from pyforge.marshal.core.supervise import (
    ACTION_PRECEDENCE,
    CeilingStatus,
    EscalationStatus,
    LadderRung,
    MtimeSighting,
    Sample,
    UsageFreshness,
    evaluate_ceiling,
    evaluate_compression_ladder,
    evaluate_escalation,
    evaluate_idle,
    evaluate_retry_escalation,
    idle_anchor,
    idle_since,
    judge_usage_freshness,
    normalise_pane,
    rung_at,
    rung_index,
    shows_fresh_output,
)
from pyforge.marshal.ports.harness import DeferredStory

_T0 = datetime(2026, 8, 3, 5, 45, 12, tzinfo=timezone.utc)


def _sample(offset_ms: int, *, pane: str | None = "same", mtime: float | None = 1.0) -> Sample:
    return Sample(moment=_T0 + timedelta(milliseconds=offset_ms), pane_content=pane, log_mtime=mtime)


# --- resting position / degenerate inputs -------------------------------------


def test_empty_samples_returns_none():
    assert evaluate_idle([], threshold_s=1.0) == LadderRung.NONE


def test_single_sample_returns_none_regardless_of_moment():
    """One sample has nothing to compare against -- elapsed is trivially
    zero (the sample IS its own reference point)."""
    assert evaluate_idle([_sample(999_999)], threshold_s=0.001) == LadderRung.NONE


def test_below_one_threshold_returns_none():
    samples = [_sample(0), _sample(50), _sample(99)]
    assert evaluate_idle(samples, threshold_s=0.1) == LadderRung.NONE


# --- ladder transitions, millisecond-scale ------------------------------------


def test_exactly_one_threshold_crossing_returns_nudge():
    samples = [_sample(0), _sample(100)]
    assert evaluate_idle(samples, threshold_s=0.1) == LadderRung.NUDGE


def test_just_under_two_thresholds_still_nudge():
    samples = [_sample(0), _sample(199)]
    assert evaluate_idle(samples, threshold_s=0.1) == LadderRung.NUDGE


def test_exactly_two_thresholds_returns_stop_and_retry():
    samples = [_sample(0), _sample(200)]
    assert evaluate_idle(samples, threshold_s=0.1) == LadderRung.STOP_AND_RETRY


def test_exactly_three_thresholds_returns_defer():
    samples = [_sample(0), _sample(300)]
    assert evaluate_idle(samples, threshold_s=0.1) == LadderRung.DEFER


def test_far_past_three_thresholds_stays_capped_at_defer():
    """The ladder never steps past `defer` regardless of how far elapsed
    exceeds it -- `defer` is terminal (the spec's own Never clause: a fixed
    3-rung sequence)."""
    samples = [_sample(0), _sample(1_000_000)]
    assert evaluate_idle(samples, threshold_s=0.1) == LadderRung.DEFER


# --- fresh output re-arms the window ------------------------------------------


def test_a_changed_pane_content_resets_the_idle_window():
    """Fresh pane output at the LAST sample resets the reference point to
    that sample's own moment -- elapsed collapses back to zero even though
    the sequence as a whole spans well past a threshold."""
    samples = [_sample(0, pane="idle"), _sample(500, pane="idle"), _sample(520, pane="responded")]
    assert evaluate_idle(samples, threshold_s=0.1) == LadderRung.NONE


def test_a_changed_mtime_also_resets_the_idle_window():
    """Either signal re-arms -- pane content is not the only observable."""
    samples = [
        _sample(0, mtime=1.0),
        _sample(500, mtime=1.0),
        _sample(520, mtime=2.0),
    ]
    assert evaluate_idle(samples, threshold_s=0.1) == LadderRung.NONE


def test_re_escalation_after_a_reset_needs_a_full_fresh_threshold():
    """A session that responds to a nudge earns a FULL threshold before the
    next rung -- not merely "some more time" (the spec's own Always
    bullet)."""
    samples = [
        _sample(0, pane="idle"),
        _sample(500, pane="idle"),
        _sample(520, pane="responded"),  # resets the window here
        _sample(610, pane="responded"),  # only 90ms since the reset
    ]
    assert evaluate_idle(samples, threshold_s=0.1) == LadderRung.NONE
    samples_full = samples + [_sample(625, pane="responded")]  # 105ms since reset
    assert evaluate_idle(samples_full, threshold_s=0.1) == LadderRung.NUDGE


def test_a_change_partway_through_a_longer_sequence_uses_the_latest_change():
    """Multiple changes across the sequence -- only the MOST RECENT one
    matters as the reference point, never the first."""
    samples = [
        _sample(0, pane="a"),
        _sample(50, pane="b"),  # change #1
        _sample(100, pane="c"),  # change #2 -- this is the real reference
        _sample(150, pane="c"),
    ]
    # 50ms since the last change (100ms), well under a 100ms threshold.
    assert evaluate_idle(samples, threshold_s=0.1) == LadderRung.NONE


def test_none_of_the_first_two_samples_ever_repeated_still_counts_as_idle():
    """Two samples with IDENTICAL pane/mtime never change -- the reference
    point is the very first sample, and elapsed accumulates from there."""
    samples = [_sample(0), _sample(0 + 250)]
    assert evaluate_idle(samples, threshold_s=0.1) == LadderRung.STOP_AND_RETRY


# --- rung_index ----------------------------------------------------------------


def test_rung_at_is_rung_index_inverse_and_clamps_out_of_range():
    """``rung_at`` is how a caller outside this module names "one rung above
    this one" without reaching into the private ordering tuple -- the
    supervisor uses it to clamp escalation to a single rung per tick. It is
    total: no index can raise or wrap backwards."""
    for expected in (LadderRung.NONE, LadderRung.NUDGE, LadderRung.STOP_AND_RETRY, LadderRung.DEFER):
        assert rung_at(rung_index(expected)) is expected
    assert rung_at(-1) is LadderRung.NONE
    assert rung_at(-999) is LadderRung.NONE
    assert rung_at(4) is LadderRung.DEFER
    assert rung_at(10**6) is LadderRung.DEFER


def test_idle_since_returns_the_latest_change_point():
    """The anchor ``evaluate_idle`` measures from, exposed because the
    CALLER needs the same value: after the supervisor's own nudge types into
    the observed pane, it rebases its sample history onto that text while
    preserving this anchor, so the supervisor's OWN output cannot re-arm the
    window it was escalating from."""
    changed = _sample(300, pane="different")
    samples = [_sample(0), _sample(100), changed, _sample(400, pane="different")]
    assert idle_since(samples) == changed.moment


def test_idle_since_falls_back_to_the_first_sample_when_nothing_ever_changed():
    samples = [_sample(0), _sample(100), _sample(200)]
    assert idle_since(samples) == samples[0].moment


def test_idle_since_returns_none_for_an_empty_sequence():
    assert idle_since([]) is None


def test_idle_since_and_evaluate_idle_can_never_disagree():
    """``evaluate_idle`` delegates to ``idle_since`` rather than repeating
    the scan, so the rung and the anchor are always derived from the same
    reading of the same sequence."""
    samples = [_sample(0), _sample(100), _sample(250, pane="fresh"), _sample(450, pane="fresh")]
    anchor = idle_since(samples)
    elapsed_s = (samples[-1].moment - anchor).total_seconds()
    assert evaluate_idle(samples, threshold_s=elapsed_s) == LadderRung.NUDGE
    assert evaluate_idle(samples, threshold_s=elapsed_s / 2) == LadderRung.STOP_AND_RETRY


def test_rung_index_orders_the_ladder_ascending():
    assert rung_index(LadderRung.NONE) == 0
    assert rung_index(LadderRung.NUDGE) == 1
    assert rung_index(LadderRung.STOP_AND_RETRY) == 2
    assert rung_index(LadderRung.DEFER) == 3


# --- contract violations -------------------------------------------------------


def test_evaluate_idle_rejects_a_bare_string_samples_argument():
    """A `str` satisfies `Sequence` -- this package's own established
    footgun guard (`core/journal.py::fold`, `core/identity.py::resolve_feed`)
    extended here."""
    with pytest.raises(TypeError):
        evaluate_idle("not-a-list-of-samples", threshold_s=1.0)


def test_evaluate_idle_rejects_a_non_sequence_samples_argument():
    with pytest.raises(TypeError):
        evaluate_idle(42, threshold_s=1.0)  # type: ignore[arg-type]


def test_evaluate_idle_rejects_a_non_positive_threshold():
    with pytest.raises(ValueError):
        evaluate_idle([_sample(0)], threshold_s=0.0)
    with pytest.raises(ValueError):
        evaluate_idle([_sample(0)], threshold_s=-1.0)


def test_evaluate_idle_rejects_a_nan_threshold():
    """Review finding: ``float('nan')`` compares ``False`` against every
    relational operator (IEEE 754), so the previous ``threshold_s <= 0``
    guard silently let a NaN threshold sail through instead of being
    rejected like every other invalid value. ``not (threshold_s > 0)``
    catches it -- verified live here alongside the boundary values a
    negated check must still get right (zero, negative, and a genuinely
    valid positive number)."""
    with pytest.raises(ValueError):
        evaluate_idle([_sample(0)], threshold_s=float("nan"))
    # Negative control: the fix must not reject anything valid.
    assert evaluate_idle([_sample(0)], threshold_s=1.0) == LadderRung.NONE


def test_idle_since_rejects_a_bare_string_samples_argument():
    """Follow-up review finding: ``idle_since`` is PUBLIC and
    ``supervisor/__main__.py`` calls it directly, not only through its
    guarded sibling -- but it carried none of ``evaluate_idle``'s type
    guards, so the same input that earns a documented ``TypeError`` one call
    over raised a raw ``AttributeError`` from inside its own ``zip``. In the
    supervisor's tick that exception class sits outside the ``except
    (FsError, ValueError)`` handler and would kill the sidecar with a
    traceback after ``supervisor-attach``."""
    with pytest.raises(TypeError):
        idle_since("not-a-list-of-samples")
    with pytest.raises(TypeError):
        idle_since(42)  # type: ignore[arg-type]


def test_a_denormal_threshold_saturates_to_defer_rather_than_overflowing():
    """Follow-up review finding: ``threshold_s`` only has to be positive and
    finite to pass every guard, and a denormal-small one overflows
    ``idle_elapsed_s / threshold_s`` to ``inf``. ``int(inf)`` raises
    ``OverflowError`` -- neither ``FsError`` nor ``ValueError``, so it
    escapes ``supervisor/__main__.py``'s own tick handler entirely and kills
    the sidecar with a raw traceback after ``supervisor-attach``. An
    infinite ratio IS ``DEFER`` by this function's own floor-and-cap
    definition."""
    samples = [_sample(0), _sample(60_000)]
    assert evaluate_idle(samples, threshold_s=5e-324) == LadderRung.DEFER
    # Negative control: a merely small threshold still floor-divides
    # normally rather than taking the saturating path.
    assert evaluate_idle(samples, threshold_s=30.0) == LadderRung.STOP_AND_RETRY


def test_evaluate_idle_rejects_a_non_numeric_threshold():
    with pytest.raises(TypeError):
        evaluate_idle([_sample(0)], threshold_s="60")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        evaluate_idle([_sample(0)], threshold_s=True)  # type: ignore[arg-type]


def test_sample_is_a_plain_frozen_dataclass():
    sample = _sample(0)
    with pytest.raises(AttributeError):
        sample.pane_content = "mutated"  # type: ignore[misc]


# --- the monotonic elapsed basis (review finding) ----------------------------


def _mono_sample(*, wall_ms: int, mono_s: float | None, pane: str | None = "same") -> Sample:
    return Sample(
        moment=_T0 + timedelta(milliseconds=wall_ms),
        pane_content=pane,
        log_mtime=1.0,
        monotonic_s=mono_s,
    )


def test_monotonic_readings_win_over_a_jumped_wall_clock():
    """Review finding: elapsed idle time must be measured monotonically.

    A host suspended mid-run (or an NTP step) advances the WALL clock across
    an interval in which the session was not running and could not possibly
    have produced output. Scored on ``moment`` alone, an hour of suspend at
    the shipped 25-minute default reached ``NUDGE`` on the first tick after
    wake and would have hard-stopped and relaunched a perfectly healthy
    engine on the next one. ``time.monotonic()`` excludes suspended time and
    cannot be stepped, so the pair of monotonic readings is the truth.
    """
    samples = [
        _mono_sample(wall_ms=0, mono_s=100.0),
        # One hour of wall clock, one second of real elapsed time.
        _mono_sample(wall_ms=3_600_000, mono_s=101.0),
    ]
    assert evaluate_idle(samples, threshold_s=60.0) == LadderRung.NONE


def test_monotonic_readings_still_escalate_on_genuine_elapsed_time():
    """The mirror of the test above -- the guard must not have simply
    disabled escalation. Here the wall clock barely moves while the
    monotonic reading records genuine elapsed idleness, and the ladder
    climbs on the monotonic evidence."""
    samples = [
        _mono_sample(wall_ms=0, mono_s=100.0),
        _mono_sample(wall_ms=1, mono_s=280.0),
    ]
    assert evaluate_idle(samples, threshold_s=60.0) == LadderRung.DEFER


def test_wall_clock_is_the_fallback_when_either_endpoint_lacks_a_reading():
    """Backwards compatibility is explicit, not incidental: a sequence that
    carries only ``moment`` (every synthetic test predating the field, and
    any future caller replaying journalled samples) keeps the previous
    behaviour exactly."""
    both_missing = [_mono_sample(wall_ms=0, mono_s=None), _mono_sample(wall_ms=120_000, mono_s=None)]
    assert evaluate_idle(both_missing, threshold_s=60.0) == LadderRung.STOP_AND_RETRY

    # One endpoint short is still a fallback -- a half-monotonic pair cannot
    # be subtracted meaningfully.
    anchor_missing = [
        _mono_sample(wall_ms=0, mono_s=None),
        _mono_sample(wall_ms=120_000, mono_s=101.0),
    ]
    assert evaluate_idle(anchor_missing, threshold_s=60.0) == LadderRung.STOP_AND_RETRY


def test_idle_anchor_returns_the_whole_sample_idle_since_reports():
    """``idle_anchor`` exists so the supervisor's post-nudge rebase can pin
    BOTH of the anchor's time readings. Pinning only ``moment`` while
    letting ``monotonic_s`` fall to the current tick's reading would restart
    the very elapsed count the rebase exists to preserve."""
    samples = [
        _mono_sample(wall_ms=0, mono_s=100.0, pane="a"),
        _mono_sample(wall_ms=1_000, mono_s=101.0, pane="b"),
        _mono_sample(wall_ms=2_000, mono_s=102.0, pane="b"),
    ]
    anchor = idle_anchor(samples)
    assert anchor is not None
    assert anchor.moment == idle_since(samples)
    assert anchor.monotonic_s == 101.0


def test_idle_anchor_guards_match_idle_since():
    assert idle_anchor([]) is None
    with pytest.raises(TypeError):
        idle_anchor("not-a-sample-sequence")


# --- evaluate_ceiling (Story 3.6, AD-20/AD-32) ---------------------------------


def test_evaluate_ceiling_below_the_approach_ratio_is_none():
    assert evaluate_ceiling(50, 100) == CeilingStatus.NONE
    assert evaluate_ceiling(79.9, 100) == CeilingStatus.NONE


def test_evaluate_ceiling_at_the_approach_ratio_is_approaching():
    assert evaluate_ceiling(80, 100) == CeilingStatus.APPROACHING
    assert evaluate_ceiling(99.9, 100) == CeilingStatus.APPROACHING


def test_evaluate_ceiling_at_or_above_the_limit_is_breached():
    assert evaluate_ceiling(100, 100) == CeilingStatus.BREACHED
    assert evaluate_ceiling(1_000_000, 100) == CeilingStatus.BREACHED


def test_evaluate_ceiling_zero_observed_is_none():
    assert evaluate_ceiling(0, 100) == CeilingStatus.NONE


def test_evaluate_ceiling_rejects_a_non_positive_limit():
    with pytest.raises(ValueError):
        evaluate_ceiling(50, 0)
    with pytest.raises(ValueError):
        evaluate_ceiling(50, -1)


def test_evaluate_ceiling_rejects_a_nan_limit():
    """The identical review finding ``evaluate_idle``'s own ``threshold_s``
    guard already documents and fixes: IEEE 754 makes every relational
    comparison against ``float('nan')`` false, so a bare ``<= 0`` would let
    a NaN limit sail through -- ``not (limit > 0)`` catches it."""
    with pytest.raises(ValueError):
        evaluate_ceiling(50, float("nan"))
    # Negative control: the fix must not reject anything valid.
    assert evaluate_ceiling(50, 100) == CeilingStatus.NONE


def test_evaluate_ceiling_rejects_an_infinite_limit():
    """A limit that can never be reached silently disables the ceiling --
    the same class of footgun ``core/policy.py::_valid_positive_number``
    already rejects at the policy layer; this is the core's own defense in
    depth for a direct caller."""
    with pytest.raises(ValueError):
        evaluate_ceiling(50, float("inf"))


def test_evaluate_ceiling_rejects_a_non_numeric_limit():
    with pytest.raises(TypeError):
        evaluate_ceiling(50, "100")  # type: ignore[arg-type]


def test_evaluate_ceiling_rejects_a_boolean_limit():
    """``isinstance(True, int)`` is ``True`` in Python -- a boolean limit is
    never a meaningful ceiling, the same guard ``core/policy.py``'s own
    ``_valid_positive_number``/``_valid_attempt_count`` validators apply."""
    with pytest.raises(TypeError):
        evaluate_ceiling(50, True)  # type: ignore[arg-type]


# --- evaluate_escalation (Story 3.7, AD-20/AD-45) -------------------------------


def test_not_paused_at_all_is_none():
    assert evaluate_escalation(None, None, None) == EscalationStatus.NONE


def test_paused_at_a_different_stage_is_none():
    """Any pause stage other than ``"escalation"`` -- spec-approval,
    epic-boundary, story-gate, plan/story-checkpoint, or an unrecognized
    future value -- is simply not this kind of pause."""
    for stage in ("spec-approval", "epic-boundary", "story-gate", "plan-checkpoint", "bogus"):
        assert evaluate_escalation(stage, "3-7-escalation-deferral-and-resume", "escalated") == EscalationStatus.NONE


def test_escalation_paused_with_the_task_still_escalated_is_unresolved():
    assert (
        evaluate_escalation("escalation", "3-7-escalation-deferral-and-resume", "escalated")
        == EscalationStatus.UNRESOLVED
    )


def test_escalation_paused_with_no_story_key_is_resolved():
    """A malformed/incomplete pause record -- `paused_stage` names an
    escalation but no `paused_story_key` is set -- is never `UNRESOLVED`
    (that classification's own definition requires a story key); it falls
    through to `RESOLVED`, this function's own "not this exact unresolved
    shape" catch-all for a stage-escalation pause."""
    assert evaluate_escalation("escalation", None, "escalated") == EscalationStatus.RESOLVED


def test_escalation_paused_with_the_task_no_longer_escalated_is_resolved():
    """bmad-loop's own ``rearm_escalation`` flips the task's phase back to
    ``pending`` WITHOUT clearing the pause itself -- the caller resumes the
    run separately. This is the one window `RESOLVED` describes: a human
    has re-armed the story, but the run has not yet been resumed."""
    assert (
        evaluate_escalation("escalation", "3-7-escalation-deferral-and-resume", "pending") == EscalationStatus.RESOLVED
    )


def test_escalation_paused_with_no_task_phase_at_all_is_resolved():
    """A story key is set but the task's own phase could not be read (e.g.
    the task disappeared from `state.json`'s own ``tasks`` map) --
    `task_phase=None` can never equal `"escalated"`, so this is `RESOLVED`,
    never `UNRESOLVED`: the classification is never permissive by default."""
    assert evaluate_escalation("escalation", "3-7-escalation-deferral-and-resume", None) == EscalationStatus.RESOLVED


def test_evaluate_escalation_never_raises_on_unexpected_string_values():
    """No type guard beyond ordinary equality (this function's own
    docstring) -- an unexpected string for any of the three inputs simply
    fails the equality checks it needs to, never raising."""
    assert evaluate_escalation("ESCALATION", "3.7", "escalated") == EscalationStatus.NONE
    assert (
        evaluate_escalation("escalation", "3-7-escalation-deferral-and-resume", "ESCALATED")
        == EscalationStatus.RESOLVED
    )


# --- evaluate_retry_escalation (Story 3.12, AD-20/AD-26) ------------------------


def _deferred(story_key: str, *, attempt: int = 0, review_cycle: int = 0) -> DeferredStory:
    return DeferredStory(
        story_key=story_key,
        reason=None,
        attempt=attempt,
        branch="",
        worktree_path="",
        spec_file=None,
        review_cycle=review_cycle,
    )


def test_no_deferred_stories_is_false():
    assert evaluate_retry_escalation((), max_dev_attempts=2, max_review_cycles=3) is False


def test_a_single_story_below_both_ceilings_is_false():
    deferred = (_deferred("3.6", attempt=1, review_cycle=1),)
    assert evaluate_retry_escalation(deferred, max_dev_attempts=2, max_review_cycles=3) is False


def test_a_story_at_the_max_dev_attempts_ceiling_is_true():
    deferred = (_deferred("3.6", attempt=2, review_cycle=0),)
    assert evaluate_retry_escalation(deferred, max_dev_attempts=2, max_review_cycles=3) is True


def test_a_story_over_the_max_dev_attempts_ceiling_is_true():
    deferred = (_deferred("3.6", attempt=5, review_cycle=0),)
    assert evaluate_retry_escalation(deferred, max_dev_attempts=2, max_review_cycles=3) is True


def test_a_story_at_the_max_review_cycles_ceiling_is_true():
    deferred = (_deferred("3.6", attempt=0, review_cycle=3),)
    assert evaluate_retry_escalation(deferred, max_dev_attempts=2, max_review_cycles=3) is True


def test_a_story_over_the_max_review_cycles_ceiling_is_true():
    deferred = (_deferred("3.6", attempt=0, review_cycle=9),)
    assert evaluate_retry_escalation(deferred, max_dev_attempts=2, max_review_cycles=3) is True


def test_mixed_deferred_stories_true_if_any_one_crosses_its_own_ceiling():
    """Run-level, not per-story: a single crossing story among several
    non-crossing ones is enough to trigger the whole run's escalation."""
    deferred = (
        _deferred("3.5", attempt=0, review_cycle=0),
        _deferred("3.6", attempt=2, review_cycle=0),
        _deferred("3.7", attempt=0, review_cycle=1),
    )
    assert evaluate_retry_escalation(deferred, max_dev_attempts=2, max_review_cycles=3) is True


def test_mixed_deferred_stories_false_when_none_cross_their_own_ceiling():
    deferred = (
        _deferred("3.5", attempt=1, review_cycle=2),
        _deferred("3.6", attempt=0, review_cycle=1),
    )
    assert evaluate_retry_escalation(deferred, max_dev_attempts=2, max_review_cycles=3) is False


# --- Story 28.6: graduated compression ladder (CAP-8) -------------------------


def test_evaluate_compression_ladder_is_none_below_threshold():
    assert evaluate_compression_ladder(39_000_000, 50_000_000, threshold=0.8, declared_aggressiveness="medium") is None


def test_evaluate_compression_ladder_escalates_at_threshold():
    decision = evaluate_compression_ladder(40_000_000, 50_000_000, threshold=0.8, declared_aggressiveness="low")
    assert decision is not None
    assert decision.declared == "low"
    assert decision.target == "medium"
    assert decision.threshold == 0.8


def test_evaluate_compression_ladder_reaches_high_before_breach():
    decision = evaluate_compression_ladder(49_000_000, 50_000_000, threshold=0.8, declared_aggressiveness="low")
    assert decision is not None
    assert decision.target == "high"


def test_evaluate_compression_ladder_already_high_returns_none():
    assert evaluate_compression_ladder(45_000_000, 50_000_000, threshold=0.8, declared_aggressiveness="high") is None


def test_compression_escalation_precedes_budget_stop_and_idle_ladder():
    """CAP-8 AC: ladder ordering -- compression before kill ladders."""
    assert ACTION_PRECEDENCE["compression-escalation"] < ACTION_PRECEDENCE["budget-stop"]
    assert ACTION_PRECEDENCE["compression-escalation"] < ACTION_PRECEDENCE["idle-nudge"]
    assert ACTION_PRECEDENCE["compression-escalation"] < ACTION_PRECEDENCE["idle-defer"]
    assert ACTION_PRECEDENCE["budget-warn"] < ACTION_PRECEDENCE["budget-stop"]


def test_evaluate_compression_ladder_journals_threshold_facts():
    decision = evaluate_compression_ladder(41_000_000, 50_000_000, threshold=0.8, declared_aggressiveness="medium")
    assert decision is not None
    assert decision.observed == 41_000_000
    assert decision.limit == 50_000_000
    assert decision.threshold == 0.8


def test_compression_escalation_decision_names_wire_aggressiveness_only():
    """CAP-8 AC: escalation raises wire-layer compression only -- the pure
    decision carries threshold facts and aggressiveness rungs, never a model
    tier or any gate/review skip signal."""
    decision = evaluate_compression_ladder(41_000_000, 50_000_000, threshold=0.8, declared_aggressiveness="low")
    assert decision is not None
    field_names = {f.name for f in dataclasses.fields(decision)}
    assert field_names == {"observed", "limit", "threshold", "declared", "target"}
    assert decision.target in {"low", "medium", "high"}


# =============================================================================
# Story 82.5 -- unobservable samples, redraw-proof pane comparison, and the
# monotonic usage-freshness judgement (DW-FU-3-5-6, DW-FU-3-5-9, DW-FU-3-6-5)
# =============================================================================


def _dark_sample(offset_ms: int) -> Sample:
    """A tick on which NEITHER channel was observed."""
    return Sample(moment=_T0 + timedelta(milliseconds=offset_ms), pane_content=None, log_mtime=None)


# --- Sample: which channels were observed ---------------------------------------


def test_sample_observed_flags_default_to_whether_a_reading_exists():
    sample = _sample(0, pane="text", mtime=1.0)
    assert (sample.pane_observed, sample.log_observed, sample.observable) == (True, True, True)

    pane_only = _sample(0, pane="text", mtime=None)
    assert (pane_only.pane_observed, pane_only.log_observed, pane_only.observable) == (True, False, True)

    log_only = _sample(0, pane=None, mtime=1.0)
    assert (log_only.pane_observed, log_only.log_observed, log_only.observable) == (False, True, True)

    dark = _dark_sample(0)
    assert (dark.pane_observed, dark.log_observed, dark.observable) == (False, False, False)


def test_an_empty_pane_is_an_observation_not_a_missing_one():
    """``""`` is a pane that was captured and was blank; only ``None`` is a
    capture that did not happen."""
    assert _sample(0, pane="", mtime=None).observable is True


def test_explicit_observed_flags_override_the_derived_defaults():
    sample = Sample(moment=_T0, pane_content="text", log_mtime=1.0, pane_observed=False, log_observed=False)
    assert sample.observable is False


# --- normalise_pane / shows_fresh_output -----------------------------------------


@pytest.mark.parametrize(
    "glyph",
    ["⠋", "⠿", "◐", "◓", "◴", "◷", "✢", "❋"],
    ids=[
        "braille-first",
        "braille-last",
        "quarter-first",
        "quarter-last",
        "corner-first",
        "corner-last",
        "star-first",
        "star-last",
    ],
)
def test_normalise_pane_removes_every_spinner_glyph_class(glyph):
    assert normalise_pane(f"Thinking {glyph}") == "Thinking "


def test_normalise_pane_removes_digit_runs_and_keeps_the_words():
    assert normalise_pane("Elapsed 1234s, 56 tokens") == "Elapsed s,  tokens"
    assert normalise_pane("no volatile content") == "no volatile content"


def test_two_panes_that_differ_only_in_a_counter_or_a_spinner_normalise_equal():
    assert normalise_pane("Working (12s) ⠋") == normalise_pane("Working (13s) ⠙")


def test_shows_fresh_output_ignores_a_redrawing_counter_and_spinner():
    before = Sample(moment=_T0, pane_content="Working (12s) ⠋", log_mtime=1.0)
    after = Sample(moment=_T0 + timedelta(seconds=1), pane_content="Working (13s) ⠙", log_mtime=1.0)
    assert shows_fresh_output(before, after) is False


def test_shows_fresh_output_sees_substantive_text():
    before = Sample(moment=_T0, pane_content="Working (12s) ⠋", log_mtime=1.0)
    after = Sample(moment=_T0 + timedelta(seconds=1), pane_content="Working (13s) ⠙\nRan the tests", log_mtime=1.0)
    assert shows_fresh_output(before, after) is True


def test_shows_fresh_output_still_re_arms_on_a_log_mtime_change():
    """The log channel is unchanged by the pane normalisation."""
    before = Sample(moment=_T0, pane_content="same", log_mtime=1.0)
    after = Sample(moment=_T0 + timedelta(seconds=1), pane_content="same", log_mtime=2.0)
    assert shows_fresh_output(before, after) is True


def test_shows_fresh_output_reads_an_unobserved_channel_as_no_evidence_either_way():
    seen = Sample(moment=_T0, pane_content="text", log_mtime=1.0)
    pane_dark = Sample(moment=_T0 + timedelta(seconds=1), pane_content=None, log_mtime=1.0)
    assert shows_fresh_output(seen, pane_dark) is False
    assert shows_fresh_output(pane_dark, seen) is False
    assert shows_fresh_output(_dark_sample(0), _dark_sample(1000)) is False


# --- evaluate_idle: unobservable samples hold, redraws do not re-arm -------------


def test_two_unobservable_samples_hold_the_rung_instead_of_reading_as_idleness():
    """AC 6 (DW-FU-3-5-6). ``None`` read against ``None`` compares equal, so
    two dark samples used to read as no fresh output -- maximal idleness."""
    samples = [_dark_sample(0), _dark_sample(1_000_000)]
    assert evaluate_idle(samples, threshold_s=0.1) == LadderRung.NONE
    assert evaluate_idle(samples, threshold_s=0.1, held=LadderRung.NUDGE) == LadderRung.NUDGE
    assert evaluate_idle(samples, threshold_s=0.1, held=LadderRung.STOP_AND_RETRY) == LadderRung.STOP_AND_RETRY


def test_an_unobservable_latest_sample_holds_the_rung_however_idle_the_history_was():
    samples = [_sample(0), _sample(1_000_000), _dark_sample(1_000_100)]
    assert evaluate_idle(samples, threshold_s=0.1) == LadderRung.NONE
    assert evaluate_idle(samples, threshold_s=0.1, held=LadderRung.NUDGE) == LadderRung.NUDGE
    # ...and the same history WITHOUT the dark tail does escalate.
    assert evaluate_idle(samples[:2], threshold_s=0.1, held=LadderRung.NUDGE) == LadderRung.DEFER


def test_an_empty_sequence_holds_the_rung_it_is_given():
    assert evaluate_idle([], threshold_s=1.0, held=LadderRung.STOP_AND_RETRY) == LadderRung.STOP_AND_RETRY


def test_an_observable_latest_sample_ignores_held():
    """``held`` is only what to report when there is no evidence -- never a
    floor under a real reading."""
    samples = [_sample(0), _sample(50)]
    assert evaluate_idle(samples, threshold_s=0.1, held=LadderRung.DEFER) == LadderRung.NONE


def test_evaluate_idle_rejects_a_non_rung_held():
    with pytest.raises(TypeError):
        evaluate_idle([_sample(0)], threshold_s=1.0, held="nudge")  # type: ignore[arg-type]


def test_dark_samples_are_skipped_by_the_scan_and_never_become_the_anchor():
    """A dark tick in the middle neither re-arms the window nor resets its
    origin: idleness accrues straight across the gap."""
    samples = [_sample(0), _dark_sample(100), _dark_sample(200), _sample(300)]
    assert evaluate_idle(samples, threshold_s=0.1) == LadderRung.DEFER
    anchor = idle_anchor(samples)
    assert anchor is not None and anchor.moment == samples[0].moment


def test_output_on_the_far_side_of_a_dark_gap_re_arms_by_differing_from_the_last_observed_sample():
    """The supervisor's own doctrine for a flaky capture: the gap is neither
    output nor silence, and real output after it still counts."""
    samples = [_sample(0, pane="before"), _dark_sample(100), _sample(300, pane="after")]
    assert evaluate_idle(samples, threshold_s=0.1) == LadderRung.NONE
    anchor = idle_anchor(samples)
    assert anchor is not None and anchor.moment == samples[2].moment


def test_a_pane_dark_sample_with_a_live_log_is_skipped_for_the_pane_comparison_only():
    samples = [_sample(0, pane="same"), _sample(100, pane=None, mtime=1.0), _sample(300, pane="same")]
    assert evaluate_idle(samples, threshold_s=0.1) == LadderRung.DEFER


def test_idle_since_and_idle_anchor_are_none_when_nothing_was_ever_observable():
    samples = [_dark_sample(0), _dark_sample(100)]
    assert idle_since(samples) is None
    assert idle_anchor(samples) is None


def test_panes_that_differ_only_in_a_counter_or_spinner_escalate_past_the_threshold():
    """AC 7 (DW-FU-3-5-9). The raw ``!=`` re-armed the window on every tick
    of a hung session whose CLI redraws a counter."""
    samples = [
        Sample(moment=_T0, pane_content="Running tool 1s ⠋", log_mtime=1.0),
        Sample(moment=_T0 + timedelta(milliseconds=60), pane_content="Running tool 2s ⠙", log_mtime=1.0),
        Sample(moment=_T0 + timedelta(milliseconds=120), pane_content="Running tool 3s ⠹", log_mtime=1.0),
    ]
    assert evaluate_idle(samples, threshold_s=0.1) == LadderRung.NUDGE
    assert evaluate_idle(samples, threshold_s=0.06) == LadderRung.STOP_AND_RETRY


def test_substantive_pane_output_still_re_arms_the_window():
    samples = [
        Sample(moment=_T0, pane_content="Running tool 1s", log_mtime=1.0),
        Sample(moment=_T0 + timedelta(milliseconds=500), pane_content="Running tool 2s", log_mtime=1.0),
        Sample(moment=_T0 + timedelta(milliseconds=520), pane_content="Running tool 3s\nTests passed", log_mtime=1.0),
    ]
    assert evaluate_idle(samples, threshold_s=0.1) == LadderRung.NONE


# --- judge_usage_freshness ---------------------------------------------------------

_WINDOW_S = 180 * 60.0
_NOW_S = 1_785_000_000.0


def _judge(mtime, *, wall=_NOW_S, mono=1000.0, window=_WINDOW_S, sighting=None):
    return judge_usage_freshness(mtime=mtime, wall_now_s=wall, monotonic_now_s=mono, window_s=window, sighting=sighting)


def test_a_just_written_mtime_is_fresh_and_recorded_with_its_first_sighting():
    freshness, sighting = _judge(_NOW_S - 30.0)
    assert freshness is UsageFreshness.FRESH
    assert sighting == MtimeSighting(mtime=_NOW_S - 30.0, first_seen_monotonic_s=1000.0, age_at_first_sight_s=30.0)


def test_a_file_already_older_than_the_window_when_first_seen_is_stale_at_once():
    freshness, sighting = _judge(_NOW_S - _WINDOW_S - 1.0)
    assert freshness is UsageFreshness.STALE
    assert sighting is not None and sighting.age_at_first_sight_s == _WINDOW_S + 1.0


def test_a_sample_ages_on_the_monotonic_clock_from_its_first_sighting():
    """AC 1 (DW-FU-3-6-6)/(DW-FU-3-6-5): first seen 40 minutes ago, inside a
    180-minute window -- fresh; the same sample is stale once the monotonic
    time since the sighting passes the window."""
    _, sighting = _judge(_NOW_S)
    freshness, _ = _judge(_NOW_S, wall=_NOW_S + 40 * 60.0, mono=1000.0 + 40 * 60.0, sighting=sighting)
    assert freshness is UsageFreshness.FRESH
    freshness, _ = _judge(_NOW_S, mono=1000.0 + _WINDOW_S + 1.0, sighting=sighting)
    assert freshness is UsageFreshness.STALE


def test_exactly_the_window_is_still_fresh_and_one_second_more_is_stale():
    _, sighting = _judge(_NOW_S)
    assert _judge(_NOW_S, mono=1000.0 + _WINDOW_S, sighting=sighting)[0] is UsageFreshness.FRESH
    assert _judge(_NOW_S, mono=1000.0 + _WINDOW_S + 1.0, sighting=sighting)[0] is UsageFreshness.STALE


def test_a_wall_clock_step_after_the_sighting_cannot_change_the_verdict():
    """AC 2 (DW-FU-3-6-5): the wall delta is taken ONCE, at first sight."""
    _, sighting = _judge(_NOW_S)
    forward, _ = _judge(_NOW_S, wall=_NOW_S + 3600.0 * 24, mono=1060.0, sighting=sighting)
    backward, _ = _judge(_NOW_S, wall=_NOW_S - 3600.0 * 24, mono=1060.0, sighting=sighting)
    assert forward is UsageFreshness.FRESH
    assert backward is UsageFreshness.FRESH

    _, stale_sighting = _judge(_NOW_S - 2 * _WINDOW_S)
    stepped_back, _ = _judge(_NOW_S - 2 * _WINDOW_S, wall=_NOW_S - 10 * _WINDOW_S, mono=1060.0, sighting=stale_sighting)
    assert stepped_back is UsageFreshness.STALE


def test_an_mtime_ahead_of_the_wall_clock_is_unevaluable_and_not_recorded():
    """AC 3 (DW-FU-3-6-5): no knowable age -- not fresh."""
    freshness, sighting = _judge(_NOW_S + 5.0)
    assert freshness is UsageFreshness.UNEVALUABLE
    assert sighting is None


def test_an_unevaluable_mtime_leaves_the_previous_sighting_untouched():
    _, earlier = _judge(_NOW_S - 10.0)
    freshness, sighting = _judge(_NOW_S + 500.0, sighting=earlier)
    assert freshness is UsageFreshness.UNEVALUABLE
    assert sighting is earlier


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_a_non_finite_mtime_is_unevaluable(bad):
    assert _judge(bad)[0] is UsageFreshness.UNEVALUABLE


def test_a_missing_file_is_stale_as_before():
    freshness, sighting = _judge(None)
    assert freshness is UsageFreshness.STALE
    assert sighting is None
    _, earlier = _judge(_NOW_S - 10.0)
    assert _judge(None, sighting=earlier) == (UsageFreshness.STALE, earlier)


def test_a_new_mtime_starts_a_fresh_sighting():
    """bmad-loop rewrote the file: the age restarts from the new write."""
    _, sighting = _judge(_NOW_S - 100.0)
    freshness, newer = _judge(_NOW_S + 7_200.0 - 20.0, wall=_NOW_S + 7_200.0, mono=1000.0 + 7_200.0, sighting=sighting)
    assert freshness is UsageFreshness.FRESH
    assert newer is not None
    assert newer.first_seen_monotonic_s == 1000.0 + 7_200.0
    assert newer.age_at_first_sight_s == 20.0


@pytest.mark.parametrize("bad", [0, -1.0, float("nan"), float("inf")])
def test_judge_usage_freshness_rejects_a_bad_window(bad):
    with pytest.raises(ValueError):
        _judge(_NOW_S, window=bad)


@pytest.mark.parametrize("bad", ["60", True, None])
def test_judge_usage_freshness_rejects_a_non_numeric_window(bad):
    with pytest.raises(TypeError):
        _judge(_NOW_S, window=bad)
