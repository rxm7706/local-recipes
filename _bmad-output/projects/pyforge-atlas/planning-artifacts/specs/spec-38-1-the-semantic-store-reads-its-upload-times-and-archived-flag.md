---
title: "38.1: The semantic store reads its upload times and archived flag"
type: 'feature'
created: '2026-10-24'
status: 'in-progress'
baseline_revision: 'c6fbf20497591bb5bb56296f5b8ab25be94fe4b2'
flag:
  key: pyforge.atlas.board_projections            # existing; minted by Story 37.4, extended to this board's path
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through src/platform/config/flag-overlays.json
  scope: global                                   # v1 is global only
  fallback: 'version-downloads reads core_version_download_history as before, with a null upload_date'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/reference/story-spec-flag-block.md
  - .claude/skills/conda-forge-expert/scripts/adoption_stage.py
  - .claude/skills/conda-forge-expert/scripts/version_downloads.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/semantic_packages/nodes.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** three boards read "unknown", fresh or empty because `semantic_packages` holds no upload time and no
archived flag on a public run.
- It declares `latest_conda_upload`, `latest_upload_age_days`, `releases_30d` and `total_versions` NULL, so the
  adoption-stage board reads `unknown` for every package and find-alternative ranks every candidate as fresh
  (DW-atlas-37-6-2).
- Its `feedstock_archived` joins only `vcs_archived_feedstocks`, which legacy's Phase E.5 GitHub query fills and a public
  run leaves empty (DW-atlas-37-7-2).
- Version-downloads' `upload_date` is null; `core_version_download_history` holds no upload date.

Story 37.6 now streams every version's upload times out of the full repodata, and the cf-graph carries the archived
flag.

**Approach:**
1. **The upload aggregate** (`RepodataUploadsDataset`) keeps each version's newest build too:
   `last_build_number` and `last_upload_unix`, the record with the highest build number, then the latest file time,
   across subdirs. That is the record legacy Phase B picks (CFA:1293-1319). A newest build with no timed file has no
   time, as legacy reads it. The aggregate version moves to 2, so a live load fetches every subdir again; until then a
   v1 copy is served with both columns null (AD-13).
2. **The release cadence** (`project_release_cadence`) adds `latest_conda_upload`: the newest build's file time of the
   version `core_packages_enumerated` names as latest, legacy Phase B's `latest_conda_upload` (CFA:1285-1325).
3. **A node,** `project_graph_archived_feedstocks` (`derived_artifacts`), writes `derived_graph_archived_feedstocks`:
   every feedstock the cf-graph flags archived. Core's Phase J skip-set and Story 37.7's scorer read the same flag.
4. **`compose_semantic_packages`** reads `derived_release_cadence` and `derived_graph_archived_feedstocks`, both produced
   datasets (the pipeline still reads no `_raw` source). It fills:
   - `latest_conda_upload` from the cadence;
   - `latest_upload_age_days` as `(now − latest_conda_upload) // 86400` (legacy `adoption_stage.py:103`; no upload
     time, or 0, is NULL). The packages model's `adoption_stage` derives the same age from `latest_conda_upload` with
     its own `now`, so the stage and `staleness_age_days` on one row read one clock, as legacy computes both;
   - `releases_30d` and `total_versions` from the cadence, legacy `adoption_stage.py`'s `package_version_downloads`
     counts;
   - `feedstock_archived` when the attributed feedstock is in either archived set.

   A package with no row in the cadence keeps NULL in those four columns, never a fabricated value.
5. **Version-downloads:** a node, `project_version_downloads` (`derived_artifacts`), joins
   `core_version_download_history` to each version's upload date (the UTC date of its earliest file, legacy
   `version_downloads.py`'s `upload_unix`) and writes `derived_version_downloads`. Behind
   `pyforge.atlas.board_projections` the board reads it; off, it reads `core_version_download_history` as before.
6. **Provenance:** `metrics.METRIC_PROVENANCE`'s `staleness_age_days` and `adoption_stage` move to `migrated-column`.
7. **Run order:** `semantic_packages` and `derived_artifacts` read each other's outputs, so they run together
   (`pyforge atlas run --pipelines derived_artifacts,semantic_packages`) or as the default pipeline; the board notes and
   the pipeline README say so.

