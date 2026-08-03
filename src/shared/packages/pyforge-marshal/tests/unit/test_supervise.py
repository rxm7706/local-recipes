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
from pyforge.marshal.core.supervise import LadderRung, Sample, evaluate_idle, rung_index

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


def test_evaluate_idle_rejects_a_non_numeric_threshold():
    with pytest.raises(TypeError):
        evaluate_idle([_sample(0)], threshold_s="60")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        evaluate_idle([_sample(0)], threshold_s=True)  # type: ignore[arg-type]


def test_sample_is_a_plain_frozen_dataclass():
    sample = _sample(0)
    with pytest.raises(AttributeError):
        sample.pane_content = "mutated"  # type: ignore[misc]
