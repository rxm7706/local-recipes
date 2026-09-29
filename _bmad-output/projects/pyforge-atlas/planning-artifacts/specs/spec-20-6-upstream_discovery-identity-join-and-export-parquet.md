---
title: 'upstream_discovery identity join and export Parquet (Story 21.6, CAP-3)'
type: 'feature'
created: '2026-08-30'
status: 'done'
baseline_revision: '2fa0d73abc1f701f60b46bf9f81deca3f90555c5'
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/identity-contract.md'
warnings: ['oversized']
deferred:
  - summary: >-
      No Atlas dataset yet carries a per-package source_repository_url, so
      from_inventory's git-purl fallback branch never fires against real
      production data (only against synthetic parity-fixture values).
    evidence: |-
      _id_universe_frame (nodes.py) hardcodes source_repository_url="" for
      every row because no catalog entry supplies it today; the git-purl
      transform logic (_id_git_purl, _id_from_inventory) is ported and
      unit-tested but structurally unreachable through the real
      build_identity_packages_primary entry point until a future story adds
      that column to some Atlas source.
    location: >-
      src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/upstream_discovery/nodes.py:_id_universe_frame
    severity: medium
  - summary: >-
      StagedRecipesPRDataset's per-open-PR files() fetch only reads the first
      100 changed files per PR, so the file-path ranking tier is incomplete
      for PRs with more than 100 files.
    evidence: |-
      _do_refresh's files-fanout loop issues one GET per open PR
      (`.../pulls/{number}/files?per_page=100`) with no pagination loop, unlike
      the PR-listing fetch above it which does paginate. Most single-recipe
      PRs have far fewer than 100 files, so this is a narrow, currently-cold
      edge (bulk/mass staged-recipes PRs), not a general regression.
    location: >-
      src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/identity_sources.py:StagedRecipesPRDataset._do_refresh
    severity: low
  - summary: >-
      discovery_local_recipes_raw's Local_Recipes_URL always points at
      github.com/rxm7706/local-recipes regardless of the new
      PYFORGE_ATLAS_LOCAL_RECIPES_DIR override, so pointing the override at a
      different checkout would still generate URLs into this repo.
    evidence: |-
      _LOCAL_RECIPES_TREE_URL_TEMPLATE is a module-level constant hardcoding
      the repo slug; only the scanned filesystem path is configurable. Narrow
      in practice — the override is documented for pointing at an alternate
      path within this same repo (e.g. test fixtures), not a different GitHub
      repo.
    location: >-
      src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/identity_sources.py:_LOCAL_RECIPES_TREE_URL_TEMPLATE
    severity: low
  - summary: >-
      spec Code Map's instruction to update tests/parity/test_parity_complete.py
      node counts does not apply — that file's _PIPELINES tuple never included
      upstream_discovery to begin with, in this story or any prior one.
    evidence: |-
      Verified by reading tests/parity/test_parity_complete.py: _PIPELINES =
      ("core", "vcs_health", "pypi_intelligence", "vulnerability"). This is a
      pre-existing inaccuracy in the spec's own Code Map, not something this
      story's diff broke or needs to fix.
    location: >-
      src/shared/packages/pyforge-atlas/tests/parity/test_parity_complete.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** `scripts/conda-forge-packaging-inventory-operations_openteams_identity.py`
