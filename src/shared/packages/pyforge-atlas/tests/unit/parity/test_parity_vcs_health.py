"""parity-diff — vcs_health pipeline fixtures (Story B1, AC-7)."""

from __future__ import annotations

import pytest

from .harness import discover_fixtures, run_fixture

_VCS = [p for p in discover_fixtures() if p.parent.name == "vcs_health"]


@pytest.mark.parametrize("fixture", _VCS, ids=lambda p: p.stem)
def test_vcs_node_matches_legacy_fixture(fixture):
    run_fixture(fixture)


def test_vcs_fixtures_exist():
    stems = {p.stem for p in _VCS}
    assert stems == {
        "enrich_maintainers",
        "detect_archived_feedstocks",
        "track_upstream_versions",
        "track_registry_versions",
        "fetch_live_health",
    }
