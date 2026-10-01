---
title: "39.1: `pr-preflight` runs the detector-aggregate tests where Doctor's run-deps are installed"
type: 'fix'
created: '2026-10-01'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-38-5-the-detector-aggregate-tests-run-where-doctor-s-run-deps-are-installed.md
  - .github/workflows/detectors.yml
  - pixi.toml
  - tests/scripts/test_detectors_doctor_sources.py
  - docs/how-to/pixi-tasks.md
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** Story 38.5 moved the three aggregate tests of `tests/scripts/test_detectors_doctor_sources.py` onto a
second Detectors `scripts-suite` step, `pixi run --frozen -e pyforge-doctor python -m pytest
tests/scripts/test_detectors_doctor_sources.py -q`, because they skip in `pyforge-ci`. `pr-preflight` depends on the
first step's task (`pyforge-doctor-scripts-test`, `-e pyforge-ci`) but has no leg for the second, so locally those
three tests only ever skip, against `pr-preflight`'s own promise that a green local run means a green CI run.

**Approach:**

- A `[feature.pyforge-doctor.tasks.pyforge-doctor-aggregate-scripts-test]` task runs that file under `pyforge-doctor`.
- The `scripts-suite` step calls the task verbatim, and `pr-preflight` gains the leg
  `{ task = "pyforge-doctor-aggregate-scripts-test", environment = "pyforge-doctor" }`, with a ninth-leg note in its
  description.
- `tests/meta/test_preflight_mirrors_scripts_suite.py` (doctor) reds any `scripts-suite` step that is not
  `pixi run --frozen -e <env> <task>` with `(task, env)` among `pr-preflight`'s `depends-on` legs.

Ledger key: `39-1-pr-preflight-runs-the-detector-aggregate-tests-where-doctor-s-run-deps-are-installed`.
Type / Effort / Deps: fix / XS / S-38.5.

### Living CAP citations

- CAP-42, CAP-43 (Stories 38.3, 38.5). A defect of 38.5's CI step, so no new CAP; `spec-feature-flag-governance` Q1: a
  `fix` needs no flag.

## Acceptance Criteria

- Given the `pyforge-doctor` env When `pixi run --frozen -e pyforge-doctor pyforge-doctor-aggregate-scripts-test` runs Then every test in the file passes and none skips
- Given `pixi.toml` When `pr-preflight`'s `depends-on` is read Then it holds `(pyforge-doctor-aggregate-scripts-test, pyforge-doctor)`, and the Detectors `scripts-suite` job's step runs exactly that task in that env
- Given a `scripts-suite` step with no matching leg, or one that is not a named task When the meta-test runs Then it names the step; a step that runs a bare-string leg in `pyforge-guild` (the environment `pr-preflight` runs in) is not reported
- Given this change When `pixi project export conda-environment -e build` runs Then `environment.yaml` is unchanged

## Boundaries & Constraints

**Always:**
- `pyforge-ci` stays stdlib-only.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not delete or weaken any test in `tests/scripts/test_detectors_doctor_sources.py`.
- Do not add `jsonschema` or `pyyaml` to `pyforge-ci`.

</intent-contract>

## Binding

Parent capabilities: CAP-42, CAP-43 (defect of Story 38.5's CI step; no new CAP).
Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-01 (evening) entry.
Ledger key: `39-1-pr-preflight-runs-the-detector-aggregate-tests-where-doctor-s-run-deps-are-installed`.
Ledger status at mint: `backlog`.
Deps: S-38.5.
Minted 2026-10-01 by operator ruling: add the missing `pr-preflight` leg now.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-aggregate-scripts-test` — expected: all pass, none skipped.
- `pixi project export conda-environment -e build` — expected: identical to `environment.yaml`.

## Review Triage Log

Review 1 (2026-10-01): an independent read-only reviewer read the staged diff against this spec and Story 38.5's. It
confirmed the new task is the old step's command (same file, flags and env), `pyforge-doctor` composes the feature and
carries PyYAML, the CI job still installs that env, `pixi run -n -e pyforge-guild pr-preflight` lists the leg, the
aggregate tests skip in `pyforge-ci` (16 passed, 3 skipped), nothing else pins the leg list or the step name, and the
chain's claims hold. No high findings:

- `[medium]` `[reject]` "`pixi.toml`'s co-governor spec-pyforge-core is not reconciled." `spec-surface-check` on this
  change reads ok (no drift; exit 0), before and after these fixes; no reconcile or stamp is due.
- `[low]` `[patch]` `tests/scripts/test_detectors_doctor_sources.py`'s `_doctor_dispatch` docstring still said the
  `detectors` job reruns the file under `pyforge-guild`, and named only `jsonschema`/`yaml`. Fixed: it names the
  `scripts-suite` second step and `pr-preflight` (this story's task, `pyforge-doctor`) and `pyforge.core`; the
  `detectors.yml` comment likewise; the file joined epic surface "39".
- `[low]` `[patch]` `docs/how-to/pixi-tasks.md` (generated) went stale with the new task. Fixed:
  `pixi run -e pyforge-guild docs-pixi-tasks` (which also restamps `docs/map.yaml`).
- `[low]` `[patch]` The meta-test read a bare-string leg as having no environment, so a step mirroring one (such as
  `docs-map-render-test` in `pyforge-guild`) would be a false positive. Fixed: a bare-string leg runs in `pyforge-guild`;
  a test pins it.
- `[low]` `[patch]` The spec and ledger rows were still `backlog`. Fixed at landing: `done`.

## Auto Run Result

Hand-built in an interactive session on the operator's ruling of 2026-10-01 (add the missing leg now). Verification:

- `pixi run --frozen -e pyforge-doctor pyforge-doctor-aggregate-scripts-test` — exit 0: 19 passed, none skipped.
- `pixi run --frozen -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/meta/test_preflight_mirrors_scripts_suite.py -q`
  — exit 0: 5 passed.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — exit 0: 1102 passed, 18 skipped.
- `pixi project export conda-environment -e build` — identical to `environment.yaml`; `pixi lock --check` exit 0.
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — run by `pr-preflight` on push.
