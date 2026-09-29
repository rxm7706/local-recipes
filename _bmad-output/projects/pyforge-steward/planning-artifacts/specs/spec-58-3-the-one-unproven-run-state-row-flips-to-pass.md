---
title: '58.3: The one unproven run-state row flips to PASS'
type: 'chore'
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

**Problem:** `spec-run-state-one-publisher`'s last unproven verification row closed

**Approach:** "live run appears on `/runs/`, timing survives teardown" is evidence, not intent.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-58-3-the-one-unproven-run-state-row-flips-to-pass.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| that row read `NOT PROVEN` because the real tool was never registered on the server answering the call **When** this story lands **Then** `spec-run-state-one-p… | this story lands **Then** `spec-run-state-one-publisher/verification-2026-09-12.md` records it `PASS` with the live run… | `spec-run-state-one-publisher/verification-2026-09-12.md` records it `PASS` with the live run's evidence | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | the run's timing is queryable after the workstation that drove it is gone | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: chart `mcp-host` Deployment gains the DB/secret env it needs plus postgres
Ledger key: `58-3-the-one-unproven-run-state-row-flips-to-pass`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-58-3-the-one-unproven-run-state-row-flips-to-pass.md`.

## Epic excerpt

As a platform operator,
I want `spec-run-state-one-publisher`'s last unproven verification row closed,
So that "live run appears on `/runs/`, timing survives teardown" is evidence, not intent.

**Type:** chore • **Effort:** S • **Deps:** S-58.1 • **FR/AD:** spec-mcp-host-real-station-tools CAP-3
**Surface:** chart `mcp-host` Deployment gains the DB/secret env it needs plus postgres
egress/ingress (previously DNS-only)
**Given** that row read `NOT PROVEN` because the real tool was never registered on the
server answering the call **When** this story lands **Then**
`spec-run-state-one-publisher/verification-2026-09-12.md` records it `PASS` with the live
run's evidence
**And** the run's timing is queryable after the workstation that drove it is gone
**Status:** done — shipped `20a85dcc79` (2026-09-12)

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `58-3-the-one-unproven-run-state-row-flips-to-pass: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
