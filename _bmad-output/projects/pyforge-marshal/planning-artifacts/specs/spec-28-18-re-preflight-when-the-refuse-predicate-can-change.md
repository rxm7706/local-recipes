---
title: 'Re-preflight when the refuse predicate can change (Story 28.18, Epic 28)'
type: 'feature'
created: '2026-09-01'
status: 'done'
updated: '2026-09-01'
review_loop_iteration: 1
followup_review_recommended: false
difficulty: medium
baseline_revision: 20e88e8b0fd1ccd2cc38101691ac72aeb8df71cc
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-drain-self-resolution/SPEC.md
  - docs/dreams/marshal-dependency-aware-dispatch.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred:
  - summary: >-
      MRS-GATE-010 (missing spec binding) rate-limits on spec-only fingerprint
      change like verify gates; may need refuse_still_applies parity with
      MRS-DISP-005 in a follow-up.
    evidence: |-
      reconcile_station_re_preflight applies verify_rerun_needed gating to all
      MRS-GATE-* gates; MRS-GATE-010 is spec-missing, not verify-failure.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_re_preflight.py:116-204
    severity: low
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

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_re_preflight.py` — pure predicate hashing, reconcile, verify-rerun helper
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` — `_reconcile_campaign_blocked_for_re_preflight`, journal `refuse_predicate` payload, `MRS-DRAIN-017`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py` — `StationCycleResult.refuse_predicate`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` / `core/verdict.py` — register `MRS-DRAIN-017`
- Tests: `tests/unit/test_dispatch_hotfix.py`, `tests/unit/test_dispatch_fleet.py`

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- Fixture: refuse → create spec file → next tick dispatches

## Review Triage Log

### 2026-09-01 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (medium 1, low 0)
- defer: 0
- reject: 0
- addressed_findings:
  - `[medium]` `[patch]` Verify-gate re-preflight cleared on spec-only predicate change, which would re-dispatch and re-run verify — rate-limit instead when `verify_rerun_needed()` is false.

### 2026-09-01 — Review pass 2
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 1: (low 1)
- reject: 0
- addressed_findings:
  - none

### 2026-09-01 — Review pass 3 (bmad-build-auto re-run)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 12
- addressed_findings:
  - none

### 2026-09-01 — Review pass 4 (bmad-build-auto dispatch)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 8
- addressed_findings:
  - none

## Auto Run Result

Status: done

**Summary:** Fleet drain re-preflights campaign-blocked stories whose refuse predicate can change. When a missing spec (`MRS-DISP-005`) later appears, the block clears and the next tick dispatches. Unchanged predicates are rate-limited with `MRS-DRAIN-017`. Verify-gate refuses rate-limit when only the spec glob changes; the block clears only when the verify fingerprint changes.

**Files changed:**
- `core/dispatch_re_preflight.py` — predicate hashing, reconcile, verify-rerun gating for MRS-GATE
- `cli/dispatch.py` — integrate reconcile before each cycle; journal predicates
- `core/dispatch_fleet.py` — optional `refuse_predicate` on cycle results
- `core/findings.py`, `core/verdict.py` — `MRS-DRAIN-017`
- `tests/unit/test_dispatch_hotfix.py`, `test_dispatch_fleet.py`, `test_findings.py`

**Review:** One medium patch applied (AC3 verify-gate spec-only rate-limit).

**Follow-up review:** false (1 medium patch; score 3 < 5).

**Verification:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 7367 passed, 0 failed (re-verified 2026-09-01 bmad-build-auto dispatch). Story-scoped tests (8) for re-preflight/reconcile also green.

**Residual risks:** Mergeable/GitHub predicate re-preflight deferred to a later story.
