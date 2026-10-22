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
review_loop_iteration: 0
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
   `PYFORGE_ATLAS_CREDENTIALED` is never set (AD-11, operator ruling "Public-only Pages"); BigQuery stays off. So the
   credentialed and enterprise boards (identity, JFrog) carry no rows on Pages. `query_plane_cache` (its input is
   steward's export, Story 36.3) and `universal_sbom` (entry-scoped) are not run. A failed build fails the job and no
   artifact is uploaded, so Pages keeps the last export it published.
3. **A row cap on static pages** (DW-atlas-37-3-1). Over a full data root two loaders return 448,301 and 210,170
   rows, which wrote 37.2 MB and 23.1 MB pages. `static_export.STATIC_ROW_CAP = 5_000`: a larger frame keeps its
   largest rows by the page's declared chart measure (ties broken by the other columns), else its first rows in an
   order of every column, so one commit's export stays byte-identical. Table and chart draw the same capped frame; the
   caption says "N of M rows, the largest <measure> first; the live dashboard holds every row", and the page header
   says tables show "up to 5,000 rows". The live dashboard is unchanged.
4. **The job's time budget** follows the measured public build (Verification).

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
  `PHASE_P` variable; the bootstrap task's pipelines are the eight fetch pipelines and never `query_plane_cache`.
- **AC4 — The cap.** A frame over the cap keeps its largest rows by the chart measure, ties broken deterministically;
  without a measure, its first rows in column order; a column that does not compare falls back to the measure alone;
  a frame at the cap is untouched; the caption names both counts.
- **AC5 — Live.** See Verification.
- **AC6 — Gates.** `pyforge-atlas-test`, the dashboard integration suite, the coverage gate, `lint-types`,
  `flag-gate-check`, `ci-surface` detectors; governing Specs reconciled and stamped scoped.

## Verification

- Unit, from the repo root: `src/shared/packages/pyforge-atlas/tests/unit/test_vizro_static_boards.py` and
  `src/shared/packages/pyforge-atlas/tests/unit/test_dashboard_static_export.py`.
- **Live, 2026-10-21** (LIVE_PLACEHOLDER)

## Boundaries & Constraints

**Never:** a secret, a token or `PYFORGE_ATLAS_CREDENTIALED` in the job; an export published when the build failed; a
board's dimension renamed; the live dashboard's frames capped.

**Residual risk:**
- **A plain `pyforge atlas run` fails on a fresh data root.** The default pipeline set includes `query_plane_cache`,
  whose input `query_plane_estate_source` has no producer until Story 36.3 (blocked); the job names its pipelines.
  DW-atlas-37-2-1.
- **A public source that is down fails the weekly build;** Pages keeps the previous export until the next run.

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-63 (amended 2026-10-19), FR-71.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-19.
- Epic 37 / Story 37.2 in `planning-artifacts/epics.md`; closes DW-atlas-37-3-1.

## Spec Change Log

- 2026-10-21: written with the implementation (branch `atlas-37-2-pages-vizro-data`, stacked on Story 37.3 at
  `5faf32c4ca`).
