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
review_loop_iteration: 0
followup_review_recommended: false
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
  `fetch_partitions` that nothing calls. No node reads the five category entries
  (`vcs_migration_{regular,longterm,paused,closed,total}_status_raw`), and no node writes
  `vcs_migration_detail_raw`. So the detail store stayed empty under "offline: no GitHub-raw fetcher wired", and
  `classify_migration_readiness` had nothing to classify.
- The bot's status files are public. On 2026-10-18 `conda-forge-bot-data/main/status/` listed 22 regular, 6
  longterm, 3 paused and 6 closed migrations; `migration_json/<name>.json` holds each one's per-package state.
- **Legacy reference:** none. `vcs_migration_readiness` is an AD-14 new signal and is never parity-gated.

**Approach:**
1. **The datasets read the bot's files publicly.** With no injected fetcher, each dataset asks
   `public_sources.live()` at each load or save, never at construction. On, the fetcher is
   `public_sources.fetch_text` plus `json.loads`: one unauthenticated GET with a 300 s timeout and no `~/.netrc`
   credential. An injected fetcher still wins. Off, today's offline behaviour stands.
   - A category `load()` refreshes first, so the driver node reads the current list. On failure it keeps last-good
     under the AD-13 marker.
2. **A driver node, `drive_migration_status`, is the detail store's single writer (AD-10).** It is pure: active =
   regular + longterm + paused, less any name the closed list carries, first-seen order, no duplicates. With none
   of the three lists loaded, the total list (less closed) stands in. Its output is the detail dataset's `save()`.
3. **`MigrationDetailDataset.save(names)` is the sweep.** It fetches one `migration_json/<name>.json` partition
   per name through `fetch_partitions`. Its guards:
   - No names is never a clean sweep: last-good stays, under "no active migration names to sweep".
   - After a clean sweep, a partition the names no longer list (a closed or retired migration) is removed, so
     readiness classifies only the active set. A partial sweep removes nothing.
   - `load()` never fetches, so it never overwrites the sweep's marker.
4. **Every default-pipeline node has its own Dagster budget.** `NODE_TIMEOUTS` states that every node appears
   explicitly, but 16 did not: Stories 21.6, 23.1 and 34.5 and the derived and Artifactory joins. All 16, the new
   driver among them, now have entries, and one test pins the whole set, both ways (healed tissue).

Ledger key: `34-8-migration-status-fills-through-a-driver-node`.
Type / Effort / Deps: feature / S / Story 34.4 (the flag and `public_sources`), Story 34.6 (`fetch_text`).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-64** (`live-sources.md`, R6): a feature behind `pyforge.atlas.live_public_sources`.
- **AD-2** (dataset-owned IO over a composed `APIDataset`), **AD-10** (one writer per dataset), **AD-13**
  (last-good under a marker), **AD-11** (every test's responses are built in memory; the suite pins the flag
  off), **AD-14** (a new signal, never parity-gated).
- **Origin.** Dream entry 2026-10-18 (atlas fills its own data), R6.

## Acceptance Criteria

- **AC1 — The driver.** `drive_migration_status` names regular + longterm + paused less closed, first-seen, no
  duplicates, and falls back to total less closed. It does no IO.
- **AC2 — Public reads, read at the call.** Flag on with no injected fetcher, a category load requests its status
  file, and the detail save requests one `migration_json/<name>.json` per name. Flag off: nothing requested; the
  offline marker. Both states are tested with `flag_states`. An injected fetcher still wins.
- **AC3 — The sweep's guards.** A clean sweep clears the marker and removes partitions the names no longer list.
  A failed partition keeps last-good, removes nothing, and marks the run stale. No names keeps last-good under the
  marker. A partition that cannot be removed is logged and the sweep stands. `load()` does not overwrite the
  sweep's marker.
- **AC4 — Readiness fills.** The swept partitions feed `classify_migration_readiness` end to end, in a test and
  live (see Verification).
