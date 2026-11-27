---
title: '117.33: Herald''s live half runs as four shards'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 117-33-herald-s-live-half-runs-as-four-shards
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '.github/workflows/pyforge-station-tests.yml'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `herald-live-test` runs three shards, split by pytest-split from `tests/durations/pyforge-herald.json`, which holds laptop timings. On the runner, herald's built-site tests cost two to three times those timings, so the three shards are equal only on a laptop. On PR #2436 the job took 111 s, the longest on that PR. By every test's runner time, printed by probe run 46072884555 (never merged), the third shard held about 215 s of tests for four xdist workers, against 184 s and 137 s, and took 66 to 72 s of tests where the others took 38 to 53 s.

**Approach:** the job's matrix runs groups 1 to 4 with `--splits 4`. With herald Story 63.1, which keeps a self-building test out of `test_site_shell.py`'s `shell` group (55 s alone), the runner times put at most about 150 s of tests in a shard and no xdist group above 40 s. The coverage gate already merges `herald-live*.json` by pattern, so it reads the fourth report unchanged.

Ledger key: `117-33-herald-s-live-half-runs-as-four-shards`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- The same tests run, each in one shard.

**Never:**
- Never change what a test asserts, or the coverage floors.

## Acceptance Criteria

**Given** a PR that runs herald's live half
**When** CI runs it
**Then** four shards run, every test once, and the gate passes on their merged reports

- **AC1 — The four groups hold every collected test once.** Run pytest-split's chunking over the collected live half with `--splits 4` (as in the Result below); expected: the groups' union is the collection and no test is in two.

- **AC2 — The durations-file and workflow tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_durations_files.py -q
  ```

</intent-contract>

## Result (2026-11-27)

- By the probe run's runner times over pytest-split's own chunking of the 839 collected tests, the four shards hold 150, 110, 126 and 151 s of tests, with xdist groups of at most 24.8, 35.0, 14.9 and 39.2 s. Three shards held 184, 137 and 215 s.
