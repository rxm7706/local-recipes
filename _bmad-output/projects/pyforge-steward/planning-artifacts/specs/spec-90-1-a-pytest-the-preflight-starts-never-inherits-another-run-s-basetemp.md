---
title: "90.1: A pytest the preflight starts never inherits another run's basetemp"
type: 'fix'
created: '2026-10-10'
status: 'in-progress'
baseline_revision: 'c0956c0f14fa632ab837b1cdd5c39cd3b8845fff'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-8-a-preflight-lane-s-scratch-lives-outside-the-checkout.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-88-1-the-preflight-runs-each-task-once-after-its-dependencies.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_suite_reduction.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight_suite_reduction.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight_scratch.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** under `pr-preflight`, steward's own suite fails nine tests that pass in CI. Each pytest those tests start
inherits the lane's `--basetemp`, and pytest refuses it. Line numbers below are at `a0f47b7301`.

- **How a lane gets its options.** `preflight.py` `_lane_scratch_env` (:248-:259) copies the preflight's environment
  and appends `--basetemp=<lane>/pytest-basetemp -o cache_dir=<lane>/pytest-cache` to whatever `PYTEST_ADDOPTS` it
  inherited (`prior`, :256-:258). Story 71.3 gave each lane its own basetemp and cache dir this way, and Story 71.8
  moved them outside the checkout. The pool builds every lane's env with it (:661), and every lane process, reduced
  suite segment and task `--collect-only` runs with that env (`_run_pixi_argv`, :364-:367).
- **How it reaches a child pytest.** Steward's preflight tests run inside the `pyforge-steward-test` lane, so they
  inherit the lane's `PYTEST_ADDOPTS`. Several of them start a child pytest in a scratch repo under `tmp_path`, and
  `tmp_path` lives under the lane's basetemp:
  - `preflight_suite_reduction.py` `collect_pytest_node_ids` (:416-:441) runs `pytest --collect-only -q` with
    `{**os.environ, **(env or {})}` (:420), so the parent's `--basetemp` goes with it;
  - the reduced-lane test helper `_run_reduced_lane_via_preflight`
    (`tests/unit/test_preflight_suite_reduction.py` :115-:169) hands its child pytest `os.environ.copy()` (:137);
  - a lane started by `run_preflight` from inside a test gets `_lane_scratch_env`'s value, which keeps the parent's
    `--basetemp` in front of its own.
