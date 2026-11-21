---
title: '129.1: A killed test run leaves no stand-in server behind'
type: 'fix'
created: '2026-11-21'
status: 'done'
story: 129-1-a-killed-test-run-leaves-no-stand-in-server-behind
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - 'src/shared/packages/pyforge-steward/tests/**'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The platform-ci-local tests' stand-in `postgres` and `redis-server` exec `sleep 999999` in a session of their own, so a test process killed before its teardown leaves them alive for about 11.5 days, and a later preflight's steward lane waited over an hour on them.

**Approach:** Each stand-in sleeps a bounded lifetime (`PLATFORM_CI_STUB_LIFETIME_S`, 600 s by default) instead.

Ledger key: `129-1-a-killed-test-run-leaves-no-stand-in-server-behind`.

### Living CAP citations

- spec-pyforge-steward CAP-175 (realized, no text change); FR-49 ← CAP-175; no AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never signal a process the test did not start, sweep another session's stand-ins, or change `scripts/platform-ci-local.sh`.

## Acceptance Criteria

**Given** the platform-ci-local tests' stand-in `postgres` and `redis-server` exec `sleep 999999` in a session of their own, so a test process killed before its teardown leaves them alive for about 11.5 days, and a later preflight's steward lane waited over an hour on them
**When** each stand-in sleeps a bounded lifetime (`PLATFORM_CI_STUB_LIFETIME_S`, 600 s by default) instead
**Then** a stand-in nobody stops exits by itself after its lifetime, a test proves it for both stand-ins, and every existing start/stop and no-survivor test still passes
**And** steward's live-tree half passes

- **AC1 — The story's own check passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-175 (realized, no text change); FR-49 ← CAP-175; no AD moves.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the third 2026-11-21 entry; operator, 2026-11-21: "Yes, fix it here".
- Epic: Epic 129, minted with this story.
- Ledger key: `129-1-a-killed-test-run-leaves-no-stand-in-server-behind` (`done`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."129"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-21: minted from the station Dream's entry and the operator, 2026-11-21: "Yes, fix it here"; done on branch `platform-ci-local-test-leak-2026-11-21`.
