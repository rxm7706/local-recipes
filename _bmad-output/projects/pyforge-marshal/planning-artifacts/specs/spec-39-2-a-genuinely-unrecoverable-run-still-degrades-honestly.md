---
title: '39.2: A genuinely unrecoverable run still degrades honestly'
type: 'bugfix'
created: '2026-09-18'
status: 'done'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** As a fleet operator, I want `MRS-STATUS-002` to keep firing when no run dir is discoverable or readable, So that the fix narrows the failure mode rather than removing honest degradation.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `39-2-a-genuinely-unrecoverable-run-still-degrades-honestly`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: bugfix / S / S-39.1.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-172` ← `spec-marshal-status-harness-run-id-poisoning CAP-2`.

## Acceptance Criteria

- Given recovery must not become a false green When this story lands Then a run with no discoverable dir — and one with only stale siblings — still reports `unknown` with the finding intact

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| recovery must not become a false green | this story lands | a run with no discoverable dir — and one with only stale siblings — still report | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 39.2 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `39-2-a-genuinely-unrecoverable-run-still-degrades-honestly: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
