---
title: '59.2: Detectors read one declaration; in-progress is grandfathered'
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

**Problem:** Those modules each keep a private status set.

**Approach:** They import the CAP-1 declaration. New Specs are not written in-progress; live in-progress files stay open until next edited. Doctor subset of Warden remains declared.

## Boundaries & Constraints

**Always:**
- board.py, chain.py, and status_body_consistency.py import the CAP-1 declaration.
- Live in-progress Specs stay open until next edited.

**Never:**
- Do not rewrite live in-progress files just to retire the status.
- Do not invert Doctor subset of Warden.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| new Spec | authoring a new SPEC.md | status is not in-progress | n/a |
| live in-progress | existing file already in-progress | unchanged until next edit | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-vocabulary-one-name-one-job CAP-2`.
Surface: src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py, chain.py, status_body_consistency.py; exit-code domains in the same declaration file (different key; DW-VOCAB-2026-09-14-8)..
Ledger key: `59-2-detectors-read-one-declaration-in-progress-is-grandfathered`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-59-2-detectors-read-one-declaration-in-progress-is-grandfathered.md`.
