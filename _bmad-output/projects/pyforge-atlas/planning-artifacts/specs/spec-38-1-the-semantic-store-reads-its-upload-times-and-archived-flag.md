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
review_loop_iteration: 3
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
   version `core_packages_enumerated` names as latest, legacy Phase B's `latest_conda_upload` (CFA:1285-1325). It adds
   `latest_build_known` too: false when that version has no row in the store, or its row came from a v1 copy. The
   semantic store then leaves the package's upload columns NULL, so its stage reads `unknown`; with the counts kept
   and the time NULL, legacy's `age or 99999` would read it `silent`.
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
7. **Run order:** `semantic_packages` and `derived_artifacts` read each other's outputs, and `derived_artifacts` reads
   most fetch pipelines' outputs, so `semantic_packages` joins the `pyforge-atlas-bootstrap` task's one DAG. The Pages
   job's separate `semantic_packages` step goes: built after the bootstrap, it left Story 37.7's scorer with nothing to
   read, and the Vizro build failed on every merge since 37.7 (kedro-viz-publish, 2026-10-24). A DAG test pins that the
   bootstrap produces every input a registered pipeline produces. The board notes and the pipeline README name the
   task.

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
- **AC2 — Latest upload.** `latest_conda_upload` is the file time of the enumerated latest version's newest build (the
  highest build number, then the latest time), NULL when that build has no timed file; `latest_build_known` is false
  when the version has no row, or its row came from a v1 copy, and the semantic store then reads the package unknown.
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
| a subdir copy cached at aggregate version 1 | served; its newest build null; the package's stage `unknown` |
| a copy of another shape with a current manifest | refetched without its ETag |
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
- Epic: Epic 38 (`backlog` until this story lands). Closes DW-atlas-37-6-2 and DW-atlas-37-7-2; opens DW-atlas-38-1-1.
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

2026-10-24, after review 2's fixes:
- `pixi run -e pyforge-atlas pyforge-atlas-test`: 3,362 passed, 20 skipped; the second run, 103 passed (after
  review 3).
