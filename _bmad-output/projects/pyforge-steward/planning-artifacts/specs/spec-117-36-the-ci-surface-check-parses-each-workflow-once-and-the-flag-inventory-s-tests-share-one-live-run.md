---
title: '117.36: The CI-surface check parses each workflow once, and the flag inventory''s tests share one live run'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 117-36-the-ci-surface-check-parses-each-workflow-once-and-the-flag-inventory-s-tests-share-one-live-run
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'scripts/_ci_surface_gates_render.py'
  - 'scripts/_ci_surface_gates_lib.py'
  - 'tests/scripts/test_flag_inventory.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** the Detectors job's library part takes 112 to 128 s, the longest job on most PRs.
- `scripts/ci_surface_gates.py --check` parses workflow files 109 times with PyYAML's pure-Python loader: 2.7 s a run, and its tests run it six times. `_workflow_jobs` and `_if_text_for_row` re-read a workflow for each registry row.
- `tests/scripts/test_flag_inventory.py` builds the live reports twice, 7.7 s each: once in the CLI test, once in a module fixture.

**Approach:**
- `_ci_surface_gates_render.load_yaml(path)` parses each distinct text once (`functools.lru_cache`, keyed by the text), with `yaml.CSafeLoader` where PyYAML was built with libyaml, else `yaml.SafeLoader`. Each call returns its own `copy.deepcopy`. Every `yaml.safe_load` of a file in the render and library modules uses it.
- One module fixture, `live_run`, runs the inventory CLI. The CLI test asserts on that run, its subject as before, and `live_reports` reads its output. Both tests share the xdist group.

Ledger key: `117-36-the-ci-surface-check-parses-each-workflow-once-and-the-flag-inventory-s-tests-share-one-live-run`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (realized, no text change); works with CAP-166 (the CI-surface registry).
- No AD moves.

## Boundaries & Constraints

**Always:**
- The check's findings and render output stay byte-identical.

**Never:**
- Never weaken an assertion or drop a test.

## Acceptance Criteria

**Given** the live tree
**When** the check, its var-use scan and its dry-run render run before and after the change
**Then** their outputs are byte-identical, and the check runs in well under a second
**And** both test files pass, serially and under xdist

- **AC1 — The two test files pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_ci_surface_gates.py tests/scripts/test_flag_inventory.py -q -n 4 --dist loadgroup
  ```

- **AC2 — The check is clean on the live tree.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild python scripts/ci_surface_gates.py --check
  ```

</intent-contract>

## Result (2026-11-27)

- `--check` 2.68 s to 0.17 s. `collect_var_uses`, `offline_check`, `--check` and `--render --dry-run` on the live tree compare byte-identical (`PYTHONHASHSEED=0`).
- `test_ci_surface_gates.py`: 25 passed in 2.3 s.
- `test_flag_inventory.py`: 88 passed in 10.3 s, serially and with four workers; the six live checks of the first took about 16 s.
- PyYAML's two loaders parsed all 18 workflows to equal documents.
