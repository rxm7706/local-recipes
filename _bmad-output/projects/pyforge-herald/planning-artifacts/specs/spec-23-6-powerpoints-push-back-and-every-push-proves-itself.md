---
title: '23.6: PowerPoints push back, and every push proves itself'
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

**Problem:** deck push skips both PPTX (Story 5.1 deferral) and read-back is a hand curl-and-strip.

**Approach:** Prove a binary write_files shape on one PPTX and adopt it for the pair. Push reads every pushed file back through the serve URL with harness stripped. Read-back mismatch is a refusal that names the file.

## Boundaries & Constraints

**Always:**
- Read-back is byte-identical for 100% of pushed files.
- Second push pushes nothing.

**Never:**
- Do not warn on a read-back mismatch — refuse and name the file.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| mismatch | serve bytes != pushed bytes | refuse naming the file | refuse |

</intent-contract>

## Binding

Parent Spec capability: `spec-design-sync-loop CAP-6`.
Surface: herald/deck_pipeline.py push_exports PPTX pair + --prove; state.py; README ledger etag row..
Ledger key: `23-6-powerpoints-push-back-and-every-push-proves-itself`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-6-powerpoints-push-back-and-every-push-proves-itself.md`.
