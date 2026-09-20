---
title: '13.7: The producer reconciles the surface it drifts'
type: 'feature'
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

**Problem:** As the operator, I want bmad-loop to name the governed paths it changed in the owning Spec's memlog, So that the spec-surface gate stops being a tax paid by whoever lands the work.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `13-7-the-producer-reconciles-the-surface-it-drifts`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: feature / M / S-13.2.

### Living CAP citations

- Cited from epics.md: FR-174

## Acceptance Criteria

- Given a loop-produced story that changed governed files When the story completes Then the owning Spec's `.memlog.md` names each changed governed path, written as part of the story rather than at landing And `spec-surface-check` is green on the station branch with no human editing a memlog And a story that changed no governed file writes nothing — silence is not a finding, and an entry per story would be noise And the loop is never handed `--write-baseline`: a producer that can stamp its own baseline is precisely the laundering S-13.2 exists to end And matching stays per-file naming under S-13.2's literal rule — no blanket claim ---

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| a loop-produced story that changed governed files | the story completes | the owning Spec's `.memlog.md` names each changed governed path, written as part | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 13.7 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `d0e11c5801` (2026-08-09, "marshal 13.7: the producer reconciles the surface it drifts"). Ledger row `13-7-the-producer-reconciles-the-surface-it-drifts: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml`, `docs/dashboard/data.js`, `scripts/.spec-surface-baseline.json`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_harness_policy_render.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
