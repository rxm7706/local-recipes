---
title: '32.4: No artifact survives that the toolchain no longer produces'
type: 'chore'
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

**Problem:** No artifact survives that the toolchain no longer produces (contract recovered from epics.md Intent + ACs).

**Approach:** `_bmad-output/projects/pyforge-*/planning-artifacts/epics-with-stories.md` (×8), `src/shared/packages/pyforge-doctor/src/pyforge/doctor/hygiene_definitions.py`, `.../doctor/sources/deps.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py`, `_bmad/scripts/bmad_tea_playwright.py`, the station `README.md` files that reference it

Ledger key: `32-4-no-artifact-survives-that-the-toolchain-no-longer-produces`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-109` ← `spec-fleet-consistency-standard CAP-3`.

## Acceptance Criteria

- Given `epics-with-stories.md` appears nowhere in BMAD 6.12, is frozen at 2026-08-08 in six of eight stations while `epics.md` moved to 2026-09-06, and has no consumer that requires it — two exclude it explicitly as a derived summary, one is an inert allowlist entry, one reads it only as a fallback When all eight are audited for normative content, anything found is rehomed to the standard first (steward's suite-shape mandate at its line 61 is known; the other seven are unaudited), and only then are the files and their four code references removed Then no station README points at one, `pyforge-doctor` and `pyforge-marshal` suites stay green, and nothing normative was lost with the file And the audit is a gate, not a formality — steward's mandate was found by accident, which is the entire reason this story reads all eight before deleting any

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `epics-with-stories.md` appears nowhere in BMAD 6.12, is frozen at 2026-08-08 in | all eight are audited for normative content, anything found  | no station README points at one, `pyforge-doctor` and `pyforge-marshal` suites s | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 32.4 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `32-4-no-artifact-survives-that-the-toolchain-no-longer-produces: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
