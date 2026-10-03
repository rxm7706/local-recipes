---
title: "27.2: The data plane honours its data root, degrades offline and fetches what it claims"
type: 'fix'
created: '2026-10-03'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** 26 open deferred-work rows (12 medium, 14 low) raised by Stories 20.2-20.8 against Atlas's datasets, catalog, pipelines and orchestration: 53 of the catalog's `filepath:` entries hard-code `data/...` and ignore `PYFORGE_ATLAS_DATA_ROOT`, and `local_recipes_dir` resolves against the member directory; a refresh batch with one success overwrites the whole persisted store; the vcs refresh triggers fetch an empty identifier batch, so no real data flows; an offline `core` run dies on `CondaChanneldataDataset`'s transport error; a malformed curated-groups seed, or a cross-pipeline input absent on a fresh data root, aborts the run; the bootstrap never populates the three fetcher-less discovery stores and does not say so; `source_repository_url` is never populated; and the atlas CI lane runs `kedro-test` but not `kedro-catalog-check`. The same modules carry the refresh-store and test-coverage lows listed below.

**Approach:** Fix each where it lives: every intermediate, primary and derived catalog path under `${globals:paths.data_root}`; `_ParquetRefreshStore._persist` merges a batch onto the store (and moves to `datasets/refresh.py`); the vcs triggers take identifiers from the identity join; `CondaChanneldataDataset` and absent cross-pipeline inputs degrade to last-good or empty plus a stale marker (AD-13); the hand-curated JSON seeds load through a degrade wrapper; the bootstrap names its fetcher-less stores as stale; `_id_universe_frame` reads a real source URL; the CI lane runs both gates. Close the same modules' lows on the way.

Ledger key: `27-2-the-data-plane-honours-its-data-root-and-fetches-what-it-claims`.
Type / Effort / Deps: fix / L / —.
Rows: 26 (12 medium, 14 low).

### Living CAP citations

