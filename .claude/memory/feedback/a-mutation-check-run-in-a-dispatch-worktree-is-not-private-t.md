---
name: "a-mutation-check-run-in-a-dispatch-worktree-is-not-private-t"
description: "A mutation check run in a dispatch worktree is not private: the harness auto-checkpoint (wip: <story> auto-checkpoint)…"
metadata:
  type: feedback
---

A mutation check run in a dispatch worktree is not private: the harness auto-checkpoint (wip: <story> auto-checkpoint) commits the working tree every few minutes, so a temporary source mutation can land in a commit (marshal 82.6: b0673f5108 held 'ceilings = None' while the real code was restored on disk, and git status then read M, not clean). Restore from a backup, then prove it against the last good commit with git diff <commit> HEAD --stat -- src (expect empty), not just cmp against your own backup; prefer mutating a copy. Related trap: a spec frontmatter deferred: item reds the deferred-work detector until it has a ledger twin; run python scripts/deferred_work_intake.py --fix --project <short-slug> (e.g. marshal) rather than hand-writing the DW row.
