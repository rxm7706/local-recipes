---
title: 'Re-preflight when the refuse predicate can change (Story 28.18, Epic 28)'
type: 'feature'
created: '2026-09-01'
status: 'ready'
updated: '2026-09-01'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: medium
baseline_revision: 20e88e8b0fd1ccd2cc38101691ac72aeb8df71cc
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-drain-self-resolution/SPEC.md
  - docs/dreams/marshal-dependency-aware-dispatch.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Fleet drain treats the first `MRS-DISP-005` / similar refuse as
permanent for the campaign (`MRS-DRAIN-005` never auto-retried). After steward
39.4's spec landed on `main`, the live supervisor kept refusing every 60s.

**Approach:** Re-evaluate a refused backlog head when the refuse predicate can
change (spec glob, mergeable). Hash the predicate; identical refuse is
rate-limited. Expensive `verify_commands` re-run only on hash change.

## Acceptance Criteria

- Given a station refused on `MRS-DISP-005`, when a unique `spec-<e>-<n>-*.md`
  appears, then the next eligible drain tick dispatches that story (no bare
  `factory dispatch`, no new campaign).
- Given the same refuse predicate as last tick, when the supervisor ticks, then
  it does not re-dispatch and journals a rate-limited skip.
- Given a verify-command refuse, when only the spec glob changed, then
  `verify_commands` are not re-run solely because the tick fired.

## Boundaries & Constraints

**Always:** Physical paths; `BMAD_ACTIVE_PROJECT=pyforge-marshal` per
invocation — never `scripts/bmad-switch`.

**Never:** Weaken `MRS-DISP-011` live-session refuse. Auto-author specs
(28.19). Silent unlimited verify loops.

Ledger key: `28-18-re-preflight-when-the-refuse-predicate-can-change`.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` — spec lookup already used for `MRS-DISP-005`
- Tests: new unit coverage next to `test_dispatch_hotfix.py` / fleet-drain tests

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- Fixture: refuse → create spec file → next tick dispatches
