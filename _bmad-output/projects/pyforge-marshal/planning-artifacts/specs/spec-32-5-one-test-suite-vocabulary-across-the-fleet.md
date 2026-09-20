---
title: '32.5: One test-suite vocabulary across the fleet'
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

**Problem:** One test-suite vocabulary across the fleet (contract recovered from epics.md Intent + ACs).

**Approach:** `src/shared/packages/pyforge-{steward,warden,marshal,herald,atlas}/tests/**`, `scripts/run_station_coverage_gate.py` (`_suite_test_paths`)

Ledger key: `32-5-one-test-suite-vocabulary-across-the-fleet`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: chore / L / S-32.1.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-108` ← `spec-fleet-consistency-standard CAP-2`.

## Acceptance Criteria

- Given eight suite names cover two concepts, and the coverage gate's suite map recognises neither spelling of `conformance` — leaving 51 real test files (steward 32, warden 19) measured by nothing, herald measured on 4 of 47 files and atlas on a fraction of 129 When each station converges on `unit/` + `integration/` + `meta/` — steward's CLI-contract conformance and marshal's `contract/` to `unit/`, warden's oracle conformance and marshal's `oracle/` to `integration/`, herald's 43 loose files to `unit/`, atlas's 15 loose files and 23 topic dirs to `unit/` with domain structure intact, and `marshal/support/` renamed `_support/` with its imports Then `_suite_test_paths` needs no per-station special case and every test file belongs to a measured suite And each station is a separate commit gated on its own suite passing — a green suite, never a reading of the diff — with `conftest.py` and `fixtures/` staying at each tests root so shared fixtures remain visible to both suites

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| eight suite names cover two concepts, and the coverage gate's suite map recognis | each station converges on `unit/` + `integration/` + `meta/` | `_suite_test_paths` needs no per-station special case and every test file belong | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 32.5 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `32-5-one-test-suite-vocabulary-across-the-fleet: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
