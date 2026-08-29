# Catalog sources — tier matrix

Companion to `SPEC.md`. Every new entry documents fetch mode:
**live** | **upstream Parquet** | **external-refresh** | **tracked seed** |
**credentialed opt-in**.

## Tier 0 — exist today; harden live-first (Phase B + C0)

| Catalog entry | Fetch mode | Pipeline | Inventory / identity use |
|---------------|------------|----------|--------------------------|
| `core_channeldata_raw` | live | `core` | `CondaForge_Verified` (~30k+ rows) |
| `pypi_simple_index_raw` | live / upstream | `pypi_intelligence` | `PyPI_Verified` |
| `pypi_json_raw` | live / upstream | `pypi_intelligence` | `PyPI_Verified`, VCS URLs |
| `pypi_conda_mapping` / `pypi_conda_map_store` | external-refresh | `pypi_intelligence` | Parselmouth name map |
| `core_feedstock_outputs_raw` → `core_feedstock_attribution` | live | `core` | Feedstock URL overlay |
| `purl_associator_mappings_raw` | live + AD-13 | `upstream_discovery` | Identity associator join |
| `openteams_project_1_board_raw` | credentialed | `upstream_discovery` | `OpenTeams_Issue_URL`, board extras |

## Tier 1 — new raw sources (Phase C1)

| Source | Catalog name (proposed) | Pipeline | Notes |
|--------|-------------------------|----------|-------|
| SelfExplainML repodata | extend `pypi_cross_channel_repodata_raw` | `pypi_intelligence` | `noarch` + `linux-64` |
| Anaconda main channeldata | `core_anaconda_main_channeldata_raw` | `core` | Same parser as `core_channeldata_raw` |
| Anaconda Dist 2026.x | `discovery_anaconda_dist_2026x_raw` | `core` or `upstream_discovery` | HTML extractor + seed fallback |
| Basilisk `/v1/packages` | `discovery_basilisk_packages_raw` | `upstream_discovery` | Distinct from `vulnerability_basilisk_*` |
| Google AOSS free Python | `discovery_aoss_free_python_raw` | `upstream_discovery` | Tracked seed for air-gap |
| Google AOSS premium Python | `discovery_aoss_premium_python_raw` | `upstream_discovery` | Live doc; Wayback last-good |

Cross-channel bioconda / pytorch / nvidia / robostack: **harden** existing
`pypi_cross_channel_repodata_raw` (subdir + repodata fallback, tests).

## Tier 2 — inventory alignment (Phase C2)

| Source | Catalog name (proposed) | Pipeline | Notes |
|--------|-------------------------|----------|-------|
| rxm7706/about README | `discovery_about_maintainers_raw` | `upstream_discovery` | Maintainer + co-maintainer sets |
| Curated org sweeps | extend `org_audit_candidates` | `upstream_discovery` | `curated_groups.json` air-gap seed |
| Artifactory / CDO names | `artifactory_downloads_raw` (live) | `artifactory_downloads` | Names only; telemetry stays inventory |
| conda-forge.org/packages | — | deferred | Prefer `core_feedstock_attribution` |

## Tier 3 — Epic 23.1 (CAP-8 closure; deferred from Epic 21 v1)

homebrew · nixpkgs · spack · debian · fedora — dataset-owned bulk indexes;
cross-channel BOOL columns on verification export. See `complete-export-contract.md` §3.3.

## Scale sanity gates

| Index | Floor (order of magnitude) |
|-------|----------------------------|
| conda-forge channeldata | ~30,000+ packages |
| Basilisk package catalog | non-zero when API healthy |
| PyPI simple index | non-empty |
| AOSS free Python | ~1,000+ |
| Anaconda main | ~5,000+ |

Bootstrap smoke or catalog tests assert floors; sub-threshold = fail, not warn-only.
