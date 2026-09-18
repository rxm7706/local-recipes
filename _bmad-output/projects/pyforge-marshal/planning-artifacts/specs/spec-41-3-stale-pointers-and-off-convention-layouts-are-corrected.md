---
title: '41.3: Stale pointers and off-convention layouts are corrected'
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

**Problem:** As a fleet operator, I want the `PROJECTS.md` Dream pointers, CLAUDE.md's sync-section path, and two off-convention directory shapes fixed, So that content that is correct stops being reached by a wrong name or path.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `41-3-stale-pointers-and-off-convention-layouts-are-corrected`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: docs / M / S-41.1.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-73` ← `spec-bmad-output-hygiene CAP-7`.

## Acceptance Criteria

- Given two `PROJECTS.md` Dream pointers resolved to a renamed or deleted file, CLAUDE.md named a stale `local-recipes` path, marshal's brief sat loose, and herald's brief/ architecture dirs carried a retired slug When this story lands Then both Dream pointers resolve to an existing `type: dream` file And CLAUDE.md matches where `bmad_drift_check.py`/`pixi.toml`/`fleet_scan` actually read from And marshal's brief is sharded to `briefs/brief-pyforge-marshal-2026-07-25/brief.md` and herald's dirs carry the station slug

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| two `PROJECTS.md` Dream pointers resolved to a renamed or deleted file, CLAUDE.m | this story lands | both Dream pointers resolve to an existing `type: dream` file | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 41.3 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.
