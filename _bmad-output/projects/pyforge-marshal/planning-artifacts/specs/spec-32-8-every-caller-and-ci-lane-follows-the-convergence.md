---
title: '32.8: Every caller and CI lane follows the convergence'
type: 'fix'
created: '2026-09-18'
status: 'done'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Every caller and CI lane follows the convergence (contract recovered from epics.md Intent + ACs).

**Approach:** `pixi.toml` (ten atlas test-path tasks), `.github/workflows/{pyforge-core,pyforge-steward-five-tier,pyforge-steward-fresh-clone}.yml` (python-version), `.github/workflows/coverage-gates.yml` (setup-uv), `src/shared/packages/pyforge-atlas/tests/{unit,integration}/**`, the eight regenerated `test-architecture.md`

Ledger key: `32-8-every-caller-and-ci-lane-follows-the-convergence`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: fix / S / S-32.5, S-32.7.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-108` ← `spec-fleet-consistency-standard CAP-2`.
- Cited: `spec-pyforge-testing-charter CAP-4`.

## Acceptance Criteria

- Given PR #1082's first full CI run went red in five lanes — three because CAP-5's `requires-python` raise made pip refuse on lanes still pinned to Python 3.12 (`Package 'pyforge-core' requires a different Python: 3.12.14 not in '>=3.14'`), one because the coverage lane collects `tests/meta/` and herald's SKF validator shells out to `uv`, and one because moving atlas's tests under `unit/` pulled three fail-loud gates into a lane that provisions none of their prerequisites When the three lanes move to 3.14 (matching `detectors.yml`, which already ran it), the coverage lane gains `astral-sh/setup-uv`, and atlas's `dashboard/`, `publish/` and `wasm/` move to `tests/integration/` Then every lane is green and no gate silently skips: the three fail-loud gates still run — in `pyforge-atlas-test`, which provisions Chromium, the DuckDB `httpfs` extension and the WASM build for exactly this reason And the ten pixi tasks naming pre-move atlas paths are repointed and the eight `test-architecture.md` regenerated from the live inventory — a green suite proved the FILES worked and said nothing about the TASKS that name them, which is why the manifest must be grepped after a tree move And CAP-5's own rationale is corrected on the record: "no environment has ever exercised 3.12" was derived from `pixi.toml` alone and never checked against `.github/workflows/` — three lanes had been exercising it

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| PR #1082's first full CI run went red in five lanes — three because CAP-5's `req | the three lanes move to 3.14 (matching `detectors.yml`, whic | every lane is green and no gate silently skips: the three fail-loud gates still  | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 32.8 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `32-8-every-caller-and-ci-lane-follows-the-convergence: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
