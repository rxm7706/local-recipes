"""Doctor Story 58.1 (spec-pyforge-doctor:CAP-97) -- the live-tree half of
``test_sources_status_body_status_comment.py`` (``sources.status_body_consistency`` CAP-4 (Story 21.15)).

The live case runs ``gather_status_comment_reconcile`` over this repository's
Dreams and ledgers, so it runs in the station's live-tree half; the fixture
tests stay in ``test_sources_status_body_status_comment.py`` (the package half).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.doctor.sources import status_body_consistency as sbc

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def test_gather_live_bmad_method_version_drift_case():
    # Was a live contradiction (comment said "Epic 14 backlog" while
    # pyforge-doctor's own epic-14 row read `done`) — fixed 2026-09-11 in
    # both directions: the resolver now scopes to the document's OWN project
    # (it had been silently checking against pyforge-atlas's epic-14 instead,
    # a cross-project key collision — pyforge-atlas sorts before
    # pyforge-doctor), and the comment itself was corrected to match.
    # Since 2026-10-26 (doctor Story 53.1, spec-one-chain-per-station CAP-11)
    # the Dream lives at archive/docs/dreams/bmad-method-version-drift.md, which
    # this source does not scan, so the assertion now guards against the file
    # returning to docs/dreams/ with the contradiction: it passes vacuously
    # while the Dream stays archived.
    repo_root = Path(__file__).resolve().parents[6]
    findings = sbc.gather_status_comment_reconcile(repo_root)
    hits = [f for f in findings if f.evidence.get("path") == "docs/dreams/bmad-method-version-drift.md"]
    assert not hits, f"expected no findings, got: {hits}"
