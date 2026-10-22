---
title: "37.2: The Pages Vizro export builds the public atlas data first"
type: 'feature'
created: '2026-10-21'
status: 'in-review'
baseline_revision: '5faf32c4ca'
flag:
  key: pyforge.atlas.vizro_static_boards          # Story 30.2's; this story adds no flag
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through src/platform/config/flag-overlays.json
  scope: global                                   # v1 is global only
  fallback: 'the vizro job neither builds data nor exports; no vizro-static-export artifact is produced and Pages keeps the last one'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-30-2-vizro-boards-publish-as-static-exports-under-dashboard-vizro.md
  - .github/workflows/kedro-viz-publish.yml
  - .github/workflows/pages.yml
  - src/shared/packages/pyforge-atlas/tools/bootstrap.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/static_export.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the boards on `/dashboard/vizro/` resolve, but every one renders honest-empty. The `vizro` job of
`kedro-viz-publish.yml` exports on a runner that holds no atlas data. Probe of the live site, 2026-10-21: the index and
each board answer 200; `distribution-breakdown` says "backing file not found: `<data-root>/primary/...`", and every
board's `data_build_timestamp` in `manifest.json` is `unavailable`.

**Approach:**
1. **A weekly schedule.** `kedro-viz-publish.yml` gains `schedule: cron '17 5 * * 1'` (Mondays 05:17 UTC) beside its
   push trigger and `workflow_dispatch` (operator ruling 2026-10-19, "Weekly + on push"). A scheduled run is not a
   push, so the `changes` job runs both producers; the `publish` job's weekly run also renews the `kedro-viz-export`
   artifact's 90-day retention. Pages (`pages.yml`, every 6 hours) mounts the newest artifact on its next build.
