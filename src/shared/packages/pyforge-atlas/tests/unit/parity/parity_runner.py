"""The credentialed-parity-run comparator (Story B4, AC-1/AC-2).

Compares the Kedro Parquet outputs of the legacy-surface (Q1) views against the
legacy ``cf_atlas.db`` tables and reports row-count + value drift per view,
emitting a ``ParityEvidenceRecord`` for each.

Two modes:

- **FIXTURE** (default, ``legacy_db=None``) — offline, synthetic, non-credentialed
  (AD-11). Builds a tiny synthetic legacy surface + matching synthetic Kedro
  frames and runs the exact same diff/evidence path. This is the SHIPPED in-loop
  gate: it proves the comparator's plumbing (row-count + value drift + benign
  classification + evidence emission) WITHOUT any real DB. A green fixture-mode
  run is NOT evidence of legacy parity (PARITY_NOTES.md).
- **CREDENTIALED** (``legacy_db=<path>`` + a ``kedro_frame_provider``) — the
  ATTENDED wave-boundary event (AD-19). Reads ``SELECT * FROM <view>`` from the
  real read-only ``cf_atlas.db`` and diffs against the caller-composed Kedro
  frame. The per-view Kedro composition (join keys, the actionable filter) is
  finalized against the real schema at the event (DW-B4) — hence the provider is
  caller-supplied, never defaulted.

This module lives in ``tests/parity/`` (NOT the package) because it reads a legacy
SQLite DB — ``sqlite3`` is on the package ``IO_DENYLIST``; ``tests/`` is not
scanned. It reuses the PURE parity core (``pyforge.atlas.parity``) for the diff,
the legacy-surface registry, and the evidence record. **No credentials / live DB
are ever touched in tests** — the credentialed path is exercised only via a
synthetic in-memory SQLite fixture DB + a synthetic Kedro provider.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Sequence
from contextlib import closing

import pandas as pd

from pyforge.atlas.parity import (
    LEGACY_SURFACE_VIEWS,
    ParityEvidenceRecord,
    compare_frames,
    legacy_surface_view_names,
)
from pyforge.atlas.parity.evidence import RUN_MODE_CREDENTIALED, RUN_MODE_FIXTURE

# A provider maps a legacy-surface view name -> the composed Kedro-side frame.
KedroFrameProvider = Callable[[str], pd.DataFrame]


def diff_view(
    view: str,
    legacy_frame: pd.DataFrame,
    kedro_frame: pd.DataFrame,
    *,
    run_mode: str,
    benign_columns: Sequence[str] = (),
    legacy_db_ref: str | None = None,
    kedro_store_ref: str | None = None,
    captured_at: str | None = None,
) -> ParityEvidenceRecord:
    """Diff one view's legacy frame vs its Kedro frame and build the evidence
    record. ``benign_columns`` (e.g. per-row timestamps) are DROPPED before the
    value diff and recorded in ``benign_diffs`` — the Q1 "timestamp/ordering-only
    diffs documented benign" rule (row order is already handled by the engine's
    order-independent sort). ``material_drift`` is set iff a difference remains
    after the benign columns are excluded.
    """
    benign = [c for c in benign_columns if c in legacy_frame.columns or c in kedro_frame.columns]
    legacy_cmp = legacy_frame.drop(columns=[c for c in benign if c in legacy_frame.columns])
    kedro_cmp = kedro_frame.drop(columns=[c for c in benign if c in kedro_frame.columns])

    result = compare_frames(kedro_cmp, legacy_cmp)
    benign_diffs = (
        (f"excluded timestamp/ordering-only columns: {benign}",) if benign else ()
    )
    return ParityEvidenceRecord(
        view=view,
        legacy_row_count=int(legacy_frame.shape[0]),
        kedro_row_count=int(kedro_frame.shape[0]),
        material_drift=not result.ok,
        run_mode=run_mode,
        benign_diffs=benign_diffs,
        legacy_db_ref=legacy_db_ref,
        kedro_store_ref=kedro_store_ref,
        captured_at=captured_at,
        human_sign_off=None,  # NEVER auto-signed — set by a human at the event
        detail="" if result.ok else result.detail,
    )


def _read_legacy_view(conn: sqlite3.Connection, view: str) -> pd.DataFrame:
    # `view` is drawn from our frozen LEGACY_SURFACE_VIEWS registry, never user
    # input — no injection surface.
    if view not in legacy_surface_view_names():
        raise KeyError(f"{view!r} is not a legacy-surface parity view")
    return pd.read_sql_query(f"SELECT * FROM {view}", conn)


# --- synthetic fixture surface (the in-loop gate; NO real data) ------------

def _synthetic_pair(view: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A tiny synthetic (legacy, kedro) pair for one view — identical by
    construction (zero drift) so fixture mode proves the happy path. Includes a
    benign ``captured_at`` column that differs, to exercise the benign-diff
    classification."""
    base = [
        {"conda_name": "numpy", "n": 3, "score": 1.5, "captured_at": "2026-07-17T00:00:00Z"},
        {"conda_name": "pandas", "n": 1, "score": 2.0, "captured_at": "2026-07-17T00:00:00Z"},
    ]
    legacy = pd.DataFrame(base)
    kedro = pd.DataFrame(
        [{**r, "captured_at": "2026-07-17T09:99:99Z"} for r in base]  # benign drift
    )
    return legacy, kedro


