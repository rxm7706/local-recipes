---
title: '58.1: Herald''s suite runs under xdist, its site builds in one worker'
type: 'chore'
created: '2026-11-26'
status: 'done'
story: 58-1-herald-s-suite-runs-under-xdist-its-site-builds-in-one-worker
spec: spec-pyforge-herald
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'pixi.toml'
  - 'pixi.lock'
  - 'environment.yaml'
  - 'src/shared/packages/pyforge-herald/tests/conftest.py'
  - 'src/shared/packages/pyforge-herald/tests/meta/test_site_builders_share_a_worker.py'
  - '.github/workflows/pyforge-station-tests.yml'
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Herald's halves each run as one pytest process. `pyforge-herald-live-test` is the longest lane of a full preflight (234 s alone, 441 to 471 s in the run) and the critical path of seven of eight PR heads (263 to 425 s). About 160 s of it are tests that run `astro build` with `docs-site/` as the working directory; they cannot overlap, and today everything else waits behind them.

**Approach:** Add `pytest-xdist` to herald's environment and `-n auto --dist loadgroup` to both suite tasks. Put every module that names the build helper `tests/meta/pages_astro.py` (the one module that runs Astro) in one xdist group, decided in `tests/conftest.py` from the module's text, so one worker runs the builds in turn and the others run the rest. A module that only reads `docs-site/`'s tracked sources, or names its pixi tasks, stays out. Run the `herald-live-test` CI job as two `pytest-split` shards, each writing its coverage report, as the package half's job does.

Ledger key: `58-1-herald-s-suite-runs-under-xdist-its-site-builds-in-one-worker`.

### Living CAP citations

- spec-pyforge-steward:CAP-175 (the preflight and a PR's CI answer within a measured budget; realized here, no text change in this station's Spec).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Measure before and after with the harness that measured the baseline.
- Keep one Astro build at a time per `docs-site/` tree.
- Keep both coverage reports and the gate's merge of them.

**Never:**
- Never delete, skip or re-mark a test to gain time.
- Never change the preflight's docs-site mutex or its lane order (steward Story 105.1).
- Never lower a coverage floor.

## Acceptance Criteria

**Given** herald's halves on one process each
**When** they run under xdist with the docs-site modules in one group
**Then** each half passes with the counts it had and the gate passes
**And** the live half takes under 210 s alone on 16 threads, the package half under 25 s

- **AC1 — Both halves pass with their counts.** Expected: exit 0; `1560 passed, 5 skipped` and `812 passed` plus the 5 of the second segment.

  ```bash
  pixi run --frozen -e pyforge-herald pyforge-herald-test-built
  ```

- **AC2 — Herald's coverage gate passes on the merged reports.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-herald pyforge-herald-coverage-gate
  ```

</intent-contract>

## Evidence (2026-11-26)

Standalone `pyforge-herald-live-test`: 233.9 s wall, 334 CPU-seconds, `812 passed, 1565 deselected in 230.54s`. Slowest: `test_the_install_runs_before_herald_s_suite_in_one_slot_and_many` 34.4 s, two `test_agent_surface_and_changes.py` builds at 12.8 s, thirteen build fixtures and tests at 5.6 to 7.4 s. CI job over seven PR heads: 314 s median, 425 s at most, 247 s of it the pytest step.

## Result (2026-11-26)

Alone on 16 threads: `pyforge-herald-test` 18.8 s (37.9 s before; `1564 passed, 5 skipped`, four of them this story's
own), `pyforge-herald-live-test` 198.4 s (233.9 s before; `812 passed` and the 5 of the second segment). Measured on
one process, the live half's time is 243 s over 812 tests, of which 207 s sit in five modules; the twelve modules that
name the build helper sum to about 180 s and still run in turn, because every Astro build has `docs-site/` as its
working directory. That chain is the half's floor in one tree. `test_preflight_pages_lane.py` (53 s) builds nothing
and now runs beside it. Running builds side by side needs one copy of `docs-site/` per worker, which this story does
not attempt.