2. **The public data build.** Between the flag step and the export, one step under the same `if`:
   `pixi run --frozen -e pyforge-atlas pyforge-atlas-bootstrap` (the empty credentials stub from
   `tools/bootstrap.py`'s `CREDENTIAL_KEYS`, the store directories, then the eight fetch pipelines) and
   `pixi run --frozen -e pyforge-atlas pyforge atlas run --pipelines semantic_packages` (the package boards' table).
   The data root is the member's `data/`, which the export reads (Story 37.1). No secret reaches the job and
   `PYFORGE_ATLAS_CREDENTIALED` is never set (AD-11, operator ruling "Public-only Pages"); BigQuery stays off. So every
   credentialed or enterprise source (the OpenTeams board, the staged-recipes PRs, JFrog) stays empty. The identity
   boards show what public inputs give them, the purl associator and the tracked inventory (operator ruling
   2026-10-21, "Publish them"). `query_plane_cache` (its input is steward's export, Story 36.3) and `universal_sbom`
   (entry-scoped) are not run. A failed build fails the job and no artifact is uploaded, so Pages keeps the last export
   it published. A step before the build frees the runner's disk of toolchains the job never uses (.NET, Android, GHC,
   CodeQL, Boost): the vulnerability database store alone reached 9.6 GB.
3. **A row cap on static pages** (DW-atlas-37-3-1). Over a full data root two loaders return 448,301 and 210,170
   rows, which wrote 37.2 MB and 23.1 MB pages. Every table is sorted -- by the page's declared chart measure, largest
   first, when that measure varies, then by every column -- so one commit's export is byte-identical whatever order a
   loader returns; a table over `static_export.STATIC_ROW_CAP = 5_000` rows keeps its first 5,000 in that order, and
   its caption says "N of M rows, the largest <measure> first" (or "the first in column order") "; the live dashboard
   holds every row". A chart never draws the capped table: it sums its measure per bar over the whole frame and keeps
   at most 5,000 bars, the largest, with a line beside it saying so. The page header says tables show "up to 5,000
   rows" and charts sum over all of them. The live dashboard is unchanged.
4. **The job's time budget** is 240 minutes: three times the measured public build (1 h 20 min on a workstation, 40
   min of it PyPI's fan-out at its 10 requests a second).
5. **The job's own hygiene.** Its checkout keeps no token (`persist-credentials: false`); nothing in the build needs
   one. The export runs with `--clock now` (a new option of `tools/vizro_static_export.py`, default `commit`): the
   pages are stamped with the build's own time, since a weekly run of an unchanged main would otherwise date this
   week's data by the last merge; a local export keeps the commit's time and stays byte-identical.

Ledger key: `37-2-the-pages-vizro-export-builds-the-public-atlas-data-first`.
Type / Effort / Deps: feature / M / Story 37.1 (the data root), stacked on Story 37.3 (the boards that read the data).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-63** amended 2026-10-19 (FR-71): the producer builds the public data first, weekly and on
  push. **CAP-64** (a plain run fills every public dataset). **AD-11** (credentialed fetches attended only),
  **AD-21** (herald: no third-party origin; unchanged), **`sld:AD-10`** (the access-column refusal; unchanged).

## Acceptance Criteria

- **AC1 — Weekly.** The workflow triggers on push (its paths), a weekly `schedule` and `workflow_dispatch`, nothing else.
- **AC2 — Data first.** The `vizro` job runs the flag step, then the build step (`pyforge-atlas-bootstrap`, then
  `pyforge atlas run --pipelines semantic_packages`), then the export and the upload; the build and the export share
  the flag's `if`; the build has no `continue-on-error`.
- **AC3 — Public only.** The `vizro` job names no `secrets.`, no `PYFORGE_ATLAS_CREDENTIALED`, no GitHub token and no
  `PHASE_P` variable; the bootstrap task's pipelines are the eight fetch pipelines and never `query_plane_cache`; the
  disk step removes only named toolchain directories under `/usr` and `/opt`; the job's budget is 240 minutes.
- **AC4 — Tables and charts.** Every table is sorted (by a varying chart measure, largest first, then every column;
  a column that does not compare falls back to the measure alone); a table over the cap keeps its first 5,000 rows and
  its caption names both counts; a measure equal on every row is not named as the order. A chart sums its measure per
  bar over the whole frame and keeps at most 5,000 bars, saying so beside it. `--clock now` stamps the build's time.
- **AC5 — Live.** See Verification.
- **AC6 — Gates.** `pyforge-atlas-test`, the dashboard integration suite, the coverage gate, `lint-types`,
  `flag-gate-check`, `ci-surface` detectors; governing Specs reconciled and stamped scoped.

## Verification

- Unit, from the repo root: `src/shared/packages/pyforge-atlas/tests/unit/test_vizro_static_boards.py` and
  `src/shared/packages/pyforge-atlas/tests/unit/test_dashboard_static_export.py`.
- **Live, 2026-10-21,** on a workstation, a fresh scratch data root, no credentials, no switch, no GitHub token in the
  environment, a scratch conf with the bootstrap's empty credential stub:
  - **The build:** `pyforge atlas run --pipelines core,pypi_intelligence,vulnerability,vcs_health,upstream_discovery,
    derived_artifacts,seed_gaps,artifactory_downloads,semantic_packages` exit 0, Kedro "completed successfully in
    4789.0 sec" (wall 1:19:58), 81 nodes, peak RSS 4.35 GB. The data root came to 9.7 GB, 9.6 GB of it the vulnerability
    database store. PyPI's fan-out took 21,326 candidates (157 answered 404). The vdb refresh failed with `apsw.IOError:
    disk I/O error` on the workstation's RAM-backed `/tmp`; the run kept going and marked the store stale (AD-13).
  - **A plain run** (no `--pipelines`) on another fresh root exit 1 after 12 of 86 nodes (DW-atlas-37-2-1).
- **Live, 2026-10-22 (UTC), the workflow's three commands as written,** in a clean worktree at review round 1's fixes:
  no `PYFORGE_ATLAS_DATA_ROOT` (the member's `data/`), no conf/local credentials file (the bootstrap wrote its empty
  stub), no token in the environment. `pixi run --frozen -e pyforge-atlas pyforge-atlas-bootstrap` (installing the
  env, then the eight pipelines; the vdb refresh installed the `vuln-db` env itself and built its store, on disk this
  time, with no stale marker) took 1:16:50; `pyforge atlas run --pipelines semantic_packages` 3 s; `vizro-static-export
  --clock now` 6 s; exit 0 throughout, no token pattern in the log. The data root came to 11 GB, the envs to 3.8 GB.
  The export: `exported_at` the build's own time, 17 of 34 boards stamped, the largest page 488 KB; version-downloads
  says "The chart sums downloads per version over all 448,301 rows and shows the 5,000 largest of 57,075 bars", and
  adoption-stage's caption no longer names its constant measure as the order.
  - **The export** over that root: exit 0 in 4.3 s, 8.0 MB in all; the largest page is 571 KB (distribution-breakdown,
    "5,000 of 210,170 rows, the largest downloads_90d first"); version-downloads 421 KB (5,000 of 448,301). 17 of the
    34 boards carry data and a data-build stamp: feedstock-health (28,966 rows), my-feedstocks (60,380),
    staleness-report, query-atlas, detail-cf-atlas and adoption-stage (34,720 packages), version-downloads,
    distribution-breakdown, the four seed-gap boards (220, 40, 13, 462), identity-catalog (871), identity-ops,
    identity-workbook, identity-export-snapshot and factory-status. The other 17 are honest-empty: estate-cache (Story
    36.3), behind-upstream, whodepends, universe-sbom and live-catalog-coverage (Story 37.4), cve-watcher,
    release-cadence, find-alternative, export-purls, mapping-gap and bootstrap-index-health (Stories 37.5-37.10),
    scan-project and env-inspect (per-invocation scans), and inventory-match, add-handoff, library-futures and
    recommend-2027 (per-invocation reports).

## Boundaries & Constraints

**Never:** a secret, a token or `PYFORGE_ATLAS_CREDENTIALED` in the job; an export published when the build failed; a
board's dimension renamed; the live dashboard's frames capped.

**Residual risk:**
- **A plain `pyforge atlas run` fails on a fresh data root.** The default pipeline set includes `query_plane_cache`,
  whose input `query_plane_estate_source` has no producer until Story 36.3 (blocked); the job names its pipelines.
  DW-atlas-37-2-1.
- **The `vizro` job shares `kedro-viz-publish.yml` with the Kedro-Viz producer** (CAP-63 leaves a separate workflow
  to the operator). Pages mounts an artifact only from a successful run, so a failed or timed-out data build (up to 4
  hours) also keeps that run's `kedro-viz-export` off Pages, which then keeps the previous one; and while the build
  runs, the workflow's one concurrency group holds back the next run, so a pending push run can be replaced by a newer
  one. Splitting the producer into its own workflow is the fix if this bites.
- **A public source that is down** marks its store stale and the run goes on (AD-13); a node that raises fails the
  weekly build, and Pages keeps the previous export until the next run.
- **The vulnerability database may not build on the runner** (it failed on the workstation's `/tmp`); the run goes on
  and the boards' vulnerability columns stay empty until a build succeeds.
- **Every push that touches the boards' paths runs the whole build** (operator ruling "Weekly + on push"): about an
  hour or more of CI per push.

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-63 (amended 2026-10-19), FR-71.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-19.
- Epic 37 / Story 37.2 in `planning-artifacts/epics.md`; closes DW-atlas-37-3-1.

## Spec Change Log

- 2026-10-22, review round 1 (FAIL), fixed:
  - B1: Story 30.1's workflow-shape test pinned the trigger to push and dispatch; it now names the weekly schedule.
  - B2: the PRD's FR-71 still said the identity boards carry no rows on Pages; FR-71 is amended in place and the PRD,
    the spine and epics.md re-stamped (chain currency current again).
  - B3: the charts drew the capped table, so a bar showed the sum of the rows kept, not of the data (adoption-stage
    "unknown" read 5,000 of 34,720); a chart now sums over the whole frame and caps bars, not rows.
  - Should-fix: every table is sorted, so the export is byte-identical on real data (six uncapped boards varied); a
    measure equal on every row is not claimed as the order; the checkout keeps no token; `--clock now` stamps the
    weekly build's time; the shared workflow's cost is a residual risk; the workflow's three commands were run as
    written (Verification).
- 2026-10-21: written with the implementation (branch `atlas-37-2-pages-vizro-data`, stacked on Story 37.3 at
  `5faf32c4ca`).
