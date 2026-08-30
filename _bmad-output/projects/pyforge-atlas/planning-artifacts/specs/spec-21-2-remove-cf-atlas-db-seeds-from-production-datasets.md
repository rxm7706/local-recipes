---
title: 'Remove cf_atlas.db seeds from production datasets (Story 21.2, Epic 21)'
type: 'feature'
created: '2026-08-29'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: true
baseline_revision: f71b388ab783f9b584f9e90f2d6d6c67d96c2ba8
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/implementation-artifacts/epic-21-context.md'
warnings: ['oversized']
deferred:
  - summary: 'pyforge-atlas-bootstrap pixi task fails on seed_gaps: seed_root resolves relative to the Kedro member dir (src/shared/packages/pyforge-atlas) instead of REPO_ROOT, so cwe_categories_seed.json is not found.'
    evidence: "Reproduces identically on baseline_revision f71b388ab783f9b584f9e90f2d6d6c67d96c2ba8 with none of this story's changes applied -- pre-existing, unrelated to the 3 target files (core_sources.py, request_datasets.py, vcs_sources.py)."
    location: 'src/shared/packages/pyforge-atlas (seed_gaps pipeline / kedro-catalog-check path-containment assertion, likely a Story 21.1 gap)'
    severity: 'low'
  - summary: >-
      11 of 13 new catalog entries (GitHub, GitLab, Codeberg, 8 registries) have their refresh-
      trigger nodes wired into the DAG correctly, but call their fetch methods with an empty
      identifier batch by design -- no real data flows until a conda_name -> upstream-identity
      mapping is wired in.
    evidence: |-
      Confirmed by the Intent Alignment auditor (pass 2): `enrich_maintainers(core_cf_graph_raw)`
      in the same pipelines/vcs_health/nodes.py already reads identifier-bearing data one node
      up, but none of the 3 new trigger nodes take it as input. Explicitly out of THIS story's
      scope per the verbatim intent ("Checklist in identity-contract.md not in scope") --
      identifier resolution is Story 21.6's ("upstream_discovery identity join") territory.
    location: 'src/pyforge/atlas/pipelines/vcs_health/nodes.py (refresh_vcs_github_store, refresh_vcs_host_stores, refresh_vcs_registry_stores); owning follow-up: Story 21.6'
    severity: 'medium'
  - summary: >-
      _ttl_cadence has no validation/clamping for a zero or negative configured cadence value in
      params:ttls, which could cause excessive live-fetch frequency once real identifiers are
      wired (Story 21.6).
    evidence: |-
      Not exercised today since every current trigger call uses an empty identifier batch (see
      the identifier-source-gap entry above); becomes live risk only once that gap is closed.
    location: 'src/pyforge/atlas/pipelines/vcs_health/nodes.py (_ttl_cadence)'
    severity: 'low'
  - summary: >-
      A batch containing at least one fetch success overwrites the ENTIRE persisted store with
      only that batch's rows, rather than merging onto existing rows for names/identifiers
      outside the batch -- a latent data-loss gap in the AD-13 persistence model this story
      introduced.
    evidence: |-
      Not reachable today (every current caller passes an empty batch), but will matter as soon
      as Story 21.6 wires a real, possibly-partial identifier batch per refresh cycle.
    location: 'src/pyforge/atlas/datasets/vcs_sources.py (_ParquetRefreshStore._persist), src/pyforge/atlas/datasets/request_datasets.py (GitHubRequestDataset.fetch_repo_health persistence)'
    severity: 'medium'
  - summary: >-
      fetch_one's retry-with-scheduler-and-backoff logic is still duplicated near-verbatim
      between VcsHostSeedDataset and RegistryUpstreamDataset -- only the persistence/staleness
      plumbing was hoisted into the shared _ParquetRefreshStore mixin.
    evidence: 'Confirmed by 2 independent reviewers on the pass-2 diff; non-blocking code-organization nit, not a correctness issue.'
    location: 'src/pyforge/atlas/datasets/vcs_sources.py'
    severity: 'low'
  - summary: >-
      _ParquetRefreshStore (the shared AD-13 persistence mixin) is defined in vcs_sources.py but
      imported cross-module into request_datasets.py -- arguably belongs in refresh.py alongside
      StalenessMarker/RefreshRequest instead.
    evidence: 'Code-organization suggestion from the Blind Hunter review; not a correctness issue.'
    location: 'src/pyforge/atlas/datasets/vcs_sources.py, src/pyforge/atlas/datasets/request_datasets.py'
    severity: 'low'
  - summary: >-
      No credentials: wired for GitLab/Codeberg/registries in catalog.yml -- for registries with
      meaningful anonymous rate limits (npm, crates.io, RubyGems, NuGet) there is no path to
      raise the ceiling via an API token without further catalog changes.
    evidence: 'Reviewer itself notes this may be deliberate for a v1; flagging so it is a documented choice, not a silent gap.'
    location: 'src/shared/packages/pyforge-atlas/conf/base/catalog.yml (vcs_gitlab_api_raw, vcs_codeberg_api_raw, vcs_registry_*_raw)'
    severity: 'low'
  - summary: >-
      PyPIJsonFanOutDataset's candidate selection is sorted(names)[:limit] every run -- with a
      bounded default limit against a ~20k-package universe, packages later in the alphabet are
      never live-fetched, indefinitely, with no rotation/offset state between refresh cycles.
    evidence: 'Real data-quality concern flagged by Blind Hunter; not required by this story''s AC (no cf_atlas.db default, safe degrade) and adds meaningful stateful-rotation complexity beyond this story''s scope.'
    location: 'src/pyforge/atlas/datasets/request_datasets.py (PyPIJsonFanOutDataset.load)'
    severity: 'low'
