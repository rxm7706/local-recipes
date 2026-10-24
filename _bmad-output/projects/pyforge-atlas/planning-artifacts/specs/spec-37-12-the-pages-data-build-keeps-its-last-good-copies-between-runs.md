---
title: '37.12: The Pages data build keeps its last good copies between runs'
type: 'fix'
created: '2026-10-24'
status: 'in-progress'
baseline_revision: '2859b706da'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-34-12-a-vulnerability-feed-that-cannot-be-reached-keeps-its-last-good-copy.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-37-2-the-pages-vizro-export-builds-the-public-atlas-data-first.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/dreams/pyforge-atlas.md
  - .github/workflows/kedro-viz-publish.yml
  - src/shared/packages/pyforge-atlas/conf/base/globals.yml
  - src/shared/packages/pyforge-atlas/conf/base/catalog.yml
  - src/shared/packages/pyforge-atlas/tests/unit/test_vizro_static_boards.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 34.12 (merged as `2859b706da`) made the CISA KEV, FIRST EPSS and MITRE CWE feeds keep their last
good frame as `raw/<entry>/last_good.parquet` and serve it under the AD-13 `.staleness.json` marker when a fetch
fails. Every other public store that keeps a last-good copy (the `raw/` JSON and API sources, the download and upload
aggregates, the OS-distro and discovery indexes, the OSV store) does the same. But the kedro-viz-publish `vizro` job
(Story 37.2) builds on a fresh checkout every run: its data root, `src/shared/packages/pyforge-atlas/data` (the
member's `data/`, the `globals.yml` default the bootstrap writes from the member directory), starts empty. So on Pages
there is never a copy: an outage publishes the source's table empty under its marker, and the bootstrap-index-health
board reads `missing` (34.12's residual risk).

**Approach:**
1. After the disk is freed and before the build, the job restores the newest last-good cache with
   `actions/cache/restore@v6` (the action `platform-ci.yml` already uses): key
   `pyforge-atlas-last-good-${{ github.run_id }}`, `restore-keys: pyforge-atlas-last-good-`. A run restores the
   entry the newest earlier successful run saved (the workflow's `concurrency` group serialises runs); a miss or an
   eviction leaves the fresh root of before.
2. After the build (`pyforge-atlas-bootstrap`, then `catalog_index`) and before the export, the job saves with
   `actions/cache/save@v6`, the same paths and key. Both steps carry the build's gate,
   `steps.vizro_flag.outputs.enabled == 'true'`, with no status function, so `success()` is implied: a failed build
   fails the job and saves nothing, and the next run restores the last good save. A failed export after a good build
   still keeps the build's copies.
3. What persists: `data/raw` and `data/stores/*`, except `data/stores/vdb`. Those hold what a dataset keeps as its own
   last-good copy and marker (every raw-layer catalog entry under the data root lies there). Not persisted: the
   vulnerability database store (9.6 GB on 2026-10-21, as large as the repository's whole 10 GB Actions cache; it is
   rebuilt every run, as today), and every pipeline output (`intermediate/`, `primary/`, `derived/`) and `cache/`, so a
   node that stops writing cannot hide behind an old file.
4. The list is `stores/*` beside `!stores/vdb`, never `stores`. `actions/cache` resolves its patterns with
   `@actions/glob` and `implicitDescendants: false` (`cacheUtils.resolvePaths`), and archives the matches with
   `tar --files-from` and no `--no-recursion` (`tar.ts`), so a listed directory is archived whole and an exclusion
   under it is ignored. With `stores/*`, each child of `stores/` is a match and `!stores/vdb` removes the one child.
   The entry's version hashes the path strings (`getCacheVersion`), so the restore and the save carry the same list.
   GNU tar keeps each file's mtime on extract (no `-m`), so provenance still reports a restored copy's own age.
5. Consequence, as on a workstation: a store inside its refresh cadence, or whose ETag has not changed (Story 34.4's
   S3 months, Story 37.6's repodata subdirs), is not fetched again.

Ledger key: `37-12-the-pages-data-build-keeps-its-last-good-copies-between-runs`.
Type / Effort / Deps: fix / S / 34.12.

### Living CAP citations

- `spec-pyforge-atlas` CAP-63 (amended 2026-10-19: the Pages producer builds the public data first) and CAP-64 (an
  unreachable endpoint keeps last-good and marks stale, AD-13). The job's fresh root voided CAP-64's promise on Pages.
  A defect, so no new CAP and no `SPEC.md` text change. Epic 34's rule (a fix restores what was meant to work) holds:
  no new flag; the two steps sit behind Story 30.2's `pyforge.atlas.vizro_static_boards`, as every step of the job does.
- AD-11 (public-only, operator ruling "Public-only Pages"), AD-13 (last-good under a marker), AD-17 (provenance is the
  data's own: a restored copy keeps its mtime).

## Acceptance Criteria

- **AC1 — Restore before the build.** The `vizro` job runs `actions/cache/restore@v6` after the flag and the disk
  steps and before `Build the public atlas data`, under the build's gate.
- **AC2 — Save after a build that succeeds.** It runs `actions/cache/save@v6` after the build and before the export,
  under the build's gate with no `always()`/`failure()`; neither the build nor the save carries `continue-on-error`.
- **AC3 — Same entry.** The restore and the save name the same path list and the key
  `pyforge-atlas-last-good-${{ github.run_id }}`; the restore's only fallback is the key's prefix, and it does not set
  `fail-on-cache-miss`.
- **AC4 — What persists.** The path list is exactly `<member>/data/raw`, `<member>/data/stores/*` and
  `!<member>/data/stores/vdb`: never an output layer or `cache/`, never `stores` listed as itself.
- **AC5 — The build's own data root.** The `globals.yml` data root defaults to `data`, the bootstrap task runs from the
  member directory, and no step of the job sets `PYFORGE_ATLAS_DATA_ROOT`.
- **AC6 — Every last-good copy is covered.** Every raw-layer catalog entry whose path resolves under the data root lies
  under `raw/` or `stores/`, the vulnerability database store the one exclusion; no other layer's entry lies under a
  cached path.
- **AC7 — Public-only.** The job names no secret, no `GITHUB_TOKEN`/`GH_TOKEN` and no `PYFORGE_ATLAS_CREDENTIALED`
  (Story 37.2's test), and the workflow has no `pull_request`/`pull_request_target` trigger, so nothing a pull request
  runs writes a cache that main restores.
- **AC8 — Mutation.** Each AC has a test that fails when its behaviour is removed.

## Boundaries & Constraints

**Never:** cache the vulnerability database store or a pipeline output; pass a secret or token to the job; set
`PYFORGE_ATLAS_CREDENTIALED`; let a failed build pass or save; change a dataset, a node or the export.

**Residual risk:**
- Eviction. The repository's Actions cache held 10.45 GB on 2026-10-24 (28 entries, 9.9 GB of them pixi
  environments), over the 10 GB limit, and GitHub evicts the least recently used entries; an entry not read for 7 days
  is removed. A weekly-only stretch reads the entry about 6 days 22 hours after its save. An evicted entry is the fresh
  root of before, never worse.
- Cache pressure. Each run that builds saves one entry of a few hundred MB (on a 2026-10-21 public root, `raw/` was
  19 MB and `stores/` without `vdb` about 290 MB, 242 MB of it the S3 download aggregates). Older entries are never
  read again and age out first.
- A dispatch on another branch reads main's entries and saves to its own branch's scope; main never reads it.
- A restored directory of a removed or renamed catalog entry rides along until it is deleted by hand; it is not read.
- A copy the previous run accepted is trusted as last-good again. Each dataset's own checks (34.12's shape check and
  set-aside, the stores' readers) still apply on load.
- The `@actions/glob` behaviour is read from the upstream source, not executed here (no runner); the first two runs on
  main after the merge are the live proof (*Verification*).

## I/O & Edge-Case Matrix

| Run | Cache | Build | Data root at build start | Saved |
|---|---|---|---|---|
| first after the merge | none | succeeds | empty (as before) | this run's `raw/`, `stores/*` without `vdb` |
| next, a feed down | newest entry | succeeds | the previous copies | this run's (the down feed's copy is the restored one, marked stale) |
| next, build fails | newest entry | fails | the previous copies | nothing; the job fails |
| next, entry evicted | none | succeeds | empty | this run's |
| flag off | not read | not run | n/a | nothing |
| re-run of one run id | that run's entry, if saved | either | that entry | nothing new (the key exists; the save warns) |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-atlas` CAP-63 (amended 2026-10-19) and CAP-64. No CAP is minted, and no
  `SPEC.md` text changes; the memlog carries the decision.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-24 entry (on Pages, last-good has nothing to
  keep).
- Epic: Epic 37 (done; this story reopens it until it lands).
- Ledger key: `37-12-the-pages-data-build-keeps-its-last-good-copies-between-runs`; status at mint `in-progress`.
- Follows Story 34.12 (its residual risk "the Pages job builds on a fresh data root").

## Verification

**Commands** (from the repo root, every verdict read from its exit code):
- `pixi run -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/unit/test_vizro_static_boards.py`
  — expected: pass.
- `pixi run -e pyforge-atlas pyforge-atlas-test` — expected: pass.
- `pixi run -e pyforge-guild lint-types` — expected: exit 0.
- `TMPDIR=$HOME/.cache/pyforge-preflight-tmp PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` —
  expected: exit 0.

**After the merge** (live; read from the run logs): the first `vizro` run on main logs `Cache not found` at the restore
and `Cache saved with key: pyforge-atlas-last-good-<run_id>` at the save, with a cache size in the hundreds of MB (a
size near 9.6 GB means the vdb store was archived: revert); the next run's restore logs `Cache restored from key:` that
key.

## Run results

Run 2026-10-24 in worktree `laughing-jackson-2bff14` (branch `claude/laughing-jackson-2bff14`, from `2859b706da`).

- **Tests:** `test_vizro_static_boards.py` 19 passed (12 before, 7 new).
- **Mutations** (`scratchpad/mutate.py`, each restored): 20 of 20 killed: no restore; no save; the restore after the
  build; the save before the build; the save under `always()`; the restore ungated; `stores` listed as itself; no vdb
  exclusion; `primary/` cached; the save naming another path list; a key that differs; no `restore-keys`;
  `fail-on-cache-miss`; `continue-on-error` on the build; `PYFORGE_ATLAS_DATA_ROOT` on the build; a `pull_request`
  trigger; the `globals.yml` data root moved; a raw entry under `cache/`; an output under `raw/`; the vdb store renamed
  inside `stores/`.
- **Upstream behaviour read 2026-10-24** (`actions/toolkit` main): `packages/cache/src/internal/cacheUtils.ts`
  (`resolvePaths`: `implicitDescendants: false`; `getCacheVersion`: a SHA-256 of the path strings, the compression
  method and a salt), `packages/cache/src/internal/tar.ts` (create: `--files-from`, no `--no-recursion`; extract: no
  `-m`/`--touch`), `packages/glob/src/internal-pattern.ts` (minimatch `dot: true`; a leading `!` negates).
- **Cache budget, 2026-10-24** (`gh api repos/rxm7706/local-recipes/actions/cache/usage`): 10,450,545,115 bytes in 28
  entries.

## Spec Change Log

- 2026-10-24: minted `in-progress` under Epic 37.

## Review Triage Log
