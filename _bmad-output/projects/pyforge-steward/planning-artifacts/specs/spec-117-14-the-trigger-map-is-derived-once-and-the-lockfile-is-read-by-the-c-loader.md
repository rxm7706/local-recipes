---
title: '117.14: The trigger map is derived once and the lockfile is read by the C loader'
type: 'fix'
created: '2026-11-26'
status: 'ready-for-dev'
story: 117-14-the-trigger-map-is-derived-once-and-the-lockfile-is-read-by-the-c-loader
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/estate_realize.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/machine.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_estate_realize.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `pyforge-steward-live-test` takes 194 s alone and 2,521 CPU-seconds on 16 workers, 35% of the CPU a full preflight spends. `test_station_tests_trigger_map.py` keeps `real_derivation()` in a `functools.cache`, which is per process: under `--dist loadgroup` its tests spread over the workers and each worker computes the derivation again (1,324 s summed over the module). `estate_realize._locked_version` parses the 3.95 MB `pixi.lock` with PyYAML's pure-Python loader on every call, eight times in one test (45.35 of 45.76 s under a profile).

**Approach:** Give the trigger-map module one `xdist_group`, so its tests share a worker and its cache. Read the lockfile with `yaml.CSafeLoader`, falling back to `yaml.SafeLoader` where libyaml is absent, and keep the parsed document per path, size and modification time. Hold both with tests: the two loaders read `pixi.lock` to equal documents, and an edited lockfile is read again.

Ledger key: `117-14-the-trigger-map-is-derived-once-and-the-lockfile-is-read-by-the-c-loader`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Measure before and after with the harness that measured the baseline (same tree shape, same machine).
- Keep `yaml.safe_load` semantics: a safe loader only, never `yaml.load` with a full loader.

**Never:**
- Never delete, skip or re-mark a test to gain time.
- Never cache a lockfile across a change of its bytes.

## Acceptance Criteria

**Given** the live-tree half at `d039bc7de3`
**When** the trigger-map module runs in one xdist group and the lockfile is parsed by the C loader once per file state
**Then** the half runs the same tests by count, and `test_estate_realize.py` takes under 10 s summed
**And** the equality and re-read tests pass

- **AC1 — The live-tree half passes with the count it had.** Expected: exit 0, `1896 passed, 1 skipped` plus the two alone-run files.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```

- **AC2 — The estate tests pass, and the loader tests with them.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_estate_realize.py -q -m live_tree
  ```

</intent-contract>

## Evidence (2026-11-26)

Standalone on 16 threads: `pyforge-steward-live-test` 194.0 s wall, 2,521 CPU-seconds. Fifteen trigger-map tests at 84 to 91 s each, one per worker. `test_bmad_preflight_and_suite_advance_hint` 169.0 s, `test_realize_argv_per_moved_class` 71.4 s, `test_operator_gate_runs_with_yes` 64.6 s. Loader bench on `pixi.lock`: `CSafeLoader` 0.54 s, `safe_load` 2.94 s, documents equal.
