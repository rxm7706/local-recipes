---
title: '40.5: One dashboard row, and no code reference to the retired name'
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

**Problem:** As a fleet operator, I want the fleet dashboard to carry a single `pyforge-marshal` row with the retired name gone from the code, So that separateness stops leaking onto the board.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `40-5-one-dashboard-row-and-no-code-reference-to-the-retired-name`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: feature / S / S-40.1.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-121` ← `spec-genesis-installer-name-retirement CAP-7`.

## Acceptance Criteria

- Given PR #233 had relabelled the second row rather than removing it When this story lands Then `IMPL_CAMPAIGN` holds one marshal entry (86 stories), `IMPL_CAMPAIGN_LEDGER` drops the key, and `dashboard_drift_check.py` is clean

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| PR #233 had relabelled the second row rather than removing it | this story lands | `IMPL_CAMPAIGN` holds one marshal entry (86 stories), `IMPL_CAMPAIGN_LEDGER` dro | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 40.5 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `40-5-one-dashboard-row-and-no-code-reference-to-the-retired-name: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
