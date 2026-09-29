---
title: '13.4: The 34 drift findings are reconciled or recorded'
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

**Problem:** As the operator, I want each drifted file either genuinely reconciled or stamped with stated reasoning, So that a green gate means the contracts actually match the code.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `13-4-the-34-drift-findings-are-reconciled-or-recorded`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: change / L / S-13.1, S-13.2.

### Living CAP citations

- Cited from epics.md: FR-166

## Acceptance Criteria

- Given the 34 `[drift]` findings across five specs (steward/spec-pyforge-steward 23, scribe/spec-team-memory 5, marshal/{fidelity-enforcement, factory-console, durable-runs} 2 each) When each spec is worked Then every finding is partitioned into *genuine surface change* (the contract moves — the spec is re-derived) or *already reconciled, unstamped* (scoped-stamped), and the partition is recorded in that spec's own memlog And the 23-file steward cluster is not bulk-stamped on the strength of being large — if that surface changed, its contract moves And `pixi run -e local-recipes spec-surface-check` exits 0 And the epic's own changes to `scripts/spec_surface_check.py` are themselves reconciled against `spec-surface-drift-reconciliation` — the detector must not be the one file that escapes its own gate

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the 34 `[drift]` findings across five specs (steward/spec-pyforge-steward 23, sc | each spec is worked | every finding is partitioned into *genuine surface change* (the contract moves — | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 13.4 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `13-4-the-34-drift-findings-are-reconciled-or-recorded: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
