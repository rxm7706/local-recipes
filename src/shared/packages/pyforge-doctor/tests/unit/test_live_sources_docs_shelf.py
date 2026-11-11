"""Story 58.2 (spec-pyforge-doctor:CAP-97) -- the live-tree half of ``test_sources_docs_shelf.py``.

``docs_shelf.gather`` runs over the repository itself here; every test that builds its own tree stays in the
package half (``test_sources_docs_shelf.py``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus
from pyforge.doctor.sources import docs_shelf

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


# --- live-repo proof, mirroring general_docs_consistency's own discipline ---


def test_live_repo_gather_is_clean():
    """Live proof (never validate only against a fully-synthetic fixture):
    the real repo's _bmad-output/ root and air-gap cluster are already
    clean per Stories 23.5/23.2 -- this pins that a live, unmodified repo
    reports silent, not merely that a synthetic fixture does."""
    repo_root = Path(__file__).resolve().parents[6]
    findings = docs_shelf.gather(repo_root)
    assert len(findings) == 1
    assert findings[0].status == DoctorStatus.OK
