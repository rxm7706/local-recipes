---
title: '47.1: The aggregate scripts test checks scope filtering without gathering'
type: 'fix'
created: '2026-10-14'
status: 'in-review'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - docs/dreams/pyforge-doctor.md
  - tests/scripts/test_detectors_doctor_sources.py
  - scripts/detectors.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py
  - .github/workflows/detectors.yml
  - pixi.toml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** GitHub cancels the Detectors `scripts-suite` job at its `timeout-minutes: 15`. It did on `main` at
`8d04520770` (run 38523258032, cancelled 15m16s in) and on PR #2204 (run 38523307187, cancelled 15m19s in), both during
the second test step, `pixi run --frozen -e pyforge-doctor pyforge-doctor-aggregate-scripts-test` (Story 39.1; Story
41.1 added its second file). On runners on 2026-10-14 the first step, `tests/scripts` in `pyforge-ci`, took 5m22s to
9m10s, and the aggregate step took 4m56s to 6m30s when it finished. Runs 38519271682, 38521425377 and 38527926138
passed, with first steps of 5m52s, 7m07s and 5m22s; runs 38523258032, 38523307187 and 38534495374 were cancelled, with
first steps of 8m00s, 9m10s and 9m09s. So the job sat between 10 and 15 minutes, and now runs past it.

**The evidence:** a local `--durations` run of the aggregate task was 59 passed in 691.89 s. One test took 684.59 s:
`tests/scripts/test_detectors_doctor_sources.py::test_run_doctor_sources_filters_by_scope_like_a_scanned_detector`. It
calls the real `detectors._run_doctor_sources("repo")` and `("all")`. Each call runs `DISPATCH[name](ROOT)`
(`scripts/detectors.py` `_run_doctor_sources`) for all 29 `_DOCTOR_SOURCE_TASKS` names over the live tree. The test then
asserts only row counts and that `dashboard-drift` is present. Every other test in the two files takes under 0.4 s.
The real gathers are already judged where they belong: the `detectors` job runs `detectors-ci`
(`detectors.py --scope repo`), which calls `_run_doctor_sources` on the live tree.

**Approach:**
1. The test replaces `pyforge.doctor.sources.__main__.DISPATCH` with a stub, `lambda root: []`, for every
   `_DOCTOR_SOURCE_TASKS` name, so it checks scope filtering and row building without gathering. It keeps its four
   assertions. It reaches the dispatch table through `_doctor_dispatch()`, so, like the other dispatch tests (Story
   38.5), it skips wherever Doctor's run-deps cannot import and runs for real wherever they can.
2. It adds the check the old test could not make: a `repo` call skips a source whose scope is `runtime`. Every one of
   the 43 `REGISTRY` rows is `repo` today, so the test marks one source `runtime` through `pyforge.doctor.sources.scope_for`,
   which `_run_doctor_sources` reads at call time. It also asserts the live split equals `scope_for`, so a real
   runtime-scope source registered later is held to the same rule.
3. `scripts-suite` gets `timeout-minutes: 25`, so the first step's growth does not cancel the lane again.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-doctor` CAP-42 and CAP-43, the pair Epic 39 cites for
  `pyforge-doctor-aggregate-scripts-test` (Stories 38.3, 38.5 and 39.1; Story 41.1 added the second file), with FR-15
  (Story 6.9, the real run path `_run_doctor_sources` this test pins). No CAP is minted, and no `SPEC.md` text changes.
- **No NFR moves.** NFR-4 is `doctor check`'s five-second budget; this story does not touch `doctor check`, so NFR-4
  is unchanged and is not this story's rule. The lane's limit is the workflow's `timeout-minutes`.
- **No flag.** This is a `fix` (`spec-feature-flag-governance` Q1): it restores the lane's intended run. Q2's closed
  exemption list binds only `type: feature`, so no `flag-exempt:` value is needed.
- **Origin.** `docs/dreams/pyforge-doctor.md` Realization log, 2026-10-14 (the Detectors scripts lane outgrew its
  timeout). Operator ask 2026-10-14: "raise timeout-minutes for that job (to about 25) and make those two test files
  faster".

## Acceptance Criteria

- **AC1 — No real gather.** The test sets `pyforge.doctor.sources.__main__.DISPATCH` to a mapping from every
  `_DOCTOR_SOURCE_TASKS` name to `lambda root: []`. No source's real gather runs in it.
