---
title: "34.8: Migration status fills through a driver node"
type: 'feature'
created: '2026-10-18'
status: 'in-review'
baseline_revision: 'c8cc5de8e3'
flag:
  key: pyforge.atlas.live_public_sources          # shared with Stories 34.4 (registered it), 34.5 and 34.6
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: on, dev: on}   # unchanged from 34.4
  scope: global                                   # v1 is global only
  fallback: 'with no injected fetcher, the category and detail datasets keep today''s behaviour: last-good under the marker "offline: no GitHub-raw fetcher wired (consumer profile)"'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 2
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/live-sources.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-3-10-migration-readiness-datasets-classification-node.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/public_sources.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/migration_status.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/vcs_health/nodes.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/definitions.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `vcs_migration_readiness` held 0 rows after the unattended refresh of 2026-10-17 (R6).

- Story B10 (3.10) built `MigrationCategoryDataset` and `MigrationDetailDataset` with a `refresh` and a
  `fetch_partitions` that nothing calls.
  - No node reads the five category entries (`vcs_migration_{regular,longterm,paused,closed,total}_status_raw`).
  - No node writes `vcs_migration_detail_raw`.
  - So the detail store stayed empty under "offline: no GitHub-raw fetcher wired", and
    `classify_migration_readiness` had nothing to classify.
- The bot's status files are public. On 2026-10-18 `conda-forge-bot-data/main/status/` listed:
  - 22 regular, 6 longterm, 3 paused and 6 closed migrations: 37 in all, the Spec's parity measure.
  - `total_status.json`'s 31, exactly regular ∪ longterm ∪ paused.
  - Every listed migration, closed ones included, has a `migration_json/<name>.json` holding its per-package
    state.
- **Legacy reference:** none. `vcs_migration_readiness` is an AD-14 new signal and is never parity-gated.

**Approach:**
1. **The datasets read the bot's files publicly.** With no injected fetcher, each dataset asks
   `public_sources.live()` at each load or save, never at construction. On, the fetcher is
   `public_sources.fetch_text` plus `json.loads`: one unauthenticated GET with a 300 s timeout and no `~/.netrc`
   credential. Off, today's offline behaviour stands.
   - **An injected fetcher still wins.** A category with one keeps B10's attended contract: its load never
     fetches.
   - **A category `load()` on the public path refreshes first,** so the driver reads the current list. On failure
     it keeps last-good under the AD-13 marker.
   - **An empty public file is a valid empty category.** A public 200 that parses to `{}` or `[]` means the
     category has no migrations, so it is written. B10's guard, never write an empty payload over a good one,
     still holds for an injected fetcher.
2. **A driver node, `drive_migration_status`, is the detail store's single writer (AD-10).**
   - It is pure. It returns every name regular, longterm, paused, closed and total carry, in that order, first
     seen, no duplicates.
   - The status page renders all four categories, so every listed migration gets a partition: 37 today.
   - `total` lists the open and paused set again. A list that failed with no last-good therefore still has its
     names.
   - **It has two outputs.** The names are the detail dataset's `save()`. The new `vcs_migration_categories`
     frame (`migration`, `category`) names each migration's first list; a name only `total` carries is
     `unlisted`.
   - **Readiness gains a `category` column**, so FR-21's "active" set is `category in {regular, longterm}`.
     - Deviation, recorded: PRD FR-21 says partitioned by *active* migration. The Spec's R6 measure, 37, counts
       every listed one.
     - Readiness therefore covers every listed migration, and the column keeps FR-21's subset one filter away.
3. **`MigrationDetailDataset.save(names)` is the sweep.** It shares `_sweep` with `fetch_partitions`: one
   `migration_json/<name>.json` partition per name. Its guards:
   - **Names:** a name that is not a migrator slug (`[A-Za-z0-9_][A-Za-z0-9_.+-]*`: never a path, never hidden)
     is logged and skipped. The excluded queue is skipped as before.
   - **No names** is never a clean sweep: last-good stays, under "no migration names to sweep".
   - **The prune:** after a clean sweep, a partition the names no longer list (a migration that left every list)
     is removed, so readiness classifies only listed migrations. A partial sweep removes nothing, and the prune
     never touches a hidden file.
   - **The load** never fetches. It marks "no detail partitions yet (sweep pending)" only when there are no
     partitions and no marker, so it never overwrites a marker the sweep left.
4. **Every default-pipeline node has its own Dagster budget.** `NODE_TIMEOUTS` states that every node appears
   explicitly, but 15 did not: Stories 21.6 and 23.1 and the derived and Artifactory joins. All 15, plus the new
   driver, now have entries, and one test pins the whole set both ways (healed tissue).

Ledger key: `34-8-migration-status-fills-through-a-driver-node`.
Type / Effort / Deps: feature / S / Story 34.4 (the flag and `public_sources`), Story 34.6 (`fetch_text`).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-64** (`live-sources.md`, R6, "37 migration partitions"): a feature behind
  `pyforge.atlas.live_public_sources`.
