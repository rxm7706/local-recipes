---
title: '39.3: Generator and batch build'
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

**Problem:** ``generate-bmad-suite`` / ``build-bmad-suite`` to refresh pins from registry class

**Approach:** metapackage bumps are mechanical after member upstream moves.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-39-3-generator-and-batch-build.md` (CHAIN-STANDARD §5).

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
Ledger key: `39-3-generator-and-batch-build`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-39-3-generator-and-batch-build.md`.

## Epic excerpt

As a factory operator,
I want ``generate-bmad-suite`` / ``build-bmad-suite`` to refresh pins from registry class,
So that metapackage bumps are mechanical after member upstream moves.

**Type:** feature • **Effort:** M • **Deps:** S-39.2 • **FR/AD:** suite:CAP-3
**Status:** done — shipped 2026-09-01

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `39-3-generator-and-batch-build: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
