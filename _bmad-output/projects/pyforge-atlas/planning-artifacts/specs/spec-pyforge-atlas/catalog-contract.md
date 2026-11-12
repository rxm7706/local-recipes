# The catalog contract — pipelines, datasets, TTLs, and identity

Companion to `SPEC.md`. The kernel's Constraints declare the seven sealed domain pipelines and
their five governed additions, the producer-owns-the-dataset rule, per-dataset TTLs, the fixed
join keys, and additive-first schema evolution as normative. This file holds the tables those
constraints compress: the pipeline-to-dataset allocation (every catalog dataset, named once under
its pipeline), every declared TTL with its legacy origin, the two distinct freshness clocks, and
the identity conventions that make a join legal.

Without the allocation table, "each dataset has exactly one producing pipeline" is
unverifiable; without the TTL table, "never a global constant" is a slogan. That is why this
is a contract and not documentation.

The catalog is `conf/base/catalog.yml`; the TTL and freshness parameters are
`conf/base/parameters.yml`. Where this file and the code disagree, **the code is right and
this file is a defect** — the catalog is the single source of truth for IO.

---

## The pipelines: seven sealed, five governed additions

The migration surface is **seven sealed domain pipelines**. Five **governed additions** are
registered beside them, each entered through its own story chain (`spec-pyforge-atlas:CAP-1`). A
new signal joins its assigned pipeline; a new pipeline enters only as a governed addition with its
own chain, never ad hoc. Two pipelines writing one dataset is the failure this rules out.

Each dataset sits under the pipeline its name prefix assigns: the longest-prefix map
`PREFIX_TO_PIPELINE` in `tests/unit/catalog/conftest.py`. The Datasets column is that file's
`EXPECTED_PIPELINE_COUNTS` (total `EXPECTED_TOTAL`), which
`tests/unit/catalog/test_catalog_resolution.py` pins under `kedro-catalog-check`;
`tests/meta/test_catalog_contract.py` holds this table and the lists below to the catalog and to
those counts.

| Pipeline | Kind | Dataset prefixes | Datasets | What it owns |
|---|---|---|---|---|
| `core` | sealed | `core_*` | 20 | The conda-side backbone: repodata and channeldata enumeration (conda-forge and Anaconda main), feedstock attribution, latest status, downloads and their breakdowns, per-version download history, the dependency graph, feedstock health |
| `vcs_health` | sealed | `vcs_*`, `warden_*`, `repo_dependency_*` | 28 | Upstream version tracking across GitHub, GitLab, Codeberg and 8 registries, maintainer enrichment, archived-feedstock detection, live health, release velocity, migration readiness, the Warden fleet-inventory export and repo dependency history |
| `pypi_intelligence` | sealed | `pypi_*`, `discovery_{homebrew,nixpkgs,spack,debian,fedora}_*` | 22 | The PyPI universe, name mapping, current versions, downloads (BigQuery and ClickHouse), cross-channel and Tier 3 OS-index flags, enrichment and readiness scoring |
| `vulnerability` | sealed | `vulnerability_*` | 16 | VDB rollup and its snapshots, per-version vulns, KEV/EPSS/CWE overlays, the OSV offline store, conda-native (Basilisk) advisories |
| `seed_gaps` | sealed | `seed_*` | 8 | The four read-only suggesters (CWE, SPDX, license-map, LTS-registry) and their seeds |
| `universal_sbom` | sealed | `sbom_*` | 6 | Manifest intake, resolution, the normalized BOM, the match and hygiene reports, the compliance report |
| `derived_artifacts` | sealed | `derived_*`, `inventory_*`, `identity_complete_export` | 19 | Cross-pipeline exports and board projections under the consumer freshness gate, the inventory universe and its queues, the complete identity export |
| `upstream_discovery` | governed addition | `discovery_*` (the rest), `trending_*`, `org_audit_*`, `enterprise_*`, `purl_associator_*`, `openteams_*`, `identity_*` | 19 | Trending and org-audit candidates, the Tier 1 and Tier 2 discovery sources, the identity join |
| `artifactory_downloads` | governed addition | `artifactory_*`, `enterprise_jfrog_consumption` | 4 | Artifactory download telemetry, its identity join and the enterprise JFrog consumption rollup |
| `query_plane_cache` | governed addition | `query_plane_*` | 2 | The query plane's estate cache |
| `semantic_packages` | governed addition | `semantic_packages` | 1 | The composed semantic store the grounded dashboard pages bind to |
| `catalog_index` | governed addition | `catalog_index_*` | 2 | The read-only catalog index and its health report |
| **Total** | | | **147** | |

