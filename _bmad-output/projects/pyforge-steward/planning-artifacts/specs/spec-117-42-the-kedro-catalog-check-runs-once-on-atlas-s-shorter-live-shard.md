---
title: '117.42: The kedro catalog check runs once, on atlas''s shorter live shard'
type: 'chore'
created: '2026-11-28'
status: 'in-progress'
story: 117-42-the-kedro-catalog-check-runs-once-on-atlas-s-shorter-live-shard
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '.github/workflows/pyforge-station-tests.yml'
  - 'docs/reference/github-workflows.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `atlas-test` is the longest station job on most pull requests that run atlas (99 to 105 s on PR #2446), and it runs as three shards. Each shard ends with `pixi run -e pyforge-atlas kedro-catalog-check`, 7 s, so the same check runs three times and lengthens every shard.

**Approach:** move the step to `atlas-live-test` and run it on that job's second shard only (`if: matrix.group == '2'`). That shard was the live half's shorter one on PR #2446 (76 s against 87 s). Atlas's live half fires on every path its package half fires on (its paths hold `src/shared/packages` and the shared surface; the package half's hold `src/shared/packages/pyforge-atlas` and the shared surface), so the check runs on every run it ran on before, once. `kedro-catalog-check` is not a local preflight lane, so the local preflight is unchanged.

Ledger key: `117-42-the-kedro-catalog-check-runs-once-on-atlas-s-shorter-live-shard`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- The check runs on every run that runs atlas's package half.

**Never:**
- Never drop the check or change what it checks.

## Acceptance Criteria

**Given** a run that runs atlas
**When** its shards run
**Then** `kedro-catalog-check` runs once, on `atlas-live-test (2)`, and no `atlas-test` shard runs it
**And** every run that runs atlas's package half runs the check

- **AC1 — This pull request.** Its run shows the check in `atlas-live-test (2)` alone, passing.
- **AC2 — The rule.** `tests/scripts/test_station_tests_shard_counts.py` holds the check to one step, in `atlas-live-test`, on a shard that both modes start.

</intent-contract>
