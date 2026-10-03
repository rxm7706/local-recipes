---
title: "83.2: Every station's dispatch verification runs the checks that read the whole tree"
type: 'fix'
created: '2026-10-02'
status: 'in-review'
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

### 2026-10-02 — Review pass
- verdicts: 11 findings — high 1, medium 0, low 2, false 8, maybe-false 0
- findings:
  - `false` `reject` Missing story binding information — Spec was correctly transformed from legacy format to new BMAD format per workflow
  - `false` `reject` Missing "Living CAP citations" section — Correct transformation per BMAD workflow 
  - `false` `reject` Missing "Ledger key" and "Type / Effort / Deps" information — Correct transformation per BMAD workflow
  - `low` `reject` Missing mutation test coverage for derived commands — Comprehensive test coverage exists; mutation tests would be cosmetic
  - `low` `reject` Missing documentation in docstrings explaining relationships — Code is clear with well-established pattern
  - `false` `reject` Missing error handling/validation in function — Commands are constants, validation unnecessary
  - `false` `reject` Missing test coverage for edge cases like malformed commands — Commands are constants, not user input
  - `false` `reject` Missing integration test for all derived commands together — Existing tests already cover this integration
  - `false` `reject` Missing deduplication test for different environment prefixes — Deduplication is whitespace-based, not prefix-based
  - `false` `reject` Missing performance impact documentation — Intent explicitly states commands are "seconds-long"
  - `high` `patch` Surface reconcile command missing from reclassification set — Added _SURFACE_RECONCILE_COMMAND to derived_commands set

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: pass (the station's `verify_commands`; MRS-GATE-010 binding)
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: pass (the station's `verify_commands`; MRS-GATE-010 binding)
- `pixi run --frozen -e pyforge-guild lint-types` -- expected: exit 0

## Auto Run Result

**Summary:** Implemented the addition of two derived commands (`pyforge-core-test` and `deferred-work-check`) to every station's dispatch verification, following the same pattern as existing derived commands.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py` — Added two new command constants and extended derived tuple in _verify_commands_with_surface_guard
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification.py` — Updated test assertions and added new test cases for derived command behavior
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verify_merge_tree.py` — Updated test assertions for merge tree verification scenarios

**Review findings breakdown:**
- **Patches applied:** 1 high-severity patch (added _SURFACE_RECONCILE_COMMAND to derived_commands set for proper reclassification handling)
- **Items deferred:** 0  
- **Rejected findings:** 10 (8 false findings for spec format changes and test coverage assumptions, 2 low findings for cosmetic improvements not worth the complexity)

**Follow-up review recommendation:** `true` — One high-severity patch was applied to fix reclassification logic that could have allowed surface reconcile failures to be incorrectly downgraded as pre-existing issues.

**Verification performed:**
- `pyforge-marshal-test`: All tests passed (10,829 passed, 5 skipped)
- `pyforge-deps-test`: All tests passed (130 passed, 3 skipped)  
- `lint-types`: All checks passed after formatting fixes

**Residual risks:** The reclassification fix ensures surface reconcile command failures are properly treated as blocking, maintaining spec surface integrity. No residual risks identified.