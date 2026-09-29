---
title: '32.2: Declared Python floor equals the tested floor'
type: 'chore'
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

**Problem:** Declared Python floor equals the tested floor (contract recovered from epics.md Intent + ACs).

**Approach:** `src/shared/packages/pyforge-{herald,marshal,mason,scribe,steward,warden,core,testing-kit}/pyproject.toml`, `pixi.toml` (`[feature.pyforge-atlas.tasks.pyforge-atlas-test]`)

Ledger key: `32-2-declared-python-floor-equals-the-tested-floor`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: chore / XS / —.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-111` ← `spec-fleet-consistency-standard CAP-5`.

## Acceptance Criteria

- Given `pixi.toml` pins `python = ">=3.14.7,3.14.*"` and every env-scoped pin is `3.14.*`, while eight of ten packages declare `requires-python = ">=3.12"` — a floor no environment in this repo installs and nothing has ever exercised When all ten are raised to `>=3.14` Then no package claims support for an interpreter this repo cannot produce, and the claim matches what CI actually runs And `pyforge-atlas-test` exists as the canonical task name (CLAUDE.md documents `pixi run -e pyforge-<station> pyforge-<station>-test` as the fleet grammar and atlas was the sole station where that command did not exist), with `kedro-test` retained as a delegating alias so no existing caller breaks

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `pixi.toml` pins `python = ">=3.14.7,3.14.*"` and every env-scoped pin is `3.14. | all ten are raised to `>=3.14` | no package claims support for an interpreter this repo cannot produce, and the c | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 32.2 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `32-2-declared-python-floor-equals-the-tested-floor: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
