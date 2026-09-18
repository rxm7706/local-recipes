---
title: '39.2: Metapackage recipe'
type: 'feature'
created: '2026-09-18'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** a ``noarch: generic`` ``bmad-suite`` metapackage pinning every active member

**Approach:** one channel install pulls the whole suite.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-39-2-metapackage-recipe.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| story body in epics.md | story lands | acceptance criteria in the epic excerpt hold | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: named on the story in epics.md
Ledger key: `39-2-metapackage-recipe`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-39-2-metapackage-recipe.md`.

## Epic excerpt

As a factory operator,
I want a ``noarch: generic`` ``bmad-suite`` metapackage pinning every active member,
So that one channel install pulls the whole suite.

**Type:** feature • **Effort:** M • **Deps:** S-39.1 • **FR/AD:** suite:CAP-2
**Status:** done — shipped 2026-09-01

