"""Doctor Story 58.1 (spec-pyforge-doctor:CAP-97) -- the live-tree half of
``test_sources_one_chain.py``.

These tests run the chain-sprawl and fr-without-cap gathers on this checkout
and pin that neither FAILs at the ruling snapshot (the conformance leg each
story names), and read the live roster's closed fold-exemption list, so they
run in the station's live-tree half.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus
from pyforge.doctor.sources import one_chain

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def _live_root() -> Path:
    """This repository's root, resolved when a test runs (never at import time)."""
    root = Path(__file__).resolve().parents[6]
    assert (root / ".claude").is_dir(), f"{root} is not the local-recipes checkout root (no .claude/)"
    return root


# --- live tree (conformance legs) --------------------------------------------


def test_live_tree_chain_sprawl_has_no_fail_at_ruling_snapshot() -> None:
    root = _live_root()
    findings = one_chain.gather_chain_sprawl(root)
    fails = [f for f in findings if f.status is DoctorStatus.FAIL]
    assert not fails, [f.message for f in fails]
    assert not any(f.check == "chain-sprawl-no-baseline" for f in findings)


def test_live_tree_fr_without_cap_has_no_fail_at_ruling_snapshot() -> None:
    """No FAIL on this checkout: every structural finding the tree still
    carries is keyed in fr-baseline.json `findings` (Story 50.1 ratchet)."""
    root = _live_root()
    findings = one_chain.gather_fr_without_cap(root)
    fails = [f for f in findings if f.status is DoctorStatus.FAIL]
    assert not fails, [f.message for f in fails]
    assert not any(f.check == "fr-without-cap-no-baseline" for f in findings)
    assert not any(f.check == "fr-baseline-stale" for f in findings), "prune fr-baseline.json"


def test_live_roster_declares_the_closed_list() -> None:
    root = _live_root()
    data = json.loads((root / "docs/governance/guild-roster.json").read_text())
    assert data["fold_exemptions"] == [
        "different-owner",
        "different-lifecycle",
        "cross-station-seam",
        "governance",
    ]
