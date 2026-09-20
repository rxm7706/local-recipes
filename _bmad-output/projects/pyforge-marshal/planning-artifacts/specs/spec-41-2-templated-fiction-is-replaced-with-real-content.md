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

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `9df7887225` (2026-09-02, "Fix chart reader scope for Story 41.2 review pass 3."); also `61b97a7931` (2026-09-02, "Honor write flag in PlaneGraphStorePlugin (Story 41.2 review)."); also `a7215e2706` (2026-09-02, "Enforce query-plane process boundary (Story 41.2)."). Ledger row `41-2-templated-fiction-is-replaced-with-real-content: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-41-2-query-plane-process-boundary.md`, `src/platform/tests/test_chart_invariants.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
