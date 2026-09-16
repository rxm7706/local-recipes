---
title: '23.5: The .potx path — template-filled PowerPoints, and every derived file stamped'
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

**Problem:** 21.5 is Marp-only; no derived file records which tree or Design etag it was derived at.

**Approach:** A registry section may declare a .potx. That deck routes through pptx-spec/pptx-fill; others through deck-export. Every derived artifact carries a tree+etag stamp. Host without Chrome reports derive-skipped: no chrome and continues.

## Boundaries & Constraints

**Always:**
- .potx decks are template-filled.
- Marp decks match 21.5.
- Stamps make stale derived files detectable.

**Never:**
- Do not fail the run when Chrome is absent for Marp-PPTX.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| no chrome | Marp-PPTX step | derive-skipped: no chrome; run continues | skip |

</intent-contract>

## Binding

Parent Spec capability: `spec-design-sync-loop CAP-5; spec-deck-family-lockstep CAP-3`.
Surface: deck README registry section; derive stage pptx-spec/pptx-fill vs deck-export; derived-file stamps..
Ledger key: `23-5-the-potx-path-template-filled-powerpoints-and-every-derived-file-stamped`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-5-the-potx-path-template-filled-powerpoints-and-every-derived-file-stamped.md`.
