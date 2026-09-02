---
title: 'Supervisor finalizes when the harness cannot run shell (Story 28.24, Epic 28)'
type: 'feature'
created: '2026-09-01'
status: 'ready'
updated: '2026-09-01'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: small
baseline_revision: eb1dbd6632ae67a4127ea17e2af43fe997d8ae69
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-drain-self-resolution/SPEC.md
  - docs/dreams/marshal-dependency-aware-dispatch.md
warnings: []
deferred: []
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