def run_parity(
    *,
    legacy_db: str | None = None,
    kedro_frame_provider: KedroFrameProvider | None = None,
    kedro_store: str | None = None,
    view_names: Sequence[str] | None = None,
    benign_columns: Sequence[str] = ("captured_at", "fetched_at", "built_at"),
) -> list[ParityEvidenceRecord]:
    """Run the parity comparison across the legacy-surface views.

    FIXTURE mode (``legacy_db is None``): synthetic, offline — the shipped gate.
    CREDENTIALED mode (``legacy_db`` given): requires ``kedro_frame_provider``
    (the per-view Kedro composition, finalized at the attended event). Reads the
    real DB read-only.
    """
    views = list(view_names) if view_names is not None else list(legacy_surface_view_names())
    # Never fabricate evidence for a view outside the frozen legacy-surface
    # registry — a bogus view name must fail, not produce a green synthetic pair.
    unknown = [v for v in views if v not in legacy_surface_view_names()]
    if unknown:
        raise KeyError(f"not legacy-surface parity views: {unknown}")

    if legacy_db is None:
        # FIXTURE MODE — synthetic, no DB, no credentials.
        records: list[ParityEvidenceRecord] = []
        for view in views:
            legacy_frame, kedro_frame = _synthetic_pair(view)
            records.append(
                diff_view(
                    view,
                    legacy_frame,
                    kedro_frame,
                    run_mode=RUN_MODE_FIXTURE,
                    benign_columns=benign_columns,
                )
            )
        return records

    # CREDENTIALED MODE — attended, real cf_atlas.db.
    if kedro_frame_provider is None:
        raise ValueError(
            "credentialed mode requires a kedro_frame_provider that composes each "
            "legacy-surface view from its Kedro Parquet datasets (finalized at the "
            "attended event, DW-B4); it is never defaulted so the loop can never "
            "silently fabricate a credentialed run."
        )
    records = []
    # Read-only connection to the real legacy DB.
    uri = f"file:{legacy_db}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as conn:
        for view in views:
            legacy_frame = _read_legacy_view(conn, view)
            kedro_frame = kedro_frame_provider(view)
            records.append(
                diff_view(
                    view,
                    legacy_frame,
                    kedro_frame,
                    run_mode=RUN_MODE_CREDENTIALED,
                    benign_columns=benign_columns,
                    legacy_db_ref=str(legacy_db),
                    kedro_store_ref=str(kedro_store) if kedro_store else None,
                )
            )
    return records


def build_synthetic_legacy_db(conn: sqlite3.Connection) -> None:
    """Create the 5 legacy-surface views as tables with synthetic rows in a
    caller-supplied SQLite connection — for exercising CREDENTIALED mode WITHOUT
    a real ``cf_atlas.db`` (tests only). Each view's synthetic legacy frame equals
    its ``_synthetic_pair`` legacy side so a matching synthetic provider yields
    zero material drift."""
    for v in LEGACY_SURFACE_VIEWS:
        legacy_frame, _ = _synthetic_pair(v.view)
        legacy_frame.to_sql(v.view, conn, if_exists="replace", index=False)
    conn.commit()
