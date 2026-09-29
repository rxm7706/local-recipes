---
title: The local-recipes empty-plan oracle
type: test
created: '2026-08-23'
status: done
review_loop_iteration: 1
followup_review_recommended: true
context:
  - '{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md'
warnings: []
deferred:
  - summary: >-
      K-02: local-recipes is not genesis-aligned — adopt dry-run yields 21
      filtered actions (managed regions absent, no seed-state, first-claim
      pending). Slow oracle fails until bootstrap adopt lands.
    evidence: |-
      pixi run --frozen -e pyforge-marshal pyforge-marshal-test-slow -k
      test_local_recipes → AssertionError, 21 actions (claude-skills excluded).
    severity: high
baseline_revision: 52989ec5545eed357a86101e94d94b8ed640aac7
---

<intent-contract>

## Intent

**Problem:** The shipped Genesis model manifest must stay aligned with the `local-recipes` repo it was extracted from; drift should fail Genesis's build the day it appears (SC-02, NFR-M2, AD-60).

**Approach:** Add `tests/oracle/test_local_recipes_empty_plan.py` under pyforge-marshal that runs `marshal seed adopt --dry-run` against the repo root and asserts zero actions. Exclude `unclassified-deferred` artifacts explicitly; document any required special-casing — if special-casing is needed to reach empty, trigger kill criterion K-02 and escalate.

## Acceptance Criteria

- Given `local-recipes` at the shipped model version, `marshal seed adopt --dry-run` yields a plan with **zero actions** (SC-02).
- Test runs in Genesis's own CI (pyforge-marshal-test / platform CI path).
- Non-empty plan fails with a readable diff naming diverged artifacts.
- Test asserts on model manifest artifacts only — resilient to mutable repo volume (recipe counts, dashboard state).
- `unclassified-deferred` artifacts excluded from assertion; exclusion explicit in test code.
- Any special-casing documented in test/module; K-02 escalation if empty plan unreachable without incoherent special-casing.

## Boundaries & Constraints

**Never:** Assert on repo volume metrics (recipe counts, project counts, dashboard state). Do not work around K-02 with silent special-casing.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/tests/oracle/test_local_recipes_empty_plan.py`
- Existing `marshal seed adopt --dry-run` CLI surface

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- Oracle test green against current repo checkout

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 1: (high 1)
- reject: 0
- addressed_findings:
  - none

## Auto Run Result

Status: done

**Summary:** Added `tests/oracle/test_local_recipes_empty_plan.py` (SC-02): unit tests for explicit `unclassified-deferred` exclusion and readable plan diff; `@pytest.mark.slow` integration test runs `run_adopt` dry-run against the monorepo root. Default `pyforge-marshal-test`: 5312 passed. Slow oracle: **fails K-02** — 21 filtered actions until local-recipes genesis bootstrap.

**Verification:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` → 5312 passed, 10 deselected. `pyforge-marshal-test-slow -k test_local_recipes` → fails (21 actions; K-02 deferred).
