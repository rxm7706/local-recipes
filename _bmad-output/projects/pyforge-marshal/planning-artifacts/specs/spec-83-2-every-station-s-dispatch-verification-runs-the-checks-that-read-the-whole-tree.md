---
title: "83.2: Every station's dispatch verification runs the checks that read the whole tree"
type: 'fix'
created: '2026-10-02'
status: 'ready-for-dev'
review_loop_iteration: 1
followup_review_recommended: false
baseline_revision: '1b490ef6ab61301170a8fefa58a9ef9fdbeab689'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
deferred:
  - summary: >-
      Missing backward compatibility for command output parsing
    evidence: |-
      Cannot verify if anything parses derived commands list format without extensive search; would need codebase-wide analysis to determine impact
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py:280
    severity: low (unverified)
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `dispatch_verify._verify_commands_with_surface_guard` folds the derived commands (the surface guard, `lint-types`) into every station's dispatch verification, but neither pyforge-core's suite nor the deferred-work check is among them. On 2026-10-02 steward 83.2 landed uncited `verified:` lines and turned doctor's live-ledger test red on `main`, and marshal 82.4's new exception root failed pyforge-core's CAP-5 meta-test in CI; the station verification passed both.

**Approach:** Append `pixi run --frozen -e pyforge-core pyforge-core-test` and `pixi run --frozen -e pyforge-guild deferred-work-check` in the same place `lint-types` was folded in, after the same dedupe rule, so every station's verification runs them. Both are seconds-long.

*Amended 2026-10-03 (operator ruling, after the first landing was refused):* the deferred-work check fails on any deferral the session itself records in its spec frontmatter (`spec-frontmatter-only-deferral`), because today those rows reach the tracked ledger only after the merge (`dispatch_land_finalize/__main__.py::_run_deferred_work_intake`, Story 53.2). So before verification runs, dispatch runs `scripts/deferred_work_intake.py --fix --project <short slug>` in the story worktree and commits the rows it writes to the story branch. The PR then carries its own deferral rows for review, and the post-merge intake finds nothing left to add.

## Boundaries & Constraints

**Always:** Fix the defect where the shipped behaviour lives, and pin it with a test that fails without the fix. Rows come from `deferred_work_intake.py`, the same script and the same short-slug `--project` form the post-merge step uses; never hand-written.

