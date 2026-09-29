---
title: '62.3: Consumers cite on rows only'
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

**Problem:** A station can mint a stealth metric.

**Approach:** Citing off, archived, or an unknown id is a refuse. Hub Outcome Guards are not implemented here — they read later.

## Boundaries & Constraints

**Always:**
- Citing off, archived, or unknown id is a refuse.

**Never:**
- Do not implement Hub Outcome Guards here.
- Do not invent weights.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| cite off | known id, state off | refuse | refuse |
| cite unknown | id not in catalog | refuse | refuse |
| cite on | known id, state on | allowed | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-build-league-scorecard CAP-3`.
Surface: a refuse path Herald / Atlas / Marshal / Doctor can call..
Ledger key: `62-3-consumers-cite-on-rows-only`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-62-3-consumers-cite-on-rows-only.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

