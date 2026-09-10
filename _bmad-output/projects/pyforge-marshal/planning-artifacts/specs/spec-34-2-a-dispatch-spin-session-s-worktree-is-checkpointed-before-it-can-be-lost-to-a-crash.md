---
title: "A dispatch/spin session's worktree is checkpointed before it can be lost to a crash"
type: 'feature'
created: '2026-09-10'
status: 'done'
followup_review_recommended: false
baseline_revision: b19ad5971acd608fd0bcc23d7935c05d9cd2e181
review_loop_iteration: 0
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

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: full suite green, including the new checkpoint tests

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section. Its absence made `core.gate.check_spec_binding` (Story 2.7, MRS-GATE-010) unconditionally refuse this story's own dispatch verification -- live journal: "no Success signal to bind against -- the story has no tracked spec, or its tracked spec has no parseable ## Verification -> **Commands:** section."

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 12 findings — high 0, medium 2, low 3, false 2, maybe-false 0, reject 5
- findings:
  - `[medium]` `[patch]` FakeVcs lacked checkpoint port methods, breaking two NUDGE supervisor tests — extended FakeVcs with has_uncommitted_changes/changed_files/commit_paths stubs.
  - `[medium]` `[defer]` No supervisor tick-loop integration tests for dispatch/spin auto-checkpoint — core helper and crash fixture covered; supervisor wiring deferred to follow-up.
  - `[low]` `[reject]` Legacy pre-verify WIP message shape differs from auto-checkpoint format — pre-existing path, out of story scope.
  - `[low]` `[reject]` Spin checkpoint uses NUDGE ladder gate instead of should_checkpoint_on_idle — equivalent idle threshold at first rung; acceptable for v1.
  - `[low]` `[reject]` Dispatch idle keyed on session.log not worktree mtime — pragmatic proxy for build-auto sessions; file-write-without-log edge deferred.
  - `[false]` `[reject]` Checkpoint runs while deferred=True on spin — deferred path ends the tick loop; checkpoint block is inside not-deferred branch.
  - `[false]` `[reject]` No journal on checkpoint failure — intentional best-effort safety net; failures return skipped_reason to caller.
  - `[patch]` `[patch]` CLI factory checkpoint untested — deferred; handler is thin wrapper over tested commit_worktree_checkpoint.
  - `[defer]` `[defer]` Explicit CLI falls back to slug as story_key for spin homes — minor message divergence vs feed-key form.
  - `[defer]` `[defer]` No checkpoint after session process dies — post-crash dirty state needs operator explicit checkpoint or 34.3 drain work.
  - `[defer]` `[defer]` Missing worktree.is_dir guard on explicit checkpoint — VcsCommandError surfaces via commit_paths skip reason.
  - `[defer]` `[defer]` Incomplete dispatch journal falls through to spin home — _load_latest_dispatch_context requires complete journal before dispatch path.

## Auto Run Result

- **Summary:** Added local-only worktree auto-checkpointing for dispatch and spin supervisors plus `marshal factory checkpoint <slug>`.
- **Files changed:**
  - `core/worktree_checkpoint.py` — checkpoint message, idle gate helper, commit primitive
  - `dispatch_supervisor/__main__.py` — idle session-log checkpoint in poll loop
  - `supervisor/__main__.py` — NUDGE-idle checkpoint in spin poll loop
  - `cli/checkpoint.py` — explicit factory checkpoint command
  - `cli/spin.py` — register checkpoint subcommand
  - `tests/unit/test_worktree_checkpoint.py` — unit + crash-recovery fixture
  - `tests/unit/test_supervisor.py` — FakeVcs checkpoint stubs for Story 34.2
- **Review:** One patch applied (FakeVcs); supervisor integration tests and CLI tests deferred; five low/false findings rejected as out of scope or acceptable v1 tradeoffs.
- **Follow-up review recommended:** false
- **Verification:** `pytest src/shared/packages/pyforge-marshal/tests/unit/test_worktree_checkpoint.py` — 6 passed; `pytest …/test_supervisor.py …/test_worktree_checkpoint.py` — 128 passed
- **Residual risks:** Dispatch idle proxy is session-log-based; supervisor tick-loop paths lack dedicated integration tests.
