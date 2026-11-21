---
title: '119.1: A challenge run past its ceiling is checked without a race'
type: 'fix'
created: '2026-11-21'
status: 'done'
story: 119-1-a-challenge-run-past-its-ceiling-is-checked-without-a-race
spec: spec-pyforge-marshal
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - 'src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `test_a_session_past_its_ceiling_exits_1_with_outcome_error` reads the pid file its fake session writes as its first line, and on a loaded machine the 1.5 s ceiling can kill the session before that line runs, so the read raises `FileNotFoundError` though the kill worked.

**Approach:** The test waits a bounded time for the pid file, checks that a session which wrote it is dead, and counts a session that never wrote it as killed before its first line.

Ledger key: `119-1-a-challenge-run-past-its-ceiling-is-checked-without-a-race`.

### Living CAP citations

- spec-pyforge-marshal CAP-298 (FR-240; realized, no text change); a fix, no new CAP.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never let a session that outlives its ceiling pass, or change the challenge runner's code.

## Acceptance Criteria

**Given** `test_a_session_past_its_ceiling_exits_1_with_outcome_error` reads the pid file its fake session writes as its first line, and on a loaded machine the 1.5 s ceiling can kill the session before that line runs, so the read raises `FileNotFoundError` though the kill worked
**When** the test waits a bounded time for the pid file, checks that a session which wrote it is dead, and counts a session that never wrote it as killed before its first line
**Then** the test passes under load as it does alone, a session that outlives its ceiling still fails it, and no other test changes
**And** marshal's suite passes

- **AC1 — The story's own check passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-marshal pyforge-marshal-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-marshal CAP-298 (FR-240; realized, no text change); a fix, no new CAP.
- Dream: `docs/dreams/pyforge-marshal.md`, the 2026-11-21 entry under *A stranger reads the chain*; operator, 2026-11-21: "fix the marshal flaky test too".
- Epic: Epic 119, minted with this story.
- Ledger key: `119-1-a-challenge-run-past-its-ceiling-is-checked-without-a-race` (`done`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."119"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-21: minted from the station Dream's 2026-11-21 entry and the operator, 2026-11-21: "fix the marshal flaky test too"; done on branch `corridor-platform-host-2026-11-21` (PR #2375).
