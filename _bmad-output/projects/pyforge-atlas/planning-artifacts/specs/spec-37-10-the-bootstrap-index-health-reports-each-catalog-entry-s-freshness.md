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
review_loop_iteration: 2
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
1. **A read-only dataset,** `CatalogIndexDataset` (new, `datasets/catalog_index.py`). Its `filepath` is
   `conf/base/catalog.yml` and its `path` the data root; Kedro makes both absolute against the project, so it reads the
   same files from any working directory. It returns one row per entry whose `filepath`, `path` or `filename` lies
   under the data root, the path globals expanded through the sibling `globals.yml` (`${globals:paths.vdb_store}`,
   `pypi_conda_map`, `warden_fleet_inventory`), or that a literal `data/...` names (Kedro anchors that at the
   project, not at `PYFORGE_ATLAS_DATA_ROOT`, and so does the index). Each row has:
   - its layer;
   - its last write: the file's mtime, or for a store directory its newest data file at any depth (JSON or Parquet;
     not a staleness marker, not a dotfile);
   - its row count: the Parquet footer's, or for a store directory the sum of its Parquet footers; none when it holds
     no Parquet, and none with `unreadable` set when a footer cannot be read (a truncated write);
   - its staleness marker: a sibling `<file>.staleness.json`, or the directory's `.staleness.json`.

   Entries that fetch live and persist nothing (an `url` only, or a path outside the data root) have no row. A file
   that vanishes mid-scan reads as not written (AD-13).
2. **A pure node,** `report_catalog_index_health`, writes `catalog_index_health` with these columns:
   - `catalog_entry`, `layer`, `regenerated_at`, `row_count`;
   - `tier`: the catalog-sources matrix, Tier 0 to 3, each source named by the dataset that persists it
     (`params:catalog_index_health.tiers`); `untiered` otherwise;
   - `floor`: the scale sanity gate's minimum (`floors`);
   - `status`: `missing` (never written), `stale` (its marker), `unreadable` (a Parquet footer that cannot be read),
     `empty`, `below_floor` or `ok`;
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

- **AC1 — Index.** Every catalog entry under the data root is listed, by any path key and through the path globals, with
  its write, footer count and marker; live-only entries and paths outside the data root are not; a store directory
  reads its newest data file and sums its Parquet footers; an unreadable catalog gives an empty frame. The index leaves
  out its own output.
- **AC2 — Status.** `missing` before `stale` before `unreadable` before `empty` before `below_floor`; a write with no
  count (not Parquet) is `ok`, an unreadable Parquet never is; tiers and floors come from the params; tiered entries
  sort first.
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
- Two catalog entries that share one store directory (`core_s3_download_stats_raw` and `core_s3_version_downloads_raw`,
  two views of `stores/core_s3_downloads`) each report the directory's summed count, which is neither view's own.
- `docs/how-to/pixi-tasks.md` is generated from `pixi.toml`, which this story leaves alone, so its bootstrap row does
  not name `catalog_index`; the README does.
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
| written, not Parquet (a JSON file, or a store of JSON files) | none | ok (no count) |
| a store holding only a marker | stale | missing |
| Parquet whose footer cannot be read (a store with one such partition too) | none | unreadable |
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

