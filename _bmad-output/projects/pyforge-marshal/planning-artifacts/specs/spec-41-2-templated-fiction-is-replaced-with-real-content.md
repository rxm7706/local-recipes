---
title: '41.2: Templated fiction is replaced with real content'
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

**Problem:** As a fleet operator, I want the fabricated `test-architecture.md`, the `[role]`/`[responsibilities]` README placeholders and the drifted `project-context.md` files regenerated against live ground truth, So that no planning document asserts something its own project contradicts.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `41-2-templated-fiction-is-replaced-with-real-content`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: docs / M / S-41.1.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-69` ← `spec-bmad-output-hygiene CAP-3`.

## Acceptance Criteria

- Given the bulk commit left fabricated prose in place When this story lands Then Genesis's `test-architecture.md` makes no claim its own PRD/architecture contradicts And no literal `[role]`/`[responsibilities]` token survives, and no README describes archived scaffolding as live And mason's and herald's `project-context.md` counts match their ledgers

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the bulk commit left fabricated prose in place | this story lands | Genesis's `test-architecture.md` makes no claim its own PRD/architecture contrad | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 41.2 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.
