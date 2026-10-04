---
title: "19.5: The testing kit's own suite runs in CI"
type: 'fix'
created: '2026-10-04'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - .github/workflows/pyforge-station-tests.yml
  - pixi.toml
  - src/shared/packages/pyforge-testing-kit/tests/unit/test_flags.py
  - src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit/flags.py
  - src/shared/packages/pyforge-core/tests/meta/test_conformance_lane_wired.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `pyforge-testing-kit` (Story 19.2, FR-130) is the cross-station seam every station's meta tests import. Its own suite runs nowhere.

- **No workflow runs it.** `.github/workflows/pyforge-station-tests.yml` names the kit only as a path trigger and as a shared-surface input that fires the eight station jobs and `core-test`. No job invokes `pyforge-testing-kit-test`.
- **The local twin skips it too.** The `pyforge-station-tests` aggregate in `pixi.toml` runs `pyforge-core-test` and the eight station tasks, so `pr-preflight` never runs the kit either.
- **It is already red.** Measured on 2026-10-04 at `main` `b656128eb6`: `pixi run --frozen -e pyforge-testing-kit pyforge-testing-kit-test` gives 1 failed, 69 passed. `tests/unit/test_flags.py::test_flagd_tree_has_the_platform_trees_shape` compares the kit's temporary flagd tree with `src/platform/config/flags.json`. Steward Story 76.2 (`spec-feature-flag-governance` CAP-5) added a flagd `metadata` block to every platform flag, and the kit's tree does not carry it. The test has been red since that change, and nothing saw it.

**Approach:**
- Add a `testing-kit-test` job to `pyforge-station-tests.yml`. It is a peer of `core-test` and runs the pixi task, never a file list.
- Gate the job on a new `testing_kit` output of the `changes` job. The output is true when the shared surface changed (the kit, `pyforge-core`, `pixi.toml`, `pixi.lock`, this workflow). It is also true when one of the two other inputs the suite reads changed: `django-pyforge` (the station API contract test imports it) and `src/platform/config/flags.json` (the shape check reads it). Add those two as `pull_request` and `push` path triggers.
- Add the kit's leg to the local `pyforge-station-tests` aggregate, right after the `pyforge-core-test` leg.
- Fix the red test. The kit's tree carries the platform tree's evaluation fields only. Only a composed tree reads flagd `metadata` (`pyforge.core.flags.compose`, which needs a `flag-overlays.json` beside the tree), and a kit tree never has overlays. Compare the evaluation fields, and say so in `flagd_tree`'s docstring.
- Pin the wiring with a kit meta test, the way `pyforge-core`'s `test_conformance_lane_wired.py` pins `core-test`.

Ledger key: `19-5-the-testing-kit-s-own-suite-runs-in-ci`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-testing-charter` CAP-3 (the shared kit) and CAP-4 ("CI invokes it"). This is a gap in shipped behaviour, so it mints no new CAP. Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.

## Acceptance Criteria

- Given a pull request that touches the kit, `pyforge-core`, `django-pyforge`, `src/platform/config/flags.json`, `pixi.toml`, `pixi.lock` or the workflow When `pyforge-station-tests` runs Then its `testing-kit-test` job runs `pixi run --frozen -e pyforge-testing-kit pyforge-testing-kit-test`
- Given a pull request that touches only one station When the workflow runs Then `testing-kit-test` is skipped
- Given the local `pyforge-station-tests` aggregate When it runs Then it runs the kit's leg after the `pyforge-core-test` leg, which stays first
- Given `main` with the platform tree's flagd `metadata` When the kit suite runs Then it passes
- Given the job, its gate, a trigger or the local leg removed When the kit's meta test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:**
- Run the pixi task, never an enumerated file list or a direct `pytest` call.
- Keep `pyforge-core-test` the first leg of the aggregate (`pyforge-core`'s meta test pins it).

**Never:**
- Never make the kit job a gate on the station jobs or on `core-test`.
- Never make the kit write fake governance `metadata` to satisfy the test.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (testing kit CI) entry.
- Epic: Epic 19. It reopens (operator ruling, 2026-10-04: a fix joins its own epic and reopens it).
- Ledger key: `19-5-the-testing-kit-s-own-suite-runs-in-ci`.
- Ledger status at mint: `in-progress`.
- Deps: —.
- Minted 2026-10-04 at the operator's request: "Wire the testing-kit suite into CI". Hand-built and hand-landed in one PR with its chain.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-testing-kit pyforge-testing-kit-test` — expected: pass, including the new meta test.
- `pixi run --frozen -e pyforge-core pyforge-core-test` — expected: pass (`test_conformance_lane_wired.py` still holds).
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (`test_workflow_path_filters_match.py` still holds).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

### 2026-10-04 — Build (hand-built in `chain-marshal-19-5`); ready for an independent review
- Measured after the build: the kit suite gives 80 passed (69 + the fixed shape test + 10 meta tests); `pyforge-core-test` gives 2221 passed; steward's `test_workflow_path_filters_match.py` passes.
- Where the build goes past the Approach, and why:
  - The workflow comment names the meta test without its directory. `pyforge-core`'s lane test reads every line up to the next job header as part of `core-test`'s block, and it refuses a `tests/meta` path there as an enumerated file list.
  - The two new triggers also fire the `guild-container` job (gated only on the `PAUSE_CONTAINER_BUILDS` variable, `true` today). Accepted: the image `COPY`s the whole checkout (`Containerfile` :79), so django-pyforge and the platform flag tree are image inputs too, the same as every station path that already triggers it.
  - `docs/dreams/pyforge-unifying-strategy.md`'s measured env matrix is refreshed (`scripts/pixi_env_matrix.py --update --dream …`). It was older than `pixi.lock` (bmad-drift `pixi-env-matrix-stale`); `pixi.lock` itself is unchanged.
  - The scoped testing-charter stamp also took in seven kit hashes this story did not touch (`README.md`, `pyproject.toml`, the package `pixi.toml`, `__init__.py`, `branch_diff_guard.py`, `cli_runner.py`, `test_branch_diff_guard.py`). Their memlog entries (2026-09-29/30, Story 74.1) already name them; 74.1's stamp was skipped.
  - Marshal 83.19 (#1860) landed the same `test_flags.py` fix first; the merge from `main` takes its wording.
  - `environment.yaml` is regenerated, as the `pixi.toml` rule requires. On `main` it was invalid YAML: its first line was a pixi `WARN` about `PIXI_PROJECT_MANIFEST`, captured by Story 86.6's Cursor session (`0b4a9112b3`, a `wip:` auto-checkpoint). The clean export drops only that line.

### 2026-10-04 — Independent review (against this spec): no HIGH, two MEDIUM, three LOW; all fixed in the branch
- MEDIUM 1, the new triggers fire `guild-container`: recorded above as an accepted cost (the image copies the whole checkout).
- MEDIUM 2, the meta test missed four mutations (a neutered `TESTING_KIT_CHANGED=true`, an extra `pytest` step, another job `needs:` the kit job, a dropped `pixi.toml` trigger): each detector now catches its mutation, with a test per mutation, and `INPUTS` names the shared-surface triggers.
- LOW 3, stale comments in the workflow (the job count, the shared-surface fan-out, the django-* trigger note): reworded.
- LOW 4, the job comment sat above the header and so inside `core-test`'s block: moved under the header, which restores the meta test's full path.
- LOW 5, the env-matrix refresh and the stamp catch-up were unrecorded: recorded above; the leg mutation test pins its message.
