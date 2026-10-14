---
title: "103.4: The `ci-surface-gates` tests write their fixtures under `tmp_path`"
type: 'fix'
created: '2026-10-14'
status: 'in-review'
baseline_revision: '6e1918fea260f9ebe879ae52d549eeba70029207'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-99-1-the-ci-surfaces-are-declared-once-and-the-workflows-are-judged-against-them.md
  - tests/scripts/test_ci_surface_gates.py
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
- **A guard, active for every test.** An autouse function-scoped fixture reads
  `git --no-optional-locks status --porcelain --untracked-files=all --ignored=matching --
  tests/scripts/fixtures/ci_surface_gates` in the repo root before and after each test. It fails the test when the
  read after it has a line the read before it did not, naming each new line and the fix, so the first failing test is
  the writer. `--ignored=matching` makes an ignored file (`!!`) count, and `--no-optional-locks` keeps the read from
  taking `index.lock`. It reads `git`'s exit code: a failed status read fails too, so the guard is never silently off.
  Function scope makes it hold under xdist (`-n auto --dist loadgroup`) and in any order. It costs two `git status`
  reads per test (about 13 ms each here).
- **The guard is tested.** `test_fixture_tree_guard_is_active_and_sees_modified_untracked_and_ignored_files` asserts
  that the guard fixture is in the test's own `request.fixturenames`, and that the repo's fixture tree is clean, so a
  leftover from an earlier run fails this one test. It then exports a decoy `GIT_DIR` and `GIT_WORK_TREE`, as a linked
  worktree's git hook does, and isolates git with `monkeypatch`: it removes `GIT_DIR`, `GIT_WORK_TREE`,
  `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`, `GIT_COMMON_DIR`, `GIT_CEILING_DIRECTORIES` and `GIT_PREFIX`, and sets
  `GIT_CONFIG_GLOBAL=/dev/null` and `GIT_CONFIG_NOSYSTEM=1`. It builds a scratch repository under `tmp_path` with one
  committed fixture and asserts that git created that repository's own `.git` and left the decoy alone. It then runs
  the guard's status read there: empty when clean, then a ` M` line for the edited file, a `??` line for a new one and
  a `!!` line for an ignored one. Every scratch commit runs with `core.hooksPath=/dev/null`, `commit.gpgsign=false`
  and `--no-verify`.

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
- **AC4 — The guard.** An autouse function-scoped fixture fails any test that adds a line to
  `git --no-optional-locks status --porcelain --untracked-files=all --ignored=matching --
  tests/scripts/fixtures/ci_surface_gates`, and fails when the status read itself fails.
  `test_fixture_tree_guard_is_active_and_sees_modified_untracked_and_ignored_files` proves that:
  - the fixture is active for it;
  - the repo's fixture tree reads empty;
  - with a decoy `GIT_DIR` exported, the isolated scratch repository's git creates its own `.git` and leaves the decoy
    alone;
  - the status read returns no line for a clean scratch tree, and a ` M`, a `??` and a `!!` line for a modified, an
    untracked and an ignored fixture.
- **AC5 — No assertion weakens.** Every test that exists at `6e1918fea2` still exists under the same name, with the
  same inputs, the same detector arguments and the same assertions. The only test added is AC4's.
