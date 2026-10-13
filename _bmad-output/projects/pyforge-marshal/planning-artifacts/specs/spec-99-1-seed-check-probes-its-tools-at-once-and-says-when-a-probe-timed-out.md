---
title: "99.1: Seed check probes its tools at once and says when a probe timed out"
type: 'fix'
created: '2026-10-12'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-98-1-two-marshal-tests-stop-failing-every-local-preflight.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/referenced_deps.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/check.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_seed_detect_referenced_deps.py
  - src/shared/packages/pyforge-marshal/tests/integration/test_performance_gates.py
---

<intent-contract>

## Intent

**Problem:** this is Story 98.1's deferral, `DW-marshal-98-1`. Before it judges anything, `marshal seed check` verifies
every `referenced` manifest entry through `seed/detect/referenced_deps.py`, starting one program after another:

- **Doctor delegation.** When `doctor` is on PATH, as it is in every Guild lane, `_doctor_findings` (`:176`) first runs
  `python -m pyforge.doctor.sources genesis-referenced-deps --json`. Doctor ships no such source, so the call always
  exits 2, in 0.32 s measured 2026-10-12, and the local probes then run.
- **Local probes.** `_local_findings` (`:218`-`:227`) probes the entries one at a time through `_probe_entry`
  (`:150`). `copier`, `pixi`, `tmux` and `bmad-loop` each start a subprocess (`_cli_installed_version`, `:104`-`:114`).

Measured at `c447946b3f`: `run_check` on the NFR-P1 fixture takes 2.65-2.95 s, 0.05 s of it in-process. `copier
--version` takes 1.78 s and `bmad-loop --version` 1.07 s; Story 98.1 measured 2.6 s and 1.4 s. Under load the sum
passes NFR-P1's 5 s.

Each probe has `_CLI_TIMEOUT_S = 5.0` (`:52`), and `_cli_installed_version` maps every `ProcessError` to `None`
(`:109`-`:110`), a timeout included. `_finding_for_entry` (`:159`) then reports `"<id>: referenced dependency is not
installed"` at DRIFT. So on a busy machine `seed check` says an installed tool is missing.

Story 98.1 stubbed `referenced_dep_findings` in the two default-lane NFR-P1 tests, which now time the walk alone.
Nothing times the real check against its budget any more. Line numbers are at `c447946b3f`; this module is unchanged on
main since.

**Approach:**
- Start the Doctor delegation and the CLI probes at the same time, so the wall time is the slowest of them rather than
  the sum. Precedence does not change: if the delegation returns findings, they win, as today, and the local results
  are discarded. Findings keep manifest order.
