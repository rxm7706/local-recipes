---
title: '41.1: Dead scaffolding is archived, never deleted'
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

**Problem:** As a fleet operator, I want dead test scaffolding, the hollow `sprint-status.yaml` stub and orphaned single files moved into a mirrored `archive/` path, So that a bulk template commit's debris leaves the live tree without losing the history.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `41-1-dead-scaffolding-is-archived-never-deleted`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: chore / M / —.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-67` ← `spec-bmad-output-hygiene CAP-1`.

## Acceptance Criteria

- Given `dad47c408a` (2026-08-02) stamped generic template content across all 9 projects When this story lands Then `tests/`/`pytest.ini`/`playwright.config.ts` are absent from the 7 station roots carrying zero real tests and present under `archive/` And the dead 0%/empty-array `sprint-status.yaml` stub is archived from all 9 projects while the live `sprint-status-ledger.yaml` stays And two orphaned single files (atlas `RESUME-EPIC-10.md`, herald intake note) are archived And every move was grep-verified beforehand as read by nothing

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `dad47c408a` (2026-08-02) stamped generic template content across all 9 projects | this story lands | `tests/`/`pytest.ini`/`playwright.config.ts` are absent from the 7 station roots | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 41.1 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `c8988f5799` (2026-09-02, "steward: fix Story 41.1 backup chart defects and close its ledger row"). Ledger row `41-1-dead-scaffolding-is-archived-never-deleted: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-41-1-dr-contract-and-postgresql-backup.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `src/platform/deploy/charts/platform/templates/postgres-statefulset.yaml`, `src/platform/tests/test_chart_invariants.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
