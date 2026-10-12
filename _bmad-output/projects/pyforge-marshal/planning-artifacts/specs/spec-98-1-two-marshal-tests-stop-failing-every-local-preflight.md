---
title: '98.1: Two marshal tests stop failing every local preflight'
type: 'fix'
created: '2026-10-12'
status: 'in-review'
baseline_revision: '6b5029f362885d615748f004fd3a8849532bc9cd'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/tests/integration/test_performance_gates.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_check.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/referenced_deps.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
deferred:
  - summary: >-
      `marshal seed check` spends about 4 s of NFR-P1's 5 s budget in machine-readiness probes, more when `doctor` is on PATH.
    evidence: |-
      Measured 2026-10-12 on the 1,200-file NFR-P1 fixture: run_check's own CPU 0.32 s, child CPU 3.74 s. referenced_dep_findings spawns `bmad-loop --version` (1.4 s wall) and `copier --version` (2.6 s wall), and first tries `python -m pyforge.doctor.sources genesis-referenced-deps --json` whenever `doctor` is on PATH. Story 98.1 stubs the probe in the two NFR-P1 tests, which measure the walk; nothing now times the real end-to-end command against NFR-P1.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/referenced_deps.py:104
    severity: medium
---

<intent-contract>

## Intent

**Problem:** On 2026-10-12 the local pre-push `pr-preflight` refused four pushes from two planning-only branches on the
same two marshal tests, while CI's `marshal-test` passed the same trees. Each push needed a journaled
`PYFORGE_PREFLIGHT_SKIP`. Line numbers below are at `6b5029f362`.

- **The NFR-P1 budget tests.** `tests/integration/test_performance_gates.py::test_check_under_nfr_p1_budget` and
  `tests/unit/test_seed_verbs_check.py::test_run_check_completes_within_the_nfr_p1_budget` time `run_check` with
  `time.perf_counter()` against 5 s on a 1,200-file tree, and read 5.10 s to 8.93 s under the preflight. A profile of
  `run_check` on that tree: own CPU 0.32 s, child CPU 3.74 s. The children are the machine-readiness probe in
  `seed/detect/referenced_deps.py`: `bmad-loop --version` (1.4 s wall) and `copier --version` (2.6 s wall), and, when
  `doctor` is on PATH (every preflight lane runs from the Guild environment), a Doctor subprocess tried first. That
  fixed cost does not depend on the tree and stretches under the preflight's parallel lanes. The unit test's own
  docstring says it measures the walk.