- **AC5 — Budgets.** Every node of the default pipeline has a `NODE_TIMEOUTS` entry, and every entry names a node.
- **AC6 — Gates.** `pyforge-atlas-test`, `kedro-test`, `kedro-catalog-check`, the coverage gate, `lint-types`
  (and mypy in `pyforge-foundry-full`), `flag-gate-check`; governing Specs reconciled and stamped scoped.

## Verification

- Unit, each named from the repo root:
  - `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_migration_status.py`: the driver, the two-state
    tests spelled with `@flag_states("pyforge.atlas.live_public_sources")`, the sweep's guards, and the end-to-end
    readiness test.
  - `src/shared/packages/pyforge-atlas/tests/unit/orchestration/test_definitions_dryrun.py`: every node has its own
    timeout.
  - `src/shared/packages/pyforge-atlas/tests/unit/pipelines/test_dag_resolves.py` and
    `src/shared/packages/pyforge-atlas/tests/unit/parity/test_parity_complete.py`: the node counts (vcs_health 12)
    and the new-signal node list.
- Live, recorded 2026-10-18: scratch copy of the 2026-10-17 data root with Story 34.4's `core_downloads`, flag on
  (dev), `--pipelines vcs_health --nodes drive_migration_status,classify_migration_readiness`.
  - **Cold:** exit 0, 13.6 s, peak RSS 0.74 GB. 31 detail partitions, no marker on any of the six datasets.
  - **`vcs_migration_readiness`:** 0 → 1,074,646 rows, 31 migrations × 34,666 enumerated packages. `noarch`
    741,148; `not-in-tracker` 322,893; `rebuild-done` 7,712; `confirmed-pending` 2,893.
  - **Warm, with a planted `retired_migration.json`:** exit 0, 6.0 s. The planted partition was removed; 31
    remain, and readiness is unchanged.

## Boundaries & Constraints

**Never:** a credential on `raw.githubusercontent.com`; an HTTP client import in the package; a test that touches
the network; `version_status.v2.json` as a partition (`EXCLUDED_STATUS_FILES`, unchanged).

**Residual risk:**
- **Category failure with no last-good.** If a category list fails on its first run while detail partitions exist
  from an earlier root, a clean sweep of the remaining names removes those partitions. Each category keeps its own
  marker, so the gap is visible, and the next good run restores the partitions.
- **Readiness size.** The node emits one row per enumerated package per migration (Story B10's design), about
  35,000 rows per active migration.
- **netrc on a redirect:** a redirect to another host still consults `~/.netrc` for that host (requests'
  `rebuild_auth`). `raw.githubusercontent.com` does not redirect today.
- The generated kedro-viz prototype mirror (`src/prototype/packages/pyforge-atlas-kedro-viz/`) has been stale since
  2026-07-18 and lacks this node, as it lacks Story 25.1's. It is regenerated by hand in `-e local-recipes`, and no
  gate reads it.

## I/O & Edge-Case Matrix

| Situation | Before | After |
|---|---|---|
| Live run, flag on | detail empty, readiness 0 rows | one partition per active migration; readiness fills |
| Flag off | offline marker | unchanged |
| One migration's detail 404s | — | that partition keeps last-good; run marked stale; nothing removed |
| A migration closes upstream | — | its partition is removed on the next clean sweep |
| Every category list empty or unreadable | — | detail keeps last-good under "no active migration names to sweep" |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-64 (FR-72), a feature.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-18 (atlas fills its own data), R6.
- Epic 34 / Story 34.8 in `planning-artifacts/epics.md`.
- Flag: `pyforge.atlas.live_public_sources` (`feature-flag-governance:CAP-1`), registered by Story 34.4.

## Spec Change Log

- 2026-10-18: written with the implementation (branch `atlas-34-8-migration-driver`, cut from Story 34.6's branch
  for `public_sources.fetch_text`).
