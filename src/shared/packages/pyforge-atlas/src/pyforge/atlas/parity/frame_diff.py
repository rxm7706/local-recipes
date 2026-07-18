"""The tightened parity frame-diff engine (Story B4, DW-B1-1 part b).

The B1 ``harness.py`` frame-diff UNDER-CHECKS two ways, manufacturing false
confidence (DW-B1-1 part b, HIGH):

1. It derives the compared column set from the EXPECTED frame only
   (``cols = list(exp.columns)``), then projects both frames to it — so a node
   that grows a **spurious column** is never compared on that column and PASSES.
2. It calls ``assert_frame_equal(..., check_dtype=False)`` — so an
   **int64-vs-float64** regression PASSES.

This module is the fix. ``compare_frames`` / ``assert_frames_equal``:

- assert **column-SET equality both directions** (a column in actual∖expected is
  a spurious-column regression; a column in expected∖actual is a dropped-column
  regression) BEFORE projecting; and
- **tighten dtype where the JSON round-trip allows**: both frames are normalized
  through the identical JSON representation the fixtures use, then compared with
  ``check_dtype=True``. ``json``'s int/float distinction survives the round-trip
  (``1``→int64, ``1.0``→float64), so a real int→float regression BITES — while
  genuinely round-trip-ambiguous cases (an all-null column → object either side,
  JSON ``null`` → NaN) stay consistent on both sides and do NOT false-fail.

The order-independent, null-unified comparison (project → unify nulls → stable
sort by a stringified key → reset index) is preserved from the B1 harness so the
diff stays about CONTENT, not row order. Both the fixture harness (via
``assert_frames_equal``) and the B4 credentialed comparator (via
``compare_frames`` → ``FrameDiffResult``) share this ONE engine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pandas as pd
from pandas.testing import assert_frame_equal


def _clean_null(v):
    """Uniform null representation (``None``) so JSON ``null`` and pandas
    NaN/NA compare equal. List cells pass through (``pd.isna`` on a list is
    ambiguous). Ported verbatim from the B1 harness."""
    if isinstance(v, list):
        return v
    return None if v is None or pd.isna(v) else v


def _json_normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Round-trip a frame through the SAME JSON representation the fixtures use
    (``expected`` is ``pd.DataFrame(json.loads(text))``). Applying it to BOTH
    sides makes the dtype comparison apples-to-apples: the JSON int/float
    distinction is preserved (so int→float BITES) while all-null/NaN columns
    coerce identically on both sides (so they do NOT false-fail).

    ``DataFrame.to_json`` natively handles numpy scalar types (``np.int64`` etc.)
    that a bare ``json.dumps(df.to_dict())`` would choke on."""
    if df.shape[1] == 0:
        return df.copy()
    return pd.DataFrame(json.loads(df.to_json(orient="records")))


