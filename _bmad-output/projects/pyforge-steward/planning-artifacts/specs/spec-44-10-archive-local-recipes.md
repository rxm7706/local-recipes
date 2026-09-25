---
title: '44.10: Archive local-recipes'
type: 'feature'
created: '2026-09-18'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

> **Retired 2026-09-25 — never dispatch.** `fnd:CAP-7` was retired by the operator's no-archive
> ruling (`spec-python-foundry-cutover` memlog 2026-09-25); this story retires with it. The ledger
> key stays `blocked`; an operator flip does not revive it. Text kept as history. The spine
> amendment is Story 67.8.

<intent-contract>

## Intent

**Problem:** `local-recipes` read-only with its README superseded, Azure disabled, the last SHA pinned in foundry, history kept, and the worktree residue retired

**Approach:** the default clone is foundry and `.steward` has one git root.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-44-10-archive-local-recipes.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.
- Do not flip ledger key `44-10-archive-local-recipes` off `blocked` (operator confirmation required).
- Do not dispatch outward Foundry/archive/conda-forge work without operator confirmation.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| every other 44.x `done` **When** the archive lands **Then** the README opens with the supersession banner, Azure pipelines are disabled, the final SHA is pinne… | the archive lands **Then** the README opens with the supersession banner, Azure pipelines are disabled, the final SHA i… | the README opens with the supersession banner, Azure pipelines are disabled, the final SHA is pinned in the foundry manifest and the Dream's Realization log, history is kept, the 268 registered workt… | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | `DW-CC-2026-09-04-1` is resolved | n/a |

</intent-contract>

## Binding

Parent Spec capability: `fnd:CAP-7`.
Surface: named on the story in epics.md
Ledger key: `44-10-archive-local-recipes`.
Ledger status at mint (unchanged): `blocked`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-44-10-archive-local-recipes.md`.

## Epic excerpt

As a platform operator,
I want `local-recipes` read-only with its README superseded, Azure disabled, the last SHA pinned in foundry, history kept, and the worktree residue retired,
So that the default clone is foundry and `.steward` has one git root.

**Type:** feature • **Effort:** M • **Deps:** S-44.1, S-44.2, S-44.3, S-44.4, S-44.5, S-44.6, S-44.7, S-44.8, S-44.9 • **FR/AD:** fnd:CAP-7 • fnd:AD-1, fnd:AD-8, fnd:AD-9, fnd:AD-11 • `DW-CC-2026-09-04-1`
**Outward, irreversible (`fnd:AD-9`):** disables CI and archives a repository — held `blocked`; dispatched only on the operator's explicit confirmation.
**Given** every other 44.x `done` **When** the archive lands **Then** the README opens with the supersession banner, Azure pipelines are disabled, the final SHA is pinned in the foundry manifest and the Dream's Realization log, history is kept, the 268 registered worktrees are retired, and a fresh clone of foundry is the default working tree
**And** `DW-CC-2026-09-04-1` is resolved

