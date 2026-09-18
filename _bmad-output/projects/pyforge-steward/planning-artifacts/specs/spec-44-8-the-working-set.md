---
title: '44.8: The working set'
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

**Problem:** only in-flight and sole-maintainer recipes in `factory/recipes/`

**Approach:** the 7,855-directory universe is never copied.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-44-8-the-working-set.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.
- Do not flip ledger key `44-8-the-working-set` off `blocked` (operator confirmation required).
- Do not dispatch outward Foundry/archive/conda-forge work without operator confirmation.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| manifest rows with `reason ∈ {in-flight, sole-maintainer, referenced-by-spec}` **When** the recipes move **Then** `factory/recipes/` is exactly that set and is… | the recipes move **Then** `factory/recipes/` is exactly that set and island CI asserts `count <= manifest rows` | `factory/recipes/` is exactly that set and island CI asserts `count <= manifest rows` | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | every other `recipes/**` row reads `stays` (archived with `local-recipes`) | n/a |
| And-clause from epics.md | when the story lands | — reciprocal note, not a `Deps:` token: **`spec-fleet-stewardship` CAP-1's `recipes/**` surface is mostly archived after this story**; its Dream and Spec carry a dated dormancy note (mason, 2026-09-0… | n/a |

</intent-contract>

## Binding

Parent Spec capability: `fnd:CAP-5`.
Surface: named on the story in epics.md
Ledger key: `44-8-the-working-set`.
Ledger status at mint (unchanged): `blocked`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-44-8-the-working-set.md`.

## Epic excerpt

As a platform operator,
I want only in-flight and sole-maintainer recipes in `factory/recipes/`,
So that the 7,855-directory universe is never copied.

**Type:** feature • **Effort:** M • **Deps:** S-44.7 • **FR/AD:** fnd:CAP-5 • fnd:AD-2, fnd:AD-10
**Given** manifest rows with `reason ∈ {in-flight, sole-maintainer, referenced-by-spec}` **When** the recipes move **Then** `factory/recipes/` is exactly that set and island CI asserts `count <= manifest rows`
**And** every other `recipes/**` row reads `stays` (archived with `local-recipes`)
**And** — reciprocal note, not a `Deps:` token: **`spec-fleet-stewardship` CAP-1's `recipes/**` surface is mostly archived after this story**; its Dream and Spec carry a dated dormancy note (mason, 2026-09-09) so the surface is not read later as live (fleet readiness 2026-09-09, mason-E4 / Class D D11)