Run 2026-10-23 in the landing worktree (Story 37.9's branch, then main `771288616d` merged in), every verdict read
from its exit code. The numbers are those after the review rework.

- **AC1–AC4, tests:** `test_catalog_index.py` (25), `catalog_index/test_nodes.py` (16) and `test_board_projections.py`
  pass; `pyforge-atlas-test` gives 3,194 passed and 20 skipped, then 103 passed (exit 0).
- **Pins moved:**
  - 12 pipelines registered (the README's inventory);
  - the catalog has 139 entries (`catalog_index_raw`, `catalog_index_health`);
  - `catalog_index` sits outside `__default__` and outside the MCP trigger surface;
  - the loader and the model gain `status`.
- **Found by the suite:**
  - `NODE_TIMEOUTS` must name exactly `__default__`'s nodes, so the node has no timeout (a residual above);
  - the MCP mirror test needed `catalog_index` in `NO_MCP_TRIGGER_PIPELINES`.
- **Mutations**, each restored, each failing a named test (20 of 20):
  - which entries are listed: any path listed; the path globals not expanded; a literal `data/` read under the data
    root;
  - store directories: the oldest write taken; the footers not summed; hidden folders counted; a file marker counted
    as a write;
  - markers and counts: `unreadable` never flagged; a store's marker ignored; a sibling marker ignored; no footer
    count;
  - status: stale before missing; unreadable read as ok; unreadable before stale; `empty` never; the floor ignored;
    the index's own output listed; no tier sort;
  - wiring: `catalog_index` inside `__default__`; the board path not switched.
- **Real data:** over Story 37.2's live data root with the shipped catalog, the index lists 115 entries in 0.08 s, and
  the board's table holds 114 (its own output left out).
  - Status: 78 `ok`, 25 `missing`, 11 `empty`.
  - Every `missing` entry is unwritten:
    - marker-only stores (credentialed or unfetched);
    - outputs that root predates;
    - `repo_dependency_history` (no repo configured);
    - `derived_purl_exports`, whose literal `data/...` the index reads under the project (this worktree), as Kedro
      does.
  - Tier 0 to 3 is all `ok`, except `openteams_project_1_board_raw` (`missing`: credentialed) and
    `enterprise_jfrog_names` (`empty`: no JFrog on a public run).
  - Each floor is met: 34,720 conda-forge packages, 5,549 Anaconda main, 919,975 PyPI names, 34,722 Basilisk.
  - `load_bootstrap_index_health` reads all 114 rows.

## Spec Change Log

- 2026-10-23, review 2 (PASS, 0 blockers, 2 should-fix), fixed on the same branch:
  - SF1: a truncated Parquet file read `ok` (no count), skipping its floor. A footer that cannot be read now sets
    `unreadable`, and the status is `unreadable`, after `stale`.
  - SF2: a literal `data/...` path was read under an overridden data root, where Kedro does not write it. It is read
    under the project now.
  - Nits: nothing under a dot-name in a store counts as data (hidden folders too); the shared-store sum is a residual
    above.
- 2026-10-23, independent review (FAIL, 2 blockers), fixed on the same branch:
  - B1: a store directory's write came from its top-level `*.parquet` only, so 11 written stores (JSON, or Parquet in
    a subfolder: the parselmouth, endoflife and SPDX `last_good.json`, the six migration stores, the two S3 month
    caches) read `missing`. A store now takes its newest data file at any depth and sums its Parquet footers.
  - B2: only the literal `${globals:paths.data_root}/` prefix was matched, so `vulnerability_vdb_store`,
    `vulnerability_osv_offline_store`, `pypi_conda_map_store` (Tier 0), `warden_fleet_inventory` and
    `derived_purl_exports` (`path: data/...`) were dropped, and a test pinned the gap. The path globals expand through
    `globals.yml`, every Kedro path key is read, and a literal `data/` is the shipped root.
  - Should-fix:
    - a store's several partitions are summed, not its newest;
    - the dataset's catalog and data root are `filepath` and `path`, which Kedro makes absolute, so an MCP or
      notebook session from another directory reads the same files;
    - the index leaves out its own output;
    - `pypi_json_raw` and `pypi_conda_map_store` are Tier 0.
  - Nits:
    - the model's docstring and its `status` comment are corrected;
    - every `stat` sits behind an `OSError` guard;
    - `docs/how-to/pixi-tasks.md` stays as generated (a residual above).
- 2026-10-23: drafted from Story 37.10, DW-atlas-37-10-1 and Story 20.9's open path.
- 2026-11-01: epics.md amended in place (append-only, EGM audit ATL-D-R6, ATL-D-C1): the Story 37.10 block gains the Flag line `pyforge.atlas.board_projections` (Story 37.4's, extended to this board; dev on, staging and production off) and its Then line reads "with the flag on", as this spec's `flag:` block has said since mint; this spec is otherwise unchanged.

## Review Triage Log

- 2026-10-23, review 1 (independent subagent, read the diff against this spec): FAIL, with 2 blockers, 4 should-fix and
  4 nits, all addressed (Spec Change Log). The reviewer also did these:
  - reproduced the first real-data run and found the 11 written stores it called `missing`;
  - ran `kedro run --pipelines catalog_index` against scratch copies of the member `conf/` and the data root (exit 0);
  - showed that a `KedroSession` opened from another directory read 0 rows before the `filepath`/`path` change;
  - checked the types through Parquet, DuckDB and BSL, for the empty table and the filled one.
- 2026-10-23, review 2 (independent subagent): PASS. 0 blockers, 2 should-fix and 2 nits, all addressed (Spec Change
  Log), each closing one of round 1's findings. The reviewer also did these:
  - confirmed Kedro makes `filepath` and `path` absolute for this dataset;
  - confirmed `docs/how-to/pixi-tasks.md` is generated, by `scripts/docs_pixi_tasks.py`;
  - probed cycles and unknown keys in the path globals;
  - timed the vdb and S3 store scans;
  - reproduced the real-data counts exactly.
