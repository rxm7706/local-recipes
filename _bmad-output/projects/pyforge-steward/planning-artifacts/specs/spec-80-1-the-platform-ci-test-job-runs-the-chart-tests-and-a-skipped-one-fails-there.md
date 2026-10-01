---
title: "80.1: The Platform CI `test` job runs the chart tests, and a skipped one fails there"
type: 'fix'
created: '2026-10-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
  - pixi.toml
  - .github/workflows/platform-ci.yml
  - src/platform/tests/test_chart_invariants.py
  - src/platform/tests/test_openfeature_file_flags.py
  - scripts/platform-ci-local.sh
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Every chart invariant carries `requires_helm` (`pytest.mark.skipif` when `helm` is not on PATH): 66 in
`test_chart_invariants.py` and 7 in `test_openfeature_file_flags.py`. The Platform CI `test` job installs only the slim
`platform-ci-test` pixi env, which has no `kubernetes-helm` (only `platform-dev` does, at `>=4.3.0`), so all 73 skip there
without a word; only `platform-ci-local` runs them. Five deferrals record the cause (DW-FU-41-2-4, DW-FU-42-1-5,
DW-FU-42-4-2, DW-steward-76-1, DW-steward-78-1-3).

**Approach:**

- Add `kubernetes-helm` to `[feature.platform-ci-test.dependencies]` at the pin `platform-dev` uses; update the lock and
  regenerate `environment.yaml` (`pixi project export conda-environment -e build > environment.yaml`) in the same change.
- `requires_helm` (both definitions) fails the test, naming the missing binary, when the `CI` environment variable is set
  and `helm` is absent; outside CI it still skips.
- Confirm on the PR's Platform CI run that the chart tests ran, and close the five deferrals with that evidence.

Ledger key: `80-1-the-platform-ci-test-job-runs-the-chart-tests-and-a-skipped-one-fails-there`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- Story 16.1 (the `platform-ci-test` env); canopy:AD-16 (pixi-provisioned tools). A defect of the Platform CI lane, so
  no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given the `platform-ci-test` env When it is installed Then `helm version` succeeds inside it
- Given `CI` is set and `helm` is absent When a `requires_helm` test runs Then it fails naming `helm`
- Given `CI` is unset and `helm` is absent When a `requires_helm` test runs Then it skips
- Given the PR's Platform CI `test` run When its log is read Then the chart tests ran, not skipped
- Given `pixi.toml` changed When `environment.yaml` is compared Then it was regenerated in the same change
- Given the CI-fail branch is removed When the new test runs Then it fails (mutation)

## Tasks

1. Read the two `requires_helm` definitions, `[feature.platform-ci-test]` in `pixi.toml` and the `test` job in `platform-ci.yml`.
2. Add the dependency; update the lock; regenerate `environment.yaml`.
3. Make `requires_helm` fail under `CI`; test both branches with a patched PATH and environment.
4. Push, read the Platform CI `test` log, close the five deferrals with that evidence.

## Boundaries & Constraints

**Always:**
- helm is pixi-provisioned (canopy:AD-16).
- A `pixi.toml` change regenerates `environment.yaml` in the same change.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not install helm on the runner outside pixi.
- Do not delete or loosen any chart test.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| CI with helm | platform-ci-test env | chart tests run | — |
| CI without helm | `CI` set, no helm | test fails, names helm | — |
| local without helm | `CI` unset | skip | — |

</intent-contract>

## Binding

Parent: Story 16.1's Platform CI lane (defect; no new CAP). DW-FU-41-2-4, DW-FU-42-1-5, DW-FU-42-4-2, DW-steward-76-1, DW-steward-78-1-3.
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-01 entry.
Ledger key: `80-1-the-platform-ci-test-job-runs-the-chart-tests-and-a-skipped-one-fails-there`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-01 by operator ruling: the deferral burn-down's "stop the inflow" changes run before its Phase 2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
