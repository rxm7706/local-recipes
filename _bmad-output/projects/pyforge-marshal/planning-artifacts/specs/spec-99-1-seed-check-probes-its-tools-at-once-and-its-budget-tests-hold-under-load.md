---
title: "99.1: Seed check probes its tools at once, and its budget tests hold under load"
type: 'fix'
created: '2026-10-12'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/referenced_deps.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/check.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_seed_detect_referenced_deps.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_check.py
  - src/shared/packages/pyforge-marshal/tests/integration/test_performance_gates.py
  - .claude/memory/feedback/the-local-pr-preflight-marshal-lane-pyforge-marshal-test-can.md
---

<intent-contract>

## Intent

**Problem:** The local `pr-preflight` marshal lane (`pyforge-marshal-test`, `-n auto`) goes red on two NFR-P1 budget
tests while CI is green on the same tree. Both build a ~1200-file fixture and assert that one `run_check` call takes
under 5 s of wall time:

- `tests/integration/test_performance_gates.py::test_check_under_nfr_p1_budget` (`:81`-`:86`)
- `tests/unit/test_seed_verbs_check.py::test_run_check_completes_within_the_nfr_p1_budget` (`:816`-`:845`)

On 2026-10-12, branch `hygiene-memory-index-prune` changed only `.claude/memory/` and `archive/`. Under preflight's
parallel lanes these tests measured 5.78 s and 10.85 s. Alone, both pass. Line numbers below are at `c447946b3f`.

**The evidence (where the 5 s goes):** `run_check` on the fixture takes 2.65-2.95 s alone. 0.05 s is in-process CPU.
The remaining ~2.6 s is CPU spent in child processes, measured with `os.times()`. A `subprocess.run` trace of one call
shows seven calls:

| Call | Time |
|---|---|
| `copier --version` | 1.78 s |
| `bmad-loop --version` | 1.07 s |
| `git status --porcelain --untracked-files=normal` | 0.03 s |
| `pixi --version` | 0.01 s |
| `tmux -V` | < 0.01 s |
| `git rev-parse --git-common-dir` | < 0.01 s |
| `git rev-parse HEAD` | < 0.01 s |

So about 95% of the check's wall time is two Python console scripts starting up. That cost has nothing to do with the
tree the fixture was built to measure. The probes run one after another in `_local_findings`
(`seed/detect/referenced_deps.py:218`-`:227`, through `_probe_entry` :150 and `_cli_installed_version` :104-:114). On a
loaded machine each interpreter start-up stretches, and the sum crosses 5 s.

**The same root cause is a product defect.** `_cli_installed_version` runs each probe with `_CLI_TIMEOUT_S = 5.0`
(`:52`), and it maps every `ProcessError` to `None` (`:109`-`:110`), a timeout included. `_finding_for_entry`
(`:159`) then reports `"<id>: referenced dependency is not installed"` at DRIFT. So on a busy machine `marshal seed
check` can tell an operator that `copier` or `bmad-loop` is missing when it is installed and only slow to answer.

**Approach:**
- Run the CLI probes at the same time, so wall time is the slowest probe rather than the sum. Findings keep manifest
  order.
- A probe that times out gets its own message: it names the command and the timeout, and never says "not installed".
- The two default-lane budget tests measure what their docstrings say they measure: the walk, classify and hash cost
  of a `local-recipes`-sized tree. The referenced-dependency probes are replaced with a fixed in-process stub.
- One `slow`-marked test keeps measuring the real end-to-end budget with real probes. It runs in the serial
  `pyforge-marshal-test-slow` lane, so CAP-13's "under 5 seconds" stays measured.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-13 (`marshal seed check` "completes offline in under 5 seconds on
  a `local-recipes`-sized repo"; NFR-P1). Story 11.5 / FR-95 (referenced-dependency presence and floor verification).
  Story 12.5 (the performance gates). No CAP is minted, and no `SPEC.md` text changes.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag. Two defects qualify: a "not installed"
  finding for an installed tool, and a budget the check misses only because it waits on its probes one at a time.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-12 (the marshal suite under load). Also the
  operator's ask the same day: "start the flaky marshal tests fix". Team memory:
  `.claude/memory/feedback/the-local-pr-preflight-marshal-lane-pyforge-marshal-test-can.md`.

## Acceptance Criteria

- **AC1 — Probes run at once.** In the local probe path, each referenced entry with a CLI probe starts its
  subprocess before any of them is awaited. A unit test replaces the subprocess runner with a stub that sleeps 1.0 s
  per call. With four CLI-probed entries, `_local_findings` (or its successor) returns in under 2.0 s, where a serial
  run takes at least 4.0 s. The returned findings are in manifest order, whatever order the probes finish in. A second
  test makes the probes finish in reverse order and asserts that.
- **AC2 — A timeout says it timed out.** When a probe times out, its finding names the command and
  `_CLI_TIMEOUT_S`, for example `"copier: \`copier --version\` did not answer within 5.0 s (manifest pin '>=9.4')"`.
  It still carries DRIFT severity and `FindingType.REFERENCED_DEP_MISSING`, so the finding schema does not change. The
  words "not installed" never appear for a timeout. A missing executable (`shutil.which` is `None`) and a nonzero exit
  keep today's messages. A unit test covers each of the three cases.