- **AC2 — Same assertions.** Its four assertions stay: `len(all_rows)` and `len(repo_rows)` each equal
  `len(detectors._DOCTOR_SOURCE_TASKS)`, and `dashboard-drift` is in both.
- **AC3 — Row building.** The `all` rows follow `_DOCTOR_SOURCE_TASKS` order. Each row's `task` is its paired pixi task,
  its `scope` equals `scope_for(Source(name))`, and its `(status, rc, summary)` is `("pass", 0, "no findings")`.
- **AC4 — A repo call skips a runtime source.** The `repo` rows are exactly the names `scope_for` reads as `repo`.
  With one source marked `runtime` through a patched `pyforge.doctor.sources.scope_for`, a `repo` call omits it and
  keeps `dashboard-drift`, an `all` call keeps it with scope `runtime`, and a `runtime` call returns only it.
- **AC5 — Timing.** `pixi run --frozen -e pyforge-doctor pyforge-doctor-aggregate-scripts-test` passes with no skip, and
  the two files together finish in under 60 s of wall time locally. Record the before and after wall times in the Spec
  Change Log.
- **AC6 — The stdlib lane still passes.** `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` exits 0.
  Wherever Doctor's dispatch table cannot import, the test skips and names the missing module.
- **AC7 — The lane's limit.** In `.github/workflows/detectors.yml` the `scripts-suite` job has `timeout-minutes: 25`.
  No other job, step or `if:` line changes, and `pixi run --as-is -e pyforge-guild ci-surface-gates-check` exits 0.
- **AC8 — Mutation.** Each change below makes the test fail. Restore each.
  - delete the `if scope not in ("all", source_scope): continue` filter in `_run_doctor_sources`;
  - build a row's `scope` from the call's argument instead of `scope_for`;
  - leave one `_DOCTOR_SOURCE_TASKS` name out of the stub mapping.

## Boundaries & Constraints

**Always:**
- Keep every assertion's intent; no test in the two files is deleted or skipped under `pyforge-doctor`.
- Read every verdict from the exit code, never through a pipe.
- Reconcile every governed path on the memlogs of the Specs that govern it, then stamp scoped (AGENTS.md pre-PR item 5).

**Never:**
- Never change `scripts/detectors.py`, `pixi.toml` or the task's command.
- Never move a real gather out of `detectors-ci`; the `detectors` job keeps judging every source on the live tree.
- Never add a dependency to `pyforge-ci` (Epic 39).

**Residual risk:**
- The test no longer proves that a real gather returns a row. `detectors-ci` proves it on every PR, and
  `test_the_real_hygiene_gather_runs_through_the_aggregate_and_reads_pass` keeps one real gather in this file.

## I/O & Edge-Case Matrix

| Call | Rows |
|---|---|
| `_run_doctor_sources("repo")`, every source `repo` | all 29, each `pass` |
| `_run_doctor_sources("all")` | all 29, in `_DOCTOR_SOURCE_TASKS` order |
| `_run_doctor_sources("repo")`, one source marked `runtime` | 28; the marked one absent, `dashboard-drift` present |
| `_run_doctor_sources("runtime")`, one source marked `runtime` | only the marked one, scope `runtime` |
| a name with no stub | its row reads `unknown` (KeyError), so AC3 fails |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-doctor` CAP-42 and CAP-43, with FR-15. No CAP is minted, and no `SPEC.md` text
  changes.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-14 (the Detectors scripts lane outgrew its
  timeout) entry.
- Epic: Epic 47 (new), minted with this story. Epic 45 is PR #2205's and Epic 46 is on `main`.
- Ledger key: `47-1-the-aggregate-scripts-test-checks-scope-filtering-without-gathering`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."47"`, added with this mint.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-aggregate-scripts-test` — expected: pass, no skip, under 60 s wall (AC1-AC5).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: exit 0 (AC6).
- `pixi run --as-is -e pyforge-guild ci-surface-gates-check` — expected: exit 0 (AC7).
- `pixi run --as-is -e pyforge-guild detectors-ci` — expected: no new findings against `main`.
- `pixi run --as-is -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlogs and scoped stamps.
- The three mutations of AC8 — expected: each fails the test. Restore each.

## Named, not fixed here

