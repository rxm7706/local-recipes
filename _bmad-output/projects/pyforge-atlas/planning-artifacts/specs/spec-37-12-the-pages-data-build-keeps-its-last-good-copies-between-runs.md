---
title: '37.12: The Pages data build keeps its last good copies between runs'
type: 'fix'
created: '2026-10-24'
status: 'in-progress'
baseline_revision: '2859b706da'
review_loop_iteration: 2
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-34-12-a-vulnerability-feed-that-cannot-be-reached-keeps-its-last-good-copy.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-37-2-the-pages-vizro-export-builds-the-public-atlas-data-first.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-atlas.md
  - .github/workflows/kedro-viz-publish.yml
  - src/shared/packages/pyforge-atlas/conf/base/globals.yml
  - src/shared/packages/pyforge-atlas/conf/base/catalog.yml
  - src/shared/packages/pyforge-atlas/tests/unit/test_vizro_static_boards.py
deferred:
  - DW-atlas-37-12-1
  - DW-atlas-37-12-2
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 34.12 (merged as `2859b706da`) made the CISA KEV, FIRST EPSS and MITRE CWE feeds keep their last
good frame as `raw/<entry>/last_good.parquet` and serve it under the AD-13 `.staleness.json` marker when a fetch
fails. Every other public store that keeps a last-good copy does the same: the `raw/` JSON and API sources, the
download and upload aggregates, the OS-distro and discovery indexes, and the OSV store. But the kedro-viz-publish
`vizro` job (Story 37.2) builds on a fresh checkout every run. Its data root, `src/shared/packages/pyforge-atlas/data`
(the member's `data/`, the `globals.yml` default the bootstrap writes from the member directory), starts empty. So on
Pages there is never a copy: an outage publishes the source's table empty under its marker, and the
bootstrap-index-health board reads `missing` (34.12's residual risk).

**Approach:**
1. After the disk is freed and before the build, the job restores the newest last-good cache entry with
   `actions/cache/restore@v6` (the action `platform-ci.yml` already uses). The key is
   `pyforge-atlas-last-good-${{ github.run_id }}-${{ github.run_attempt }}` and `restore-keys` is
   `pyforge-atlas-last-good-`. A run restores the entry that the newest earlier successful run (or attempt) saved;
   the workflow's `concurrency` group runs one at a time. A miss or an eviction leaves the fresh root of before.
2. After the build (`pyforge-atlas-bootstrap`, then `catalog_index`) and before the export, the job saves with
   `actions/cache/save@v6`, using the same paths and key. Both steps carry the build's gate,
   `steps.vizro_flag.outputs.enabled == 'true'`, with no status function, so `success()` is implied. A failed build
   fails the job and saves nothing, and the next run restores the last good save. A failed export after a good build
   still keeps the build's copies. The build keeps the default shell (`bash -e`; no `shell:` on the step and no
   `defaults.run.shell` on the job or workflow), so a failed bootstrap stops the step before `catalog_index` can turn
   it green.
3. What persists: `data/raw` and `data/stores/*`, except `data/stores/vdb`. Every raw-layer catalog entry under the
   data root lies there, and in nearly all of them the dataset keeps its own last-good copy and marker. A trigger node
   emits a refresh request and the store's dataset writes the copy.
   - Five plain raw-layer entries (any type outside `pyforge.atlas.datasets`) also lie there, and none is a
     last-good store. `org_audit_candidates`, `artifactory_downloads_raw` and `artifactory_consumption_raw` are
     rewritten by their nodes on every build. Two are written only by another station, never by the Pages build:
     `query_plane_estate_source` (steward's export; only `query_plane_cache` reads it, and the build does not run that
     pipeline) and `warden_fleet_inventory` (`stores/warden_fleet_inventory.json`, warden's export).
   - `pypi_conda_map_store` (`stores/pypi_conda_map.json`, a `MappingCacheDataset`) merges each export onto its last
     copy and keeps the keys only the old copy has. On Pages that map now grows across runs, as it does on a
     workstation, and it feeds `pypi_json_raw`'s candidate set.
   - Not persisted: the vulnerability database store (9.6 GB on 2026-10-21, close to the repository's whole 10 GB
     default cache; it is rebuilt every run, as today), the output layers (`intermediate/`, `primary/`, `derived/`)
     and `cache/`. So a node that stops writing cannot hide behind an old file.
4. The list is `stores/*` beside `!stores/vdb`, never `stores`. `actions/cache` resolves its patterns with
   `@actions/glob` and `implicitDescendants: false` (`cacheUtils.resolvePaths`). It archives the matches with
   `tar --files-from` and no `--no-recursion` (`tar.ts`), so a listed directory is archived whole and an exclusion
   under it is ignored. With `stores/*`, each child of `stores/` is a match, and `!stores/vdb` removes that one
   child. The entry's version hashes the path strings (`getCacheVersion`), so the restore and the save carry the same
   list. GNU tar keeps each file's mtime on extract (no `-m`), so provenance still reports a restored copy's own age.
5. The consequence is the same as on a workstation: a store that is inside its refresh cadence, or whose ETag has not
   changed, is not fetched again. That covers Story 34.4's S3 months and Story 37.6's repodata subdirs.
6. **Operator ruling 2026-10-24 (option C, "Cache + raise limit"):** keep `actions/cache` for the copies. The operator
   raises the repository's Actions cache limit; that is an operator-owned setting, never changed from a session.
   Until it is raised, the copies survive only between runs a few hours apart (see *Residual risk*). The pending
   raise is `DW-atlas-37-12-1`, also captured in team memory. Two alternatives were set aside:
   - an artifact hand-off from the previous successful run, through a sibling job holding `github.token` with
     `actions: read`, as `pages.yml` does;
   - a best-effort cache with no limit change.

Ledger key: `37-12-the-pages-data-build-keeps-its-last-good-copies-between-runs`.
Type / Effort / Deps: fix / S / 34.12.

### Living CAP citations

- `spec-pyforge-atlas` CAP-63 (amended 2026-10-19: the Pages producer builds the public data first) and CAP-64 (an
  unreachable endpoint keeps last-good and marks stale, AD-13). The job's fresh root voided CAP-64's promise on Pages.
  This is a defect, so there is no new CAP and no `SPEC.md` text change. Epic 34's rule holds: a fix restores what was
  meant to work and needs no new flag. The two steps sit behind Story 30.2's `pyforge.atlas.vizro_static_boards`, as
  every step of the job does.
- AD-11 (public-only, operator ruling "Public-only Pages"); AD-13 (last-good under a marker); AD-17 (provenance comes
  from the data itself, so a restored copy keeps its mtime).

## Acceptance Criteria

- **AC1 — Restore before the build.** The `vizro` job runs `actions/cache/restore@v6` after the flag and disk steps and
  before `Build the public atlas data`, under the build's gate.
- **AC2 — Save after a build that succeeds.** It runs `actions/cache/save@v6` after the build and before the export,
  under the build's gate with no `always()`/`failure()`. Neither the build nor the save carries `continue-on-error`,
  and the build keeps the default shell (no `shell:` on the step, no `defaults.run.shell` on the job or workflow).
- **AC3 — Same entry.** The restore and the save name the same path list and the key
  `pyforge-atlas-last-good-${{ github.run_id }}-${{ github.run_attempt }}`. The restore's only fallback is the key's
  prefix, and it does not set `fail-on-cache-miss`.
- **AC4 — What persists.** The path list is exactly `<member>/data/raw`, `<member>/data/stores/*` and
  `!<member>/data/stores/vdb`. It never lists an output layer or `cache/`, and never lists `stores` itself.
- **AC5 — The build's own data root.** The `globals.yml` data root defaults to `data`, and the bootstrap task runs
  from the member directory. `PYFORGE_ATLAS_DATA_ROOT` is set nowhere the job reads: not in the workflow, job or step
  `env`, not in the bootstrap or export pixi task's `env`, and not in the `pyforge-atlas` activation env.
- **AC6 — Every last-good copy is covered.** Read every path key `CatalogIndexDataset` reads (`filepath`, `path`,
  `filename`). Every raw-layer entry whose path resolves under the data root lies under `raw/` or `stores/`. Nothing
  except the vulnerability database store lies at or under `stores/vdb`. No other layer's entry lies under a cached
  path. The plain raw-layer entries (any type outside `pyforge.atlas.datasets`) under a cached path are exactly the
  five named in Approach 3.
- **AC7 — Public-only.** The job names no secret, no `GITHUB_TOKEN`/`GH_TOKEN` and no `PYFORGE_ATLAS_CREDENTIALED`
  (Story 37.2's test). No workflow in `.github/workflows/` has a trigger that runs untrusted input in main's cache
  scope (`pull_request_target`, `workflow_run`, `issue_comment`, `issues`, `discussion`, `discussion_comment`). A
  `pull_request` run saves to the pull request's own scope.
- **AC8 — Mutation.** Each AC has a test that fails when its behaviour is removed.

## Boundaries & Constraints

**Never:**
- cache the vulnerability database store or an output layer;
- pass a secret or token to the job, or set `PYFORGE_ATLAS_CREDENTIALED`;
- let a failed build pass or save;
- change a dataset, a node or the export;
- change the repository's cache limit from a session (it is the operator's).

**Residual risk:**
- **Eviction, until the limit is raised (operator ruling 2026-10-24, `DW-atlas-37-12-1`).** On 2026-10-24 the
  repository's Actions cache held 10,450,545,115 bytes in 29 entries, about 9.9 GB of them pixi environments. That is
  over the 10 GB limit, and GitHub evicts the least recently used entries. The horizon is set by how much the other
  workflows write, not by a fixed time: at 15:18Z the oldest entry had last been read at 11:42Z, and at 15:54Z
  review 2 still found it (about 4 hours unread).
  - Until the operator raises the limit, the copies survive only between runs a few hours apart. Recent push runs
    came 1 to 11 hours apart, and the copies never survive to the weekly run.
  - After the raise, the weekly-only case reads its entry about 7 days minus the build's run time (1 to 4 hours)
    after the save, inside GitHub's 7-day unused-entry window. A schedule delay longer than that margin loses the
    copy; that run is the fresh root of before.
  - An evicted entry is the fresh root of before, never worse.
- **Cache pressure.** Each run that builds saves one entry of a few hundred MB. On a 2026-10-21 public root, `raw/`
  was 19 MB and `stores/` without `vdb` about 290 MB, 242 MB of it the S3 download aggregates. Older entries are never
  read again and age out first.
- **Output-layer stores still start empty on Pages** (`DW-atlas-37-12-2`, blocked on `DW-atlas-37-12-1`). Two
  kinds of output-layer dataset read their own previous copy: `vulnerability_rollup_snapshots` (`primary/`, the
  `SnapshotHistoryDataset` the cve-watcher diffs; Story 37.5's residual risk) and the `IncrementalParquetDataset` TTL
  row caches. They are not cached, so the cve-watcher stays empty on Pages. Approach 5 covers the raw-layer stores
  only. Caching the snapshot store helps only once copies survive a week, which needs the limit raise.
- **Other branches.** A dispatch on another branch reads main's entries and saves to its own branch's scope; main
  never reads it.
- **Stale directories.** A restored directory of a removed or renamed catalog entry rides along until someone deletes
  it by hand; nothing reads it.
- **Trusted copies.** A copy the previous run accepted is trusted as last-good again, and each dataset's own checks
  still apply on load (34.12's shape check and set-aside, the stores' `_readable` checks). The PyPI-to-conda map keeps
  every key any earlier run exported (Approach 3).
- **Partial restore.** If the tar extract fails partway, `actions/cache` only warns and leaves a partial tree. The
  readers set aside or refetch what they cannot read (review 1 checked 34.12's set-aside and the S3 and repodata
  `_readable` checks).
- **Unexecuted behaviour.** The `@actions/glob` behaviour was read from the upstream source; it was not executed here,
  because there is no runner. The first runs on main after the merge are the live proof (*Verification*).

## I/O & Edge-Case Matrix

| Run | Cache | Build | Data root at build start | Saved |
|---|---|---|---|---|
| first after the merge | none | succeeds | empty (as before) | this run's `raw/`, `stores/*` without `vdb` |
| next, a feed down | newest entry | succeeds | the previous copies | this run's (the down feed's copy is the restored one, marked stale) |
| next, build fails | newest entry | fails | the previous copies | nothing; the job fails |
| next, entry evicted | none | succeeds | empty | this run's |
| flag off | not read | not run | n/a | nothing |
| re-run attempt of a run | the newest entry (the earlier attempt's, if it saved) | either | that entry | this attempt's, under its own key |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-atlas` CAP-63 (amended 2026-10-19) and CAP-64. No CAP is minted and no
  `SPEC.md` text changes; the memlog carries the decision and the operator's ruling.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-24 entry (on Pages, last-good has nothing to
  keep).
- Epic: Epic 37 (done; this story reopens it until it lands).
- Ledger key: `37-12-the-pages-data-build-keeps-its-last-good-copies-between-runs`; status at mint `in-progress`.
- Deferred work: opens `DW-atlas-37-12-1` (operator-owned: raise the repository's Actions cache limit) and
  `DW-atlas-37-12-2` (the output-layer history store and TTL caches on Pages; blocked on the first).
- Follows Story 34.12 (its residual risk "the Pages job builds on a fresh data root").

## Verification

**Commands** (from the repo root, every verdict read from its exit code):
- `pixi run -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/unit/test_vizro_static_boards.py`
  — expected: pass.
- `pixi run -e pyforge-atlas pyforge-atlas-test` — expected: pass.
- `pixi run -e pyforge-guild lint-types` — expected: exit 0.
- `TMPDIR=$HOME/.cache/pyforge-preflight-tmp PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` —
  expected: exit 0.

**After the merge** (live, read from the run logs). The merge itself does not start the job: the workflow file is not
in `on.push.paths`. The first run is the weekly schedule, a push touching the vizro paths, or a dispatch.
- The first `vizro` run on main logs `Cache not found` at the restore, and
  `Cache saved with key: pyforge-atlas-last-good-<run_id>-<attempt>` at the save.
- The saved cache's size is in the hundreds of MB. A size near 9.6 GB means the vdb store was archived: revert.
- A run a few hours later logs `Cache restored from key:` with that key.
- The weekly run's restore is proven once the operator has raised the limit (`DW-atlas-37-12-1`).

## Run results

Run 2026-10-24 in worktree `laughing-jackson-2bff14` (branch `claude/laughing-jackson-2bff14`, from `2859b706da`).

- **Tests:** `test_vizro_static_boards.py`: 19 passed (13 before, 6 new; reviews 1 and 2 widened four of them).
  `pixi run -e pyforge-atlas pyforge-atlas-test` (before review 1's fixes): 3,433 passed and 20 skipped, then 103
  passed. `pixi run -e pyforge-guild lint-types`: exit 0. `scripts/ci_surface_gates.py --check`: exit 0.
- **Mutations** (`scratchpad/mutate.py`, each restored): 33 of 33 killed.
  - The first 20: no restore; no save; the restore after the build; the save before the build; the save under
    `always()`; the restore ungated; `stores` listed as itself; no vdb exclusion; `primary/` cached; the save naming
    another path list; a key that differs; no `restore-keys`; `fail-on-cache-miss`; `continue-on-error` on the build;
    `PYFORGE_ATLAS_DATA_ROOT` on the build; a `pull_request` trigger; the `globals.yml` data root moved; a raw entry
    under `cache/`; an output under `raw/`; the vdb store renamed inside `stores/`.
  - After review 1: no `run_attempt` in the key; a raw store nested under `stores/vdb/`; a raw entry with a `path:`
    key under `cache/`; `PYFORGE_ATLAS_DATA_ROOT` in the workflow-level env; the same in the bootstrap pixi task's
    env; `shell: bash {0}` on the build; a `workflow_run` trigger in another workflow; a new plain raw output under
    `raw/`.
  - After review 2: a plain `json.JSONDataset` raw output under `raw/`; a `text.TextDataset` under `stores/`;
    `defaults.run.shell: bash {0}` on the job; the same on the workflow; `warden_fleet_inventory` dropped from the
    plain set.
- **Upstream behaviour, read 2026-10-24** (`actions/toolkit` main):
  - `packages/cache/src/internal/cacheUtils.ts`: in `resolvePaths`, `implicitDescendants: false`; `getCacheVersion` is
    a SHA-256 of the path strings, the compression method and a salt.
  - `packages/cache/src/internal/tar.ts`: create uses `--files-from` with no `--no-recursion`; extract has no
    `-m`/`--touch`.
  - `packages/glob/src/internal-pattern.ts`: minimatch `dot: true`, and a leading `!` negates.
  - Review 1 confirmed all three independently, with the negation applied in `internal-pattern-helper.ts`.
- **Cache budget, 2026-10-24** (`gh api repos/rxm7706/local-recipes/actions/cache/usage` and `…/actions/caches`):
  10,450,545,115 bytes in 29 entries; the oldest last read at 11:42Z, at 15:18Z.

## Spec Change Log

- 2026-10-24, review 2 (FAIL: 0 blockers, 4 should-fix, 3 nits), fixed on the same branch:
  - S1: the memlog's decision entry still named the old key, "every raw-layer copy" and this workflow's own triggers;
    a correction event follows it (the memlog is append-only).
  - S2: the plain-entry guard reads every type outside `pyforge.atlas.datasets`, and `warden_fleet_inventory` is the
    fifth plain entry (Approach 3, AC6, the workflow comment).
  - S3: the shell check covers `defaults.run.shell` on the job and the workflow (AC2).
  - S4: the output-layer stores that read their own previous copy are a residual risk and `DW-atlas-37-12-2`.
  - Nits: the DW row and the team-memory capture name the per-attempt key; the test count is 13 before and 6 new;
    the eviction horizon is set by write volume, and the weekly margin after the raise is about the build's run
    time; the path-list test reads the workflow's own list, not the module's literal.
- 2026-10-24, review 1 (FAIL: 1 blocker, 3 should-fix, 2 nits), fixed on the same branch:
  - Blocker (the cache evicts within about 3.5 hours): put to the operator. The ruling (option C, "Cache + raise
    limit") is in Approach 6, the memlog, the Dream entry and Story 37.12's Then line. The raise is
    `DW-atlas-37-12-1` and a scribe project capture. The eviction residual risk now carries the measured horizon.
  - S2 ("never a pipeline output" was wrong): Approach 3, the Dream, the story and the workflow comment now name the
    four plain raw-layer entries and the PyPI-to-conda map's merge. The test pins the plain entries.
  - S3 (wrong trigger): `test_no_workflow_runs_untrusted_input_in_main_s_cache_scope` scans every workflow for events
    that run in main's cache scope. The workflow comment says so.
  - S4 (test gaps): every catalog path key; a store nested under `stores/vdb/`; the data root override in the
    workflow-level env, the pixi tasks' env and the activation env; `shell` on the build. Each has a killed mutant.
  - Nit 5: the key carries `run_attempt`, so a successful re-run saves its fresher copies. Nit 6: a partial restore is
    a residual risk.
- 2026-10-24: minted `in-progress` under Epic 37.

## Review Triage Log

- 2026-10-24, review 2 (independent subagent): FAIL, 0 blockers, 4 should-fix, 3 nits.
  - It confirmed the operator's ruling is recorded the same way in all six places.
  - It checked every round-1 fix against the code (the map's merge in `refresh.py`, its use in
    `request_datasets.py`, `catalog_index.py`'s path keys) and traced `@actions/glob` through `stores/*` with
    `!stores/vdb`.
  - It ran 17 mutants: 5 survivors became S2 and S3; 4 more were harmless.
  - It ran the planning detectors (`chain-completeness`, `dream-chain`, `dreams-hygiene`, `deferred-work`,
    `story-status`, `spec-surface`): all exit 0.
  - Every finding was fixed on the branch (Spec Change Log).
- 2026-10-24, review 1 (independent subagent, read the diff against this spec): FAIL, 1 blocker, 3 should-fix, 2
  nits.
  - It read the upstream `actions/toolkit` and `actions/cache` source and confirmed the globbing, the tar recursion,
    the version hash, the gating and the security model.
  - It measured the cache's eviction horizon (the blocker) and ran 14 mutants; the 4 survivors became S4.
  - It ran `chain-completeness-check`, `dream-chain-check`, `story-status-check` and `spec-surface-check`: all exit 0.
  - The blocker went to the operator (Approach 6); every other finding was fixed on the branch (Spec Change Log).
