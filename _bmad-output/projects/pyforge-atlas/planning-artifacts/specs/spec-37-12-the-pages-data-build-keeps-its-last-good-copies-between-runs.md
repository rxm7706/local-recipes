---
title: '37.12: The Pages data build keeps its last good copies between runs'
type: 'fix'
created: '2026-10-24'
status: 'in-progress'
baseline_revision: '2859b706da'
review_loop_iteration: 4
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
  - DW-atlas-37-12-3
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
3. What persists is what a dataset reads back as its own previous copy: `data/raw` and `data/stores/*` (except
   `data/stores/vdb`), and `data/primary/vulnerability_rollup_snapshots`. Every raw-layer catalog entry under the data
   root lies under the first two. In all but seven, the dataset keeps its own last-good copy and marker; a trigger node
   emits a refresh request, and the store's dataset writes the copy. The test pins the 32 classes that do this.
   - The snapshot history (`vulnerability_rollup_snapshots`, the one `SnapshotHistoryDataset`) is appended to on
     every run and deduplicated on `(snapshot_at, conda_name)`. `diff_vulnerability_snapshots` diffs the latest
     snapshot against the newest one at least `since_days` (7) older. When none is, it falls back to the
     second-latest. So from the second run whose cache survives, the cve-watcher has a pair of snapshots to diff on
     Pages, which Story 37.5 left empty there "until a store persists across runs". A pair hours apart often moves no
     count, and then the board is still empty. **Operator ruling 2026-10-24: "Approve"** (this scope change,
     given in the Story 37.12 session; on the memlog).
   - Seven raw-layer entries there are no last-good store. Five are plain (any type outside
     `pyforge.atlas.datasets`), and two are the SBOM entries, whose runtime-param defaults the Pages build never
     writes. `org_audit_candidates`, `artifactory_downloads_raw` and `artifactory_consumption_raw` are
     rewritten by their nodes on every build. Two are written only by another station, never by the Pages build:
     `query_plane_estate_source` (steward's export; only `query_plane_cache` reads it, and the build does not run that
     pipeline) and `warden_fleet_inventory` (`stores/warden_fleet_inventory.json`, warden's export).
   - `pypi_conda_map_store` (`stores/pypi_conda_map.json`, a `MappingCacheDataset`) merges each export onto its last
     copy and keeps the keys only the old copy has. On Pages that map now grows across runs, as it does on a
     workstation, and it feeds `pypi_json_raw`'s candidate set.
   - Not persisted:
     - the vulnerability database store (9.6 GB on 2026-10-21, close to the repository's whole 10 GB default cache;
       it is rebuilt every run, as today);
     - every other output-layer file (`intermediate/`, `primary/`, `derived/`), so a stopped node's table there
       cannot hide behind an old file;
     - `cache/`;
     - the `IncrementalParquetDataset` TTL row caches. They are only an optimisation, and each Pages build recomputes
       them, as before.
     The raw layer's three plain node outputs are cached and rewritten every build.
4. The list is `stores/*` beside `!stores/vdb`, never `stores`. `actions/cache` resolves its patterns with
   `@actions/glob` and `implicitDescendants: false` (`cacheUtils.resolvePaths`). It archives the matches with
   `tar --files-from` and no `--no-recursion` (`tar.ts`), so a listed directory is archived whole and an exclusion
   under it is ignored. With `stores/*`, each child of `stores/` is a match, and `!stores/vdb` removes that one
   child. The entry's version hashes the path strings (`getCacheVersion`), so the restore and the save carry the same
   list. GNU tar keeps each file's mtime on extract (no `-m`), so provenance still reports a restored copy's own age.
5. The consequence is the same as on a workstation, for the cached stores: a store that is inside its refresh
   cadence, or whose ETag has not changed, is not fetched again. That covers Story 34.4's S3 months and Story 37.6's
   repodata subdirs.
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
- **AC4 — What persists.** The path list is exactly `<member>/data/raw`, `<member>/data/stores/*`,
  `<member>/data/primary/vulnerability_rollup_snapshots` and, last, `!<member>/data/stores/vdb`. It lists no other
  output-layer path, never `cache/`, and never `stores` itself.
- **AC5 — The build's own data root.** The `globals.yml` data root defaults to `data`, and the bootstrap task runs
  from the member directory. `PYFORGE_ATLAS_DATA_ROOT` is set nowhere the job reads: not in the workflow, job or step
  `env`; not in the bootstrap or export pixi task's `env` or `cmd`; and not in the `pyforge-atlas` feature's or the
  workspace's activation env.
- **AC6 — Every last-good copy is covered.** Read every path key `CatalogIndexDataset` reads (`filepath`, `path`,
  `filename`). Every raw-layer entry whose path resolves under the data root lies under `raw/` or `stores/`. Nothing
  except the vulnerability database store lies at or under `stores/vdb`. Every `SnapshotHistoryDataset` lies under
  its listed path, and no other entry of another layer lies under a cached path. The raw-layer entries under a cached
  path whose class is not one of the pinned last-good classes are exactly the seven named in Approach 3.
- **AC7 — Public-only.** The job names no secret, no `GITHUB_TOKEN`/`GH_TOKEN` and no `PYFORGE_ATLAS_CREDENTIALED`
  (Story 37.2's test). No workflow in `.github/workflows/` has a trigger that runs untrusted input in main's cache
  scope (`pull_request_target`, `workflow_run`, `issue_comment`, `issues`, `discussion`, `discussion_comment`). A
  `pull_request` run saves to the pull request's own scope.
- **AC8 — Mutation.** Each AC has a test that fails when its behaviour is removed.

## Boundaries & Constraints

**Never:**
- cache the vulnerability database store, or an output-layer file other than the snapshot history;
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
- **The snapshot history grows.** Nothing prunes `vulnerability_rollup_snapshots`: each run that saves adds one
  snapshot, about as many rows as packages with a vulnerability. An eviction resets it.
  - A run between snapshots fewer than 7 days apart diffs against the second-latest, as legacy `cve_watcher.py` does.
- **A failed vulnerability database build republishes the previous diff as current** (`DW-atlas-37-12-3`; worse
  than on a workstation).
  - `stores/vdb` is not cached, so a run whose vdb build fails has no store, and its rollup is empty.
  - `SnapshotHistoryDataset.save` appends nothing for an empty frame. So `diff_vulnerability_snapshots` diffs the
    same pair as the run before.
  - The cve-watcher board shows no snapshot date, and its AD-17 stamp is the derived file's fresh mtime. So the old
    diff reads as current, with no marker.
  - On a workstation the vdb store keeps its last-good copy and the rollup is not empty.
  - Review 4's probe showed it: the third run's diff equalled the second's, from a 27-hour-old snapshot.
  - The fix belongs to Story 37.5's nodes, outside this workflow-only story.
- **A partial rollup appends a partial snapshot.** A run whose vulnerability data is incomplete appends what it has,
  and the diff then shows packages dropping to 0, a mass "resolved". That is Story 37.5's behaviour, the same as on a
  workstation, but Pages rebuilds the vdb every run, so it is reached more often.
- **Other branches.** A dispatch on another branch reads main's entries and saves to its own branch's scope; main
  never reads it.
- **Stale directories.** A restored directory of a removed or renamed catalog entry rides along until someone deletes
  it by hand; nothing reads it.
- **Trusted copies.** A copy the previous run accepted is trusted as last-good again, and each dataset's own checks
  still apply on load (34.12's shape check and set-aside, the stores' `_readable` checks). The PyPI-to-conda map keeps
  every key any earlier run exported (Approach 3).
- **Partial restore.** If the tar extract fails partway, `actions/cache` only warns and leaves a partial tree.
  - The raw-layer readers set aside or refetch what they cannot read (review 1 checked 34.12's set-aside and the S3
    and repodata `_readable` checks).
  - `SnapshotHistoryDataset` does not. It keeps an unreadable history and skips every later append, and the save step
    caches the bad file again.
  - So the cve-watcher stays empty on Pages until the entry is evicted. After the limit raise, that may not happen
    while runs come less than 7 days apart.
  - Recovery is the operator's: delete the repository's `pyforge-atlas-last-good-*` Actions cache entries. The next
    run then starts from a fresh root.
- **Unexecuted behaviour.** The `@actions/glob` behaviour was read from the upstream source; it was not executed here,
  because there is no runner. The first runs on main after the merge are the live proof (*Verification*).

## I/O & Edge-Case Matrix

| Run | Cache | Build | Data root at build start | Saved |
|---|---|---|---|---|
| first after the merge | none | succeeds | empty (as before) | this run's `raw/`, `stores/*` without `vdb`, the snapshot history |
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
  `DW-atlas-37-12-3` (atlas: a failed vdb build republishes the previous cve-watcher diff as current; a fix to Story
  37.5's nodes). Review 2's `DW-atlas-37-12-2` (the snapshot history on Pages) was opened and closed on the branch
  (review 3).
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
- **Mutations** (`scratchpad/mutate.py` and two by hand, each restored): 41 of 41 killed.
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
  - After review 3: the history store left out of the list; the negation listed first; a raw output of
    `DegradingParquetDataset` (a class outside the pinned last-good set) under `raw/`; a second
    `SnapshotHistoryDataset`, not cached; the history store moved off its listed path; a primary output nested under
    the history store's path.
  - After review 4: `PYFORGE_ATLAS_DATA_ROOT=` as a prefix of the bootstrap task's `cmd`; a workspace-level
    `[activation.env]` setting it.
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

- 2026-10-24, review 4 (FAIL: 0 blockers, 2 should-fix, 3 nits), fixed on the same branch:
  - S1 (a failed vdb build republishes the previous diff as current, unmarked): a residual risk and
    `DW-atlas-37-12-3` (a fix to Story 37.5's nodes, outside this story's Never).
  - S2 ("the readers set aside or refetch" was false for the snapshot history): the partial-restore residual risk says
    `SnapshotHistoryDataset` keeps an unreadable file and skips later appends, and names the operator's recovery.
  - N1: a partial rollup's mass "resolved" diff is a residual risk; "fill the cve-watcher" now reads "a pair of
    snapshots to diff" (Approach 3, the DW-2 resolution). N2: the epics `updated:` stamp names the snapshot history.
    N3: the team memory calls the 4 hours a lower bound. AC5 and its test cover the task `cmd` and the workspace's
    activation env.
- 2026-10-24: operator ruling "Approve" on review 3's scope change (the snapshot history persists); recorded in
  Approach 3 and the memlog.
- 2026-10-24, review 3 (FAIL: 0 blockers, 2 should-fix, 3 nits), fixed on the same branch:
  - S1 (the deferral reason misread the cve-watcher): `diff_vulnerability_snapshots` falls back to the second-latest
    snapshot. So the job now caches `data/primary/vulnerability_rollup_snapshots` too, and the cve-watcher fills on
    Pages without the limit raise. `DW-atlas-37-12-2` is closed, and Approach 3, AC4, AC6, Never, the residual risks,
    the Dream, Story 37.12, the workflow comment and the memlog (a correction event) say so.
  - S2 (the eviction horizon was still a fixed 3.5 hours in three records): the DW row, the team-memory capture and
    the memlog correction now say it depends on how much the other workflows write.
  - N1 (the plain-entry guard read the type's module): the test pins the 32 last-good classes and the seven raw
    entries that are not, and checks that no pinned class is stale.
  - N2 ("a node that stops writing cannot hide" was absolute): the wording names the output layers, and says the
    raw layer's plain node outputs are cached and rewritten. N3: review 1's S2 line corrected.
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
  - S2 ("never a pipeline output" was wrong): Approach 3 and the workflow comment name the plain raw-layer entries
    and the PyPI-to-conda map's merge, the Dream and the story say "never an output layer", and the test pins the
    plain entries. (Review 3's N3 corrected this line, which had said the Dream and the story name them too.)
  - S3 (wrong trigger): `test_no_workflow_runs_untrusted_input_in_main_s_cache_scope` scans every workflow for events
    that run in main's cache scope. The workflow comment says so.
  - S4 (test gaps): every catalog path key; a store nested under `stores/vdb/`; the data root override in the
    workflow-level env, the pixi tasks' env and the activation env; `shell` on the build. Each has a killed mutant.
  - Nit 5: the key carries `run_attempt`, so a successful re-run saves its fresher copies. Nit 6: a partial restore is
    a residual risk.
- 2026-10-24: minted `in-progress` under Epic 37.

## Review Triage Log

- 2026-10-24, review 4 (independent subagent): FAIL, 0 blockers, 2 should-fix, 3 nits.
  - It confirmed the write order (the snapshot is appended before the diff reads it), the dedupe and the schema
    handling.
  - It checked all 32 pinned last-good classes and found none wrong.
  - It probed the real `SnapshotHistoryDataset` and diff node with a failed vdb build, a truncated history and a
    partial rollup, which gave S1, S2 and N1.
  - It ran 6 mutants; the 2 survivors folded into the AC5 nit.
  - Every finding was fixed on the branch (Spec Change Log).
- 2026-10-24, review 3 (independent subagent): FAIL, 0 blockers, 2 should-fix, 3 nits.
  - It checked the five plain entries against the pipelines and found every raw entry under the data root cached.
  - It found that the cve-watcher's diff falls back to the second-latest snapshot, which it proved by running
    `diff_vulnerability_snapshots` on two snapshots 3 hours apart (S1).
  - It ran 10 mutants; the one survivor became N1.
  - It ran the planning detectors: all exit 0.
  - Every finding was fixed on the branch (Spec Change Log).
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