- **Why pytest refuses it.** pytest splits `PYTEST_ADDOPTS` with `shlex.split` and validates every `--basetemp` it
  sees, not only the last one. A basetemp that is the working directory or one of its parents is an error ("basetemp
  must not be empty, the current working directory or any parent directory of it"). The child exits 4 before it runs a
  test.
- **What a child does with a basetemp it can use.** pytest deletes an explicit basetemp at start-up. A child that
  inherits a parent's basetemp and runs outside it wipes the parent's temp tree while the parent is still running.
  That is how marshal's lane lost its xdist workers' directories on 2026-10-10 (evidence below).

**Evidence:**
- **The red lane.** Hygiene PR #2092 (`hygiene-873-dark-2026-10-10`, head `a27146f8d7`) ran `pr-preflight
  --keep-going` as run `089d593c-38dc-4eb1-87ea-35477101f7d2` (28 lanes, `.steward/preflight-runs.jsonl` of that
  worktree). Its kept lane log `/tmp/pyforge-preflight-s0n28vwu/pyforge-steward-test.log` reads "9 failed, 2283
  passed, 2 skipped", each failure "argument --basetemp: basetemp must not be empty, the current working directory or
  any parent directory of it", "config source: via PYTEST_ADDOPTS". The nine:
  - `test_preflight_suite_reduction.py`: `test_reduced_and_gate_collections_partition_task` (both parameters),
    `test_empty_gate_directory_segment_passes`, `test_failing_segment_still_reds_lane`,
    `test_doctor_shape_single_complement_no_tests_selected`,
    `test_all_segments_no_tests_and_task_collects_nothing_reds`, `test_equal_marker_omits_gate_complement_segment`,
    `test_collect_pytest_node_ids_exit_five_is_empty`;
  - `test_preflight_scratch.py`: `test_pytest_sees_no_git_work_tree_outside_checkout`.
- **Reproduced on `a0f47b7301`** (2026-10-10): `pixi run --frozen -e pyforge-steward pytest
  src/shared/packages/pyforge-steward/tests/unit/test_preflight_suite_reduction.py
  src/shared/packages/pyforge-steward/tests/unit/test_preflight_scratch.py -q` passes 32 of 32 with
  `PYTEST_ADDOPTS` unset, which is how CI runs them. With `PYTEST_ADDOPTS="--basetemp=<dir> -o cache_dir=<dir>"` set,
  the same nine fail.
- **Two tests pass for the wrong reason.** Under the same inherited basetemp,
  `test_collect_pytest_node_ids_raises_on_failure` (:639) gets its `RuntimeError` from the usage error, not from the
  missing path it names. `test_pytest_fails_when_scratch_lives_inside_checkout_mutation`
  (`test_preflight_scratch.py` :132) gets its non-zero exit from the same exit 4, not from the `git` assertion it
  exists to prove. Both were checked on `a0f47b7301` by calling the same code with the outer `PYTEST_ADDOPTS`.
- **The cost.** Any change that makes the preflight run steward's whole suite, every `pyforge-core` edit included
  (the shared-surface rule), can never go green locally. #2092 went out under `PYFORGE_PREFLIGHT_SKIP`
  (`.steward/preflight-skips.log`, 2026-10-10T20:58:42Z) after each red lane was proved green outside the preflight.
- **The same class elsewhere, fixed in #2092.** Run `91398d3b-cc7d-4a1c-bd87-98c9db603e4c` lost marshal's lane:
  `/tmp/pyforge-preflight-_xqpl6d1/pyforge-marshal-test.log` shows 8976 errors, each a `FileNotFoundError` for
  `.../pyforge-marshal-test/pytest-basetemp/popen-gw0`. `test_dispatch_supervisor_main_coverage_floor.py`'s child
  pytest had inherited the lane's basetemp and wiped it. Marshal now drops `PYTEST_ADDOPTS` from that child's env
  (`b8d5910e57`). In run `e459c7a4-cd0e-453f-8276-c41ed2bd319c`, a marshal fake-VCS test matched a path substring
  against a basetemp under `.../pyforge-marshal-coverage-gate/`; marshal fixed that in `02b5372835`. Neither is
  steward's.

**Approach:** each pytest the preflight starts carries only its own basetemp and cache dir.
- **One pure helper in steward's preflight modules.** It takes a `PYTEST_ADDOPTS` value and returns it without any
  basetemp or cache-dir option. It tokenizes with `shlex.split`, as pytest does, and rebuilds with `shlex.join`. It
  removes `--basetemp=<dir>` and `--basetemp <dir>`, and a `cache_dir` override in each spelling pytest accepts:
  `-o cache_dir=<dir>`, `-ocache_dir=<dir>`, `-o=cache_dir=<dir>`, `--override-ini=cache_dir=<dir>` and
  `--override-ini cache_dir=<dir>`.
  Every other token stays, in order, `-p no:cacheprovider` included: it carries no path into the child. The helper
  lives in `preflight_suite_reduction.py`, which `preflight.py` already imports, so there is no import cycle and no
  new module.
- **The lane env (`_lane_scratch_env`).** It applies the helper to the inherited value, then appends the lane's own
  `--basetemp` and `-o cache_dir` once. A lane's pytest options are then the invoker's options plus the lane's own
  scratch, as Story 71.3 meant.
- **The node-id collection (`collect_pytest_node_ids`).** It applies the helper to `PYTEST_ADDOPTS` in the env it
  builds, after merging the caller's `env`. It adds no basetemp: `--collect-only` makes no temp dirs. When nothing is
  left, it drops the variable.
- **The reduced-lane test helper.** `_run_reduced_lane_via_preflight` builds its `LaneRunContext.env` with
  `preflight._lane_scratch_env(lane_dir)`, as the pool does at :661, instead of `os.environ.copy()`. The four tests
  that use it then exercise the env a real lane gets.
- **Tests that pass for the wrong reason.** `test_collect_pytest_node_ids_raises_on_failure` asserts the error names
  `definitely-not-a-real-path-xyz`. The scratch mutation test asserts the child's exit is 1 and its output carries the
  `git` assertion, so exit 4 from any inherited option can no longer satisfy it.
- **Unchanged:** which lanes run (Story 71.2), the reduced suite's segments and their outcomes (Stories 71.4, 71.9),
  dependency order and `--skip-deps` (Story 88.1), `cancelled`, `cancelled_by` and `blocked_by` (Stories 71.10,
  88.1), process cleanup (Story 71.11), the scratch root outside the checkout (Story 71.8), the journal, the exit codes
  0 / 1 / 2 / 130, `pr-preflight`'s command line, the `pre-push` hook and `PYFORGE_PREFLIGHT_SKIP`.

**Why this shape, per the steward spine:**
- **Where the fix lives.** The defect is in how steward composes a child's pytest options, so it is fixed where the
  env is built: the lane env and the collection env, which are steward's production code. CAP-159 promises each lane
  "its own temp dir, pytest basetemp and cache dir"; an inherited basetemp is not the lane's own. Fixing only the
  tests would leave the same hazard for any invoker that sets `PYTEST_ADDOPTS`, a nested preflight among them.
- **AD-1 (wrap, never reimplement).** pytest keeps owning its options. Steward edits only the variable it already
  writes, with the tokenizer pytest itself uses. It never parses the rest of the option grammar and never re-declares
  a pytest default.
- **AD-8 (exit-code sole ownership).** A lane's verdict stays the exit code of the suite it runs. Today exit 4, a usage
  error caused by steward's own env, stands in for the suite's verdict; after the fix it cannot.
- **Rejected: drop `PYTEST_ADDOPTS` from every child,** as marshal's #2092 fix does for its one child. For the lane env
  it would discard options the invoker set on purpose (`-p no:randomly`, `-x`, a timeout), which reach every lane
  today.
- **Rejected: `monkeypatch.delenv("PYTEST_ADDOPTS")` in each affected test,** as doctor's `test_cli_bridge.py`
  fixture does (`795d1bbfac`). It hides the defect in steward's env composition and leaves the next test that starts a
  child exposed.
- **Rejected: one helper in `pyforge-core` or the testing kit for every station.** That is a cross-station seam with
  its own chain under `spec-pyforge-core`. This story fixes steward; the audit below names what other stations do.

Ledger key: `90-1-a-pytest-the-preflight-starts-never-inherits-another-run-s-basetemp`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-159 (FR-32; Epic 71): Story 71.3's per-lane basetemp and cache
  dir, Story 71.8's scratch outside the checkout, and Story 71.9's reduced segments and `--collect-only`, plus Story
  88.1's dependency lanes. This story fixes the realization of shipped behaviour, so it needs no new CAP and no
  SPEC.md change.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag: it restores intended behaviour, and a
  flag would keep the bug reachable.
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, 2026-10-10 (preflight basetemp inherited). Operator
  ruling 2026-10-10, verbatim: "yes mint the steward preflight fix story".

## Acceptance Criteria

- **AC1 — The lane env carries only the lane's own basetemp and cache dir.**
  - **Given** an inherited `PYTEST_ADDOPTS` holding `-p no:randomly`, each basetemp spelling (`--basetemp=/outer`,
    `--basetemp /outer`), each `cache_dir` spelling (`-o cache_dir=/outer-cache`, `-ocache_dir=/outer-cache`,
    `-o=cache_dir=/outer-cache`, `--override-ini=cache_dir=/outer-cache`, `--override-ini cache_dir=/outer-cache`)
    and `-x`, **When** `_lane_scratch_env(<lane dir>)` builds the env, **Then** `shlex.split` of its `PYTEST_ADDOPTS`
    holds exactly one basetemp, the lane's, and exactly one `cache_dir`, the lane's. `-p no:randomly` and `-x` are
    still there, in their order.
  - With `PYTEST_ADDOPTS` unset or empty, the value is the lane's two options alone, as today.
  - A value pytest cannot split (an unclosed quote) is not guessed at: it passes through unchanged and the lane's own
    options are appended, as today.
- **AC2 — The collection carries no inherited basetemp.**
  - **Given** a scratch repo under `tmp_path` and `PYTEST_ADDOPTS="--basetemp=<tmp_path> -o cache_dir=<tmp_path>/c"`
    (a parent of the repo, as in a lane) **When** `collect_pytest_node_ids` runs **Then** it returns the same node ids
    as with the variable unset, and the scratch repo still exists afterwards.
  - The same holds when the caller passes the basetemp through `env=`.
- **AC3 — A real child pytest runs under an outer basetemp.** **Given** `PYTEST_ADDOPTS="--basetemp=<tmp_path>"`
  **When** `run_preflight` runs a lane whose `run_lane_ctx` starts `python -m pytest` in a repo under `tmp_path` with
  `ctx.env` (the shape of `test_pytest_sees_no_git_work_tree_outside_checkout`) **Then** the child runs its test and
  the preflight exits 0.
- **AC4 — Steward's suite is green with an outer basetemp.** With `PYTEST_ADDOPTS="--basetemp=<dir> -o
  cache_dir=<dir>"` set, the nine tests named in the Evidence pass, and so do the two modules' other 23. The only
  change to them is the reduced-lane helper's env.
- **AC5 — No test passes on a usage error.**
  - `test_collect_pytest_node_ids_raises_on_failure` asserts the `RuntimeError` names
    `definitely-not-a-real-path-xyz`.
  - `test_pytest_fails_when_scratch_lives_inside_checkout_mutation` asserts the child exits 1 and its output carries
    the `git` assertion's failure.
  - Both still pass with `PYTEST_ADDOPTS` unset and with an outer basetemp set.
- **AC6 — The audit is recorded.** This spec's § Child-pytest audit lists every test in the ten `pyforge-*` packages
  and `src/platform` that starts a child pytest, how its child gets `PYTEST_ADDOPTS`, and whether it is safe. The
  story fixes the unsafe ones in steward. Any unsafe one in another station is a follow-up row, not a change here.
- **AC7 — Unchanged otherwise.** The preflight tests for Stories 71.1-71.11 and 88.1 pass, with no change beyond AC4's
  helper and AC5's two assertions. Which lanes run, what each runs, the journal and the exit codes 0 / 1 / 2 / 130 do
  not change.
- **AC8 — Mutation.**
  - Keeping the inherited basetemp in `_lane_scratch_env` fails AC1 and AC3.
  - Dropping the helper from `collect_pytest_node_ids` fails AC2.
  - Going back to `os.environ.copy()` in the reduced-lane helper fails AC4's reduced-lane tests under the outer
    basetemp.

## Boundaries & Constraints

**Always:**
- Fix it in steward: `preflight.py`, `preflight_suite_reduction.py` and steward's unit tests.
- Keep every inherited pytest option other than a basetemp or a `cache_dir` override, in order.
- Put the new tests in the steward suite, so the station's `verify_commands` runs them.
- Reconcile every governed path the change touches on the memlogs of the Specs that govern it, then stamp those Specs
  scoped: `spec-pyforge-steward`, `spec-pyforge-core` (it co-governs every station's `src/`) and any co-governor
  `spec-surface-check` names (AGENTS.md pre-PR item 5).

**Never:**
- Never change another station's code or tests. An unsafe child pytest outside steward is a follow-up row.
- Never drop `PYTEST_ADDOPTS` wholesale from a lane's env.
- Never change which lanes run, what each runs, the journal, the exit codes, `pr-preflight`'s command line, the
  `pre-push` hook or `PYFORGE_PREFLIGHT_SKIP`.
- Never weaken or delete an existing test. AC5 makes two assertions stricter.

**Residual risk:**
- A `PYTEST_ADDOPTS` spelling pytest accepts but the helper does not list would still pass through. pytest 9.1.1
  rejects abbreviations (`--basete=`, `--override-i=` are "unrecognized arguments"; checked 2026-10-10), so the listed
  spellings are the ones it accepts for these two options.
- `TMPDIR` and `COVERAGE_FILE` are still inherited by the collection run. Neither is validated against the working
  directory, and `--collect-only` writes no coverage data.

## Out of scope: three load-sensitive tests

Three tests failed in the same 28-lane runs and pass alone: doctor
`test_doctor_check_completes_within_the_five_second_budget`, marshal `test_check_under_nfr_p1_budget` and atlas
`test_count_star_reads_footer_only_over_range`. Their assertions depend on wall time or on what a reader fetched, not
on a basetemp. They are recorded as `DW-steward-90-1-1` (open, low) in steward's deferred-work ledger, and this story
does not change them.

## Child-pytest audit (AC6)

Read at `a0f47b7301` on 2026-10-10 across the tests of `pyforge-atlas`, `-core`, `-doctor`, `-herald`, `-marshal`,
`-mason`, `-scribe`, `-steward`, `-testing-kit` and `-warden`, and `src/platform/tests`. A test counts when it really
executes a pytest, directly or through code it calls. Tests that only build or inspect a pytest command, and tests whose
process runner is a fake that never executes, do not count. No test in any tree uses `pytester`, `testdir`,
`runpytest`, `inline_run` or `pytest.main`, and no `conftest.py` removes `PYTEST_ADDOPTS`.

Every unsafe row is green in CI and under a plain `pixi run`, where `PYTEST_ADDOPTS` is unset. It goes red, or green for
the wrong reason, only inside a preflight lane, whose `--basetemp` is a parent of `tmp_path`. Paths in the table are
relative to each package's root, except the platform row.

| Package | Test (file:line) | How the child pytest starts | Its `PYTEST_ADDOPTS` | Verdict |
|---|---|---|---|---|
| steward | `tests/unit/test_preflight_suite_reduction.py:95` `test_reduced_and_gate_collections_partition_task` (2 cases), `:285` `test_equal_marker_omits_gate_complement_segment`, `:311` `test_collect_pytest_node_ids_exit_five_is_empty` | `collect_pytest_node_ids` runs `bash -lc "pytest --collect-only …"` (`preflight_suite_reduction.py:426`) in a repo under `tmp_path` | inherited whole (`{**os.environ}`, `:420`) | unsafe: exit 4 in a lane. Fixed here (AC2, AC4) |
| steward | `tests/unit/test_preflight_suite_reduction.py:639` `test_collect_pytest_node_ids_raises_on_failure` | the same, in `tmp_path` | inherited whole | green for the wrong reason: the usage error raises the same `RuntimeError`. Fixed here (AC5) |
| steward | `tests/unit/test_preflight_suite_reduction.py:172`, `:200`, `:230`, `:260` (the four reduced-lane tests) | `_run_reduced_lane_via_preflight` (`:115`) patches `_run_pixi_argv` to run `python -m pytest <segment>` and the `--collect-only` fallback (`:157`-`:163`) in a repo under `tmp_path` | inherited whole (`os.environ.copy()`, `:137`) | unsafe: exit 4 in a lane. Fixed here (AC4) |
| steward | `tests/unit/test_preflight_scratch.py:88` `test_pytest_sees_no_git_work_tree_outside_checkout` | `run_preflight` with a `run_lane_ctx` that runs `python -m pytest` (`:113`-`:117`) in a repo under `tmp_path` | `_lane_scratch_env`: the inherited value first, the lane's own after it | unsafe: exit 4 in a lane. Fixed here (AC1, AC3) |
| steward | `tests/unit/test_preflight_scratch.py:132` `test_pytest_fails_when_scratch_lives_inside_checkout_mutation` | `subprocess.run([python, -m, pytest, …])` (`:156`-`:160`) in a repo under `tmp_path` | `_lane_scratch_env` called directly (`:155`) | green for the wrong reason: exit 4 satisfies `returncode != 0`. Fixed here (AC5) |
| doctor | `tests/unit/test_cli_bridge.py:223`, `:233`, `:243` (`test_run_pytest_*`) | `cli_bridge.run_pytest` (`cli_bridge.py:163`) in `tmp_path` | removed by the `_no_inherited_pytest_addopts` fixture (`:215`, `monkeypatch.delenv`; `795d1bbfac`) | safe |
| marshal | `tests/meta/test_dispatch_supervisor_main_coverage_floor.py:73` `test_the_supervisor_entrypoint_measures_at_or_above_its_floor` | `python -m pytest … --cov` (`:78`) in the package root | popped from a copied env (`:69`; `b8d5910e57`, #2092) | safe |
| platform | `src/platform/tests/test_helm_gate.py:142` `test_a_real_pytest_run_reports_each_branch` (3 cases) | `python -m pytest -c /dev/null …` (`:165`-`:191`) in `tmp_path` | filtered out of a copied env (`:158`-`:162`) | safe |

No test in `pyforge-atlas`, `-core`, `-herald`, `-mason`, `-scribe`, `-testing-kit` or `-warden` starts a child
pytest. **Follow-up rows: none.** Every unsafe test is steward's, and this story fixes all of them: nine red in a
lane, two green for the wrong reason.

Production code that starts a pytest with an inherited environment, for the record (not tests, and unchanged here):
- steward `upgrade.py:3657`-`:3664` (`run_cfe_meta_tests`): no `env`, in the invoker's checkout, when an operator runs
  prove-landed. Its tests inject the runner. The invoker's options are the intended ones; no preflight lane reaches it.
- doctor `cli_bridge.py:158`-`:163`, called by the `platform-policy-suite` source (`sources/platform_policy.py:94`)
  that `detectors-ci` runs. In a lane it inherits that lane's own basetemp, which is not a parent of its working
  directory (`src/platform`) and which no other pytest in that lane uses.
- marshal `dispatch_verify.py:315` and `dispatch_land.py:1127`, through `pyforge.core.process`'s `PosixProcess.run`
  with no `env`: verify and flag-registry commands in a dispatch worktree, under the supervisor's environment. No
  preflight lane reaches them.
- `scripts/coverage_gates_ci.py:188`-`:201`: inherits its coverage-gate lane's own basetemp on purpose and runs its
  pytest runs one after another.

## I/O & Edge-Case Matrix

| Situation | Today (`a0f47b7301`) | After |
|---|---|---|
| `PYTEST_ADDOPTS` unset | lane gets its own two options | unchanged |
| invoker sets `-p no:randomly -x` | kept, lane's two options appended | unchanged |
| invoker sets `--basetemp=X` | kept before the lane's; pytest validates X against the lane's cwd and may exit 4 | removed; the lane's own is the only one |
| invoker sets `-o cache_dir=Y` | kept before the lane's; the lane's wins | removed; the lane's own is the only one |
| a test in a lane collects node ids in a scratch repo under `tmp_path` | the lane's basetemp is a parent of the cwd; exit 4, `RuntimeError` | collects; no inherited basetemp |
| a child pytest inherits a basetemp outside its cwd | runs and wipes the parent's basetemp at start-up | never inherits one |
| `PYTEST_ADDOPTS` has an unclosed quote | appended to as-is | unchanged (passed through, lane's options appended) |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-10 (preflight basetemp inherited) entry.
- Epic: Epic 90 (a new fix epic, because Epic 71, which shipped CAP-159, and Epic 88 are `done`).
- Ledger key: `90-1-a-pytest-the-preflight-starts-never-inherits-another-run-s-basetemp`.
- Ledger status at mint: `backlog`.
- Deps: none.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- `PYTEST_ADDOPTS="--basetemp=$(mktemp -d)/bt -o cache_dir=$(mktemp -d)/c" pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass, the nine tests named in the Evidence among them.
- `pixi run --frozen -e pyforge-guild pr-preflight` on a branch whose diff touches `src/shared/packages/pyforge-core/` — expected: the `pyforge-steward-test` lane is `ok`, and its kept or printed log has no "basetemp must not be empty".
- Mutation: put the inherited basetemp back in `_lane_scratch_env` and re-run the new test module; AC1 and AC3 fail. Restore it.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and scoped stamps.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: no new finding against `main`.
