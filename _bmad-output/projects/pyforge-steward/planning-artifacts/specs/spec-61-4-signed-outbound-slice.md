---
title: '61.4: Signed outbound slice'
type: 'feature'
created: '2026-09-16'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
baseline_revision: 'ff2455866b3379fccf333e175e5166dab351c67e'
---

<intent-contract>

## Intent

**Problem:** A dump of Jira or factory BMAD can leave unsigned.

**Approach:** Default deny; a named slice plus recorded signer is required. The vendor loads our file — we do not PAT into their org.

## Boundaries & Constraints

**Always:**
- Default deny.
- Named slice plus recorded signer required.

**Never:**
- Do not PAT into the vendor private GitHub.
- Do not treat Epic 8 as this product.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| unsigned dump | no signer | refused | refuse |

</intent-contract>

## Binding

Parent Spec capability: `spec-work-passports-dated-extracts CAP-4`.
Surface: outbound loader; named outbound-signer role on the existing app..
Ledger key: `61-4-signed-outbound-slice`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-61-4-signed-outbound-slice.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

