---
title: '117.27: Each station''s coverage gate runs on the runner''s Python'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 117-27-each-station-s-coverage-gate-runs-on-the-runner-s-python
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '.github/workflows/pyforge-station-tests.yml'
  - 'scripts/pixi_version_registry.py'
  - 'tests/scripts/test_coverage_gates_ci_driver.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - scripts/coverage_gates_ci.py
  - scripts/coverage_gate.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** On PR #2412's three CI runs the station path ended on a gate job: herald's at +153 and +166 s, atlas's at +169 s. Each of the eight gate jobs in `pyforge-station-tests.yml` takes 21 to 28 s: checkout 6 s, `setup-pixi` installing the station's whole pixi environment 10 to 17 s, and the gate itself 1 s. The gate runs `scripts/coverage_gates_ci.py --report …`. With every shard's report present, the script judges the reports and runs no test. It and `scripts/coverage_gate.py` import only the standard library, and they call `git`.

**Approach:** Each gate job sets up Python 3.14 with `actions/setup-python@v7`, the action and version `detectors.yml` and `pyforge-pip-install.yml` already use, in place of `setup-pixi`, and runs `python scripts/coverage_gates_ci.py` with the same arguments. `scripts/pixi_version_registry.py` counts the workflow's remaining setup-pixi steps (29 down to 21). Two tests hold the change:
- each gate job has one setup-python step at the estate's Python, no setup-pixi step and no `pixi run`, and runs the driver once;
- the driver and the scripts it imports take only the standard library, checked in a bare interpreter (`python -I -S`).

The local preflight's gate tasks (`pyforge-<station>-coverage-gate`) keep running in each station's pixi environment.

Ledger key: `117-27-each-station-s-coverage-gate-runs-on-the-runner-s-python`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (the preflight and a PR's CI answer within a measured budget; realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Each gate reads the same reports, judges the same floors with the same arguments, and exits as before.
- The gate's Python is the estate's: the test compares it with the interpreter the scripts suite runs on.

**Never:**
- Never change a floor, a report, a shard or the local gate tasks.
- Never add a dependency the gate scripts would need outside the standard library.

## Acceptance Criteria

**Given** the eight gate jobs of `pyforge-station-tests.yml`
**When** each one runs on a PR
**Then** it sets up Python 3.14 with `actions/setup-python`, installs no pixi environment, and judges its station's reports as before

- **AC1 — Each gate job runs the driver on setup-python, and the driver takes only the standard library.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_coverage_gates_ci_driver.py -q
  ```

- **AC2 — The pixi-version registry counts the workflow's setup-pixi steps.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild pixi-version-check
  ```

- **AC3 — On the PR's own CI run, every gate job passes with no setup-pixi step.** Expected: each `*-gate` job green, its steps showing `actions/setup-python`.

</intent-contract>

## Result (2026-11-27)

- The eight gate jobs (atlas, doctor, herald, marshal, mason, scribe, steward and warden, one per `coverage_gate.STATIONS` entry) each set up Python 3.14 with `actions/setup-python@v7` in place of `setup-pixi`, and run `python scripts/coverage_gates_ci.py` with the arguments they had. No other step changes. `scripts/pixi_version_registry.py` counts 21 setup-pixi steps in the workflow, down from 29.
- `tests/scripts/test_coverage_gates_ci_driver.py` gains two tests. The first holds that each gate job has exactly one setup-python step at the scripts suite's own Python (3.14), no setup-pixi step and no `pixi run`, and runs the driver once. The second imports the driver in `python -I -S` and holds that every module it loads is in `sys.stdlib_module_names` or is a `scripts/` sibling. Each test was checked by mutation: putting `pixi run` back on herald's gate reds the first, and an `import yaml` in `coverage_gate.py` reds the second.
- `docs/reference/container-base-layer-convention.md` names the registry as a source; its one claim about the registry, that it pins every Containerfile's pixi builder tag, still holds, and the page is re-verified.
- With the reports present, the driver never runs a test, so the gate needs nothing but the standard library and `git`. If a report were missing, the driver's fallback, a coverage run of the suite, would fail on the bare interpreter. CI never reaches it: every upload step fails when its report is missing, and the gate needs those jobs.
- AC1: the driver tests pass (52 passed with the registry tests). AC2: `pixi-version-check` exits 0. AC3 is read from the PR's own CI run.