- **Six places in `pixi.toml` still describe `pyforge-ci` as stdlib-only or free of runtime libraries.** All are
  tracked as `DW-doctor-47-1-1` (owner steward). `grep -n "carries no runtime\|unavailable in \`pyforge-ci\`\|stdlib-only\|pure stdlib" pixi.toml`
  finds them:
  - `:651-652`, the `pyforge-steward-container-gates-test` comment: "`pyforge-ci` (deliberately zero runtime deps, mirrors
    why `pyforge-doctor-scripts-test` lives there for its stdlib-only target)".
  - `:830-832`, the `pyforge-deps-test` comment: "the leanest env in the repo — which carries no runtime libraries at
    all". Its "the check is pure stdlib (ast + tomllib)" is about the check, and stays true.
  - `:837`, the `pyforge-deps-test` description: "pure stdlib; no runtime deps required". It describes the check, and
    stays true; it is listed because the grep finds it.
  - `:840-847`, the comment above `pyforge-doctor-scripts-test` ("both it and `pyforge.doctor.models` are pure stdlib,
    so this fits the same lean env") and its description ("pure stdlib, no runtime deps required").
  - `:1638`, the `pr-preflight` description: "jsonschema (unavailable in `pyforge-ci`, which
    `pyforge-doctor-scripts-test` already covers for the stdlib-only subset)".
  - `:3078`, the `pyforge-doctor-aggregate-scripts-test` description: "skip under pyforge-doctor-scripts-test
    (pyforge-ci, stdlib-only by design)".

  They are not edited here: a `pixi.toml` change fires every station suite and the `environment.yaml` rule, which is
  out of scale for a description fix.
- **`pyforge-ci` is not stdlib-only in practice.** It declares none of Doctor's run-deps, but its `python` feature pulls
  `jsonschema` and `pyyaml` in through `spec-kit` (`pixi tree -e pyforge-ci -i jsonschema`: `spec-kit` -> `mcp` ->
  `jsonschema`), and `tests/scripts/conftest.py` puts `pyforge-core` on `sys.path`. So Doctor's dispatch tests run in
  the first step as well as the second. The env's composition is steward's, not this story's surface.

## Spec Change Log

- 2026-10-14: minted at the operator's ask "raise timeout-minutes for that job (to about 25) and make those two test
  files faster". The evidence is the local `--durations` run (691.89 s, 684.59 s in one test) and the two cancelled runs
  above.
- 2026-10-14, implemented. A third cancelled run: PR #2205, run 38534495374, cancelled 15m17s in, during the aggregate
  step. Measured on this machine, `pixi run --frozen -e pyforge-doctor pyforge-doctor-aggregate-scripts-test`:
  - before (at `b35ddf046c`): 59 passed in 721.41 s, 723.28 s wall;
  - after: 59 passed in 6.12 s, 7.03 s wall. The slowest test is now 0.29 s; the scope test is 0.19 s.
- 2026-10-14, a correction found while implementing. The mint said the test would skip under `pyforge-ci`. It does not:
  that env resolves Doctor's run-deps (see *Named, not fixed here*). The old test ran its real gathers in the first step
  too, 519.90 s for that one test under `pyforge-ci` locally. After the change,
  `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` is 1547 passed, 28 skipped in 35.44 s (36 s wall); on a
  runner that step was 1549 passed, 28 skipped in 321.15 s (run 38527926138). AC6 and Approach item 1 now say what is
  true. The `_doctor_dispatch` docstring and the `detectors.yml` comment above the aggregate step said the same wrong
  thing, and both are corrected in the same change.
- 2026-10-14, AC8: each of the three mutations failed the test (the filter removed: the marked source appeared in the
  `repo` rows; the scope taken from the argument: `'all' == 'repo'`; one stub left out: that row read `unknown`), and
  the restored tree passed.
- 2026-10-14, after the independent review (FAIL on prose only): the workflow comments, the test docstring, the runner
  timings here and in the Dream entry, and a memlog correction are fixed; `DW-doctor-47-1-1` records the two `pixi.toml`
  descriptions and the env question. See *Review (2026-10-14, independent)*.
- 2026-10-14, after the re-review (iteration 2, three low text-only findings): the `detectors.yml` comment says what
  the `pyforge-ci` env composes, and *Named, not fixed here* and `DW-doctor-47-1-1` list all six `pixi.toml` places,
  not two. `review_loop_iteration` is 1.

