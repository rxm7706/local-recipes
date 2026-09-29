---
title: '60.2: Publish uses tools we wield; steward records the review'
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

**Problem:** A module can appear without a recorded review.

**Approach:** A listing cannot appear without steward review, unless it is already in the wielded suite (Certified). Tiers are Unverified / Community Reviewed / BMad Certified.

## Boundaries & Constraints

**Always:**
- No listing without steward review unless already Certified in the wielded suite.
- Tiers are Unverified / Community Reviewed / BMad Certified.

**Never:**
- Do not invent a fourth tier.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| unreviewed module | publish without steward review | refused unless already Certified | refuse |

</intent-contract>

## Binding

Parent Spec capability: `spec-self-hosted-bmad-marketplace CAP-2`.
Surface: Builder / module-template / SKF publish path; the estate catalog registry YAML..
Ledger key: `60-2-publish-uses-tools-we-wield-steward-records-the-review`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-60-2-publish-uses-tools-we-wield-steward-records-the-review.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

