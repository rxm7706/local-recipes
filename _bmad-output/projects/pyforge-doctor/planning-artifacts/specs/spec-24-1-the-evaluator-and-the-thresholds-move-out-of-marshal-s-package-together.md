---
title: '24.1: The evaluator and the thresholds move out of marshal''s package, together'
type: 'feature'
created: '2026-09-16'
status: 'in-progress'
baseline_revision: '2f98ede57d5ebb7df285bbd1383782cf6a7c86af'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** coverage_gate.py and coverage_thresholds.toml ship inside marshal, so a three-line [stations.marshal] edit lowers the floor that reds marshal's own PRs with no Doctor verdict.

**Approach:** Move evaluator and thresholds together out of pyforge.marshal. Re-point every caller. Amend the AD-3/AD-4 contract in the same change. Floors stay byte-identical. No pyforge.<station> module is the evaluator of any station's CI gate.

## Boundaries & Constraints

**Always:**
- Evaluator and thresholds move together, never CAP-2 alone.
- Effective floors are byte-identical before and after.
- docs/governance/coverage-thresholds.toml carries the governance-act $comment.

**Never:**
- Do not leave the evaluator inside any pyforge.<station> package.
- Do not change any station's floor as a side effect.
- Do not invent a pyforge-gates ninth package.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| after move | import pyforge.marshal.coverage_gate | resolves nowhere | n/a |
| CI tasks | eight coverage-gate pixi tasks | call the new home; same floors | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-coverage-gate-independence CAP-1 CAP-2`.
Surface: pyforge/marshal/coverage_gate.py and coverage_thresholds.toml removed; docs/governance/coverage-thresholds.toml; evaluator outside every pyforge.<station> package; scripts/coverage_gates_ci.py; scripts/run_station_coverage_gate.py; .github/workflows/coverage-gates.yml; eight pyforge-<station>-coverage-gate tasks; marshal AD-3/AD-4 import-linter contract and marshal tests for the old module..
Ledger key: `24-1-the-evaluator-and-the-thresholds-move-out-of-marshals-package-together`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-24-1-the-evaluator-and-the-thresholds-move-out-of-marshals-package-together.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

