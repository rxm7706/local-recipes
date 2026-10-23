---
title: "37.10: The bootstrap-index-health reports each catalog entry's freshness"
type: 'feature'
created: '2026-10-23'
status: 'done'
baseline_revision: '88a313d7e7cc00547557352af4fc4ed709df6009'
flag:
  key: pyforge.atlas.board_projections            # existing; minted by Story 37.4, extended to this board
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through src/platform/config/flag-overlays.json
  scope: global                                   # v1 is global only
  fallback: 'the bootstrap-index-health reads derived/bootstrap_index_health as before, which nothing writes, and renders empty'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/catalog-sources.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-20-9-vizro-bootstrap-health-pages-optional-cap-5.md
  - docs/reference/story-spec-flag-block.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipeline_registry.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the bootstrap-index-health board reads `derived/bootstrap_index_health/`, and no node writes it
(DW-atlas-37-10-1). Story 20.9 left the path and schema to be decided at implementation. The intended shape is one
row per catalog entry: name, tier, row count, staleness (`catalog-sources.md`'s tier matrix and scale sanity gates).
Today nothing reports whether a run left an index missing, empty or stale.

**Approach:**
1. **A read-only dataset,** `CatalogIndexDataset` (new, `datasets/catalog_index.py`). It reads `conf/base/catalog.yml`
   and returns one row per entry whose `filepath` lies under the data root. Each row has:
   - its layer;
   - its last write: the file's mtime, or for a store directory its newest `*.parquet`;
   - the row count its Parquet footer gives;
   - its staleness marker: a sibling `<file>.staleness.json`, or the directory's `.staleness.json`.

   Entries that fetch live and persist nothing (an `url` only, or a path outside the data root) have no row.
2. **A pure node,** `report_catalog_index_health`, writes `catalog_index_health` with these columns:
   - `catalog_entry`, `layer`, `regenerated_at`, `row_count`;
   - `tier`: the catalog-sources matrix, Tier 0 to 3, each source named by the dataset that persists it
     (`params:catalog_index_health.tiers`); `untiered` otherwise;
   - `floor`: the scale sanity gate's minimum (`floors`);
   - `status`: `missing` (never written), `stale` (its marker), `empty`, `below_floor` or `ok`;
   - `stale_reason`.
3. **Its own pipeline, run after the build.** A node with no upstream edge would land in Kedro's first toposort
   group and read the data root before the run writes it. So the node lives in a new `catalog_index` pipeline, which:
   - `pipeline_registry` keeps out of `__default__` (`AFTER_RUN_PIPELINES`);
   - the Pages job runs last, after `semantic_packages`;
   - an operator runs after a build with `pyforge atlas run --pipelines catalog_index` (the README says so).
     `pyforge-atlas-bootstrap` is not changed: its task lives in `pixi.toml`, which eight Specs govern.
4. **The board,** behind `pyforge.atlas.board_projections` as Stories 37.4, 37.5 and 37.9's boards are:
   - on, bootstrap-index-health reads `derived/catalog_index_health/`, with a note, `tier` and `status` filters, and
     a `status` dimension the model gains;
   - off, it reads `derived/bootstrap_index_health/` as before.

Ledger key: `37-10-the-bootstrap-index-health-reports-each-catalog-entry-s-freshness`.
Type / Effort / Deps: feature / M / Story 37.1 (the data root).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-69** (FR-77, the boards no pipeline feeds). **AD-2/AD-13** (the dataset owns the file
  reads; an unreadable catalog degrades to empty), **AD-8** (BSL over DuckDB; no metric computed in the app),
  **AD-14** (a new rider, not parity-gated), **AD-17** (the page's stamp from the dataset it reads).

## Acceptance Criteria

- **AC1 — Index.** Every catalog entry under the data root is listed, with its write, footer count and marker; live-only
  entries and paths outside the data root are not; a store directory reads its newest Parquet; an unreadable catalog
  gives an empty frame.
- **AC2 — Status.** `missing` before `stale` before `empty` before `below_floor`; a write with no count (not Parquet) is
  `ok`; tiers and floors come from the params; tiered entries sort first.
- **AC3 — Order.** `catalog_index` is registered, absent from `__default__`, and run after the build by the Pages job;
  the README tells an operator to run it after a build.
- **AC4 — Board.** With the flag on, bootstrap-index-health reads `catalog_index_health` and its AD-17 stamp names that
  file; off, it reads `derived/bootstrap_index_health/` as before.

## Boundaries & Constraints

**Always:** read-only over the data root; a missing or unreadable file degrades, never raises (AD-13).

**Never:** reach the network; read a dataset's rows (only Parquet footers).

**Residual risk:**
- A store that persists JSON rather than Parquet shows its write and no count, so `empty` and `below_floor` cannot fire
  for it.
- A run that does not end with `catalog_index` (the bootstrap task, or a hand-run subset of pipelines) leaves the board at
  the last index.
- Dagster: `NODE_TIMEOUTS` covers exactly `__default__`'s nodes, so `report_catalog_index_health` has no timeout and no
  scheduled job; the whole-DAG jobs do not run it.

## I/O & Edge-Case Matrix

| Entry on disk | Marker | Status |
|---------------|--------|--------|
| absent | any | missing |
| Parquet, rows ≥ floor | stale | stale |
| Parquet, 0 rows | none | empty |
| Parquet, rows < floor | none | below_floor |
| Parquet, rows ≥ floor or no floor | none | ok |
| written, not Parquet | none | ok (no count) |
| `url` only, or outside the data root | — | not listed |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-69 (FR-77). No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-19 entry (the Vizro boards read their data).
- Epic: Epic 37 (in progress). Closes DW-atlas-37-10-1.
- Ledger key: `37-10-the-bootstrap-index-health-reports-each-catalog-entry-s-freshness`.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas pyforge-atlas-test` — expected: pass.
- From the repo root: `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_catalog_index.py`,
  `src/shared/packages/pyforge-atlas/tests/unit/pipelines/catalog_index/test_nodes.py` and
  `src/shared/packages/pyforge-atlas/tests/unit/test_board_projections.py` (both flag states) — expected: pass.

## Run results

Run 2026-10-23 in the landing worktree, stacked on Story 37.9's branch (`88a313d7e7`), every verdict read from
its exit code.

- **AC1–AC4, tests:** `test_catalog_index.py` (12), `catalog_index/test_nodes.py` (13) and `test_board_projections.py`
  pass; `pyforge-atlas-test` gives 3,178 passed and 20 skipped, then 103 passed (exit 0).
- **Pins moved:** 12 pipelines registered (the README's inventory), the catalog 139 entries (`catalog_index_raw`,
  `catalog_index_health`), `catalog_index` outside `__default__` and outside the MCP trigger surface; the loader and the
  model gain `status`.
- **Found by the suite:** `NODE_TIMEOUTS` must name exactly `__default__`'s nodes, so the node has no timeout (a
  residual above); the MCP mirror test needed `catalog_index` in `NO_MCP_TRIGGER_PIPELINES`.
- **Mutations**, each restored, each failing a named test (11 of 11): every filepath listed, the oldest Parquet in a
  store, a store's marker ignored, a sibling marker ignored, no footer count, stale before missing, `empty` never,
  the floor ignored, no tier sort, `catalog_index` inside `__default__`, and the board path not switched.
- **Real data:** over Story 37.2's live data root with the shipped catalog, the index lists 110 entries in 0.10 s:
  64 `ok`, 35 `missing` and 11 `empty`. Every Tier 0–3 entry is `ok` except `openteams_project_1_board_raw`
  (`missing`: credentialed, so a public run leaves only its marker) and `enterprise_jfrog_names` (`empty`: no JFrog on
  a public run). Each floor is met (34,720 conda-forge packages, 5,549 Anaconda main, 919,975 PyPI names, 34,722
  Basilisk packages). `load_bootstrap_index_health` reads all 110 rows.

## Spec Change Log

- 2026-10-23: drafted from Story 37.10, DW-atlas-37-10-1 and Story 20.9's open path.

## Review Triage Log
