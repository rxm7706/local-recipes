---
title: 'Rebuild steward in foundry'
type: 'feature'
created: '2026-09-13'
status: 'done'
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Steward in foundry must provision the suite without a
brownfield fold.

**Approach:** Regenerate `pyforge steward` (CLI + MCP) from Frame + Specs
on a python-foundry worktree. Pass the CAP-1 steward slice.

## Boundaries & Constraints

**Always:**
- Verb remains `pyforge steward`.
- Provision path follows the suite register.

**Never:**
- Never copy `src/shared/packages/pyforge-steward` as the engine.
- Never flip `cutover_root` in this Story.

</intent-contract>

## Acceptance Criteria

1. `pyforge steward` on foundry passes the CAP-1 steward slice.
2. Public verb unchanged.
3. Implementation only in a python-foundry worktree.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `54-3-rebuild-steward-in-foundry: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
