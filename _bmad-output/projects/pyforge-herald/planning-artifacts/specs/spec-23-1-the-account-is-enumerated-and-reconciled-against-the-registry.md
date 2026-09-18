---
title: '23.1: The account is enumerated and reconciled against the registry'
type: 'feature'
created: '2026-09-16'
status: 'in-review'
baseline_revision: 'e2a1fe04044bd28a4636cc6a295c9dce422a4a0f'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** list_projects pages of 20 and deck status only know README registry sections, so several projects are invisible.

**Approach:** Enumerate every project the login returns (paging), classify presentation / design system / excluded-by-name, reconcile against the registry. deck status lists linked / mirrored / excluded (<reason>) / untwinned. Two retired projects excluded by name in presentations/README.md.

## Boundaries & Constraints

**Always:**
- No account project is absent from herald deck status.

**Never:**
- Do not exclude by a name heuristic.
- Do not invent a second registry.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| retired project | REMOVED-PyForge Unifying Strategy | excluded (<reason>) | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-design-sync-loop CAP-1`.
Surface: pyforge/herald/registry.py, state.py, cli.py (deck status account view); presentations/README.md; tests..
Ledger key: `23-1-the-account-is-enumerated-and-reconciled-against-the-registry`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-1-the-account-is-enumerated-and-reconciled-against-the-registry.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's policy `verify_commands` entry; MRS-GATE-010 binds the dispatch gate to this Success signal, and it is read from the primary tree's tracked spec, so it must be declared here before dispatch, not by the session).

**Manual checks:**
- `herald deck status` lists every project the account returns, each tagged `linked` / `mirrored` / `excluded (<reason>)` / `untwinned`; `REMOVED-PyForge Unifying Strategy` and `Local recipes repository connection` appear as `excluded` with the reason recorded in `presentations/README.md`.
