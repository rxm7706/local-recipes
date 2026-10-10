---
title: "85.7: A cross-surface refusal gets the same one fix turn"
type: 'fix'
created: '2026-10-10'
status: 'in-progress'
baseline_revision: '21aae5aa16e9537aa983afed72125d240a8b8a1d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-85-1-a-verification-refusal-goes-back-to-the-session-that-wrote-the-change-for-one-fix-turn.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-85-6-a-fix-turn-re-runs-only-the-failing-commands-and-knows-the-flag-checklist.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verification_journal.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_verify_fix.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_verification.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - docs/how-to/troubleshoot-bmad-agent-loops.md
deferred:
  - summary: >-
      Teach the fix-turn prompt the flag gate's two-state test shape when flag-gate-check fails with flag-test-not-two-state.
    evidence: |-
      Two of the four 2026-10-09/10 cross-surface refusals were flag-gate-check exit 1 on flag-test-not-two-state: marshal 87.5 (run pyforge-marshal-20261009T221327283Z-283f3080; its tests named the flag key through an imported constant, which the static check cannot see, and hand fix 0af3a4267e names it literally) and steward 85.5 (run pyforge-steward-20261010T100406402Z-aee344c6; hand fix 7cda758bab writes the two flagd trees through a *flagd_tree* writer with the literal key). scripts/flag_gate_check.py judge_two_state (:571) reads the files a done spec's ## Verification names and wants the spec's flag.key written literally together with pyforge.testing_kit.flags.flag_states, or two *flagd_tree* calls, one with "on" and one with "off" (:35-:42, :478-:483). Story 85.6's checklist (core/dispatch_verify_fix.py build_verify_fix_prompt) names the four registration points only. Out of Story 85.7's scope: it changes the prompt's content, needs its own mutation test, and needs a line in docs/reference/story-spec-flag-block.md.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_verify_fix.py
    severity: medium
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** dispatch verification refuses at two gates, and only one of them gets Story 85.1's fix turn.
`MRS-GATE-001` covers a failed story verify command. `MRS-GATE-015` covers a failed cross-surface verify command
(`pixi run -e pyforge-guild flag-gate-check`, `pixi run -e pyforge-guild platform-ci-local -- --test`,
`pixi run -e pyforge-guild bmad-estate-check`). When `MRS-GATE-015` is the only failure, the run gets no turn and goes
straight to `failed`. When it follows a `MRS-GATE-001` turn, the park names no command. Line numbers below are at
`2d90c634f3`.

- **Where the cross-surface command goes.** `dispatch_verify.py` runs each matched cross-surface rule (:972-:997)
  through `_run_verify_command(..., failure_prefix="cross-surface verify command")` (:976-:981). It rewrites a
  `MRS-GATE-001` result to `MRS-GATE-015` with the message `cross-surface verify command '<cmd>' exited N` (:983-:988)
  and stores the command's report under `data["cross_surface_checks"][i]["report"]` (:990-:999). The report never
  goes into `data["commands"]` (:854).
- **Where it is lost.** With `pyforge.marshal.verify_fix_loop` on and a refusal,
  `dispatch_verification_journal.py` builds the OUTCOME's `failed_commands` (:61-:81) from
  `verify_data.get("commands")` only (:66-:67), through `core/dispatch_verify_fix.py` `extract_failed_verify_commands`
  (:153-:194). That function admits `MRS-GATE-015` (`CROSS_SURFACE_GATE_CODE`, :169), so Story 85.1 meant the fix turn
  to cover it. But it parses every message with `core/dispatch_verification.py` `_command_from_gate_001_message`
  (:136-:148), and that returns `None` unless the message starts `verify command '` (:137-:139). So a `MRS-GATE-015`
  command never enters the failed set. Even if it did, its report is not among the reports the function reads, so its
  output tail would be empty.
- **Where the turn is skipped.** `dispatch_supervisor/__main__.py` `_maybe_run_verify_fix_turn` (:1267) reads those
  rows (:1371) and calls `decide_verify_fix_turn(..., has_failed_commands=bool(failed_cmds))` (:1382-:1390). An empty
  list returns `no failed verify command to fix` (`core/dispatch_verify_fix.py`:311-:312). The supervisor returns at
  :1391 and journals nothing about the skip, and finalize (:1926-:1962) records `verified: false`.
