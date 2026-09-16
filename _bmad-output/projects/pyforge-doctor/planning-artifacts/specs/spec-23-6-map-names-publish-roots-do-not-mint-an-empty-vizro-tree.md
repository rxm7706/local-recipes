---
title: '23.6: MAP names publish roots; do not mint an empty vizro/ tree'
type: 'fix'
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

**Problem:** docs/dashboard/kedro-viz/ is a generated Pages upload root and Vizro is a different product.

**Approach:** MAP and the dashboard README state one subfolder per board. kedro-viz is not renamed. docs/dashboard/vizro/ does not exist unless a later publish story created it.

## Boundaries & Constraints

**Always:**
- kedro-viz keeps its name.
- No empty docs/dashboard/vizro/ tree is minted.

**Never:**
- Do not rename kedro-viz.
- Do not mint an empty vizro/ directory.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| MAP after story | docs/MAP.md | one subfolder per board; no vizro/ invent | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-docs-shelf-alignment CAP-6`.
Surface: docs/MAP.md, docs/dashboard/README.md..
Ledger key: `23-6-map-names-publish-roots-do-not-mint-an-empty-vizro-tree`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-6-map-names-publish-roots-do-not-mint-an-empty-vizro-tree.md`.
