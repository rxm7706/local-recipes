---
title: '61.3: As-of glass and mailed query'
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

**Problem:** Standup asks "any news from the vendor?"

**Approach:** Standup cites a waybill; empty on-time file fails; late drop leaves yesterday stale; unborn before first waybill. A mailed/export of the same table is a switchable plugin.

## Boundaries & Constraints

**Always:**
- Standup cites a waybill.
- Empty on-time file fails.
- Late drop leaves yesterday stale.

**Never:**
- Do not invent a second standup source of truth.
- Do not treat Epic 8 as this product.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| empty on-time file | waybill present, file empty | fail | fail |
| late drop | file after window | yesterday remains visible | n/a |
| before first waybill | no waybill yet | unborn, not empty-success | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-work-passports-dated-extracts CAP-3`.
Surface: existing app views standup and shipped; optional CSV/markdown export..
Ledger key: `61-3-as-of-glass-and-mailed-query`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-61-3-as-of-glass-and-mailed-query.md`.
