"""Doctor Story 58.1 (spec-pyforge-doctor:CAP-97) -- the live-tree half of
``test_sources_status_body_consistency.py`` (``sources.status_body_consistency`` CAP-1 (Story 21.12)).

The live pin runs ``gather_progress_phrase`` over this repository's Dreams and
Specs, so it runs in the station's live-tree half; the fixture
tests stay in ``test_sources_status_body_consistency.py`` (the package half).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.doctor.sources import status_body_consistency as sbc

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def test_gather_live_dream_and_spec_progress_phrases():
    """Re-measured 2026-09-18: the live fleet no longer carries a
    progress-phrase contradiction (herald Dream cleaned; scribe already
    clean). Fixture tests above still prove the detector fires; this live
    pin only asserts the fleet stays silent."""
    repo_root = Path(__file__).resolve().parents[6]
    findings = sbc.gather_progress_phrase(repo_root)
    progress = [f for f in findings if f.check == sbc._CHECK_PROGRESS]
    assert progress == []
