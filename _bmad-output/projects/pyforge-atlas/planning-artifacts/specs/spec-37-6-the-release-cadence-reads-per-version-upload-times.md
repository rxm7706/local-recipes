---
title: "37.6: The release-cadence reads per-version upload times"
type: 'feature'
created: '2026-10-23'
status: 'in-progress'
baseline_revision: '20621275f265b348e7748b81fe6d67dec3968125'
flag:
  key: pyforge.atlas.board_projections            # existing; minted by Story 37.4, extended to this board
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through src/platform/config/flag-overlays.json
  scope: global                                   # v1 is global only
  fallback: 'the release-cadence reads primary/release_cadence as before, which nothing writes, and renders empty'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/reference/story-spec-flag-block.md
  - .claude/skills/conda-forge-expert/scripts/release_cadence.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/s3_downloads.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the release-cadence board reads `primary/release_cadence/`, and no node writes it (DW-atlas-37-6-1).
Legacy `release_cadence.py` counts each package's releases in 30, 90 and 365 days from
`package_version_downloads.upload_unix`, "the earliest upload time across a version's files". Atlas never fetches a
per-version upload time: `AnacondaDownloadsDataset` is empty, and the S3 monthly parquet carries none.

**Operator ruling (2026-10-23):** the source is the full `repodata.json.zst` of each conda-forge subdir, not the
anaconda.org files fan-out.

