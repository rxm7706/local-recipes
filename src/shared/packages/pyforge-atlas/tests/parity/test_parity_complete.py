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
    "vcs_health": 6,  # B9 added derive_release_velocity (FR-20; new-signal, AD-14)
    "pypi_intelligence": 10,  # B5 added export_pypi_conda_map (§ 3.4 refresh asset)
    "vulnerability": 9,  # B5 +refresh_vdb_store/+refresh_osv_offline_store; B8 +2 Basilisk (FR-19)
}

# Story B5 external-refresh assets (§ 3.4) — these write the three separately-built
# external stores (vdb / OSV / mapping cache), NOT the legacy-surface data outputs B4
# parity-diffs. They are the § 3.4 MIGRATION BOUNDARY, so they are deliberately OUT of
# the parity harness's NODE_REGISTRY (mirrors AD-14's "not parity-gated" discipline).
_REFRESH_ASSETS = {
    "refresh_vdb_store",
    "refresh_osv_offline_store",
    "export_pypi_conda_map",
}

# Story B8 Basilisk ingestion nodes (FR-19) — ADDITIVE new-signal riders, NEVER
# parity-gated (AD-14; the output `vulnerability_basilisk_advisories` is in B4's
# EXCLUDED_NEW_SIGNAL_DATASETS). Out of the parity harness's NODE_REGISTRY exactly
# like the § 3.4 refresh-asset boundary above.
_NEW_SIGNAL_NODES = {
    "ingest_basilisk_advisories",
    "fetch_basilisk_details",
    # Story B9 release-velocity node (FR-20) — same AD-14 additive-rider boundary.
    "derive_release_velocity",
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
    # The parity SURFACE is the 26 Wave-B legacy-surface nodes; the 3 B5 refresh assets
    # (§ 3.4 boundary) and the 2 B8 Basilisk new-signal nodes (AD-14 additive rider) are
    # NOT parity-diffed.
    parity_surface = all_nodes - _REFRESH_ASSETS - _NEW_SIGNAL_NODES
    assert len(parity_surface) == 26  # the 26 Wave-B parity-surface nodes

    missing = parity_surface - set(NODE_REGISTRY)
    assert not missing, (
        f"parity harness NODE_REGISTRY is missing pipeline nodes: {missing}"
    )
