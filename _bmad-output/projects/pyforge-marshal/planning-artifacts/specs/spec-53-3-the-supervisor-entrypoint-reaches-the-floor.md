---
title: '53.3: The supervisor entrypoint reaches the floor'
type: 'chore'
created: '2026-09-20'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/coverage_thresholds.toml
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** As the operator who landed 53.2 behind a dated exception, I want `dispatch_supervisor/__main__.py` (623 statements, 388 uncovered, 35% on 2026-09-20; 36% on `main` before 53.2 touched 15 of its 1,895 lines) unit-covered to the 80% floor and the `[modules."pyforge.marshal.dispatch_supervisor.__main__"]` exception removed from `coverage_thresholds.toml`, So that Epic 53 closes with no named debt and the touched-module gate is whole again for marshal.

**Approach:** ports-driven unit tests of the supervisor's finalize / halt / land / completion sequences (the same fakes `test_dispatch_supervisor_*.py` already use), added until the gate reports ≥ 80%; then delete the exception entry. No production change unless a test proves a defect (which becomes its own finding).

Ledger key: `53-3-the-supervisor-entrypoint-reaches-the-floor`.
Ledger status (do not edit the ledger): `backlog`.

### Living CAP citations

- `spec-pyforge-marshal` CAP-264; the gate itself is `spec-pyforge-steward:CAP-153`.

## Acceptance Criteria

- Given the module sits at 35% behind a dated exception, When this story lands, Then `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` reports `pyforge.marshal.dispatch_supervisor.__main__` ≥ 80%.
- The `[modules."pyforge.marshal.dispatch_supervisor.__main__"]` entry is gone from `coverage_thresholds.toml` and the gate's OK line names no dated exception for marshal.
- `test_the_live_file_names_the_supervisor_exception_with_its_story` in `tests/unit/test_coverage_gate_module_floors.py` is retired with the entry (it pins the exception's presence, not its absence).

## Boundaries & Constraints

- Coverage comes from tests, never from excluding lines or lowering floors.
- The supervisor's process boundary is faked through its ports (`HarnessPort`, `VcsPort`, `ForgePort`); no live harness, no network.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary checkout's copy of this file).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass.

**Manual checks:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — the module ≥ 80%, no exception named.

</intent-contract>
