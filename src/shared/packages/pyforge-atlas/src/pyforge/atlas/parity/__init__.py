"""Parity core (Story B4) — the pure, IO-free verification surface.

B4 proves the Kedro pipeline is output-equivalent to the legacy orchestrator on
the legacy-surface (``v_actionable_packages``-family) views, so the legacy
orchestrator + ``phase_state`` can be retired on RECORDED EVIDENCE + human
sign-off (AD-19, FR-4) — never on a diff that silently passes a regression.

This package holds only the **pure** logic so it survives the whole-package
``test_no_inline_io`` + AD-1 scans (pandas / dataclasses / stdlib only — NO
``sqlite3`` / HTTP / ``dagster`` / ``kedro_mcp``). The IO-bearing credentialed
comparator + the recapture tooling live in ``tests/parity/`` (which legitimately
reads a legacy SQLite ``cf_atlas.db``), mirroring ``harness.py``'s home.

Modules:
- ``frame_diff``     — the TIGHTENED frame-diff engine (DW-B1-1 part b): column-SET
  equality both directions + dtype tightening where the JSON/Parquet round-trip
  allows. Shared by the fixture harness AND the credentialed comparator.
- ``legacy_surface`` — the frozen registry of the legacy-surface views (Q1) +
  the AD-14 exclusion of the B8/B9/B10 new-signal datasets.
- ``evidence``       — the parity-evidence record + the retirement gate (AC-3):
  legacy retirement is allowed ONLY after every legacy-surface view has a
  credentialed, zero-material-drift, human-signed evidence record.
"""

from __future__ import annotations

from .evidence import (
    ParityEvidenceRecord,
    RetirementDecision,
    may_retire_legacy,
)
from .frame_diff import (
    FrameDiffResult,
    assert_frames_equal,
    compare_frames,
)
from .legacy_surface import (
    EXCLUDED_NEW_SIGNAL_DATASETS,
    LEGACY_SURFACE_VIEWS,
    LegacySurfaceView,
    legacy_surface_view_names,
)

__all__ = [
    "EXCLUDED_NEW_SIGNAL_DATASETS",
    "LEGACY_SURFACE_VIEWS",
    "FrameDiffResult",
    "LegacySurfaceView",
    "ParityEvidenceRecord",
    "RetirementDecision",
    "assert_frames_equal",
    "compare_frames",
    "legacy_surface_view_names",
    "may_retire_legacy",
]
