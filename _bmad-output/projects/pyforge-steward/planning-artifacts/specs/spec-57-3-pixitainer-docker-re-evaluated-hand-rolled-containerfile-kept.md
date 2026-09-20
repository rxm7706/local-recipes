---
title: '57.3: pixitainer-docker re-evaluated, hand-rolled Containerfile kept'
type: 'docs'
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

**Problem:** the Docker/Podman pixitainer backend re-tested against the Story 10.3 contract now that it's on conda-forge

**Approach:** adopting a generated Containerfile is a measured choice, not a retry of the SIF-only rejection from 10.3.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-57-3-pixitainer-docker-re-evaluated-hand-rolled-containerfile-kept.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| `pixitainer-docker` 0.8.3 is now on conda-forge (missing as a Docker backend when Story 10.3 evaluated SIF-only `pixitainer`) | this story lands **Then** `pixitainer-eval.md` carries a dated Design Note with each Story-10.3 must-hold row scored pa… | `pixitainer-eval.md` carries a dated Design Note with each Story-10.3 must-hold row scored pass/fail and the CLI/package actually invoked | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | a failing row keeps the hand-rolled Containerfile rather than reopening SIF-only `pixi-containerize` | n/a |
| And-clause from epics.md | when the story lands | Mason presenton's own pixitainer usage is untouched either way | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: named on the story in epics.md
Ledger key: `57-3-pixitainer-docker-re-evaluated-hand-rolled-containerfile-kept`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-57-3-pixitainer-docker-re-evaluated-hand-rolled-containerfile-kept.md`.

## Epic excerpt

As a platform operator,
I want the Docker/Podman pixitainer backend re-tested against the Story 10.3
contract now that it's on conda-forge,
So that adopting a generated Containerfile is a measured choice, not a retry
of the SIF-only rejection from 10.3.

**Type:** docs • **Effort:** S • **Deps:** — • **FR/AD:** spec-platform-image-one-pixi-env CAP-3
**Given** `pixitainer-docker` 0.8.3 is now on conda-forge (missing as a Docker
backend when Story 10.3 evaluated SIF-only `pixitainer`)
**When** this story lands **Then** `pixitainer-eval.md` carries a dated Design
Note with each Story-10.3 must-hold row scored pass/fail and the CLI/package
actually invoked
**And** a failing row keeps the hand-rolled Containerfile rather than
reopening SIF-only `pixi-containerize`
**And** Mason presenton's own pixitainer usage is untouched either way
**Status:** done — shipped `59083b8391` (2026-08-25); Design Note recorded
outcome: fail, hand-rolled Containerfile kept

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `57-3-pixitainer-docker-re-evaluated-hand-rolled-containerfile-kept: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