- The atlas capabilities that shipped each behaviour (see each row's source story); a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given `PYFORGE_ATLAS_DATA_ROOT` set to an empty directory When the bootstrap runs Then every catalog output lands under it, nothing lands under the member's `data/`, and a catalog test fails on any literal `data/` filepath
- Given a persisted refresh store and a partial batch with one success When the batch persists Then rows outside the batch survive
- Given a fixture identity join When the vcs refresh triggers fire Then they fetch a non-empty identifier batch, and a zero or negative TTL cadence is clamped
- Given no network When `kedro run --pipelines core` and `kedro run --pipelines upstream_discovery,artifactory_downloads` run on a fresh data root Then both exit 0, the degraded inputs carry stale markers, and a malformed curated-groups seed yields zero rows plus a stale marker
- Given the bootstrap When it finishes Then its summary lists the three fetcher-less discovery stores as stale, and the task description and README name that degrade category
- Given a pull request touching the package When CI runs Then the atlas job runs `kedro-catalog-check` as well as `kedro-test`
- Given each defect this story fixes When its new test runs against the tree before the fix Then it fails, and after the fix it passes
- Given this story lands When its deferred-work rows are read Then each of `DW-FU-21-2-2`, `DW-FU-21-2-4`, `DW-FU-21-4`, `DW-FU-21-5`, `DW-FU-21-5-3`, `DW-FU-21-6`, `DW-FU-21-8-2`, `DW-FU-21-8-9`, `DW-FU-21-8-3`, `DW-FU-21-8-5`, `DW-FU-21-8-10`, `DW-FU-21-8-8`, `DW-FU-21-2-3`, `DW-FU-21-2-5`, `DW-FU-21-2-6`, `DW-FU-21-2-7`, `DW-FU-21-2-8`, `DW-FU-21-3`, `DW-FU-21-4-2`, `DW-FU-21-4-3`, `DW-FU-21-4-4`, `DW-FU-21-6-2`, `DW-FU-21-6-3`, `DW-FU-21-6-4`, `DW-FU-21-8`, `DW-FU-21-8-4` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** Degrade, never fail, offline (NFR-3, AD-13): keep the last-good dataset and mark it stale. Credential scoping stays declarative in the catalog with its allowlist test updated (AD-2). Generate no live call in a test; every new test is fixture-based. Fix each defect where the shipped behaviour lives now and pin it with a test that fails without the fix. A re-ingested twin closes with the row it repeats, citing the same fix.

**Never:** Never import Dagster, `kedro-mcp` or an agent in `pipelines/`, `datasets/` or `hooks.py` (AD-1). Never pass the Kedro `version:` kwarg to `IncrementalParquetDataset`. Never use a purl as an internal join key. Never close a row without a landed fix and a cited `verified:` line (no blanket closure).

</intent-contract>

## Deferred-work rows this story closes (operator ruling 2026-10-03, deferral burn-down Phase 4+5)

- `DW-FU-21-2-2` (medium) — The three vcs refresh-trigger nodes take their identifier batch from the identity join's repository identities (Story 20.6) instead of an empty batch; a fixture run shows non-empty batches.
- `DW-FU-21-2-4` (medium) — `_ParquetRefreshStore._persist` and `GitHubRequestDataset.fetch_repo_health` merge a batch's rows onto the persisted store by identifier, never dropping rows outside the batch.
- `DW-FU-21-4` (medium) — `CondaChanneldataDataset.load()` degrades a transport error to the last-good frame plus a stale marker (AD-13), so an offline `kedro run --pipelines core` exits 0.
- `DW-FU-21-5` (medium) — `discovery_curated_groups_seed`, and the precedent `seed_cwe_categories` and `seed_spdx_schema`, load through a degrade wrapper: malformed JSON yields zero rows plus a stale marker, not a `DatasetError` that aborts the run.
- `DW-FU-21-5-3` (medium) — A cross-pipeline Parquet input absent on a fresh data root (`core_feedstock_attribution` for `join_enterprise_conda_maintainers`) degrades to empty plus a stale marker, so `kedro run --pipelines upstream_discovery,artifactory_downloads` exits 0 on an empty root, as spec-20-5's Verification claims.
- `DW-FU-21-6` (medium) — `_id_universe_frame` takes `source_repository_url` from the catalog source that carries a source URL, instead of a hard-coded empty string, so the git-purl fallback fires on real data.
- `DW-FU-21-8-2` (medium) — Every intermediate, primary and derived `filepath:` in `conf/base/catalog.yml` resolves under `${globals:paths.data_root}`; a catalog test fails on a literal `data/` filepath.
- `DW-FU-21-8-9` (medium) — Re-ingested twin of `DW-FU-21-8-2` (same text, later intake); closed by the same fix and test.
- `DW-FU-21-8-3` (medium) — The three fetcher-less discovery stores (`discovery_basilisk_packages_raw`, `discovery_aoss_premium_python_raw`, `discovery_anaconda_dist_2026x_raw`) are listed as stale (no refresher in an unattended run) in the bootstrap summary, and the `pyforge-atlas-bootstrap` task description and README name that degrade category.
- `DW-FU-21-8-5` (medium) — Re-ingested twin of `DW-FU-21-8-3` (same text, later intake); closed by the same fix and test.
- `DW-FU-21-8-10` (medium) — Re-ingested twin of `DW-FU-21-8-3` (same text, later intake); closed by the same fix and test.
- `DW-FU-21-8-8` (medium) — The `atlas-test` job in `.github/workflows/pyforge-station-tests.yml` runs `kedro-catalog-check` as well as `kedro-test` on every pull request touching the package; today it runs only `kedro-test`.
- `DW-FU-21-2-3` (low) — `_ttl_cadence` clamps a zero or negative configured cadence to a floor and logs it.
- `DW-FU-21-2-5` (low) — `VcsHostSeedDataset` and `RegistryUpstreamDataset` share one `fetch_one` retry-with-backoff helper.
- `DW-FU-21-2-6` (low) — `_ParquetRefreshStore` moves to `datasets/refresh.py` beside `StalenessMarker` and `RefreshRequest`; both consumers import it from there.
- `DW-FU-21-2-7` (low) — GitLab, Codeberg and the rate-limited registries (npm, crates.io, RubyGems, NuGet) take optional token credentials declared in `catalog.yml`, with the credential-scoping allowlist test updated; anonymous stays the default.
- `DW-FU-21-2-8` (low) — `PyPIJsonFanOutDataset.load` rotates its candidate window with a persisted offset, so every name is fetched across cycles.
- `DW-FU-21-3` (low) — `match_source_urls`' `recipe_source_url` tier keeps only names in `core_packages_enumerated`, so the `conda_name` subset property holds for every persisted row.
- `DW-FU-21-4-2` (low) — `tests/pipelines/test_refresh_single_writer.py` includes `upstream_discovery` in `_all_nodes()` and maps `trending_candidates` and the three Tier-1 stores.
- `DW-FU-21-4-3` (low) — `_fetch_repodata_at_url` tells a connection-level failure from a miss, and `_fetch_channel_repodata` skips that mirror's remaining combinations, keeping the worst case inside `flag_cross_channel`'s node timeout.
- `DW-FU-21-4-4` (low) — `NODE_TIMEOUTS` maps the five unmapped nodes, and a completeness test fails on any registered node missing from it.
- `DW-FU-21-6-2` (low) — `StagedRecipesPRDataset._do_refresh` paginates each pull request's `files` listing past 100.
- `DW-FU-21-6-3` (low) — `_LOCAL_RECIPES_TREE_URL_TEMPLATE` takes its repository slug from a configurable value beside `PYFORGE_ATLAS_LOCAL_RECIPES_DIR`.
- `DW-FU-21-6-4` (low) — Either `tests/parity/test_parity_complete.py` gains `upstream_discovery` (if it has parity fixtures) or spec-20-6 gains a Spec Change Log line correcting its Code Map; the story picks one and pins it.
- `DW-FU-21-8` (low) — `paths.local_recipes_dir` resolves against the repo root, as `seed_root` does since DW-FU-21-2, so a default bootstrap scans the real `recipes/` tree.
- `DW-FU-21-8-4` (low) — Re-ingested twin of `DW-FU-21-8` (same text, later intake); closed by the same fix and test.

## Binding

Parent: The atlas capabilities that shipped each behaviour; a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag.
Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-03 (Phase 4+5) entry.
Ledger key: `27-2-the-data-plane-honours-its-data-root-and-fetches-what-it-claims`.
Ledger status at mint: `backlog`.
Deps: —.
Surface: `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/` (`vcs_sources.py`, `request_datasets.py`, `refresh.py`, `core_sources.py`, `identity_sources.py`, `basilisk.py`, `upstream_discovery.py`), `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/` (`vcs_health/`, `upstream_discovery/`, `pypi_intelligence/`), `src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/definitions.py`, `src/shared/packages/pyforge-atlas/conf/base/` (`catalog.yml`, `globals.yml`, `parameters.yml`), `src/shared/packages/pyforge-atlas/tests/` (`pipelines/`, `parity/`, `catalog/`), `src/shared/packages/pyforge-atlas/README.md`, the `pyforge-atlas-bootstrap` task description (member or root `pixi.toml`, with `environment.yaml` regenerated if the root changes), `.github/workflows/pyforge-station-tests.yml` (the atlas job), `planning-artifacts/specs/spec-20-6-upstream_discovery-identity-join-and-export-parquet.md` (a Spec Change Log line only), the atlas deferred-work ledger.
Minted 2026-10-03 from the operator's Phase 4+5 ruling (open medium and low deferrals fixed together, split by package area, at most about 30 rows per story).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
