---
title: '60.4: Frame index and a thin browse list'
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

**Problem:** Operators read YAML by hand and Frames have no catalog row.

**Approach:** A read-only list shows modules and Frames (name, tier, link or install hint). A Frame listing is a reviewed git add; share uses CAP-3 backends. It is not an App Store, MyBMAD, Collab, or nebari-frames.

## Boundaries & Constraints

**Always:**
- Read-only list of modules and Frames with name, tier, link or install hint.

**Never:**
- Do not build an App Store, MyBMAD, Collab, or nebari-frames.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Frame listing | reviewed git add | row appears on the browse list | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-self-hosted-bmad-marketplace CAP-4 CAP-7`.
Surface: docs/foundry/frames/; a generated index or existing chrome page..
Ledger key: `60-4-frame-index-and-a-thin-browse-list`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-60-4-frame-index-and-a-thin-browse-list.md`.
