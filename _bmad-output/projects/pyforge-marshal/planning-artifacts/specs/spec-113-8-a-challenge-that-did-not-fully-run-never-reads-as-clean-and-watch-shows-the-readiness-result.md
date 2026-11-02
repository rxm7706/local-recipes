---
title: "113.8: a challenge that did not fully run never reads as clean, and watch shows the readiness result"
type: 'fix'
created: '2026-11-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py
---

<intent-contract>

## Intent

**Problem:** a challenge that did not fully run can read as clean, and the readiness result never reaches the screen the
operator watches. Line numbers are at `03a7aff5d9` (the challenger's `src/` is unchanged since).

- `parse_report` (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py:382-426`) trusts the
  orchestrator's own `reviewers` list and never checks it against the personas the stage dispatched. A report that
  omits a spawned reviewer, or lists none with zero findings, parses as clean, and `run_one`
  (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py:342`) exits 0 (EGM audit MAR-M-D1).
- `--audit` returns `exit_code_for(Verdict.UNEVALUABLE)` only when every station errors
  (`cli/challenge.py:664`, `if errors and not reports`); a sweep in which some stations error exits 0, against the
  Spec Constraint that unevaluable is failure.
- The readiness result is the launch intent's `readiness_challenge` and `MRS-DISP-067` in the dispatch envelope only;
  `marshal watch` and `marshal status` never read it, so CAP-300's "visible in `marshal watch`" is unmet
  (`DW-marshal-113-3-1`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md:9167`;
  EGM audit MAR-M-Z4).

**Approach:**
- **Reviewer coverage.** Beside `parse_report`, a pure check returns why a parsed report is unevaluable: its `reviewers`
  list misses any dispatched `agent_type(persona)`, is empty, or its `stage` differs from the one requested. `run_one`
  applies it after the parse; an unevaluable report is outcome `error`, exit 1, and the dispatch readiness hook reports
  it as `MRS-DISP-067` (WARN), as it does a failed session today.
- **The audit's exit.** `--audit` returns `exit_code_for(Verdict.UNEVALUABLE)` when any station errors, not only when
  every station does. Findings still never change the exit code.
- **The readiness result on screen.** `gather_dispatch_journal_facts`
  (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py`) carries the launch intent's
  `readiness_challenge`; `marshal status`'s dispatch overlay row and `marshal watch`'s station text show its report path
  and whether it is red, with `MRS-DISP-067` when red. With no `readiness_challenge` on the intent (the switch off), both
  render exactly as today.
- **The deferral closes by a fix.** `DW-marshal-113-3-1` is closed in the deferred-work ledger, naming this story.
- **The contract follows the code.** The memlog events for MAR-M-D1 and MAR-M-Z4 are already on `spec-pyforge-marshal`
  (2026-11-01, commit `7dde4a0202`). Re-derive CAP-298 (an unevaluable session exits 1; findings never change the exit
  code), CAP-300 (the result is visible in `marshal watch` and `marshal status`) and CAP-302 (a partly errored audit is
  unevaluable, settling its "exits 0" text against the Constraint "unevaluable is failure") with `bmad-spec`, never by
  hand. Then the chain-currency cascade re-stamp (`updated:` on the PRD, the architecture spine and `epics.md`), `git
  add`, and the scoped spec-surface stamp for every Spec `spec-surface-check` names.
- **`type: fix`, no flag.** CAP-298 and CAP-300 already promise this behaviour; the paths stay behind the existing
  `pyforge.marshal.egm_*` switches (`spec-feature-flag-governance` Q1).

Ledger key: `113-8-a-challenge-that-did-not-fully-run-never-reads-as-clean-and-watch-shows-the-readiness-result`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-298** (FR-240): the verb's exit domain; an unevaluable session exits 1.
- **CAP-300** (FR-242): the readiness result is visible in `marshal watch` and the run journal.
- **CAP-302** (FR-244): the audit sweep; a partly errored sweep is unevaluable.
- This story mints no CAP. Origin: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md`
  (cluster MAR-CL4; findings MAR-M-D1, MAR-M-Z4), the operator's rulings of 2026-11-01.

## Acceptance Criteria

- **AC1 — A missing reviewer is unevaluable.** A report whose `reviewers` list omits one dispatched agent, is empty, or
  names a `stage` other than the requested one makes `run_one` record outcome `error` and the verb exit 1; a report that
  lists every dispatched agent and the requested stage behaves as today. Unit tests in
  `src/shared/packages/pyforge-marshal/tests/unit/test_challenge_core.py` cover each case of the pure check, and
  `src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py` covers the exit codes.
- **AC2 — Findings never change the exit code.** A complete report with findings exits 0; a complete report with none
  exits 0.
- **AC3 — A partly errored audit is unevaluable.** On a fixture fleet where one station's session fails and the rest
  report, `--audit` exits 1; with every station reporting it exits 0.
- **AC4 — Readiness on screen.** A dispatch whose launch intent carries a red `readiness_challenge` shows its report path
  and `MRS-DISP-067` in `marshal status` and `marshal watch`; a clean one shows clean; an intent without the field
  renders byte-identical to today (`src/shared/packages/pyforge-marshal/tests/unit/test_status.py`,
  `src/shared/packages/pyforge-marshal/tests/unit/test_watch.py`).
- **AC5 — The deferral closes.** `DW-marshal-113-3-1` reads closed by Story 113.8 in the deferred-work ledger, and
  `deferred-work-check` stays green.
- **AC6 — The contract.** CAP-298, CAP-300 and CAP-302 are re-derived by `bmad-spec` (both self-validate passes
  logged); `spec-surface-check`, `chain-currency-sweep-check` and `chain-completeness-check` exit 0.
- **AC7 — Mutation.** Making the coverage check return nothing fails AC1's tests; reverting the audit exit to
  `errors and not reports` fails AC3's. Restore each.
- **AC8 — The suites.** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` green, and the marshal unit coverage
  floor stays at 80% (`pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate`).

## Boundaries & Constraints

**Always:**
- Keep the frozen exit-code domain: refusals are the usage code 2, unevaluable is 1; mint no new code.
- Keep the readiness hook report-only: it never blocks a launch, moves a `status` or writes a ledger.

**Ask first:**
- Any change to how `MRS-DISP-067` is graded (it stays WARN), or to the dispatch launch when the switch is off.

**Never:**
- Never hand-edit `SPEC.md`; never let a finding count change an exit code; never write a ledger.
- A story that fails its independent review twice drops to `backlog` and the landing PR proceeds without it (operator
  ruling 2026-11-01).

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-marshal` CAP-298 (FR-240).
- Parent capability: `spec-pyforge-marshal` CAP-300 (FR-242).
- Parent capability: `spec-pyforge-marshal` CAP-302 (FR-244).

Parent: `spec-pyforge-marshal` CAP-298, CAP-300 and CAP-302 (a fix; no CAP minted)

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-11-01 (the audit lands) entry.
- Research: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md` (MAR-CL4).
- Epic: Epic 113.
- Ledger key: `113-8-a-challenge-that-did-not-fully-run-never-reads-as-clean-and-watch-shows-the-readiness-result`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py`, their tests,
  `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` and the re-derived `SPEC.md`;
  within `marshal-policy.toml` `[epic_surfaces]."113"`.
- Minted 2026-11-01 by the EGM fleet audit (marshal Story 113.7); implemented in the Story 113.7 landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).

**Run before the push:**
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_challenge_core.py src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py src/shared/packages/pyforge-marshal/tests/unit/test_watch.py src/shared/packages/pyforge-marshal/tests/unit/test_status.py` — expected: pass.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.
- `pixi run --frozen -e pyforge-guild deferred-work-check` — expected: exit 0.

## Auto Run Result

Status: done (independent review passed 2026-11-01; see Review Triage Log)

Summary: implemented 2026-11-01 in the Story 113.7 landing worktree (`egm-audit-2026-11`); uncommitted, for the
session owner to land.

What changed:
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py`: `unevaluable_reason(report, stage=,
  personas=)` — the pure check beside `parse_report`: another stage, no reviewers (empty or blank names), or a missing
  dispatched `agent_type(persona)` each return the reason; a complete report returns `None`. `readiness_view(payload)`
  / `readiness_text(view)` — the launch intent's `readiness_challenge` as status and watch show it: report, counts,
  `red` (an error or a finding, the hook's own `MRS-DISP-067` rule) and `code: MRS-DISP-067` when red.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py`: `run_one` applies the check after the
  parse; an unevaluable report is outcome `error` (journaled, `report` is `None`, exit 1), so the dispatch readiness
  hook reports it as `MRS-DISP-067` (WARN) as it does a failed session. `--audit` exits
  `exit_code_for(Verdict.UNEVALUABLE)` when any station errors (was: only when every one did), and an incomplete
  resume marker is re-run instead of read as done. Findings still never change an exit code.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py`: `DispatchJournalFacts.readiness_challenge`,
  read off the launch INTENT by `gather_dispatch_journal_facts`. The launch hook and its grading are unchanged.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py`: the dispatch row carries
  `dispatch_readiness_challenge` (the view) and the text line ` READINESS='red MRS-DISP-067: …; report <path>'` or
  `'clean, report <path>'`; absent on the intent, neither appears.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py`: a dispatch station's `sections` carry
  `readiness_challenge` (the view, from `marshal status`'s row) and the text a `**Readiness Challenge:**` line; absent,
  the sections and text are unchanged.
- Tests: `tests/unit/test_challenge_core.py` (each case of the pure check, the view and text),
  `tests/unit/test_factory_challenge.py` (`FakeRunner` now lists the agents the prompt dispatched; AC1 exit 1 per case,
  AC2 exit 0 with and without findings, AC3 partly errored audit exits 1 then 0, an incomplete marker re-runs, the hook
  raises `MRS-DISP-067` on an incomplete report, the view's `red` matches the hook's finding),
  `tests/unit/test_status.py` and `tests/unit/test_watch.py` (red, unevaluable, clean, and absent — the field adds only
  its own key and text).

Not done here (session owner): AC5 (`DW-marshal-113-3-1` closes at promotion; the deferred-work ledger is not edited
here) and AC6 (the `bmad-spec` re-derive of CAP-298/300/302, the chain-currency re-stamp and the scoped spec-surface
stamp). Two `spec-pyforge-marshal` memlog events carry the surface reconcile and the new behaviour for the re-derive.

Commands (exit codes):
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_challenge_core.py src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py src/shared/packages/pyforge-marshal/tests/unit/test_watch.py src/shared/packages/pyforge-marshal/tests/unit/test_status.py`
  — 0 (505 passed).
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 0 (13594 passed, 15 skipped; 34 passed, 4 skipped).
- Coverage gate over the touched modules: `COVERAGE_GATES_STATIONS=marshal pixi run --frozen -e pyforge-marshal python
  scripts/coverage_gates_ci.py --paths-file <this change's paths> --suites unit --report
  ".steward/coverage/marshal-unit*.json"` — 0 (7 modules ≥ 80%). The `pyforge-marshal-coverage-gate` task diffs
  `origin/main..HEAD`, which does not yet hold this uncommitted change, so the paths were passed explicitly.
- `ruff check` / `ruff format --check` on the eleven files, from the package directory (the lint gate's cwd) — 0 / 0.
- `mypy --cache-dir .mypy_cache/pyforge-guild -p pyforge.marshal` from the package directory (the `lint-types` mypy
  slice) — 0 (217 source files).
- AC7 mutation, on a scratch copy of the package: `unevaluable_reason` returning `None` fails 10 of AC1's tests;
  the audit exit reverted to `errors and not reports` fails `test_a_partly_errored_audit_is_unevaluable`. Both restored
  (the scratch copy was deleted; the live tree was never mutated).

### Fix round 1 — 2026-11-01

Status: blocked. AC5 is closed. AC6 is closed except for the `SPEC.md` render: the auto-mode classifier refused the
render script for this session (`[Auto-Mode Bypass]`), and it was not retried. No code changed in this round.

- **AC5, closed.** `DW-marshal-113-3-1` in
  `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` now carries
  `resolved: 2026-11-01 (marshal Story 113.8, spec-pyforge-marshal CAP-300)` and `status: closed`.
  `deferred-work-check` exits 0.
- **AC6, the re-derive (`bmad-spec`, headless).** The memlog decision is appended to `spec-pyforge-marshal/.memlog.md`.
  It re-derives CAP-298, CAP-300 and CAP-302 success from the Story 113.8 behaviour event. For coherence, the
  Constraint *The challenger never gates* now names an unevaluable session or sweep (exit 1) beside the refusals,
  never a finding. The anchor-asserting render script is
  `/tmp/claude-1000/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/f004f771-b628-48bc-8566-9d9f8b02ff2e/scratchpad/render_113_8.py`
  (argument: the `SPEC.md` path). It makes 8 substitutions: the frontmatter `updated:` note, the three CAP provenance
  arrows, the CAP-298, CAP-300 and CAP-302 success clauses, and the Constraint. It asserts every needle once,
  undo-to-original byte for byte, an unchanged CAP definition count (303) and an unchanged line count (1388). A dry
  run on a scratch copy exits 0. **Not done:** writing `SPEC.md` and logging the two self-validate passes. That step is
  the session owner's, under the operator-approved route of 2026-11-01. It cannot run from this subagent.
- **AC6, the cascade.**
  - Brief: `updated: 2026-11-01` and § *Currency reconciliation — 2026-11-01* close research→brief, marshal's only
    stale edge. The EGM audit research extends *zero false greens* to the challenger's own reads.
  - PRD: § 48, and the FR-240, FR-242 and FR-244 bodies follow the re-derive. No arrow moves.
  - Spine: § *Currency reconciliation — 2026-11-01 (Story 113.8)*. No AD is added or amended. The AD-7/AD-8 and
    AD-5/AD-26 readings are recorded.
  - `epics.md` already reads 2026-11-01 and no story text moves, so it is not stamped. None of these files is on
    marshal's spec surface.
- Commands, exit codes read from `$?`:
  - `deferred-work-check`: 0.
  - `spec-surface-check`: 0. Its only warning is steward's `spec-pyforge-unifying-strategy` drift, which is another
    station's.
  - `chain-completeness-check`: 0.
  - `fr-without-cap-check`: 0.
  - `chain_currency_sweep_check.py --project pyforge-marshal`: 0, with 0 findings. The repo-wide run still reds on
    the other stations, which are other agents' work.
  - `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`: 0 (13666 passed, 15 skipped; 34 passed, 4 skipped).
  - The four story test files: 0 (549 passed).
  - `pyforge-marshal-coverage-gate`: 0. It judged no module, because the change is uncommitted.
  - `lint-types`: 1. Its only finding is the import order in pyforge-doctor's
    `tests/unit/test_sources_pages_liveness.py`, another station's file. pyforge-marshal is ok.
- **To unblock:**
  1. Run the render script on
     `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md`.
  2. Append the pass 1 (coherence) and pass 2 (preservation) `--type event` lines.
  3. `git add`, then run the scoped stamp `--spec pyforge-marshal/spec-pyforge-marshal`.
  4. Return this story to `in-review`.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (`research/egm-audit-2026-11-01.md`, cluster MAR-CL4: MAR-M-D1, MAR-M-Z4)
  at the operator's ruling of 2026-11-01 (implement in the Story 113.7 landing PR). `type: fix`, no flag, no CAP.

## Review Triage Log

- 2026-11-01 — reviewer: independent session. I did not write this code. I judged `git diff HEAD` of the story's
  files against this spec, not against the Auto Run Result. **Verdict: fail**; status is back to `in-progress`.
  - Read:
    - `core/challenge.py`: `unevaluable_reason`, `readiness_view` and `readiness_text`.
    - `cli/challenge.py`: the check in `run_one` after the parse, the `--audit` exit, and the audit-marker re-check.
    - `core/dispatch.py` and `cli/dispatch.py`: `readiness_challenge` read off the launch INTENT.
    - `core/status.py` and `cli/status.py`: `dispatch_readiness_challenge` and ` READINESS=`.
    - `cli/watch.py`: `sections["readiness_challenge"]` and the `**Readiness Challenge:**` line.
    - Their tests, and the launch hook's own red rule in `_readiness_challenge_before_launch` (an error or a finding
      raises the `MRS-DISP-067` WARN; unchanged). `readiness_view`'s `red` is the same rule. Every renderer adds its
      field only when the intent carries one.
  - AC1 holds. `test_challenge_core.py` covers a report that omits a reviewer, one with empty or blank reviewers, one
    for another stage, and a complete one. `test_an_incomplete_report_is_unevaluable` (3 ids) gives exit 1 and
    outcome `error`.
  - AC2 holds. `test_a_complete_report_exits_0_whatever_its_findings` gives exit 0 with 0 and with 2 findings.
  - AC3 holds. `test_a_partly_errored_audit_is_unevaluable` exits 1, then 0 once every station reports.
  - AC4 holds. `TestReadinessChallengeOnTheRow` drives `run_status` JSON and text through red, unevaluable, clean and
    absent. The three `test_watch.py` cases do the same for watch. Absent, neither renderer adds a key or text.
  - AC7 holds, re-observed:
    - `unevaluable_reason` returning `None`: exit 1, 10 failed (the 5 core cases, the 3 exit-code ids, the hook-red
      test and the marker re-run).
    - The audit exit reverted to `errors and not reports`: exit 1, `test_a_partly_errored_audit_is_unevaluable`
      failed.
  - AC8 holds. The suite is green and the touched-module unit coverage is at or above 80% (see the shared evidence).
  - Shared evidence (one run covers all five Epic 113 fix stories; every verdict read from `$?`):
    `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` exit 0 (13666 passed, 15 skipped; 34 passed,
    4 skipped). The challenge, harness, status, watch and dispatch unit files exit 0 (730 passed). ruff check and
    ruff format --check over the 14 changed marshal files (package config, package cwd) exit 0 and 0.
    `lint_types.py ruff-format` exit 0 and `lint_types.py mypy` exit 0, with marshal ok in both. `lint-types` exit 1;
    its only finding is pyforge-doctor's `tests/unit/test_sources_pages_liveness.py` import order, which is another
    station's in-flight file. `pyforge-marshal-coverage-gate` exit 0 but judged nothing, because the change is
    uncommitted. `coverage_gates_ci.py --paths-file` over the 8 touched marshal `src` modules (`--suites unit`) exit 0,
    with every module at or above 80%. `spec-surface-check` 0, `chain-completeness-check` 0, `deferred-work-check` 0,
    `dream-chain-check` 0, `dreams-hygiene-check` 0, `fr-without-cap-check` 0. `chain-currency-sweep-check` exit 1:
    a staleness checkpoint fails on all eight stations, marshal included. `spec-pyforge-marshal/SPEC.md` and the
    marshal PRD have no diff against HEAD. The memlog's newest self-validate entries are the 2026-11-01 amendment's
    pass 1 and pass 2, which predate these stories' events.
  - Mutations ran on a scratch copy of the package `src`, placed first on `PYTHONPATH`. The import path was
    confirmed and the unmutated scratch baseline exits 0 (157 passed). Each mutant was restored from the live file,
    and the live tree was never touched.
  - A guard plugin on `PosixProcess.run` covered the whole unit and meta suite: no challenge test reached a real
    `claude --version`. The only hits were the pre-existing `test_harness_bmadloop_probe.py` cases, which stub
    `subprocess.run`.
  - Failures:
    1. AC5 is not met. `DW-marshal-113-3-1` (`deferred-work-ledger.md:9167`) is unedited and carries no closure naming
       Story 113.8.
    2. AC6 is not met. There is no `bmad-spec` re-derive of CAP-298, CAP-300 or CAP-302: `SPEC.md` is unchanged, so
       CAP-298 never says that an unevaluable session exits 1. No self-validate pass is logged for these stories, and
       `chain-currency-sweep-check` exits 1. The memlog events the re-derive needs are present.
    Neither failure needs a code change. One `bmad-spec` re-derive of `spec-pyforge-marshal` can cover Stories 113.8
    and 113.10–113.13, with both self-validate passes logged. The DW closure and marshal's cascade re-stamp then close
    this story; return it to `in-review` after that.
  - Not blocking: the `cli/dispatch.py` diff also carries Story 113.9's `launch_model` plumbing, and 113.9 is
    `blocked`. Landing 113.8 without 113.9 means separating that hunk.

- 2026-11-01 — reviewer: independent session, second review. I did not write this work. I judged the committed code
  (`origin/main..HEAD`) and the rendered `SPEC.md` against this spec, not against the Auto Run Result or the fix
  rounds. **Verdict: pass**; status set to `done`.
  - AC1 holds. `unevaluable_reason` returns a reason for another stage, no reviewers (empty or blank) or a missing
    dispatched `agent_type(persona)`. `run_one` turns it into an `error` outcome with `report` `None`, and `_run`
    exits `exit_code_for(Verdict.UNEVALUABLE)` (1). The tests are green in the suite.
  - AC2 holds. `test_a_complete_report_exits_0_whatever_its_findings` passes.
  - AC3 holds. `--audit` returns 1 when `errors` is non-empty (`if errors`), and
    `test_a_partly_errored_audit_is_unevaluable` passes.
  - AC4 holds. `DispatchJournalFacts.readiness_challenge` is read off the launch INTENT. `marshal status` adds
    `dispatch_readiness_challenge` and ` READINESS=` only when it is present, and `marshal watch` adds
    `readiness_challenge` and the `**Readiness Challenge:**` line only when it is present. `readiness_view`'s `red`
    is the hook's rule.
  - AC5 holds. `DW-marshal-113-3-1` reads `resolved: 2026-11-01 (marshal Story 113.8, spec-pyforge-marshal CAP-300)`
    and `status: closed`. `deferred-work-check` exits 0.
  - AC6 holds (this review's re-check of the first review's failure):
    - CAP-298 success: the verb exits 0 "whatever the findings say once every reviewer it dispatched has reported".
      A session that failed or left no valid report, or whose report omits a dispatched reviewer, lists none or names
      another stage, is unevaluable, and the verb exits 1. This matches `unevaluable_reason` and `run_one`.
    - CAP-300 success: the result is visible in the run journal, in `marshal status` (`dispatch_readiness_challenge`,
      ` READINESS=`) and in `marshal watch` (`readiness_challenge`, a `Readiness Challenge` line), with
      `MRS-DISP-067` when red, under one rule shared by the hook and both readers. This matches `readiness_view`.
    - CAP-302 success: the sweep exits 0 when every station reported, and a sweep in which any station errored is
      unevaluable and exits 1. This matches `_run`.
    - The Constraint *The challenger never gates* now names an unevaluable session or sweep (exit 1) beside the
      usage-code refusals, never a finding.
    - The memlog carries the Story 113.8 behaviour event and its `(decision) Re-derive 2026-11-01 (marshal Story
      113.8 ...)`. The CAP-298, CAP-300 and CAP-302 definition lines name Story 113.8. The self-validate pair is
      logged. `spec-surface-check` 0, `chain-completeness-check` 0, chain-currency for marshal 0.
  - AC7 holds, re-observed:
    - `unevaluable_reason` returning `None`: exit 1, 10 failed (the five core cases, the three
      `test_an_incomplete_report_is_unevaluable` ids, `test_dispatch_hook_reports_an_incomplete_report_as_red` and
      `test_an_incomplete_audit_marker_is_re_run`).
    - The audit exit reverted to `errors and not reports`: exit 1, `test_a_partly_errored_audit_is_unevaluable`
      failed.
  - AC8 holds. The suite and the coverage gate exit 0.
  - Shared evidence (one run covers Stories 113.8-113.13 on committed `HEAD` f742908321; every verdict read from `$?`,
    from the worktree root):
    - `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` exit 0 (13667 passed, 15 skipped; 34 passed,
      4 skipped).
    - `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` exit 0. The change is committed now, so the
      gate judged `origin/main..HEAD`: "coverage gate OK for pyforge-marshal unit: 8 module(s) ≥ 80%".
    - `chain-completeness-check` 0, `spec-surface-check` 0 (its only warnings are steward's
      `spec-pyforge-unifying-strategy`), `fr-without-cap-check` 0, `deferred-work-check` 0, `dream-chain-check` 0,
      `dreams-hygiene-check` 0, `scripts/chain_currency_sweep_check.py --project pyforge-marshal` 0 (marshal
      `current`).
    - `ad-citation-check` exit 1, on one NEW cap-citation issue outside these six stories:
      `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md:586` (added in
      f742908321 by herald's glossary decision) cites bare `CAP-299`. Qualify it as `spec-pyforge-marshal:CAP-299`
      before the landing PR is pushed. No marshal file is named.
    - The contract, `spec-pyforge-marshal/SPEC.md` (the working tree equals `HEAD`):
      - 303 CAP definitions at `origin/main` and at `HEAD`, with an identical id-and-title list; 1388 lines in both.
        No CAP id changed.
      - The intent and success lines of CAP-298..CAP-303 equal the memlog's six `(capability) ... (amended
        2026-11-01 ...)` entries byte for byte.
      - Each story's `(decision) Re-derive 2026-11-01 (marshal Story 113.n ...)` entry and behaviour event are on the
        memlog. Each changed definition line's provenance names the story.
      - One self-validate pair is logged after the final render: `Self-validate pass 1 (coherence) 2026-11-01, EGM
        audit re-derive` and `Self-validate pass 2 (preservation)`. Pass 1 judges all six CAPs, the four EGM
        Constraints and the EGM Assumption. Pass 2 names the Story 113.8, 113.10, 113.11, 113.12 and 113.13
        re-derives as kept verbatim, and the Story 113.9 findings as landed. The per-story pass texts drafted in the
        fix rounds were not appended separately; this one pair stands for them.
      - The 22 tests the CAP success lines name each exist exactly once in pyforge-marshal's `tests/unit`.
    - Mutations ran on a scratch copy of the package `src`, placed first on `PYTHONPATH`; the import path was
      confirmed. The unmutated scratch baseline (`test_challenge_core.py`, `test_factory_challenge.py`,
      `test_challenge_harness.py`) exits 0 (158 passed). Each mutant was restored, and `git status` shows the live
      package untouched.
