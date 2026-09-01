---
title: 'Re-preflight when the refuse predicate can change (Story 28.18, Epic 28)'
type: 'feature'
created: '2026-09-01'
status: 'done'
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
  - summary: >-
      AC3 verify non-execution is proven via reconcile block retention only;
      no fleet-level test spies verify_commands subprocess invocation.
    evidence: |-
      test_reconcile_rate_limits_verify_refuse_when_only_spec_changes asserts
      RATE_LIMITED at reconcile layer; no execute_fleet_cycle test counts
      evaluate_dispatch_verification calls when spec glob changes alone.
    location: >-
      src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_hotfix.py:270-294
    severity: low
  - summary: >-
      _campaign_blocked_from_journal accumulates every historical REFUSED row;
      a later DISPATCHED cycle does not prune the block, so a third tick may
      re-clear and re-attempt dispatch (mitigated by in-flight / done checks).
    evidence: |-
      dispatch.py:2945-2966 replays all REFUSED outcomes; no test covers
      refuse → spec lands → dispatch succeeds → next supervised cycle.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py:2904-2967
    severity: low
  - summary: >-
      MRS-DRAIN-017 rate-limit findings are emitted to stdout/findings but not
      persisted in the campaign journal outcome payload.
    evidence: |-
      _journal_fleet_cycle() does not store findings list; predicate recovery
      depends on older REFUSED rows with refuse_predicate sidecar.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py:2160-2200
    severity: low
  - summary: >-
      Parallel wave dispatch stores one refuse_predicate per station using
      primary_story; refused non-primary members lack journal predicates.
    evidence: |-
      execute_fleet_cycle computes refuse_predicate for primary_story only when
      cycle_status is REFUSED; mixed DISPATCHED+REFUSED waves skip predicate
      entirely.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py:2847-2867
    severity: low
  - summary: >-
      Legacy REFUSED journal rows without refuse_predicate sidecar rate-limit
      forever on MRS-GATE-* even when verify_commands policy changes.
    evidence: |-
      reconcile_station_re_preflight treats prior is None as rate-limit without
      reaching verify_rerun_needed clear path.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_re_preflight.py:175-187
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
- defer: 4: (low 4)
- reject: 0
- addressed_findings:
  - none

### 2026-09-01 — Review pass (bmad-build-auto dispatch, Cursor)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

### 2026-09-01 — Review pass 3 (bmad-build-auto, Cursor)
- intent_gap: 0
- bad_spec: 0
- patch: 1: (medium 1, low 0)
- defer: 2: (low 2)
- reject: 0
- addressed_findings:
  - `[medium]` `[patch]` `refuse_still_applies` treated `spec:unreadable` as cleared for MRS-DISP-005, causing dispatch retry loops — now rate-limits like `spec:missing`; added unit tests.

## Auto Run Result

Status: done

**Summary:** Fleet drain re-preflights campaign-blocked stories whose refuse predicate can change. When a missing spec (`MRS-DISP-005`) later appears, the block clears and the next tick dispatches. Unchanged predicates are rate-limited with `MRS-DRAIN-017`. Verify-gate refuses rate-limit when only the spec glob changes; the block clears only when the verify fingerprint changes. Review pass 3 fixed unreadable-spec rate-limiting.

**Files changed:**
- `core/dispatch_re_preflight.py` — predicate hashing, reconcile, verify-rerun gating; unreadable spec stays blocked
- `cli/dispatch.py` — integrate reconcile before each cycle; journal predicates
- `core/dispatch_fleet.py` — optional `refuse_predicate` on cycle results
- `core/findings.py`, `core/verdict.py` — `MRS-DRAIN-017`
- `tests/unit/test_dispatch_hotfix.py`, `test_dispatch_fleet.py`, `test_findings.py`

**Review:** Intent-alignment audit — all three ACs satisfied at operational surfaces. Pass 3 applied one medium patch (unreadable spec); two new low items deferred (parallel-wave predicate, legacy journal without sidecar). Six low items total in frontmatter `deferred`.

**Follow-up review:** false (1 medium patch; score 3 < 5).

**Verification:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — **7369 passed**, 12 deselected (2026-09-01, bmad-build-auto dispatch).

**Residual risks:** Items tracked in frontmatter `deferred`. Mergeable/GitHub predicate re-preflight deferred to a later story.
