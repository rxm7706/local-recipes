"""The bite-proof tests for the tightened parity diff (Story B4, DW-B1-1 part b).

Proof that the tightened ``compare_frames`` now catches the two regressions the
B1 harness let pass silently (spurious column, int64-vs-float64) — AND does NOT
false-fail on the genuinely round-trip-ambiguous cases (all-null column, JSON
null → NaN). If any of these regress, the parity gate stops biting.
"""

from __future__ import annotations

import pandas as pd
import pytest

from pyforge.atlas.parity import assert_frames_equal, compare_frames


def test_bites_on_spurious_column():
    """A node growing a column the expected frame does not have MUST fail
    (the B1 under-check derived columns from EXPECTED only, so this passed)."""
    expected = pd.DataFrame([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}])
    actual = pd.DataFrame(
        [{"a": 1, "b": "x", "sneaky": 9}, {"a": 2, "b": "y", "sneaky": 9}]
    )
    result = compare_frames(actual, expected)
    assert not result.ok
    assert "sneaky" in result.spurious_columns
    with pytest.raises(AssertionError, match="spurious column"):
        assert_frames_equal(actual, expected)


def test_bites_on_dropped_column():
    """A node dropping an expected column MUST fail (both-directions check)."""
    expected = pd.DataFrame([{"a": 1, "b": "x"}])
    actual = pd.DataFrame([{"a": 1}])
    result = compare_frames(actual, expected)
    assert not result.ok
    assert "b" in result.missing_columns


def test_bites_on_int_vs_float_dtype():
    """int64-vs-float64 on identical values MUST fail (B1 used
    check_dtype=False, so this passed)."""
    expected = pd.DataFrame([{"n": 1}, {"n": 2}])  # int64
    actual = pd.DataFrame([{"n": 1.0}, {"n": 2.0}])  # float64
    result = compare_frames(actual, expected)
    assert not result.ok
    assert result.value_or_dtype_mismatch
    assert "n" in result.mismatch_columns


def test_bites_on_value_change():
    """A changed value MUST fail."""
    expected = pd.DataFrame([{"a": 1, "b": "x"}])
    actual = pd.DataFrame([{"a": 1, "b": "CHANGED"}])
    assert not compare_frames(actual, expected).ok


def test_passes_on_genuine_match_order_independent():
    """Identical content in a different row order MUST pass (the diff is about
    content, not order)."""
    expected = pd.DataFrame([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}])
    actual = pd.DataFrame([{"a": 2, "b": "y"}, {"a": 1, "b": "x"}])
    result = compare_frames(actual, expected)
    assert result.ok, result.detail
    assert_frames_equal(actual, expected)  # does not raise


def test_does_not_false_fail_on_all_null_column():
    """An all-null column coerces identically on both sides (object/float) —
    MUST NOT false-fail (this is the 'where the round-trip allows' tolerance)."""
    expected = pd.DataFrame([{"a": 1, "note": None}, {"a": 2, "note": None}])
    actual = pd.DataFrame([{"a": 1, "note": None}, {"a": 2, "note": None}])
    assert compare_frames(actual, expected).ok


def test_does_not_false_fail_on_json_null_vs_nan():
    """JSON ``null`` and pandas NaN must compare equal (null unification)."""
    expected = pd.DataFrame([{"a": 1, "x": None}, {"a": 2, "x": 3.0}])
    actual = pd.DataFrame([{"a": 1, "x": float("nan")}, {"a": 2, "x": 3.0}])
    assert compare_frames(actual, expected).ok


def test_does_not_false_fail_on_list_valued_columns():
    """List cells (subdirs/maintainers) compare by content, unhashable-safe."""
    expected = pd.DataFrame(
        [{"pkg": "a", "subdirs": ["linux-64", "noarch"]}, {"pkg": "b", "subdirs": []}]
    )
    actual = pd.DataFrame(
        [{"pkg": "b", "subdirs": []}, {"pkg": "a", "subdirs": ["linux-64", "noarch"]}]
    )
    assert compare_frames(actual, expected).ok


def test_row_counts_reported():
    """FrameDiffResult carries row counts so the credentialed comparator can
    build row-count-drift evidence."""
    expected = pd.DataFrame([{"a": 1}, {"a": 2}, {"a": 3}])
    actual = pd.DataFrame([{"a": 1}, {"a": 2}])
    result = compare_frames(actual, expected)
    assert result.row_count_actual == 2
    assert result.row_count_expected == 3
    assert result.row_count_delta == -1


def test_empty_expected_requires_empty_actual():
    """A columnless empty expected frame (JSON ``[]``) passes only when actual is
    also empty; a non-empty actual is a real diff."""
    empty = pd.DataFrame([])
    assert compare_frames(pd.DataFrame([]), empty).ok
    assert not compare_frames(pd.DataFrame([{"a": 1}]), empty).ok
