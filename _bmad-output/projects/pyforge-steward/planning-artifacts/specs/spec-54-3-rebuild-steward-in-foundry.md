---
title: 'Rebuild steward in foundry'
type: 'feature'
created: '2026-09-13'
status: 'backlog'
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