- **How the budget is counted.** `_verify_fix_turn_journaled` (:601-:605) is true once any `dispatch-verify-fix`
  OUTCOME exists for the run, whatever gate refused, so the budget is already one turn per run. `_journal_fix_turn_park`
  (:1225-:1263) names `failed_after[0]["command"]` (:1240) from the same `failed_commands`, so a re-verification that
  refuses at `MRS-GATE-015` parks with `failed_command: null`. That breaks CAP-286's own success criterion, which says
  the park names "the failing command".

**Evidence** (Tier-3 run journals, `_bmad-output/projects/<station>/implementation-artifacts/dispatch-runs/<run>/journal.jsonl`):
- **Marshal 87.5** (run `pyforge-marshal-20261009T221327283Z-283f3080`). The verification OUTCOME is
  `failed_gate: MRS-GATE-015`, `failed_message: cross-surface verify command 'pixi run -e pyforge-guild
  flag-gate-check' exited 1`, `failed_commands: []`. There is no `dispatch-verify-fix` entry, and finalize records
  `verified: false`. Its tests named the flag key through an imported constant, which the static check cannot see.
  The hand fix `0af3a4267e` names the key literally.
- **Steward 85.5** (run `pyforge-steward-20261010T100406402Z-aee344c6`). Same shape: 5 findings (4 `MRS-GATE-012`
  advisories and one `MRS-GATE-015` on `flag-gate-check`), `failed_commands: []`, no turn. The hand fix `7cda758bab`
  writes the two flagd trees through a `*flagd_tree*` writer with the literal key.
- **Herald 19.2** (run `pyforge-herald-20261010T105313078Z-a4b44f7d`):
  - The first verification refused at `MRS-GATE-001`, with 4 findings and no scope advisories. The fix turn's INTENT
    has `failed_command_count: 3`, and `verify-fix-prompt.txt` names only the three `MRS-GATE-001` commands. The
    session had changed `src/platform/tests/test_station_api_host_dispatch.py`, so the platform rule ran in that
    first verification.
  - Re-verification refused at `MRS-GATE-015` on `pixi run -e pyforge-guild platform-ci-local -- --test` with
    `failed_commands: []`. The park was `MRS-DISP-060` with `failed_command: null`.
  - It was fixed by hand: a platform ruff fix and a test-isolation bug in a cached webhook app.
- **Marshal 87.4** (run `pyforge-marshal-20261009T225108225Z-cb5973ce`). Its `MRS-GATE-001` turn ran and then stopped
  at its spec-surface reconcile. The `flag-gate-check` failure surfaced only at hand landing.

**Approach:** read the cross-surface failures the same way the story failures are read, and leave the decision
alone.
- **One parser for both gates.** A refusal message is either `verify command '<cmd>' …` or
  `cross-surface verify command '<cmd>' …`, and the parser `extract_failed_verify_commands` uses returns `<cmd>` for
  both. `reclassify_pre_existing_gate_findings` (`core/dispatch_verification.py`, about :179-:227) reads only
  `MRS-GATE-001` and keeps doing so. A cross-surface failure is never downgraded to `MRS-GATE-014`.
- **Both report sets.** `build_dispatch_verification_journal_entries` passes the reports under `commands` and the
  `report` of every entry under `cross_surface_checks` to `extract_failed_verify_commands`. Each `failed_commands` row
  gains `gate`, the code of the finding that named it (`MRS-GATE-001` or `MRS-GATE-015`). The change is additive, and
  the scrub-before-tail path (Stories 85.3/85.4) is unchanged.
- **The supervisor decides as it does today.** With the failed set no longer empty, a `MRS-GATE-015`-first refusal
  goes through the same `decide_verify_fix_turn`, the same launch, the same commit, ruff pass, reconcile and single
  re-verification (Stories 85.2, 85.5, 22.20), and the same park. The fix-turn INTENT payload gains `trigger_gate`
  (the refused verification OUTCOME's `failed_gate`) and `failed_gates` (the sorted distinct `gate` values of the
  rows it was given).
- **Budget: one turn per run, across both gates (choice recorded).** A run that used its turn on `MRS-GATE-001` and
  then refuses at `MRS-GATE-015` parks with `MRS-DISP-060`, as today, now naming the cross-surface command. A second
  turn is not warranted:
  - **One turn would have seen everything.** Herald 19.2 is the only case where a second turn could have helped. Its
    first verification counted 4 findings while its turn received 3 commands. Once both gates are read, a first
    refusal hands the one turn every failed command of both gates at once.
  - **A second turn costs too much.** It would double the worst-case wall clock (2 × 900 s), and every turn already
    re-runs the full verification.
  - **The operator's constraint.** The operator allows no unbounded loop, and the CAP-286 contract ("no second turn
    runs") stands.