Cross-pipeline reads are legal and normal — `vcs_health.enrich_maintainers` reads
`core_cf_graph_raw`, a `core` source. What is illegal is a second *writer*: the writer of a dataset
is the node whose output it is, and `tests/unit/pipelines/test_dag_resolves.py` pins that no
dataset has two. A dataset with no writing node is a source: its catalog dataset fetches or reads
it.

Five datasets are written by a pipeline other than the one their prefix assigns (the registered
pipelines, 2026-11-11). Each still has one writer; the prefix is the count's bucket, not the
writer.

| Dataset | Prefix pipeline | Written by |
|---|---|---|
| `derived_mapping_gap` | `derived_artifacts` | `pypi_intelligence` |
| `derived_vuln_history` | `derived_artifacts` | `vulnerability` |
| `derived_purl_exports` | `derived_artifacts` | `artifactory_downloads` (its `artifactory_downloads.tsv` partition) |
| `vulnerability_basilisk_rollup` | `vulnerability` | `derived_artifacts` |
| `enterprise_jfrog_names` | `upstream_discovery` | `artifactory_downloads` |

### `core`

- `core_repodata_raw`
- `core_channeldata_raw`
- `core_anaconda_main_channeldata_raw`
- `core_feedstock_outputs_raw`
- `core_anaconda_downloads_raw`
- `core_s3_download_stats_raw`
- `core_s3_version_downloads_raw`
- `core_repodata_uploads_raw`
- `core_cf_graph_raw`
- `core_packages_enumerated`
- `core_anaconda_main_packages`
- `core_feedstock_attribution`
- `core_latest_status`
- `core_downloads`
- `core_downloads_platform_breakdown`
- `core_downloads_pyver_breakdown`
- `core_downloads_channel_breakdown`
- `core_version_download_history`
- `core_dependencies`
- `core_feedstock_health`

### `vcs_health`

- `vcs_github_api_raw`
- `vcs_gitlab_api_raw`
- `vcs_codeberg_api_raw`
- `vcs_registry_npm_raw`
- `vcs_registry_cran_raw`
- `vcs_registry_cpan_raw`
- `vcs_registry_luarocks_raw`
- `vcs_registry_crates_raw`
- `vcs_registry_rubygems_raw`
- `vcs_registry_maven_raw`
- `vcs_registry_nuget_raw`
- `vcs_maintainers`
- `vcs_package_maintainers`
- `vcs_archived_feedstocks`
- `vcs_upstream_versions`
- `vcs_registry_versions`
- `vcs_live_health`
- `vcs_release_velocity`
- `vcs_migration_regular_status_raw`
- `vcs_migration_longterm_status_raw`
- `vcs_migration_closed_status_raw`
- `vcs_migration_paused_status_raw`
- `vcs_migration_total_status_raw`
- `vcs_migration_detail_raw`
- `vcs_migration_categories`
- `vcs_migration_readiness`
- `warden_fleet_inventory`
- `repo_dependency_history`

### `pypi_intelligence`

- `pypi_simple_index_raw`
- `pypi_json_raw`
- `pypi_bigquery_downloads_raw`
- `pypi_clickhouse_downloads_raw`
- `pypi_parselmouth_mapping_raw`
- `pypi_cross_channel_repodata_raw`
- `discovery_homebrew_packages_raw`
- `discovery_nixpkgs_packages_raw`
- `discovery_spack_packages_raw`
- `discovery_debian_packages_raw`
- `discovery_fedora_packages_raw`
- `pypi_endoflife_raw`
- `pypi_conda_map_store`
- `pypi_universe`
- `pypi_universe_serial_snapshots`
- `pypi_conda_mapping`
- `pypi_current_versions`
- `pypi_downloads_monthly`
- `pypi_cross_channel_flags`
- `pypi_tier3_channel_flags`
- `pypi_intelligence_enriched`
- `pypi_intelligence_scored`

### `vulnerability`

