---
title: "83.10: A verification refusal never relaunches a fresh session or raises the model"
type: 'fix'
created: '2026-10-03'
status: 'done'
baseline_revision: 'd82497d9c5a21d3a1a6b7d681577c96a10df3dd8'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/drain_plan.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `core/dispatch_retry.py` classifies a dispatch verification refusal (`MRS-GATE-001`..`006`, `010`, `011`, `015`) as `TRANSIENT`, so a campaign's next cycle re-dispatches the story as a fresh bmad-build-auto session, and after `max_dev_attempts` failed attempts `resolve_dispatch_model_with_retry_escalation` (Story 33.6) floor-raises the dev model to the review tier. A finished session's work is thrown away and redone on a refusal that is usually mechanical. On 2026-10-03 the Epic 83 campaign re-ran 83.2 three times as full sessions (24.7 + 10.3 + 13.4 min, the third floor-raised to opus by Story 33.6), each refused at verification on the same unformatted line; every other Cursor story refused at verification (83.3, 83.6, 66.2, 84.1) was fixed by hand and re-dispatched for land-only, each fix costing about four more full-suite runs.

**Approach:** A refusal at dispatch verification after a session finished its work is not retried by launching a new session. The story is parked for the operator with a finding naming the failed command, unless its branch head has moved since the refused verification (someone fixed it), in which case the campaign takes the land-only path (re-verify the existing branch, no session). Verification refusals no longer count toward Story 33.6's floor-raise; that escalation stays for failed sessions (a crash, a halt, a blocked run, a harness failure). When Story 85.1's flag is on, its single fix turn runs before the park.

Ledger key: `83-10-a-verification-refusal-never-relaunches-a-fresh-session-or-raises-the-model`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- Story 33.6 (spec-adaptive-model-tiering CAP-2 on factory dispatch), the dispatch hotfix of 2026-09-01 (`core/dispatch_retry.py`) and Story 29.2 (land-only). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a story whose latest run finished its session and was refused at dispatch verification, and whose branch head is unchanged since When the next campaign cycle plans Then it launches no session, parks the story with a finding naming the failed verification command, and reports it as parked, never as dispatched
- Given the same story after its branch head moved (an operator fix) When the next cycle plans Then it takes the land-only path (re-verify the branch, merge on green), launching no session
- Given a story with prior verification refusals When it is next dispatched for any reason Then the refusals do not count toward `max_dev_attempts`, and the dev model is not floor-raised for them
- Given a story whose session failed (crash, halt, blocked, harness failure) When it is retried Then retry and Story 33.6's floor-raise behave as today
- Given the park rule removed When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Fix the defect where the shipped behaviour lives (`core/dispatch_retry.py`, the campaign's retry decision, `_count_prior_failed_dispatch_attempts`), and pin it with a test that fails without the fix. The single-story `marshal factory dispatch` override (an operator's explicit re-dispatch) keeps working.

**Never:** Never discard the refused branch or its worktree. Never relaunch a fresh session for a verification refusal from inside a campaign. Never change how session failures are retried or escalated.

</intent-contract>

## Binding

Parent: Story 33.6, the 2026-09-01 dispatch hotfix (`core/dispatch_retry.py`) and Story 29.2.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (evening) entry.
Ledger key: `83-10-a-verification-refusal-never-relaunches-a-fresh-session-or-raises-the-model`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 at the operator's request, from the verification cost analysis of that date.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

### 2026-10-03 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none — adversarial self-review found no patch-worthy gaps beyond Story 83.10 tests)

## Auto Run Result

Status: done

Summary: Verification refusals after finished session work now classify as terminal (park) when the branch head is unchanged, land-only when the operator moved the head, and are excluded from Story 33.6's prior-failure counter.

Files changed:
- `core/dispatch_retry.py` — park/land-only helpers; verify gates with git progress are TERMINAL
- `core/dispatch_harness_done.py` — `should_take_verification_refusal_land_only`
- `cli/dispatch.py` — block facts, floor-raise count, CAP-4 land-only wiring
- `cli/drain_plan.py` — drain plan land-only for fixed branches
- `tests/unit/test_dispatch_hotfix.py`, `tests/unit/test_dispatch_retry_83_10.py` — regression + mutation

Review: 0 patches applied; followup_review_recommended false.

Verification: `pyforge-marshal-test` pass (10913 tests); `pyforge-deps-test` pass; `lint-types` pass; `python scripts/spec_surface_reconcile.py` exit 0 after memlog reconcile on `spec-pyforge-marshal` and co-governor `spec-pyforge-core`.
