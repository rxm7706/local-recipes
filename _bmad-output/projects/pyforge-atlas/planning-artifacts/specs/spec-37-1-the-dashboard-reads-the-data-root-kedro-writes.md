---
title: "37.1: The dashboard reads the data root Kedro writes"
type: 'fix'
created: '2026-10-19'
status: 'in-review'
baseline_revision: '85f5895f45'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/data.py
  - src/shared/packages/pyforge-atlas/conf/base/globals.yml
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** `dashboard.data.default_data_root()` walks up to the repo root (`.git` or `_bmad-output`) and returns
`<repo>/data`, which holds only `raw/`. Kedro writes `globals.yml`'s `paths.data_root` (`data`) relative to the Kedro
project, the member `src/shared/packages/pyforge-atlas/`, where `pyforge atlas run` runs (Story 33.1). So a local run
never shows on the boards unless `PYFORGE_ATLAS_DATA_ROOT` is set, and the static export reads the same wrong root.

**Approach:** `default_data_root()` returns `PYFORGE_ATLAS_DATA_ROOT` when set; else the member's `data/` when the
member's `conf/base/catalog.yml` is beside it; else `data/` under the working directory (an installed layout, as Kedro
resolves a relative path). The fix restores the intended behaviour, so it carries no flag (Q1).

Ledger key: `37-1-the-dashboard-reads-the-data-root-kedro-writes`.
Type / Effort / Deps: fix / S / — (the Epic 37 chain).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-69** (FR-77): `default_data_root` resolves the data root Kedro writes.
- **AD-8, AD-17** (the boards read Parquet through BSL; each page's stamp from the dataset it reads).

## Acceptance Criteria

- **AC1 — The member's data.** With no `PYFORGE_ATLAS_DATA_ROOT`, the root is the member's `data/` (beside
  `conf/base/catalog.yml`), the directory `pyforge atlas run` writes.
- **AC2 — The override.** `PYFORGE_ATLAS_DATA_ROOT` still wins.
- **AC3 — An installed layout.** With no member beside the module, the root is `data/` under the working directory.
- **AC4 — Live.** See Verification.
- **AC5 — Gates.** `pyforge-atlas-test`, `dashboard-dryrun`, the coverage gate, `lint-types`; governing Specs
  reconciled and stamped scoped.

## Verification

- Unit, from the repo root: `src/shared/packages/pyforge-atlas/tests/unit/test_dashboard_data.py`.
- **Live, 2026-10-19:** with no `PYFORGE_ATLAS_DATA_ROOT`, `default_data_root()` resolved
  `src/shared/packages/pyforge-atlas/data`; over the operator's member data root (an earlier run's, linked in for the
  check) the packages board read `primary/semantic_packages` with 34,666 rows, where the old root had no such file.

## Boundaries & Constraints

**Never:** a change to `globals.yml`'s `paths.data_root`; a board path changed (Stories 37.3, 37.4).

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-69 (FR-77), a fix.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-19 (the Vizro boards read what the pipelines write).
- Epic 37 / Story 37.1 in `planning-artifacts/epics.md`.

## Spec Change Log

- 2026-10-19: written with the implementation (branch `atlas-37-1-dashboard-data-root`, stacked on the Epic 37 chain
  branch at `85f5895f45`).