**Deviations from legacy:**
- The upload times come from the main-label full repodata (Story 37.6's ruling and its declared deviations): a version
  only under another label has none.
- `upload_date` is the UTC date; legacy prints the local date of the same instant.
- A timestamp is read as seconds when it is one (Story 37.6's `_seconds`); legacy Phase B always divides by 1000.
- `total_versions` counts the versions the full repodata lists. Legacy counts `package_version_downloads` rows, which
  also hold versions the download store still names after repodata dropped them (Run results: 4.3% of packages read
  fewer here).

Ledger key: `38-1-the-semantic-store-reads-its-upload-times-and-archived-flag`.
Type / Effort / Deps: feature / M / Story 37.6.

### Living CAP citations

- **`spec-pyforge-atlas` CAP-69** (FR-77): the boards no pipeline feeds, here their missing inputs.
- **AD-8:** the classifiers stay `metrics.adoption_stage` and `staleness_age_days`.
- **AD-13:** the upload store's last-good holds across its version bump.
- **AD-14:** a new rider, not parity-gated.
- **AD-17:** each page's stamp comes from the dataset it reads.

## Acceptance Criteria

- **AC1 — Newest build.** The upload aggregate carries each version's earliest file time, and its newest build's
  build number and file time, across subdirs. A copy cached at aggregate version 1 is served with those two null.
- **AC2 — Latest upload.** `latest_conda_upload` is the last file time of the enumerated latest version, NULL when that
  version has no timed file.
- **AC3 — Semantic inputs.** `semantic_packages` fills its four upload columns as legacy derives them, NULL for a
  package the cadence lacks, and `feedstock_archived` from either archived source through attribution.
- **AC4 — Classifiers.** Over the composed store, `adoption_stage` and `staleness_age_days` classify packages with real
  inputs, both against the model's `now`; a package with none still reads `unknown` / NULL.
- **AC5 — Version-downloads.** With the flag on, the board reads `derived_version_downloads` and its stamp names it,
  `upload_date` filled where the version has a timed file; off, it reads as before.
- **AC6 — Pipelines.** `semantic_packages` reads no `_raw` dataset; no core output changes.

## Boundaries & Constraints

**Always:** pure nodes; no network in tests; NULL where a source has no value.

**Never:** change a core output, or `vcs_archived_feedstocks` (it is on the legacy parity surface).

**Residual risk:**
- The boards that read `semantic_packages` change their output: adoption-stage, staleness and detail-cf-atlas.
  Find-alternative's recency and stage do too. The Run results record the counts before and after.
- A package that a live feedstock builds but attribution ties to an archived one now reads archived in every view
  (DW-atlas-37-7-3).

## I/O & Edge-Case Matrix

| Input | Result |
|-------|--------|
| a package in the cadence with a timed latest version | all four columns filled |
| the latest version's newest build untimed, an older build timed | `latest_conda_upload` NULL |
| a late rebuild of an older build number on another subdir | not the newest build |
| a subdir copy cached at aggregate version 1 | served; its newest build null |
| the latest version untimed, older versions timed | `latest_conda_upload` NULL, the counts filled |
| a package not in the cadence | the four columns NULL |
| a feedstock archived only in the cf-graph | `feedstock_archived` 1 |
| a feedstock archived only by the GitHub query | `feedstock_archived` 1 |
| a version with no timed file | `upload_date` null |
| nothing in | typed empty frames |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-69 (FR-77). No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-24 entry.
- Epic: Epic 38 (in progress). Closes DW-atlas-37-6-2 and DW-atlas-37-7-2.
- Ledger key: `38-1-the-semantic-store-reads-its-upload-times-and-archived-flag`.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas pyforge-atlas-test` — expected: pass.
- From the repo root: `src/shared/packages/pyforge-atlas/tests/unit/test_semantic_packages_pipeline.py`,
  `src/shared/packages/pyforge-atlas/tests/unit/pipelines/derived_artifacts/test_release_cadence.py`,
  `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_repodata_uploads.py`,
  `src/shared/packages/pyforge-atlas/tests/unit/pipelines/semantic_packages/test_upload_inputs.py` and
  `src/shared/packages/pyforge-atlas/tests/unit/test_board_projections.py` (both flag states) and
  `src/shared/packages/pyforge-atlas/tests/unit/semantic/` — expected: pass.

## Run results

2026-10-24, after review 1's fixes:
- `pixi run -e pyforge-atlas pyforge-atlas-test`: 3,353 passed, 20 skipped; the second run, 103 passed.
- `pixi run -e pyforge-guild lint-types`: exit 0.
- Mutation check, 43 mutations over the upload store (newest-build ranking within and across subdirs, the
  build-number bound, the v1 serve, the version bump), the cadence, the model clock, the semantic node and pipeline,
  the two lifecycle nodes and the board path: all 43 fail a named test. Before review, 29 mutations left one
  equivalent survivor and three that new tests now cover.

Real data, 2026-10-24: the v2 upload store fetched live into scratch (140 s; 446,663 versions, 436,926 with a newest
build time) over Story 37.2's data root (34,720 enumerated packages) and the cf-graph of Story 37.7's run.
- Cadence: 34,495 packages with `latest_conda_upload`. The graph flags 1,601 feedstocks archived;
  `vcs_archived_feedstocks` is empty on a public run.
- `semantic_packages` before: no upload column set, 0 archived, every package `unknown`.
- After: 34,495 packages with an upload time and an age (median 270 days); 828 archived. Adoption stage: mature 13,985,
  declining 8,602, silent 7,056, stable 4,141, bleeding-edge 936. The 225 packages whose latest version's newest build
  has no timed file read `silent`, legacy's `age or 99999` rule.
- Against legacy `cf_atlas.db` (read-only), 34,669 packages matched:
  - `latest_conda_upload`: of 34,430 set in both, 95.7% exact (95.1% before review, when the newest file stood for the
    newest build). The other 1,493 are newer here, and legacy's own age accounts for them: 1,228 have a newer latest
    version here, and the other 265 were rebuilt after legacy's newest record (2026-10-18).
  - `feedstock_archived`: 825 legacy, 828 here, 99.99% agree; no package legacy marks archived reads live here.
  - Adoption stage: 92.9% agree. The difference is mostly legacy's own age: its `package_version_downloads` ends
    2026-10-09, so the last 15 days' uploads are missing from its 30-day window (mature to stable 1,661; stable to
    bleeding-edge 424).
  - At legacy's own cutoff, with the store truncated to it: `releases_30d` 99.81% exact over 33,809 packages;
    `total_versions` 95.64% exact, 4.34% fewer here (the deviation above).
- Version-downloads: 448,301 rows, 428,065 dated (95.5%), carrying 99.3% of the downloads.

## Spec Change Log

- 2026-10-24: drafted from Story 38.1, DW-atlas-37-6-2 and DW-atlas-37-7-2.
- 2026-10-24: review 1 — the newest build instead of the newest file (legacy Phase B's record), a v1 copy served
  across the version bump, the stage on the model's clock, the run order documented.

## Review Triage Log

**Review 1 (independent, 2026-10-24): FAIL** — 1 must-fix, 5 should-fix, 7 nits; all fixed.
- M1: a v1 cached copy was discarded after the version bump, so a run with live sources off (or a failed refetch)
  emptied the release cadence. Fixed: `_read_cache` serves a v1 copy with the two new columns null.
- S1: nothing pinned the positional wiring of the two new pipeline inputs. Fixed: the kedro-run test asserts the
  cadence values and both archived sources reach their rows.
- S2: `latest_conda_upload` took the version's newest file; legacy takes the newest build's (highest build number, then
  time). Fixed: the store keeps `last_build_number` and ranks by it, within and across subdirs.
- S3: `semantic_packages` and `derived_artifacts` read each other's outputs; the notes said run `semantic_packages`
  alone. Fixed: the notes, `data.py` and the pipeline README name the combined run.
- S4: stale text (the staleness note, `data.py`, the catalog, `models.py`, `alternatives.py`, the pipeline test).
  Fixed.
- S5: the stage read the age frozen at compose time while the staleness age used the model's `now`. Fixed:
  `metrics.adoption_stage(t, now_unix)` derives the age from `latest_conda_upload`, as legacy does.
- Nits: the cf-graph flag reads strings as core's Phase J does (N1); `downloads` is nullable (N2); a version listed
  twice no longer raises (N3); the date test uses a time a local-date reading fails (N4); a flag-off test writes the
  history and reads it with a null date (N5); the epics header and run counts (N6); the seconds reading is a declared
  deviation (N7).
