---
title: '83.5: A campaign supervisor keeps ticking through fleet-lock contention'
type: 'fix'
created: '2026-10-02'
status: 'in-progress'
baseline_revision: 'e32c50a30f0afc2bf42e6aa37e8f0f177bb84c0f'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `cli/dispatch.py::run_fleet_drain` refuses a cycle that cannot take the fleet cycle lock (MRS-DRAIN-010) and returns an envelope with no `data.complete`; `dispatch_fleet_supervisor.cycle_completion` reads that as unreadable, and after `_MAX_CONSECUTIVE_UNREADABLE_CYCLES` (5) the supervisor stops. On 2026-10-02 the marshal campaign stopped this way while a steward campaign held the lock, although the refusal's comment says the detached supervisor simply ticks again.

**Approach:** The MRS-DRAIN-010 refusal carries `data.complete: false`, so the supervisor reads it as an ordinary not-complete cycle and ticks again; the unreadable ceiling keeps counting cycles that truly cannot run.

Ledger key: `83-5-a-campaign-supervisor-keeps-ticking-through-fleet-lock-contention`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- Story 22.7 (fleet drain) and Story 22.11 (the campaign supervisor). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a cycle refused with MRS-DRAIN-010 When the supervisor reads it Then it reads as not complete, not unreadable, and ticks again
- Given five or more contended cycles in a row When the supervisor runs Then it does not stop
- Given a cycle that cannot run at all When it repeats Then it still counts toward the unreadable ceiling
- Given complete dropped from the refusal When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Fix the defect where the shipped behaviour lives, and pin it with a test that fails without the fix.

**Never:** Do not retry a cycle inside one tick. Do not raise the unreadable ceiling.

</intent-contract>

## Binding

Parent: Story 22.7 (fleet drain) and Story 22.11 (the campaign supervisor).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 (night) entry.
Ledger key: `83-5-a-campaign-supervisor-keeps-ticking-through-fleet-lock-contention`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-02 at the operator's request to chain the defects found landing Phase 2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.

### 2026-10-03 — Reset by the operator session
- Run `pyforge-marshal-20261003T020120169Z-d937e761` halted before any work: bmad-build-auto does not recognize the minted status `backlog` (step-01: "status missing or unrecognized"), so it set `blocked`. Status reset to `ready-for-dev`; nothing else changed. The seam defect is chained as Story 83.8.
