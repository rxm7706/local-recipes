"""parity-diff harness — B3 completeness assertion (Story B3, Task 5).

B1 began / B2 extended / B3 completes the parity-diff build (B4 consumes);
this pins registry ⊇ pipeline-nodes so B4 gets a provably-complete
harness. Frame-diff under-check tightening stays B4's (DW-B1-1).
"""

from __future__ import annotations

import importlib

from .harness import NODE_REGISTRY

_PIPELINES = ("core", "vcs_health", "pypi_intelligence", "vulnerability")
_EXPECTED_NODE_COUNTS = {
    "core": 7,
    "vcs_health": 5,
    "pypi_intelligence": 9,
    "vulnerability": 5,
}


def _pipeline_node_names() -> dict[str, set[str]]:
    names: dict[str, set[str]] = {}
    for name in _PIPELINES:
        mod = importlib.import_module(f"pyforge.atlas.pipelines.{name}.pipeline")
        names[name] = {n.name for n in mod.create_pipeline().nodes}
    return names


def test_harness_build_completes_at_b3():
    per_pipeline = _pipeline_node_names()
    for pipeline, expected in _EXPECTED_NODE_COUNTS.items():
        assert len(per_pipeline[pipeline]) == expected, pipeline

    all_nodes = set().union(*per_pipeline.values())
    assert len(all_nodes) == 26  # the 26 Wave-B nodes

    missing = all_nodes - set(NODE_REGISTRY)
    assert not missing, (
        f"parity harness NODE_REGISTRY is missing pipeline nodes: {missing}"
    )
