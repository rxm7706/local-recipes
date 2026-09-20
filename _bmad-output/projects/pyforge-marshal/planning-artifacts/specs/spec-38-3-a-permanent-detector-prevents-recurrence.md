---
title: '38.3: A permanent detector prevents recurrence'
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

**Problem:** As a fleet operator, I want a later-added unmarked forward dependency caught in CI, So that recurrence costs a red check rather than a burned dev attempt plus review cycles.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `38-3-a-permanent-detector-prevents-recurrence`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: feature / S / S-38.2.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-55` ← `spec-bmad-loop-forward-dependency-blindness CAP-3`.

## Acceptance Criteria

- Given the failure mode was discovered by burning compute When this story lands Then the detector self-registers (`detectors.py:227` → `("forward-dependency", "forward-dependency-check")`) and fails if a forward-dependent story is still `backlog` or `ready-for-dev` And it still reports on a red run, not only a green one

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the failure mode was discovered by burning compute | this story lands | the detector self-registers (`detectors.py:227` → `("forward-dependency", "forwa | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 38.3 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `38-3-a-permanent-detector-prevents-recurrence: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
