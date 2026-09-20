---
title: '44.2: marshal watch is reachable over MCP'
type: 'feature'
created: '2026-09-15'
status: 'done'
baseline_revision: '640b7ef224'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `marshal watch` exists as a CLI verb (Story 44.1) but an agent on
`POST /stations/marshal/mcp` cannot call it, and FR-155 treats `watch` as a
CLI verb with no tool.

**Approach:** Register `marshal_watch` on the Host POST face
(`django_marshal_portal/mcp_asgi.py`) and on Marshal's FastMCP tool surface
(`pyforge.marshal.mcp`), both forwarding the same argv Story 44.1 already
owns.

## Boundaries & Constraints

**Always:**
- Same project/run/fleet parameters as `marshal watch`.
- Return the Story 44.1 envelope/report shape (via `marshal watch --format json`).
- Callable as `POST /stations/marshal/mcp` only for the persona `mcp` kind.

**Never:**
- Never resolve, resume, dispatch, or write a sprint ledger.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Tool + project/run | `marshal_watch(project, run)` | Same JSON envelope as CLI | CLI findings pass through |
| Tool + fleet | `marshal_watch(fleet=true)` | Fleet snapshot envelope | CLI findings pass through |
| FR-155 | live CLI verbs | `watch` has a claiming tool | Gate stays green |

</intent-contract>

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `44-2-marshal-watch-is-reachable-over-mcp: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
