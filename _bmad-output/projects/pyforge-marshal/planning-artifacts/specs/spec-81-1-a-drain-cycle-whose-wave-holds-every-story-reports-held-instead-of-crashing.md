---
title: '81.1: A drain cycle whose wave holds every story reports held instead of crashing'
type: 'fix'
created: '2026-10-01'
status: 'backlog'
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
