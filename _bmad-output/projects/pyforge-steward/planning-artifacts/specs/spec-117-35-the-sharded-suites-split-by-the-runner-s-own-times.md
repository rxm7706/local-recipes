---
title: '117.35: The sharded suites split by the runner''s own times'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 117-35-the-sharded-suites-split-by-the-runner-s-own-times
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'tests/durations/pyforge-steward.json'
  - 'tests/durations/pyforge-steward-live.json'
  - 'tests/durations/pyforge-atlas.json'
  - 'tests/durations/pyforge-atlas-live.json'
  - 'tests/durations/pyforge-marshal.json'
  - 'tests/durations/pyforge-marshal-live.json'
  - 'tests/durations/platform.json'
  - 'tests/durations/README.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** the sharded suites split by durations files written on a laptop (Stories 117.25 and 117.34), and the CI runner's times are not a laptop's. A `PyForge station tests` run dispatched to print every test's time (46102690187; `--durations=0 --durations-min=0` on each sharded job) and a `Platform CI` run (46102692069) show the runner at 1.6 times the file's seconds for steward's live half and 0.46 times its package half's stale file (which also lacked 274 tests). Marshal's live half split 34 s against 2 s, and marshal's package half 75, 46, 58 and 36 s.

**Approach:** write each file from that run's times. For every `<seconds>s <setup|call|teardown> <test id>` line, sum each test id's three phases, as `pytest-split --store-durations` does. Merge each task's shards into one file, and write it as pytest-split writes its own (`sort_keys=True`, `indent=4`, two decimals, no trailing newline). `tests/durations/README.md` says how.

Ledger key: `117-35-the-sharded-suites-split-by-the-runner-s-own-times`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- The same tests run, each in one shard.

**Never:**
- Never change a test, a job or a lane in this story.

## Acceptance Criteria

**Given** each task's pytest segments split in collection order as `duration_based_chunks` does
**When** split by the new file and scored by the runner's times
**Then** each suite's heaviest shard is lighter than under the old file
**And** every collected test is in exactly one shard

- **AC1 — The durations-files test passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_durations_files.py -q
  ```

- **AC2 — This PR's CI shards.** Expected: each sharded job's slowest shard is no slower than on the runs this story measured.

</intent-contract>

## Result (2026-11-27)

The simulated split reproduced the probe's measured shards (steward's live half 107/68/121/74 s simulated against 106/68/121/74 s measured; marshal 75/46/58/36 s against 75/46/58/36 s). Heaviest shard, old file to new, in summed runner seconds:

| Suite | Old | New |
|---|---|---|
| marshal | 75 | 54 |
| steward live half | 121 | 106 |
| steward package half | 58 | 52 |
| atlas | 49 | 43 |
| atlas live half | 41 | 33 |
| marshal live half | 34 | 21 |

On a local subset of Platform CI's tests (the laptop collects 1,355 of the runner's 1,593), the old file split 91/129/74 s and the new one 98/101/95 s.