- **Docs.** `docs/how-to/troubleshoot-bmad-agent-loops.md` is the dispatch troubleshooting how-to, and it says nothing
  about fix turns. No doc line describes them today: `docs/reference/story-spec-flag-block.md`:45 mentions only the
  prompt's flag checklist. The how-to gains one passage covering four things:
  - a refusal at `MRS-GATE-001` (story verify command) or `MRS-GATE-015` (cross-surface command) gets one fix turn
    while `pyforge.marshal.verify_fix_loop` is on;
  - the turn re-runs exactly the quoted commands;
  - a still-red re-verification parks with `MRS-DISP-060` naming the command;
  - the turn is read from the `dispatch-verify-fix` entries in the run's `journal.jsonl`.

  Its `sources:` gain the supervisor and `core/dispatch_verify_fix.py`, and its `verified:` date moves.

Ledger key: `85-7-a-cross-surface-refusal-gets-the-same-one-fix-turn`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-286 (FR-233): Story 85.1's fix turn, Story 85.2's supervisor
  wiring and park (`MRS-DISP-060`), Story 85.6's exact-re-run prompt. The cross-surface gate is Story 22.12/22.14's
  `MRS-GATE-015` on CAP-161's independent verification (← `spec-marshal-single-story-dispatch` CAP-3; Story 22.3).
  CAP-286's intent already covers a refusal at any verification gate, and Story 85.1 already admits
  `CROSS_SURFACE_GATE_CODE` in the extraction. This story fixes the realization of shipped behaviour, so it needs no
  new CAP and no SPEC.md change.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag. The behaviour rides
  `pyforge.marshal.verify_fix_loop` unchanged (ON in dev and staging, OFF in production, Story 85.3). With the flag
  off, neither gate gets a turn and the OUTCOME keeps `main`'s keys.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-10 (cross-surface fix turn). Operator ruling
  2026-10-10, verbatim: "mint the MRS-GATE-015 fix-turn marshal story".

## Acceptance Criteria

- **AC1 — A first refusal at `MRS-GATE-015` gets the turn.**
  - **Given** the flag on and a finished session whose verification refuses with exactly one ERROR finding,
    `MRS-GATE-015` `cross-surface verify command 'pixi run -e pyforge-guild flag-gate-check' exited 1`. Its
    `cross_surface_checks` report holds `returncode: 1` and stdout naming `flag-test-not-two-state` (the marshal 87.5
    shape).
  - **When** `_run_supervisor_finalize_sequence` runs with a fake verify runner and a fake fix session, **Then:**
    - the verification OUTCOME's `failed_commands` holds one row: `command` that command, `exit_code: 1`, a non-empty
      scrubbed `output_tail`, `gate: MRS-GATE-015`;
    - exactly one fix session launches, and its prompt contains `Failed command: pixi run -e pyforge-guild
      flag-gate-check`, `Exit code: 1`, the tail, Story 85.6's exact-re-run instruction and Story 85.6's flag
      checklist (the `flag-gate-check` signal);
    - when the scripted re-verification is green, finalize records `verified: true`.
- **AC2 — Still red after the turn: park with the command.** **Given** AC1's refusal and a re-verification that
  refuses the same way **When** the turn ends **Then** one `MRS-DISP-060` observation is journaled with
  `failed_command: "pixi run -e pyforge-guild flag-gate-check"` (never `null`). Its finding message names that
  command. No second session launches, on this pass or on a later supervisor pass over the same journal.
- **AC3 — `MRS-GATE-001`, then `MRS-GATE-015`: the budget is spent.**
  - **Given** a first refusal at `MRS-GATE-001` only, and a re-verification that refuses at `MRS-GATE-015` on
    `pixi run -e pyforge-guild platform-ci-local -- --test` (the herald 19.2 shape).
  - **When** finalize runs, **Then:**
    - exactly one session launches;
    - the park is `MRS-DISP-060` with `failed_command: "pixi run -e pyforge-guild platform-ci-local -- --test"`;
    - `_verify_fix_turn_journaled` reads true for the run, and a second finalize pass launches nothing.
- **AC4 — Both gates at once go to one turn.** **Given** a first refusal carrying three `MRS-GATE-001` findings and one
  `MRS-GATE-015` finding, each with its report **When** the turn launches **Then** its INTENT has
  `failed_command_count: 4`, and the prompt names all four commands in sorted order.
