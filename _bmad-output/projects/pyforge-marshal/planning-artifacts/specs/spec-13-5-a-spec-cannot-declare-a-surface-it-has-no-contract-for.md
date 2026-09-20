---
title: '13.5: A Spec cannot declare a surface it has no contract for'
type: 'change'
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

**Problem:** As the operator, I want a governed Spec with no `.memlog.md` reported by name, So that a surface whose contract can never move stops passing as green.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `13-5-a-spec-cannot-declare-a-surface-it-has-no-contract-for`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: change / M / S-13.1, S-13.2.

### Living CAP citations

- Cited from epics.md: FR-168

## Acceptance Criteria

- Given a spec that governs ≥1 tracked file under the default `surface-drift: memlog` mode When its `.memlog.md` does not exist Then a gating `[drift-blind]` finding names the spec, its governed-file count, and the path the memlog belongs at — because `contract_hash()` returns `""`, so the contract can never move and the "reconcile the spec" remedy the detector prints is unreachable And a spec governing zero files, a `surface-drift: exempt` spec, and a `surface-drift: sentinel:<path>` spec each report nothing — none of them can go blind And `[drift-blind]` gates even though `[drift-presumed]` does not: presumed reconciliation is *unproven* over historical entries nobody can retro-name, blindness is *structurally impossible* and clears by creating one file And the detector never creates the memlog it checks for — a self-clearing finding is not a finding, and it would author a decision record nobody decided And the 7 live instances (396 governed files: mason/spec-conda-forge-expert-rebuild 370, herald/spec-herald-moments-2-4-live-backend 18, four marshal specs 7, steward/spec-unified-container 1) are dispositioned by writing each memlog and scoped-stamping its baseline in the same change — a new memlog moves the contract hash off `""`, so stamping later would silently downgrade that spec's next drift from gating `[drift]` to informational `[drift-presumed]` And a before/after finding diff proves no `[drift]` became `[drift-presumed]` as a side effect of the seven memlogs And a mutation test proves the guard both ways: deleting a governed fixture's memlog reds the new test, and removing the check re-greens it

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| a spec that governs ≥1 tracked file under the default `surface-drift: memlog` mo | its `.memlog.md` does not exist | a gating `[drift-blind]` finding names the spec, its governed-file count, and th | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 13.5 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `872ebfb066` (2026-08-08, "marshal 13.5: a Spec cannot declare a surface it has no contract for"). Ledger row `13-5-a-spec-cannot-declare-a-surface-it-has-no-contract-for: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py`, `_bmad-output/projects/pyforge-atlas/planning-artifacts/sprint-status-ledger.yaml`, `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-herald-moments-2-4-live-backend/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-dashboard-project-path-derivation/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-dream-to-code-model-self-verification/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-sprint-status-auto-promote/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-surface-drift-reconciliation/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-surface-drift-reconciliation/SPEC.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml` (+6 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
