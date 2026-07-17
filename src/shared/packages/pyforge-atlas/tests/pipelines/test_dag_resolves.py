"""DAG-resolution smoke (Story B1, Task 3 / AC-1).

Proves the two pipelines auto-discover and their nodes WIRE with no procedural call
order and no dataset written by two pipelines (AD-3). This is the pytest form of the
``kedro registry list`` proof (which needs a bootstrapped project); it asserts the
same invariants offline.
"""

from __future__ import annotations

from pyforge.atlas.pipelines.core import create_pipeline as core_create
from pyforge.atlas.pipelines.pypi_intelligence import create_pipeline as pypi_create
from pyforge.atlas.pipelines.vcs_health import create_pipeline as vcs_create
from pyforge.atlas.pipelines.vulnerability import create_pipeline as vuln_create


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


# -- B2: pypi_intelligence (9 nodes) + vulnerability (5 nodes) ----------------

def test_pypi_intelligence_pipeline_has_nine_nodes():
    pypi = pypi_create()
    assert len(pypi.nodes) == 9
    assert {n.name for n in pypi.nodes} == {
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


def test_vulnerability_pipeline_has_five_nodes():
    vuln = vuln_create()
    assert len(vuln.nodes) == 5
    assert {n.name for n in vuln.nodes} == {
        "ingest_cisa_kev",
        "ingest_epss",
        "ingest_cwe_catalog",
        "summarize_vdb_vulns",
        "per_version_vulns",
    }


def test_no_dataset_is_written_by_two_pipelines_b2():
    core, vcs, pypi, vuln = core_create(), vcs_create(), pypi_create(), vuln_create()
    pipes = {"core": core, "vcs": vcs, "pypi": pypi, "vuln": vuln}
    names = list(pipes)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            assert not (pipes[a].outputs() & pipes[b].outputs()), (a, b)


def test_combined_four_pipeline_dag_resolves_topologically():
    combined = core_create() + vcs_create() + pypi_create() + vuln_create()
    # 7 core + 5 vcs + 9 pypi + 5 vuln = 26 nodes; the runner orders them from declared
    # inputs/outputs alone (no PHASES list driver, FR-2/AD-3).
    assert len(combined.nodes) == 26
    grouped = combined.grouped_nodes
    assert sum(len(g) for g in grouped) == 26


def test_pypi_cross_pipeline_edges_resolve_by_name():
    # Phase C reads core_packages_enumerated (core -> pypi_intelligence, AD-3).
    pypi = pypi_create()
    assert "core_packages_enumerated" in pypi.inputs()


def test_vulnerability_cross_pipeline_edge_resolves_by_name():
    # Phase G' reads core_version_download_history (core/Phase I -> vulnerability, AD-3).
    vuln = vuln_create()
    assert "core_version_download_history" in vuln.inputs()


def test_v_current_version_vulns_is_backed_by_per_version_vulns():
    # AC-2: the per_version_vulns output is the datastore behind the ONLY
    # query-time-correct vuln source (v_current_version_vulns).
    vuln = vuln_create()
    assert "vulnerability_package_version_vulns" in vuln.outputs()
