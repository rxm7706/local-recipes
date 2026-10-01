---
title: "80.1: The Platform CI `test` job runs the chart tests, and a skipped one fails there"
type: 'fix'
created: '2026-10-01'
status: 'in-review'
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
  - summary: >-
      Three more `importorskip` sites can skip chart-related tests silently under `CI`, beyond the one `DW-steward-80-1-2` names.
    evidence: >-
      `test_openfeature_file_flags.py` calls `pytest.importorskip("openfeature")` and `pytest.importorskip("openfeature.contrib.provider.flagd")` at module level (lines 48-49), so a missing package skips the whole module, including its 7 `requires_helm` tests. `pytest.importorskip("yaml")` is also called inline in `test_openfeature_file_flags.py` (line 102, `_render_core`) and in `test_story_48_4_eso_example_lists_required_platform_secret_keys` in `test_chart_invariants.py` (line 2753), which is not `requires_helm`-gated. No trigger is known today: `openfeature-sdk` and `openfeature-provider-flagd` are direct `platform-ci-test` dependencies, and PyYAML is locked there transitively; a local `platform-ci-test` run of both modules had zero skips. Making these fail under `CI` would change tests unrelated to helm and needs a decision between a `CI`-aware helper and a direct `pyyaml` dependency, which this story's intent (`requires_helm` only) does not make. Settled by that decision, taken together with `DW-steward-80-1-2`.
    location: src/platform/tests/test_openfeature_file_flags.py
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

## Auto Run Result

### Summary of implemented change

