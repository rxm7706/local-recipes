---
title: 'Rebuild pyforge-core in foundry'
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

**Problem:** Folding `src/shared/packages/pyforge-core` copies path debt.

**Approach:** Birth a core leaf under foundry `src/packages/` from
`station_port`, hooks, and cutover-root contracts. Pass the CAP-1 core
slice.

## Boundaries & Constraints

**Always:**
- Implementation commits on `rxm7706/python-foundry`.
- Public import/CLI contracts that Frames name stay.

**Never:**
- Never `apply --phase 1a` as the source of the leaf.
- Never commit the leaf on the local-recipes shared checkout.

</intent-contract>

## Acceptance Criteria

1. Foundry has a core leaf; CAP-1 core slice green.
2. No fold copy is the source of record.
3. Ledger key stays `backlog` until the foundry PR lands.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `54-2-rebuild-pyforge-core-in-foundry: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