**Approach:**
1. **A public dataset,** `RepodataUploadsDataset` (new, `datasets/repodata_uploads.py`), as `core_repodata_uploads_raw`
   over `CONDA_FORGE_BASE_URL` and the seven subdirs `CondaRepodataDataset` reads. It follows Story 34.4's
   `S3DownloadStatsDataset`:
   - it fetches only behind `pyforge.atlas.live_public_sources`; off, it serves its cache;
   - each subdir is fetched with its cached ETag (`If-None-Match`), so an unchanged subdir costs a 304;
   - each subdir's body is streamed: stdlib `compression.zstd`, then an incremental JSON decode of each `packages`
     and `packages.conda` record. No whole repodata document is ever held; linux-64, 59 MB compressed with 799,045
     files, parses in about 3 s within about 150 MB;
   - each subdir is cached as one Parquet of (`conda_name`, `version`, `upload_unix`, `file_count`) under
     `stores/core_repodata_uploads`, with a manifest of ETags. A failed fetch or parse keeps that subdir's cached
     copy under the AD-13 `.staleness.json` marker, and the load never raises;
   - a load combines the subdirs: `upload_unix` is the earliest file timestamp of a version across every subdir, in
     epoch seconds (a millisecond timestamp, conda's own rule, is divided by 1,000); `file_count` is the number of
     its files.
2. **A node,** `project_release_cadence` (new module `derived_artifacts/release_cadence.py`, a port of legacy's query).
   For each enumerated package it gives:
   - `total_versions`;
   - `releases_30d`, `releases_90d` and `releases_365d`: the versions uploaded on or after now minus N days;
   - `first_upload`, `last_upload` and `latest_version`.

   It writes `derived_release_cadence`.
3. **The board,** behind `pyforge.atlas.board_projections` as Stories 37.4–37.10's boards are:
   - on, release-cadence reads `derived_release_cadence`, and `trend_label` is the existing
     `metrics.release_trend_label`, legacy's classifier;
   - off, it reads `primary/release_cadence/` as before.

**Deviations from legacy:**
- The upload time is the earliest file timestamp in the channel's repodata. Legacy reads anaconda.org's per-file
  `upload_time`. A file removed from the channel no longer counts, and a version with no timestamped file has no
  upload time: it counts in `total_versions`, but in no window.
- The scope is the enumerated packages (`core_packages_enumerated`), as legacy's `package_version_downloads` holds
  only packages its `packages` table lists. Repodata names that the current repodata does not list are dropped.
- `latest_version` among equal upload times is the larger version string. Legacy's order among ties is SQLite's.
- The board aggregates every package. Legacy's `--package`, `--maintainer` and `--limit` filters are query options,
  not data.

Ledger key: `37-6-the-release-cadence-reads-per-version-upload-times`.
Type / Effort / Deps: feature / M / Story 37.1 (the data root).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-69** (FR-77, the boards no pipeline feeds).
- **AD-2/AD-13:** the dataset owns the fetch and the parse, composes `APIDataset`, and keeps last-good under the
  staleness marker.
- **AD-8:** BSL over DuckDB; the trend is the registered classifier, not app code.
- **AD-11:** the fetch sits behind `pyforge.atlas.live_public_sources`, which the tests pin off.
- **AD-14:** a new rider, not parity-gated.
- **AD-17:** the page's stamp comes from the dataset it reads.

## Acceptance Criteria

- **AC1 — Parse.** Every record in `packages` and `packages.conda` of a zstd-compressed repodata is read, whatever its
  whitespace and wherever a chunk boundary falls, including inside a multi-byte character or a number. A record with
  no name or version is skipped. A malformed body is a failure of that subdir, never a crash.
- **AC2 — Upload time.** A version's `upload_unix` is the earliest timestamp of its files across subdirs, in seconds;
  a millisecond timestamp is divided by 1,000; an untimestamped file counts in `file_count` and nowhere else.
- **AC3 — Cache.** A subdir is fetched with its cached ETag and reused on a 304. A failed fetch or parse keeps its
  cached copy and writes the staleness marker; a full success removes it. With the flag off nothing is fetched and
  the cache is served. Without `filepath` the dataset is the empty frame.
- **AC4 — Cadence.** For each enumerated package: `total_versions` counts its versions, and each window counts the
  versions uploaded on or after now minus 30, 90 or 365 days; `latest_version` is the version last uploaded.
- **AC5 — Board.** With the flag on, the board reads `derived_release_cadence` and its AD-17 stamp names that file;
  `trend_label` follows legacy's classifier. With the flag off, it reads `primary/release_cadence/` as before.

## Boundaries & Constraints

**Always:** no test reaches the network; the dataset never raises out of a load; the node is pure over its frames.

**Never:** change `core_repodata_raw`, `CondaRepodataDataset`, or any core output.

**Residual risk:**
- `semantic_packages`' upload-time inputs (`latest_conda_upload`, `latest_upload_age_days`, `releases_30d`,
  `total_versions`) stay NULL. Wiring them from this dataset would light up the adoption-stage board and
  find-alternative's recency and stage, but it changes those boards' outputs, so it is DW-atlas-37-6-2's.
- A run with the flag off, or a first run whose fetches fail, has no cache and gives an empty board.

## I/O & Edge-Case Matrix

| Input | Result |
|-------|--------|
| a version only on noarch, another on three subdirs | each once, earliest timestamp, every file counted |
| a timestamp in milliseconds | seconds |
| a record with no timestamp | counted in `file_count`, no `upload_unix` |
| a record with no name or version | skipped |
| a subdir that answers 304 | its cached copy, no parse |
| a subdir whose fetch fails or body is corrupt | its cached copy, staleness marker |
| a version with no upload time | in `total_versions`, in no window |
| a repodata name not enumerated | not on the board |
| nothing in | an empty frame with the output columns |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-69 (FR-77). No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-19 entry (the Vizro boards read their data).
- Epic: Epic 37 (in progress). Closes DW-atlas-37-6-1; opens DW-atlas-37-6-2.
- Ledger key: `37-6-the-release-cadence-reads-per-version-upload-times`.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas pyforge-atlas-test` — expected: pass.
- From the repo root: `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_repodata_uploads.py` (the parse,
  the cache, the marker), `src/shared/packages/pyforge-atlas/tests/unit/pipelines/derived_artifacts/test_release_cadence.py`
  (the windows) and `src/shared/packages/pyforge-atlas/tests/unit/test_board_projections.py` (both flag states) —
  expected: pass.

## Run results

Run 2026-10-23 in the landing worktree on `20621275f2`, every verdict read from its exit code.

- **AC1–AC5, tests:** `test_repodata_uploads.py` (27), `test_release_cadence.py` (5) and
  `test_board_projections.py` pass; `pyforge-atlas-test` gives 3,302 passed and 20 skipped, then 103 passed (exit 0).
- **Pins moved:** `derived_artifacts` has 14 nodes (13), the combined DAG 73 (72), the catalog 145 entries (143); the
  node has a timeout (900 s).
- **Mutations**, each restored, each failing a named test (25 of 25):
  - parse: milliseconds not converted; a bool or zero timestamp accepted; the latest file kept; files not counted;
    nameless records kept; `packages.conda` ignored; a number cut at the buffer end not re-read; UTF-8 decoded per
    chunk; the value cap removed;
  - cache: the subdirs combined to the latest upload; their files not summed; the cached ETag not sent; a 304
    parsed; the marker never removed; the flag ignored; `If-None-Match` not set; the manifest version ignored;
  - cadence: a window exclusive at its cutoff; untimed versions not counted; non-enumerated packages kept; a tie
    going to the smaller version; an untimed version as the latest;
  - board and provenance: the board path not switched; the dataset not marked for provenance.
- **Real data:** a live load of the seven subdirs into a scratch store, with Story 37.2's live data root for
  `core_packages_enumerated`:
  - the first load fetches and streams them in 24.0 s, at a peak RSS of 515 MB for the whole process. That gives
    446,584 versions (436,853 timed) over 3,391,308 files; the cache is 10.4 MB of Parquet over seven subdirs;
  - a second load is 0.8 s: every subdir answers 304, and the frame is identical;
  - the node runs in 0.3 s over all 34,720 enumerated packages. 5,192 released in the last 30 days, 9,011 in 90 and
    16,273 in 365; a package has a median of 4 versions (numpy 113, python 179);
  - **against legacy:** the primary checkout's `cf_atlas.db` holds 442,267 per-version `upload_unix` values from
    anaconda.org's files API. 425,904 of them match a timed version here, with a median difference of 55 s; 98.7%
    are within an hour, and 99.2% within a day.


## Spec Change Log

- 2026-10-23: drafted from Story 37.6, DW-atlas-37-6-1 and the operator's ruling on the source.

## Review Triage Log

Pending.