- `vulnerability_cisa_kev_raw`
- `vulnerability_epss_raw`
- `vulnerability_cwe_catalog_raw`
- `vulnerability_vdb_store`
- `vulnerability_osv_offline_store`
- `vulnerability_basilisk_raw`
- `vulnerability_basilisk_detail_raw`
- `vulnerability_cisa_kev`
- `vulnerability_epss_scores`
- `vulnerability_cwe_categories`
- `vulnerability_package_rollup`
- `vulnerability_rollup_snapshots`
- `vulnerability_package_version_vulns`
- `vulnerability_basilisk_advisories`
- `vulnerability_basilisk_details`
- `vulnerability_basilisk_rollup`

### `seed_gaps`

- `seed_lts_registry`
- `seed_cwe_categories`
- `seed_spdx_schema`
- `seed_spdx_upstream_list_raw`
- `seed_gaps_lts_registry_report`
- `seed_gaps_cwe_report`
- `seed_gaps_spdx_report`
- `seed_gaps_license_map_report`

### `universal_sbom`

- `sbom_intake_entry`
- `sbom_resolution_entry`
- `sbom_normalized_bom_entry`
- `sbom_match_report_entry`
- `sbom_hygiene_entry`
- `sbom_compliance_report_entry`

### `derived_artifacts`

- `derived_mapping_gap`
- `derived_vuln_history`
- `derived_purl_exports`
- `derived_purl_artifacts`
- `derived_purl_export_manifest`
- `derived_alternative_candidates`
- `derived_release_cadence`
- `derived_graph_archived_feedstocks`
- `derived_version_downloads`
- `derived_distribution_breakdown`
- `derived_universe_sbom`
- `derived_behind_upstream`
- `derived_live_catalog_coverage`
- `derived_universe_sbom_summary`
- `inventory_universe`
- `inventory_priority_assignments`
- `inventory_verified_packages`
- `inventory_aoss_free_queue`
- `identity_complete_export`

### `upstream_discovery`

- `discovery_recipe_extras_raw`
- `trending_candidates`
- `trending_candidates_classified`
- `org_audit_candidates`
- `org_audit_candidates_classified`
- `discovery_anaconda_dist_2026x_raw`
- `discovery_basilisk_packages_raw`
- `discovery_aoss_free_python_raw`
- `discovery_aoss_premium_python_raw`
- `discovery_about_maintainers_raw`
- `discovery_curated_groups_seed`
- `enterprise_conda_maintainers`
- `purl_associator_mappings_raw`
- `openteams_project_1_board_raw`
- `discovery_staged_recipes_prs_raw`
- `discovery_local_recipes_raw`
- `identity_packages_primary`
- `identity_export_parquet`
- `enterprise_jfrog_names`

### `artifactory_downloads`

- `artifactory_downloads_raw`
- `artifactory_downloads_joined`
- `artifactory_consumption_raw`
- `enterprise_jfrog_consumption`

### `query_plane_cache`

- `query_plane_estate_source`
- `query_plane_estate`

### `semantic_packages`

- `semantic_packages`

### `catalog_index`

- `catalog_index_raw`
- `catalog_index_health`

## Two freshness clocks, never conflated

This is the distinction most likely to be misread, so it is stated before the tables.

| Clock | Declared in | Question it answers | On breach |
|---|---|---|---|
| **Fetch TTL** | `parameters.yml` → `ttls.<dataset>` | "Is this row stale enough to re-fetch?" | Row re-fetches; fresh rows skip |
| **Consumer freshness** | `parameters.yml` → `freshness.stale_after_days` (AD-15, 14 d) | "Is this dataset too old to be *read*?" | Consumer **refuses** the input |

A fetch TTL is a producer-side economy. A freshness contract is a consumer-side refusal.
A dataset can be well inside its fetch TTL and still fail the consumer gate, and that is
correct behavior, not a bug.

TTLs are injected at runtime by `pyforge.atlas.hooks.ProjectHooks` from `params:ttls.<name>`.
**Nodes never read TTLs** — a node that reads a TTL has taken on a dataset concern.

## Declared fetch TTLs

Every value below is declared per dataset, under `ttls:` in `parameters.yml`. There is no global
TTL constant, and reintroducing one is a contract breach. A dataset with no row has no fetch TTL:
`discovery_aoss_free_python_raw` is a tracked seed and `discovery_local_recipes_raw` a plain
filesystem read.

