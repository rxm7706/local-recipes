---
title: "Test Architecture — pyforge-atlas"
type: test-architecture
generator: bmad_tea_playwright.py
generator_version: 2.1.0
status: generated
station: atlas
source_fingerprint: 2db5c540fa304382
story_count: 143
test_file_count: 187
coverage_target_unit: ">=80%"
coverage_target_integration: ">=70%"
---

# Test Architecture — PyForge Atlas

This document is **machine-generated** by `bmad_tea_playwright.py` (v2.1.0). Do not hand-edit; re-run the generator after epics or tests change.

## Executive Summary

- **Station:** `pyforge-atlas`
- **Stories parsed:** 143
- **Epics parsed:** 38
- **Test files inventoried:** 187 under `src/shared/packages/pyforge-atlas/tests/`
- **Frameworks:** pytest (unit/integration/meta) + Playwright where present
- **Coverage targets:** unit ≥80%, integration ≥70% (gated by Story 19.3)
- **Source fingerprint:** `2db5c540fa304382`

## Risk Assessment

### High-risk epics

- Epic 35: VCS and registry fetches cover the full universe, credentialed on opt-in (spec-pyforge-atlas CAP-65, FR-73)

### Medium-risk epics

- Epic 1: Wave 0 — Legacy Translation via Skill Forge (SKF)
- Epic 2: Wave A — `nebi` Scaffold & Catalog
- Epic 3: Wave B — Pipeline Node Porting & MCP Integration
- Epic 4: Wave C — Orchestration & Visualization
- Epic 5: Wave D — Semantic Layer & Dashboards
- Epic 6: Wave E — A2A Integration, Lineage & Observability
- Epic 7: Wave F — The DuckDB Singularity
- Epic 8: Wave G — WebAssembly Portability & Event-Driven Sensors
- Epic 9: Wave H — The AI Software Factory & Karpathy Wiki
- Epic 10: Post-Audit Remediation — Round-3 Findings
- Epic 11: Kedro-org tooling — audit, publish, decide
- Epic 12: Upstream discovery — what to package next
- Epic 13: Atlas query dashboards — hand-someone-a-link views
- Epic 14: Artifactory download intelligence — mock-first AQL
- Epic 15: Wagtail corporate brain — the narrow DW-H3 contract
- Epic 16: The packaging-inventory intake engine, governed
- Epic 17: Kedro hooks on the shared contract
- Epic 18: Atlas owns its skill, persona, and one portal job
- Epic 19: The query plane meets the query surfaces
- Epic 20: Kedro catalog expansion — self-contained inventory data plane
- Epic 21: Vizro parity with identity canvases
- Epic 22: Complete inventory export — zero deferred
- Epic 23: Atlas builds its MCP face with `mcp-builder`
- Epic 24: Turn on what is built — atlas's realization-gate effect stories
- Epic 25: Atlas keeps each scanned repo's dependency history (spec-pyforge-atlas CAP-61)
- Epic 27: Phase 4+5 of the deferral burn-down — atlas's open medium and low deferrals, fixed
- Epic 28: The live-attach fixture Postgres starts under any basetemp (fix under spec-pyforge-atlas CAP-6)
- Epic 29: The range test server records each response before the client can read it (fix under spec-pyforge-atlas CAP-16)
- Epic 30: The DAG export and the Vizro boards reach Pages as workflow artifacts (spec-pyforge-atlas CAP-62, CAP-63)
- Epic 31: Atlas passes mypy in `pyforge-foundry-full`, and a lane keeps it so (fix under spec-pyforge-atlas CAP-20)
- Epic 32: The DAG export builds in CI, and a failed build fails its task (fix under spec-pyforge-atlas CAP-62)
- Epic 33: The atlas CLI reaches the verbs its contracts name, from any directory (fix under spec-pyforge-atlas CAP-9)
- Epic 34: A plain run fills every dataset a public source serves (spec-pyforge-atlas CAP-64, FR-72)
- Epic 36: Basilisk, the OpenTeams identity sources and the estate source (spec-pyforge-atlas CAP-66..CAP-68, FR-74..FR-76)
- Epic 37: The Vizro boards read what the pipelines write, on Pages too (spec-pyforge-atlas CAP-63 amended, CAP-69, FR-71, FR-77)
- Epic 38: The semantic store has its upload times and archived flag (spec-pyforge-atlas CAP-69, FR-77)

