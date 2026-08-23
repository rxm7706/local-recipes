---
title: "Test Architecture — pyforge-atlas"
type: test-architecture
generator: bmad_tea_playwright.py
generator_version: 2.0.0
status: generated
station: atlas
source_fingerprint: cf0477d924b22869
story_count: 57
test_file_count: 95
coverage_target_unit: ">=80%"
coverage_target_integration: ">=70%"
---

# Test Architecture — PyForge Atlas

This document is **machine-generated** by `bmad_tea_playwright.py` (v2.0.0). Do not hand-edit; re-run the generator after epics or tests change.

## Executive Summary

- **Station:** `pyforge-atlas`
- **Stories parsed:** 57
- **Epics parsed:** 26
- **Test files inventoried:** 95 under `src/shared/packages/pyforge-atlas/tests/`
- **Frameworks:** pytest (unit/integration/meta) + Playwright where present
- **Coverage targets:** unit ≥80%, integration ≥70% (gated by Story 19.3)
- **Source fingerprint:** `cf0477d924b22869`

## Risk Assessment

### High-risk epics

- none observed

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
- Epic 12: Kedro-org tooling — audit, publish, decide
- Epic 13: Upstream discovery — what to package next
- Epic 14: Atlas query dashboards — hand-someone-a-link views
- Epic 15: Artifactory download intelligence — mock-first AQL
- Epic 16: Wagtail corporate brain — the narrow DW-H3 contract
- Epic 17: The packaging-inventory intake engine, governed
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

### Low-risk epics

- none observed

## Test Inventory

| Relative path | Level | Linked stories |
|---------------|-------|----------------|
| `src/shared/packages/pyforge-atlas/tests/a2a_surface/test_a2a_payloads.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/artifactory/test_aql_adapter.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/artifactory/test_identity_join.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/catalog/test_catalog_resolution.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/catalog/test_conventions.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/catalog/test_credential_scoping.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/catalog/test_no_inline_io.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/catalog/test_override_points.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/catalog/test_yaml_hygiene.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/dashboard/test_dashboard_dryrun.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/dashboard/test_dashboard_e2e.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/datasets/test_basilisk.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/datasets/test_bigquery_cost_gate.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/datasets/test_incremental_parquet.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/datasets/test_migration_status.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/datasets/test_no_thirty_gb_lie.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/datasets/test_pypi_json_request_dataset.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/datasets/test_rate_limit.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/datasets/test_refresh_assets.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/datasets/test_request_datasets.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/datasets/test_sbom_intake.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/datasets/test_upstream_discovery.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/datasets/test_vdb_boundary.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/factory/test_crews.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/factory/test_lasuite.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/factory/test_lasuite_live_rehearsal.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/factory/test_personas.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/factory/test_wiki_scaffold.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/mcp/test_audit_mapping.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/mcp/test_kedro_mcp_absent.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/mcp/test_no_business_logic_in_tool_bodies.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/mcp/test_read_surface.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/mcp/test_trigger_surface.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/nl/test_query_vizro_ai_dryrun.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/observability/test_observability_fixtures.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/orchestration/test_definitions_dryrun.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/orchestration/test_viz_loadable.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/parity/test_capture_tooling.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/parity/test_evidence_and_retirement_gate.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/parity/test_frame_diff_bites.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/parity/test_legacy_surface_scope.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/parity/test_parity_complete.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/parity/test_parity_core.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/parity/test_parity_pypi_intelligence.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/parity/test_parity_runner_fixture_mode.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/parity/test_parity_vcs_health.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/parity/test_parity_vulnerability.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/artifactory_downloads/test_nodes.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/core/test_nodes.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/derived_artifacts/test_universe_sbom.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/pypi_intelligence/test_mapping_export.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/pypi_intelligence/test_nodes.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/pypi_intelligence/test_review_hardening.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/pypi_intelligence/test_serial_gate.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/seed_gaps/test_byte_identical_seed.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/seed_gaps/test_nodes.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/seed_gaps/test_pipeline_shape.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/test_dag_resolves.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/test_refresh_schedule_fixtures.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/test_refresh_single_writer.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/universal_sbom/test_freshness.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/universal_sbom/test_match.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/universal_sbom/test_normalize.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/upstream_discovery/test_nodes.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/vcs_health/test_migration_readiness.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/vcs_health/test_nodes.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/vcs_health/test_rate_limit_contract.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/vcs_health/test_release_velocity.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/vulnerability/test_basilisk_nodes.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/vulnerability/test_contracts.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/pipelines/vulnerability/test_nodes.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/policy_gate/test_policy_gate.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/publish/test_emit_range.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/rag/test_vss_similarity_search.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/semantic/test_bsl_metric_parity.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/semantic/test_maintainer_dimension.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/semantic/test_metric_provenance.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/singularity/test_duckdb_sole_engine.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/test_admission.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/test_hooks.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/test_import_smoke.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/test_main_version.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/test_scaffold_layout.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/trending_candidates/test_handoff.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/trending_candidates/test_main.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/trending_candidates/test_query.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/trending_candidates/test_surface_parity.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/validation/test_validation_hook.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/views/test_cli_bridge.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/views/test_live.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/views/test_registry.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/views/test_render.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/views/test_resources.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/views/test_widgets.py` | unit | none observed |
| `src/shared/packages/pyforge-atlas/tests/wasm/test_wasm_smoke.py` | unit | none observed |

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
| 12.1 | kedro-skills audit-then-adopt (FR-61) | none observed |
| 12.2 | Publish the real DAG continuously (FR-62) | none observed |
| 12.3 | Record the `vscode-kedro` verdict (FR-63) | none observed |
| 13.1 | Trending ingest (FR-64) | none observed |
| 13.2 | Tier classification (FR-65) | none observed |
| 13.3 | `trending-candidates` operator surface (FR-66) | none observed |
| 13.4 | Fixed-source audit track (FR-67) | none observed |
| 13.5 | Downstream handoff to Mason (FR-68) | none observed |
| 14.1 | Static view catalog (CAP-1) | none observed |
| 14.2 | Pluggable widget registry (CAP-3) | none observed |
| 14.3 | Bokeh WebSocket interactivity (CAP-2) | none observed |
| 14.4 | Air-gap asset rewriting (CAP-4) | none observed |
| 15.1 | Injectable AQL adapter (CAP-1) | none observed |
| 15.2 | Identity join and internal flag (CAP-2, CAP-3) | none observed |
| 15.3 | Kedro pipeline surfacing (CAP-4) | none observed |
| 16.1 | Instance deploy definition (CAP-1) | none observed |
| 16.2 | Httpx opener and rehearsal (CAP-2, CAP-3) | none observed |
| 17.1 | The from-scratch run is a chartered capability | none observed |
| 17.2 | Handoffs are execution-ready | none observed |

## Quality Gates

| Gate | Target | Enforcement |
|------|--------|-------------|
| Unit coverage | ≥80% | Story 19.3 CI gate |
| Integration coverage | ≥70% | Story 19.3 CI gate |
| Forbidden placeholder token | zero occurrences | this generator (hard fail) |
| Idempotent regen | byte-identical on unchanged tree | FR-132 |

## Regeneration

```bash
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-atlas
python _bmad/scripts/bmad_tea_playwright.py --all
```
