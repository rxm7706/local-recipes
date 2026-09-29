---
title: '37.1: Phase 0 — mechanical debt to zero before any semantic audit'
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

**Problem:** As a fleet operator, I want every detector green and every `[drift-presumed]` warn closed before the audit reads a single story premise, So that semantic findings are never confused with mechanical noise.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `37-1-phase-0-mechanical-debt-to-zero-before-any-semantic-audit`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: chore / M / —.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-25` ← `spec-artifact-chain-reconciliation CAP-1`.

## Acceptance Criteria

- Given 51 `[drift-presumed]` warns stood fleet-wide (atlas 24 / mason 1 / marshal 26) When this story lands Then six detectors plus the meta-suite are green and zero `[drift-presumed]` remains And dangling commits are dispositioned rather than ignored

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 51 `[drift-presumed]` warns stood fleet-wide (atlas 24 / mason 1 / marshal 26) | this story lands | six detectors plus the meta-suite are green and zero `[drift-presumed]` remains | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 37.1 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `37-1-phase-0-mechanical-debt-to-zero-before-any-semantic-audit: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