- **The packaging-gate test.** `tests/unit/test_dispatch_verification.py::test_evaluate_dispatch_verification_pre_existing_packaging_gate_warns`
  expects `verified` and reads `refused`. Its `PackagingFailProcess` (:1688) fails any command where
  `"pyforge-marshal-test" in " ".join(tokens)`. `pr-preflight` names each lane's scratch directory after the lane
  (`pyforge/steward/preflight.py`, `_lane_scratch_env`), so `tmp_path` sits under
  `…/pyforge-marshal-test/pytest-basetemp/popen-gw0/…`. The commit-attribution check runs `git` with the worktree path
  in its argv, the substring matches, the fake returns exit 1, and the evaluation adds `MRS-GATE-009` ("could not read
  'refs/remotes/origin/main...HEAD'"), an error. Reproduced in 1.2 s with `--basetemp` under a directory named
  `pyforge-marshal-test`; under any other name the test passes. Bare runs, `-n auto`, two workers and the Guild PATH
  alone all passed, which is why the first diagnosis (a module cache poisoned across an xdist worker) was wrong.

**Approach:**

- **NFR-P1 tests:** `monkeypatch.setattr("pyforge.marshal.seed.verbs.check.referenced_dep_findings", ...)` returning
  `()` in both tests, with a comment giving the measured cost. The assertion stays `time.perf_counter()` against 5 s.
  `run_adopt` never calls the probe, so the NFR-P2 test does not change.
- **Packaging-gate fake:** match `"pyforge-deps-test"` and `"pyforge-marshal-test"` as exact members of the argv list.
  Parametrize the test over a worktree parent of `""` and `"pyforge-marshal-test"`, so it pins the path-independence
  without relying on how pytest names `tmp_path`. The verdict assertion's message lists every finding as
  `(code, severity, message)`.
- **Team memory:** correct `.claude/memory/feedback/the-local-pr-preflight-marshal-lane-pyforge-marshal-test-can.md`,
  which blamed load and a poisoned cache.

Ledger key: `98-1-two-marshal-tests-stop-failing-every-local-preflight`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-13** (seed check; PRD NFR-P1: `check` completes in under 5 s on a `local-recipes`-sized
  repo). The two tests keep that budget on the walk they were written for.
- **`spec-pyforge-marshal` CAP-139** (verify blast radius, `pre-existing-gate`, from `spec-marshal-drain-self-resolution`
  CAP-5). The packaging-gate test keeps asserting that a failure outside the story's diff warns instead of refusing.
- **No flag** (`spec-feature-flag-governance` Q1, a fix). **No product code**: only tests and the memory entry change.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-12 (two tests red the local preflight). Operator
  ask: "Do this task here: “Fix two marshal tests that red local pr-preflight”".

## Acceptance Criteria

- **AC1 — The walk is timed.** Both NFR-P1 tests stub `seed.verbs.check.referenced_dep_findings` and assert a
  `time.perf_counter()` budget under 5 s; with the Guild environment's bin on PATH they finish in under 1 s each.
- **AC2 — The verdict does not depend on the path.** The packaging-gate test runs for worktree parents `""` and
  `"pyforge-marshal-test"` and reads `verified` for both, under `--basetemp` below a directory named
  `pyforge-marshal-test` and below one named otherwise.
- **AC3 — Mutation.** Restoring `"pyforge-marshal-test" in " ".join(argv)` in the fake fails the `pyforge-marshal-test`
  case, even under a neutral `--basetemp`.
- **AC4 — The lane under the preflight's conditions.** The full `pyforge-marshal-test` lane passes three times in a
  worktree with the Guild environment on PATH, `PYTEST_XDIST_AUTO_NUM_WORKERS=2`, and `TMPDIR` and `--basetemp` under a
  directory named `pyforge-marshal-test`.
- **AC5 — The gate.** `pixi run -e pyforge-guild pr-preflight` exits 0 on this branch.
- **AC6 — The record.** The team-memory entry names the two real causes; the probe cost is this spec's deferral.

## Boundaries & Constraints

- Nothing under `src/shared/packages/pyforge-marshal/src/` changes.
- NFR-P1 stays a wall-clock budget of 5 s; no test is skipped, marked `slow`, retried or loosened.
- `pyforge/steward/preflight.py`'s lane naming does not change; the tests stop depending on it.

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-marshal` CAP-13 and CAP-139. No CAP is minted and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-12 (two tests red the local preflight) entry.
- Epic: Epic 98 (new). Epics 12 and 28, which shipped the tests, are `done`.
- Ledger key: `98-1-two-marshal-tests-stop-failing-every-local-preflight`; status at mint `backlog`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."98"` (added with this mint).
- Minted and implemented 2026-10-12 in one PR; landed by hand with the subject
  `Merge pyforge-marshal/98-1 into main`, then `dispatch_land_finalize` for the promotion.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-marshal pytest "src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification.py::test_evaluate_dispatch_verification_pre_existing_packaging_gate_warns" --basetemp=<dir>/pyforge-marshal-test/bt -n0` — expected: 2 passed (AC2).
- The AC3 mutation against a scratch copy — expected: the `pyforge-marshal-test` case fails; revert.
- The full lane three times under the AC4 conditions — expected: exit 0 each.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python3 scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamp.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0 (AC5).

## Spec Change Log

- 2026-10-12: minted and implemented from the operator's ask. `type: fix`, no flag, no CAP; bound to
  `spec-pyforge-marshal` CAP-13 and CAP-139. The probe's end-to-end cost is deferred (frontmatter `deferred:`).
