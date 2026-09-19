---
title: '61.1: Corridor transports — upload default'
type: 'feature'
created: '2026-09-16'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Vendor and estate lists have no idempotent drop path.

**Approach:** Inbound and outbound files load by batch sha + waybill. Default transport is app upload; email and share-folder are plugins. Do not treat Epic 8 as this product. Do not PAT into the vendor private GitHub.

## Boundaries & Constraints

**Always:**
- Load is idempotent on batch sha + waybill.
- Default transport is app upload.

**Never:**
- Do not treat steward Epic 8 as this product.
- Do not PAT into the vendor private GitHub.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| duplicate drop | same batch sha + waybill | idempotent no-op | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-work-passports-dated-extracts CAP-1`.
Surface: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-work-passports-dated-extracts/transports-and-vendors.md; the existing Postgres app / a steward load duty..
Ledger key: `61-1-corridor-transports-upload-default`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-61-1-corridor-transports-upload-default.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

