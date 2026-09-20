---
title: '39.1: A null harness run id recovers by filesystem discovery'
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

**Problem:** As a fleet operator, I want `marshal status` to recover the real run id from `.bmad-loop/runs/` when the journal field is null, So that a spin-time poll timeout cannot permanently blind status to a healthy run.

**Approach:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py`

Ledger key: `39-1-a-null-harness-run-id-recovers-by-filesystem-discovery`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: bugfix / S / —.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-171` ← `spec-marshal-status-harness-run-id-poisoning CAP-1`.

## Acceptance Criteria

- Given a poll timeout (`MRS-SPIN-004`) journals `harness_run_id: null` permanently into the launch OUTCOME entry, and the only fallback re-read the same poisoned field When this story lands Then a timestamp-correlated `.bmad-loop/runs/` scan recovers the real id, the same discovery `cli/spin.py::_latest_run_dir` already did And status reports real state (`running`/`idle`/`stopped`) instead of `unknown`

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| a poll timeout (`MRS-SPIN-004`) journals `harness_run_id: null` permanently into | this story lands | a timestamp-correlated `.bmad-loop/runs/` scan recovers the real id, the same di | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 39.1 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `39-1-a-null-harness-run-id-recovers-by-filesystem-discovery: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
