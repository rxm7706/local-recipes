"""Doctor Story 58.1 (spec-pyforge-doctor:CAP-97) -- the live-tree half of
``test_sources_status_body_open_questions.py`` (``sources.status_body_consistency`` CAP-2 (Story 21.13)).

The live charter case runs ``gather_open_questions_reconcile`` over this
repository's Specs, so it runs in the station's live-tree half; the fixture
tests stay in ``test_sources_status_body_open_questions.py`` (the package half).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.doctor.sources import status_body_consistency as sbc

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def test_gather_live_charter_case():
    repo_root = Path(__file__).resolve().parents[6]
    findings = sbc.gather_open_questions_reconcile(repo_root)
    charter_hits = [
        f
        for f in findings
        if f.check == sbc._CHECK_OPEN_QUESTIONS and f.evidence.get("path", "").endswith("spec-pyforge-charter/SPEC.md")
    ]
    assert not charter_hits, "live charter was reconciled 2026-09-09; fixture covers the firing case"
    scanned = next(
        (f.evidence.get("scanned_specs") for f in findings if "scanned_specs" in f.evidence),
        None,
    )
    assert scanned and scanned > 0
