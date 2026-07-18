"""parity-diff — pypi_intelligence pipeline fixtures (Story B2, AC-6).

**SHAPE-ONLY SEEDS.** These fixtures prove the harness dispatch + each node's output
schema on a representative input; ``expected`` is the node's own transform, NOT a
credentialed legacy capture (DW-B1-1 honesty — a hand-authored legacy value risks
encoding an implementer belief, the downloads_source='merged' incident). A green
``parity-diff`` here is NOT evidence of legacy parity; B4 replaces these with credentialed
legacy snapshots at the attended event (AD-19). See PARITY_NOTES.md.
"""

from __future__ import annotations

import pytest

from .harness import discover_fixtures, run_fixture

_PYPI = [p for p in discover_fixtures() if p.parent.name == "pypi_intelligence"]


@pytest.mark.parametrize("fixture", _PYPI, ids=lambda p: p.stem)
def test_pypi_node_matches_seed_fixture(fixture):
    run_fixture(fixture)


def test_pypi_fixtures_exist_for_all_nine_nodes():
    stems = {p.stem for p in _PYPI}
    assert stems == {
        "map_pypi_conda",
        "match_source_urls",
        "enumerate_pypi_universe",
        "fetch_pypi_current_versions",
        "snapshot_pypi_serials",
        "fetch_pypi_downloads",
        "flag_cross_channel",
        "enrich_pypi_intelligence",
        "score_pypi_readiness",
    }


def test_pypi_fixtures_are_flagged_shape_only():
    # DW-B1-1: each seed MUST declare its provenance so B4 knows to recapture.
    import json

    for path in _PYPI:
        spec = json.loads(path.read_text(encoding="utf-8"))
        assert spec.get("provenance") == "shape-only-seed-B2-needs-B4-recapture", path.name
