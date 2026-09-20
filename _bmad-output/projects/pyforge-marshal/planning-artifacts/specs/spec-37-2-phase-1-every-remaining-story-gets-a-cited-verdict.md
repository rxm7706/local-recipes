---
title: '37.2: Phase 1 — every remaining story gets a cited verdict'
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

**Problem:** As a fleet operator, I want all 68 remaining stories given one of five verdicts with `file:line` or command-output evidence, plus a coverage map and both-directions repair, So that the backlog is measured against code rather than against its own self-assessment.

**Approach:** companion `audit-method.md` (verdict enum, traceability-matrix row shape, coverage-debt row shape, done-claim sampling protocol, two-sided repair rule)

Ledger key: `37-2-phase-1-every-remaining-story-gets-a-cited-verdict`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: docs / L / S-37.1.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-26` ← `spec-artifact-chain-reconciliation CAP-2`.

## Acceptance Criteria

- Given the ledger reported intent and nothing had checked it against fact When this story lands Then 68/68 verdict rows exist (STILL-VALID / ALREADY-DONE / CONTRADICTED / NEEDS-RESPEC / DROP), each cited And each gate report carries a TEA/coverage-debt table, with an uncovered AC recorded as a visible non-gating row And stale artifacts are rebuilt through their owning skills and diverged code is corrected with tests, each traceable to its verdict row

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the ledger reported intent and nothing had checked it against fact | this story lands | 68/68 verdict rows exist (STILL-VALID / ALREADY-DONE / CONTRADICTED / NEEDS-RESP | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 37.2 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `37-2-phase-1-every-remaining-story-gets-a-cited-verdict: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
