---
title: 'Relocate atlas data defaults and add pyforge-atlas-bootstrap (Story 21.1, CAP-1)'
type: 'feature'
created: '2026-08-29'
status: 'done'
updated: '2026-08-29'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: dd1454da2afe9be88baf1f2c0ccd518791f74b08
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/docs/dreams/atlas-kedro-catalog-expansion.md'
warnings: []
---

<intent-contract>

## Intent

**Problem:** Kedro atlas still defaults external stores (`vdb_store`, `osv_offline_store`,
`pypi_conda_map`) to `.claude/data/conda-forge-expert/…` and has no single documented bootstrap
entrypoint on `PYFORGE_ATLAS_DATA_ROOT`. Operators proved the combined legacy+Kedro path works,
but a fresh clone cannot run the catalog-owned data plane without manual path wiring.

**Approach:** Phase A only — relocate `conf/base/globals.yml` store paths under
`${paths.data_root}/stores/…`, document one operator env block, and add pixi task
`pyforge-atlas-bootstrap` that runs B5 external-refresh + the documented pipeline chain in
dependency order. **Do not** remove `cf_atlas.db` seeds in this story (Story 21.2).

## Boundaries & Constraints

**Always:**
- Default `paths.data_root` remains `${env_or:PYFORGE_ATLAS_DATA_ROOT,data}` with member
  default `src/shared/packages/pyforge-atlas/data/` documented in operator help.
- Store paths become:
  - `vdb_store: ${paths.data_root}/stores/vdb`
  - `osv_offline_store: ${paths.data_root}/stores/osv`
  - `pypi_conda_map: ${paths.data_root}/stores/pypi_conda_map.json`
- Bootstrap task creates `stores/` subdirs if missing before external-refresh.
- Bootstrap smoke: empty data root + no `CF_ATLAS_DB` → task exits 0 (may skip credentialed
  pipelines with structured notice — same pattern as admin bootstrap 2026-08-29).

**Block If:** None for Phase A.

**Never:**
- Do not edit dataset `seed_*_from_cf_atlas()` call sites (Story 21.2).
- Do not add Tier 1 catalog entries (Story 21.4).
- Do not change inventory scripts or `--live-catalog` (Story 21.3).
- Do not require legacy `bootstrap-data` or `.claude/data/` on the Kedro path.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh data root | Empty `PYFORGE_ATLAS_DATA_ROOT` | Bootstrap creates `stores/` + runs chain; exits 0 or documented skip for credentialed-only steps | Fail loud on missing pixi env, not silent |
| Env override | `PYFORGE_ATLAS_DATA_ROOT=/tmp/atlas-test` | All store paths resolve under override | No hardcoded `.claude/data/` in resolved globals |
| Re-run idempotent | Second bootstrap on same root | External-refresh respects TTL; no destructive wipe | AD-13 last-good preserved |
| Legacy coexistence | `.claude/data/` still on machine | Kedro path does not require it when env block set | Document parallel validity |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/conf/base/globals.yml` — relocate `paths.vdb_store`,
  `osv_offline_store`, `pypi_conda_map` under `${paths.data_root}/stores/…`.
- `pixi.toml` — add `[feature.pyforge-atlas.tasks] pyforge-atlas-bootstrap` (and/or
  `[feature.local-recipes.tasks]` if operator-facing from default env — match existing atlas task
  placement pattern).
- `src/shared/packages/pyforge-atlas/README.md` or bootstrap task `--help` — operator env block:
  `PYFORGE_ATLAS_DATA_ROOT`, optional credentialed vars listed but not required for smoke.
- `tests/catalog/` — extend or add smoke asserting resolved store paths stay under `data_root`
  (no repo escape, mirror P9 gate).

## Tasks & Acceptance

**Execution:**
- [x] Update `globals.yml` store defaults to `${paths.data_root}/stores/…`.
- [x] Add `pyforge-atlas-bootstrap` pixi task invoking B5 external-refresh + pipeline chain
  (document exact pipeline list in task description; match 2026-08-29 admin bootstrap order).
- [x] Ship operator env block documentation (README section or task help text).
- [x] Bootstrap smoke test or catalog test: resolved paths under data root.

**Acceptance Criteria:**
- Given an empty `PYFORGE_ATLAS_DATA_ROOT`, when `pixi run pyforge-atlas-bootstrap` runs, then
  `stores/vdb`, `stores/osv`, and `stores/pypi_conda_map.json` paths resolve under the data root
  and the task completes with exit 0 (or documented skip for attended-only steps).
- Given `globals.yml` after this story, when `kedro-catalog-check` runs, then it passes with
  updated path assertions only — no SQLite seed removal yet.
- Given the operator env block, when read by a human, then `PYFORGE_ATLAS_DATA_ROOT` default
  member path and override behavior are explicit.

## Spec Change Log

- 2026-08-29: Promoted from `stories.yaml` S-21.1; epic renumbered 18→21 to avoid collision
  with Epic 18 (Kedro hooks) in `epics.md`.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass after path assertion updates.
- `pixi run pyforge-atlas-bootstrap` (or documented env) — expected: smoke pass on empty root.

**Dev Notes -- recovery + real verification, 2026-08-29:** the original dispatch's own
supervisor crashed (`compose_dispatch_policy`'s `tomllib.loads(read_bytes())` type bug, fixed
separately in marshal PR #930) before the review/finalize stage ever ran, leaving all four
execution checkboxes above self-marked `[x]` but the story stuck `in-progress` with real,
uncommitted work sitting in the dead dispatch worktree
(`.worktrees/dispatch-pyforge-atlas-21.1`). Rather than discard and redispatch, the operator
independently re-verified the actual diff before landing it: `pixi run --frozen -e pyforge-atlas
kedro-catalog-check` in that worktree — 49/50 passed, the sole failure being
`test_no_inline_io_in_package_code`'s pre-existing `sqlite3` finding, confirmed present
identically on clean `main` (Story 21.2's own scope, explicitly out of bounds here — see
Approach above) and NOT a regression from this story's work. `tools/bootstrap.py` run
standalone against a fresh `/tmp` data root: exit 0, `stores/{vdb,osv}` created correctly, an
existing `credentials.yml` left untouched. The two new catalog tests
(`test_store_paths_derive_from_data_root`, `test_store_paths_resolve_under_data_root`) both
pass, including the `PYFORGE_ATLAS_DATA_ROOT` override case. The verified diff was copied onto
a fresh branch off current `main` and landed there — the dead dispatch worktree/branch were
never reused for the actual merge.