- **AC6 — Mutations.** Each change below fails a named test, and the Auto Run Result records which. Each is reverted.
  - one test's case root moved back under the repository's `tests/scripts/fixtures/ci_surface_gates/`: the guard fails
    that test, and no other;
  - `--untracked-files=no` in the guard's status read: the read fails, so every test fails;
  - the guard declared without `autouse=True`, `--ignored=matching` dropped, or `GIT_DIR` dropped from the scrub: AC4's
    named test fails;
  - an untracked file left in the repo's fixture tree before the run: AC4's named test fails, and no other.
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
- The per-test guard fails only the test that adds a line, so a leftover from an earlier run is caught by AC4's named
  test alone, once per run.
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
| The file runs under a linked worktree's git hook (`GIT_DIR` exported) | not applicable | the scratch repository ignores it; the shared `.git/config` and the branch are untouched |
| A file matching an ignore rule (`*.log`) lands in the fixture tree | not applicable | it reads `!!` and the guard fails the writer |

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
- `.pixi/envs/pyforge-guild/bin/ruff check tests/scripts/test_ci_surface_gates.py` (the root config) — expected: exit 0.
- `pixi run --frozen -e pyforge-scribe-pg scribe-pg-up`, then `pixi run -e pyforge-guild pr-preflight` — expected: exit 0, read from the exit code, and `git status --porcelain` empty after it (AC7).
- `git push` — expected: the `pre-push-preflight` hook passes with no `PYFORGE_PREFLIGHT_SKIP` (AC7).

## Spec Change Log

- 2026-10-14: minted on the operator's standing direction of 2026-10-14 ("be autonomous, keep merging ... complete as
  much as you can autonomously"; "pre-existing findings are fixed now"). `type: fix`, no flag, no CAP. Bound to
  `spec-pyforge-steward` CAP-166 through Stories 99.1 and 99.6.
- 2026-10-14, review 1 (failed): the Approach, AC4, AC6, the residual risk and the I/O matrix follow the review's
  fixes. The guard fails only the writer and sees ignored files; the named test isolates git from a hook's exports
  and catches a leftover; `tests/scripts/fixtures/ci_surface_gates/` leaves `context:`.

## Auto Run Result

Status: in-review (implemented by hand in worktree `local-recipes-wt-chain-steward-103-4-fixture-writes-2026-10-14`,
branch `chain-steward-103-4-fixture-writes-2026-10-14`, on `6e1918fea2` plus the chain commit).

What changed:
- `tests/scripts/test_ci_surface_gates.py`: the twelve writing tests take `tmp_path` and build every case there under
  the names they used before; `FIXTURES` became the `FIXTURE_TREE` pathspec, which only the guard reads. The autouse
  `_fixture_tree_stays_clean` fixture and `test_fixture_tree_guard_is_active_and_sees_untracked_and_modified_files`
  were added. No import line changed, and no other test's body changed.
- `tests/scripts/fixtures/ci_surface_gates/`: all 18 files removed with `git rm`; nothing there stays tracked.

Verification (2026-10-14):
- Measured before the change (AC2, AC3), at `6e1918fea2` in `pyforge-ci`: a run on a clean checkout, 20 passed, left
  `unregistered/registry.yaml` and `workflows_match.json` modified (`dashboard.yml` -> `pages.yml` three times in the
  first, once in the second). With the directory deleted, a run recreated all 18 tracked paths. Each test run alone
  against an emptied directory wrote exactly these, and the eight others wrote nothing:
  - `test_fixture_unregistered_pause_var`, `test_fixture_row_switch_not_in_if`, `test_fixture_bad_switch_name`,
    `test_fixture_wrong_pause_comparison`, `test_fixture_missing_job`, `test_fixture_paused_missing_review_by`: their
    case's `.github/workflows/sample.yml` and `registry.yaml` (12 files);
  - `test_live_fixture_match_exits_zero`, `test_live_extra_disabled_workflow_exits_one`,
    `test_live_paused_manually_row_but_active_exits_one`: `workflows_match.json`, `workflows_extra_disabled.json`,
    `workflows_active_mismatch.json`;
  - `test_matrix_wrapped_if_parsed_like_bare`, `test_matrix_multiline_if_collects_both_vars`,
    `test_high_cost_row_without_canary_fails_check`: their case's `sample.yml` (3 files).
  No checked-in input was found, so no file stays (AC3).
- With the deletions staged but not committed, the file passed 21 tests and the guard raised 21 teardown errors, each
  listing the 18 `D` lines: the guard sees the tree, staged changes included.
