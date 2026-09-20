---
title: '37.5: Phase 3 — decomposition only behind a landed gate report'
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

**Problem:** As a fleet operator, I want each queued decomposition chain to start only after its own station's audit gate report has landed, So that new stories are never built on an unaudited premise.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `37-5-phase-3-decomposition-only-behind-a-landed-gate-report`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: docs / M / S-37.3.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-30` ← `spec-artifact-chain-reconciliation CAP-6`.

## Acceptance Criteria

- Given four chains were queued (atlas → herald → doctor → steward) When this story lands Then every decomposition PR cites the landed gate report it builds on

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| four chains were queued (atlas → herald → doctor → steward) | this story lands | every decomposition PR cites the landed gate report it builds on | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 37.5 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `37-5-phase-3-decomposition-only-behind-a-landed-gate-report: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
