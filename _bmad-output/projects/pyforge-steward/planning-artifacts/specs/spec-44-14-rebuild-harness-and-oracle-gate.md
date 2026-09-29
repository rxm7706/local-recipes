---
title: '44.14: Rebuild harness and oracle gate'
type: 'feature'
created: '2026-09-18'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** a rebuild path in foundry — Dream and memlog to re-derived Spec, spine and epics, drained by Marshal — that cannot pass without the archived suite passing against it

**Approach:** a rebuilt capability is a regeneration drill, never a rewrite by another name.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-44-14-rebuild-harness-and-oracle-gate.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.
- Do not flip ledger key `44-14-rebuild-harness-and-oracle-gate` off `blocked` (operator confirmation required).
- Do not dispatch outward Foundry/archive/conda-forge work without operator confirmation.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| one pilot capability marked `rebuild` (Scribe, per the first pass) **When** the harness runs in foundry **Then** its Spec, spine and epics are re-derived from… | the harness runs in foundry **Then** its Spec, spine and epics are re-derived from the moved memlog, Marshal drains its… | its Spec, spine and epics are re-derived from the moved memlog, Marshal drains its stories under the metered `steward budget` ceiling (44.15), and the archived Scribe suite passes against the rebuilt… | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | the moment the row entered `rebuilding` its source paths froze in `local-recipes`, and `steward cutover plan --append` reports any change against them as a finding | n/a |
| And-clause from epics.md | when the story lands | the harness is reusable for every later `rebuild` row without operator scripting | n/a |

</intent-contract>

## Binding

Parent Spec capability: `fnd:CAP-9`.
Surface: named on the story in epics.md
Ledger key: `44-14-rebuild-harness-and-oracle-gate`.
Ledger status at mint (unchanged): `blocked`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-44-14-rebuild-harness-and-oracle-gate.md`.

## Epic excerpt

As a platform operator,
I want a rebuild path in foundry — Dream and memlog to re-derived Spec, spine and epics, drained by Marshal — that cannot pass without the archived suite passing against it,
So that a rebuilt capability is a regeneration drill, never a rewrite by another name.

**Type:** feature • **Effort:** L • **Deps:** S-44.12, S-44.15 • **FR/AD:** fnd:CAP-9 • fnd:AD-18, fnd:AD-21, fnd:AD-22, fnd:AD-23 • regenerable-factory Dream (the drill)
**Given** one pilot capability marked `rebuild` (Scribe, per the first pass) **When** the harness runs in foundry **Then** its Spec, spine and epics are re-derived from the moved memlog, Marshal drains its stories under the metered `steward budget` ceiling (44.15), and the archived Scribe suite passes against the rebuilt code before the row reads `verified-in-foundry`
**And** the moment the row entered `rebuilding` its source paths froze in `local-recipes`, and `steward cutover plan --append` reports any change against them as a finding
**And** the harness is reusable for every later `rebuild` row without operator scripting

