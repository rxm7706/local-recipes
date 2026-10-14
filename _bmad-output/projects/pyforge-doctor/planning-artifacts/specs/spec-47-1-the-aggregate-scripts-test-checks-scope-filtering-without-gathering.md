---
title: '47.1: The aggregate scripts test checks scope filtering without gathering'
type: 'fix'
created: '2026-10-14'
status: 'ready-for-dev'
review_loop_iteration: 0
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
41.1 added its second file). On a runner the first step, `tests/scripts` in `pyforge-ci`, takes 7 to 9 minutes and the
aggregate step 5 to 7, so the job sat between 10 and 15 minutes and now runs past it.

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
   assertions. It reaches the dispatch table through `_doctor_dispatch()`, so under `pyforge-ci` it skips with the other
   dispatch tests (Story 38.5) and runs for real under `pyforge-doctor`.
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
- **AC6 — The stdlib lane still passes.** Under `pyforge-ci` the test skips, naming the missing module, and
  `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` exits 0.
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
- Never add a dependency to `pyforge-ci` (Epic 39: it stays stdlib-only).

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

- **The first `scripts-suite` step** (`tests/scripts` in `pyforge-ci`) takes 7 to 9 minutes on a runner. It is many
  stations' tests and is not this story's surface; the 25-minute limit gives it room.

## Spec Change Log

- 2026-10-14: minted at the operator's ask "raise timeout-minutes for that job (to about 25) and make those two test
  files faster". The evidence is the local `--durations` run (691.89 s, 684.59 s in one test) and the two cancelled runs
  above.

## Review Triage Log

- No review has run yet.
