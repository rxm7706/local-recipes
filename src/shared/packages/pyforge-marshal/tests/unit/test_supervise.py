"""Unit tests for ``pyforge.marshal.core.supervise`` (Story 3.5,
architecture spine AD-9/AD-20) -- ``evaluate_idle``'s full ladder-transition
matrix, driven entirely through synthetic ``Sample`` sequences with
millisecond-scale ``datetime`` deltas (AD-20's own "every supervisor
behaviour has a test that runs in milliseconds"). No port, no clock, no
subprocess anywhere in this file -- ``evaluate_idle`` is pure.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pyforge.marshal.core.supervise import (
    CeilingStatus,
    LadderRung,
    Sample,
    evaluate_ceiling,
    evaluate_idle,
    idle_anchor,
    idle_since,
    rung_at,
    rung_index,
)

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


def _mono_sample(
    *, wall_ms: int, mono_s: float | None, pane: str | None = "same"
) -> Sample:
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