- `pixi run -e pyforge-guild lint-types`: exit 0.
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight`: exit 0, with every station suite (the
  diff changes `pixi.toml`): core, scribe, mason, warden, atlas, marshal, herald, doctor and steward.
- Mutation check, 65 mutations in four passes. Every one fails a named test, except one equivalent mutant that a
  later edit removed: a second pass that nulled a v1-mixed version's newest build, which the sort already does.
  - After review 1, 43: the newest-build ranking within and across subdirs, the build-number bound, the v1 serve, the
    version bump, the cadence, the model clock, the semantic node and pipeline, the two lifecycle nodes, the board path.
  - After review 2, 19: the known newest build, the shape-checked ETag, the combine's sort, find-alternative's clock,
    the bootstrap's one DAG and the workflow step.
  - After review 3, 3: the cadence's newest-build ranking for a version listed twice.

Real data, 2026-10-24: the v2 upload store fetched live into scratch (446,669 versions, 436,932 with a newest build
time) over Story 37.2's data root (34,720 enumerated packages) and the cf-graph of Story 37.7's run.
- Cadence: 34,495 packages with `latest_conda_upload`; every package's newest build is known (a fresh store holds no
  v1 copy). The graph flags 1,601 feedstocks archived; `vcs_archived_feedstocks` is empty on a public run.
- `semantic_packages` before: no upload column set, 0 archived, every package `unknown`.
- After: 34,495 packages with an upload time and an age (median 270 days); 828 archived. Adoption stage: mature 13,988,
  declining 8,602, silent 7,055, stable 4,139, bleeding-edge 936. The 225 packages whose latest version's newest build
  has no timed file read `silent`, legacy's `age or 99999` rule.
- Against legacy `cf_atlas.db` (read-only), 34,669 packages matched:
  - `latest_conda_upload`: of 34,430 set in both, 95.7% exact (95.1% before review 1, when the newest file stood for
    the newest build). The other 1,493 are newer here, and legacy's own age accounts for them: 1,228 have a newer
    latest version here, and the other 265 were rebuilt after legacy's newest record (2026-10-18).
  - `feedstock_archived`: 825 legacy, 828 here, 99.99% agree; no package legacy marks archived reads live here.
  - Adoption stage: 92.9% agree. The difference is mostly legacy's own age: its `package_version_downloads` ends
    2026-10-09, so the last 15 days' uploads are missing from its 30-day window (mature to stable 1,664; stable to
    bleeding-edge 425).
  - At legacy's own cutoff, with the store truncated to it: `releases_30d` 99.81% exact over 33,809 packages;
    `total_versions` 95.64% exact, 4.34% fewer here (the deviation above).
- Version-downloads: 448,301 rows, 428,065 dated (95.5%), carrying 99.3% of the downloads.

## Spec Change Log

- 2026-10-24: drafted from Story 38.1, DW-atlas-37-6-2 and DW-atlas-37-7-2.
- 2026-10-24: review 1 — the newest build instead of the newest file (legacy Phase B's record), a v1 copy served
  across the version bump, the stage on the model's clock, the run order documented.
- 2026-10-24: review 2 — a newest build of unknown provenance reads unknown, not silent; `semantic_packages` builds in
  the bootstrap's one DAG (the Pages Vizro build was red since Story 37.7); find-alternative's stage on the board's
  clock; a copy of another shape refetched; a v1-mixed version's newest build null.
- 2026-10-24: review 3 — the package README and the provenance notes follow the bootstrap and the metrics; the
  cadence ranks a version listed twice as `combine_subdirs` does; the memlogs name `pixi.toml` and the regenerated
  docs.

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

**Review 2 (independent, 2026-10-24): FAIL** — review 1's findings verified fixed (S3 and S4 partly); 1 must-fix,
3 should-fix, 6 nits; all fixed.
- B-1: a served v1 copy left `latest_conda_upload` NULL with the counts filled, so a package uploaded five days ago read
  `silent`. Fixed: the cadence's `latest_build_known`; the semantic store leaves all three inputs NULL where it is
  false, and the stage reads `unknown`.
- B-2: the documented run order failed on a fresh data root, and the Pages job built `semantic_packages` after the
  bootstrap. The live check found the Vizro build red on main since Story 37.7 merged (`semantic_packages: Failed while
  loading data`). Fixed: `semantic_packages` joins the bootstrap task; the separate step goes; a DAG test pins the
  bootstrap's self-sufficiency; the notes and README name the task. The same live check found five earlier red runs
  from a cwe.mitre.org outage: a public vulnerability feed's connection failure fails the whole build. That is
  DW-atlas-38-1-1, not this story's surface.
- B-3: AC2 described the newest file. Fixed.
- B-4: find-alternative's stage read the age stored at scoring time. Fixed: the candidates carry `latest_conda_upload`;
  the model and loader take the board's `now`.
- Nits: a v1-mixed version's newest build is null (N-a); `_readable` checks the columns, so a copy of another shape is
  refetched rather than kept by a 304 (N-b); `_build_number`'s docstring (N-c); stale "newest file" wording (N-d);
  `build_packages_model`'s expected columns (N-e); the Binding line (N-f).

**Review 3 (independent, 2026-10-24): PASS** — review 2's findings verified fixed; 0 must-fix, 3 should-fix, 6 nits;
all fixed before landing.
- S1: the package README still said the bootstrap runs eight pipelines and excludes `semantic_packages`. Fixed: nine,
  with the reason; the Pages job runs `catalog_index` after the bootstrap. `test_pipeline_inventory.py` pins nine.
- S2: `tests/unit/semantic/PROVENANCE_NOTES.md` still listed the two metrics' data wiring as deferred. Fixed.
- S3: the scoped stamps of `spec-pyforge-core` and `spec-pyforge-unifying-strategy` passed for `pixi.toml` only because
  older memlog entries name it. Fixed: an event on each names the bootstrap task change, and one on
  `spec-pyforge-doctor` names `docs/how-to/pixi-tasks.md` and `docs/map.yaml`.
- Nits: find-alternative's note names the unknown and untimed cases, and the catalog and `data.py` comments name the
  unknown newest build (N1); the cadence keeps a version-listed-twice's newest build by the same sort as
  `combine_subdirs`, not two maxima (N2); `vizro-static-export --clock` says a local export of data newer than the
  commit needs `now`, or ages read negative (N3); the epic's Surface line (N4); stale run-order text in a test
  docstring and the pipeline README (N5); the station suites run in the full preflight, since `pixi.toml` changed
  (N6).
