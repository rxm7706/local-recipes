---
title: '61.2: Work passport and core schema'
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

**Problem:** Jira keys and GitHub numbers can collide across rooms.

**Approach:** Identity is a UUID we mint; keys and numbers are nicknames. vendor_id is on inbound rows; v1 operates one vendor.

## Boundaries & Constraints

**Always:**
- Identity is a minted UUID.
- vendor_id is on inbound rows; v1 is one vendor.

**Never:**
- Do not use Jira keys or GitHub numbers as primary identity.
- Do not treat Epic 8 as this product.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| same Jira key two rooms | two inbound rows | two UUIDs; keys are nicknames | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-work-passports-dated-extracts CAP-2`.
Surface: the existing Postgres join store..
Ledger key: `61-2-work-passport-and-core-schema`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-61-2-work-passport-and-core-schema.md`.
