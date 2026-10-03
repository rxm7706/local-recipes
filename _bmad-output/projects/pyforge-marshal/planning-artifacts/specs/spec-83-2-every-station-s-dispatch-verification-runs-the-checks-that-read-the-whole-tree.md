---
title: "83.2: Every station's dispatch verification runs the checks that read the whole tree"
type: 'fix'
created: '2026-10-02'
status: 'in-progress'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '1b490ef6ab61301170a8fefa58a9ef9fdbeab689'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `dispatch_verify._verify_commands_with_surface_guard` folds the derived commands (the surface guard, `lint-types`) into every station's dispatch verification, but neither pyforge-core's suite nor the deferred-work check is among them. On 2026-10-02 steward 83.2 landed uncited `verified:` lines and turned doctor's live-ledger test red on `main`, and marshal 82.4's new exception root failed pyforge-core's CAP-5 meta-test in CI; the station verification passed both.

**Approach:** Append `pixi run --frozen -e pyforge-core pyforge-core-test` and `pixi run --frozen -e pyforge-guild deferred-work-check` in the same place `lint-types` was folded in, after the same dedupe rule, so every station's verification runs them. Both are seconds-long.

## Boundaries & Constraints

**Always:** Fix the defect where the shipped behaviour lives, and pin it with a test that fails without the fix.

**Never:** Do not edit any station's `verify_commands`. Do not make a WARN-only detector finding fail verification.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py` -- Contains `_verify_commands_with_surface_guard` function that needs modification
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification.py` -- Test file that validates derived command behavior and needs updated assertions
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verify_merge_tree.py` -- Another test file that checks command lists in merge tree scenarios

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py` -- Add two new command constants and extend the `derived` tuple in `_verify_commands_with_surface_guard` to include pyforge-core-test and deferred-work-check -- Fixes the core defect where station dispatch verification was missing these critical checks
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification.py` -- Update test assertions to expect the two new commands in the verification command lists -- Ensures tests reflect the new behavior and catch regressions
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verify_merge_tree.py` -- Update test assertions to include the new commands in expected command sequences -- Maintains test coverage for merge tree verification scenarios

**Acceptance Criteria:**
- Given a story whose change fails pyforge-core's suite, when its dispatch verifies, then verification fails and the landing is refused
- Given a story whose change adds an uncited post-cutoff verified: line, when its dispatch verifies, then verification fails
- Given a story that breaks neither, when its dispatch verifies, then it lands as today
- Given either command removed from the guard, when its new test runs, then it fails (mutation)

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: pass (the station's `verify_commands`; MRS-GATE-010 binding)
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: pass (the station's `verify_commands`; MRS-GATE-010 binding)
- `pixi run --frozen -e pyforge-guild lint-types` -- expected: exit 0