(the legacy quartet's identity script) owns four separate live-fetch/parse surfaces —
PURL Associator mappings index, OpenTeams project 1 GraphQL board, conda-forge/
staged-recipes PR REST API, and a local `recipes/` filesystem scan — plus the whole
identity join (`lookup_assoc` / `from_assoc` / `from_inventory` / `from_board_only` /
`attach_packaging_urls` / `overlay_live_local`), entirely inside a `scripts/` file. None
of it is catalog-declared, none of it is dataset-owned IO (AD-2), and none of it
materializes as Parquet a downstream consumer (Epic 22 Vizro, Epic 23 complete export)
can read directly. CAP-3 / Phase D (`SPEC.md`) requires this join to move into
`upstream_discovery` as catalog-owned Parquet, reproducing `lookup_assoc` /
`from_assoc` / `from_inventory` / `from_board_only` parity on a fixed fixture corpus
(`identity-contract.md`).

**Approach:** Extend the EXISTING `upstream_discovery` pipeline (no 9th pipeline) with
four new dataset-owned source catalog entries — `purl_associator_mappings_raw`,
`openteams_project_1_board_raw`, `discovery_staged_recipes_prs_raw`,
`discovery_local_recipes_raw` — and two new pure join/shape nodes producing
`identity_packages_primary` (the 18-column "identity tab minimum") and
`identity_export_parquet` (the full `GIST_SCHEMA` shape, ranking/JFROG columns present
but null). Port `lookup_assoc` / `from_assoc` / `from_inventory` / `from_board_only` /
`attach_packaging_urls` / `overlay_live_local` from the legacy script (verified present
at `scripts/conda-forge-packaging-inventory-operations_openteams_identity.py`, lines
249-889) with identical logic, expressed as pandas operations over `DataFrame`
catalog inputs instead of `dict` rows over an XLSX tab, verified against a parity
fixture corpus covering every scenario `identity-contract.md`'s Parity test corpus
section names.

## Boundaries & Constraints

**Always:**
- Phase D extends `upstream_discovery` only — append nodes to the existing
  `create_pipeline()` in `pipelines/upstream_discovery/pipeline.py`; do not create a new
  pipeline package (SPEC.md Constraints, epic-21-context.md Technical Decisions).
- All fetch/parse/rate-limit/fallback IO for the three new *live* sources lives in
  `pyforge.atlas.datasets.*` (AD-2); the join/shape nodes stay pure `DataFrame ->
  DataFrame` (mirrors `classify_trending_candidates`, `nodes.py` lines 275-373).
- Every new external-refresh dataset degrades via last-good Parquet + `StalenessMarker`,
  never raises, never silently substitutes a different source (AD-13) — mirrors
  `TrendingSnapshotDataset` (`datasets/upstream_discovery.py` lines 207-351).
- `purl_associator_mappings_raw` fetches `mappings-index.json` at refresh time; per-package
  shards (for `alternative_purls` / `cpes`) are fetched on demand, not eagerly for the
  whole index (`identity-contract.md` Source datasets table: "Index required at
  bootstrap; shards fetched on demand").
- `openteams_project_1_board_raw` and `discovery_staged_recipes_prs_raw` both carry
  `credentials: github_token` — the one existing per-host credential covering GitHub
  GraphQL/REST (`conf/local/credentials.yml` already declares it; `vcs_github_api_raw`
  is the existing consumer). Do not invent a second GitHub credential key.
- The join reproduces `lookup_assoc` (PEP 503 key + `-`/`.`/`_` alias fallback),
  `from_assoc` / `from_inventory` / `from_board_only`, `attach_packaging_urls`, and
  `overlay_live_local` semantics exactly (`identity-contract.md` Join semantics 1-7)
  against the fixed parity fixture corpus (`identity-contract.md` Parity test corpus).
- `identity_export_parquet` carries the FULL `GIST_SCHEMA` column set (legacy script
  lines 84-120, the `GIST_SCHEMA`/`GIST_COLUMNS` constants) in the same order; ranking/
  JFROG columns (`P`, `Rank`, `Score`, `Work`, `Platforms`, `Apps`, `Downloads`,
  `Versions`, `Vuln`, `Priority_Bucket_Description`, `Priority_Source`,
  `Priority_Reason`, `JFROG_risk_level`, `JFROG_latest_vuln_count`,
  `internal_component_count`, `internal_lob_count`) are declared present but null —
  never fabricated; merged later by `priority.py` at gist-publish time (out of this
  story — Epic 21 boundary; Epic 23.5 completes the export).
- `kedro-catalog-check`, `parity-diff`, and `kedro-test` stay green throughout.
- Every new override/credential surface addition gets its accounting comment AND its
  test constant updated together: `globals.yml`'s override-count header comment, and
  `tests/catalog/conftest.py`'s `EXPECTED_EXTRA_OVERRIDES` / `PATHS_ENV_VARS` /
  `EXPECTED_ENV_OVERRIDE_SURFACE` / `CREDENTIAL_ALLOWLIST` — mirrors how every prior
  override addition in this catalog was landed (e.g. `BASILISK_BASE_URL`,
  `vcs_github_api_raw`'s `github_token` entry).

**Block If:**
- The enterprise "CDO-ENT-JFROG ∪ CDO-ENT-CONDA" consumption-universe Parquet
  (`identity-contract.md` Join semantics step 1) is Story 21.5's (Tier 2, `epics.md`
  lists `S-21.5` as this story's own `Deps:`) deliverable and is **not yet landed** —
  verified: only `spec-21-1` and `spec-21-2` exist under `planning-artifacts/specs/`
  today, and `catalog.yml` has no `discovery_about_maintainers_raw` / Tier-2 entry.
  `artifactory_downloads_raw` / `artifactory_downloads_joined` exist (Epic 15, Story
  15.3) but carry only the names that story wired, not the full enterprise-consumption
  union — `SPEC.md`'s own `open_questions` still flags "CDO-ENT-JFROG universe names
  via `artifactory_downloads` live fetch — confirm attended credential path before
  Story 21.5 lands." **Do not fabricate a substitute enterprise universe.** If Story
  21.5 has landed by the time this story is implemented, join `identity_packages_primary`
  against its output directly. If it has not, join against the broadest available
  *public*-verification signal instead: `pypi_universe` (existing catalog entry)
  restricted to rows where `PyPI_Verified` (`pypi_simple_index_raw` / `pypi_json_raw`)
  or `CondaForge_Verified` (`core_channeldata_raw` / `pypi_conda_mapping`) is true —
  exactly the mapping `verification-matrix.md` already documents for those two fields,
  both already live/cataloged today. Record the substitution as a `deferred` finding
  naming Story 21.5 as the owner of narrowing this to the true enterprise universe.
  This keeps the join runnable without inventing enterprise-scoped data that does not
  exist in the codebase.

**Never:**
- Do not add a 9th pipeline package.
- Do not write to the pinned identity gist or call any `gh gist` / `gh issue create`
  mutation from Atlas — gist publish, ranking merge, and issue creation stay
  quartet-owned (CAP-4 / SPEC.md Non-goals). `publish_gist_files` / `create_missing_issues`
  (legacy script lines 1161-1235, 358-440) are **not** ported.
- Do not port `write_gist_markdown` / `write_dashboard_markdown` / canvas-writing logic
  (legacy script lines 974-1235) — dashboard/canvas generation stays quartet-owned
  through Epic 21; CAP-7 (Epic 22) is the parallel Vizro track, not this story.
- Do not port ranking (`P` / `Rank` / `Score` / `Work`) or JFROG telemetry computation —
  Epic 23.2 / 23.3 territory (`SPEC.md` Constraints).
- Do not wire real `(conda_name, identifier)` batches into the 10 dormant `vcs_health`
  GitHub/GitLab/Codeberg/registry refresh-trigger nodes. `spec-21-2`'s own `deferred`
  entries name this story as a plausible future *consumer* of resolved identities, but
  wiring those batches is a `vcs_health` pipeline change — out of this
  `upstream_discovery`-only story's scope (`invoke_dev_with`: "Extend upstream_discovery
  only; no 9th pipeline"). Leave it deferred; do not expand scope to close it here.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Associator hit | Universe row's name (or a `-`/`.`/`_` alias) found in `purl_associator_mappings_raw`'s packages index | `identity_source="purl-associator"`, `associator_key`=matched alias, `primary_purl`/`primary_type`/`alternative_purls`/`cpes` from the associator record, `conda_purl` carried from the universe row when present | Never raises; a per-package shard fetch failure (`alternative_purls`/`cpes`) degrades those two columns to empty for that row, never a row drop |
| Inventory-derived fallback | No associator hit; a `PyPI_PURL` and/or a recognizable `Source_Repository_URL` (github/gitlab/bitbucket) is present on the universe row | `identity_source="inventory"`, `associator_status="inventory-derived"`, `primary_purl`=PyPI purl or derived git purl (github/gitlab/bitbucket only), `alternative_purls` includes the other when both exist | An unrecognized/malformed source host degrades `git_purl` to `None`, never raises |
| Unmapped (none) | No associator hit, no `PyPI_PURL`, no recognizable source URL | `identity_source="none"`, `associator_status="unmapped"`, `primary_purl=""`; row is still emitted | Never a silent drop |
| Board-only extra | `openteams_project_1_board_raw` has a `[Conda-Forge Packaging] {name}` issue whose PEP-503 name is absent from the universe | A new row is appended: `identity_source="openteams-board"`, `OpenTeams_Issue_URL` set, associator re-checked for this name too (mirrors `from_board_only`) | A duplicate board name (same PEP-503 key) across multiple issues keeps the FIRST issue URL seen, never overwritten |
| `conda_purl` only when CondaForge_Verified | A universe row present in `core_channeldata_raw` / `pypi_conda_mapping` (conda-forge-verified) vs. one absent from both | `conda_purl` populated only for the verified row; empty for the unverified row | n/a |
| Overlay URLs — feedstock + metadata + staged PR + local recipes | `core_feedstock_attribution` has a feedstock for the name; `discovery_staged_recipes_prs_raw` has an open/merged PR touching `recipes/<name>/` or matching the name via title-parse; `discovery_local_recipes_raw` has a local `recipes/<name>/recipe.yaml` | `Conda-Forge_FeedStock_URL`, `Conda-Forge_Metadata_URL`, `Staged_Recipes_PR_URL`, `Local_Recipes_URL`, `Local_Build_Status` all populated per `attach_packaging_urls`/`overlay_live_local` precedence (open PR ranked above merged above closed; file-path match ranked above title-parse match) | A malformed/absent CFE `cfe-local-build-status` stamp leaves `Local_Build_Status` blank, never fabricated |
| PURL Associator fetch fails | `purl_associator_mappings_raw` endpoint unreachable on a DUE refresh | Every universe row falls through to `from_inventory`/`from_board_only` (identical to an always-empty associator index); last-good Parquet (if any) is kept, `StalenessMarker` set | Never raises |
| OpenTeams board fetch fails / paginates incompletely | `openteams_project_1_board_raw` GraphQL call fails partway through cursor pagination | Board-only extras and the `OpenTeams_Issue_URL` overlay both degrade to whatever was already accumulated before the failure (or empty); last-good store kept, staleness marked; the universe-row join still proceeds using inventory/associator data alone | Never raises |
| `identity_export_parquet` shape | `identity_packages_primary` non-empty | Output carries the FULL `GIST_SCHEMA` column order: the 18 core columns populated, every ranking/JFROG column present as null | An empty `identity_packages_primary` yields an empty frame carrying the full schema, not a missing/absent file |
| Enterprise universe not yet available | Story 21.5 has not landed (see Block If) | Join falls back to the `PyPI_Verified ∪ CondaForge_Verified` public universe; a `deferred` finding records the narrowing gap | Never raises; never fabricates enterprise-only rows |

</intent-contract>

## Code Map

- `scripts/conda-forge-packaging-inventory-operations_openteams_identity.py` — the parity
  target (verified present in the live repo). `lookup_assoc` (~L249-255), `pep503_name`
  (~L258-259), `git_purl` (~L222-236), `from_assoc` (~L802-821), `from_inventory`
  (~L824-854), `from_board_only` (~L857-889), `attach_packaging_urls` (~L779-799),
  `overlay_live_local` (~L686-710) + helpers `load_local_recipes` (~L625-651) /
  `load_local_build_status` (~L654-683), `load_feedstock_outputs` (~L488-509),
  `load_staged_prs` (~L534-622) + `names_from_pr_title` (~L512-531),
  `fetch_project_issues` (~L300-336) + `board_packaging_urls` (~L339-350),
  `GIST_SCHEMA`/`GIST_COLUMNS` (~L84-121), `COLUMNS` (~L47-66), `ASSOCIATOR_URL`
  (~L79), `FEEDSTOCK_OUTPUTS_URL` (~L122-125), `STAGED_PR_API` (~L151). Do NOT port
  `write_gist_markdown` / `write_dashboard_markdown` / `publish_gist_files` /
  `create_missing_issues` (Boundaries "Never").
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/upstream_discovery/pipeline.py`
  — append new nodes to the existing `create_pipeline()` (currently 4 nodes, L31-69).
- `.../pipelines/upstream_discovery/nodes.py` — add `refresh_purl_associator_store` /
  `refresh_openteams_board_store` / `refresh_staged_recipes_prs_store` (pure
  `params -> RefreshRequest` triggers, mirror `refresh_trending_candidates`, L44-55) plus
  `build_identity_packages_primary` / `build_identity_export_parquet` (pure
  join-then-DataFrame nodes, mirror `classify_trending_candidates`'s style, L275-373).
- `.../datasets/upstream_discovery.py` — `TrendingSnapshotDataset` (L207-351) is the
  exact "live + AD-13" shape `PurlAssociatorMappingsDataset` mirrors: `ExternalRefreshDataset`
  subclass, injected `fetcher`, atomic write, `StalenessMarker`, empty-result-falls-back
  pattern (mirrors the daily-scrape -> Search-API-fallback shape for the
  index-then-shards two-tier fetch).
- NEW `.../datasets/identity_sources.py` (proposed name — implementer's call whether to
  colocate in `upstream_discovery.py` instead) — `PurlAssociatorMappingsDataset`,
  `OpenTeamsBoardDataset`, `StagedRecipesPRDataset`, `LocalRecipesOverlayDataset`.
- `.../datasets/request_datasets.py::GitHubRequestDataset` (L318-541) — the credentialed
  GraphQL POST + `_ParquetRefreshStore` precedent `OpenTeamsBoardDataset` mirrors for
  credential wiring (`credentials: github_token`) and last-good persistence; NOT its
  per-repo batching shape — `OpenTeamsBoardDataset` needs cursor pagination over a single
  `organization.projectV2.items` query (mirrors `fetch_project_issues`, legacy script
  L300-336), a different fetch shape entirely.
- `.../datasets/refresh.py` — `ExternalRefreshDataset` (L170+), `RefreshRequest` /
  `StalenessMarker` (L105-167), `DAILY_SECONDS` / `WEEKLY_SECONDS` (L76-81),
  `MappingCacheDataset` (L560+) — the never-clobber-on-empty `save()` pattern to mirror
  for any of the four new datasets that merge onto a prior snapshot rather than fully
  replacing it.
- `conf/base/catalog.yml` — append to the existing `upstream_discovery` block (currently
  L852-919): `purl_associator_mappings_raw`, `openteams_project_1_board_raw`,
  `discovery_staged_recipes_prs_raw`, `discovery_local_recipes_raw` (layer `raw`),
  `identity_packages_primary` (layer `primary`), `identity_export_parquet` (layer
  `derived`, plain `pandas.ParquetDataset`).
- `conf/base/globals.yml` — add `extra_overrides.PURL_ASSOCIATOR_BASE_URL`
  (`https://prefix-dev.github.io`, a new host — NOT one of the 20 helper-backed
  `endpoint_bases`; mirrors how `ANACONDA_API_BASE_URL`/`OSV_VULNS_BUCKET_URL` were
  added, L62-65). Reuse the EXISTING `GITHUB_API_BASE_URL` (L42) for both
  `openteams_project_1_board_raw` (GraphQL) and `discovery_staged_recipes_prs_raw`
  (REST) — no second GitHub override point. Add
  `paths.local_recipes_dir: ${env_or:PYFORGE_ATLAS_LOCAL_RECIPES_DIR,recipes}`
  (repo-root-relative, mirrors the existing P9 convention, L104-109) for
  `discovery_local_recipes_raw`. Update the file's own override-count header comment
  (currently "20 + 3 + 3 + 5 = 31", L12-22) to the new total (33: extra_overrides 3->4,
  paths 5->6).
- `conf/base/parameters.yml` — add `ttls.purl_associator_mappings_raw`,
  `ttls.openteams_project_1_board_raw`, `ttls.discovery_staged_recipes_prs_raw` cadence
  entries (mirrors `ttls.trending_candidates`, L53).
- `conf/local/credentials.yml` — no new key; both new credentialed entries reuse the
  existing `github_token` stub (verified present: `token: mock-github-token`).
- `tests/catalog/conftest.py` — `EXPECTED_EXTRA_OVERRIDES` (L174-178, add
  `PURL_ASSOCIATOR_BASE_URL`), `PATHS_ENV_VARS` (L193-196, add `local_recipes_dir` ->
  `PYFORGE_ATLAS_LOCAL_RECIPES_DIR`), `EXPECTED_ENV_OVERRIDE_SURFACE` (L212, 31 -> 33),
  `CREDENTIAL_ALLOWLIST` (L218-221, add `openteams_project_1_board_raw` and
  `discovery_staged_recipes_prs_raw` -> `github_token`).
- `tests/pipelines/upstream_discovery/test_nodes.py` (exists) — extend with the parity
  fixture corpus, one test per I/O & Edge-Case Matrix row above.
- `tests/datasets/test_upstream_discovery.py` (exists) — extend, or add a sibling
  `test_identity_sources.py`, with unit coverage for the four new dataset classes'
  fetch/degrade/persist behavior (mirrors `TrendingSnapshotDataset`'s existing test
  shape in the same file).
- `tests/parity/fixtures/` — currently `core/`, `pypi_intelligence/`, `vcs_health/`,
  `vulnerability/` subdirs only (verified: no `upstream_discovery/` subdir exists yet);
  add one carrying the fixed parity corpus (associator hit / inventory-derived /
  board-only / unmapped / conda_purl-verified / overlay-URLs fixture rows) that
  `identity-contract.md`'s Parity test corpus names.
- `tests/pipelines/test_dag_resolves.py` / `tests/parity/test_parity_complete.py` —
  node-count updates (mirrors `spec-21-2`'s own Files-changed pattern for this pair).
- NOTE — `tests/artifactory/test_identity_join.py` (`pyforge.atlas.artifactory.join_identity`)
  is a DIFFERENT, unrelated identity join (JFROG download-row conda-name resolution,
  Epic 15/19-scoped CAP-2/CAP-3 labels reused across epics) — do not confuse it with this
  story's OpenTeams identity join or reuse its fixtures.

## Tasks & Acceptance

**Execution:**
- `datasets/identity_sources.py` (new) — `PurlAssociatorMappingsDataset(ExternalRefreshDataset)`:
  fetches `mappings-index.json` via an injected fetcher (mirrors `TrendingSnapshotDataset`),
  persists the packages index as Parquet; exposes a second method (`fetch_shard(key)` or
  similar) for the on-demand per-package shard fetch (`alternative_purls`/`cpes`) — called
  from the join node, not eagerly for the whole index.
- Same file — `OpenTeamsBoardDataset(ExternalRefreshDataset)`: cursor-paginated GraphQL
  fetch of `organization(login: "OpenTeams-WFT-CDO") { projectV2(number: 1) { items } }`
  (mirrors `fetch_project_issues`), `credentials: github_token`, persists issue rows
  (number/title/url/state/milestone) as Parquet; a partial-pagination failure keeps
  whatever pages succeeded (or last-good) rather than raising.
- Same file — `StagedRecipesPRDataset(ExternalRefreshDataset)`: REST fetch of
  `conda-forge/staged-recipes` PRs (paginated `--jq` shape mirrors `STAGED_PR_API`) plus
  the open-PRs-with-files listing (mirrors `load_staged_prs`), `credentials: github_token`;
  persists `(number, state, merged_at, url, title, files)` rows.
- Same file — `LocalRecipesOverlayDataset(AbstractDataset)`: plain filesystem read (no
  cadence/staleness needed — a local repo-tree walk is cheap and always current) over
  `${globals:paths.local_recipes_dir}`, extracting per-recipe-dir name aliases (dir name +
  names parsed from `recipe.yaml`/`meta.yaml`), the GitHub tree URL, and the CFE
  `cfe-local-build-status` stamp (mirrors `load_local_recipes` + `load_local_build_status`
  combined into one row-per-recipe-dir frame).
- `pipelines/upstream_discovery/nodes.py` — three new pure refresh-trigger nodes (mirror
  `refresh_trending_candidates`); `build_identity_packages_primary(purl_associator_mappings_raw,
  openteams_project_1_board_raw, discovery_staged_recipes_prs_raw, discovery_local_recipes_raw,
  core_feedstock_attribution, <universe input per Block If>)` implementing `lookup_assoc` /
  `from_assoc` / `from_inventory` / `from_board_only` / `attach_packaging_urls` /
  `overlay_live_local` parity, one row per universe package + board-only extras, never a
  silent drop; `build_identity_export_parquet(identity_packages_primary)` reshaping to the
  full `GIST_SCHEMA` column order with ranking/JFROG columns null.
- `pipelines/upstream_discovery/pipeline.py` — append the 5 new nodes (3 refresh triggers +
  2 join/shape nodes) to `create_pipeline()`'s existing node list.
- `conf/base/catalog.yml`, `conf/base/globals.yml`, `conf/base/parameters.yml`,
  `tests/catalog/conftest.py` — wire the new catalog entries, override points, cadences,
  and test constants exactly as itemized in the Code Map above.
- Tests: extend `tests/pipelines/upstream_discovery/test_nodes.py` (one test per I/O &
  Edge-Case Matrix row), extend/add dataset unit tests, add the
  `tests/parity/fixtures/upstream_discovery/` fixture corpus, update
  `test_dag_resolves.py` / `test_parity_complete.py` node counts.
- Run `pixi run -e pyforge-atlas kedro-catalog-check`, `kedro-test`, and `parity-diff` —
  confirm all green.

**Acceptance Criteria:**
- Given the fixed parity fixture corpus (associator hit, inventory-derived fallback,
  board-only extra, unmapped/none, conda_purl-only-when-verified, overlay URLs from
  feedstock + staged PR + local recipes), when `build_identity_packages_primary` runs,
  then every row's `identity_source` / `associator_key` / `associator_status` /
  `primary_purl` / `primary_type` / `alternative_purls` / `cpes` / `conda_purl` /
  `source_repository_url` / `OpenTeams_Issue_URL` / feedstock+metadata+staged+local URL
  columns / `Local_Build_Status` match the legacy script's `lookup_assoc` / `from_assoc` /
  `from_inventory` / `from_board_only` / `attach_packaging_urls` / `overlay_live_local`
  output exactly for the same inputs.
- Given `identity_packages_primary` non-empty, when `build_identity_export_parquet` runs,
  then the output carries the full `GIST_SCHEMA` column order (identity-contract.md Export
  columns + ranking/JFROG columns), with ranking/JFROG columns null on every row.
- Given a fetch failure on any of the three new live sources (PURL Associator, OpenTeams
  board, staged-recipes PRs), when the refresh-trigger node runs, then last-good Parquet
  is kept, `StalenessMarker` is set, and the join node still completes using whatever data
  is available — never raises.
- Given `pixi run -e pyforge-atlas kedro-catalog-check`, `kedro-test`, and `parity-diff`,
  when run after this story, then all three pass, including the new
  `EXPECTED_ENV_OVERRIDE_SURFACE` / `EXPECTED_EXTRA_OVERRIDES` / `CREDENTIAL_ALLOWLIST`
  assertions.
- Given Story 21.5 has not landed at implementation time, when the join resolves its
  universe input, then it uses the `PyPI_Verified ∪ CondaForge_Verified` public-universe
  substitute (Block If) and records a `deferred` finding naming Story 21.5 as the owner
  of narrowing it to the true enterprise universe — the join must not fabricate
  enterprise-scoped rows or silently claim full CDO-ENT parity it cannot yet deliver.

## Design Notes

The AD-13 never-clobber pattern every new dataset follows (mirrors `MappingCacheDataset.save()`
and `TrendingSnapshotDataset._do_refresh`/`load()`): a DUE refresh that fails, or a refresh
producing an empty result, must never overwrite last-good data — mark stale and return
last-good, or atomically write + clear the stale marker only on a genuinely non-empty
success. A store with no last-good yet degrades to an empty-but-correctly-columned frame,
marked stale, matching every existing `ExternalRefreshDataset` subclass's first-run shape.

`identity_export_parquet`'s column order matters: it is the contract Epic 21's gist publish
(future, out of this story) and Epic 23.5's `identity_complete_export.parquet` both key off
by name — declare the full `GIST_SCHEMA` order once (as a module-level constant, mirroring
the legacy `GIST_COLUMNS` list) rather than re-deriving it ad hoc in the node.

The PURL Associator's two-tier fetch (index required at bootstrap, shards on demand) is a
genuinely different shape from `TrendingSnapshotDataset`'s "fetch 3 fixed URLs, fall back to
a 4th" pattern — `PurlAssociatorMappingsDataset` needs an index-only `_do_refresh` (persisted
like every other `ExternalRefreshDataset`) plus a separate, uncached-by-`ExternalRefreshDataset`
per-package shard fetch method the join node calls only for rows it actually needs
`alternative_purls`/`cpes` for — do not eagerly fetch every shard for the whole universe on
every run (identity-contract.md's own "shards fetched on demand" language is explicit about
this).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass, including the updated
  `EXPECTED_ENV_OVERRIDE_SURFACE` (33) / `EXPECTED_EXTRA_OVERRIDES` (+
  `PURL_ASSOCIATOR_BASE_URL`) / `CREDENTIAL_ALLOWLIST` (+ 2 entries) assertions.
- `pixi run -e pyforge-atlas kedro-test` — expected: the new
  `tests/pipelines/upstream_discovery/test_nodes.py` parity-corpus tests and the new/extended
  dataset unit tests all pass; no regression in the existing 4-node `upstream_discovery`
  suite.
- `pixi run -e pyforge-atlas parity-diff` — expected: stays green (unrelated pipelines
  unaffected); if a fixture-mode parity check is added for `identity_export_parquet` vs. a
  frozen legacy-script output, it passes too.
- `kedro run --pipelines upstream_discovery` on fixture-backed catalog inputs — expected:
  exit 0, `identity_packages_primary` and `identity_export_parquet` both materialize with
  the documented schemas.

## Review Triage Log

### 2026-08-30 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7 (high 1, medium 3, low 3)
- defer: 4 (medium 1, low 3)
- reject: 9
- addressed_findings:
  - `[high]` `[patch]` `paths.local_recipes_dir` default (`globals.yml`) resolves relative to the kedro project dir (`src/shared/packages/pyforge-atlas`), the actual cwd of the only documented invocation (`pyforge-atlas-bootstrap` pixi task) — not the repo root where `recipes/` lives, so `discovery_local_recipes_raw` silently always resolves empty in every real run. Fixed the default to `../../../../recipes`.
  - `[medium]` `[patch]` No test guarded `enterprise_jfrog_names` (read for the first time by `build_identity_packages_primary`) staying produced by a pipeline in the documented bootstrap set — a future edit dropping `artifactory_downloads` from `pyforge-atlas-bootstrap`'s `--pipelines` list would crash with no test failure. Added a DAG-completeness assertion.
  - `[medium]` `[patch]` `LocalRecipesOverlayDataset.load()`'s `recipes_dir.iterdir()` walk was unguarded against `OSError` (e.g. a permission-denied directory), contradicting the class's own never-raise contract. Wrapped it to degrade to an empty frame.
  - `[medium]` `[patch]` `parse_purl_associator_index`'s `alternative_purls`/`cpes` extraction iterated the raw JSON value without checking it is a list first — a malformed upstream payload (string instead of list) would char-split into fabricated single-character entries. Added a list-type guard, degrading to `[]` otherwise.
  - `[low]` `[patch]` `_id_universe_frame` always preferred `conda_name` over `pypi_name` when both are present on an `enterprise_jfrog_names` row, discarding the PyPI identity whenever the two names normalize to different PEP-503 keys (currently dormant — `artifactory.virtual_repos` defaults to `[]` — but a real gap once enterprise JFrog activates). Now registers both names' keys.
  - `[low]` `[patch]` Three bounded fetch loops (`OpenTeamsBoardDataset`'s 500-page cap, `StagedRecipesPRDataset`'s 200-page cap and 500-PR open-files fan-out cap) truncated silently on hitting their cap, unlike every other degrade path in `identity_sources.py` which logs a `logger.warning`. Added warnings on cap-hit.
  - `[low]` `[patch]` `_id_metadata_url` interpolated the package name into a URL with no encoding; a name containing `/`, `?`, `&`, or spaces would produce a malformed URL. Wrapped the segment in `urllib.parse.quote`.

Findings investigated and rejected after verification: `PurlAssociatorMappingsDataset.fetch_shard` being unwired from the join is correct, not a gap — the module's own investigation confirmed the legacy parity target (`lookup_assoc`/`from_assoc`) never performs a second/shard fetch either, so wiring it would break byte-for-byte parity with the legacy script, the story's primary mandate; `_id_pep503` vs. `_normalize_pypi_name` stripping-behavior mismatch is real but requires a leading/trailing-hyphen package name to manifest (negligible in practice, already documented as deliberate); `_ID_GIT_HOST_RE` matching `codeberg.org` while `_id_git_purl` returns `None` for it is spec-compliant — the I/O matrix scopes "recognizable" source URLs to github/gitlab/bitbucket only; duplicate `assoc_key` last-wins is structurally unreachable (the JSON source object has unique keys and the store is replaced, not merged, on each refresh); the untracked parity-fixture test files flagged by the verification-gap reviewer are resolved automatically by this step's own Finalize (all reviewed-diff files get committed); the remaining rejects (`LocalRecipesOverlayDataset` per-run scan cost, no reciprocal legacy-script comment, no fixture for conflicting `conda_purl` values, uniform weekly TTL cadence across the three new sources) are non-behavioral/informational observations with no test or contract impact.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `20-6-upstream_discovery-identity-join-and-export-parquet: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `in-review` → `done` (ledger row `20-6-upstream_discovery-identity-join-and-export-parquet: done`).
- `## Auto Run Result` reconstructed from git (none survived).
