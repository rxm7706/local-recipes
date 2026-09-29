---
title: '44.4: marshal watch report is viewable in the portal'
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

**Problem:** Watching a run still required a terminal after Story 44.1.

**Approach:** Add `watch_report` next to `chrome_home`, route
`/stations/marshal/watch/`, and render Story 44.1's report via
`PortalClient.call` (no `pyforge.*` import in the view).

## Boundaries & Constraints

**Always:**
- Same marshal station role as `chrome_home`.
- Selection is `project` / `run` / `fleet` query parameters.
- Report shape is Story 44.1's envelope.

**Never:**
- Never import `pyforge.*` from `views.py`.
- Never open raw HTTP from the portal.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Marshal role + project/run | GET watch/?project=&run= | Renders completions / delta / running / queue / action | Injected job in tests |
| Wrong station role | steward role | 403 | n/a |

</intent-contract>

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `44-4-marshal-watchs-report-is-viewable-in-the-portal: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
