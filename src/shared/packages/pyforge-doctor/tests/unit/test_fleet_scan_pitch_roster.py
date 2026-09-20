"""``scripts/fleet_scan.py::scan_pitch`` must never score a documented
non-pipeline presentation twin against the 6-artifact deck-family standard.

Regression for Story 23.2 (spec-design-sync-loop CAP-2): adding
``presentations/six-quarter-roadmap/`` and ``presentations/llm-knowledge-bases/``
(local twins that do not follow the deck-family build pipeline, per each
one's own README) made ``scan_pitch()`` walk into them and report a
permanent, meaningless partial score (``0/6`` and ``1/6`` respectively) --
exactly the problem ``_NOT_A_DECK`` was introduced to prevent for
``presentations/_design-systems/``. Verified live 2026-09-18 (before this
fix): ``scan_pitch()`` returned cards for both new twins with garbled
titles (``"PyForge Llm-knowledge-bases"``, ``"PyForge Six-quarter-roadmap"``).

Loads the real ``scripts/fleet_scan.py`` the same way
``test_fleet_scan_currency_feeds.py`` does, and runs ``scan_pitch()``
against this repo's real, tracked ``presentations/`` tree -- there is no
seam to inject a temp directory, since ``fleet_scan.py`` resolves
``REPO_ROOT`` itself.
"""

from __future__ import annotations

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
    return board._load_foreign_module(_SCAN, "_fleet_scan_pitch_roster")


_NON_PIPELINE_TWINS = frozenset({"_design-systems", "six-quarter-roadmap", "llm-knowledge-bases"})


def test_not_a_deck_covers_every_documented_non_pipeline_twin(fleet_scan) -> None:
    assert _NON_PIPELINE_TWINS <= fleet_scan._NOT_A_DECK


def test_scan_pitch_never_scores_a_non_pipeline_twin(fleet_scan) -> None:
    slugs = {card["slug"] for card in fleet_scan.scan_pitch()}
    assert slugs.isdisjoint(_NON_PIPELINE_TWINS)
