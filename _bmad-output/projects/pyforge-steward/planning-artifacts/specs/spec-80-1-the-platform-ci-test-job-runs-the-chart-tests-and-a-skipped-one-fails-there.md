---
title: "80.1: The Platform CI `test` job runs the chart tests, and a skipped one fails there"
type: 'fix'
created: '2026-10-01'
status: 'in-progress'
baseline_revision: '423056819c2ecb0f2d244e3109edbe0df03621a4'
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
warnings:
  - oversized
deferred:
  - summary: >-
      The Platform CI `test` log has not been read, so the five chart-test deferrals stay open.
    evidence: >-
      Closing DW-FU-41-2-4, DW-FU-42-1-5, DW-FU-42-4-2, DW-steward-76-1 and DW-steward-78-1-3 needs a Platform CI `test` run of this change showing the chart tests ran, not skipped. That run exists only after a push, and this run did not push or open a PR. Local evidence (the `platform-ci-test` env running the chart modules with zero helm skips) is recorded in the Auto Run Result, not offered as the CI log. Settled by reading the PR's `test` job log for skip counts on `tests/test_chart_invariants.py` and `tests/test_openfeature_file_flags.py`.
    location: .github/workflows/platform-ci.yml
    severity: medium
  - summary: >-
      A missing PyYAML would still skip the chart tests silently under CI.
    evidence: >-
      `_import_yaml` and the flags module use `pytest.importorskip("yaml")`, which skips rather than fails when PyYAML is absent. PyYAML is in the `platform-ci-test` lock only as a transitive dependency, not a direct one in `[feature.platform-ci-test.dependencies]`. The same silent-skip class this story closes for helm, with no known trigger today. Settled by deciding whether `importorskip("yaml")` fails under `CI` too, or `pyyaml` becomes a direct dependency.
    location: src/platform/tests/test_chart_invariants.py
    severity: low
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

## Code Map

- `pixi.toml` -- `[feature.platform-ci-test.dependencies]` (~L408) gains `kubernetes-helm`; `platform-dev` (~L332) holds the pin `>=4.3.0`
- `pixi.lock` -- moves with the manifest via `pixi lock` (never `pixi add`/`pixi update`: pre-shell hook denies them)
- `environment.yaml` -- export of the `build` env; holds no `platform-ci-test` content, so a regenerated file is expected byte-identical
- `src/platform/tests/test_chart_invariants.py` -- `requires_helm` (L168), 67 function-level uses (the contract's 66 is stale), `_import_yaml` (L182) `importorskip("yaml")`
- `src/platform/tests/test_openfeature_file_flags.py` -- `requires_helm` (L57), 7 uses; module-level `importorskip("openfeature...")` L47-48
- `src/platform/tests/__init__.py` -- present; there is no `conftest.py`, so the shared gate is a plain module
- `.github/workflows/platform-ci.yml` -- `test` job (L168-254) installs via `platform-test-setup`, runs `python -m pytest -v` from `src/platform`; GitHub sets `CI=true`, so no workflow edit
- `scripts/platform-ci-local.sh` -- L110 `PATH="$CIT:$DEV:$PATH"`, never sets `CI`; unchanged
- `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md` -- the five rows (L3129, L3417, L3987, L5546, L5579); closing them needs the PR's CI log

## Tasks & Acceptance

**Execution:**
- `pixi.toml` -- add `kubernetes-helm = ">=4.3.0"` to `[feature.platform-ci-test.dependencies]`; run `pixi lock`; regenerate `environment.yaml` -- helm becomes pixi-provisioned in the CI env (AD-16)
- `src/platform/tests/helm_gate.py` -- new: one `requires_helm` decorator (helm present: test unchanged; absent and `CI` set: fails naming `helm`; absent: skip) -- replaces both `pytest.mark.skipif` definitions
- `src/platform/tests/test_chart_invariants.py`, `src/platform/tests/test_openfeature_file_flags.py` -- import `requires_helm` from the gate, drop the local definition and the unused `shutil` import, fix the stale "pip-only CI lane" wording -- one definition, no drift
- `src/platform/tests/test_helm_gate.py` -- new: the three branches with patched `PATH` and `CI`; mutation run removes the CI branch and the CI test must red -- covers the I/O matrix
- Run the platform suite in the `platform-ci-test` env -- zero helm skips in `test_chart_invariants.py` and `test_openfeature_file_flags.py`

**Acceptance Criteria:**
- Given the `platform-ci-test` env, when it is installed from the lock, then `helm version` exits 0 inside it
- Given `CI` is set and `helm` is absent, when a `requires_helm` test runs, then it fails with a message naming `helm`
- Given `CI` is unset and `helm` is absent, when a `requires_helm` test runs, then it skips
- Given `pixi.toml` changed, when `environment.yaml` is regenerated, then the committed file equals the export
- Given the CI-fail branch is removed, when `test_helm_gate.py` runs, then it fails
- Given the PR's Platform CI `test` run, when its log is read, then the chart tests ran, not skipped (post-push; recorded under `deferred:`, never claimed from local evidence)

## Spec Change Log

## Binding

Parent: Story 16.1's Platform CI lane (defect; no new CAP). DW-FU-41-2-4, DW-FU-42-1-5, DW-FU-42-4-2, DW-steward-76-1, DW-steward-78-1-3.
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-01 entry.
Ledger key: `80-1-the-platform-ci-test-job-runs-the-chart-tests-and-a-skipped-one-fails-there`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-01 by operator ruling: the deferral burn-down's "stop the inflow" changes run before its Phase 2.

## Design Notes

- A mark cannot fail a test, so `requires_helm` becomes a decorator: helm on PATH returns the test unchanged; absent with `CI` set returns a stand-in that calls `pytest.fail` naming `helm`; absent otherwise applies `pytest.mark.skip`. It reads `shutil.which("helm")` and `os.environ` when built (import time, like the old `skipif(bool)`), so a test patches `PATH` and `CI` with `monkeypatch` and rebuilds it.
- `CI` counts as set when non-empty; GitHub Actions exports `CI=true`.
- One shared `helm_gate.py` replaces the two copies the contract calls "both definitions": same behaviour in each module, one place to test and mutate.
- Latent, out of scope: `_import_yaml`'s `pytest.importorskip("yaml")` still skips silently under CI. PyYAML is in the `platform-ci-test` lock only transitively; recorded under `deferred:`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e platform-ci-test bash -c 'cd src/platform && python -m pytest tests/test_helm_gate.py tests/test_chart_invariants.py tests/test_openfeature_file_flags.py -rs -q'` — expected: pass, no `helm not on PATH` skip lines.
- `pixi run --frozen -e platform-ci-test bash -c 'cd src/platform && ruff check . && ruff format --check . && mypy platformapp config tests'` — expected: exit 0.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
