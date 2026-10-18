---
title: "34.4: The download tables fill from Anaconda's monthly parquet"
type: 'feature'
created: '2026-10-18'
status: 'in-review'
baseline_revision: '80754b2026'
flag:
  key: pyforge.atlas.live_public_sources          # new; minted by this story, shared by Epic 34's feature stories
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: on, dev: on}   # per-env values through src/platform/config/flag-overlays.json
  scope: global                                   # v1 is global only
  fallback: 'S3DownloadStatsDataset serves its month cache and fetches nothing; on a fresh data root that is the empty frame of today'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/live-sources.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/reference/story-spec-flag-block.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/s3_downloads.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/request_datasets.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/core/nodes.py
  - .claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py
  - .claude/skills/conda-forge-expert/scripts/_parquet_cache.py
  - src/platform/config/flags.json
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `core_downloads`, its platform, Python and channel breakdowns and `core_version_download_history` were
0 rows after the unattended refresh of 2026-10-17 (R2).

- `S3DownloadStatsDataset.load()` returned an empty frame by design: "stub-empty until s3-parquet fan-out lands".
- `_RequestParameterizedAPIDataset.fetch_one` loaded the composed base URL whatever key it was given, and returned the
  raw `Response`, so `AnacondaDownloadsDataset.load_many` skipped every payload as not a dict.
- `compute_downloads` summed every channel the source carries, but legacy Phase F reads totals, the latest month and
  the platform and Python cuts from conda-forge only (Wave 2). Only its channel cut spans every channel (Wave 3,
  CFA:3279). The Python filter was `^\d+\.\d+$`, but legacy's is `^(2\.7|3\.([0-9]|1[0-9]|20))$` (CFA:3246).
- `compute_version_download_history` read only the anaconda-api source. Legacy builds per-version downloads from the
  same parquet (Aggregate 2, CFA:3402).
- **The source, measured 2026-10-18.**
  - `anaconda-package-data` publishes `conda/monthly/<YYYY>/<YYYY-MM>.parquet` over public HTTPS: 117 months
    (2017-01 to 2026-09), 603 MB in all, and the month in progress is 404.
  - Columns: `time`, `data_source`, `pkg_name`, `pkg_version`, `pkg_platform`, `pkg_python`, `counts`, dictionary
    encoded. `''` stands for a noarch platform and for an unknown Python.
  - 2026-09: 2,260,832 rows; 1,721,701 of them conda-forge, over 34,518 packages.
  - Per month aggregated: about 363k breakdown rows (every channel) and 438k version rows (conda-forge).

**Approach:**
1. `datasets/s3_downloads.py`: `S3DownloadStatsDataset(url, prefix, view, filepath)`.
   - `url` is the bucket base (`S3_PARQUET_BASE_URL`, existing override). The dataset lists the months with
     ListObjectsV2 over a composed `APIDataset`, then fetches each month's parquet.
   - Each month is aggregated with pyarrow into two cached views under `<filepath>/months/`: `breakdown`
     (`conda_name`, `month`, `platform`, `pyver`, `channel`, `downloads`) and `versions` (`conda_name`, `version`,
     `downloads`, conda-forge only).
   - `pkg_name` is kept exactly; an empty platform reads `noarch`. Legacy (DW-W2-2) makes `pkg_name` PEP 503
     canonical, but a conda name is not a PyPI name. `typing_extensions` and `typing-extensions` are two conda-forge
     packages; legacy merges the first into the second and writes 0 for every eligible name that holds `_` or `.`
     (see AC7).
   - The breakdown view's text columns are read straight into parquet dictionaries and leave as categoricals, with
     `month` ordered. It holds 18.9M rows over every month (294 MB).
   - `manifest.json` records each cached month's ETag, and a month is fetched again only when the listing gives it a
     new one. The two catalog entries share the one cache.
   - A failed listing or month keeps the cache under the AD-13 marker; any other error raises.
   - `staleness()` and `last_good_path` (the manifest) feed `provenance.py`.
   - Behind `pyforge.atlas.live_public_sources`: off, the dataset serves its cache and fetches nothing.
2. `compute_downloads` reads totals, `downloads_30d` and the platform and pyver cuts from conda-forge rows, the channel
   cut from every row, and the pyver filter is legacy's. `compute_version_download_history` takes the s3 versions as a
   second input and prefers them per package; anaconda-api rows fill only the packages s3 lacks, never summed.
   Categorical columns leave the nodes as plain strings.
3. `fetch_one` requests the key it is given (an absolute URL or a path under the base) and decodes a JSON body.
4. Catalog: `core_s3_download_stats_raw` (breakdown) and the new `core_s3_version_downloads_raw` (versions), both on
   `${paths.data_root}/stores/core_s3_downloads`; the core pipeline wires the second into
   `compute_version_download_history`.
5. The flag is registered in the four places `docs/reference/story-spec-flag-block.md` names. It is ON in dev and
   staging and OFF in production: the shipped tree carries no running cleanup clock
   (`test_no_running_cleanup_clock_in_the_shipped_tree_after_story_76_4`), and `PYFORGE_ENVIRONMENT` defaults to
   `dev`.

**Deviation from the epic's Surface line**, recorded here: the dataset moved from `core_sources.py` to its own module;
`pipelines/core/{nodes,pipeline}.py`, `provenance.py` and the parity fixtures and harness for Phases F and I change
too. The epic named only the dataset, `fetch_one`, the catalog and the flag, but its Then clause (five tables within
tolerance of legacy) needs the node fixes.

Ledger key: `34-4-the-download-tables-fill-from-anaconda-s-monthly-parquet`.
Type / Effort / Deps: feature / M / none.

