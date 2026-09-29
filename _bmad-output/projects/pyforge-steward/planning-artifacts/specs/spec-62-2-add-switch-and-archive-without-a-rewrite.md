---
title: '62.2: Add, switch, and archive without a rewrite'
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

**Problem:** A new source or a dead source would fork the product.

**Approach:** Add is a new row starting off; archive keeps the id and forbids reuse. on / off / archived is a config flip.

## Boundaries & Constraints

**Always:**
- Add starts off.
- Archive keeps the id and forbids reuse.
- State is a config flip.

**Never:**
- Do not invent weights.
- Do not rewrite the product to add or retire a source.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| add measure | new id | row starts off | n/a |
| archive | existing id | id retained; reuse refused | refuse |

</intent-contract>

## Binding

Parent Spec capability: `spec-build-league-scorecard CAP-2`.
Surface: a config the catalog and later consumers read..
Ledger key: `62-2-add-switch-and-archive-without-a-rewrite`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-62-2-add-switch-and-archive-without-a-rewrite.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

