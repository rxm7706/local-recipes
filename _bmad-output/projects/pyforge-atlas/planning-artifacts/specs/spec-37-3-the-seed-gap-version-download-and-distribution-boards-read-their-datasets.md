---
title: "37.3: The seed-gap, version-download and distribution boards read their datasets"
type: 'fix'
created: '2026-10-19'
status: 'in-review'
baseline_revision: '94793a3910'
review_loop_iteration: 2
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/data.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/semantic/models.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/derived_artifacts/nodes.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** six boards read paths no pipeline writes, so they render "backing file not found" whatever the run:
- the four seed-gap boards read `primary/<x>_gap/`; `seed_gaps` writes `derived/seed_gaps_<x>_report/` with other
  column names (`slug`, `confidence`, `category`, `packages`);
- version-downloads reads `primary/version_downloads/`; the download history is `core_version_download_history`,
  with no upload date;
- distribution-breakdown reads `primary/distribution_breakdown/`; `compute_downloads` writes three cuts (platform,
  python version, channel), never one table.

**Approach:**
1. **Seed gaps.** Each board reads its report's path; its model maps the report's columns to the board's names
   (lts: `product_name`←`slug`, `tier`←`confidence`, `matched_conda_name`←`conda_name`; cwe: `tier`←`confidence`,
   `suggested_category`←`category`; spdx: `license_id`←`spdx_id`, else `license`, `package_usage_count`←`packages`;
   license map: `tier`←`confidence`, `package_count`←`packages`). The CWE impact count is deferred (DW-B6-2), so it
   reads null, never a fabricated 0.
2. **Version downloads.** The board reads `core_version_download_history`; `upload_date` is the store's when it has
   one (a fixture, or Story 37.6's), else a typed null.
3. **Distribution.** `compose_distribution_breakdown` (`derived_artifacts`) writes the three cuts as one table behind a
   `facet` (`platform`, `python-version`, `channel`) to `derived_distribution_breakdown`, which the board reads.
   `downloads_90d` carries each cut's `downloads`: the months Anaconda's parquet holds, not a 90-day window (the name
   predates the store). The Python floors are not migrated, so they are null and the bump classifier reads "unknown".
   The table keeps its column types when every cut is empty (a run with no download store), so the board reads it
   empty instead of failing on an Arrow `null` column.
4. A board's dimension and measure names stay; only its path, its expressions and the fixture paths move. The
   version-downloads and distribution notes say what the store holds (no upload date; lifetime totals; facets of
   different populations). The boards were meant to show these datasets, so this is a fix (no flag, Q1).

Ledger key: `37-3-the-seed-gap-version-download-and-distribution-boards-read-their-datasets`.
Type / Effort / Deps: fix / M / Story 37.1 (the data root).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-69** (FR-77). **AD-8** (BSL over DuckDB), **AD-14** (the compose node is a new rider, not
  parity-gated), **AD-17** (each page's stamp from the dataset it now reads).

## Acceptance Criteria

- **AC1 — Paths.** Each of the six boards' constants is the `filepath` of the catalog dataset a node writes.
- **AC2 — Seed gaps.** Each seed-gap loader returns the report's rows under the board's names; the CWE impact is null.
- **AC3 — Version downloads.** The loader returns the history's rows; `upload_date` null when the store has none.
- **AC4 — Distribution.** The compose node joins the three cuts behind a `facet`; an absent or malformed cut adds no
  rows; the board reads its table, including the typed empty table a run with no download store writes.
- **AC5 — Live.** See Verification.
- **AC6 — Gates.** `pyforge-atlas-test`, the dashboard integration suite, `kedro-catalog-check`, the coverage gate,
  `lint-types`; governing Specs reconciled and stamped scoped.

## Verification

- Unit, from the repo root: `src/shared/packages/pyforge-atlas/tests/unit/test_board_wiring.py` and
  `src/shared/packages/pyforge-atlas/tests/unit/semantic/test_board_models.py` (every board model's declared query
  over a two-row store; `semantic.models` is first measured by the unit coverage gate in this story).
- **Live, 2026-10-19,** each loader over a real produced dataset from this effort's scratch roots:
  - distribution-breakdown: the three cuts of a 2026-10-18 root (Story 34.4) composed to 210,170 rows (84,631
    platform, 41,833 python-version, 83,706 channel); the board read all 210,170.
  - version-downloads: `core_version_download_history` of 2026-10-18, 448,301 rows; the board read 448,301.
  - lts-registry-gap 87 of 87, spdx-schema-gap 13 of 13, license-map-gap 28 of 28, cwe-seed-gap 40 of 40.

## Boundaries & Constraints

**Never:** a board's dimension or measure renamed; a value invented for a column the store lacks.

**Residual risk:**
- **`downloads_90d` is not a 90-day figure;** the board's note says what the store holds until a windowed cut exists.
- **Page weight:** over a full data root the static version-downloads page is 37.2 MB and distribution 23.1 MB.
  DW-atlas-37-3-1: Story 37.2 caps them before Pages publishes them.
- **The upload date stays null** on Pages and locally until Story 37.6 brings per-version upload times.

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-69 (FR-77), a fix.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-19.
- Epic 37 / Story 37.3 in `planning-artifacts/epics.md`.

## Spec Change Log

- 2026-10-21, review round 2 (PASS), should-fix applied: the four seed-gap notes still said "renders empty until
  the ... dataset materializes"; each now names its report and what it suggests, the CWE note says the impact count
  stays empty (DW-B6-2), and the SPDX note says which rows stay empty (DW-B6-1).
- 2026-10-21, review round 1 (FAIL), fixed:
  - B1: with every download cut empty the node wrote untyped columns; DuckDB read the Arrow `null` columns as INTEGER
    and the bump classifier's `re_extract` raised AttributeError, so the board crashed on 4 of 5 scratch roots. The
    table is typed (string, `Int64`) even when empty; a test reads the empty composed table through the loader.
  - B2: the unit coverage gate measured `semantic.models` for the first time (78.9% < 80%): 18 builders had no unit
    test. `test_board_models.py` runs each model's declared query over a two-row store.
  - Should-fix: the version-downloads and distribution notes say what the store holds; page weight recorded as
    DW-atlas-37-3-1 for Story 37.2; the chart's mixed facets named in the note.
  - Nits: the CycloneDX catalog comment back above its dataset; `astype("string")`; the DAG test's name; the
    fixture's `upload_date` typed as a date; the epics Surface line names every touched area.
- 2026-10-19: written with the implementation (branch `atlas-37-3-boards-read-their-datasets`, stacked on Story
  37.1 at `94793a3910`).