### Living CAP citations

- **`spec-pyforge-atlas` CAP-64** (`live-sources.md` row 2): a feature behind `pyforge.atlas.live_public_sources`.
- **AD-2** (dataset-owned IO over a composed `APIDataset`), **AD-5** (incremental: one month at a time, by ETag),
  **AD-13**, **AD-11** (every test builds the listing and parquet in memory).
- **Origin.** Dream entry 2026-10-18 (atlas fills its own data), R2.

## Acceptance Criteria

- **AC1 — The source.** A listing page parses into months and ETags, with a continuation token; a body that is not a
  listing raises `ValueError` inside the dataset, which marks stale. A month aggregates into both views with
  canonical names, `noarch`, and nameless rows dropped.
- **AC2 — Incremental.** The first load fetches every listed month; a second load, of either view, fetches none; a new
  ETag fetches that month only; a failed month is named in the marker and retried alone on the next run.
- **AC3 — AD-13.** A failed or empty listing keeps the cache under the marker; provenance reports the manifest's
  mtime and the marker; a programming error raises.
- **AC4 — Legacy Phase F semantics.** Totals, `downloads_30d`, platform and pyver from conda-forge; the channel cut
  over every channel; pyver through legacy's filter; versions prefer s3 and fall back to anaconda-api per package.
- **AC5 — `fetch_one`.** It requests the key it is given and decodes JSON; `load_many` yields rows.
- **AC6 — The flag.** Both states tested with `flag_states`: on, the dataset fetches; off, it requests nothing and
  serves its cache. `flag-gate-check` exits 0.
- **AC7 — Live:** see Verification below.
- **AC8 — Gates.** `pyforge-atlas-test`, `kedro-test`, `kedro-catalog-check`, the coverage gate, `lint-types`, the
  `pyforge-core` and `platform` flag tests, `flag-gate-check` and `flag-inventory` exit 0; governing Specs reconciled
  and stamped scoped.

## Verification

- Unit: `tests/unit/datasets/test_s3_downloads.py`, `tests/unit/datasets/test_request_datasets.py`,
  `tests/unit/pipelines/core/test_nodes.py`, `tests/unit/parity` (Phases F and I fixtures).
- Live (AC7), recorded 2026-10-18. Cold run: fresh scratch data root, flag on (dev), `--pipelines core --nodes
  compute_downloads,compute_version_download_history`, exit 0, 2:24, peak RSS 3.57 GB. It fetched 117 months, giving a
  241 MB cache of 234 files, with no marker. A warm re-run made the listing request only: 12 s, peak RSS 2.65 GB.
  - **Before:** 0 rows in all five tables.
  - **`core_downloads`:** 35,445 packages, every one `s3-parquet`.
  - **Against legacy's 31,072 nonzero `s3-parquet` rows** (`cf_atlas.db`, read-only): 30,907 equal exactly (99.47%) and
    none is missing. Of the 165 that differ, 147 are legacy's separator merge. The other 18 are rows legacy last
    refreshed on 2026-08-29 (its seven-day TTL), before 2026-08 and 2026-09 entered its sweep; their month data is
    byte-for-byte the same in both caches.
  - **Legacy's 2,815 zero-total rows:**
    - 2,653 hold `_` or `.`, and atlas has their downloads (`python_abi` 345,141,605; `_openmp_mutex` 301,143,078).
    - 161 have no parquet rows; atlas writes no row for them.
    - 1 other.
  - **The breakdowns,** legacy rows equal exactly:
    - platform 76,247 of 76,625 (99.51%); atlas 85,051 rows
    - pyver 37,463 of 37,764 (99.20%); atlas 41,853
    - channel 54,158 of 54,413 (99.53%); atlas 84,221 over 57,491 packages
    - `core_version_download_history` 415,033 of legacy's 417,022 `s3-parquet` version rows (99.52%); atlas 448,759
    - The residue has the same two causes.

## Boundaries & Constraints

**Never:** a credential on the bucket; an HTTP client import in the package; a test that touches the network; the two
download sources summed.

**Residual risk:**
- Legacy's `downloads_90d` and `downloads_trend_90d` (Wave 2) have no atlas column; `core_downloads`'s schema is
  unchanged.
- `core_downloads` covers every package the parquet names, including packages no longer on conda-forge; legacy
  restricts it to its `packages` rows.
- **Legacy's DW-W2-2 merge** stays in the CFE copy until the legacy-fix story after Epic 36 (operator ruling
  "Kedro first, legacy after"). That story's scope now includes it.
- **Memory:** a cold run peaks at 3.57 GB, a warm one at 2.65 GB. The breakdown view is 18.9M rows, because the node
  contract keeps `month` per row.

## I/O & Edge-Case Matrix

| Situation | Before | After |
|---|---|---|
| Live run, flag on | 0 rows in the five tables | 117 months cached; five tables filled |
| Second run, nothing republished | — | listing only; no month fetched |
| A month republished | — | that month fetched again |
| Bucket unreachable | — | cache served, marker "listing failed" |
| One month unreadable | — | the others cached; marker names it; retried next run |
| Flag off | empty frame | cache served; nothing requested |
| Another channel's downloads | summed into totals | channel breakdown only |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-64 (FR-72), a feature.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-18 (atlas fills its own data), R2.
- Epic 34 / Story 34.4 in `planning-artifacts/epics.md`.
- Flag: `pyforge.atlas.live_public_sources` (`feature-flag-governance:CAP-1`).

## Spec Change Log

- 2026-10-18: written with the implementation (branch `atlas-34-4-downloads-monthly-parquet`, cut from 34.3's
  branch, which touches the same files).
