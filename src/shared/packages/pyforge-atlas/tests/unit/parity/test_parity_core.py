"""parity-diff — core pipeline fixtures (Story B1, AC-7)."""

from __future__ import annotations

import pytest

from .harness import discover_fixtures, run_fixture

_CORE = [p for p in discover_fixtures() if p.parent.name == "core"]


@pytest.mark.parametrize("fixture", _CORE, ids=lambda p: p.stem)
def test_core_node_matches_legacy_fixture(fixture):
    run_fixture(fixture)


def test_core_fixtures_exist():
    # the 7 core nodes each have a captured fixture (compute_downloads = 1 file,
    # multi-output verified inside run_fixture)
    stems = {p.stem for p in _CORE}
    assert stems == {
        "enumerate_conda_packages",
        "attribute_feedstocks",
        "detect_latest_status",
        "compute_downloads",
        "compute_version_download_history",
        "build_dependency_graph",
        "compute_feedstock_health",
    }
