---
title: 'Rebuild pyforge-core in foundry'
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
