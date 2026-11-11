"""Story 58.2 (spec-pyforge-doctor:CAP-97) -- the live-tree half of ``test_sources_general_docs_consistency.py``.

``general_docs_consistency.gather`` runs over the repository itself here; every test that builds its own tree (the
``pre``/``post`` fixtures included) stays in the package half (``test_sources_general_docs_consistency.py``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus
from pyforge.doctor.sources import general_docs_consistency

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def test_live_repo_gather_no_longer_fires_after_story_22_1_landed():
    """Live proof, mirroring Story 21.9's discipline (never validate only
    against a fully-synthetic fixture): at authoring time this detector fired
    against the real, live Story 22.1 contradictions (doctor's own
    README.md/AGENTS.md). Story 22.1 has since landed and corrected both --
    the stronger live proof now available is that the corrected repo produces
    neither warn, confirmed against the real files, not a frozen copy. The
    `pre`/`post` fixtures (test_pre_story_22_1_doctor_readme_fires_against_
    skill_brief / test_post_story_22_1_doctor_readme_is_silent and their
    AGENTS/Herald counterparts in test_sources_general_docs_consistency.py)
    remain the authoritative, stable regression coverage for the fire/no-fire
    behavior itself."""
    repo_root = Path(__file__).resolve().parents[6]
    findings = general_docs_consistency.gather(repo_root)
    warns = [f for f in findings if f.status == DoctorStatus.WARN]
    checks = {f.check for f in warns}
    assert "general-docs-station-gate-advisory" not in checks
    assert "general-docs-agents-herald-marshal" not in checks
