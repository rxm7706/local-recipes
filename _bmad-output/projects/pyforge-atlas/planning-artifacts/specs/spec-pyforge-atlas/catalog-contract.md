# The catalog contract — pipelines, datasets, TTLs, and identity

Companion to `SPEC.md`. The kernel's Constraints declare the seven closed domain pipelines,
the producer-owns-the-dataset rule, per-dataset TTLs, the fixed join keys, and additive-first
schema evolution as normative. This file holds the tables those constraints compress: the
pipeline-to-dataset allocation, every declared TTL with its legacy origin, the two distinct
freshness clocks, and the identity conventions that make a join legal.

Without the allocation table, "each dataset has exactly one producing pipeline" is
unverifiable; without the TTL table, "never a global constant" is a slogan. That is why this
is a contract and not documentation.

The catalog is `conf/base/catalog.yml`; the TTL and freshness parameters are
`conf/base/parameters.yml`. Where this file and the code disagree, **the code is right and
this file is a defect** — the catalog is the single source of truth for IO.

---

## The seven closed pipelines

The pipeline set is **fixed**. A new signal joins its assigned pipeline; it never opens an
ad-hoc eighth. Two pipelines writing one dataset is the failure this rules out.

| Pipeline | Dataset prefix | Datasets | What it owns |
|---|---|---|---|
| `core` | `core_*` | 16 | The conda-side backbone: enumeration, feedstock attribution, downloads, dependency graph, feedstock health |
| `vcs_health` | `vcs_*` | 25 | Upstream version tracking across 8 registries, maintainer enrichment, archived-feedstock detection, live health |
| `pypi_intelligence` | `pypi_*` | 15 | The PyPI universe, name mapping, current versions, downloads, cross-channel flags, enrichment and readiness scoring |
| `vulnerability` | `vulnerability_*` | 14 | VDB rollup, per-version vulns, KEV/EPSS/CWE overlays, conda-native (Basilisk) advisories |
| `seed_gaps` | `seed_*` | 8 | The four read-only suggesters (CWE, SPDX, license-map, LTS-registry) |
| `universal_sbom` | `sbom_*` | 6 | Manifest intake, resolution, the universe BOM, six-bucket classification |
| `derived_artifacts` | `derived_*` | 2 | Cross-pipeline exports under the consumer freshness gate |
| **Total** | | **86** | |

Cross-pipeline reads are legal and normal — `vcs_health.enrich_maintainers` reads
`core_cf_graph_raw`, produced by `core`. What is illegal is a second *writer*.

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

Every value below is declared per dataset. There is no global TTL constant, and reintroducing
one is a contract breach.

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
| `pypi_intelligence_enriched` | 7 d | 604800 | `PHASE_R_TTL_DAYS` |
| `pypi_conda_map_store` | 7 d | 604800 | `MAPPING_TTL_DAYS` mapping cache |
| `pypi_endoflife_raw` | 7 d | 604800 | endoflife.date cache; `lts_registry_gap` `ttl_days=7` |
| `vulnerability_cisa_kev_raw` | 1 d | 86400 | Daily KEV re-fetch (G-4/B2 decision — CISA publishes on a rolling basis) |
| `vulnerability_epss_raw` | 1 d | 86400 | EPSS daily CSV |
| `vulnerability_cwe_catalog_raw` | 90 d | 7776000 | CWE catalog |
| `vulnerability_package_rollup` | 7 d | 604800 | `PHASE_G_TTL_DAYS`; gate column `vdb_scanned_at` |
| `vulnerability_package_version_vulns` | 30 d | 2592000 | `PHASE_GP_TTL_DAYS`; legacy reset = row absence |
| `vulnerability_osv_offline_store` | 7 d | 604800 | `cve_manager` `CVE_TTL_DAYS` |
| `vcs_upstream_versions` | 7 d | 604800 | `PHASE_K_TTL_DAYS`; column `github_version_fetched_at` |
| `vcs_registry_versions` | 7 d | 604800 | `PHASE_L_TTL_DAYS`; per-source `*_fetched_at` |
| `vcs_live_health` | 1 d | 86400 | `PHASE_N_TTL_DAYS` — live signals change fast |

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
`tests/catalog/test_no_inline_io.py` under the `kedro-catalog-check` gate, which bans HTTP and
DB clients inside `pipelines/`, `datasets/`, `hooks/`, and `mcp/`.

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
rather than porting it. The 20 `resolve_*_urls`-style override points survive as dataset-level
endpoint config, so an enterprise mirror substitutes with no code change. Both properties are
asserted under `kedro-catalog-check`.

Tracked configuration versus local configuration is a hard boundary: base config is tracked,
local config holds credentials and is gitignored, and explicit environment or run-config always
beats a profile default.