- After the change (AC1, AC4, AC7), each with `git status --porcelain --untracked-files=all` empty afterwards:
  - `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_ci_surface_gates.py -q`: 21 passed, exit 0;
  - `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_ci_surface_gates.py -q`: 21 passed, exit 0;
  - the same file under `-n auto --dist loadgroup` in `pyforge-ci`: 21 passed, exit 0;
  - `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test`: 1555 passed, 28 skipped, exit 0;
  - `pixi run --frozen -e pyforge-doctor pyforge-doctor-aggregate-scripts-test`: 59 passed, exit 0.
  `tests/scripts/fixtures/ci_surface_gates/` is not recreated, and `git ls-files` lists nothing under it (AC2).
- AC6, mutations, each restored from a saved copy and checked with `cmp`:
  - `test_live_fixture_match_exits_zero` writing `workflows_match.json` into the repo's fixture tree again: the guard
    failed at teardown of that test (`?? tests/scripts/fixtures/ci_surface_gates/workflows_match.json`), and of the
    eight tests after it in file order while the stray file stayed (21 passed, 9 errors). The stray file was removed;
  - `--untracked-files=no` in `_tree_status`: `test_fixture_tree_guard_is_active_and_sees_untracked_and_modified_files`
    failed (the `??` line missing, only ` M` reported);
  - the guard declared without `autouse=True`: the same test failed (`_fixture_tree_stays_clean` not in
    `request.fixturenames`).
- AC5: the 20 tests of `6e1918fea2` keep their names, inputs, detector arguments and assertions; the one test added is
  AC4's.
