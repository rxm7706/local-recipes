---
title: "37.3: The seed-gap, version-download and distribution boards read their datasets"
type: 'fix'
created: '2026-10-19'
status: 'in-review'
baseline_revision: '94793a3910'
review_loop_iteration: 0
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
4. A board's dimension and measure names stay; only its path, its expressions and the fixture paths move. The boards
   were meant to show these datasets, so this is a fix (no flag, Q1).

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
  rows; the board reads its table.
- **AC5 — Live.** See Verification.
- **AC6 — Gates.** `pyforge-atlas-test`, the dashboard integration suite, `kedro-catalog-check`, the coverage gate,
  `lint-types`; governing Specs reconciled and stamped scoped.

## Verification

- Unit, from the repo root: `src/shared/packages/pyforge-atlas/tests/unit/test_board_wiring.py`.
- **Live, 2026-10-19,** each loader over a real produced dataset from this effort's scratch roots:
  - distribution-breakdown: the three cuts of a 2026-10-18 root (Story 34.4) composed to 210,170 rows (84,631
    platform, 41,833 python-version, 83,706 channel); the board read all 210,170.
  - version-downloads: `core_version_download_history` of 2026-10-18, 448,301 rows; the board read 448,301.
  - lts-registry-gap 87 of 87, spdx-schema-gap 13 of 13, license-map-gap 28 of 28, cwe-seed-gap 40 of 40.

## Boundaries & Constraints

**Never:** a board's dimension or measure renamed; a value invented for a column the store lacks.

**Residual risk:**
- **`downloads_90d` is not a 90-day figure;** the board says what the store holds until a windowed cut exists.
- **The upload date stays null** on Pages and locally until Story 37.6 brings per-version upload times.

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-69 (FR-77), a fix.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-19.
- Epic 37 / Story 37.3 in `planning-artifacts/epics.md`.

## Spec Change Log

- 2026-10-19: written with the implementation (branch `atlas-37-3-boards-read-their-datasets`, stacked on Story
  37.1 at `94793a3910`).
