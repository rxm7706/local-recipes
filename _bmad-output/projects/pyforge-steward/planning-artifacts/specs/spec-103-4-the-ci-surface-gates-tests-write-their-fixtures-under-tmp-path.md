---
title: "103.4: The `ci-surface-gates` tests write their fixtures under `tmp_path`"
type: 'fix'
created: '2026-10-14'
status: 'ready-for-dev'
baseline_revision: '6e1918fea260f9ebe879ae52d549eeba70029207'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-99-1-the-ci-surfaces-are-declared-once-and-the-workflows-are-judged-against-them.md
  - tests/scripts/test_ci_surface_gates.py
  - tests/scripts/fixtures/ci_surface_gates/
  - scripts/ci_surface_gates.py
  - scripts/_ci_surface_gates_lib.py
  - docs/governance/ci-surfaces.yaml
  - .pre-commit-config.yaml
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** running `tests/scripts/test_ci_surface_gates.py` edits tracked files. Every `pr-preflight` runs it, so
since Story 102.1 every preflight leaves the tree dirty, and the pre-push hook refuses the push even when the verdict
is ok. Line numbers are at `6e1918fea2`.

- **The writes.** Twelve of the file's 20 tests build what they check under `FIXTURES`
  (`tests/scripts/fixtures/ci_surface_gates/`, `:20`), in the tracked tree:
  - six rule cases each write `<case>/.github/workflows/sample.yml` and `<case>/registry.yaml`
    (`test_fixture_unregistered_pause_var` `:61`, `test_fixture_row_switch_not_in_if` `:91`,
    `test_fixture_bad_switch_name` `:144`, `test_fixture_wrong_pause_comparison` `:196`, `test_fixture_missing_job`
    `:248`, `test_fixture_paused_missing_review_by` `:300`);
  - three live-mode tests each write one workflow-state JSON (`test_live_fixture_match_exits_zero` `:381`,
    `test_live_extra_disabled_workflow_exits_one` `:399`, `test_live_paused_manually_row_but_active_exits_one` `:409`);
  - three parser tests each write one `sample.yml` (`test_matrix_wrapped_if_parsed_like_bare` `:435`,
    `test_matrix_multiline_if_collects_both_vars` `:448`, `test_high_cost_row_without_canary_fails_check` `:475`).
- **Two of them copy the live registry.** `test_fixture_unregistered_pause_var` dumps
  `docs/governance/ci-surfaces.yaml` into `unregistered/registry.yaml`, and `test_live_fixture_match_exits_zero` builds
  `workflows_match.json` from its rows. Story 102.1 renamed `.github/workflows/dashboard.yml` to `pages.yml` and
  updated the registry, so the tracked copies went stale and every run rewrites them.
- **Nothing there is an input.** Measured at `6e1918fea2`: with the whole directory deleted, the file passes (20 passed
  in `pyforge-ci`) and recreates all 18 tracked paths. Each path is written by exactly one test, and no test reads a
  file there that it did not write first. A run on a clean checkout leaves exactly two files modified,
  `unregistered/registry.yaml` and `workflows_match.json`; the other 16 come back byte-identical. All 18 entered git
  through the dispatch auto-checkpoints `2c6ff4dd4a` (`wip: 99.1`) and `aa8abbe32e` (`wip: 99.6`, `missing_canary`),
  never as authored inputs.
- **The refusal.** `.pre-commit-config.yaml`'s `pre-push-preflight` hook runs `pr-preflight`. pre-commit fails a hook
  that modifies files ("files were modified by this hook") whatever its exit code. Two pushes on 2026-10-14 went out
  with `PYFORGE_PREFLIGHT_SKIP=1` and a journaled reason.

**Approach:**
- **Every case under `tmp_path`.** Each of the twelve tests takes pytest's `tmp_path` and builds its case root, its
  registry and its workflow-state JSON there, under the same relative names it uses today (`<case>/.github/workflows/
  sample.yml`, `<case>/registry.yaml`, `workflows_*.json`). The workflow text, the registry dicts, the detector
  arguments and every assertion stay as they are. The `FIXTURES` constant goes; nothing else uses it.
- **The generated files leave git.** All 18 tracked files under `tests/scripts/fixtures/ci_surface_gates/` are removed
  with `git rm`. None is a checked-in input, so none stays. The directory then holds nothing tracked.
