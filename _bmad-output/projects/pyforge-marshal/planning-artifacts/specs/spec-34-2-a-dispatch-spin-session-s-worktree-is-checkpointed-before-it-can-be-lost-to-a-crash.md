---
title: "A dispatch/spin session's worktree is checkpointed before it can be lost to a crash"
type: 'feature'
created: '2026-09-10'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** A dispatch or spin session that crashes (terminal/IDE crash, not a code failure)
loses every uncommitted change in its worktree unless the operator notices and manually
`git add -A && git commit`s a recovery checkpoint before relaunching. Hit four separate times in
one session (doctor 21.1 twice, herald 19.1, steward 48.6 twice) across two terminal crashes —
every recovery was done by hand, live, under time pressure. Real work (a completed story once,
hundreds of lines of a WebSocket-streaming feature another time) sat one `git worktree` cleanup
away from silent loss each time. Marshal's own supervisor already polls these sessions for
completion; it never checkpoints their in-flight worktree state.

**Approach:** The supervisor's own poll loop detects uncommitted changes in the story's worktree
and, once the session has been idle past a threshold, commits a local-only
`wip: <story> (auto-checkpoint)` commit — never pushed, never opens a PR, purely a local safety
net. Also expose an explicit `factory checkpoint <slug>` call for an operator to trigger one
on demand.

## Boundaries & Constraints

**Always:**
- The checkpoint commit is LOCAL-ONLY: never pushed, never opens a PR.
- Checkpointing fires from the supervisor's existing poll loop (uncommitted changes + idle past
  threshold) or on an explicit `factory checkpoint <slug>` call.
- The commit message is clearly marked as an auto-checkpoint (`wip: <story> (auto-checkpoint)`),
  distinguishable from a real dev-session commit.

**Never:**
- Never pushes or opens a PR from an auto-checkpoint commit — landing a story stays a
  human/operator-triggered act.
- Never checkpoints a CLEAN worktree (nothing to commit) — no-op, not an empty commit.
- Never interferes with a live, actively-writing session — checkpointing only fires once the
  session has been idle past the threshold, avoiding a race with the session's own writes.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Live reproduction (the motivating case) | A dispatch/spin session crashes mid-story with real uncommitted progress in its worktree | A prior auto-checkpoint commit exists, so the crash loses at most the checkpoint interval's worth of work | n/a |
| Clean worktree | Session idle past threshold, nothing uncommitted | No-op, no empty commit | n/a |
| Explicit trigger | Operator calls `factory checkpoint <slug>` | Checkpoints immediately regardless of idle threshold | n/a |
| Active session | Session still actively writing (not idle past threshold) | No checkpoint fires, avoiding a race with in-flight writes | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/supervise.py` — the dispatch/spin supervisor's own polling loop; add checkpoint detection + commit.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py` — the commit primitive.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` or a new `cli/checkpoint.py` — the explicit `factory checkpoint <slug>` entrypoint.
- `src/shared/packages/pyforge-marshal/tests/unit/test_supervise*.py` — new fixtures.

## Tasks & Acceptance

**Execution:**
- `feature` — extend the supervisor's poll loop to detect uncommitted worktree changes.
- `feature` — commit a local-only `wip: <story> (auto-checkpoint)` commit once the session has been idle past a threshold, with uncommitted changes present.
- `feature` — add an explicit `factory checkpoint <slug>` CLI entrypoint for an on-demand checkpoint.
- `feature` — add a fixture simulating a mid-session crash after the checkpoint fires and asserting the worktree's uncommitted changes survive as a commit.
- `feature` — add a fixture confirming a clean worktree produces no checkpoint commit.

**Acceptance Criteria:**
- Given four separate crash recoveries in one session each required the operator to manually checkpoint uncommitted worktree changes before a story could be safely relaunched, when the supervisor's own poll loop detects the worktree has uncommitted changes and the session has been idle past a threshold (or an explicit `factory checkpoint <slug>` call is made), then it commits a local-only `wip: <story> (auto-checkpoint)` commit — never pushed, never opens a PR.
- A fixture simulates a mid-session crash after the checkpoint fires and asserts the worktree's uncommitted changes survive as a commit, not as working-tree state a `git worktree remove --force` could destroy.

## Spec Change Log

## Review Triage Log
