"""Doctor Story 58.1 (spec-pyforge-doctor:CAP-97) -- the live-tree half of
``test_sources_status_body_promissory.py`` (``sources.status_body_consistency`` CAP-3 (Story 21.14)).

The two live cases measure and gather promissory language over this
repository's Dreams and Specs, so they run in the station's live-tree half; the fixture
tests stay in ``test_sources_status_body_promissory.py`` (the package half).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus
from pyforge.doctor.sources import status_body_consistency as sbc

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def test_gather_live_herald_pair_and_zero_false_positives():
    """Re-measured 2026-09-18 (was herald_pair_fired == 1): the Dream side of
    the known pair was cleaned too -- zero live promissory hits, still zero
    false positives, still `accepted`. Fixture tests above still prove the
    detector fires.

    Re-measured again 2026-09-19: the live scan is now fully clean -- the last
    non-promissory finding (an `unparseable` WARN for the unquoted `title:`
    in `docs/dreams/pyforge-mason-recipe-validator.md`) was reconciled by PR
    #1493 -- so `gather_promissory_language` emits its clean-state OK summary
    (same `check`, `status: OK`, see `test_gather_measured_and_rejected_when_
    not_accepted` for the shape). That summary is the *absence* of a hit, so
    the assertion filters on the WARN status a real hit carries; a bare
    `check ==` filter read the summary as a hit and redded the station gate on
    `main` the moment the tree got clean (doctor dispatch 28.1, MRS-GATE-001)."""
    repo_root = Path(__file__).resolve().parents[6]
    measurement = sbc.measure_promissory_language_precision(repo_root)
    assert measurement.herald_pair_fired == 0
    assert measurement.false_positive_documents == 0
    assert measurement.accepted is True
    assert sbc.PROMISSORY_LANGUAGE_ACCEPTED is True

    findings = sbc.gather_promissory_language(repo_root)
    promissory = [f for f in findings if f.check == sbc._CHECK_PROMISSORY and f.status is DoctorStatus.WARN]
    assert promissory == []
    # Every finding the live gather returns is either the clean-state OK
    # summary or a non-promissory WARN (an unparseable/unreadable document);
    # never a promissory hit.
    assert all(f.status is DoctorStatus.OK or f.check != sbc._CHECK_PROMISSORY for f in findings)


def test_gather_live_includes_cap1_and_cap3_together():
    """Re-measured 2026-09-18: CAP-1/CAP-3 live hits are zero (fleet cleaned).
    Combined gather still returns other status-body checks; fixture tests
    cover CAP-1/CAP-3 firing."""
    repo_root = Path(__file__).resolve().parents[6]
    findings = sbc.gather(repo_root)
    checks = {f.check for f in findings}
    assert sbc._CHECK_PROGRESS not in checks
    assert sbc._CHECK_PROMISSORY not in checks
    assert checks  # still reports other live status-body findings
