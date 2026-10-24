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
review_loop_iteration: 0
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
1. **The upload aggregate** (`RepodataUploadsDataset`) keeps each version's last file time too,
   `last_upload_unix` (its aggregate version moves to 2, so a cached v1 copy is fetched again).
2. **The release cadence** (`project_release_cadence`) adds `latest_conda_upload`: the last file time of the version
   `core_packages_enumerated` names as latest. That is legacy Phase B's `latest_conda_upload`, the newest build of the
   latest current-repodata version (CFA:1285-1325).
3. **A node,** `project_graph_archived_feedstocks` (`derived_artifacts`), writes `derived_graph_archived_feedstocks`:
   every feedstock the cf-graph flags archived. Core's Phase J skip-set and Story 37.7's scorer read the same flag.
4. **`compose_semantic_packages`** reads `derived_release_cadence` and `derived_graph_archived_feedstocks`, both produced
   datasets (the pipeline still reads no `_raw` source). It fills:
   - `latest_conda_upload` from the cadence;
   - `latest_upload_age_days` as `(now − latest_conda_upload) // 86400` (legacy `adoption_stage.py:103`; no upload
     time, or 0, is NULL);
   - `releases_30d` and `total_versions` from the cadence, legacy `adoption_stage.py`'s `package_version_downloads`
     counts;
   - `feedstock_archived` when the attributed feedstock is in either archived set.

   A package with no row in the cadence keeps NULL in those four columns, never a fabricated value.
5. **Version-downloads:** a node, `project_version_downloads` (`derived_artifacts`), joins
   `core_version_download_history` to each version's upload date (the UTC date of its earliest file, legacy
   `version_downloads.py`'s `upload_unix`) and writes `derived_version_downloads`. Behind
   `pyforge.atlas.board_projections` the board reads it; off, it reads `core_version_download_history` as before.
6. **Provenance:** `metrics.METRIC_PROVENANCE`'s `staleness_age_days` and `adoption_stage` move to `migrated-column`.

**Deviations from legacy:**
- The upload times come from the main-label full repodata (Story 37.6's ruling and its declared deviations): a version
  only under another label has none.
- `upload_date` is the UTC date; legacy prints the local date of the same instant.
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

- **AC1 — Last file time.** The upload aggregate carries each version's earliest and last file times across subdirs.
- **AC2 — Latest upload.** `latest_conda_upload` is the last file time of the enumerated latest version, NULL when that
  version has no timed file.
- **AC3 — Semantic inputs.** `semantic_packages` fills its four upload columns as legacy derives them, NULL for a
  package the cadence lacks, and `feedstock_archived` from either archived source through attribution.
- **AC4 — Classifiers.** Over the composed store, `adoption_stage` and `staleness_age_days` classify packages with real
  inputs; a package with none still reads `unknown` / NULL.
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
  `src/shared/packages/pyforge-atlas/tests/unit/test_board_projections.py` (both flag states) — expected: pass.

## Run results

2026-10-24, on the branch before review:
- `pixi run -e pyforge-atlas pyforge-atlas-test`: 3,344 passed, 20 skipped; the second run, 103 passed.
- `pixi run -e pyforge-guild lint-types`: exit 0.
- Mutation check: 29 mutations over the upload store, the cadence, the semantic node and pipeline, the two lifecycle
  nodes and the board path. 28 fail a named test. One survives and is equivalent: guarding the last-file update on an
  empty entry instead of on a timed file writes NULL over NULL. The first pass left three more; the tests now cover
  them (an age floored, never rounded; an empty or flagless graph; a history with no downloads column).

Real data, 2026-10-24: the v2 upload store fetched live into scratch (27 s; 446,654 versions, 436,923 with a last file
time) over Story 37.2's data root (34,720 enumerated packages) and the cf-graph of Story 37.7's run.
- Cadence: 34,496 packages with `latest_conda_upload`. The graph flags 1,601 feedstocks archived;
  `vcs_archived_feedstocks` is empty on a public run.
- `semantic_packages` before: no upload column set, 0 archived, every package `unknown`.
- After: 34,496 packages with an upload time and an age (median 269 days); 828 archived. Adoption stage: mature 13,984,
  declining 8,600, silent 7,067, stable 4,104, bleeding-edge 965. The 224 packages whose latest version has no timed
  file read `silent`, legacy's `age or 99999` rule.
- Against legacy `cf_atlas.db` (read-only), 34,669 packages matched:
  - `latest_conda_upload`: of 34,430 set in both, 95.1% exact and 95.7% within a day; the other 4.9% are newer here.
  - `feedstock_archived`: 825 legacy, 828 here, 99.99% agree; no package legacy marks archived reads live here.
  - Adoption stage: 92.8% agree. The difference is mostly legacy's own age: its `package_version_downloads` ends
    2026-10-09, so the last 15 days' uploads are missing from its 30-day window (mature to stable 1,643; stable to
    bleeding-edge 450).
  - At legacy's own cutoff, with the store truncated to it: `releases_30d` 99.81% exact over 33,809 packages;
    `total_versions` 95.64% exact, 4.34% fewer here (the deviation above).
- Version-downloads: 448,301 rows, 428,065 dated (95.5%), carrying 99.3% of the downloads.

## Spec Change Log

- 2026-10-24: drafted from Story 38.1, DW-atlas-37-6-2 and DW-atlas-37-7-2.

## Review Triage Log

Pending.
