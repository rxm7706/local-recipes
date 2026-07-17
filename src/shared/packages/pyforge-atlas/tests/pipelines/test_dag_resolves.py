"""DAG-resolution smoke (Story B1, Task 3 / AC-1).

Proves the two pipelines auto-discover and their nodes WIRE with no procedural call
order and no dataset written by two pipelines (AD-3). This is the pytest form of the
``kedro registry list`` proof (which needs a bootstrapped project); it asserts the
same invariants offline.
"""

from __future__ import annotations

from pyforge.atlas.pipelines.core import create_pipeline as core_create
from pyforge.atlas.pipelines.vcs_health import create_pipeline as vcs_create


def test_core_pipeline_has_seven_nodes():
    core = core_create()
    assert len(core.nodes) == 7
    assert {n.name for n in core.nodes} == {
        "enumerate_conda_packages",
        "attribute_feedstocks",
        "detect_latest_status",
        "compute_downloads",
        "compute_version_download_history",
        "build_dependency_graph",
        "compute_feedstock_health",
    }


def test_vcs_health_pipeline_has_five_nodes():
    vcs = vcs_create()
    assert len(vcs.nodes) == 5
    assert {n.name for n in vcs.nodes} == {
        "enrich_maintainers",
        "detect_archived_feedstocks",
        "track_upstream_versions",
        "track_registry_versions",
        "fetch_live_health",
    }


def test_no_dataset_is_written_by_two_pipelines():
    core, vcs = core_create(), vcs_create()
    assert not (core.outputs() & vcs.outputs())


def test_combined_dag_resolves_topologically_with_no_procedural_order():
    # Pipeline.__add__ + node grouping proves the runner can order the 12 nodes
    # from declared inputs/outputs alone (no PHASES list driver).
    combined = core_create() + vcs_create()
    assert len(combined.nodes) == 12
    # grouped_nodes is the topological grouping the runner uses
    grouped = combined.grouped_nodes
    assert sum(len(g) for g in grouped) == 12


def test_phase_i_output_is_declared_by_name():
    # AC-3: Phase I is an explicit node with a declared output name so its
    # downstream consumers resolve by catalog name (AD-3).
    core = core_create()
    assert "core_version_download_history" in core.outputs()


def test_cross_pipeline_cf_graph_edge_resolves_by_name():
    # AC-1: Phase E (vcs_health) reads core_cf_graph_raw — the shared raw source
    # referenced by catalog name (AD-3).
    vcs = vcs_create()
    assert "core_cf_graph_raw" in vcs.inputs()