### Low-risk epics

- Epic 26: The factory-status page stops reading the retired intake-spec tier (spec-one-chain-per-station CAP-11)

## Test Inventory

| Relative path | Level | Linked stories |
|---------------|-------|----------------|
| `src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_dashboard_controls.py` | integration | none observed |
| `src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_dashboard_dryrun.py` | integration | none observed |
| `src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_dashboard_e2e.py` | integration | none observed |
| `src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_dashboard_provenance.py` | integration | none observed |
| `src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_identity_catalog_page.py` | integration | none observed |
| `src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_identity_gist_markdown.py` | integration | none observed |
| `src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_identity_ops_page.py` | integration | none observed |
| `src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_identity_parity.py` | integration | none observed |
| `src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_identity_workbook_page.py` | integration | none observed |
| `src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_vizro_static_export.py` | integration | none observed |
| `src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_vizro_static_export_flag.py` | integration | none observed |
| `src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_zero_deferred_e2e_gate.py` | integration | none observed |
| `src/shared/packages/pyforge-atlas/tests/integration/publish/test_emit_range.py` | integration | none observed |
| `src/shared/packages/pyforge-atlas/tests/integration/wasm/test_wasm_smoke.py` | integration | none observed |
| `src/shared/packages/pyforge-atlas/tests/meta/test_cli_tool_parity.py` | meta | none observed |
| `src/shared/packages/pyforge-atlas/tests/meta/test_foundry_full_mypy_lane.py` | meta | none observed |
| `src/shared/packages/pyforge-atlas/tests/meta/test_planning_record.py` | meta | none observed |
| `src/shared/packages/pyforge-atlas/tests/meta/test_portal_inventory_row.py` | meta | none observed |
| `src/shared/packages/pyforge-atlas/tests/meta/test_skf_skill_and_persona.py` | meta | none observed |
| `src/shared/packages/pyforge-atlas/tests/tools/test_live_artifactory_transport.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/a2a_surface/test_a2a_payloads.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/artifactory/test_aql_adapter.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/artifactory/test_identity_join.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/catalog/test_catalog_resolution.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/catalog/test_conventions.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/catalog/test_credential_scoping.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/catalog/test_json_sources_catalog.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/catalog/test_no_inline_io.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/catalog/test_override_points.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/catalog/test_scale_floors.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/catalog/test_tracked_seeds.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/catalog/test_yaml_hygiene.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_basilisk.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_basilisk_population.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_bigquery_cost_gate.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_catalog_index.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_cf_graph_split.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_clickhouse_downloads.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_core_sources.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_credentialed_switch.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_dependency_history.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_github_versions_health.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_hosts_and_registries.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_identity_live_sources.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_identity_sources.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_incremental_parquet.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_json_sources.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_migration_status.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_no_thirty_gb_lie.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_public_sources.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_pypi_json_phase_h.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_pypi_json_request_dataset.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_rate_limit.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_recipe_extras.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_refresh_assets.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_repodata_uploads.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_request_datasets.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_s3_downloads.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_sbom_intake.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_snapshot_history.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_story_27_2_degraded_datasets.py` | unit | 27.2 |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_tier3_sources.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_upstream_discovery.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_vcs_sources.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_vdb_boundary.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_vulnerability_feeds.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_vulnerability_stores_live.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/factory/test_crews.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/factory/test_lasuite.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/factory/test_lasuite_live_rehearsal.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/factory/test_personas.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/factory/test_wiki_scaffold.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/mcp/test_audit_mapping.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/mcp/test_bootstrapped_session.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/mcp/test_kedro_mcp_absent.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/mcp/test_no_business_logic_in_tool_bodies.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/mcp/test_official_sdk_server.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/mcp/test_read_surface.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/mcp/test_trigger_surface.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/nl/test_query_vizro_ai_dryrun.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/observability/test_observability_fixtures.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/orchestration/test_definitions_dryrun.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/orchestration/test_fleet_inventory_sensor.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/orchestration/test_viz_loadable.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/parity/test_capture_tooling.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/parity/test_evidence_and_retirement_gate.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/parity/test_frame_diff_bites.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/parity/test_legacy_surface_scope.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/parity/test_parity_complete.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/parity/test_parity_core.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/parity/test_parity_pypi_intelligence.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/parity/test_parity_runner_fixture_mode.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/parity/test_parity_vcs_health.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/parity/test_parity_vulnerability.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/artifactory_downloads/test_nodes.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/catalog_index/test_nodes.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/core/test_nodes.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/derived_artifacts/test_alternatives.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/derived_artifacts/test_derived_artifacts_e2e.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/derived_artifacts/test_identity_complete_export.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/derived_artifacts/test_inventory_aoss_free_queue.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/derived_artifacts/test_inventory_priority_assignments.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/derived_artifacts/test_inventory_universe.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/derived_artifacts/test_inventory_verification.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/derived_artifacts/test_inventory_verified_packages.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/derived_artifacts/test_purl_exports.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/derived_artifacts/test_release_cadence.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/derived_artifacts/test_universe_sbom.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/pypi_intelligence/test_mapping_export.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/pypi_intelligence/test_mapping_gap.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/pypi_intelligence/test_mapping_tiers.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/pypi_intelligence/test_nodes.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/pypi_intelligence/test_review_hardening.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/pypi_intelligence/test_serial_gate.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/seed_gaps/test_byte_identical_seed.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/seed_gaps/test_nodes.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/seed_gaps/test_pipeline_shape.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/semantic_packages/test_nodes.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/semantic_packages/test_upload_inputs.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/test_dag_resolves.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/test_refresh_schedule_fixtures.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/test_refresh_single_writer.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/universal_sbom/test_freshness.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/universal_sbom/test_match.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/universal_sbom/test_normalize.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/upstream_discovery/test_identity_parity_fixtures.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/upstream_discovery/test_nodes.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/vcs_health/test_migration_readiness.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/vcs_health/test_nodes.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/vcs_health/test_rate_limit_contract.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/vcs_health/test_release_velocity.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/vcs_health/test_universe_batches.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/vulnerability/test_basilisk_nodes.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/vulnerability/test_contracts.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/vulnerability/test_nodes.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/pipelines/vulnerability/test_vuln_history.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/policy_gate/test_policy_gate.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/query_plane/test_face_parity.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/rag/test_store_vss_free.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/rag/test_vss_similarity_search.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/semantic/test_board_models.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/semantic/test_bsl_metric_parity.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/semantic/test_composite_scores.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/semantic/test_maintainer_dimension.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/semantic/test_metric_classifiers.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/semantic/test_metric_provenance.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/singularity/test_duckdb_sole_engine.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/singularity/test_one_duckdb_server_launch_site.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_admission.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_board_projections.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_board_wiring.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_cap18_kedro_hook_map.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_cve_watcher_staleness.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_dashboard_app.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_dashboard_data.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_dashboard_factory_status.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_dashboard_identity_gist.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_dashboard_static_export.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_duckdb_boundary.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_estate_cache_bsl.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_hooks.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_import_smoke.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_main_dispatch.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_main_version.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_one_duckdb_writer.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_pipeline_inventory.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_query_plane_boot.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_query_plane_parquet_cache.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_query_plane_vectors.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_read_only_live_attach.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_scaffold_layout.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_scan_submit.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_scribe_plane_recall.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_semantic_packages_pipeline.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_viz_export_artifact.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_viz_publish_build.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/test_vizro_static_boards.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/trending_candidates/test_handoff.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/trending_candidates/test_main.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/trending_candidates/test_query.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/trending_candidates/test_surface_parity.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/validation/test_validation_hook.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/views/test_cli_bridge.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/views/test_live.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/views/test_registry.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/views/test_render.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/unit/views/test_widgets.py` | unit | none observed |

## Story Coverage Matrix

| Story | Title | Linked test files |
|-------|-------|-------------------|
| 1.1 | Generate legacy contextual skill | none observed |
| 2.1 | Scaffold the Kedro + pixi project via `nebi` | none observed |
| 2.2 | Define the Data Catalog for all sources + outputs | none observed |
| 2.3 | Implement `IncrementalParquetDataset` for TTL gating | none observed |
| 3.1 | Port the conda-side backbone phases into Kedro nodes | none observed |
| 3.2 | Port the PyPI & Vulnerability pipelines | none observed |
| 3.3 | Re-expose the data surface as Kedro-API-native MCP tools | none observed |
| 3.4 | Verify dataset parity against the legacy orchestrator | none observed |
| 3.5 | Port the external-refresh assets (§ 3.4) | none observed |
| 3.6 | Port the Seed-Gaps pipeline | none observed |
| 3.7 | Extend the Universal SBOM intake (resolver, formats, universe BOM, buckets) | none observed |
| 3.8 | Basilisk conda-native vulnerability ingestion | none observed |
| 3.9 | Release-to-availability velocity columns | none observed |
| 3.10 | Migration-readiness datasets + classification node | none observed |
| 4.1 | Integrate `kedro-dagster` for scheduling + execution | none observed |
| 4.2 | Integrate `kedro-viz` + expose a pixi task | none observed |
| 5.1 | Define the Boring Semantic Layer (BSL) models | none observed |
| 5.2 | Build the Vizro dashboard + port the 28 CLIs to pages | none observed |
| 5.3 | Integrate Vizro-AI + expose the NL interface as an MCP tool | none observed |
| 6.1 | Implement the A2A communication interfaces | none observed |
| 6.2 | Integrate OpenLineage + OpenTelemetry | none observed |
| 7.1 | Complete the DuckDB consolidation + prove the cold-start claim | none observed |
| 7.2 | Implement the data-validation hook and inline Pandera contracts | none observed |
| 7.3 | Implement Vector Similarity Search (RAG) via DuckDB `vss` | none observed |
| 7.4 | Dependency-hygiene node + unified CI policy gate | none observed |
| 8.1 | Compile the intelligence layer to Pyodide / DuckDB-WASM | none observed |
| 8.2 | Emit Parquet artifacts to a static web host | none observed |
| 8.3 | Implement Dagster Sensors for near-real-time ingestion | none observed |
| 9.1 | Scaffold the Karpathy Wiki folder structure and Agent Personas | none observed |
| 9.2 | Implement Agno Compilation, Linting, and Q&A Crews | none observed |
| 9.3 | Integrate La Suite Docs REST API Sync | none observed |
| 9.4 | Orchestrate Crews via Dagster | none observed |
| 10.1 | Restore atlas dependency-completeness so the suite can collect | none observed |
| 10.2 | Truth-up the Spec kernel and its companions | none observed |
| 10.3 | Uniform story-spec frontmatter, without laundering provenance | none observed |
| 10.4 | Preserve NULL identity under pandas 3.0 | none observed |
| 10.5 | Stamp advisory data with its build provenance (AD-17) | none observed |
| 10.6 | Make run admission real, or stop claiming it | none observed |
| 11.1 | kedro-skills audit-then-adopt (FR-61) | none observed |
| 11.2 | Publish the real DAG continuously (FR-62) | none observed |
| 11.3 | Record the `vscode-kedro` verdict (FR-63) | none observed |
| 12.1 | Trending ingest (FR-64) | none observed |
| 12.2 | Tier classification (FR-65) | none observed |
| 12.3 | `trending-candidates` operator surface (FR-66) | none observed |
| 12.4 | Fixed-source audit track (FR-67) | none observed |
| 12.5 | Downstream handoff to Mason (FR-68) | none observed |
| 13.1 | Static view catalog (CAP-1) | none observed |
| 13.2 | Pluggable widget registry (CAP-3) | none observed |
| 13.3 | Bokeh WebSocket interactivity (CAP-2) | none observed |
| 13.4 | Air-gap asset rewriting (CAP-4) | none observed |
| 14.1 | Injectable AQL adapter (CAP-1) | none observed |
| 14.2 | Identity join and internal flag (CAP-2, CAP-3) | none observed |
| 14.3 | Kedro pipeline surfacing (CAP-4) | none observed |
| 15.1 | Instance deploy definition (CAP-1) | none observed |
| 15.2 | Httpx opener and rehearsal (CAP-2, CAP-3) | none observed |
| 16.1 | The from-scratch run is a chartered capability | none observed |
| 16.2 | Handoffs are execution-ready | none observed |
| 17.1 | Map existing Kedro hooks to CAP-18 | none observed |
| 18.1 | SKF domain skill and BMAD persona for atlas | none observed |
| 18.2 | First portal slice — one inventory/run row | none observed |
| 19.1 | One boot script raises both plane faces (CAP-5) | none observed |
| 19.2 | Face parity is part of done (CAP-5) | none observed |
| 19.3 | Named-pipeline derivation of the dashboard stores (CAP-6) | none observed |
| 19.4 | The CIS two-spine specs exist (CAP-7) | none observed |
| 19.5 | Port the remaining nineteen Vizro pages (CAP-7) | none observed |
| 20.1 | Relocate atlas data defaults and add pyforge-atlas-bootstrap | none observed |
| 20.2 | Remove cf_atlas.db seeds from production datasets | none observed |
| 20.3 | Tier 0 harden and `--live-catalog` contract | none observed |
| 20.4 | Tier 1 catalog sources (SelfExplainML, Anaconda, Basilisk, AOSS) | none observed |
| 20.5 | Tier 2 sources (about, curated orgs, Artifactory names) | none observed |
| 20.6 | upstream_discovery identity join and export Parquet | none observed |
| 20.7 | Quartet thin-out and gist wrapper | none observed |
| 20.8 | End-to-end verification gate | none observed |
| 20.9 | Vizro bootstrap health pages (optional, CAP-5) | none observed |
| 20.10 | Kedro-Viz CI path sync (optional, CAP-6) | none observed |
| 21.1 | Ranked export bridge (quartet → Vizro feed) | none observed |
| 21.2 | Vizro `identity-catalog` page | none observed |
| 21.3 | Vizro `identity-ops` page | none observed |
| 21.4 | Vizro `identity-workbook` page | none observed |
| 21.5 | Canvas vs Vizro parity gate | none observed |
| 21.6 | Canvas deprecation switch | none observed |
| 22.1 | Tier 3 bulk OS indexes | none observed |
| 22.2 | Enterprise JFROG consumption Parquet | none observed |
| 22.3 | Priority rules in Kedro (`inventory_priority_assignments`) | none observed |
| 22.4 | Deliverable A + `Packaging_Candidate_Status` | none observed |
| 22.5 | `identity_complete_export.parquet` (canonical) | none observed |
| 22.6 | BSL gist aggregates (CAP-8d) | none observed |
| 22.7 | Zero-deferred E2E gate | none observed |
| 22.8 | Workbook-free metrics universe (Kedro `inventory_universe` + `--analysis-xlsx... | none observed |
| 22.9 | Quartet workbook retirement (thin actuators, no `openpyxl` in `scripts/`) | none observed |
| 23.1 | `mcp-builder` is atlas-wielded for the MCP face | none observed |
| 24.1 | Retire the second Lane-3 runtime | none observed |
| 24.2 | Materialize CAP-8's canonical Parquets — one recorded run | none observed |
| 24.3 | Atlas's MCP tools pass the CLI⇄tool parity gate | none observed |
| 24.4 | A live Artifactory transport exists for the attended operator to plug in | none observed |
| 25.1 | A per-repo dependency-history dataset from git-pkgs and an estate pixi parser | none observed |
| 25.2 | A poll-cursor sensor refreshes the history over Warden's fleet inventory | none observed |
| 26.1 | The factory-status frame drops its docs/specs rows | none observed |
| 27.1 | The inventory exports refuse a hollow verification set, and the quartet scrip... | none observed |
| 27.2 | The data plane honours its data root, degrades offline and fetches what it cl... | `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_story_27_2_degraded_datasets.py` |
| 27.3 | The read surfaces render what DESIGN.md specifies, and prove it on fixture data | none observed |
| 27.4 | The planning record matches the tree and the cross-station seams hold | none observed |
| 27.5 | The distribution-breakdown facet filter builds its control | none observed |
| 28.1 | The live-attach fixture Postgres starts under any basetemp | none observed |
| 29.1 | The range test server records each response before the client can read it | none observed |
| 30.1 | The DAG export reaches Pages as a workflow artifact | none observed |
| 30.2 | Vizro boards publish as static exports under /dashboard/vizro/ | none observed |
| 31.1 | Atlas passes mypy in `pyforge-foundry-full`, and a lane keeps it so | none observed |
| 32.1 | The DAG export builds in CI, and a failed build fails its task | none observed |
| 33.1 | The atlas CLI reaches the verbs its contracts name, from any directory | none observed |
| 34.1 | endoflife.date and the SPDX list arrive as records the seed-gap reports read | none observed |
| 34.2 | The Phase C mapping fills from the conda-forge bot's name mapping | none observed |
| 34.3 | Dependencies, feedstock health and maintainers read the bot's split graph repos | none observed |
| 34.4 | The download tables fill from Anaconda's monthly parquet | none observed |
| 34.5 | The five OS-distro indexes refresh themselves | none observed |
| 34.6 | The public discovery stores refresh themselves | none observed |
| 34.7 | The vulnerability stores refresh themselves | none observed |
| 34.8 | Migration status fills through a driver node | none observed |
| 34.9 | Phase P fills from the public ClickHouse mirror | none observed |
| 34.10 | Phase H covers every mapped PyPI project, gated by its serial | none observed |
| 34.11 | The Phase C mapping fills legacy's name-coincidence and recipe-source tiers | none observed |
| 34.12 | A vulnerability feed that cannot be reached keeps its last good copy | none observed |
| 35.1 | One opt-in switch, and GitHub authenticates | none observed |
| 35.2 | The VCS batches come from the whole universe | none observed |
| 35.3 | Upstream versions and feedstock health come from GitHub | none observed |
| 35.4 | GitLab, Codeberg and the eight registries fill | none observed |
| 36.1 | The Basilisk population runs | none observed |
| 36.2 | The OpenTeams board and the staged-recipes PRs fill on opt-in | none observed |
| 36.3 | The query-plane estate source has a producer | none observed |
| 37.1 | The dashboard reads the data root Kedro writes | none observed |
| 37.2 | The Pages Vizro export builds the public atlas data first | none observed |
| 37.3 | The seed-gap, version-download and distribution boards read their datasets | none observed |
| 37.4 | Behind-upstream, whodepends, live-catalog coverage and the universe SBOM boar... | none observed |
| 37.5 | The cve-watcher reads a vulnerability history | none observed |
| 37.6 | The release-cadence reads per-version upload times | none observed |
| 37.7 | The find-alternative scores candidates for archived packages | none observed |
| 37.8 | The export-purls lists the PURL artifacts | none observed |
| 37.9 | The mapping-gap classifies the unmapped packages | none observed |
| 37.10 | The bootstrap-index-health reports each catalog entry's freshness | none observed |
| 37.11 | A board's note reads "Data gap" only where data is missing | none observed |
| 37.12 | The Pages data build keeps its last good copies between runs | none observed |
| 37.13 | The cve-watcher marks an earlier run's diff stale | none observed |
| 38.1 | The semantic store reads its upload times and archived flag | none observed |

## Quality Gates

| Gate | Target | Enforcement |
|------|--------|-------------|
| Unit coverage | ≥80% | Story 19.3 CI gate |
| Integration coverage | ≥70% | Story 19.3 CI gate |
| Forbidden placeholder token | zero occurrences | this generator (hard fail) |
| Idempotent regen | byte-identical on unchanged tree | FR-132 |
| Story-id coverage drift | every epic story id in matrix | `--check` (CAP-5 / Story 19.4) |

## Regeneration

```bash
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-atlas
python _bmad/scripts/bmad_tea_playwright.py --all
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-atlas --check
python _bmad/scripts/bmad_tea_playwright.py --all --check
```