- **A guard, active for every test.** An autouse function-scoped fixture runs, after each test,
  `git status --porcelain --untracked-files=all -- tests/scripts/fixtures/ci_surface_gates` in the repo root and fails
  the test when the output is not empty, naming each line and the fix. It reads `git`'s exit code: a failed status read
  fails too, so the guard is never silently off. Function scope makes it hold under xdist (`-n auto --dist loadgroup`)
  and in any order, and it names the test that wrote. It costs one `git status` per test (about 13 ms here).
- **The guard is tested.** `test_fixture_tree_guard_is_active_and_sees_untracked_and_modified_files` asserts that the
  guard fixture is in the test's own `request.fixturenames`. It then builds a scratch repository under `tmp_path` with
  one committed fixture and runs the guard's status read there: empty when clean, then a ` M` line for the edited file
  and a `??` line for a new one. It runs `git` with the global and system config off and `--no-verify`, so no user
  hook or signing setting reaches the scratch commit.

**Rejected:**
- **Regenerating the two stale files and keeping them tracked.** They go stale again on the next registry edit. Any
  tracked copy of a generated file can drift the same way.
- **A `.gitignore` entry for the directory.** It hides the writes instead of stopping them, and the guard could no
  longer see one.
- **A guard that runs the whole file again in a subprocess.** It doubles the file's run time, and with xdist one
  worker's run can race another's.
- **A module-scoped guard.** Under xdist each worker tears it down at a different time, and the failure names no test.
- **Moving the file's yaml-needing tests out of `pyforge-ci`.** Story 103.3 owns the env split. This story changes no
  import line and no `pixi.toml`.

Ledger key: `103-4-the-ci-surface-gates-tests-write-their-fixtures-under-tmp-path`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-166 (Story 99.1, the CI surfaces registry and its offline gate;
  Story 99.6 added the canary case). This story changes how the gate's tests build their cases, not what the gate
  checks. It mints no CAP and changes no `SPEC.md`.
- **Governance.** `tests/scripts/test_ci_surface_gates.py` is on `spec-pyforge-steward`'s surface
  (`scripts/.spec-surface-baseline.json`). The fixture files are on no Spec's baseline.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag.