- A probe that times out gets its own message naming the command and the limit.
- One `slow` test times the real `run_check`, with real probes, against the 5 s budget.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-13 (`marshal seed check` "completes offline in under 5 seconds on
  a `local-recipes`-sized repo"; NFR-P1) and FR-95 (referenced-dependency presence and floor, Story 11.5). No CAP is
  minted, and no `SPEC.md` text changes.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag. Two defects qualify: a "not installed"
  finding for an installed tool, and a budget spent waiting on programs one at a time.
- **Origin.** `DW-marshal-98-1` (Story 98.1). `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-12 (seed
  check waits on its probes one at a time). The operator's asks the same day: "start the flaky marshal tests fix",
  then "merge 2171 and rescope 2172".

## Acceptance Criteria

- **AC1 — The probes run at once.** `referenced_dep_findings` starts the Doctor delegation (when `doctor` is on PATH)
  and every CLI probe before it waits on any of them. Tests replace the process runner with a stub that sleeps 1.0 s
  per call:
  - with `doctor` on PATH and four CLI-probed entries, the call returns in under 2.0 s (serial is at least 5.0 s);
  - with `doctor` absent, it also returns in under 2.0 s.
- **AC2 — Precedence and order are unchanged.**
  - When the delegation returns parseable findings, the result is exactly those findings, as today.
  - When it exits 2 or returns anything unusable, the result is the local findings.
  - The local findings are in manifest order, whatever order the probes finish in. A test makes them finish in
    reverse order and asserts it.
- **AC3 — A timeout says it timed out.** When a CLI probe times out, its finding names the command and
  `_CLI_TIMEOUT_S`, for example `"copier: \`copier --version\` did not answer within 5.0 s (manifest pin '>=9.4')"`.
  - The severity stays DRIFT and the type stays `FindingType.REFERENCED_DEP_MISSING`, so the finding schema does not
    change.
  - The words "not installed" never appear for a timeout.
  - A missing executable and a nonzero exit keep today's messages.
  - A unit test covers each of the three cases.
- **AC4 — The real budget is measured again.** One `@pytest.mark.slow` test runs `run_check` with the real probes on
  the NFR-P1 fixture and asserts its wall time is under 5.0 s. It is collected by `pyforge-marshal-test-slow` and not
  by `pyforge-marshal-test`. Record its time before and after the change in the Spec Change Log: about 2.9 s before;
  expected about 1.8 s after.
- **AC5 — Mutation.** Each change below makes a named test fail:
  - probe serially again: AC1's timing tests;
  - return local findings in completion order: AC2's order test;
  - let a local result win over a successful delegation: AC2's precedence test;
  - map a timeout to "not installed" again: AC3's timeout test.
- **AC6 — The deferral closes.** `DW-marshal-98-1` is marked resolved with this story's commit and the before and after
  numbers.

## Boundaries & Constraints

**Always:**
- Keep each probe's own timeout. The concurrency must not let one probe's timeout cut another short.
- Bound the pool by the number of probes started, and let it live only for the call.
- Read every verdict from the exit code, never through a pipe.
- Reconcile every governed path on the memlogs of the Specs that govern it (spec-pyforge-marshal, and
  spec-pyforge-core, which co-governs station `src/`), then stamp scoped (AGENTS.md pre-PR item 5).

**Never:**
- Never raise NFR-P1's 5 s budget, and never scale it by load.
- Never import the probed tools (`copier`, `bmad_loop`, `pyforge.doctor`) in-process to read a version. The probe checks
  the tool on PATH, and Doctor holds verdicts on Marshal, never the reverse.
- Never change a finding's severity or type, and never add a field to the finding schema.
- Never remove the Doctor delegation. Whether Doctor should ship `genesis-referenced-deps` is Doctor's decision.

**Residual risk:**
- `pyforge-marshal-test-slow` does not run in CI (no workflow invokes it), so AC4's test runs only when someone runs that
  lane. Wiring the slow lane into CI is not this story.

## I/O & Edge-Case Matrix

| Case | Result |
|---|---|
| `doctor` on PATH, delegation returns findings | Doctor's findings, unchanged; the local results are discarded |
| `doctor` on PATH, delegation exits 2 | local findings, in manifest order |
| `doctor` absent | local findings, in manifest order |
| version at or above the pin | no finding |
| version below the pin | today's "below manifest floor" message |
| executable not on PATH, or nonzero exit | today's "not installed" message |
| probe timeout after `_CLI_TIMEOUT_S` | new: names the command and the timeout; never "not installed" |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-marshal` CAP-13 (NFR-P1) and FR-95. No CAP is minted, and no `SPEC.md` text
  changes.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-12 (seed check waits on its probes one at a
  time) entry.
- Deferral closed: `DW-marshal-98-1`.
- Epic: Epic 99 (new), minted with this story.
- Ledger key: `99-1-seed-check-probes-its-tools-at-once-and-says-when-a-probe-timed-out`.
- Ledger status at mint: `backlog`.
- Deps: none. Story 98.1 is done.
- Surface: `marshal-policy.toml` `[epic_surfaces]."99"`, added with this mint.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, with AC1-AC3's tests (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test-slow` — expected: pass, with AC4's test collected and green.
- `pixi run --frozen -e pyforge-guild marshal seed check --repo-root .` before and after — expected: the same findings, faster.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlogs and scoped stamps.
- The four mutations of AC5 — expected: each fails its named test. Restore each.

## Named, not fixed here

- **Doctor's missing source.** Doctor ships no `genesis-referenced-deps` source, so every delegation costs an
  interpreter start-up and then falls through. Whether to ship it, or to drop the delegation, belongs to Doctor's chain
  and this delegation contract.
- **The slow lane in CI.** No workflow runs `pyforge-marshal-test-slow`.

## Spec Change Log

- 2026-10-12: implemented Story 99.1 — AC4 slow `test_check_under_nfr_p1_budget_with_real_probes` on the NFR-P1 fixture: `run_check` wall time ~2.9 s before (serial probes, baseline c447946b3f) → ~1.7 s after (parallel probes, measured 2026-10-12 in `pyforge-marshal` env); closes `DW-marshal-98-1`.
- 2026-10-12: first minted on PR #2172 as Epic 99 with Stories 99.1 (probes plus budget tests) and 99.2
  (dispatch-verification test hermeticity). Re-scoped the same day, after Story 98.1 (#2171) landed: 98.1 found and
  fixed 99.2's real cause (a fake that matched the lane-named temp path), and it stubbed the probes in the budget tests.
  99.2 is withdrawn, and 99.1 keeps only the product half that 98.1 deferred (`DW-marshal-98-1`).

## Review Triage Log

- 2026-10-12: adversarial review (build-auto). Patched doctor-absent AC1 timing stub (`which` must leave CLI tools on PATH); removed duplicate `_local_findings` in favour of `_findings_from_probes`; closed `DW-marshal-98-1` in deferred-work-ledger. Accepted: timeout detection via `ProcessError` text matches pyforge-core contract.
