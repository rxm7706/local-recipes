---
title: '61.5: Quarantine — mint then reject'
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

**Problem:** Inbound rows arrive without a passport.

**Approach:** First 14 days (config) mint into quarantine; after that, no mint. No title-match endpoint exists.

## Boundaries & Constraints

**Always:**
- First configured window (default 14 days) mints into quarantine.
- After the window, no mint.

**Never:**
- Do not add a title-match endpoint.
- Do not treat Epic 8 as this product.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| new inbound, day 3 | no passport | mint into quarantine | n/a |
| new inbound, day 15 | no passport | no mint | refuse |

</intent-contract>

## Binding

Parent Spec capability: `spec-work-passports-dated-extracts CAP-5`.
Surface: quarantine shelf on the existing app..
Ledger key: `61-5-quarantine-mint-then-reject`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-61-5-quarantine-mint-then-reject.md`.
