"""Meta: the local-recipes BMAD project docs keep structural INTEGRITY.

Integrity = the broken-drift-contract class that is wrong regardless of release cadence:
  - every tracked doc has a parseable source_pin (catches the corrupt `span` frontmatter bug),
  - filing conventions are respected (sprint-change-proposals in change-history/, retros in
    retros/, no stray .patch/.bak artifacts),
  - every file under the project is classified (no doc silently escapes drift coverage).

This deliberately does NOT fail on mere *currency* drift (a doc a few releases behind the live
skill) — that is expected between syncs and is surfaced on demand by
``pixi run -e local-recipes bmad-drift-check``. The full reconciliation procedure (BMAD skills +
baseline re-stamp) lives in ``_bmad-output/projects/local-recipes/SYNC-RUNBOOK.md``.

Portable: skips cleanly when the BMAD project is absent (the skill ships without it).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT = REPO_ROOT / "scripts" / "bmad_drift_check.py"
PROJECT = REPO_ROOT / "_bmad-output" / "projects" / "local-recipes"


@pytest.mark.skipif(
    not PROJECT.is_dir() or not SCRIPT.is_file(),
    reason="local-recipes BMAD project / drift-check script not present (skill used standalone)",
)
def test_bmad_artifacts_integrity():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--integrity-only"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    assert result.returncode == 0, (
        "BMAD artifact integrity drift detected. Reconcile via SYNC-RUNBOOK.md "
        "(some issues auto-fix: `pixi run -e local-recipes bmad-drift-check -- --fix`).\n\n"
        + result.stdout
        + result.stderr
    )
