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

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

## Note — 2026-09-19

Story 65.1 (PR #1507) shipped a `WorkPassport` Django model (`dashboard/models.py`, migration
`0002_workpassport`: minted UUID `passport_id`; `jira_key` / `github_item_id` as aliases), its
admin and a flag-gated `passport_sync` — CAP-140's identity rule realized in part, outside this
story's declared surface (no `vendor_id`; not the existing Postgres join store; 61.1's corridor not
landed). This story builds on that model; it does not mint a second one.
