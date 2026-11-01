---
title: "113.8: a challenge that did not fully run never reads as clean, and watch shows the readiness result"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
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

Status: backlog

Summary: not yet implemented.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (`research/egm-audit-2026-11-01.md`, cluster MAR-CL4: MAR-M-D1, MAR-M-Z4)
  at the operator's ruling of 2026-11-01 (implement in the Story 113.7 landing PR). `type: fix`, no flag, no CAP.

## Review Triage Log

- (none yet)
