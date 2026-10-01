---
title: '81.1: A drain cycle whose wave holds every story reports held instead of crashing'
type: 'fix'
created: '2026-10-01'
status: 'in-review'
baseline_revision: 'f73e1f3680068a50352326b7848ba17638756f87'
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

**Problem:** `cli/dispatch.py::execute_fleet_cycle` builds a station's cycle result from the queue walk's outcome when no
story was dispatched: `dispatch_fleet.StationCycleStatus(plan.outcome.value)`. The queue walk can answer
`StationQueueOutcome.DISPATCH` ("a story is eligible") while the parallel wave then holds every candidate out because their
declared Deps are not all done. `StationCycleStatus` has no `dispatch` value, so the cycle raises
`ValueError: 'dispatch' is not a valid StationCycleStatus` and the operator sees a traceback, not the reason. Found
2026-10-01: `marshal factory dispatch pyforge-marshal --stories 73.1,73.2` crashed this way while 73.1 waited on 66.1;
`drain --plan` reported the same state correctly as `held` (MRS-DRAINPLAN-004). Latent since 2026-09-01.

**Approach:**

- A held wave is reported as held: the station's cycle result reads a `held` status (added to `StationCycleStatus`) and a
  WARN finding names each held story with its unmet Deps, in the words `drain --plan` uses.
- Any queue outcome that has no cycle-status twin is mapped explicitly, never through `StationCycleStatus(value)`.

Ledger key: `81-1-a-drain-cycle-whose-wave-holds-every-story-reports-held-instead-of-crashing`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- Story 22.7 (the fleet-wide drain cycle) and Story 65.1 (`spec-pyforge-marshal` CAP-274, `drain --plan`'s `held`
  outcome). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a station whose queue walk picks a story and a parallel wave that holds every candidate for unmet Deps When `execute_fleet_cycle` runs Then the station result reads `held`, a WARN names each held story and its unmet Deps, and no exception escapes
- Given the same state When `marshal factory dispatch <slug> --stories <keys>` runs Then it exits through its normal verdict and reports the held stories
- Given a wave that admits at least one story When the cycle runs Then the result is unchanged (`dispatched`)
- Given the explicit mapping replaced by `StationCycleStatus(plan.outcome.value)` When the new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Report a held story; never dispatch it early. Keep the queue walk and the wave planner pure.

**Never:** Do not change which stories a wave admits. Do not change `drain --plan`'s output.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` -- `execute_fleet_cycle`: two sites built the cycle status as `StationCycleStatus(plan.outcome.value)` (no next story; empty wave). The empty-wave one crashes on `DISPATCH`. `plan_station_cycle` / `StationCyclePlan` hold the facts (`wave`, `deps_graph`, `statuses`, `stories_to_dispatch`); `skip_basis` is the precedent for a helper the cycle and `drain --plan` share.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py` -- `StationQueueOutcome`, `StationCycleStatus`, `TERMINAL_STATION_STATUSES`, `campaign_complete` / `unresolved_stations` (the only status consumers: a terminal status stops the campaign supervisor).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_prelaunch.py` -- `unmet_deps` (pure Deps readiness); the home of the shared held-reason wording.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/drain_plan.py` -- `_held_reason` and the `held` rows: read-only evidence of the wording to keep; its output must not change.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` / `core/verdict.py` -- `MRS-DRAIN-016` (a story refused from a wave, dep-unmet included) is `WARN`; reused, so no new code to register.
- `src/shared/packages/pyforge-marshal/tests/unit/test_drain_plan.py` / `test_dispatch_fleet.py` -- cycle fixtures (`_run_one_cycle`, `_seed_unmet_deps`, `_plan`) and the core-level status tests.

## Tasks & Acceptance

**Execution:**
- `core/dispatch_fleet.py` -- add `StationCycleStatus.HELD`, make it terminal, and add `idle_station_status(outcome)`, an explicit total mapping from every `StationQueueOutcome` (`DISPATCH` -> `HELD`) -- the enum lookup is the defect
- `core/dispatch_prelaunch.py` -- add `held_reason(story, statuses, graph, wave)`, the one wording of why the wave holds a story out -- `drain --plan` and the cycle must not drift
- `cli/dispatch.py` -- add `wave_held_stories(cycle)`; map both idle sites through `idle_station_status`; on an empty wave report `held`, with one `MRS-DRAIN-016` WARN per held story the refusal loop has not already named, and the held stories and reasons in `detail`
- `cli/drain_plan.py` -- delegate `_held_reason` and the held-story selection to the shared helpers, output unchanged
- `tests/unit/test_drain_plan.py`, `tests/unit/test_dispatch_fleet.py` -- tests for each Acceptance Criterion, the mapping's totality and the terminal status
- `spec-marshal-single-story-dispatch/fleet-drain-playbook.md` -- the campaign exit criteria list `held` among the terminal statuses

**Acceptance Criteria:**
- Given an empty wave on an eligible head, when `execute_fleet_cycle` runs, then the station reads `held`, a WARN names the story and its unmet Deps, and no exception escapes
- Given the same state, when `factory dispatch <slug> --stories <keys>` runs, then it exits through its normal verdict, spawns no campaign supervisor, and reports the held stories
- Given a wave that admits a story, when the cycle runs, then it reads `dispatched` with no held finding
- Given the enum lookup restored at the empty-wave site, when the new tests run, then they fail

## Spec Change Log

## Design Notes

`held` is terminal. A held station only moves once a Dep lands outside its own drain, which a supervisor tick cannot cause; left non-terminal, the campaign would poll a station that cannot progress. A station still working elsewhere in the fleet keeps the campaign going, and every cycle re-plans every station, so a Dep that lands is picked up. `MRS-DRAIN-016` is reused rather than minting a code: its registry text already covers a story held from a wave for unmet Deps.

## Binding

Parent: Story 22.7's fleet cycle and Story 65.1 (CAP-274); defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-01 (evening) entry.
Ledger key: `81-1-a-drain-cycle-whose-wave-holds-every-story-reports-held-instead-of-crashing`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-01 by operator ruling: fix the defect now.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
