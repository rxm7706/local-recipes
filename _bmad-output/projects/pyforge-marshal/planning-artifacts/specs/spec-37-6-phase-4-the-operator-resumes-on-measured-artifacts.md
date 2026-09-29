---
title: '37.6: Phase 4 — the operator resumes on measured artifacts'
type: 'docs'
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

**Problem:** As a fleet operator, I want a final baseline re-stamp, a regenerated board and a per-station go/no-go sheet, So that the resume decision reads measurements rather than presumption.

**Approach:** companion `resume-package-2026-08-10.md` — the decision sheet itself

Ledger key: `37-6-phase-4-the-operator-resumes-on-measured-artifacts`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: docs / M / S-37.5.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-31` ← `spec-artifact-chain-reconciliation CAP-7`.

## Acceptance Criteria

- Given the audit is complete When this story lands Then the baseline is stamped, the board matches the ledger, and the story projection is backed by verdict rows And the per-station sheet names specific unmet gates rather than rubber-stamping

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the audit is complete | this story lands | the baseline is stamped, the board matches the ledger, and the story projection  | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 37.6 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `37-6-phase-4-the-operator-resumes-on-measured-artifacts: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
