---
title: '81.3: The campaign supervisor keeps --retry-environment-blocks across its cycles'
type: 'fix'
created: '2026-10-01'
status: 'done'
baseline_revision: '6f444ca2edf47a292ae77461ffc8c36eb063dd4c'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** `cli/dispatch.py::_spawn_campaign_supervisor` starts the detached `dispatch_fleet_supervisor` with the
campaign's mode, cycle bounds, station, story list, harness and in-flight cap (Story 22.11 threads the scoping flags so
"every SUPERVISED tick re-runs the SAME scoped/sequenced" campaign), but not `retry_environment_blocks`. A campaign
launched with `--retry-environment-blocks` therefore skips an environment-classified block only in its foreground first
cycle; every supervised cycle after it runs without the flag, stops on the same block (MRS-DRAIN-005) and the campaign
ends. Found 2026-10-01: campaign `pyforge-marshal-20261001T214108388Z-9418f6e6` exited after one cycle on 81.1's
OAuth-refresh block while 81.2 was still running.

**Approach:** `_spawn_campaign_supervisor` takes `retry_environment_blocks` and passes it on the supervisor's argv;
the supervisor parses it and hands it to every `run_fleet_drain` cycle it runs. False stays the default.

Ledger key: `81-3-the-campaign-supervisor-keeps-retry-environment-blocks-across-its-cycles`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- Story 22.11 (FR-193 CAP-10, the campaign's flags threaded through every supervised tick). A defect of shipped
  behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a campaign launched with `--retry-environment-blocks` When its supervisor is spawned Then the spawn argv carries the flag and the supervisor's parsed arguments read it true
- Given that campaign's second cycle and an environment-blocked story When the cycle runs Then the story is skipped (MRS-DRAIN-004) and the next eligible story is dispatched
- Given a campaign launched without the flag When its supervisor runs Then cycles behave as today
- Given the flag dropped from the spawn argv When the new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Thread the flag the way Story 22.11 threads station and stories.

**Never:** Do not change how a block is classified. Do not retry or skip a story-classified block.

</intent-contract>

## Code Map

All paths under `src/shared/packages/pyforge-marshal/`.

- `src/pyforge/marshal/cli/dispatch.py::_spawn_campaign_supervisor` -- builds the detached supervisor's argv; takes `station`/`stories`/`harness`/`max_in_flight` (Story 22.11), no `retry_environment_blocks`. Positional contract, empty string = unset.
- `src/pyforge/marshal/cli/dispatch.py::run_fleet_drain` -- the one call site (`_spawn_campaign_supervisor(...)`, after `execute_fleet_cycle`), which already reads `args.retry_environment_blocks` for the foreground cycle; the MRS-DRAIN-007 recovery message below it repeats `--station`/`--stories`.
- `src/pyforge/marshal/dispatch_fleet_supervisor/__main__.py` -- `main` (supervisor argparse), `run_fleet_campaign_supervisor`, `build_cycle_argv` (the `marshal factory drain --once --campaign <id>` argv every supervised tick re-runs; this is how a flag reaches `run_fleet_drain` on cycle 2+). Imports nothing from `cli/` (AD-9).
- `src/pyforge/marshal/cli/main.py::_build_parser` -- the real parser; reuse in the test to turn `build_cycle_argv` output into the Namespace a cycle sees.
- `src/pyforge/marshal/core/dispatch_fleet.py` (~l.949-1017) -- `retry_environment_blocks` consumer; read-only here (classification is out of scope).
- `tests/unit/test_dispatch_fleet.py` -- `test_dispatch_supervisor_re_invocation_carries_station_and_stories` (`build_cycle_argv`), `test_stories_supervisor_reinvocation_via_run_fleet_drain_carries_stories` (spawn argv via `FakeProcess.spawned`), `test_retry_environment_blocks_cli_wiring_moves_past_crash` (cycle skip), `_drain_args`/`_run_drain`/`_seed_live_dispatch_journal` helpers.

## Tasks & Acceptance

**Execution:**
- `src/pyforge/marshal/cli/dispatch.py` -- `_spawn_campaign_supervisor` gains `retry_environment_blocks: bool = False`; when true the supervisor argv ends with the `--retry-environment-blocks` flag (omitted when false, so the default argv is byte-identical); the `run_fleet_drain` call site passes `bool(getattr(args, "retry_environment_blocks", False))`; the MRS-DRAIN-007 recovery command repeats the flag -- cycle-2 behaviour must survive a manual resume the way `--station`/`--stories` do
- `src/pyforge/marshal/dispatch_fleet_supervisor/__main__.py` -- `main` parses `--retry-environment-blocks` (`store_true`); `run_fleet_campaign_supervisor` and `build_cycle_argv` take `retry_environment_blocks` and append `--retry-environment-blocks` to the tick argv when true
- `tests/unit/test_dispatch_fleet.py` -- spawn-argv test through the real `run_fleet_drain` path (flag present when set, absent when not); `main` parse test (flag reads true, default false); `build_cycle_argv` test (present/absent); end-to-end cycle-2 test feeding `build_cycle_argv` through the real `_build_parser` into a campaign cycle over an environment-blocked story (MRS-DRAIN-004, next story dispatched)

## Design Notes

The supervisor's own CLI is positional (empty string = unset) because `station`/`stories`/`harness`/`max_in_flight` are always supplied. A boolean has no useful empty-string form, so it rides as an optional `--retry-environment-blocks` flag appended after the positionals and only when true; argparse reads a trailing flag after `nargs="?"` positionals without ambiguity, and a false flag leaves the argv unchanged.

## Binding

Parent: Story 22.11 (FR-193 CAP-10); defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-01 (night) entry.
Ledger key: `81-3-the-campaign-supervisor-keeps-retry-environment-blocks-across-its-cycles`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-01 under the operator's ruling to fix the drain defects found that day now.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

### 2026-10-01 — Review pass
- verdicts: 16 findings — high 0, medium 4, low 6, false 6, maybe-false 0
- findings:
  - `[low]` `[patch]` (Blind Hunter) the MRS-DRAIN-007 recovery hint still omits `--harness` and `--max-in-flight`, which the supervisor spawn carries — real: the gap predates this story but sits in the block this change edits, and the repo rule is fix-now; fixed: the hint appends ` --harness <v>` and ` --max-in-flight <n>` when set, and `test_manual_resume_hint_repeats_retry_environment_blocks` asserts both
  - `[medium]` `[patch]` (Blind Hunter) no test feeds the argv `_spawn_campaign_supervisor` actually emits into the supervisor's `main`; the parse test hand-writes its positionals, so spawn/parser drift passes — real, and AC1 reads "the supervisor's parsed arguments read it true" from the spawn argv; fixed: the spawn test now runs `sup.main(campaign_argv[3:])` with a recording process and reads the tick argv back through the real `_build_parser`
  - `[false]` `[reject]` (Blind Hunter) the MRS-DRAIN-007 change has no acceptance criterion — no bad outcome: the Tasks list names it, the Always clause says to thread the flag the way Story 22.11 threads station and stories, and 22.11's own patch pass put those in the same hint; the only fix is to edit this build's spec
  - `[false]` `[reject]` (Blind Hunter) the `--retry-environment-blocks` help text is not updated — no sentence is wrong: the help already describes the flag as skipping environment blocks for the drain, never as first-cycle-only; the defect was behaviour falling short of it
  - `[low]` `[patch]` (Blind Hunter) `bool(getattr(args, "retry_environment_blocks", False))` is written twice in `run_fleet_drain` — real developer-only drift risk; fixed: computed once above the cycle `try:` and read by the cycle call, the spawn and the recovery hint
  - `[low]` `[reject]` (Blind Hunter) nothing enforces parity between the drain parser's campaign options and `build_cycle_argv` — a parity meta-test needs an exclusion list for the launch-only flags (`--plan`, `--once`, `--campaign`, `--all-stories`), so the fix is more than a direct correction and a second omission is unlikely in everyday use
  - `[low]` `[reject]` (Blind Hunter) an already-running campaign and the exited campaign named in the Problem have no documented resume path — inherent to a detached supervisor's fixed argv; `drain --campaign <id> --retry-environment-blocks` already respawns a flagged supervisor, and a documentation-only fix is not worth a spec edit
  - `[medium]` `[patch]` (Blind Hunter) the envelope does not report the setting, and the diff carries no memlog entry or Dream line — the memlog part is real (`spec_surface_reconcile.py` names governed paths missing from the owning memlog); fixed: surface-reconcile entries naming `cli/dispatch.py`, `dispatch_fleet_supervisor/__main__.py` and `tests/unit/test_dispatch_fleet.py` appended to `spec-pyforge-marshal`, `spec-pyforge-core`, `spec-marshal-drain-self-resolution` and `spec-marshal-verify-fail-terminalization`; the envelope field is rejected (a new JSON envelope surface the intent does not ask for) and the Dream line is left as minted (its 2026-10-01 night entry already links Story 81.3)
  - `[low]` `[patch]` (Edge Case Hunter) same root cause as the first Blind Hunter row — the recovery hint drops `--harness` and `--max-in-flight`; fixed by the same patch
  - `[low]` `[reject]` (Edge Case Hunter) the flag is not recorded in the campaign journal, so a later non-once `drain --campaign <id>` without it spawns a flagless supervisor beside the flagged one — the same limitation holds for `--station`, `--stories`, `--harness` and `--max-in-flight` (the Story 22.11 pattern the Always clause names); persisting launch flags is a new mechanism, and the trigger is an operator re-running a second drain by hand
  - `[medium]` `[patch]` (Edge Case Hunter) same root cause as the second Blind Hunter row — the supervisor `main` is never tested with the argv the spawn emits; fixed by the same patch
  - Verification Gap Reviewer: reported no findings (zero rows)
  - `[medium]` `[patch]` (Intent Alignment) AC1's "parsed arguments" half is exercised through hand-built positionals and no single test chains spawn, `main` and the tick — same root cause as the second Blind Hunter row; fixed by the same patch
  - `[false]` `[reject]` (Intent Alignment) the cycle-2 test bypasses the spawn and runs the tick in-process rather than as a subprocess — the in-process run uses the same `_build_parser` and `run_fleet_drain` the subprocess `python -m pyforge.marshal.cli.main` runs, and a dropped spawn flag is caught by the spawn test and the chained test (all three mutations re-run after the patch pass failed at least one new test)
  - `[false]` `[reject]` (Intent Alignment) the MRS-DRAIN-007 change goes beyond the intent text — same refutation as the third Blind Hunter row: the Always clause covers it
  - `[false]` `[reject]` (Intent Alignment) a broader reading (every launch flag survives every cycle) is not implemented — the intent itself excludes it: the Problem, Approach, title and ledger key name only `retry_environment_blocks`, and the other flags already ride the spawn
  - `[false]` `[reject]` (Intent Alignment) cycle 1 of the cycle-2 test does not model the flagged foreground cycle — cycle 1 only mints the campaign directory the tick re-enters; the flagged foreground behaviour is already covered by `test_retry_environment_blocks_cli_wiring_moves_past_crash`

## Auto Run Result

Status: done
Blocking condition: none

**Summary.** A campaign launched with `--retry-environment-blocks` now keeps the flag on every supervised cycle. `_spawn_campaign_supervisor` appends a trailing `--retry-environment-blocks` to the detached supervisor's argv when set; the supervisor parses it and `build_cycle_argv` re-appends it to the `marshal factory drain --once --campaign <id>` tick argv. Without the flag the argv is unchanged, and block classification is untouched.

**Files changed** (under `src/shared/packages/pyforge-marshal/`):
- `src/pyforge/marshal/cli/dispatch.py` -- `_spawn_campaign_supervisor` takes `retry_environment_blocks`; `run_fleet_drain` computes it once and passes it to the cycle, the spawn and the MRS-DRAIN-007 hint, which now also repeats `--harness` and `--max-in-flight`.
- `src/pyforge/marshal/dispatch_fleet_supervisor/__main__.py` -- `main` parses the flag; `run_fleet_campaign_supervisor` and `build_cycle_argv` thread it onto every tick.
- `tests/unit/test_dispatch_fleet.py` -- spawn-argv round trip through the supervisor `main` and the real `marshal` parser, `main` parse, `build_cycle_argv`, a cycle-2 test (skip with MRS-DRAIN-004 versus stop with MRS-DRAIN-005), and the recovery-hint test.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/{spec-pyforge-marshal,spec-pyforge-core,spec-marshal-drain-self-resolution,spec-marshal-verify-fail-terminalization}/.memlog.md` -- surface-reconcile entries naming the three governed paths above; no baseline stamped.

**Review findings.** 16 findings (high 0, medium 4, low 6, false 6, maybe-false 0). 7 rows routed to patch, grouped into 4 entries: the recovery-hint omissions (`low`), the spawn-to-`main` round-trip test (`medium`), the duplicated flag expression (`low`) and the memlog surface reconcile (`medium`). 0 deferred. 9 rows rejected: 3 `low` (parity meta-test, running-campaign resume note, persisted launch flags -- each needs more than a direct correction and is unlikely in everyday use) and 6 `false`, each on the refutation recorded in the triage log. The Verification Gap Reviewer reported nothing.

**Follow-up review recommendation: false.** Patched entries at entry verdict: medium 2, low 2. No unverified risk remains: every patch was re-verified on the patched tree (full station suite, `pyforge-deps-test`, `lint-types`, `spec_surface_reconcile.py`) and the three AC4 mutations were re-run after the patches.

**Verification performed** (exit codes read directly, not through a pipe):
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- exit 0, 9764 passed, 1 skipped.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- exit 0, 130 passed, 3 skipped.
- `pixi run --frozen -e pyforge-guild lint-types` -- exit 0.
- `python scripts/spec_surface_reconcile.py` -- exit 0 (no drift), run after the memlog entries.
- AC4 mutation: dropping the flag at the spawn call site, in `build_cycle_argv`, or in `main` each fails one of the new tests; the files were restored and show no diff.

**Residual risks.** A running campaign keeps its old supervisor argv until it is respawned (resume with `drain --campaign <id> --retry-environment-blocks`). Launch flags are not persisted in the campaign journal, so a second manual drain without the flag beside a live supervisor still runs flagless -- the same limitation `--station`/`--stories` already have.
