---
title: "37.1: The dashboard reads the data root Kedro writes"
type: 'fix'
created: '2026-10-19'
status: 'done'
baseline_revision: '85f5895f45'
review_loop_iteration: 2
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

**Approach:** `default_data_root()` returns the member's `data/` when the member's `conf/base/catalog.yml` is beside
it. `PYFORGE_ATLAS_DATA_ROOT` overrides the `data` name: an absolute value is used as is, and a relative one is anchored
at the member, as Kedro and `admission._data_root` anchor it. A blank override counts as unset, as in `admission`. An
installed layout with no member resolves against the working directory, where Kedro starts looking for a project. The
fix restores the intended behaviour, so it carries no flag (Q1).

Ledger key: `37-1-the-dashboard-reads-the-data-root-kedro-writes`.
Type / Effort / Deps: fix / S / — (the Epic 37 chain).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-69** (FR-77): `default_data_root` resolves the data root Kedro writes.
- **AD-8, AD-17** (the boards read Parquet through BSL; each page's stamp from the dataset it reads).

## Acceptance Criteria

- **AC1 — The member's data.** With no `PYFORGE_ATLAS_DATA_ROOT`, the root is the member's `data/` (beside
  `conf/base/catalog.yml`), the directory `pyforge atlas run` writes.
- **AC2 — The override.** An absolute `PYFORGE_ATLAS_DATA_ROOT` still wins; a relative one resolves under the member,
  the directory Kedro writes it to; a blank one counts as unset.
- **AC3 — An installed layout.** With no member beside the module, the root (or a relative override) resolves under the
  working directory.
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

- 2026-10-21, review round 2 (FAIL, ledger only), fixed: the DW-10-5-7 verified line cited no code, so
  `deferred-work-check` failed (`verified-line-uncited`); it now cites `data.py::default_data_root`. The
  `cli_bridge` env-override comment no longer claims to mirror the data root's override.
- 2026-10-21, review round 1 (PASS), should-fix applied:
  - A relative `PYFORGE_ATLAS_DATA_ROOT` resolved against the working directory, so `dashboard-serve` run from the repo
    root read `<repo>/data-ci` where the bootstrap wrote `<member>/data-ci`. It is now anchored at the member; a blank
    value counts as unset.
  - `views/cli_bridge.py`'s `default_scripts_dir` docstring no longer describes the retired repo-root walk.
  - DW-10-5-7 records the changed premise (both surfaces now default to the member's `data/`); it stays open for the
    hand-maintained path mirror.
  - Tests pin `_MEMBER_ROOT / "data"` from another working directory, the anchored and blank overrides, and an installed
    layout whose fake member sits outside the working directory.
- 2026-10-19: written with the implementation (branch `atlas-37-1-dashboard-data-root`, stacked on the Epic 37 chain
  branch at `85f5895f45`).
