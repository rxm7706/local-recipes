---
title: "83.10: A verification refusal never relaunches a fresh session or raises the model"
type: 'fix'
created: '2026-10-03'
status: 'done'
baseline_revision: '302b6ad99859f4305316a419b3b3afba2f5545e3'
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

**Added 2026-10-03 (landing review):**
- Given a story with a prior refused run whose worktree spec reads `status: blocked` When the drain plan evaluates it Then it refuses MRS-DISP-045, as before this story.
- Given a story refused at MRS-GATE-018 after a finished session When it is next dispatched Then that refusal does not count toward `max_dev_attempts`, and an operator fix (head moved) takes the land-only path.
- Given a parked story When the plan reports it Then the reason names the failed verification command or message from the refused run.

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

## Spec Change Log

- 2026-10-03 — sent back by the operator session after the landing review (findings below). Three acceptance criteria added. Status back to `ready-for-dev`.

## Review Triage Log

### 2026-10-03 (later) — Landing review (operator session) — landed by hand
- PR #1773 was merged before this session's fixes were pushed, so `main` carried the first session's code. The supervisor then read the story as merged on `main` and stopped without verifying or pushing. The operator session landed this session's fix commits through a new PR.
- The three findings below are fixed: the blocked refusal stays reachable, MRS-GATE-018 is in the set, and the park reason names the failed message.
- `low` `patch` (applied by the operator session) The blocked-refusal fix had no test. `test_a_blocked_worktree_spec_with_a_prior_run_is_still_disp_045` adds one (it fails with the old `elif` chain).

### 2026-10-03 — Landing review (operator session) — sent back
- `high` `patch` **The drain plan stops refusing blocked stories.** `cli/drain_plan.py` `evaluate_story` inserts `elif latest_journal is not None:` ahead of `elif status == "blocked": refuse("MRS-DISP-045", ...)` in the same `if`/`elif` chain. So any story with a prior run, which every re-dispatched story has, enters the new branch, and the MRS-DISP-045 refusal for a `blocked` worktree spec is never reached. Fix: decide the verification-refusal land-only as its own step (for example `if not land_only and latest_journal is not None: ...`) and keep the blocked refusal reachable whenever the story is not land-only.
- `medium` `patch` **MRS-GATE-018 is not a verification refusal here.** Story 83.2 added MRS-GATE-018 (the pre-verification deferred-work intake refused; `core/verdict.py` maps it to `GATE_FAILED`), and it is a dispatch verification refusal like 001-006. But `_VERIFY_REFUSAL_GATES` does not list it. So a 018 refusal still counts toward Story 33.6's floor-raise, and never takes the land-only path after an operator fix. That is what happened to 83.3's run `pyforge-marshal-20261003T133852198Z-8c6f8963`. Fix: add MRS-GATE-018 to the set, with a test.
- `medium` `patch` **The park reason does not name the failed command.** `format_verification_refusal_park_reason` takes `failed_command`, but `station_story_block_facts` never passes it. So the park reason names only the gate, and the first acceptance criterion asks for the failed verification command. Fix: pass the refused verification's failed command or message from the journal (`dispatch-verification` outcome `failed_message`), and test the text.

### 2026-10-03 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none — adversarial self-review found no patch-worthy gaps beyond Story 83.10 tests)

## Auto Run Result

Status: done

Summary: Landing-review fixes: drain plan keeps `MRS-DISP-045` reachable when a prior run exists; `MRS-GATE-018` is a verification refusal for park/land-only and floor-raise exclusion; park reasons include the journaled verification `failed_message`.

Files changed:
- `core/dispatch_retry.py` — add `MRS-GATE-018` to verification refusal gates
- `core/dispatch.py` — `DispatchJournalFacts.verification_failed_message`
- `cli/dispatch.py` — read `failed_message` from verification journal; pass into park reason
- `cli/drain_plan.py` — verification-refusal land-only and blocked refusal are separate steps
- `tests/unit/test_dispatch_retry_83_10.py` — 018 + park message + terminal classification

Review: 0 patch-worthy findings on pass 2; followup_review_recommended false.

Verification: `pyforge-marshal-test` pass (10917 tests); `pyforge-deps-test` pass; `lint-types` pass; `python scripts/spec_surface_reconcile.py` exit 0 after memlog reconcile on `spec-pyforge-marshal` and co-governor `spec-pyforge-core`.
