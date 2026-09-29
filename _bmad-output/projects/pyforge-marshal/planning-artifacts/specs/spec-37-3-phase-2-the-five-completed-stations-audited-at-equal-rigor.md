---
title: '37.3: Phase 2 — the five completed stations audited at equal rigor'
type: 'docs'
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

**Problem:** As a fleet operator, I want atlas, doctor, herald, scribe and warden audited as hard as the unfinished stations, So that "complete" is an earned status rather than an unexamined one.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `37-3-phase-2-the-five-completed-stations-audited-at-equal-rigor`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: docs / L / S-37.2.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-27` ← `spec-artifact-chain-reconciliation CAP-3`.

## Acceptance Criteria

- Given five stations read complete and had never been sampled against code When this story lands Then each has a gate report, every chain column is verified or carries a dispositioned finding, and Spec statuses are corrected to their earned values

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| five stations read complete and had never been sampled against code | this story lands | each has a gate report, every chain column is verified or carries a dispositione | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 37.3 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `37-3-phase-2-the-five-completed-stations-audited-at-equal-rigor: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