- AC8: `spec-pyforge-steward`'s memlog reconciles `tests/scripts/test_ci_surface_gates.py` and the removed fixtures
  (no fixture path is on any Spec's baseline), then one scoped stamp, re-stamped after the last code edit;
  `pixi run -e pyforge-guild spec-surface-check` exits 0. Its 123 `drift-presumed` warnings are all
  `spec-pyforge-herald`'s deck files, present unchanged at `6e1918fea2`, and not this story's.
- AC7, the full preflight: `pixi run --frozen -e pyforge-scribe-pg scribe-pg-up`, then `pixi run -e pyforge-guild
  pr-preflight` on `f189bfc149`: exit 0 (read from the exit code). It ran 20 of 36 lanes, with 16 skipped by their
  workflow's own rules, and every lane that ran was `ok`: `detectors-ci`, `pyforge-doctor-scripts-test`,
  `pyforge-doctor-aggregate-scripts-test`, the eight station suites (`pyforge-steward-test`: 2606 passed, 1 skipped),
  `pages-check` and the docs-site checks. `git status --porcelain --untracked-files=all` was empty afterwards.

## Review (2026-10-14, independent)

Verdict: failed, one blocker (PR #2222 at `13b92761f7`). Each finding went back to implementation (review loop
iteration 1), and the fix column records what landed. The named guard test is now
`test_fixture_tree_guard_is_active_and_sees_modified_untracked_and_ignored_files`; the Auto Run Result above records
the first pass under its old name.

| # | Severity | Finding | Fix |
|---|---|---|---|
| 1 | BLOCKER | The scratch-repo guard test ran `git` with the caller's whole environment, though the Approach and the memlog said the global and system config were off; only `-c` overrides were passed. Under a linked worktree's pre-push hook git 2.43 exports `GIT_DIR=<main>/.git/worktrees/<name>`, and with that inherited the test set `core.bare=true` in the shared `.git/config` and committed `seed` onto the current branch. The reviewer reproduced both in scratch repositories. | `_isolate_git(monkeypatch)` deletes `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`, `GIT_COMMON_DIR`, `GIT_CEILING_DIRECTORIES` and `GIT_PREFIX`, and sets `GIT_CONFIG_GLOBAL=/dev/null` and `GIT_CONFIG_NOSYSTEM=1` (the precedents: `test_mason_cfe_surface_check.py`'s `_isolate_git_env`, `test_fleet_poll_sync.py`'s `_git_env`). The test exports a decoy `GIT_DIR` and `GIT_WORK_TREE` first, then asserts that git made the scratch repository's own `.git` and left the decoy alone. Reproduced in a scratch main repository with a linked worktree, running the guard test with `GIT_DIR=<main>/.git/worktrees/wt` exported: the `13b92761f7` file set `core.bare=true` in the scratch main and committed `seed` onto the worktree's branch; the fixed file passed, and `core.bare` stayed `false` with no new commit. The real primary checkout reads `core.bare=false` and has no `seed` commit, because `scripts/pre_push_preflight.sh` unsets `GIT_DIR` before `pr-preflight`. |
| 2 | NIT | The guard missed files that match ignore rules (`*.log`, `*.tmp`, `__pycache__/`, `.venv`, a global excludesFile). | `_tree_status` passes `--ignored=matching`, so an ignored file reads `!!` and counts; the named test covers a `!!` line for a `*.log` file. |
| 3 | NIT | A stray file failed the teardown of every later test (15 errors in mutation 1), and the read could take `index.lock`. | The guard snapshots the status before each test and fails only on new lines, so only the writer fails. The named test also asserts the repo's fixture tree is clean, so a leftover from an earlier run fails it once. The read runs `git --no-optional-locks status`. |
| 4 | NIT | Seven older `subprocess.run` calls lacked `check=` (ruff `PLW1510` under the root config; `ruff check` on the file exited 1). | `check=False` on each; behaviour unchanged. `ruff check tests/scripts/test_ci_surface_gates.py` exits 0. |
| 5 | NIT | `context:` still listed the removed `tests/scripts/fixtures/ci_surface_gates/`; the memlog read "Story 103.3s". | The path left `context:`; a one-line correction is appended to the `spec-pyforge-steward` memlog, which is append-only. |
| 6 | OUT OF SCOPE | `test_six_fixture_rules_together_six_findings` is vacuous: it takes the `len()` of a six-item literal set, so Story 99.1's AC2 has no test. AC5 freezes the existing assertions. | Deferred to a follow-up story, which the coordinator is chaining. |

Verification after review 1 (2026-10-14):
- The file: 21 passed in `pyforge-ci`, in `pyforge-guild` and in `pyforge-ci` under `-n auto --dist loadgroup`, each
  exit 0 with `git status --porcelain` empty afterwards.
- `.pixi/envs/pyforge-guild/bin/ruff check tests/scripts/test_ci_surface_gates.py`: exit 0. `ruff format --diff`
  shows only three hunks, all on lines this story did not touch (the module docstring's blank line, the
  `grandfathered_names` assertion and one registry dict), left alone beside Story 103.3's coming import edit.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test`: 1555 passed, 28 skipped, exit 0.
  `pixi run --frozen -e pyforge-doctor pyforge-doctor-aggregate-scripts-test`: 59 passed, exit 0. The tree was clean
  after both.
- Mutations, each restored from a saved copy and checked with `cmp`:
  - `test_live_fixture_match_exits_zero` writing into the repo's fixture tree: only that test failed, at teardown
    (`?? …/workflows_match.json`; 21 passed, 1 error);
  - `--untracked-files=no`: git refuses it beside `--ignored` ("Unsupported combination"), so the read fails and every
    test errors; the guard fails closed;
  - the guard without `autouse=True`: the named test failed (`_fixture_tree_stays_clean` not in `request.fixturenames`);
  - `--ignored=matching` dropped: the named test failed (the `!!` line missing);
  - `GIT_DIR` dropped from `_LEAKY_GIT_VARS`: the named test failed ("git followed the exported GIT_DIR instead of its
    own cwd");
  - an untracked `leftover.json` in the repo's fixture tree before the run: only the named test failed, naming it.
- `spec-pyforge-steward`'s memlog records the review, the correction and the reconcile, then one scoped stamp after
  the last code edit; `spec-surface-check` exits 0.
