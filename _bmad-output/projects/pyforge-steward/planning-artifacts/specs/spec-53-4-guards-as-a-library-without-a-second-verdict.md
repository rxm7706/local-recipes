---
title: '53.4: Guards as a library without a second verdict'
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

**Problem:** Source-Grounding exists only at scribe recall AD-8 and Outcome is absent **When** this story lands **Then** a Spec can name which paper Guard categories it lacks

**Approach:** a Spec can name which paper Guard categories it lacks

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-53-4-guards-as-a-library-without-a-second-verdict.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Source-Grounding exists only at scribe recall AD-8 and Outcome is absent **When** this story lands **Then** a Spec can name which paper Guard categories it lac… | this story lands **Then** a Spec can name which paper Guard categories it lacks | a Spec can name which paper Guard categories it lacks | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | Warden stays the sole PR verdict and doctor stays advisory — no Guard mints a second verdict | n/a |
| And-clause from epics.md | when the story lands | Source-Grounding is the first category added to the library | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: named on the story in epics.md
Ledger key: `53-4-guards-as-a-library-without-a-second-verdict`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-53-4-guards-as-a-library-without-a-second-verdict.md`.

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** 53.1 • **FR/AD:** spec-intelligence-hub
CAP-4 (B7)
**Given** Source-Grounding exists only at scribe recall AD-8 and Outcome is
absent **When** this story lands **Then** a Spec can name which paper Guard
categories it lacks
**And** Warden stays the sole PR verdict and doctor stays advisory — no Guard
mints a second verdict
**And** Source-Grounding is the first category added to the library
**Status:** done

