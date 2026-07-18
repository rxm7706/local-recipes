"""DAG-resolution smoke (Story B1, Task 3 / AC-1).

Proves the two pipelines auto-discover and their nodes WIRE with no procedural call
order and no dataset written by two pipelines (AD-3). This is the pytest form of the
``kedro registry list`` proof (which needs a bootstrapped project); it asserts the
same invariants offline.
"""

from __future__ import annotations

from pyforge.atlas.pipelines.core import create_pipeline as core_create
from pyforge.atlas.pipelines.derived_artifacts import create_pipeline as derived_create
from pyforge.atlas.pipelines.pypi_intelligence import create_pipeline as pypi_create
from pyforge.atlas.pipelines.seed_gaps import create_pipeline as seed_create
from pyforge.atlas.pipelines.universal_sbom import create_pipeline as sbom_create
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


def test_vcs_health_pipeline_has_seven_nodes():
    # B9 added derive_release_velocity (FR-20); B10 added classify_migration_readiness
    # (FR-21) — both NEW-SIGNAL, not parity-gated (AD-14).
    vcs = vcs_create()
    assert len(vcs.nodes) == 7
    assert {n.name for n in vcs.nodes} == {
        "enrich_maintainers",
        "detect_archived_feedstocks",
        "track_upstream_versions",
        "track_registry_versions",
        "fetch_live_health",
        "derive_release_velocity",
        "classify_migration_readiness",
    }


def test_no_dataset_is_written_by_two_pipelines():
    core, vcs = core_create(), vcs_create()
    assert not (core.outputs() & vcs.outputs())


def test_combined_dag_resolves_topologically_with_no_procedural_order():
    # Pipeline.__add__ + node grouping proves the runner can order the 13 nodes
    # from declared inputs/outputs alone (no PHASES list driver). B9's
    # derive_release_velocity reads the pypi_intelligence Phase H/Phase C datasets as
    # FREE inputs here (produced in the full 7-pipeline DAG) — Kedro allows free inputs.
    combined = core_create() + vcs_create()
    assert len(combined.nodes) == 14
    # grouped_nodes is the topological grouping the runner uses
    grouped = combined.grouped_nodes
    assert sum(len(g) for g in grouped) == 14


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

def test_pypi_intelligence_pipeline_has_ten_nodes():
    # B5 added export_pypi_conda_map (the § 3.4 update-mapping-cache Q6 export shim).
    pypi = pypi_create()
    assert len(pypi.nodes) == 10
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
        "export_pypi_conda_map",
    }


def test_vulnerability_pipeline_has_nine_nodes():
    # B5 added refresh_vdb_store + refresh_osv_offline_store (§ 3.4 refresh assets).
    # B8 added the two Basilisk ingestion nodes (FR-19; ADDITIVE, not parity-gated AD-14).
    vuln = vuln_create()
    assert len(vuln.nodes) == 9
    assert {n.name for n in vuln.nodes} == {
        "refresh_vdb_store",
        "refresh_osv_offline_store",
        "ingest_cisa_kev",
        "ingest_epss",
        "ingest_cwe_catalog",
        "summarize_vdb_vulns",
        "per_version_vulns",
        "ingest_basilisk_advisories",
        "fetch_basilisk_details",
    }


def test_no_dataset_is_written_by_two_pipelines_b2():
    core, vcs, pypi, vuln = core_create(), vcs_create(), pypi_create(), vuln_create()
    pipes = {"core": core, "vcs": vcs, "pypi": pypi, "vuln": vuln}
    names = list(pipes)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            assert not (pipes[a].outputs() & pipes[b].outputs()), (a, b)


def test_seed_gaps_pipeline_has_four_nodes():
    # B6: the four READ-ONLY seed-freshness suggesters; mapping-gap is NOT one of
    # them (it is a writer, stays in pypi_intelligence — AC-4).
    seed = seed_create()
    assert len(seed.nodes) == 4
    assert {n.name for n in seed.nodes} == {
        "report_lts_registry_gap",
        "report_cwe_seed_gap",
        "report_spdx_schema_gap",
        "report_license_map_gap",
    }
    assert "mapping-gap" not in {n.name for n in seed.nodes}


def test_universal_sbom_pipeline_has_four_nodes():
    # B7: § 4.10 intake -> CycloneDX normalize -> six-bucket match. F4: + the deptry
    # hygiene node + the SINGLE-producer four-axis policy gate (AD-12). Names FROZEN.
    sbom = sbom_create()
    assert len(sbom.nodes) == 4
    assert {n.name for n in sbom.nodes} == {
        "normalize_intake_to_cyclonedx",
        "match_against_universe",
        "run_dependency_hygiene",
        "assemble_and_gate",
    }


def test_derived_artifacts_pipeline_has_one_node():
    # B7: the full-universe CycloneDX BOM producer (AD-15 14-day freshness).
    derived = derived_create()
    assert len(derived.nodes) == 1
    assert {n.name for n in derived.nodes} == {"build_universe_sbom"}


def test_combined_seven_pipeline_dag_resolves_topologically():
    combined = (
        core_create()
        + vcs_create()
        + pypi_create()
        + vuln_create()
        + seed_create()
        + sbom_create()
        + derived_create()
    )
    # 7 core + 7 vcs + 10 pypi + 9 vuln + 4 seed_gaps + 4 universal_sbom
    # + 1 derived_artifacts = 42 nodes (B7 added the SBOM intake/match + universe
    # BOM; B8 added the two Basilisk ingestion nodes, FR-19; B9 added
    # derive_release_velocity, FR-20; B10 added classify_migration_readiness, FR-21;
    # F4 added the deptry hygiene node + the four-axis policy gate, FR-16/FR-18).
    # The runner orders them from declared inputs/outputs alone (no PHASES list driver,
    # FR-2/AD-3).
    assert len(combined.nodes) == 42
    grouped = combined.grouped_nodes
    assert sum(len(g) for g in grouped) == 42


def test_no_dataset_is_written_by_two_pipelines_b7():
    # AD-3: derived_universe_sbom is produced ONLY by derived_artifacts; the
    # entry-scoped sbom_* outputs ONLY by universal_sbom (no double-write).
    pipes = {
        "core": core_create(),
        "vcs": vcs_create(),
        "pypi": pypi_create(),
        "vuln": vuln_create(),
        "seed": seed_create(),
        "sbom": sbom_create(),
        "derived": derived_create(),
    }
    names = list(pipes)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            assert not (pipes[a].outputs() & pipes[b].outputs()), (a, b)


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
