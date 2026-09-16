---
title: '59.5: One mint-time slugify and two DW families'
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

**Problem:** One story is spelled three non-derivable ways and DW- has eleven grammars.

**Approach:** A new story's heading, ledger key, and spec-<ledger-key>.md derive from one function. A new DW- id is story-scoped or sweep-scoped and includes the short station token. The 53 divergent slugs and 1338 existing DW- ids are untouched.

## Boundaries & Constraints

**Always:**
- New heading, ledger key, and spec-<ledger-key>.md share one slugify.
- New DW- ids are story-scoped or sweep-scoped and carry the short station token.

**Never:**
- Do not retro-rename the 53 divergent slugs.
- Do not rewrite the 1338 existing DW- ids.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| new story mint | one title | heading, ledger key, spec filename all derive | n/a |
| existing DW- id | any of the 1338 | byte-identical | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-vocabulary-one-name-one-job CAP-6`.
Surface: scripts/deferred_work_promote.py.
Ledger key: `59-5-one-mint-time-slugify-and-two-dw-families`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-59-5-one-mint-time-slugify-and-two-dw-families.md`.
