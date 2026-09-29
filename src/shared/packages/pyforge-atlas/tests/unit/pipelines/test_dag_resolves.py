"""DAG-resolution smoke (Story B1, Task 3 / AC-1).

Proves the two pipelines auto-discover and their nodes WIRE with no procedural call
order and no dataset written by two pipelines (AD-3). This is the pytest form of the
``kedro registry list`` proof (which needs a bootstrapped project); it asserts the
same invariants offline.
"""

from __future__ import annotations

from pyforge.atlas.pipelines.artifactory_downloads import create_pipeline as artifactory_create
from pyforge.atlas.pipelines.core import create_pipeline as core_create
from pyforge.atlas.pipelines.derived_artifacts import create_pipeline as derived_create
from pyforge.atlas.pipelines.pypi_intelligence import create_pipeline as pypi_create
from pyforge.atlas.pipelines.seed_gaps import create_pipeline as seed_create
from pyforge.atlas.pipelines.universal_sbom import create_pipeline as sbom_create
from pyforge.atlas.pipelines.upstream_discovery import create_pipeline as discovery_create
from pyforge.atlas.pipelines.vcs_health import create_pipeline as vcs_create
from pyforge.atlas.pipelines.vulnerability import create_pipeline as vuln_create


def test_core_pipeline_has_eight_nodes():
    # Story 21.4 added enumerate_anaconda_main_packages (the Tier-1 Anaconda main
    # channeldata materializer — the only consumer of core_anaconda_main_channeldata_raw).
    core = core_create()
    assert len(core.nodes) == 8
    assert {n.name for n in core.nodes} == {
        "enumerate_conda_packages",
        "enumerate_anaconda_main_packages",
        "attribute_feedstocks",
        "detect_latest_status",
        "compute_downloads",
        "compute_version_download_history",
        "build_dependency_graph",
        "compute_feedstock_health",
    }


