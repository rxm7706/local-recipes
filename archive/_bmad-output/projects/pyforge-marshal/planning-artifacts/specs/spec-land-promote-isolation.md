---
title: Land publishes the sprint ledger from an isolated worktree
type: feature
created: '2026-09-02'
status: in-progress
owner-dream: docs/dreams/sprint-status-auto-promote.md
context:
  - spec-sprint-status-auto-promote CAP-5
  - FR-136 leftover
  - Story 4.3 merge_branch isolation
---

<intent-contract>

## Intent

**Problem:** `_promote_sprint_ledger` committed the tracked twin on
`repo_root()` (`main`) after `gh pr merge` advanced `origin/main`. Local
`main` diverged every land (ahead-by-promote, behind-by-merge). The story
dispatch worktree is the wrong place for a `done` flip.

**Approach:** Fetch `origin/<landing_base_branch>`, read the twin at that
ref, render advancements, commit the bytes in a throwaway detached
worktree pinned to the remote tip, fast-forward-push the new commit to
`refs/heads/<base>`. Never `git checkout` / `commit_paths` / `update-ref`
on the operator checkout. Same isolation as `VcsPort.merge_branch`.

## Acceptance Criteria

- After a successful promote, the operator checkout's `HEAD` and working
  tree are unchanged by the promote commit.
- `origin/<base>` fast-forwards to a commit that contains only the
  promoted ledger path (AD-29).
- A non-fast-forward remote is `MRS-LAND-011` WARN; never `--force`.
- Existing 15.2 behavior holds: landing still triggers promote; lock
  contention still WARNs; already-`done` stays idempotent.

## Boundaries & Constraints

**Never:** Commit on operator `main`. Flip `done` on the open story PR.
`scripts/bmad-switch`. Second lock. History rewrite.

</intent-contract>
