---
title: '117.43: Platform CI''s test job restores the warden environment from the pixi cache'
type: 'chore'
created: '2026-11-28'
status: 'in-progress'
story: 117-43-platform-ci-s-test-job-restores-the-warden-environment-from-the-pixi-cache
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '.github/actions/platform-test-setup/action.yml'
  - '.github/workflows/platform-ci.yml'
  - 'docs/reference/github-workflows.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
  - src/platform/conftest.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Platform CI's golden-path and warden tests run `pixi run -e pyforge-warden`. The session fixture `pyforge_warden_env` (Story 117.23) installs that environment first, one worker at a time under a lock, because the test job's setup installs only `platform-ci-test`. On PR #2446 the shard that held those tests ran 129 s against 109 s for the other two: each of its four workers waited 13 to 25 s, at its first such test, for the one install.

**Approach:** the `platform-test-setup` action takes two inputs, the environments to install and the cache key's prefix, whose defaults are today's (`platform-ci-test`, `platform-ci-test-`). The test job passes `platform-ci-test pyforge-warden` and its own prefix, so setup-pixi restores both environments from one cache entry, written on a push to `main` as today. The `checks` job keeps the defaults. The fixture stays: with the environment installed, its `pixi install` returns at once, and a run whose cache has no entry yet still installs it safely.

Ledger key: `117-43-platform-ci-s-test-job-restores-the-warden-environment-from-the-pixi-cache`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- The `checks` job's setup and cache entry are unchanged.
- `platform-ci-test` stays the activated environment.

**Never:**
- Never remove the fixture's install or its lock.

## Acceptance Criteria

**Given** a Platform CI test shard that runs the golden-path tests
**When** its setup has installed `pyforge-warden`
**Then** no worker waits on an install at its first warden test
**And** the suite runs and passes as before

- **AC1 — This pull request.** Platform CI's test job passes on every shard.
- **AC2 — A push to `main`.** The test job writes its cache entry; the next run's shards restore it and their longest per-worker gap at a warden test falls below 5 s.

</intent-contract>