def _normalize(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Project to ``columns``, unify nulls, sort deterministically, reset index
    — so the diff is order-independent. List-valued columns are excluded from the
    sort KEY (unhashable) but still compared (via a stringified key)."""
    proj = df[[c for c in columns if c in df.columns]].copy()
    proj = proj.map(_clean_null)
    if len(proj.columns):
        key = proj.map(repr)
        order = key.sort_values(list(proj.columns), kind="stable").index
        proj = proj.loc[order]
    return proj.reset_index(drop=True)


@dataclass(frozen=True)
class FrameDiffResult:
    """Structured outcome of a parity frame-diff. The credentialed comparator
    builds ``ParityEvidenceRecord`` row counts + material-drift verdicts from
    this; the fixture harness calls ``raise_for_status`` to keep assert-on-diff.
    """

    ok: bool
    row_count_actual: int
    row_count_expected: int
    spurious_columns: tuple[str, ...] = ()
    missing_columns: tuple[str, ...] = ()
    value_or_dtype_mismatch: bool = False
    detail: str = ""
    # Names of columns whose values/dtype differed, when derivable.
    mismatch_columns: tuple[str, ...] = field(default=())

    @property
    def row_count_delta(self) -> int:
        return self.row_count_actual - self.row_count_expected

    def raise_for_status(self) -> None:
        if not self.ok:
            raise AssertionError(self.detail)


def compare_frames(
    actual: pd.DataFrame,
    expected: pd.DataFrame,
) -> FrameDiffResult:
    """Tightened parity diff of ``actual`` vs ``expected``. Returns a
    ``FrameDiffResult`` (does NOT raise) so callers can record evidence.

    Always compares on the FULL expected column set — there is deliberately no
    ``columns`` subset knob (a subset that omitted a differing column would let
    value drift pass silently, defeating the whole point of the gate).

    Contract:
    - **Column-SET equality both directions.** Any column in ``actual`` not in
      ``expected`` (spurious) OR in ``expected`` not in ``actual`` (dropped)
      fails. When ``expected`` is a columnless empty frame (a JSON ``[]`` seed),
      the column-set check is skipped and only row-count parity is checked.
    - **Value + dtype equality** on the compared columns after identical JSON
      normalization + order-independent sort.
    """
    row_a = int(actual.shape[0])
    row_e = int(expected.shape[0])

    a_cols = list(actual.columns)
    e_cols = list(expected.columns)
    expected_is_columnless_empty = len(e_cols) == 0 and row_e == 0

    # --- column-set equality (both directions) ---
    if not expected_is_columnless_empty:
        spurious = tuple(sorted(set(a_cols) - set(e_cols)))
        missing = tuple(sorted(set(e_cols) - set(a_cols)))
        if spurious or missing:
            parts = []
            if spurious:
                parts.append(f"spurious column(s) in actual: {list(spurious)}")
            if missing:
                parts.append(f"column(s) missing from actual: {list(missing)}")
            return FrameDiffResult(
                ok=False,
                row_count_actual=row_a,
                row_count_expected=row_e,
                spurious_columns=spurious,
                missing_columns=missing,
                detail="column-set mismatch — " + "; ".join(parts),
            )
    else:
        # Nothing captured beyond row count; the only meaningful check is that
        # actual is empty too.
        if row_a != 0:
            return FrameDiffResult(
                ok=False,
                row_count_actual=row_a,
                row_count_expected=row_e,
                detail=(
                    f"row-count mismatch: expected empty frame, actual has {row_a} row(s)"
                ),
            )
        return FrameDiffResult(ok=True, row_count_actual=0, row_count_expected=0)

    # --- value + dtype equality (order-independent) ---
    cols = list(e_cols)
    a_norm = _normalize(_json_normalize(actual), cols)
    e_norm = _normalize(_json_normalize(expected), cols)
    try:
        assert_frame_equal(a_norm, e_norm, check_dtype=True, check_like=False)
    except AssertionError as exc:
        mismatch_cols = tuple(
            c
            for c in cols
            if c in a_norm.columns
            and c in e_norm.columns
            and (
                a_norm[c].dtype != e_norm[c].dtype
                or not a_norm[c].equals(e_norm[c])
            )
        )
        # Fallback: if the raised diff was a shape/row-count mismatch (no
        # per-column value diff derivable), still report the compared columns
        # so the evidence detail is never misleadingly empty.
        if not mismatch_cols:
            mismatch_cols = tuple(cols)
        return FrameDiffResult(
            ok=False,
            row_count_actual=row_a,
            row_count_expected=row_e,
            value_or_dtype_mismatch=True,
            mismatch_columns=mismatch_cols,
            detail=f"value/dtype mismatch on columns {list(mismatch_cols)}: {exc}",
        )

    return FrameDiffResult(ok=True, row_count_actual=row_a, row_count_expected=row_e)


def assert_frames_equal(actual: pd.DataFrame, expected: pd.DataFrame) -> None:
    """Raise ``AssertionError`` on any parity diff — the fixture-harness entry
    point (replaces the B1 harness's inline ``assert_frame_equal`` call)."""
    compare_frames(actual, expected).raise_for_status()