## Review (2026-10-14, independent)

**Iteration 1 — verdict: FAIL.** The code and all eight ACs pass, and all eight of the reviewer's mutations turned the test red. The
failures are in comments and prose. Each finding, and what changed:

1. **(medium) The workflow comment said the verdict-writer tests run in `pyforge-ci` too.** False. In `pyforge-ci`,
   `tests/scripts/test_apply_verification_verdicts.py:31`'s module-level `importorskip` skips the whole file
   ("could not import 'pyforge.doctor.sources.chain'"). Collection is alphabetical, so it runs before
   `test_detectors_doctor_sources.py` puts Doctor's source on `sys.path`. In the reverse order, 31 tests fail, because
   the script's subprocess refuses outside `pyforge-doctor`. **Changed:** the comment above the aggregate step limits
   the "run there too" claim to the dispatch tests, and says the verdict-writer file skips there and why. Reproduced:
   in `pyforge-ci`, the two files give 23 passed and 1 skipped (`test_apply_verification_verdicts.py:31`).
2. **(low) The stale "pyforge-ci is stdlib-only" claim remained** at `.github/workflows/detectors.yml:71-72`,
   `pixi.toml:3078` and `pixi.toml:840-847`. **Changed:** the workflow comment now says what the env carries.
   `pixi.toml` is not edited. Its two lines are in *Named, not fixed here*, and doctor's `deferred-work-ledger.md`
   gains `DW-doctor-47-1-1` (owner steward, low, open), which covers both the stale task descriptions and the
   `pyforge-ci` env-composition question.
3. **(low) The runner timings overstated.** "7 to 9 minutes" and "5 to 7" did not match run 38527926138 (5m22s and
   4m56s) or main's run 38523258032 (8m00s for the first step before the cancel). **Changed:** the workflow comment
   cites run 38523258032. This spec's Intent and the Dream entry give the measured ranges and name the six runs.
4. **(low) The test docstring said 691.89 s was "this file's".** It is the whole two-file task (59 tests).
   **Changed:** the docstring says so.
5. **(low) The design memlog entry said "three assertions"; there are four.** **Changed:** a correction entry is
   appended to `spec-pyforge-doctor/.memlog.md`. Past lines are not edited. The same entry corrects that entry's runner
   timings.
6. **(informational)** No action.

**Iteration 2 — re-review of `65f1315a4e`.** Findings 1-5 are confirmed fixed. Three new findings, all low and
text-only:

- **A. The `detectors.yml` comment said `pyforge-ci` "declares only build and test tools".** False. `pixi.toml:1051`
  builds `pyforge-ci` from the `python` and `pyforge-ci` features. The `python` feature (`pixi.toml:35-44`) declares
  gh, gitpython, nodejs, pnpm, bmad-method, spec-kit and truststore, and the `pyforge-ci` feature
  (`pixi.toml:814-822`) also carries `ruamel.yaml` and `twine`. **Changed:** the comment now says the `pyforge-ci`
  feature declares build, test and upload tools (plus `ruamel.yaml` for one test), and that the env also composes the
  `python` feature, whose `spec-kit` pulls `jsonschema` and PyYAML in.
- **B. `DW-doctor-47-1-1` and *Named, not fixed here* said "two" `pixi.toml` descriptions.** The grep finds six places:
  `:651-652`, `:830-832`, `:837`, `:840-847`, `:1638` and `:3078`. **Changed:** both now list every hit, with its text.
  `:837`, and the "pure stdlib" clause at `:830`, describe the check rather than the env and stay true; they are
  listed because the grep finds them. The DW row is amended in place, because it was minted on this unmerged branch;
  doctor's precedent is Story 44.1's review amending `DW-doctor-44-1` in `c3ebc48537`. Its `origin:` says so.
- **C. `review_loop_iteration` stayed 0.** **Changed:** it is 1, one key (precedent: doctor 44.1, `c3ebc48537`).

## Review Triage Log

- Independent review, 2026-10-14: FAIL on prose only; findings 1-5 fixed as above, 6 informational.
- Re-review (iteration 2), 2026-10-14: findings 1-5 confirmed fixed; A, B and C (low, text-only) fixed as above.
