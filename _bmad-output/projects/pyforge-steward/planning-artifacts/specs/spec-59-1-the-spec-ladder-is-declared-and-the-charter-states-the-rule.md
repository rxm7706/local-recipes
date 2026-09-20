---
title: '59.1: The Spec ladder is declared and the Charter states the rule'
type: 'docs'
created: '2026-09-16'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Eight Spec statuses are live and only extension-point is defined.

**Approach:** Define all eight Spec statuses in the governance declaration the Charter cites. Keep the three ended-acts distinct. shipped remains Spec-terminal. The enum is recommended, not required; unknown values are preserved and warned, never reset.

## Boundaries & Constraints

**Always:**
- All eight statuses are defined in one declaration the Charter cites.
- The three ended-acts are not collapsed.
- shipped remains Spec-terminal.

**Never:**
- Do not make the enum required or reset unknown values.
- Do not flip any Epic 44 blocked key.
- Do not change docs/dreams/README.md's Dream-ladder job.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| unknown status | Spec uses a value not in the eight | preserved and warned, never reset | warn |
| ended-act trio | three ended statuses present | remain three named acts | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-vocabulary-one-name-one-job CAP-1`.
Surface: docs/governance/; docs/dreams/pyforge-charter.md. docs/dreams/README.md stays the Dream ladder only..
Ledger key: `59-1-the-spec-ladder-is-declared-and-the-charter-states-the-rule`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-59-1-the-spec-ladder-is-declared-and-the-charter-states-the-rule.md`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `6542fd59c2` (2026-09-18, "Merge pull request #1435 from rxm7706/dispatch/pyforge-steward/59.1"). Ledger row `59-1-the-spec-ladder-is-declared-and-the-charter-states-the-rule: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `docs/dreams/pyforge-charter.md`, `docs/governance/guild-roster.json`, `tests/scripts/test_spec_ladder_is_declared.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready` → `done` (ledger row `59-1-the-spec-ladder-is-declared-and-the-charter-states-the-rule: done`).
- `## Auto Run Result` reconstructed from git (none survived).