def test_vcs_health_pipeline_has_ten_nodes():
    # B9 added derive_release_velocity (FR-20); B10 added classify_migration_readiness
    # (FR-21) — both NEW-SIGNAL, not parity-gated (AD-14). Story 21.2 added the three
    # external-refresh trigger nodes (single writers of the GitHub/GitLab/Codeberg/
    # registry live-fetch stores — mirrors refresh_vdb_store/refresh_osv_offline_store).
    vcs = vcs_create()
    assert len(vcs.nodes) == 10
    assert {n.name for n in vcs.nodes} == {
        "refresh_vcs_github_store",
        "refresh_vcs_host_stores",
        "refresh_vcs_registry_stores",
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
    # Pipeline.__add__ + node grouping proves the runner can order the nodes from
    # declared inputs/outputs alone (no PHASES list driver). B9's
    # derive_release_velocity reads the pypi_intelligence Phase H/Phase C datasets as
    # FREE inputs here (produced in the full 7-pipeline DAG) — Kedro allows free
    # inputs. Story 21.2 added 3 external-refresh trigger nodes to vcs_health (14 -> 17);
    # Story 21.4 added enumerate_anaconda_main_packages to core (17 -> 18).
    combined = core_create() + vcs_create()
    assert len(combined.nodes) == 18
    # grouped_nodes is the topological grouping the runner uses
    grouped = combined.grouped_nodes
    assert sum(len(g) for g in grouped) == 18


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


def test_pypi_intelligence_pipeline_has_seventeen_nodes():
    # B5 added export_pypi_conda_map (the § 3.4 update-mapping-cache Q6 export shim).
    # Story 21.2 review fix #6 added refresh_pypi_json_store (the pypi_json_raw
    # external-refresh trigger — same § 3.4 boundary as export_pypi_conda_map).
    # Story 23.1 added five Tier-3 external-refresh triggers + flag_tier3_channels (+6).
    pypi = pypi_create()
    assert len(pypi.nodes) == 17
    assert {n.name for n in pypi.nodes} == {
        "refresh_pypi_json_store",
        "map_pypi_conda",
        "match_source_urls",
        "enumerate_pypi_universe",
        "fetch_pypi_current_versions",
        "snapshot_pypi_serials",
        "fetch_pypi_downloads",
        "flag_cross_channel",
        "refresh_discovery_homebrew_store",
        "refresh_discovery_nixpkgs_store",
        "refresh_discovery_spack_store",
        "refresh_discovery_debian_store",
        "refresh_discovery_fedora_store",
        "flag_tier3_channels",
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


def test_derived_artifacts_pipeline_has_seven_nodes():
    # B7: the full-universe CycloneDX BOM producer (AD-15 14-day freshness).
    # Story 23.8 added build_inventory_universe (the workbook-free metrics universe).
    # Story 23.3 added derive_basilisk_vuln_rollup + assign_inventory_priority.
    # Story 23.4 added build_inventory_verified_packages + build_inventory_aoss_free_queue.
    # Story 23.5 added build_identity_complete_export.
    derived = derived_create()
    assert len(derived.nodes) == 7
    assert {n.name for n in derived.nodes} == {
        "build_universe_sbom",
        "build_inventory_universe",
        "derive_basilisk_vuln_rollup",
        "assign_inventory_priority",
        "build_inventory_verified_packages",
        "build_inventory_aoss_free_queue",
        "build_identity_complete_export",
    }


def test_combined_seven_pipeline_dag_resolves_topologically():
    combined = (
        core_create() + vcs_create() + pypi_create() + vuln_create() + seed_create() + sbom_create() + derived_create()
    )
    # 8 core + 10 vcs + 17 pypi + 9 vuln + 4 seed_gaps + 4 universal_sbom
    # + 7 derived_artifacts = 59 nodes (Story 23.5: derived_artifacts 6 -> 7).
    assert len(combined.nodes) == 59
    grouped = combined.grouped_nodes
    assert sum(len(g) for g in grouped) == 59


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


# -- Story 21.4/21.5: upstream_discovery (9 nodes) + Tier-1/Tier-2 single-writer wiring -----


def test_upstream_discovery_pipeline_has_fourteen_nodes():
    # Stories 13.1/13.2/13.4 landed the original four; Story 21.4 added the three Tier-1
    # external-refresh triggers (single writers of the discovery_*_raw stores); Story
    # 21.5 added the two Tier-2 nodes (refresh_about_maintainers +
    # join_enterprise_conda_maintainers); Story 21.6 added the CAP-3 identity join's
    # three external-refresh triggers + two pure join/shape nodes.
    discovery = discovery_create()
    assert len(discovery.nodes) == 14
    assert {n.name for n in discovery.nodes} == {
        "refresh_trending_candidates",
        "classify_trending_candidates",
        "load_org_audit_candidates",
        "classify_org_audit_candidates",
        "refresh_anaconda_dist_2026x",
        "refresh_basilisk_packages",
        "refresh_aoss_premium_python",
        "refresh_about_maintainers",
        "join_enterprise_conda_maintainers",
        "refresh_purl_associator_mappings",
        "refresh_openteams_board",
        "refresh_staged_recipes_prs",
        "build_identity_packages_primary",
        "build_identity_export_parquet",
    }


def test_tier_1_external_refresh_stores_have_exactly_one_writer_each():
    # The Story 21.2 pipeline-dormancy lesson, pinned: each save()-gated Tier-1 store is
    # written by EXACTLY ONE trigger node across the full DAG; the tracked-seed entry
    # (discovery_aoss_free_python_raw) is deliberately written by none.
    combined = (
        core_create()
        + vcs_create()
        + pypi_create()
        + vuln_create()
        + seed_create()
        + sbom_create()
        + derived_create()
        + discovery_create()
    )
    writers = {
        "discovery_anaconda_dist_2026x_raw": "refresh_anaconda_dist_2026x",
        "discovery_basilisk_packages_raw": "refresh_basilisk_packages",
        "discovery_aoss_premium_python_raw": "refresh_aoss_premium_python",
        "discovery_about_maintainers_raw": "refresh_about_maintainers",
        "core_anaconda_main_packages": "enumerate_anaconda_main_packages",
        "purl_associator_mappings_raw": "refresh_purl_associator_mappings",
        "openteams_project_1_board_raw": "refresh_openteams_board",
        "discovery_staged_recipes_prs_raw": "refresh_staged_recipes_prs",
        "identity_packages_primary": "build_identity_packages_primary",
        "identity_export_parquet": "build_identity_export_parquet",
    }
    for store, expected in writers.items():
        producers = [n.name for n in combined.nodes if store in n.outputs]
        assert producers == [expected], (store, producers)
    assert not [n.name for n in combined.nodes if "discovery_aoss_free_python_raw" in n.outputs]
    # the materializer is the ONLY consumer of the live Anaconda main raw entry
    consumers = [n.name for n in combined.nodes if "core_anaconda_main_channeldata_raw" in n.inputs]
    assert consumers == ["enumerate_anaconda_main_packages"]


# -- Story 21.5 + 23.2: artifactory_downloads (6 nodes) ------------------------------------


def test_artifactory_downloads_pipeline_has_six_nodes():
    # Story 15.3: three nodes; Story 21.5: +project_artifactory_names;
    # Story 23.2: +fetch_artifactory_consumption + build_enterprise_jfrog_consumption.
    artifactory = artifactory_create()
    assert len(artifactory.nodes) == 6
    assert {n.name for n in artifactory.nodes} == {
        "fetch_artifactory_downloads",
        "join_artifactory_identity",
        "format_artifactory_purl_export",
        "project_artifactory_names",
        "fetch_artifactory_consumption",
        "build_enterprise_jfrog_consumption",
    }


def test_enterprise_jfrog_names_has_exactly_one_writer():
    artifactory = artifactory_create()
    producers = [n.name for n in artifactory.nodes if "enterprise_jfrog_names" in n.outputs]
    assert producers == ["project_artifactory_names"]


# -- Story 21.6 (review finding, patch): DAG-completeness for build_identity_packages_primary's
# cross-pipeline free inputs -----------------------------------------------------------------


# Entries upstream_discovery's free inputs legitimately have NO producer NODE
# for — raw/seed sources whose load() reads a git-tracked seed or the live
# filesystem directly (mirrors discovery_aoss_free_python_raw's own
# no-trigger-node shape, asserted separately in
# test_tier_1_external_refresh_stores_have_exactly_one_writer_each above).
_NO_PRODUCER_NEEDED = {"discovery_curated_groups_seed", "discovery_local_recipes_raw"}


def test_upstream_discovery_free_inputs_are_all_produced_by_the_bootstrap_pipeline_set():
    """``build_identity_packages_primary`` reads several free (cross-pipeline)
    inputs — ``enterprise_jfrog_names`` (artifactory_downloads),
    ``core_feedstock_attribution`` / ``core_packages_enumerated`` (core), and
    ``pypi_universe`` / ``pypi_conda_mapping`` / ``pypi_intelligence_enriched``
    (pypi_intelligence). Each is a plain ``pandas.ParquetDataset`` with NO AD-13
    missing-file degrade, so a fresh-clone run needs every one of them actually
    produced by SOME node in the same combined DAG — the exact
    ``pyforge-atlas-bootstrap`` pixi task's pipeline list (core, pypi_intelligence,
    vulnerability, vcs_health, upstream_discovery, derived_artifacts, seed_gaps,
    artifactory_downloads). This pins that completeness so a future edit reverting
    the pixi.toml artifactory_downloads addition (or dropping any other producer)
    fails loudly here instead of only at a live, credentialed `kedro run`.

    ``Pipeline.outputs()`` is the FREE-output set (produced but never consumed
    WITHIN that same pipeline) — every one of these inputs IS consumed again
    internally by a later node in its owning pipeline (e.g. ``pypi_universe`` is
    also read by ``flag_cross_channel``), so it never appears there. The
    "was this produced by ANY node at all" question is ``all_outputs()``."""
    combined = (
        core_create()
        + vcs_create()
        + pypi_create()
        + vuln_create()
        + seed_create()
        + sbom_create()
        + derived_create()
        + discovery_create()
        + artifactory_create()
    )
    combined_all_outputs = combined.all_outputs()
    free_inputs = discovery_create().inputs() - discovery_create().outputs()
    # params:* entries are parameter bindings, never produced by a node's outputs=
    # — excluded from the "must be produced somewhere" check on that basis alone.
    unresolved = {
        name
        for name in (free_inputs - combined_all_outputs)
        if not name.startswith("params:") and name not in _NO_PRODUCER_NEEDED
    }
    assert not unresolved, (
        f"upstream_discovery free input(s) with no producer in the bootstrap pipeline set: {unresolved}"
    )
    # Named assertion for the specific Story 21.6 dependency the finding called
    # out — a clearer failure message than the set-diff above if this regresses.
    assert "enterprise_jfrog_names" in (discovery_create() + artifactory_create()).all_outputs()
