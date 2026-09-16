---
title: '23.7: A new Doctor source flags leftover-shelf occupancy'
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

**Problem:** general_docs_consistency is identity-only with frozen 22.3 fixtures.

**Approach:** A new warn-only, fail-open source compares leftover-shelf paths to the MAP allow-list. Re-adding a dated campaign note at _bmad-output/ root, or a second air-gap how-to outside the cluster, is a finding with a quoted path. A clean MAP fixture is silent. Never a second PR gate.

## Boundaries & Constraints

**Always:**
- Warn-only, fail-open.
- Finding quotes the leftover path.
- Finding is never a second PR gate.

**Never:**
- Do not reuse general_docs_consistency.py.
- Do not make this a competing PR verdict.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| dated note at root | _bmad-output/<campaign>.md | finding with quoted path | warn |
| clean MAP fixture | allow-listed only | silent | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-docs-shelf-alignment CAP-7`.
Surface: a new pyforge.doctor.sources module (not general_docs_consistency.py), pixi task, unit fixtures..
Ledger key: `23-7-a-new-doctor-source-flags-leftover-shelf-occupancy`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-7-a-new-doctor-source-flags-leftover-shelf-occupancy.md`.
