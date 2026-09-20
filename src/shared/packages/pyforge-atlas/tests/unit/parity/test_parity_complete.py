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
    "core": 8,  # Story 21.4 +enumerate_anaconda_main_packages (Tier-1 materializer, new-signal — AD-14, not parity-gated)
    "vcs_health": 10,  # B9 +derive_release_velocity (FR-20); B10 +classify_migration_readiness (FR-21) — new-signal, AD-14; Story 21.2 +3 external-refresh trigger nodes (§ 3.4 boundary)
    "pypi_intelligence": 17,  # Story 23.1: +5 Tier-3 refresh triggers + flag_tier3_channels
    "vulnerability": 9,  # B5 +refresh_vdb_store/+refresh_osv_offline_store; B8 +2 Basilisk (FR-19)
}

# Story B5 external-refresh assets (§ 3.4) — these write the separately-built
# external stores (vdb / OSV / mapping cache / GitHub / GitLab / Codeberg / registry /
# PyPI-JSON live-fetch stores), NOT the legacy-surface data outputs B4 parity-diffs.
# They are the § 3.4 MIGRATION BOUNDARY, so they are deliberately OUT of the parity
# harness's NODE_REGISTRY (mirrors AD-14's "not parity-gated" discipline). Story 21.2
# adds the GitHub/GitLab+Codeberg/registry/PyPI-JSON trigger nodes — same boundary as
# refresh_vdb_store.
_REFRESH_ASSETS = {
    "refresh_vdb_store",
    "refresh_osv_offline_store",
    "export_pypi_conda_map",
    "refresh_vcs_github_store",
    "refresh_vcs_host_stores",
    "refresh_vcs_registry_stores",
    "refresh_pypi_json_store",
    "refresh_discovery_homebrew_store",
    "refresh_discovery_nixpkgs_store",
    "refresh_discovery_spack_store",
    "refresh_discovery_debian_store",
    "refresh_discovery_fedora_store",
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
    # Story B10 migration-readiness classification (FR-21) — same AD-14 boundary.
    "classify_migration_readiness",
    # Story 21.4 Anaconda-main materializer (Tier 1, CAP-2) — a NEW source with no
    # legacy cf_atlas.db surface to diff against; same AD-14 additive-rider boundary.
    "enumerate_anaconda_main_packages",
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
    # The parity SURFACE is the 27 Wave-B legacy-surface nodes; the B5 refresh assets
    # (§ 3.4 boundary), the 5 Story-23.1 Tier-3 refresh triggers, and the 2 B8
    # Basilisk new-signal nodes (AD-14 additive rider) are NOT parity-diffed.
    parity_surface = all_nodes - _REFRESH_ASSETS - _NEW_SIGNAL_NODES
    assert len(parity_surface) == 27  # + flag_tier3_channels (Story 23.1)

    missing = parity_surface - set(NODE_REGISTRY)
    assert not missing, f"parity harness NODE_REGISTRY is missing pipeline nodes: {missing}"
