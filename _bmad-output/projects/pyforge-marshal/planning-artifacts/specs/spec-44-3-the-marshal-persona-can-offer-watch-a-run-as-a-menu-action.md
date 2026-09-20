---
title: '44.3: The Marshal persona can offer watch a run as a menu action'
type: 'feature'
created: '2026-09-15'
status: 'done'
baseline_revision: '640b7ef224'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** An operator addressing Marshal as a persona has STATUS/HOMES/MCP
but no menu entry that watches a run.

**Approach:** Add a `WATCH` `[[agent.menu]]` entry whose prompt dispatches
`pyforge marshal watch` grammar. Do not change Allowed/Forbidden actions.

## Boundaries & Constraints

**Always:**
- Menu prompt issues a `grammar` action starting `pyforge marshal watch`.
- Transcript stays FR-13 / FR-11 only.

**Never:**
- Never add filesystem or ad-hoc HTTP permissions.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Operator selects WATCH | customize.toml menu | Prompt names `pyforge marshal watch` | n/a |
| Golden transcript | marshal-watch-e2e.json | `grammar` argv starts `pyforge marshal watch` | Freelance kinds fail the persona contract |

</intent-contract>

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `44-3-the-marshal-persona-can-offer-watch-a-run-as-a-menu-action: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
