---
title: '117.19: Every preflight lane writes bytecode, whatever its caller says'
type: 'fix'
created: '2026-11-26'
status: 'done'
story: 117-19-every-preflight-lane-writes-bytecode-whatever-its-caller-says
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_preflight_scratch.py'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md'
  - 'docs/how-to/run-and-read-pr-preflight.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** An agent session runs `pr-preflight` with `PYTHONDONTWRITEBYTECODE=1` (Claude Code exports it; the operator's terminal does not). Every lane inherits it, so no `.pyc` is written: each xdist worker of each lane rewrites and compiles every test module and every repository module it imports, on every run. Marshal's collection takes 12.8 s that way and 3.4 s with a warm bytecode cache.

**Approach:** `_lane_scratch_env` removes `PYTHONDONTWRITEBYTECODE` from a lane's environment, so a lane writes bytecode beside its sources as it does from the operator's terminal (`__pycache__/` is gitignored at every depth). Nothing else in the environment changes.

Ledger key: `117-19-every-preflight-lane-writes-bytecode-whatever-its-caller-says`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (the preflight and a PR's CI answer within a measured budget; realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Measure before and after with the harness that measured the baseline (same machine, same tree shape).
- Leave every other variable of the caller's environment as it is.

**Never:**
- Never delete, skip or re-mark a test, lower a coverage floor, or weaken a lint, type or detector gate to gain time.
- Never write bytecode into a tracked path.

## Acceptance Criteria

**Given** an agent session whose environment sets `PYTHONDONTWRITEBYTECODE=1`
**When** `pr-preflight` starts a lane
**Then** the lane's environment has no `PYTHONDONTWRITEBYTECODE`, and the second run of a lane reuses the bytecode the first one wrote

- **AC1 — The lane-environment tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_preflight_scratch.py -q
  ```

- **AC2 — A full preflight in an agent session is faster than the 543 s cold baseline.** Expected: exit 0; `total_seconds` read from `.steward/preflight-runs.jsonl`.

  ```bash
  PYFORGE_PREFLIGHT_SCOPE=full pixi run --frozen -e pyforge-guild pr-preflight
  ```

</intent-contract>

## Evidence (2026-11-26)

Four lanes, each run alone on 16 threads, with and without bytecode writing (the second run with a warm cache): `pyforge-marshal-test` 461.7 to 375.4 CPU-seconds, `pyforge-atlas-live-test` 433.3 to 325.5, `pyforge-steward-live-test` 477.6 to 434.6, `pyforge-doctor-live-test` 443.2 to 498.3 (no gain). Collection alone, without and with a warm cache: marshal 12.8 and 3.4 s, atlas 14.4 and 8.2 s, steward 5.4 and 1.5 s.

## Result (2026-11-26)

A full preflight of all 50 lanes, measured with the harness that measured the baseline on the same machine: 312.5 s cold and 319.1 s warm, against 543.2 s and 532.1 s after PR #2405 (42% and 40% less); about 3,900 CPU-seconds against 6,100. `pyforge-herald-live-test` starts 13 to 17 s in on 6 workers and takes 105 to 118 s; the run is bound by the machine. The only red lanes are `detectors-ci` and `test-ci-meta`, reading the measurement's own uncommitted probe lines, as in the baseline.