| Dataset | TTL | Seconds | Legacy origin |
|---|---|---|---|
| `core_downloads` | 7 d | 604800 | `PHASE_F_TTL_DAYS`; gate column `downloads_fetched_at` |
| `core_downloads_platform_breakdown` | 7 d | 604800 | Phase F, s3-parquet path only |
| `core_downloads_pyver_breakdown` | 7 d | 604800 | Phase F, s3-parquet path only |
| `core_downloads_channel_breakdown` | 7 d | 604800 | Phase F, s3-parquet path only |
| `core_version_download_history` | 7 d | 604800 | Phase I — the promoted side-effect, now an explicit node output |
| `core_cf_graph_raw` | 1 d | 86400 | `ATLAS_CFGRAPH_TTL_DAYS` cached tarball |
| `pypi_universe` | 7 d | 604800 | `PHASE_D_UNIVERSE_TTL_DAYS` |
| `pypi_current_versions` | 7 d | 604800 | `PHASE_H_TTL_DAYS`; serial-gated on `pypi_version_fetched_at` |
| `pypi_downloads_monthly` | 30 d | 2592000 | `PHASE_P_TTL_DAYS`; monthly partitions; admin-only |
| `pypi_cross_channel_flags` | 7 d | 604800 | `PHASE_Q_TTL_DAYS` |
| `pypi_tier3_channel_flags` | 7 d | 604800 | None; the Tier 3 OS bulk-index flags (Story 23.1) |
| `pypi_intelligence_enriched` | 7 d | 604800 | `PHASE_R_TTL_DAYS` |
| `pypi_conda_map_store` | 7 d | 604800 | `MAPPING_TTL_DAYS` mapping cache |
| `pypi_endoflife_raw` | 7 d | 604800 | endoflife.date cache; `lts_registry_gap` `ttl_days=7` |
| `discovery_homebrew_packages_raw` | 7 d | 604800 | None; Tier 3 OS-distro bulk index, weekly (Story 23.1) |
| `discovery_nixpkgs_packages_raw` | 7 d | 604800 | None; Tier 3 OS-distro bulk index, weekly (Story 23.1) |
| `discovery_spack_packages_raw` | 7 d | 604800 | None; Tier 3 OS-distro bulk index, weekly (Story 23.1) |
| `discovery_debian_packages_raw` | 7 d | 604800 | None; Tier 3 OS-distro bulk index, weekly (Story 23.1) |
| `discovery_fedora_packages_raw` | 7 d | 604800 | None; Tier 3 OS-distro bulk index, weekly (Story 23.1) |
| `vulnerability_cisa_kev_raw` | 1 d | 86400 | Daily KEV re-fetch (G-4/B2 decision — CISA publishes on a rolling basis) |
| `vulnerability_epss_raw` | 1 d | 86400 | EPSS daily CSV |
| `vulnerability_cwe_catalog_raw` | 90 d | 7776000 | CWE catalog |
| `vulnerability_package_rollup` | 7 d | 604800 | `PHASE_G_TTL_DAYS`; gate column `vdb_scanned_at` |
| `vulnerability_package_version_vulns` | 30 d | 2592000 | `PHASE_GP_TTL_DAYS`; legacy reset = row absence |
| `vulnerability_osv_offline_store` | 7 d | 604800 | `cve_manager` `CVE_TTL_DAYS` |
| `vcs_upstream_versions` | 7 d | 604800 | `PHASE_K_TTL_DAYS`; column `github_version_fetched_at` |
| `vcs_registry_versions` | 7 d | 604800 | `PHASE_L_TTL_DAYS`; per-source `*_fetched_at` |
| `vcs_live_health` | 1 d | 86400 | `PHASE_N_TTL_DAYS` — live signals change fast |
| `trending_candidates` | 1 d | 86400 | None; the daily discovery cadence (Story 13.1) |
| `discovery_anaconda_dist_2026x_raw` | 7 d | 604800 | None; Tier 1 discovery source, weekly (Story 21.4) |
| `discovery_basilisk_packages_raw` | 7 d | 604800 | None; Tier 1 discovery source, weekly (Story 21.4) |
| `discovery_aoss_premium_python_raw` | 7 d | 604800 | None; Tier 1 discovery source, weekly (Story 21.4) |
| `discovery_about_maintainers_raw` | 7 d | 604800 | None; Tier 2 maintainer lists, refreshed by hand (Story 21.5) |
| `purl_associator_mappings_raw` | 7 d | 604800 | None; identity-join source, weekly (Story 21.6) |
| `openteams_project_1_board_raw` | 7 d | 604800 | None; identity-join source, weekly (Story 21.6) |
| `discovery_staged_recipes_prs_raw` | 7 d | 604800 | None; identity-join source, weekly (Story 21.6) |

