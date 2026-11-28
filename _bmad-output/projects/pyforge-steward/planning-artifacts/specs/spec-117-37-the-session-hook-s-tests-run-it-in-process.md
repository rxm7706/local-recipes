---
title: '117.37: The session hook''s tests run it in-process'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 117-37-the-session-hook-s-tests-run-it-in-process
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'tests/scripts/test_pre_shell_hook.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - .claude/hooks/pre-shell.py
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `tests/scripts/test_pre_shell_hook.py` runs `.claude/hooks/pre-shell.py` in a new interpreter for each of about 600 calls. Each takes 57 ms, against 4 ms for the same compiled script run in-process with a fresh module. The file took 62.2 s serially, in the Detectors job's stdlib part and the local preflight's `pyforge-doctor-scripts-test` lane (118 s at two workers).

**Approach:** `_run` runs the hook in-process, giving each call what a fresh process gets:
- a new `__main__` module from the compiled script (compiled once per path), so no cache survives a call;
- the call's cwd, environment, stdin and `argv`, with the script's directory first on `sys.path`;
- its exit code from the script's own `__main__` block: `sys.exit(main())`, or 2 from its exception handler;
- stdout and stderr captured.

Afterwards the cwd, environment, `sys.path`, `argv`, stdin and `sys.modules` are restored, and modules the call imported are dropped. `_run_process` keeps the real interpreter. `test_in_process_runs_match_the_real_process` holds the two to each other.

Ledger key: `117-37-the-session-hook-s-tests-run-it-in-process`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (realized, no text change); works with CAP-5 (the session hook).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Every existing test keeps its result; the hook does not change.

**Never:**
- Never drop a case or weaken an assertion.

## Acceptance Criteria

**Given** the hook's test file
**When** `_run` runs the hook in-process
**Then** every test passes, and the parity test finds each kind of result the same as the real interpreter gives (exit code, stdout, stderr)
**And** the file runs in well under half its former time

- **AC1 — The file passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_pre_shell_hook.py -q
  ```

</intent-contract>

## Result (2026-11-27)

- Serially, the file ran 597 tests in 62.2 s on `main` and runs 598 in 24.1 s here; the added test is the parity test.
- The parity test covers a Claude deny and a Cursor deny, an allow, a Cursor warning (exit 1), an environment-dependent deny, a worktree commit, a hook copy's own roster, and the exit-2 failure.
