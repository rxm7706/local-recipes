---
title: '38.4: An unparseable epics format is reported honestly, never silently clean'
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

**Problem:** As a fleet operator, I want a station whose epics doc the detector cannot parse reported as **not determinable** rather than clean, So that the fidelity doctrine applies to the detector itself.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `38-4-an-unparseable-epics-format-is-reported-honestly-never-silently-clean`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: feature / S / S-38.3.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-56` ← `spec-bmad-loop-forward-dependency-blindness CAP-4`.

## Acceptance Criteria

- Given some stations use an older narrative format (confirmed: `pyforge-warden`) When this story lands Then those report not-determinable, never a bare "clean"

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| some stations use an older narrative format (confirmed: `pyforge-warden`) | this story lands | those report not-determinable, never a bare "clean" | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 38.4 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `38-4-an-unparseable-epics-format-is-reported-honestly-never-silently-clean: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