- **AC3 — Default-lane budget tests measure the tree.** Both NFR-P1 tests in the default lane run `run_check` with the
  referenced-dependency probe replaced by an in-process stub that returns each entry's pinned floor. One shared fixture
  or helper does this; the two tests do not each re-implement it. Each test still asserts `< 5.0` s. With the stub,
  `run_check` on the fixture takes well under 1 s alone. Each test's docstring says the probes are stubbed and why.
- **AC4 — The real budget stays measured.** One `@pytest.mark.slow` test runs `run_check` with the real probes on the
  same fixture and asserts `< 5.0` s. It is collected by `pyforge-marshal-test-slow` and not by
  `pyforge-marshal-test`. Before the concurrency change, this test reads about 2.9 s alone; after it, about 1.8 s.
  Record both numbers in the Spec Change Log.
- **AC5 — Holds under load.** The default lane's two budget tests pass while one busy-loop process per CPU runs
  alongside them (`python3 -c "while True: pass"`, `nproc` copies), 5 runs out of 5. The load processes are killed by
  exact PID afterwards. This is a Verification command, not a unit test.
- **AC6 — Mutation.** Each change below makes a named test fail:
  - Probe serially again: AC1's timing test.
  - Return findings in completion order: AC1's ordering test.
  - Map a timeout to `None` again: AC2's timeout test.
  - Remove the stub from the default-lane budget tests: AC5's load run. This one is a Verification command, so record
    its result in the Spec Change Log.

## Boundaries & Constraints

**Always:**
- Keep the Doctor delegation path (`_doctor_findings`, `:176`) exactly as it is: tried first, falling through to the
  local probe on any failure.
- Bound the concurrency to the number of CLI-probed entries. The thread or process pool lives only for the call.
- Keep every probe's own `_CLI_TIMEOUT_S`. The concurrency must not let one probe's timeout cut another short.
- Read every verdict from the exit code, never through a pipe.
- Reconcile every governed path on the memlogs of the Specs that govern it (spec-pyforge-marshal, and
  spec-pyforge-core, which co-governs station `src/`), then stamp scoped (AGENTS.md pre-PR item 5).

**Never:**
- Never raise the 5 s budget, and never loosen it with a load-scaled multiplier. CAP-13 states 5 s.
- Never skip or `xfail` a budget test because of load, and never mark the default-lane tests `slow` to hide them.
- Never import the probed tools (`copier`, `bmad_loop`) in-process to read a version. The probe checks the tool on
  `PATH`, which is not necessarily the running interpreter's.
- Never change a finding's severity or type, and never add a field to the finding schema.

**Residual risk:**
- A machine loaded enough that one probe alone passes 5 s still gets AC2's timeout finding. That finding is now
  accurate, not a false "missing".

## I/O & Edge-Case Matrix

| Probe outcome | Finding |
|---|---|
| version at or above the pin | none |
| version below the pin | today's "below manifest floor" message |
| executable not on `PATH` | today's "not installed" message |
| nonzero exit | today's "not installed" message |
| timeout after `_CLI_TIMEOUT_S` | new: names the command and the timeout; never "not installed" |
| Doctor delegation succeeds | Doctor's findings, unchanged; no local probe runs |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-marshal` CAP-13 (NFR-P1) and the Story 11.5 / FR-95 behaviour it reports.
  No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-12 (the marshal suite under load) entry.
- Requirements and architecture: FR-95 and NFR-P1, unchanged.
- Epic: Epic 99 (new), minted with this story.
- Ledger key: `99-1-seed-check-probes-its-tools-at-once-and-its-budget-tests-hold-under-load`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."99"`, added with this mint.
- Spec: the `spec-pyforge-marshal` memlog records the evidence, the design and this mint.
- Epic 98 is left free on purpose. `docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md` § 5 reserves marshal Epic
  98 for the ci-pauses-at-merge feature.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, with the tests for AC1-AC3 (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test-slow` — expected: pass, with AC4's real-probe budget test collected and green.
- AC5's load run: start `nproc` copies of `python3 -c "while True: pass"`, then run `pixi run --frozen -e pyforge-marshal python -m pytest -q src/shared/packages/pyforge-marshal/tests/integration/test_performance_gates.py::test_check_under_nfr_p1_budget src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_check.py::test_run_check_completes_within_the_nfr_p1_budget` five times, then kill the load processes by exact PID — expected: 5 of 5 exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlogs and scoped stamps.
- The four mutations of AC6 — expected: each fails its named test or command. Restore each.

## Named, not fixed here

- **Doctor delegation start-up.** When `doctor` is on `PATH`, as it is in `pyforge-guild`, `referenced_dep_findings`
  first runs `python -m pyforge.doctor.sources genesis-referenced-deps --json`. Doctor does not ship that source yet
  (the module docstring says so), so the call exits 2 and the local probes run afterwards. That is one more
  interpreter start-up on every check in the guild env. Running it concurrently with the probes, or skipping it until
  the source exists, is a separate decision. It belongs to the source's owner (doctor) and to this delegation contract.
- **The dispatch-verification flake.** The third test the same preflight run reported,
  `test_evaluate_dispatch_verification_pre_existing_packaging_gate_warns`, is Story 99.2.

## Spec Change Log

- 2026-10-12: minted with Epic 99 at the operator's ask "start the flaky marshal tests fix". The evidence comes from
  the measurements above, taken at `c447946b3f`: the `subprocess.run` trace, the `os.times()` split, and the 5.78 s
  and 10.85 s preflight readings.

## Review Triage Log

- No review has run yet.
