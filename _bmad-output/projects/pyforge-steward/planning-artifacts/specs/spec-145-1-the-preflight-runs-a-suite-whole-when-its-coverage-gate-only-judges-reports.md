---
title: '145.1: The preflight runs a suite whole when its coverage gate only judges reports'
type: 'fix'
created: '2026-11-26'
status: 'done'
story: 145-1-the-preflight-runs-a-suite-whole-when-its-coverage-gate-only-judges-reports
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_suite_reduction.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_preflight_suite_reduction.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** A full preflight of a change that touches `pyforge.mason.cli` reds mason's coverage gate at 34.3%; the suite run whole gives 99.2%. The gate, with `--report`, judges the reports the station's test lanes wrote and runs no test. The suite reduction assumes the gate runs the unit tests, reduces the package half to the complement of that run (nothing), and the empty lane writes the report the gate judges.

**Approach:** In `build_suite_lane_overrides`, do not reduce a suite whose gate command carries `--report`; journal the reason. Decide from the gate's own command, before asking it for a plan. Keep the reduction for a gate that runs its own tests. Hold with a test that every station gate in `pixi.toml` carries `--report` today.

Ledger key: `145-1-the-preflight-runs-a-suite-whole-when-its-coverage-gate-only-judges-reports`.

### Living CAP citations

- spec-pyforge-steward CAP-159 (the pr-preflight; realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never lower a coverage floor or exempt a module to clear the red.
- Never remove the reduction for a gate that runs its own tests.

## Acceptance Criteria

**Given** a gate that judges the suite's reports and a suite lane reduced as if the gate ran the tests
**When** the preflight plans a suite lane whose gate command carries `--report`
**Then** the lane runs whole and its journal says why
**And** a gate without `--report` is reduced as before

- **AC1 — The reduction's tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_preflight_suite_reduction.py -q -m live_tree
  ```

- **AC2 — A full preflight of a change touching `pyforge.mason.cli` passes mason's coverage gate.** Expected: exit 0.

  ```bash
  PYFORGE_PREFLIGHT_SCOPE=full pixi run --frozen -e pyforge-guild pr-preflight
  ```

</intent-contract>

## Evidence (2026-11-26)

Two full preflights of the JSON-output change failed on `pyforge-mason-coverage-gate`: "pyforge.mason.cli: 34.3% (threshold 80% unit)". In each, `pyforge-mason-test` logged "1802 deselected" and then a `--collect-only` run, and `mason-unit.json` held 13.2% for the module. Run by hand, `pyforge-mason-test` then `pyforge-mason-live-test` then `pyforge-mason-coverage-gate` exit 0, with the module at 99.2%.
