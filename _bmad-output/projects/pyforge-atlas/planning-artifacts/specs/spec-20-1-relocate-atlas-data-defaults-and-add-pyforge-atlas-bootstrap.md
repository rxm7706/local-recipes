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
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `e8162cae74` (2026-09-13, "docs(herald): seed deck-family-currency — Dream, Spec CAP-1..5, Epic 20, Story 20.1"); also `ec4dc5dfd4` (2026-09-06, "feat(pyforge-doctor): suite drift derives each member's probe class (Story 20.1)"). Ledger row `20-1-relocate-atlas-data-defaults-and-add-pyforge-atlas-bootstrap: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-herald/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-20-1-the-standard-has-one-home-and-the-deck-spec-points-to-it.md`, `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-family-currency/.memlog.md`, `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-family-currency/SPEC.md`, `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-family-currency/deck-inventory.md`, `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-family-currency/facts-ledger.md`, `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-family-currency/infographic-standard.md`, `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md`, `_bmad-output/projects/pyforge-herald/planning-artifacts/sprint-status-ledger.yaml`, `docs/dreams/README.md`, `docs/dreams/deck-family-currency.md`, `docs/specs/presentation-deck.md` (+2 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
