"""Doctor Story 58.1 (spec-pyforge-doctor:CAP-97) -- the live-tree half of
``test_sources_chain_source_spec_resolution.py``.

The herald ``DW-FU-15-1`` regression resolves its ``source_spec`` against this
repository's own tree, so it runs in the station's live-tree half; every other
resolution case builds its own tree and stays in
``test_sources_chain_source_spec_resolution.py`` (the package half).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_sources_chain_source_spec_resolution import _HERALD_DW_FU_15_1_SOURCE_SPEC, _HERALD_SPEC_REL

from pyforge.doctor.sources import chain

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def _repo_root() -> Path:
    """This repository's root, resolved when a test runs (never at import time)."""
    root = Path(__file__).resolve().parents[6]
    assert (root / ".claude").is_dir(), f"{root} is not the local-recipes checkout root (no .claude/)"
    return root


def test_herald_dw_fu_15_1_live_regression() -> None:
    """Regression fixture built from herald's real ``DW-FU-15-1`` ledger row."""
    repo_root = _repo_root()
    resolution = chain.resolve_source_spec(
        _HERALD_DW_FU_15_1_SOURCE_SPEC,
        repo_root=repo_root,
        project="pyforge-herald",
    )

    assert resolution.status is chain.SourceSpecResolutionStatus.PRESENT
    assert resolution.resolution_basis == "project_root"
    expected = repo_root / "_bmad-output/projects/pyforge-herald" / _HERALD_SPEC_REL
    assert resolution.resolved_path == expected.resolve()
    assert chain.source_spec_mechanical_still_open_eligible(resolution) is False