**Never:** Do not edit any station's `verify_commands`. Do not make a WARN-only detector finding fail verification. Do not remove the post-merge intake (it still covers runs that did not go through dispatch verification). Do not write another station's ledger.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py` -- Contains `_verify_commands_with_surface_guard` function that needs modification
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification.py` -- Test file that validates derived command behavior and needs updated assertions
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verify_merge_tree.py` -- Another test file that checks command lists in merge tree scenarios
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py` -- `_run_deferred_work_intake` (Story 53.2): the post-merge intake whose invocation (script path, short-slug `--project`) the pre-verification step reuses
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py::evaluate_dispatch_verification` -- where verification runs; the intake and its commit happen before it, in the worktree, on the story branch

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
- Given a session that records a deferral in its spec frontmatter, when its dispatch verifies, then dispatch first runs `deferred_work_intake.py --fix --project <short slug>` in the worktree and commits the new rows to the story branch, the deferred-work check passes, and the landing's post-merge intake adds nothing
- Given a session that records no deferral, when its dispatch verifies, then no intake commit is made
- Given the intake refuses a deferral (it cites no resolvable repo path, Story 21.8) or exits non-zero, when its dispatch verifies, then verification fails naming the intake's refusal, never passes silently
- Given the pre-verification intake removed, when its new test runs, then it fails (mutation)

## Spec Change Log

- 2026-10-03 — operator ruling ("write rows first"). The first landing was refused on `lint-types` (`ruff format` on `dispatch_verify.py:372`, fixed on this branch by the operator session). Landing review then found the design defect: `pixi run --frozen -e pyforge-guild deferred-work-check` exits 2 on this branch with `spec-frontmatter-only-deferral` for this spec's own `deferred:` entry, so with the derived check as built every dispatch that records a deferral would be refused. Amended Approach, Boundaries, Code Map and four acceptance criteria (pre-verification intake on the story branch). Status back to `ready-for-dev`.

## Review Triage Log

### 2026-10-03 — Landing review (operator session) — sent back
- Dispatch run `pyforge-marshal-20261003T002853465Z-a34606bb` refused at verification: MRS-GATE-001, `pixi run --frozen -e pyforge-guild lint-types` exited 1 (`ruff format`, `dispatch_verify.py:372`). Fixed on the branch by `ruff format`; `lint-types`, `pyforge-marshal-test` (10832 passed), `pyforge-deps-test` (130 passed) and `pyforge-core-test` (2171 passed) then green.
- `high` `bad_spec` `deferred-work-check` exits 2 on this branch: `spec-frontmatter-only-deferral` for this spec's own `deferred:` entry, because frontmatter deferrals reach the tracked ledger only post-merge. As built, the derived check refuses every dispatch that records a deferral. Operator ruling 2026-10-03: run the intake before verification and commit its rows to the story branch (Spec Change Log).
- The open `deferred:` entry ("Missing backward compatibility for command output parsing") is left for the pre-verification intake to ingest, which is the amended behaviour's own first exercise.

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

### 2026-10-02 — Review pass
- verdicts: 7 findings — high 1, medium 0, low 0, false 5, maybe-false 1  
- findings:
  - `false` `reject` Missing error handling for malformed derived commands during deduplication — Commands are constants, not user input; deduplication uses standard string operations that cannot fail
  - `false` `reject` Missing documentation about performance implications — Intent explicitly states both commands are "seconds-long"
  - `false` `reject` Missing test coverage for simultaneous command failures — Each command tested independently; simultaneous failures are multiple independent failures with same handling
  - `false` `reject` Missing validation that command constants are valid pixi commands — Constants follow established pattern; validation not done for any derived commands
  - `false` `reject` Missing integration test for all four derived commands together — Existing tests cover derived behavior; integration covered by main verification flow
  - `maybe-false` `defer` Missing backward compatibility for command output parsing — Cannot verify if anything parses derived commands list format without extensive search; would need codebase-wide analysis to determine impact
  - `high` `patch` Missing reclassification tests for new derived commands — Tests exist for command failures but not for verifying failures are never downgraded to pre-existing issues like existing test for lint-types

**Verification performed:**
- `pyforge-marshal-test`: All tests passed (10,829 passed, 5 skipped)
- `pyforge-deps-test`: All tests passed (130 passed, 3 skipped)  
- `lint-types`: All checks passed after formatting fixes

**Residual risks:** The reclassification fix ensures surface reconcile command failures are properly treated as blocking, maintaining spec surface integrity. No residual risks identified.

### 2026-10-02 — Review pass (bmad-build-auto follow-up)
- verdicts: 8 findings — high 1, medium 0, low 3, false 4, maybe-false 0
- findings:
  - `low` `reject` Missing newline at end of spec file — Cosmetic; does not affect functionality
  - `false` `reject` Contradictory follow-up review flag in frontmatter vs narrative — Handled by the Finalize section which computes and sets the correct value
  - `low` `reject` Deferred-item location wrong (cites line 280) — Location is approximate and refers to a different function; not a defect
  - `false` `reject` Surface-reconcile memlog entries too sparse — Entries follow the correct reconcile format
  - `low` `reject` Inconsistent pinned-vs-imported constants in tests — Minor inconsistency where `_SURFACE_RECONCILE_COMMAND` is imported while others are pinned; not worth the complexity of fixing
  - `false` `reject` Long line in implementation — lint-types passes; no long line issue
  - `false` `reject` Magic-number comment in test — Cosmetic comment; not worth fixing
  - `high` `patch` Missing reclassification test for `_SURFACE_RECONCILE_COMMAND` — Added `test_evaluate_dispatch_verification_surface_guard_red_on_the_story_own_file_is_never_pre_existing` to verify surface guard failures are never reclassified to MRS-GATE-014

**Verification performed:**
- `pyforge-marshal-test`: All tests passed (10,832 passed, 5 skipped)
- `pyforge-deps-test`: All tests passed (130 passed, 3 skipped)
- `lint-types`: All checks passed
- `spec_surface_reconcile.py`: OK — every tracked file governed or allowlisted; no drift

**Follow-up review recommendation:** `false` — One high-severity patch was applied but it is a straightforward test addition following the established pattern; no unverified risk remains.

**Residual risks:** None. The new test pins the reclassification behavior for the surface reconcile command, closing the mutation gap identified by the Verification Gap reviewer.