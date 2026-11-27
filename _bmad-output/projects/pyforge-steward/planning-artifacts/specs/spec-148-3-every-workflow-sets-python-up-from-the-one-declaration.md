---
title: '148.3: Every workflow sets Python up from the one declaration'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 148-3-every-workflow-sets-python-up-from-the-one-declaration
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '.github/actions/setup-estate-python/action.yml'
  - '.github/actions/sync-pypi-mappings/action.yml'
  - '.github/workflows/pyforge-station-tests.yml'
  - '.github/workflows/detectors.yml'
  - '.github/workflows/pyforge-pip-install.yml'
  - '.github/workflows/platform-deploy.yml'
  - '.github/workflows/platform-ci.yml'
  - '.github/workflows/test-linux.yml'
  - 'scripts/target_version_check.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_target_version_check_surfaces.py'
  - 'tests/scripts/test_coverage_gates_ci_driver.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - pixi.toml
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Ten `actions/setup-python` steps hard-code `'3.14'`, so the runner takes its newest 3.14 (3.14.10 on PR #2413's run) whatever the estate declares. `sync-pypi-mappings` carries a `python-version` input nothing reads. Three jobs run Python on the runner's own 3.12: `platform-deploy.yml`'s verify script, `test-linux.yml`'s upload client, and `platform-ci.yml`'s air-gap mirror build.

**Approach:** One composite action, `.github/actions/setup-estate-python`, reads `python = "X.Y.Z.*"` under `[feature.interpreter.dependencies]` from `pixi.toml` and sets that Python up with `actions/setup-python`. Every setup-python step uses it; the deploy and upload jobs use it before their Python; the air-gap build runs through `pixi run -e platform-dev`. The unused input is removed. `target-version-check` (CAP-153) holds the whole chain: a second `python` declaration, an environment without the `interpreter` feature, a lock off the declared version, an `actions/setup-python` step outside the action, or a step that starts `python` before its job has an interpreter (the action, an activated pixi environment, or a container) each red it.

Ledger key: `148-3-every-workflow-sets-python-up-from-the-one-declaration`.

### Living CAP citations

- spec-pyforge-steward CAP-153 (realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- The version is read from `pixi.toml` at run time; no workflow or action carries a copy.

**Never:**
- Never hold the recipe lanes' `setup-miniconda` `python-version` to the estate: it is the Python a recipe is built for, a per-build choice.

## Acceptance Criteria

**Given** the workflows and actions
**When** `target-version-check` reads them with the manifest and the lock
**Then** it exits 0, and each of its rules reds a tree that breaks it

- **AC1 — The tree is clean.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild target-version-check
  ```

- **AC2 — Each rule is held by a test.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_target_version_check_surfaces.py -q
  ```

- **AC3 — The gates use the action.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_coverage_gates_ci_driver.py -q
  ```

</intent-contract>

## Result (2026-11-27)

- `setup-estate-python` reads the declaration with `sed` from `${GITHUB_WORKSPACE}/pixi.toml` (it gives `3.14.10` on this tree) and fails with an annotation when none is found. The eight gates, `detectors.yml` and `pyforge-pip-install.yml` use it; `platform-deploy.yml` and `test-linux.yml`'s upload step take it before their Python; the air-gap mirror build runs `pixi run --frozen -e platform-dev python …`, the environment its `setup-pixi` installs, which carries `requests`.
- `target-version-check` reads the version from the `interpreter` feature and adds the four rules; it exits 0 on the tree (36 environments; 21 workflow and action files). Run before the changes to the deploy, upload and air-gap jobs, its first version also flagged `platform-ci.yml`'s `docker run … \` continuation and the recipe lanes' `setup-miniconda` `python-version`; the rule now skips continuation lines, and the miniconda input is out of its scope by the boundary above.
- `test_target_version_check_surfaces.py` seeds the declaration, two environments, a lock and the action, and gains 15 cases: each rule reds its breach, five interpreters (the action, an activated pixi environment, `docker`, a continuation line, `pixi run`) and a container job are clean, a local action that activates pixi provides the interpreter, and dropping the lock check would hide drift. `test_coverage_gates_ci_driver.py`'s gate test asserts the action and no `actions/setup-python`.
- AC1: exit 0. AC2: 37 passed. AC3: the driver tests pass.
