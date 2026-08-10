"""Meta: the local-recipes BMAD project docs keep structural INTEGRITY.

Integrity = the broken-drift-contract class that is wrong regardless of release cadence:
  - every tracked doc has a parseable source_pin (catches the corrupt `span` frontmatter bug),
  - filing conventions are respected (sprint-change-proposals in change-history/, retros in
    retros/, no stray .patch/.bak artifacts),
  - every file under the project is classified (no doc silently escapes drift coverage).

This deliberately does NOT fail on mere *currency* drift (a doc a few releases behind the live
skill) — that is expected between syncs and is surfaced on demand by
``pixi run -e local-recipes bmad-drift-check``. The full reconciliation procedure (BMAD skills +
baseline re-stamp) lives in ``_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md``.

Story 6.9: `scripts/bmad_drift_check.py` retired into
`pyforge.doctor.sources.factory` (ported verbatim in behavior, Story 6.8) —
this test now exercises `factory.gather` directly (in-process, no
subprocess: there is no script left to shell out to) rather than running the
deleted script's own `--integrity-only` flag. HARD (the origin's own
severity) maps 1:1 onto `DoctorStatus.FAIL` (`factory.py`'s own
`_SEVERITY_TO_STATUS`), so "integrity clean" is "no FAIL-status finding" --
the equivalent of the origin's `--integrity-only` filter, expressed against
the port's own Finding stream instead of a second parsed exit code.

Portable: skips cleanly when the BMAD project or the `pyforge.doctor`
package is absent (the skill ships without either).
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
PROJECT = REPO_ROOT / "_bmad-output" / "projects" / "pyforge-marshal"

try:
    from pyforge.doctor.models import DoctorStatus
    from pyforge.doctor.sources import factory as bmad_drift_factory
except ImportError:
    bmad_drift_factory = None  # type: ignore[assignment]


@pytest.mark.skipif(
    not PROJECT.is_dir() or bmad_drift_factory is None,
    reason="pyforge-marshal BMAD project / pyforge.doctor not present (skill used standalone)",
)
def test_bmad_artifacts_integrity():
    findings = bmad_drift_factory.gather(REPO_ROOT)
    hard = [f for f in findings if f.status is DoctorStatus.FAIL]
    assert not hard, (
        "BMAD artifact integrity drift detected. Reconcile via SYNC-RUNBOOK.md.\n\n"
        + "\n".join(f"[{f.check}] {f.message}" for f in hard)
    )