- **AD-2** (dataset-owned IO over a composed `APIDataset`), **AD-10** (one writer per dataset), **AD-13**
  (last-good under a marker), **AD-11** (every test's responses are built in memory; the suite pins the flag
  off), **AD-14** (a new signal, never parity-gated).
- **Origin.** Dream entry 2026-10-18 (atlas fills its own data), R6.

## Acceptance Criteria

- **AC1 — The driver.** `drive_migration_status` names every migration each of the five lists carries, once,
  in list order, with each one's first list as its category. A list that failed still leaves `total`'s names
  (`unlisted`). It does no IO.
- **AC2 — Public reads, read at the call.**
  - Flag on with no injected fetcher, a category load requests its status file, and the detail save requests one
    `migration_json/<name>.json` per name.
  - Flag off: nothing requested; the offline marker.
  - Both states are tested with `flag_states`.
  - An injected fetcher wins over the public path with the flag on.
  - A public empty category is written as empty.
- **AC3 — The sweep's guards.**
  - A clean sweep clears the marker and removes partitions the names no longer list, never a hidden file.
  - A failed partition keeps last-good, removes nothing, and marks the run stale.
  - No names keeps last-good under the marker.
  - A name that is not a slug is never fetched or written, a path behind a slug prefix included.
  - A flag-off save removes nothing, whatever names it is given.
  - A partition that cannot be removed is logged, and the sweep stands.
  - The load keeps the sweep's marker, on a fresh root too. An offline marker from an earlier flag-off run gives
    way to "sweep pending".
- **AC4 — Readiness fills.** The swept partitions feed `classify_migration_readiness` end to end, in a test and
  live (see Verification). Every readiness row carries its migration's category.
- **AC5 — Budgets.** Every node of the default pipeline has a `NODE_TIMEOUTS` entry, and every entry names a node.
- **AC6 — Gates.** `pyforge-atlas-test`, `kedro-test`, `kedro-catalog-check`, the coverage gate, `lint-types`
  (and mypy in `pyforge-foundry-full`), `flag-gate-check`; governing Specs reconciled and stamped scoped.

## Verification

- Unit, each named from the repo root:
  - `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_migration_status.py` covers:
    - the driver;
    - the two-state tests, spelled with `@flag_states("pyforge.atlas.live_public_sources")`;
    - the sweep's guards and the round-1 repros;
    - the end-to-end readiness test.
  - `src/shared/packages/pyforge-atlas/tests/unit/orchestration/test_definitions_dryrun.py`: every node has its own
    timeout.
  - `src/shared/packages/pyforge-atlas/tests/unit/pipelines/test_dag_resolves.py`: the node counts (vcs_health 12),
    and the detail store's single writer.
  - `src/shared/packages/pyforge-atlas/tests/unit/parity/test_parity_complete.py`: the new-signal node list.
  - `src/shared/packages/pyforge-atlas/tests/unit/pipelines/vcs_health/test_migration_readiness.py`: the readiness
    columns, `category` among them.
  - `src/shared/packages/pyforge-atlas/tests/unit/catalog/test_catalog_resolution.py`: the entry counts
    (`vcs_health` 28, total 129).
- **Live, recorded 2026-10-18.**
  - **Setup:** a scratch copy of the 2026-10-17 data root with Story 34.4's `core_downloads`, flag on (dev),
    `--pipelines vcs_health --nodes drive_migration_status,classify_migration_readiness`.
  - **Cold:** exit 0, 11.3 s, peak RSS 0.82 GB.
    - 37 detail partitions; no marker on any of the six datasets.
    - The category files hold 22 / 6 / 3 / 6 / 31.
  - **`vcs_migration_readiness`:** 0 → 1,282,642 rows, 37 migrations × 34,666 enumerated packages. `noarch`
    884,596; `not-in-tracker` 387,372; `rebuild-done` 7,768; `confirmed-pending` 2,906.
  - **Warm, with a planted `retired_migration.json`:** exit 0, 6.8 s. The planted partition was removed and 37
    remain.
  - **After review round 2, cold:** exit 0, 13.2 s, peak RSS 0.85 GB, the same 37 partitions and 1,282,642 rows.
    `vcs_migration_categories` holds 22 regular, 6 longterm, 3 paused and 6 closed, and every readiness row
    carries one.

## Boundaries & Constraints

**Never:**
- a credential on `raw.githubusercontent.com`;
- an HTTP client import in the package;
- a test that touches the network;
- `version_status.v2.json` as a partition (`EXCLUDED_STATUS_FILES`, unchanged);
- a partition path built from a name that is not a migrator slug.

**Residual risk:**
- **A closed migration that leaves `closed_status.json`** has its partition removed on the next clean sweep, as
  any name that leaves every list does.
- **Every list failing with no last-good** leaves no names. That is never a clean sweep, so nothing is removed.
- **A public `{}` for every open list.** If regular, longterm, paused and total all answer `{}` while closed is
  intact, the sweep is clean over the closed names alone and removes every open partition. This is unlikely: the
  bot writes every list from one migrator load. The next good run restores the partitions.