- **AC5 — The journal names the gate.** **Given** AC1 and AC3 **When** each turn's `dispatch-verify-fix` INTENT is
  journaled **Then** it carries `trigger_gate` equal to the refused verification OUTCOME's `failed_gate`
  (`MRS-GATE-015` for AC1, `MRS-GATE-001` for AC3). It also carries `failed_gates`, the sorted distinct `gate` values
  of its rows: `["MRS-GATE-015"]` for AC1 and `["MRS-GATE-001", "MRS-GATE-015"]` for AC4.
- **AC6 — `MRS-GATE-001` behaviour unchanged.** **Given** the existing tests in
  `tests/unit/test_dispatch_supervisor_verify_fix.py` and `tests/unit/test_dispatch_verify_fix.py` **When** the
  station suite runs **Then** they pass with no change beyond accepting the additive `gate`, `trigger_gate` and
  `failed_gates` keys. With the flag off, a refusal's OUTCOME has exactly `main`'s keys and no turn runs.
- **AC7 — The pre-existing reclassifier is untouched.** **Given** a `MRS-GATE-015` finding whose output names only
  paths outside the story's blast radius **When** `reclassify_pre_existing_gate_findings` runs **Then** the finding
  stays `MRS-GATE-015` and is never downgraded to `MRS-GATE-014`.
- **AC8 — Docs name both gates.** **Given** `docs/how-to/troubleshoot-bmad-agent-loops.md` **When** read **Then** it
  names `MRS-GATE-001`, `MRS-GATE-015`, `pyforge.marshal.verify_fix_loop`, one fix turn per run and `MRS-DISP-060`, and
  points to the run's `journal.jsonl` `dispatch-verify-fix` entries. A test asserts that the passage exists, or a grep
  in `## Verification` checks it.
- **AC9 — Mutation.**
  - Restoring the `verify command '`-only parse fails AC1's test: no turn launches.
  - Dropping the `cross_surface_checks` reports from the extraction input fails AC1's tail assertion.
  - Making the budget per gate (counting only OUTCOMEs whose INTENT has the same `trigger_gate`) fails AC3's test.

## Boundaries & Constraints

**Always:**
- One parser for the verify-refusal message family, and one extraction (`extract_failed_verify_commands`), each
  reused by every caller and never copied.
- Scrub before tail, with the policy's `verify_fix_output_tail_bytes` bound (Stories 85.3/85.4), for the
  cross-surface output exactly as for a story command.
- Reconcile every governed path the change touches on the memlogs of the Specs that govern it, then stamp those Specs
  scoped. The supervisor and core modules are governed by `spec-pyforge-marshal` and `spec-pyforge-core`, plus
  whatever co-governors `spec-surface-check` names. `docs/how-to/troubleshoot-bmad-agent-loops.md` is governed by
  `spec-pyforge-doctor` (AGENTS.md pre-PR item 5).

**Never:**
- Never a second fix turn in a run, and never a per-gate budget.
- Never a turn for a refusal whose failed set is still empty: `MRS-GATE-002`/`-003` (a command that could not run or
  parse), `MRS-GATE-018` and the other non-command gates keep today's no-turn path.
- Never relax verification, change which cross-surface rules run, or change `pyforge.marshal.verify_fix_loop` or its
  per-environment values.
- Never downgrade a `MRS-GATE-015` finding through the Story 28.22 reclassifier.
- Never put the two-state test teaching into this story's prompt change. That is the deferred follow-up in this
  spec's frontmatter.

**Residual risk:** `platform-ci-local -- --test` is the slowest cross-surface command. A turn that re-runs it may
spend its 900 s budget and park with `MRS-DISP-059`, as any slow turn does today.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-10 (cross-surface fix turn) entry.
- Epic: Epic 85 (a fix joins its own epic, which reopens; doctor Story 41.5, as Story 85.6 did).
- Ledger key: `85-7-a-cross-surface-refusal-gets-the-same-one-fix-turn`.
- Ledger status at mint: `backlog`.
- Deps: none.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- AC8: `grep -n "MRS-GATE-015" docs/how-to/troubleshoot-bmad-agent-loops.md` and `grep -n "MRS-DISP-060" docs/how-to/troubleshoot-bmad-agent-loops.md` each print a line.
- Mutation: restore the `verify command '`-only parse in the extraction and re-run the station suite; AC1's test fails. Restore it.
- `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0 after the memlog reconciles and scoped stamps.
- On the next dispatch whose only refusal is cross-surface, the run's `journal.jsonl` shows a `dispatch-verify-fix` INTENT with `trigger_gate: MRS-GATE-015`.
