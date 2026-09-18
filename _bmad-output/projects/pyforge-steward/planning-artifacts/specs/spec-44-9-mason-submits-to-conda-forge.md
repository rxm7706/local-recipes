---
title: '44.9: Mason submits to conda-forge'
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

**Problem:** `submit` targeting staged-recipes or the bot fork and `update` targeting the feedstock maintainer-edit path from foundry

**Approach:** an agent-opened PR never targets `local-recipes`.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-44-9-mason-submits-to-conda-forge.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.
- Do not flip ledger key `44-9-mason-submits-to-conda-forge` off `blocked` (operator confirmation required).
- Do not dispatch outward Foundry/archive/conda-forge work without operator confirmation.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| the submit path **When** an agent submits **Then** the target is staged-recipes or the bot fork, never `local-recipes` (asserted in a test on the submit path),… | an agent submits **Then** the target is staged-recipes or the bot fork, never `local-recipes` (asserted in a test on th… | the target is staged-recipes or the bot fork, never `local-recipes` (asserted in a test on the submit path), and feedstock updates use the maintainer-edit path | fail loud; never silent skip |

</intent-contract>

## Binding

Parent Spec capability: `fnd:CAP-6`.
Surface: named on the story in epics.md
Ledger key: `44-9-mason-submits-to-conda-forge`.
Ledger status at mint (unchanged): `blocked`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-44-9-mason-submits-to-conda-forge.md`.

## Epic excerpt

As a platform operator,
I want `submit` targeting staged-recipes or the bot fork and `update` targeting the feedstock maintainer-edit path from foundry,
So that an agent-opened PR never targets `local-recipes`.

**Type:** feature • **Effort:** M • **Deps:** S-44.6, S-44.8 • **FR/AD:** fnd:CAP-6 • fnd:AD-4, fnd:AD-9, fnd:AD-11 • CLAUDE.md Rule 1 / Rule 2 (Mason)
**Outward (`fnd:AD-9`):** opens pull requests against conda-forge — held `blocked`; dispatched only on the operator's explicit confirmation.
**Given** the submit path **When** an agent submits **Then** the target is staged-recipes or the bot fork, never `local-recipes` (asserted in a test on the submit path), and feedstock updates use the maintainer-edit path

