---
title: '33.11: Attribution becomes unforgeable before the Track serves a second principal'
type: 'feature'
created: '2026-09-18'
status: 'blocked'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Attribution becomes unforgeable before the Track serves a second principal (contract recovered from epics.md Intent + ACs).

**Approach:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/journal.py` (`:159` the only site naming operator attribution), `cli/gate.py`, `cli/journal*.py` (the operator-attributed write surface), `tests/unit/test_journal*.py`

Ledger key: `33-11-attribution-becomes-unforgeable-before-the-track-serves-a-second-principal`.
Ledger status (do not edit the ledger): `blocked`.
Type / Effort / Deps: feature / L / S-33.4.

### Living CAP citations

- Cited from epics.md: spec-pyforge-marshal F-4 (answered 2026-09-09: B is the contract, A the v1 state) • `hub:CAP-3` (the Track's human-approvals field) • batch § 8 item 1

## Acceptance Criteria

- Given the governed agent is trusted in v1 and operator attribution is advisory — enforced at the call surface only, with no authentication primitive anywhere in the package, the worktree not a sandbox, and process isolation deferred — so a run record is a log, not evidence, the moment a second principal reads it When the trigger fires (the Foundry cutover flag, a shared Hub, or an external adopter — whichever comes first) and this story is dispatched behind 33.4's single publisher Then operator-attributed journal entries carry a signature the call surface verifies (a keyed primitive whose key never lives in the worktree), an unsigned or mis-signed operator entry is refused with a printed reason, the Track published by 33.4 carries the verified attribution in its human-approvals field, and process isolation is still deferred but named as the remaining gap And this story is minted `blocked` on its trigger by design: it never outranks 33.5/33.2/33.3 on the throughput queue (operator 2026-09-09 — governance scores zero on speed-to-market until a second principal exists)

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.
- Do not flip this key off `blocked`. Operator trigger (Foundry cutover / shared Hub / second principal) only.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the governed agent is trusted in v1 and operator attribution is advisory — enfor | the trigger fires (the Foundry cutover flag, a shared Hub, o | operator-attributed journal entries carry a signature the call surface verifies  | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 33.11 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.