- **helm in the CI env:** `kubernetes-helm = ">=4.3.0"` (the pin `platform-dev` holds) joins `[feature.platform-ci-test.dependencies]`; `pixi lock` added one line to `pixi.lock` (4.3.0 was already locked for `platform-dev`). `environment.yaml` regenerated byte-identical (it holds no `platform-ci-test` content).
- **One gate:** `src/platform/tests/helm_gate.py` holds `requires_helm`, a decorator. helm on PATH: the test unchanged. Absent with `CI` set (non-empty): a `functools.wraps` stand-in that calls `pytest.fail` naming `helm`. Absent otherwise: `pytest.mark.skip`. Both old `pytest.mark.skipif` definitions are gone; the two modules import the gate. No chart test was touched, deleted or loosened (the contract's 66 uses is 67 in `test_chart_invariants.py`, plus 7 in `test_openfeature_file_flags.py`).
- **Tests of the gate:** `src/platform/tests/test_helm_gate.py` pins the three branches (and an empty `CI` as unset) against a patched `PATH`/`CI`, then drives a real `pytest` subprocess per branch (passed / failed naming helm / skipped), so the stand-in is proven to be collected as a failure, with fixtures resolved.

### Files changed

- `pixi.toml`, `pixi.lock` -- helm in `platform-ci-test`
- `src/platform/tests/helm_gate.py` (new), `src/platform/tests/test_helm_gate.py` (new)
- `src/platform/tests/test_chart_invariants.py`, `src/platform/tests/test_openfeature_file_flags.py` -- import the gate; local definition and unused `shutil` import dropped; the "pip-only CI lane" wording fixed
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md` (surface reconcile + a correction entry; the baseline `scripts/.spec-surface-baseline.json` is NOT changed, see Residual risks), `.../deferred-work-ledger.md` (the two `deferred:` entries ingested as `DW-steward-80-1` and `DW-steward-80-1-2` by `deferred_work_intake.py --fix --project steward`)

### Review findings breakdown

No independent review has run (implementation and review stay separate).

### Follow-up review recommendation

`followup_review_recommended: false`. The one thing a reviewer should read is the stand-in in `helm_gate.py`: it relies on `functools.wraps` carrying the signature so pytest still injects fixtures, which the subprocess test covers for a fixture-taking test.

### Verification performed

- `pixi run --frozen -e platform-ci-test helm version` -- exit 0, `v4.3.0+conda-forge`, inside the worktree's own env installed from the updated lock.
- `pixi run --frozen -e platform-ci-test bash -c 'cd src/platform && python -m pytest tests/test_helm_gate.py tests/test_chart_invariants.py tests/test_openfeature_file_flags.py -rs -q'` -- exit 0, 171 passed, no skips, no `helm not on PATH` line.
- `ruff check .`, `ruff format --check .`, `mypy platformapp config tests` in `platform-ci-test` -- each exit 0.
- `pixi run --frozen -e pyforge-guild platform-ci-local -- --test` (the local twin of the whole `test` job: system checks, ruff, mypy, policy, sqlmigrate, full suite) -- exit 0, 1100 passed, 13 skipped (none helm).
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- exit 0, 1909 passed, 2 skipped.
- Mutation, restored byte-for-byte: the `if os.environ.get("CI"):` branch replaced by `if False:` -- `test_helm_gate.py` fails `test_helm_absent_under_ci_fails_naming_helm` and `test_a_real_pytest_run_reports_each_branch[helm-absent-under-ci]` (2 failed, 5 passed).
- Re-run by the orchestrator after the implementer returned (exit codes read directly): the three-module `pytest` command (171 passed, 0 skipped, no `helm not on PATH` line); `ruff check`, `ruff format --check` and `mypy platformapp config tests` (each 0); `pyforge-steward-test` (0, 1909 passed, 2 skipped); the mutation (2 failed, 5 passed, restored with `cmp` exit 0); `pixi lock --check` (0, lock up to date); `pixi project export conda-environment -e build` against `environment.yaml` (`cmp` exit 0, byte-identical); `python scripts/spec_surface_reconcile.py` (0) and `spec-surface-check` (0), both with the baseline file untouched, no stamp.
- Exit codes 0 (implementer): `chain-currency-sweep-check`, `story-status-check`, `chain-completeness-check`, `deferred-work-check` (after the intake), `governance-currency`, `llms-full-check`, `platform-ci-test-requirements-check`, `pixi-version-check`, `scripts/spec_surface_reconcile.py`. `pr-preflight` was not run in full.

### Residual risks

- **Open, by design:** the PR's Platform CI `test` log has not been read; nothing was pushed. The five chart-test deferrals (DW-FU-41-2-4, DW-FU-42-1-5, DW-FU-42-4-2, DW-steward-76-1, DW-steward-78-1-3) stay open until it shows the chart tests ran.
- `importorskip("yaml")` in `_import_yaml` (and the flags module's `importorskip("openfeature...")`) still skip silently under CI; PyYAML is only a transitive dependency of `platform-ci-test` (`DW-steward-80-1-2`).
- `CI` unset on a CI-like runner that does not export it would skip rather than fail; GitHub Actions exports `CI=true`, and `platform-ci-local.sh` deliberately does not set it.
- **Baseline stamp reverted.** The implementer ran a scoped `--write-baseline` for `spec-pyforge-unifying-strategy`. It re-stamped about 40 paths, of which only five are this story's (`pixi.toml`, the two new test files and the two edited modules); the rest were other stories' (78.1, 77.1, 76.2) pending drift, which a producer must not accept. This run's rule is never to pass `--write-baseline`, so the orchestrator restored `scripts/.spec-surface-baseline.json` to the baseline revision (`git restore --source=423056819c2ecb0f2d244e3109edbe0df03621a4`, that one path). Both `spec_surface_reconcile.py` and `spec-surface-check` exit 0 without it. The stamp stays the operator's, at landing, from a clean tree.
- The `.memlog.md` entries (and the new-file docstrings before the orchestrator's edit) say 73 chart tests; the true count is 74 (67 in `test_chart_invariants.py`, 7 in `test_openfeature_file_flags.py`). The memlog is append-only, so its figure stands uncorrected; the two new files no longer state a count.
