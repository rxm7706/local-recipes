---
name: "never-run-a-realize-step-that-installs-git-hooks-pre-commit"
description: "Never run a realize step that installs git hooks (pre-commit install) from a linked worktree: .git/hooks is shared thro…"
metadata:
  type: feedback
---

Never run a realize step that installs git hooks (pre-commit install) from a linked worktree: .git/hooks is shared through the common git dir, so the hooks get repointed at that worktree's own .pixi interpreter and break every other checkout once the worktree is removed. Story 100.7 hit this (2026-10-14); the register row now carries primary_checkout_only: true and estate realize reports skipped-worktree. Repair from the primary checkout: .pixi/envs/pyforge-guild/bin/pre-commit install --hook-type pre-commit --hook-type pre-push --hook-type commit-msg.
