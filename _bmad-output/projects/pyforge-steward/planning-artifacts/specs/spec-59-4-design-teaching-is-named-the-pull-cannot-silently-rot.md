---
title: '59.4: Design teaching is named; the pull cannot silently rot'
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

**Problem:** The deck teaches four-phases / three-tracks and is 13.5 KB behind.

**Approach:** The deck names itself teaching-only except method-vs-machinery and project-context-as-constitution. Retired BMAD skill names and Paige are gone from the pulled deck. A detector flags silent size/etag drift.

## Boundaries & Constraints

**Always:**
- Pulled deck states teaching-only except the two named exceptions.
- Retired BMAD skill names and Paige are absent from the pulled deck.
- A detector flags silent size/etag drift.

**Never:**
- Do not treat the whole deck as operational contract.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| silent etag/size drift | pulled artifact diverges without a recorded pull | detector finding | finding |

</intent-contract>

## Binding

Parent Spec capability: `spec-vocabulary-one-name-one-job CAP-5`.
Surface: presentations/agentic-sdlc/; DW-VOCAB-2026-09-14-3. Herald executes the pull; steward wrote the ruling..
Ledger key: `59-4-design-teaching-is-named-the-pull-cannot-silently-rot`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-59-4-design-teaching-is-named-the-pull-cannot-silently-rot.md`.
