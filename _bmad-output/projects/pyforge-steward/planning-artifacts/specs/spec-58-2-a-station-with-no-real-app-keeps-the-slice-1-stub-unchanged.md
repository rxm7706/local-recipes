---
title: '58.2: A station with no real app keeps the slice-1 stub, unchanged'
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

**Problem:** every station without a real in-process MCP app to keep answering exactly as slice 1 shipped it

**Approach:** adding real-tool hosting for one station cannot regress the other eight.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-58-2-a-station-with-no-real-app-keeps-the-slice-1-stub-unchanged.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| only marshal has a real app **When** this story lands **Then** `spec-mcp-era-isolation`'s CAP-1..145 acceptance (dual-era handshake, protocol-version negotiati… | this story lands **Then** `spec-mcp-era-isolation`'s CAP-1..145 acceptance (dual-era handshake, protocol-version negoti… | `spec-mcp-era-isolation`'s CAP-1..145 acceptance (dual-era handshake, protocol-version negotiation, 405 on non-POST) still holds unchanged for every station without one | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | `_apps` covers all 9 default stations while `_real_apps` covers only `{"marshal"}` | n/a |
| And-clause from epics.md | when the story lands | a `django.setup()` failure for any reason falls back to the stub for **every** station, covered directly by a mocked-failure unit test on that isolation seam | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: named on the story in epics.md
Ledger key: `58-2-a-station-with-no-real-app-keeps-the-slice-1-stub-unchanged`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-58-2-a-station-with-no-real-app-keeps-the-slice-1-stub-unchanged.md`.

## Epic excerpt

As a platform operator,
I want every station without a real in-process MCP app to keep answering exactly as
slice 1 shipped it,
So that adding real-tool hosting for one station cannot regress the other eight.

**Type:** feature • **Effort:** S • **Deps:** S-58.1 • **FR/AD:** spec-mcp-host-real-station-tools CAP-2
**Given** only marshal has a real app **When** this story lands **Then**
`spec-mcp-era-isolation`'s CAP-1..145 acceptance (dual-era handshake, protocol-version
negotiation, 405 on non-POST) still holds unchanged for every station without one
**And** `_apps` covers all 9 default stations while `_real_apps` covers only `{"marshal"}`
**And** a `django.setup()` failure for any reason falls back to the stub for **every**
station, covered directly by a mocked-failure unit test on that isolation seam
**Status:** done — shipped `20a85dcc79` (2026-09-12); sidecar boot logs show all 9 session
managers starting cleanly

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `58-2-a-station-with-no-real-app-keeps-the-slice-1-stub-unchanged: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