- **Origin.** Found by the orchestrating session on 2026-10-14 while pushing, verified the same day; recorded in
  `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-14 (CI and estate follow-ups) entry's addition.

## Acceptance Criteria

- **AC1 — Every case under `tmp_path`.** Each of the twelve tests named in the Intent builds every file it generates
  under its own `tmp_path`. No test in the file writes, creates or deletes a path under the repository root, and the
  `FIXTURES` constant is gone (`grep -n FIXTURES tests/scripts/test_ci_surface_gates.py` finds no write target).
- **AC2 — The generated files leave git.** `git ls-files tests/scripts/fixtures/ci_surface_gates` is empty. The 18
  removed paths are exactly the 18 the twelve tests write, and each is shown to be written by a test before it is
  removed (the Intent's measurement, repeated in the Auto Run Result).
- **AC3 — A checked-in input stays.** No file under `tests/scripts/fixtures/ci_surface_gates/` is read by a test
  without being written by it first, so no file stays. If the implementation finds one, it stays tracked, and the Auto
  Run Result names it.
- **AC4 — The guard.** An autouse function-scoped fixture fails any test after which
  `git status --porcelain --untracked-files=all -- tests/scripts/fixtures/ci_surface_gates` is non-empty, or the status
  read itself fails. `test_fixture_tree_guard_is_active_and_sees_untracked_and_modified_files` proves the fixture is
  active for it, and that the status read returns an empty string for a clean scratch tree, a ` M` line for a modified
  tracked fixture and a `??` line for an untracked one.
- **AC5 — No assertion weakens.** Every test that exists at `6e1918fea2` still exists under the same name, with the
  same inputs, the same detector arguments and the same assertions. The only test added is AC4's.
- **AC6 — Mutations.** Each change below fails a named test, and the Auto Run Result records which. Each is reverted.
  - one test's case root moved back under the repository's `tests/scripts/fixtures/ci_surface_gates/`: the guard fails
    that test;
  - `--untracked-files=no` in the guard's status read: AC4's named test fails.
- **AC7 — Green, and the tree clean.** Each of the following exits 0, and `git status --porcelain` is empty after it:
  - `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_ci_surface_gates.py -q`;
  - `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_ci_surface_gates.py -q`;
  - `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` and
    `pixi run --frozen -e pyforge-doctor pyforge-doctor-aggregate-scripts-test` (the Detectors `scripts-suite` steps);
  - `pixi run -e pyforge-guild pr-preflight`.
  The branch's push then passes the `pre-push-preflight` hook with no `PYFORGE_PREFLIGHT_SKIP`.
- **AC8 — The surface reconciled.** The changed governed paths get a surface-reconcile entry on the memlog of every
  Spec `spec-surface-check` names, then one scoped stamp per Spec, and `spec-surface-check` exits 0.

## Boundaries & Constraints

**Always:**
- Keep every existing test's name, inputs, detector arguments and assertions.
- Make the guard fail closed: a status read that fails is a failure, never a pass.
- Reconcile every governed path the change touches on each governing Spec's memlog, then stamp each scoped (AGENTS.md
  pre-PR item 5).

**Never:**
- Never change an import line in the test file, `pixi.toml`, `pixi.lock` or any environment: Story 103.3 owns which
  environment runs which `tests/scripts` file, and its guards.
- Never change `scripts/ci_surface_gates.py`, `scripts/_ci_surface_gates_lib.py`, `docs/governance/ci-surfaces.yaml`
  or a workflow file.
- Never ignore the fixture directory in `.gitignore`.

**Residual risk:**
- A checkout made before this merge that still holds the two modified copies keeps them as local edits to deleted
  files. Merging `main` over them stops on the local change; `git checkout -- tests/scripts/fixtures/ci_surface_gates`
  before the merge clears it. A fresh worktree from `main` has none.
- The guard covers this file's fixture tree only. Another `tests/scripts` file that writes into the tracked tree is not
  caught by it.

## I/O & Edge-Case Matrix

| Situation | Today (`6e1918fea2`) | After |
|---|---|---|
| The file runs on a clean checkout | 20 pass; `unregistered/registry.yaml` and `workflows_match.json` left modified | 21 pass; `git status --porcelain` empty |
| `pr-preflight` then `git push` | verdict ok; pre-push hook fails, "files were modified by this hook" | verdict ok; the hook passes |
| The registry gains, renames or drops a row | the tracked copies go stale on the next run | nothing tracked to go stale |
| A future test writes into the fixture tree | silently, and an auto-checkpoint may commit it | the guard fails that test |
| xdist spreads the file over workers | each worker writes the shared tracked paths | each test writes only its own `tmp_path` |
| `git status` cannot run in the repo root | not checked | the guard fails, naming the error |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-166 (Story 99.1's offline gate and its tests; Story 99.6's canary
  case). No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-14 (CI and estate follow-ups) entry, its
  "Added the same day (ci-surface-gates fixture writes)" addition.
- Epic: Epic 103, beside Stories 103.1-103.3. Epic 99, which shipped CAP-166, is `done`.
- Ledger key: `103-4-the-ci-surface-gates-tests-write-their-fixtures-under-tmp-path`.
- Ledger status at mint: `backlog`.
- Deps: none. Story 103.3 will add a module-level guard to this file's imports and may move the file to another
  environment's task; this story touches neither, so the two merge independently.
- Spec: the `spec-pyforge-steward` memlog records the operator's direction, the evidence, the design and this mint.
- Surface: `marshal-policy.toml` `[epic_surfaces]."103"` covers `tests/scripts/**`.
- Minted 2026-10-14 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass. This is the station's
  `verify_commands` (MRS-GATE-010 binding); this story changes no steward package file.

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_ci_surface_gates.py -q`, then `git status --porcelain` — expected: exit 0, then empty (AC1, AC4, AC7).
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_ci_surface_gates.py -q`, then `git status --porcelain` — expected: exit 0, then empty (AC7).
- `git ls-files tests/scripts/fixtures/ci_surface_gates` — expected: empty (AC2).
- The AC6 mutations, one at a time, re-running the file each time — expected: each fails its named test. Revert each.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` and `pixi run --frozen -e pyforge-doctor pyforge-doctor-aggregate-scripts-test` — expected: exit 0, tree clean (AC7).
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamp (AC8).
- `pixi run --frozen -e pyforge-scribe-pg scribe-pg-up`, then `pixi run -e pyforge-guild pr-preflight` — expected: exit 0, read from the exit code, and `git status --porcelain` empty after it (AC7).
- `git push` — expected: the `pre-push-preflight` hook passes with no `PYFORGE_PREFLIGHT_SKIP` (AC7).

## Spec Change Log

- 2026-10-14: minted on the operator's standing direction of 2026-10-14 ("be autonomous, keep merging ... complete as
  much as you can autonomously"; "pre-existing findings are fixed now"). `type: fix`, no flag, no CAP. Bound to
  `spec-pyforge-steward` CAP-166 through Stories 99.1 and 99.6.