The four distinct tiers — 1 d, 7 d, 30 d, 90 d — track how fast the *upstream* moves, not how
fast we would like to re-run.

## Incremental state is a dataset concern

`IncrementalParquetDataset` round-trips `*_fetched_at` TTL state and exposes
`stale_mask` / `fresh_mask`. A node calls the mask to decide which rows need re-fetching and
hands that set back to the dataset. The node implements **no** checkpoint, **no** backoff, and
**no** retry. The legacy `phase_state` checkpoint table is deleted and does not return;
resumability comes from the runner plus persisted intermediate datasets.

## Identity and join keys

Fixed and non-negotiable. Guessing an identity is how a false join silently produces a
confident wrong answer.

| Concern | Rule |
|---|---|
| Canonical join keys | `conda_name` (plus feedstock attribution where it applies), `pypi_name`, `(conda_name, advisory_id)` |
| The only bridge | The name-mapping dataset. Nothing else joins conda-side to PyPI-side. |
| purls | **Interchange identity only — never an internal join key.** Conda purls carry the `?channel=conda-forge` qualifier. |
| Property namespace | `cfe:*` is preserved end to end and never stripped |
| Versions | Compare by PEP 440 |
| Percentiles | Stored on exactly one scale |
| Timestamps | Normalize to **epoch seconds at the dataset boundary**. Repodata per-build values are milliseconds — convert once, at the boundary, never downstream. |

## Schema evolution — additive-first

New columns are **nullable**. A breaking change to a persisted dataset requires, *in the same
story*: a catalog version note, plus a migration node or a re-materialization, plus updated
contracts and fixtures. No global schema-version constant returns.

## The no-inline-IO boundary

Nodes are pure functions: dataframe in, dataframe out. Sources, outputs, credentials,
endpoints, and physical layout are catalog concerns. The structural ban is enforced by
`tests/unit/catalog/test_no_inline_io.py` under the `kedro-catalog-check` gate, which bans HTTP,
DB and subprocess clients in every module of `src/pyforge/atlas/` except the five root-level
framework files its conftest's `NO_INLINE_IO_EXEMPT` names.

The one real tension — Phase K's 3-RPS token bucket and Phase F's HTTP fetches are imperative
code inside the legacy phase function — resolves the same way every time: **fetching and rate
limiting are dataset or resource concerns.** The request, the token bucket, `Retry-After` plus
jittered backoff, per-registry concurrency caps, and the 403 → `last_error` → TTL-bypass
re-pick all live in the catalog dataset or in an injected client passed to the node as a
catalog input. The node receives already-fetched frames.

If an acceptance criterion or a convenience tempts an inline `requests`/`urllib` call in a node
body — stop. That is the exact failure the migration exists to remove.

## Credential scoping

Credentials attach to a dataset's destination **host**, never globally. A non-JFrog host
provably never receives the JFrog API header — this closes the legacy global-injection defect
rather than porting it. The `<HOST>_BASE_URL` override points survive as dataset-level
endpoint config, so an enterprise mirror substitutes with no code change: 27 endpoint bases in
`conf/base/globals.yml` (19 carried from the legacy `resolve_*_urls` helpers, 2 from Story 21.4,
5 from Story 23.1, and 1 reserved), inside a 43-wide environment-override surface. Both
properties are asserted under `kedro-catalog-check`, by
`tests/unit/catalog/test_override_points.py` and `tests/unit/catalog/test_credential_scoping.py`.

Tracked configuration versus local configuration is a hard boundary: base config is tracked,
local config holds credentials and is gitignored, and explicit environment or run-config always
beats a profile default.