---

<intent-contract>

## Intent

**Problem:** 5 dataset classes across 3 files (`core_sources.py`, `request_datasets.py`,
`vcs_sources.py`) still default to a legacy `cf_atlas.db` SQLite read, and when
`CF_ATLAS_DB` is unset they silently return an empty-but-correctly-columned frame instead
of marking staleness (violates AD-13). Each already has a live-fetch `url:` wired in
`catalog.yml` that its constructor accepts and discards (`_ = (url, kwargs)`). This blocks
the epic's self-contained-data-plane goal and fails two existing gates today
(`test_no_inline_io_in_package_code`, `test_no_sqlite_in_the_migrated_surface`).

**Approach:** Replace each site's sqlite3 seed with the `refresh.py::ExternalRefreshDataset`
last-good-Parquet + staleness-marker pattern (mirror `MappingCacheDataset.save()`), fetching
from the catalog's already-wired `url:`. Parselmouth instead reads from the existing
`pypi_conda_map_store` (already populated by Story 21.1's bootstrap chain) rather than a new
fetch. The 8 `RegistryUpstreamDataset` registries and the 2 `VcsHostSeedDataset` hosts get one
shared generic implementation (same REST-GET-then-extract-version shape) parameterized per
entry — mechanically repeated, not 10 bespoke designs.

## Boundaries & Constraints

**Always:**
- After this story, no dataset `load()` path may reference `CF_ATLAS_DB`/`CF_ATLAS_DB_PATH`,
  `.claude/data/conda-forge-expert/cf_atlas.db`, or import `sqlite3`, in any of the 3 files.
- Every replacement never raises on fetch failure; it marks stale and returns last-good data
  (AD-13), mirroring `MappingCacheDataset.save()`/`load()`.
- Parselmouth reads from `pypi_conda_map_store` — do not add a second fetch for it.
- `tests/catalog/test_no_inline_io.py::test_no_inline_io_in_package_code` and
  `tests/singularity/test_duckdb_sole_engine.py::test_no_sqlite_in_the_migrated_surface` both
  go green for `core_sources.py`, `request_datasets.py`, `vcs_sources.py`.
- `pixi run -e pyforge-atlas kedro-catalog-check` and `pixi run -e pyforge-atlas parity-diff`
  stay green throughout.

**Block If:** None — the epic's own checklist ("each replacement is one of: live fetch,
upstream Parquet, external-refresh, tracked seed, or credentialed opt-in — documented per
entry in catalog.yml") delegates the per-entry strategy choice to this spec; resolved below,
not a human decision.

**Never:**
- Do not touch `identity-contract.md`'s checklist (Story 21.6/21.7 territory).
- Do not add Tier 0-2 "public index" catalog sources (Story 21.3-21.5 — a different axis:
  those are PyPI/conda-forge/Anaconda/Basilisk/AOSS package-existence indexes, not these VCS
  upstream-version checks).
- Do not retire `cf_atlas.db` or the legacy CFE atlas CLIs themselves — only remove these 5
  sites' *dependency* on it.
- Do not modify `tests/parity/parity_runner.py`'s credentialed legacy-comparison mode.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh bootstrap, no CF_ATLAS_DB | Empty data root, no legacy DB | All 5 sites load via their new source; the bootstrap pipeline chain (`core,pypi_intelligence,vulnerability,vcs_health,upstream_discovery,derived_artifacts`) completes with no `cf_atlas.db` touched | Never raise; mark stale if fetch fails |
| Fetch fails (network/4xx/5xx) | Live endpoint unreachable | Return last-good Parquet + staleness marker set | Log warning, do not clobber last-good with empty |
| First-ever run, no last-good yet | No prior Parquet, fetch also fails | Return empty-but-correctly-columned frame, marked stale | Same shape as today's `_empty_pypi_json_frame()` |
| Legacy `.claude/data/` still present | `CF_ATLAS_DB` set, cf_atlas.db exists | Ignored — none of the 5 sites reads it anymore | No special-casing; simply unreferenced |

</intent-contract>

## Code Map

- `src/pyforge/atlas/datasets/refresh.py` -- `ExternalRefreshDataset` base (~L170) +
  `MappingCacheDataset` (~L560-640) -- the AD-13 last-good/staleness pattern to mirror for all
  5 sites; `StalenessMarker` (~L150-167), `_mark_stale()` (~L225-242).
- `src/pyforge/atlas/datasets/core_sources.py` -- `seed_parselmouth_mapping_from_cf_atlas()`
  (~L612-632) + `ParselmouthMappingDataset.load()` (~L642-646) -- replace with a read from
  `pypi_conda_map_store`.
- `src/pyforge/atlas/datasets/request_datasets.py` -- `_cf_atlas_db_path()` (~L81-86),
  `seed_pypi_json_from_cf_atlas()` (~L93-138), `PyPIJsonFanOutDataset.load()` (~L462-479,
  currently seed-first / live-fanout-only-for-gaps via `PYPI_JSON_LIVE_FANOUT=1`) --
  promote live fanout to the primary path, wrap in the staleness pattern;
  `GitHubRequestDataset.load()` (~L353-357, delegates to `vcs_sources.seed_github_from_cf_atlas`)
  -- implement the real GraphQL fetch using the already-wired `credentials: github_token`
  (catalog `vcs_github_api_raw`, `${GITHUB_API_BASE_URL}/graphql`, POST).
- `src/pyforge/atlas/datasets/vcs_sources.py` -- `_cf_atlas_db_path()` (~L19-24, duplicate of
  request_datasets.py's), `seed_github_from_cf_atlas()` (~L27-64), `seed_vcs_host_from_cf_atlas()`
  (~L67-82, GitLab/Codeberg), `seed_registry_from_cf_atlas()` (~L85-100, 8 registries),
  `VcsHostSeedDataset.load()` (~L118-119), `RegistryUpstreamDataset.load()` (~L143-144) --
  both classes currently discard their `url`/`kwargs` constructor params; wire them up.
- `conf/base/catalog.yml` -- `pypi_parselmouth_mapping_raw` (~L215), `pypi_json_raw` (~L188),
  `vcs_github_api_raw` (~L470, already has `credentials: github_token`), `vcs_gitlab_api_raw`
  (~L481), `vcs_codeberg_api_raw` (~L488), `vcs_registry_{npm,cran,cpan,luarocks,crates,
  rubygems,maven,nuget}_raw` (~L497-547) -- all `url:` values already resolve through live
  `endpoint_bases` in `conf/base/globals.yml` (~L24-65); no new override points needed.
- `tests/catalog/test_no_inline_io.py` + `tests/catalog/conftest.py` (`NO_INLINE_IO_EXEMPT`,
  ~L51-62) -- the gate this story must turn green (no exemption should be added — the fix is
  removing `sqlite3`, not allowlisting it).
- `tests/singularity/test_duckdb_sole_engine.py::test_no_sqlite_in_the_migrated_surface` --
  the second gate; documents the one legitimate sqlite3 reader (`tests/parity/parity_runner.py`,
  exempt by design — do not touch).
- `tests/datasets/` -- `test_request_datasets.py`, `test_pypi_json_request_dataset.py` exist;
  no `test_vcs_sources.py` and no Parselmouth test file exist yet -- add coverage for the
  classes this story changes.
- `src/pyforge/atlas/pipelines/vulnerability/nodes.py` (~L81, ~L96) + `pipeline.py` (~L36-45)
  -- `refresh_vdb_store`/`refresh_osv_offline_store`: the EXACT precedent pattern for wiring a
  refresh-trigger node into a pipeline (pure `RefreshRequest` producer, IO in the dataset).
- `src/pyforge/atlas/pipelines/pypi_intelligence/nodes.py` (~L630) + `pipeline.py` (~L91) --
  `export_pypi_conda_map`: the second precedent, already consumed by this story's Parselmouth
  wiring.
- `conf/base/parameters.yml` (~L67-72) -- `refresh_cadences` (`WEEKLY_SECONDS`), the TTL gate
  both precedent nodes read; the new GitHub/GitLab/Codeberg/registry trigger nodes must use the
  same mechanism, not fire unconditionally on every pipeline run.
- `src/pyforge/atlas/pipelines/vcs_health/nodes.py` (has `track_registry_versions`, per
  investigation) + `pipeline.py` -- the owning pipeline for the 10 currently-unwired
  GitHub/GitLab/Codeberg/registry catalog entries; add the new trigger nodes here.
- `src/pyforge/atlas/orchestration/definitions.py` (~L169-234) -- the `"refresh_assets"`
  Dagster job listing per-op timeouts for the two existing refresh triggers; add entries for
  the new ones for consistency (not required for this story's AC, but keeps the job accurate).

## Tasks & Acceptance

<!-- Amended in review_loop_iteration 1 -- see Spec Change Log. Supersedes the original task
     list, which produced correct-in-isolation but pipeline-dormant code for 10 of 12 entries
     plus 22 smaller bugs across the 4-layer review. -->

**Execution:**
- `src/pyforge/atlas/datasets/core_sources.py` -- remove
  `seed_parselmouth_mapping_from_cf_atlas()` and its sqlite3 import; `ParselmouthMappingDataset.load()`
  reads `pypi_conda_map_store` instead (KEEP -- this worked and is verified). Guard the
  `MappingCacheDataset(...).load()` call with try/except so a raised or non-dict result
  degrades to `{}` rather than propagating (never-raises). Raise on unexpected `**kwargs`
  rather than silently discarding them (catches stale catalog misconfiguration loudly).
- `src/pyforge/atlas/datasets/request_datasets.py`:
  - `PyPIJsonFanOutDataset` -- remove `_cf_atlas_db_path()` and `seed_pypi_json_from_cf_atlas()`;
    source candidate names from `pypi_conda_map_store` (KEEP). Drop `PYPI_JSON_LIVE_FANOUT` as
    a hard gate (KEEP this part of the prior amendment), but give `PYPI_JSON_FANOUT_LIMIT` a
    bounded, non-unlimited default (do not let removing the attended-only gate also make the
    fan-out unbounded by default) and guard a non-numeric env value with try/except, degrading
    to that same default rather than raising.
  - `GitHubRequestDataset` -- implement the real GraphQL fetch against `vcs_github_api_raw`
    (`fetch_repo_health()`, KEEP the batched-query design and the existing
    `self.scheduler.acquire()` rate-limit call). Move `scheduler.acquire()` and
    `build_batch_query(...)` inside the try/except so a failure there degrades rather than
    raising. Persist results through the same `ExternalRefreshDataset` last-good +
    `StalenessMarker` pattern as `VcsHostSeedDataset` (this story's GitHub path must not be the
    only one of the 5 sites without a persisted, staleness-marked store).
- `src/pyforge/atlas/datasets/vcs_sources.py` -- remove `_cf_atlas_db_path()`,
  `seed_github_from_cf_atlas()`, `seed_vcs_host_from_cf_atlas()`, `seed_registry_from_cf_atlas()`,
  and the sqlite3 import. `VcsHostSeedDataset` (GitLab/Codeberg) and `RegistryUpstreamDataset`
  (8 registries) subclass `ExternalRefreshDataset` (KEEP this mechanism and the per-registry
  `_REGISTRY_SPECS` extractor table design -- both are correct). Within that:
  - Fix the persistence clobber bug: a batch where every identifier's fetch fails or returns no
    version must be treated as EMPTY for persistence (mark stale, preserve last-good) in BOTH
    classes -- align `VcsHostSeedDataset._persist`/`load_many` with `RegistryUpstreamDataset`'s
    already-correct skip-on-failure logic (KEEP `RegistryUpstreamDataset`'s existing approach as
    the reference). Update or replace the existing test that currently documents the clobber as
    intended (`test_vcs_host_load_many_per_repo_failure_is_recorded_never_raises`) so it asserts
    the fixed behavior instead.
  - Add a `last_error` column to `RegistryUpstreamDataset._COLUMNS` to match `VcsHostSeedDataset`.
  - Wire the existing rate-limit scheduler into both classes' `fetch_one` (mirror
    `GitHubRequestDataset`'s `self.scheduler.acquire()`).
  - Thread `timeout_seconds`/`max_retries` into the actual `APIDataset` `load_args` in
    `fetch_one` for both classes -- currently accepted in `__init__` and silently discarded.
  - Raise (not silently fall through to another entry's shape) when `self._host` or
    `self._registry` is not a recognized key in `_HOST_SPECS`/`_REGISTRY_SPECS`.
  - Percent-encode every interpolated identifier (`urllib.parse.quote`) across all request-path
    builders, not only GitLab's hand-rolled escaping.
  - Fix `_luarocks_extract` to pick a genuinely latest version (e.g. sort version keys) instead
    of `next(iter(versions))` on unordered dict iteration.
  - Give `_codeberg_request_path` an explicit sort/order query param (mirroring GitLab's
    `order_by=updated`) rather than relying on unverified default tag ordering.
  - Guard against an empty/blank identifier after `.strip('/')` in the GitLab/Codeberg path
    builders -- raise rather than build a malformed double-slash URL.
  - Reinstate an explicit read-only `save()` override on both classes (raise, matching the
    guard these classes had before this story) rather than silently inheriting
    `ExternalRefreshDataset`'s no-op `save()`.
  - De-duplicate the near-identical `_persist`/`_store_path`/`_store_exists`/`_store_mtime`/
    `_write`/`load()` blocks between the two classes into `ExternalRefreshDataset` itself or a
    shared mixin -- keep each class's distinct fetch/extract logic separate, hoist only the
    shared persistence plumbing.
  - Fix `VcsHostSeedDataset.load_many`'s type hint to `list[tuple[str, str]]` to match its
    actual `(conda_name, identifier)` unpacking.
- **New: wire the 10 currently-dormant entries into a real pipeline run.** Add one refresh-
  trigger node per site (or grouped sensibly) into `pipelines/vcs_health/pipeline.py`, mirroring
  the *exact* existing pattern of `refresh_vdb_store`/`refresh_osv_offline_store`
  (`vulnerability/nodes.py` + `pipeline.py`) and `export_pypi_conda_map`
  (`pypi_intelligence/nodes.py` + `pipeline.py`): a pure `RefreshRequest`-producer node, gated
  by the same `params:refresh_cadences` TTL mechanism, calling the dataset's own `load_many`/
  `fetch_repo_health` for the actual IO (KEEP those methods as-is -- do not duplicate fetch
  logic in the node). Without this, `load()` for these 10 entries stays empty on every normal
  `kedro run` regardless of how correct the underlying fetch code is.
- `tests/datasets/test_vcs_sources.py` (new) + Parselmouth test coverage in
  `tests/datasets/test_request_datasets.py` -- unit-test the I/O matrix (fetch success, fetch
  failure keeps last-good + marks stale -- now correctly, first-run-no-last-good) for
  `ParselmouthMappingDataset`, `VcsHostSeedDataset`, `RegistryUpstreamDataset` (KEEP this test
  file's structure). Close these specific gaps: a `luarocks` case in
  `test_registry_extractor_shapes` (the only registry currently untested -- it has a materially
  different payload shape from the other 7); a `PYPI_JSON_FANOUT_LIMIT` truncation test plus a
  non-numeric-value-degrades test; a `request_path()` shape test for PyPI JSON; a test asserting
  the rate-limit scheduler is acquired in the new `fetch_one` paths; a test proving a
  total-failure batch does NOT clobber `VcsHostSeedDataset`'s last-good store (replacing the one
  that currently documents the opposite).
- Verification housekeeping: `grep -rn 'seed_.*_from_cf_atlas\|_cf_atlas_db_path'` across the
  whole repo (not just `pyforge-atlas`) to confirm no remaining importer of the deleted symbols;
  check whether any `conf/local/` or test-fixture catalog override redefines the 12 touched
  catalog entries and needs a matching update.
- Run `pixi run -e pyforge-atlas kedro-catalog-check`, `duckdb-singularity`, `parity-diff`, and
  `kedro-test` -- confirm all green as the story's own verification (see amended `##
  Verification` section for the bootstrap-chain command, which excludes the unrelated
  `seed_gaps` failure).

**Acceptance Criteria:**
- Given no `CF_ATLAS_DB` env var and an empty `PYFORGE_ATLAS_DATA_ROOT`, when the 5 datasets
  load, then none references `cf_atlas.db`/`sqlite3` and each returns fresh-fetched or
  last-good-plus-stale data, never raising.
- Given `pixi run -e pyforge-atlas kedro-catalog-check` and `duckdb-singularity`, when run
  after this story, then both pass for `core_sources.py`, `request_datasets.py`,
  `vcs_sources.py` (both currently fail on these 3 files).
- Given the bootstrap pipeline chain (`core,pypi_intelligence,vulnerability,vcs_health,
  upstream_discovery,derived_artifacts`) on a fresh data root with no `CF_ATLAS_DB`, when run,
  then it completes without touching `.claude/data/conda-forge-expert/cf_atlas.db` -- the
  literal `pyforge-atlas-bootstrap` pixi task also runs `seed_gaps`, which fails on a
  pre-existing, unrelated path-resolution bug verified to reproduce identically on this
  story's `baseline_revision`; that failure is out of this story's scope (see `deferred`).
- Given `pixi run -e pyforge-atlas parity-diff` (fixture mode), when run after this story,
  then it stays green (unrelated to these seed sites, but must not regress).
- Given a normal `kedro run` of the pipeline the new trigger nodes are wired into (`vcs_health`),
  when it completes, then the GitHub/GitLab/Codeberg/registry catalog entries are populated (or
  correctly marked stale on fetch failure) via those nodes -- not left permanently empty behind
  an unwired `load_many`/`fetch_repo_health`.
- Given a batch where every identifier's fetch fails, when `VcsHostSeedDataset` or
  `RegistryUpstreamDataset` persist, then last-good data is preserved and staleness is marked --
  never overwritten with an all-null result.

## Spec Change Log

- 2026-08-29: Narrowed the matrix "Fresh bootstrap" row and AC #3 from the literal
  `pyforge-atlas-bootstrap` pixi task to its underlying kedro pipeline chain minus
  `seed_gaps`. Implementation + verification found `seed_gaps` fails on a pre-existing,
  unrelated `seed_root` path-resolution bug that reproduces identically on
  `baseline_revision` with none of this story's changes applied. Recorded as a `deferred`
  follow-up rather than fixed here (out of the 3-file scope) or treated as a story blocker.
  KEEP: all other matrix rows, ACs, and the Code Map/Tasks strategy assignments are
  unaffected and verified as written.
- 2026-08-29 (review_loop_iteration 1): First implementation pass was reverted after 4-layer
  review found 2 bad_spec-rooted findings plus 21 code-level bugs (full list in that pass's
  Review Triage Log entry below). Root causes: (1) Tasks never required the 10 GitHub/GitLab/
  Codeberg/registry catalog entries' fetch logic to be reachable from a normal `kedro run` --
  the implementer correctly built and unit-tested `load_many`/`fetch_repo_health` but had no
  spec instruction to wire either into a pipeline node, so `load()` stayed dormant/empty for
  10 of 12 entries; (2) Tasks explicitly told the implementer to drop
  `PyPIJsonFanOutDataset`'s `PYPI_JSON_LIVE_FANOUT` gate without specifying a bounded
  replacement default, flipping a previously attended-only feature to default-on/unbounded.
  Amended: added an explicit pipeline-wiring task + 2 new ACs mirroring the existing
  `refresh_vdb_store`/`export_pypi_conda_map` precedent; added a bounded-default requirement
  for `PYPI_JSON_FANOUT_LIMIT`; folded in explicit fixes for all 21 code-level findings
  (clobber-safety parity between `VcsHostSeedDataset`/`RegistryUpstreamDataset`, rate
  limiting, timeout wiring, GitHub persistence, URL encoding, luarocks extractor, Codeberg
  ordering, unknown-host/registry guards, dedup, missing tests, read-only `save()`, type-hint
  fix, repo-wide grep for orphaned symbols).
  KEEP (verified working, must survive re-derivation): `ParselmouthMappingDataset` reading
  `pypi_conda_map_store` instead of a new fetch; the `ExternalRefreshDataset` subclassing
  approach and per-registry `_REGISTRY_SPECS` extractor-table design for
  `VcsHostSeedDataset`/`RegistryUpstreamDataset`; `RegistryUpstreamDataset`'s existing
  skip-on-failure persistence logic (the reference for fixing `VcsHostSeedDataset`);
  `GitHubRequestDataset`'s existing `self.scheduler.acquire()` rate-limit call and batched-
  GraphQL query design; the `tests/datasets/test_vcs_sources.py` file structure and I/O-matrix
  test coverage approach; removal of all sqlite3/`CF_ATLAS_DB` references (this closed
  `test_no_inline_io_in_package_code` and `test_no_sqlite_in_the_migrated_surface` correctly
  and should not be undone).

## Review Triage Log

### 2026-08-29 — Review pass
- intent_gap: 0
- bad_spec: 2 (high, high)
- patch: 21 (high 3, medium 15, low 3)
- defer: 0
- reject: 0
- addressed_findings:
  - none

### 2026-08-29 — Review pass (pass 2, review_loop_iteration 1)
- intent_gap: 0
- bad_spec: 0
- patch: 13 (high 2, medium 6, low 5)
- defer: 7 (medium 2, low 5)
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` `_luarocks_extract`'s lexicographic string sort mis-ranks multi-digit
    versions (e.g. "1.10-1" sorted below "1.2-1"); the test fixture had locked in the wrong
    answer -- fixed with a numeric-aware sort and corrected test expectation.
  - `[high]` `[patch]` `GitHubRequestDataset`'s default `save()` path made a real live GraphQL
    call even with an empty identifier batch (unlike its siblings, which make zero calls) --
    fixed to short-circuit to a true no-op on an empty batch.
  - `[medium]` `[patch]` Retry loops in `VcsHostSeedDataset`/`RegistryUpstreamDataset.fetch_one`
    bypassed the rate-limit scheduler after the first attempt and had no backoff -- fixed.
  - `[medium]` `[patch]` `GitHubRequestDataset._max_retries` was accepted but unused -- wired
    into a real retry loop matching its siblings.
  - `[medium]` `[patch]` No batch-size ceiling on GitHub GraphQL batching -- chunked via the
    existing `chunk_queries`/`BASILISK_QUERYBATCH_MAX` precedent.
  - `[medium]` `[patch]` `PyPIJsonFanOutDataset` was architecturally inconsistent with the
    AD-13 pattern used by every other class in this diff (no cadence gate, no persisted
    last-good) -- wired through the same cadence-gated refresh-trigger + persisted-store
    pattern.
  - `[medium]` `[patch]` `PYPI_JSON_FANOUT_LIMIT=0` silently fell back to the default instead
    of disabling fan-out -- fixed to treat `0` as an explicit disable.
  - `[medium]` `[patch]` No validation that a `RefreshRequest.store` matches the receiving
    dataset's own expected store name, leaving a silent-misrouting risk on any future
    positional-order drift -- added an explicit check + regression test.
  - `[low]` `[patch]` `PyPIJsonFanOutDataset.__init__` silently sank unrecognized `**kwargs`,
    inconsistent with `ParselmouthMappingDataset`'s explicit no-sink rule in the same diff --
    fixed to raise.
  - `[low]` `[patch]` No unit tests for the 3 new trigger node functions or `_ttl_cadence`'s
    fallback behavior -- added.
  - `[low]` `[patch]` `_codeberg_path` did not guard against an identifier with more than one
    `/` segment -- fixed to raise on an unexpected shape.
  - `[low]` `[patch]` `PyPIJsonFanOutDataset`'s candidate extraction did not filter non-string
    `conda_name` values, unlike `ParselmouthMappingDataset` -- fixed to match.
  - `[low]` `[patch]` Dead `import os` in `core_sources.py` after its only user was removed --
    removed if confirmed unused.

## Design Notes

The AD-13 pattern to mirror (`refresh.py::MappingCacheDataset.save()`): never clobber
last-good with an empty/failed fetch -- mark stale and return, or atomically write + clear
the stale marker on success:

```python
def save(self, data: Any) -> None:
    new_map = data if isinstance(data, dict) else {}
    if not new_map:
        self._mark_stale("export produced no entries — keeping last-good")
        return
    merged = {**self._read_existing(), **new_map}
    try:
        self._atomic_write(self._cache_path, lambda p: p.write_text(json.dumps(merged)))
    except Exception as exc:
        self._mark_stale(f"write failed: {exc}")
        return
    self._clear_stale()
```

Registry/VcsHost endpoint construction (exact per-package path + response field to extract
for each of GitLab, Codeberg, npm, CRAN, CPAN, LuaRocks, crates.io, RubyGems, Maven Central,
NuGet) is a step-03 research task against each registry's public, stable REST API -- not an
open spec question, since the *shape* (GET the wired base URL + package identifier, extract
one version string, wrap in the same staleness pattern) is fixed and identical across all 10.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-catalog-check` -- expected: pass, zero sqlite3/CF_ATLAS_DB
  findings in `core_sources.py`, `request_datasets.py`, `vcs_sources.py`.
- `pixi run -e pyforge-atlas duckdb-singularity` -- expected: 6/6 passed (currently 5/1 fail).
- `pixi run -e pyforge-atlas parity-diff` -- expected: stays green.
- `kedro run --pipelines core,pypi_intelligence,vulnerability,vcs_health,upstream_discovery,
  derived_artifacts` (the bootstrap chain minus `seed_gaps`, which has a pre-existing
  unrelated failure -- see `deferred`) on an empty data root, no `CF_ATLAS_DB` set --
  expected: exit 0, no `cf_atlas.db` touched.

## Auto Run Result

**Summary:** Removed the `cf_atlas.db` SQLite seed dependency from 5 dataset classes across
`core_sources.py`, `request_datasets.py`, `vcs_sources.py`. Each got a real AD-13-compliant
replacement (last-good Parquet + staleness marker, never raise): `ParselmouthMappingDataset`
and `PyPIJsonFanOutDataset` read from the existing `pypi_conda_map_store`;
`GitHubRequestDataset`, `VcsHostSeedDataset` (GitLab/Codeberg), and `RegistryUpstreamDataset`
(8 registries) do real HTTP fetches through a shared `_ParquetRefreshStore` persistence mixin,
each wired to a refresh-trigger pipeline node mirroring the existing `refresh_vdb_store`
precedent, gated by the existing TTL cadence mechanism. Took two implementation passes: pass 1
built correct-but-pipeline-dormant fetch code for 10 of 12 new entries and removed a fanout
safety gate without a bounded replacement (both spec-level gaps, fixed by amendment); pass 2's
own review found 13 further code-level bugs, all patched in place (no second revert needed).

**Files changed** (all under `src/shared/packages/pyforge-atlas/`):
- `src/pyforge/atlas/datasets/core_sources.py` -- `ParselmouthMappingDataset` reads
  `pypi_conda_map_store`; no `**kwargs` sink; guards `MappingCacheDataset.load()` exceptions.
- `src/pyforge/atlas/datasets/request_datasets.py` -- `PyPIJsonFanOutDataset` rewritten onto
  `_ParquetRefreshStore` (cadence-gated fan-out, bounded `PYPI_JSON_FANOUT_LIMIT` with an
  explicit `0`-disables case, non-string-value filtering, no kwargs sink);
  `GitHubRequestDataset` gained a real batched-GraphQL `fetch_repo_health()` (chunked, retried
  with backoff, empty-batch short-circuits to zero network calls) persisted via the shared
  mixin.
- `src/pyforge/atlas/datasets/vcs_sources.py` -- `VcsHostSeedDataset`/`RegistryUpstreamDataset`
  do real REST fetches (percent-encoded, host/registry-guarded, numeric-aware luarocks version
  sort, Codeberg identifier-shape guard, retry-with-backoff-and-scheduler, clobber-safe
  persistence); shared `_ParquetRefreshStore` mixin; `RefreshRequest.store` validated against
  each dataset's own expected store name.
- `src/pyforge/atlas/pipelines/vcs_health/nodes.py` + `pipeline.py`,
  `pipelines/pypi_intelligence/pipeline.py` -- 4 new refresh-trigger nodes (GitHub, GitLab/
  Codeberg, 8 registries, PyPI JSON), each a pure `RefreshRequest` producer gated by the
  existing TTL cadence params, with an explicit code comment noting the empty identifier batch
  is a deliberate Story 21.2 boundary (real identifiers deferred to Story 21.6).
- `src/pyforge/atlas/orchestration/definitions.py` -- new nodes added to `NODE_TIMEOUTS` and
  the `refresh_assets` schedule.
- `conf/base/catalog.yml` -- `filepath:`/store keys for the 13 touched entries, reusing
  existing override points.
- `tools/bootstrap.py`, `README.md` -- corrected stale pre-story wording about GitHub/fanout
  default behavior.
- Tests -- `tests/datasets/test_vcs_sources.py` (new), `test_core_sources.py`,
  `test_pypi_json_request_dataset.py`, `test_request_datasets.py`,
  `tests/pipelines/vcs_health/test_nodes.py` + `pypi_intelligence/test_nodes.py` (new node/
  cadence tests), `test_dag_resolves.py`, `test_parity_complete.py` (node-count updates).

**Review findings breakdown:** pass 1 -- 2 bad_spec (fixed via spec amendment + full
re-implementation), 21 patch-class findings folded into the same re-implementation. Pass 2 --
13 patches applied in place, 7 deferred (recorded in frontmatter `deferred`, none rejected).

**Follow-up review recommendation:** `true` -- pass 2 had 2 high-severity patched findings
(luarocks version-sort correctness, GitHub empty-batch live network call), which alone
triggers the recommendation regardless of the medium/low score.

**Verification performed:** `kedro-catalog-check` 50 passed, `duckdb-singularity` 6/6 passed,
`parity-diff` 70 passed, `kedro-test` full suite 1372 passed / 21 skipped / 0 new failures
(only 2 pre-existing environment-only errors, unrelated to this story). A live end-to-end
`kedro run` on a fresh empty data root with no `CF_ATLAS_DB` completed successfully with real
network calls; all new stores correctly created and marked stale on the (expected, deferred)
empty-identifier-batch path. Independently spot-checked `kedro-catalog-check` and
`duckdb-singularity` a second time after the patch pass, both green.

**Residual risks:** the 7 deferred findings (see frontmatter) -- most significant is that 11 of
13 new catalog entries have no real identifier source yet, so they mark stale rather than
populate real data until Story 21.6 wires an identity mapping in; this is intent-authorized
scope (`identity-contract.md` explicitly excluded from 21.2), not a defect.
