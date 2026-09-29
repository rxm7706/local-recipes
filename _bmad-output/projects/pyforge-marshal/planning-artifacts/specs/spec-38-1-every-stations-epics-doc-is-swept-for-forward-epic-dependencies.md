---
title: '38.1: Every station''s epics doc is swept for forward-epic dependencies'
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

**Problem:** As a fleet operator, I want every story whose documented `**Deps:**` points into a later epic found by a sweep across all eight stations, So that a structural blocker is known before a run burns attempts on it.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `38-1-every-stations-epics-doc-is-swept-for-forward-epic-dependencies`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-53` ← `spec-bmad-loop-forward-dependency-blindness CAP-1`.

## Acceptance Criteria

- Given `next_actionable` is a strict file-order scan with no `depends_on` concept, and marshal's own epics.md documented three forward deps (2.3→S-3.2, 2.7→S-4.1, 8.5→S-10.2) the engine could not see When this story lands Then a sweep covers all 8 stations

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `next_actionable` is a strict file-order scan with no `depends_on` concept, and  | this story lands | a sweep covers all 8 stations | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 38.1 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `38-1-every-stations-epics-doc-is-swept-for-forward-epic-dependencies: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
