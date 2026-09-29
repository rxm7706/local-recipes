---
title: '23.2: Fold the getting-started and air-gap cluster; stub the binders'
type: 'feature'
created: '2026-09-16'
status: 'done'
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

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `7c7ffb39b0` (2026-09-18, "Merge pull request #1439 from rxm7706/dispatch/pyforge-doctor/23.2"). Ledger row `23-2-fold-the-getting-started-and-air-gap-cluster-stub-the-binders: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/deployment-guide.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/development-guide.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/index.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/project-overview.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/source-tree-analysis.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `docs/MAP.md`, `docs/dreams/pyforge-steward.md`, `docs/explanation/enterprise-deployment.md`, `docs/how-to/air-gapped-mirror-setup.md`, `docs/how-to/pixi-tasks.md` (+7 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready` → `done` (ledger row `23-2-fold-the-getting-started-and-air-gap-cluster-stub-the-binders: done`).
- `## Auto Run Result` reconstructed from git (none survived).