- **Readiness size:** the node emits one row per enumerated package per migration (Story B10's design), about
  35,000 rows per migration.
- **netrc on a redirect:** a redirect to another host still consults `~/.netrc` for that host (requests'
  `rebuild_auth`). `raw.githubusercontent.com` does not redirect today.
- **The kedro-viz mirror is stale.** The generated prototype (`src/prototype/packages/pyforge-atlas-kedro-viz/`)
  has been stale since 2026-07-18 and lacks this node, as it lacks Story 25.1's. It is regenerated by hand in
  `-e local-recipes`, and no gate reads it.
- **An injected fetcher** keeps B10's contract: its category load never fetches. Nothing injects one today; a
  Dagster resource that does must drive `refresh()` itself.

## I/O & Edge-Case Matrix

| Situation | Before | After |
|---|---|---|
| Live run, flag on | detail empty, readiness 0 rows | one partition per listed migration (37); readiness fills |
| Flag off | offline marker | unchanged |
| One migration's detail 404s | — | that partition keeps last-good; run marked stale; nothing removed |
| A migration leaves every list | — | its partition is removed on the next clean sweep |
| The bot publishes an empty category | marked stale, last-good kept | written as empty |
| Every category list unreadable, fresh root | — | "no migration names to sweep"; the load keeps that marker |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-64 (FR-72), a feature.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-18 (atlas fills its own data), R6.
- Epic 34 / Story 34.8 in `planning-artifacts/epics.md`.
- Flag: `pyforge.atlas.live_public_sources` (`feature-flag-governance:CAP-1`), registered by Story 34.4.

## Spec Change Log

- 2026-10-18: written with the implementation (branch `atlas-34-8-migration-driver`, cut from Story 34.6's branch
  for `public_sources.fetch_text`).
- 2026-10-18: independent review round 1 FAIL: 3 blockers, 5 should-fix, 11 nits; 28 mutants, 4 survived.
  - **Blockers:**
    - **B1:** on a fresh root the load overwrote the sweep's marker. It now marks only with no marker present,
      with fresh-root tests.
    - **B2:** paused contributed nothing visible in the driver test, and nothing tested an injected fetcher with
      the flag on. Tests now cover both; all four survivors are killed.
    - **B3:** red gates inherited from 34.6's branch. Fixed by merging 34.6's branch, which carries `main`.
  - **Should-fix:**
    - **S1:** a public empty category is now valid.
    - **S2:** `total` now always contributes its names.
    - **S3:** the docstring and catalog comments are rewritten. `ACTIVE_CATEGORIES` keeps its meaning, the open
      set.
    - **S4:** the partition set is now every listed migration, so the count is the Spec's 37; "16" is corrected
      to 15 plus the driver.
    - **S5:** declined. An injected fetcher's category load stays B10's attended contract (B10's
      `test_category_wired_but_unpopulated_load_marks_stale`), and nothing injects one; recorded as residual risk.
  - **Nits:**
    - **N1:** names are validated as migrator slugs.
    - **N2:** the prune skips hidden files.
    - **N3:** the sweep returns its own success, instead of the prune re-reading the marker.
    - **N4:** partition presence no longer parses partitions.
    - **N5:** the driver docstring.
    - **N6:** the timeout comments.
    - **N7:** the stale node-count comment.
    - **N8:** the pipeline comments sit with their nodes.
    - **N9:** the detail store joins the single-writer pin.
    - **N10:** requested URLs, the offline reason and `last_good_exists` are asserted.
    - **N11:** `_describe` names the public URL, and the marker text no longer says "wired fetcher".
- 2026-10-18: re-review round 2 FAIL: 2 blockers, 3 should-fix, 4 nits; 42 mutants, 7 survived.
  - **Blockers:**
    - **RB1:** no test failed when a flag-off sweep pruned. With the flag off by default in production, that
      path could unlink every partition. Fixed: a flag-off save with unlisted names, or with none, removes nothing.
    - **RB2:** the merge of 34.6's branch reverted 34.8's scoped stamp. The scoped stamps then refused, printing
      only "baseline untouched", which was read as success. Fixed: re-stamped after the round-2 merge of `main`,
      with the full output read and each governed file's baseline hash checked against the tree.
  - **Should-fix:**
    - **RS1:** readiness could not tell closed or paused migrations from open ones. Fixed by the category column;
      the FR-21 deviation is recorded.
    - **RS2:** stale "active" wording is fixed in the dataset, node and catalog docstrings.
    - **RS3:** a path behind a slug prefix is now tested.
  - **Nits:**
    - **N1:** an offline marker gives way to "sweep pending" on a flag-on load.
    - **N2:** the public-empty-open-lists prune is named in Residual risk.
    - **N3:** `last_good_exists` and a public `null` are pinned.
    - **N4:** the driver fixture's `total` is now the realistic union.
