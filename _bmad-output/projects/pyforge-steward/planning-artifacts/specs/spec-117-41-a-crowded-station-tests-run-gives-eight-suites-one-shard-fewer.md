---
title: '117.41: A crowded station-tests run gives eight suites one shard fewer'
type: 'chore'
created: '2026-11-28'
status: 'in-progress'
story: 117-41-a-crowded-station-tests-run-gives-eight-suites-one-shard-fewer
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '.github/workflows/pyforge-station-tests.yml'
  - 'docs/reference/github-workflows.md'
  - 'tests/scripts/test_station_tests_shard_counts.py'
  - 'tests/meta/scripts-lib-test.txt'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
  - tests/durations/README.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** the account runs at most 40 GitHub Actions jobs at once. A pull request that runs every station (15 of the last 40 station-tests runs on pull requests) starts 37 station test jobs beside about 11 from the other workflows (Platform CI 4, Detectors 3, and four single jobs). The jobs past the limit wait for a slot: the longest wait in each of those 15 runs was 3 to 109 s, median 39 s. On PR #2446's last commit, 40 jobs ran at the peak and the station-tests run took 178 s where its longest job took 105 s. A pull request that runs one or two stations starts 7 to 21 jobs and never waits.

**Approach:** the `changes` job already decides which jobs run. Its filter step now also holds one table of every sharded suite's shard count, normal and crowded. It sums the normal job count of every job the run will start (on a dispatch, every job), and when that sum is over 29 (40 less the other workflows' 11) it uses the crowded counts. It writes each sharded suite's group list as an output (`<suite>_groups`, a JSON list), each sharded job's matrix reads it (`group: ${{ fromJSON(needs.changes.outputs.<suite>_groups) }}`), and `--splits` reads `strategy.job-total`, so the split always matches the matrix. A one-shard job passes no pytest-split options: at `--splits 1`, pytest-split 0.11.0's `duration_based_chunks` steps past its one group (`IndexError`) once the summed durations reach the whole and a zero-second test follows, as `warden-test` did on dispatch 46144823146. Crowded, eight suites run one shard fewer:

| Job | Normal | Crowded | Estimated crowded job (s) |
|---|---|---|---|
| `doctor-live-test` | 2 | 1 | 76 |
| `herald-test` | 2 | 1 | 84 |
| `herald-live-test` | 4 | 3 | 88 |
| `marshal-test` | 4 | 3 | 103 |
| `marshal-live-test` | 2 | 1 | 98 |
| `steward-test` | 2 | 1 | 98 |
| `steward-live-test` | 4 | 3 | 83 |
| `warden-test` | 2 | 1 | 82 |

Each estimate is the job's measured overhead (its run time less its test step) plus its suite's summed test-step time over one shard fewer, from PR #2446's run. `atlas-test` (3) and `atlas-live-test` (2) keep their counts in both modes; they are the longest jobs already. Crowded, the run starts 29 test jobs.

The local preflight's CI selection already expands a `fromJSON(needs.changes.outputs.<x>)` matrix by running the `changes` job's filter step, so it keeps evaluating every job. The local preflight runs every suite unsharded, as before.

Ledger key: `117-41-a-crowded-station-tests-run-gives-eight-suites-one-shard-fewer`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Every test still runs exactly once: `--splits` equals the matrix's job count in every multi-shard run, and a one-shard job runs the whole suite.
- A run of 29 or fewer test jobs keeps today's shard counts.
- The table is the one place a sharded suite's shard counts are declared.

**Never:**
- Never add a step condition or expression the local preflight's selection cannot evaluate in the `changes` job.
- Never change which jobs a run starts; only how many shards a started suite has.

## Acceptance Criteria

**Given** a run whose started jobs, at normal counts, are more than 29
**When** the `changes` job writes the group lists
**Then** the eight suites above take their crowded counts and the run starts 29 station test jobs
**And** a run of 29 or fewer takes the normal counts

- **AC1 — The rule.** A scripts-lib test runs the filter step's shard section against stated outputs and asserts the group lists: crowded on a dispatch and on a full set, normal on one station, and `--splits` read from `strategy.job-total` in every sharded job.
- **AC2 — This pull request.** It touches the shared surface, so its own run is crowded: 29 station test jobs start, and every one passes.
- **AC3 — The local preflight.** A full preflight selects the same lanes as before.

</intent-contract>
