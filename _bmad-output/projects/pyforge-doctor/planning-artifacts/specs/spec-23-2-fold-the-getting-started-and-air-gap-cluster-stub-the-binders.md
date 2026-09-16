---
title: '23.2: Fold the getting-started and air-gap cluster; stub the binders'
type: 'feature'
created: '2026-09-16'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Air-gap and getting-started facts live in three or more places and brownfield binders disagree.

**Approach:** Extract unique operational steps into the existing Diátaxis files. Binders become stubs pointing at docs/ plus SYNC-RUNBOOK.md. One tutorial path, one air-gap how-to, one air-gap explanation. Delete docs/reference/ redirect stubs after the pointer sweep. epics.md is not moved.

## Boundaries & Constraints

**Always:**
- One tutorial path, one air-gap how-to, one air-gap explanation.
- The planning tree still exists; epics.md is not moved.

**Never:**
- Do not move epics.md.
- Do not leave the binders as a second operational home.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| binder after fold | marshal development-guide.md | stub pointing at docs/ + SYNC-RUNBOOK.md | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-docs-shelf-alignment CAP-2`.
Surface: docs/tutorials/getting-started.md, docs/how-to/, docs/explanation/enterprise-deployment.md, marshal planning-artifacts/development-guide.md and deployment-guide.md, src/shared/packages/pyforge-marshal/docs/, docs/reference/ redirect stubs..
Ledger key: `23-2-fold-the-getting-started-and-air-gap-cluster-stub-the-binders`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-2-fold-the-getting-started-and-air-gap-cluster-stub-the-binders.md`.
