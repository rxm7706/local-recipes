---
title: 'Rebuild marshal in foundry'
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

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `aee221edae` (2026-09-13, "Mark foundry Story 54.4 and epic-54 done."). Ledger row `54-4-rebuild-marshal-in-foundry: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-54-4-rebuild-marshal-in-foundry.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
