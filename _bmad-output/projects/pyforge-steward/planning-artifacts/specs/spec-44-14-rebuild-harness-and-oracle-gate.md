---
title: '44.14: Rebuild harness and oracle gate'
type: 'feature'
created: '2026-09-18'
status: 'blocked'
flag:
  key: pyforge.steward.cutover_rebuild_harness
  provider: openfeature-file
  default: {production: off, staging: off, dev: off}
  scope: global
  fallback: "A stays the oracle; no rebuild harness runs"
  cleanup: 90 days after ON in every environment (Q4)   # retrofit block (spec-feature-flag-governance CAP-7, operator ruling R6 of 2026-10-26): the key joins the tree when this story builds
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

> **Amended 2026-11-10 (Story 120.3) — re-derived from the memlog B reads at the pin; no `moving` state.** Operator
> rulings of 2026-11-10 (`docs/dreams/pyforge-unifying-strategy.md` § Realization log, ruling 1 and the mint
> entry): nothing is moved, so a `rebuild` row's Spec, spine and epics are re-derived on B from Dream plus memlog,
> read from A at the pinned SHA (a Frame is a pointer, not a seed). The ledger states are `planned`, `rebuilding`,
> `verified-in-foundry` and `cut` (`fnd:CAP-9` as amended at the 2026-11-10 mint); there is no `moving` state.
> `rebuilding` is the one freezing state, and a change under its frozen paths is named by doctor's
> `frozen-path-changed` source (`spec-pyforge-doctor:CAP-94`), not by `steward cutover plan --append`. The matrix
> and the epic excerpt below follow the amended story body in `epics.md`. The ledger key stays `blocked`.

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
| one pilot capability marked `rebuild` (Scribe, per the first pass) | the harness runs in foundry | its Spec, spine and epics are re-derived from Dream plus memlog read from A at the pinned SHA, Marshal drains its stories under the metered `steward budget` ceiling (44.15), and the archived Scribe suite passes against the rebuilt code before the row reads `verified-in-foundry` | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | the moment the row entered `rebuilding` its source paths froze in `local-recipes`, and doctor's `frozen-path-changed` source (`spec-pyforge-doctor:CAP-94`) reports any change against them as a finding | n/a |
| States (amended 2026-11-10) | any ledger row the harness reads or writes | its state is one of `planned`, `rebuilding`, `verified-in-foundry`, `cut`; there is no `moving` state | n/a |
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
**Given** one pilot capability marked `rebuild` (Scribe, per the first pass) **When** the harness runs in foundry **Then** its Spec, spine and epics are re-derived from Dream plus memlog read from A at the pinned SHA, Marshal drains its stories under the metered `steward budget` ceiling (44.15), and the archived Scribe suite passes against the rebuilt code before the row reads `verified-in-foundry`
**And** the moment the row entered `rebuilding` its source paths froze in `local-recipes`, and doctor's `frozen-path-changed` source (`spec-pyforge-doctor:CAP-94`) reports any change against them as a finding
**And** the harness is reusable for every later `rebuild` row without operator scripting

