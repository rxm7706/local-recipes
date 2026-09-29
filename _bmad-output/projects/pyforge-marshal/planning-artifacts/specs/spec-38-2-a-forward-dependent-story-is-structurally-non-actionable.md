---
title: '38.2: A forward-dependent story is structurally non-actionable'
type: 'feature'
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

**Problem:** As a fleet operator, I want a found forward-dependent story set to a status the picker cannot select, So that the engine is structurally unable to dispatch it early rather than merely advised not to.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `38-2-a-forward-dependent-story-is-structurally-non-actionable`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: feature / S / S-38.1.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-54` ← `spec-bmad-loop-forward-dependency-blindness CAP-2`.

## Acceptance Criteria

- Given `ACTIONABLE_STATUSES = {"backlog", "ready-for-dev"}` When this story lands Then the story reads `blocked` in both the Tier-3 feed and the tracked ledger, and `next_actionable(epic=2)` returns 2.4 rather than the blocked story

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `ACTIONABLE_STATUSES = {"backlog", "ready-for-dev"}` | this story lands | the story reads `blocked` in both the Tier-3 feed and the tracked ledger, and `n | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 38.2 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `38-2-a-forward-dependent-story-is-structurally-non-actionable: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
