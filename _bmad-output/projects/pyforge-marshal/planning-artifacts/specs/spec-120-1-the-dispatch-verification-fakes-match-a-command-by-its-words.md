---
title: '120.1: The dispatch-verification fakes match a command by its words'
type: 'fix'
created: '2026-11-21'
status: 'done'
story: 120-1-the-dispatch-verification-fakes-match-a-command-by-its-words
spec: spec-pyforge-marshal
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - 'src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification_live_tree.py'
  - 'src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_environment_yaml.py'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `CrossSurfaceProcess` in `test_dispatch_verification_live_tree.py` counts a command as a platform, bmad-estate or flag-gate run when the joined command line merely contains `platform-ci-local`, `bmad-estate-check` or `flag-gate-check`, so a worktree whose path holds one of those words (the interpreter's path is a token) reds six cross-surface tests, and the environment-yaml fake in `test_dispatch_environment_yaml.py` matches `steward` and `provision` the same way.

**Approach:** Each fake matches its command by a whole token of the command (`platform-ci-local` in the token list), never by a substring of the joined line.

Ledger key: `120-1-the-dispatch-verification-fakes-match-a-command-by-its-words`.

### Living CAP citations

- spec-pyforge-marshal CAP-170 (realized, no text change); a fix, no new CAP.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never change marshal's dispatch code, or stop counting a real invocation.

## Acceptance Criteria

**Given** `CrossSurfaceProcess` in `test_dispatch_verification_live_tree.py` counts a command as a platform, bmad-estate or flag-gate run when the joined command line merely contains `platform-ci-local`, `bmad-estate-check` or `flag-gate-check`, so a worktree whose path holds one of those words (the interpreter's path is a token) reds six cross-surface tests, and the environment-yaml fake in `test_dispatch_environment_yaml.py` matches `steward` and `provision` the same way
**When** each fake matches its command by a whole token of the command (`platform-ci-local` in the token list), never by a substring of the joined line
**Then** the cross-surface and environment-yaml tests pass in a worktree whose path names those commands, and still count every real invocation
**And** marshal's suite passes

- **AC1 — The story's own check passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-marshal pyforge-marshal-live-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-marshal CAP-170 (realized, no text change); a fix, no new CAP.
- Dream: `docs/dreams/pyforge-marshal.md`, the second 2026-11-21 entry under *A stranger reads the chain*; operator, 2026-11-21: "Yes, fix it here".
- Epic: Epic 120, minted with this story.
- Ledger key: `120-1-the-dispatch-verification-fakes-match-a-command-by-its-words` (`done`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."120"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-21: minted from the station Dream's entry and the operator, 2026-11-21: "Yes, fix it here"; found when a worktree named `platform-ci-local-test-leak-2026-11-21` reddened six cross-surface tests; done on that branch.
