---
title: '59.7: atlas check= is a finding code only'
type: 'fix'
created: '2026-09-16'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Six sites put runtime data in the finding-code field.

**Approach:** Those sites put the data in evidence and check= stays a kebab code.

## Boundaries & Constraints

**Always:**
- The six atlas sites keep check= as a kebab code; runtime data is in evidence.

**Never:**
- Do not put runtime data in the finding-code field.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| atlas finding | a check emits a finding | check= is kebab; payload in evidence | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-vocabulary-one-name-one-job CAP-8`.
Surface: src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/atlas.py.
Ledger key: `59-7-atlas-check-is-a-finding-code-only`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-59-7-atlas-check-is-a-finding-code-only.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

