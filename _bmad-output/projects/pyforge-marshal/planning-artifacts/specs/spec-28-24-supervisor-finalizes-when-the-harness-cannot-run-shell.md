---
title: 'Supervisor finalizes when the harness cannot run shell (Story 28.24, Epic 28)'
type: 'feature'
created: '2026-09-01'
status: 'done'
updated: '2026-09-02'
review_loop_iteration: 1
followup_review_recommended: false
difficulty: small
baseline_revision: eb1dbd6632ae67a4127ea17e2af43fe997d8ae69
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-drain-self-resolution/SPEC.md
  - docs/dreams/marshal-dependency-aware-dispatch.md
warnings: []
deferred:
  - summary: >-
      End-to-end dispatch_once integration test for MRS-DISP-039 not present;
      unit tests cover the helper directly.
    evidence: |-
      `_redispatch_blocked_pending_supervisor_finalize` is tested in isolation;
      no test exercises the full dispatch launch path that emits MRS-DISP-039.
    location: >-
      src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_finalize.py
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Dispatch of 28.18 left a commitable dirty worktree. The Cursor
session reported implementation done and “shell unavailable” (`pixi` / `git`
rejected in-session). Drain warned `MRS-DISP-036` and redispatched over dirt.
No `origin/dispatch/…` until a chat committed, pushed, and merged PR #1000.

**Approach:** Finalization is a **supervisor** duty, not a harness privilege.
When the session claims done or leaves a commitable dirty tree, marshal
commits, pushes (28.21 / CAP-4), and runs `verify_commands`. Do not loop
redispatch on dirt without that attempt. If supervisor shell fails, escalate.

## Acceptance Criteria

- Given a dispatch worktree with a commitable dirty tree and a session that
  reported done or shell-unavailable, when the supervisor tick runs, then
  marshal creates a story commit and `git ls-remote` shows
  `dispatch/<slug>/<story>`.
- Given `MRS-DISP-036` dirt, when the next drain cycle runs, then it does not
  redispatch the same story until finalize was attempted.
- Given supervisor `git`/`pixi` also fail, when status / fleet-picture run,
  then the station is `awaiting-operator` (or ATTENTION) naming the worktree
  path.

## Boundaries & Constraints

**Never:** Skip `verify_commands`. Force-push `main`. `scripts/bmad-switch`.
Commit secrets or untracked junk outside the story surface.

Ledger key: `28-24-supervisor-finalizes-when-harness-cannot-run-shell`.

</intent-contract>

## Code Map

- `dispatch_supervisor/__main__.py` — finalize: commit leftover, push, verify
- `cli/dispatch.py` / `core/dispatch_fleet.py` — do not redispatch on
  `MRS-DISP-036` until finalize attempted
- Tests: dirty worktree fixture + fake vcs/shell port

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`

## Review Triage Log

### 2026-09-02 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 1: (high 0, medium 1, low 0)
- reject: 0
- addressed_findings:
  - none

### 2026-09-02 — Review pass (verification retry)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

### 2026-09-02 — Review pass (bmad-build-auto re-run)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

### 2026-09-02 — Review pass (Cursor bmad-build-auto, shell unavailable)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

### 2026-09-02 — Review pass (Cursor bmad-build-auto dispatch worktree)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

### 2026-09-02 — Review pass (bmad-build-auto single-story dispatch)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

## Auto Run Result

Status: done

### Summary

Story 28.24 (CAP-7): when a dispatch session dies with commitable git progress but the harness could not run shell, the dispatch supervisor now commits leftover work, pushes the dispatch branch (28.21), and runs verify_commands. Drain refuses redispatch over MRS-DISP-036 dirt until a finalize attempt is journaled (MRS-DISP-039 ERROR). Supervisor shell failures surface as `awaiting-operator` in fleet status with the worktree path named.

### Files changed

| File | Change |
|---|---|
| `core/dispatch_supervisor_finalize.py` | New — finalize trigger classification, should-finalize gate, journal readers |
| `dispatch_supervisor/__main__.py` | Supervisor tick runs commit/push/verify finalize sequence; journals `dispatch-finalize` |
| `cli/dispatch.py` | MRS-DISP-039 redispatch block; `gather_fleet_finalize_escalations` |
| `core/dispatch.py` | `KIND_DISPATCH_FINALIZE` journal kind |
| `core/status.py` | Finalize escalation facts; `_apply_finalize_escalation` → `awaiting-operator` |
| `core/dispatch_fleet.py` | `FinalizeEscalation` dataclass |
| `cli/status.py` | Wire finalize escalations into fleet home facts |
| `core/findings.py` / `core/verdict.py` | Register MRS-DISP-039 (ERROR) |
| `tests/unit/test_dispatch_supervisor_finalize.py` | New — unit tests for all three ACs |
| `tests/unit/test_findings.py` | Register MRS-DISP-039 in catalog test |

### Review findings

- **Patches applied:** 0
- **Deferred:** 1 medium — end-to-end `dispatch_once` integration test for MRS-DISP-039 (unit tests cover helper directly)
- **Rejected:** 0

### Follow-up review recommendation

`followup_review_recommended: false` (0 patch findings across both review passes)

### Verification performed

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`: **PASS** — 7474 passed, 12 deselected (2026-09-02, initial run)
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`: **PASS** — 7474 passed, 12 deselected in 35.79s (2026-09-02, bmad-build-auto re-run)
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`: **PASS** — 7474 passed, 12 deselected in 34.91s (2026-09-02, dispatch worktree bmad-build-auto)
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`: **PASS** — 7474 passed, 12 deselected in 34.94s (2026-09-02, bmad-build-auto single-story dispatch)

### Residual risks

- Finalize sequence journals `ok=True` when commit/push succeed but verify_commands refuse — intentional per CAP-7 (shell failure escalation only applies to commit/push VCS errors).
