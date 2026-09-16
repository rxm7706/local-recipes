---
title: '62.1: The catalog names eight measures and their states'
type: 'docs'
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

**Problem:** Q5 named faces and no numbers.

**Approach:** The eight ids are published with dimension, source, and state. First cut is all on; no consumer invents a substitute.

## Boundaries & Constraints

**Always:**
- Eight ids published with dimension, source, and state.
- First cut is all on.

**Never:**
- Do not invent weights.
- Do not let a consumer invent a substitute id.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| catalog published | measure-catalog.md | eight rows, all on | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-build-league-scorecard CAP-1`.
Surface: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-build-league-scorecard/measure-catalog.md; docs/dreams/pyforge-unifying-strategy.md Q5 cite..
Ledger key: `62-1-the-catalog-names-eight-measures-and-their-states`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-62-1-the-catalog-names-eight-measures-and-their-states.md`.
