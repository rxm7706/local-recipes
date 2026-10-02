---
title: '81.3: The campaign supervisor keeps --retry-environment-blocks across its cycles'
type: 'fix'
created: '2026-10-01'
status: 'in-progress'
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

- No review has run yet.
