---
title: 'Rebuild marshal in foundry'
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

**Problem:** Launch needs one real dispatch on the foundry remote, not a
folded marshal tree.

**Approach:** Regenerate `pyforge marshal` cursor-native dispatch (CLI +
MCP). Thin oracle plus one foundry-remote dispatch. Extra `MRS-DISP-*`
wait for 44.14.

## Boundaries & Constraints

**Always:**
- Verb remains `pyforge marshal`.
- `cutover_root` stays `local-recipes`.

**Never:**
- Never fold `src/shared/packages/pyforge-marshal`.
- Never claim the kernel is debt-free.

</intent-contract>

## Acceptance Criteria

1. One marshal dispatch against the foundry remote is green.
2. CAP-1 marshal slice is green.
3. `cutover_root` is still `local-recipes`.
