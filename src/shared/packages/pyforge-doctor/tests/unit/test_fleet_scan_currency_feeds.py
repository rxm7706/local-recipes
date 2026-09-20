"""``scripts/fleet_scan.py::_currency`` feeds edges — the retired ``epics→sprint`` pair.

Retired 2026-09-04 (PR #1043). The tracked sprint ledger is a GENERATED twin of the
gitignored Tier-3 feed: no frontmatter, so ``_artifact_dates`` falls through to git
last-touch, and ``sprint-ledger-sync`` writes nothing when no status changed. On an
idle station the ledger therefore cannot move, and a currency-only ``epics.md``
re-stamp produced a permanent "epics newer than sprint" finding that no honest act
could clear (scribe, 2026-09-04). "Did the ledger follow the epics?" is answered by
content by chain-completeness INV-B (epics story ids == ledger keys), so the
date-based edge is redundant where it is right and wrong where it is not.

Loads the real ``scripts/fleet_scan.py`` the same way ``sources/board.py`` does.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from pyforge.doctor.sources import board

try:
    _REPO_ROOT: Path | None = Path(__file__).resolve().parents[6]
except IndexError:
    _REPO_ROOT = None
_SCAN = (_REPO_ROOT / "scripts" / "fleet_scan.py") if _REPO_ROOT else None

pytestmark = pytest.mark.skipif(not (_SCAN and _SCAN.is_file()), reason="scripts/fleet_scan.py required")


@pytest.fixture(scope="module")
def fleet_scan():
    assert _SCAN is not None
    # the package's own loader: registers the module in sys.modules before executing it,
    # which fleet_scan's dataclasses need to resolve their annotations
    return board._load_foreign_module(_SCAN, "_fleet_scan_currency_feeds")


_TODAY = date(2026, 9, 4)


def test_epics_to_sprint_is_not_a_feeds_edge(fleet_scan) -> None:
    assert ("epics", "sprint") not in fleet_scan._FEEDS
    # the contract edges the runbook still lists are untouched
    for pair in (("spec", "prd"), ("prd", "arch"), ("arch", "epics"), ("code", "retro")):
        assert pair in fleet_scan._FEEDS


def test_idle_ledger_behind_a_currency_only_epics_restamp_is_not_stale(fleet_scan) -> None:
    # scribe on 2026-09-04: epics re-stamped today, twin last touched 2026-09-01 (> grace)
    updated_at = {"arch": "2026-09-04", "epics": "2026-09-04", "sprint": "2026-09-01"}
    out = fleet_scan._currency("pyforge-scribe", {}, updated_at, set(), _TODAY, realized=True)
    assert [f for f in out if f["kind"] == "feeds"] == []


def test_contract_edges_still_fire_past_the_grace_window(fleet_scan) -> None:
    # arch re-cut 4 days after the epics were last validated -> arch→epics fires
    updated_at = {"arch": "2026-09-04", "epics": "2026-08-31", "sprint": "2026-09-01"}
    out = fleet_scan._currency("pyforge-scribe", {}, updated_at, set(), _TODAY, realized=True)
    feeds = [f for f in out if f["kind"] == "feeds"]
    assert [(f["stage"], f["than"]) for f in feeds] == [("arch", "epics")]
