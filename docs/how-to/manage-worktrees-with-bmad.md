---
sources:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - scripts/worktree_sweep.py
  - scripts/bmad-switch
  - _bmad/scripts/resolve_config.py
  - docs/how-to/detect-concurrent-agent-activity.md
verified: 2026-09-19
---

# How to Manage Worktrees with BMAD

PyForge employs a strictly isolated branching strategy. Every agent and human sub-task must operate in its own Git worktree and land its changes through a PR. The primary trunk (`main`) must never be modified directly by a development session.

To enforce this, we use the station wrappers instead of raw `git worktree add`.

## Why Not Raw `git`?

A raw `git worktree add` creates an isolated filesystem space, but it does not know about the gitignored Tier-3 sprint feeds, the `BMAD_ACTIVE_PROJECT` resolution, or the station environments.

Two wrappers exist, for two different kinds of worktree:

1. **Story dispatch worktrees** — `marshal factory dispatch <slug> <key>` provisions a fresh isolated worktree from `origin/main` and launches exactly one detached `bmad-build-auto` story session with `BMAD_ACTIVE_PROJECT` set per-invocation and physical artifact paths; `marshal factory spin` launches a multi-story `bmad-loop` run in the station's loop home under `~/.bmad-loops/<station>` (bmad-loop stamps each story's `task.baseline_commit` when its worktree opens). Both journal the launch, and `marshal land` is how their waves land.
2. **Scratch worktrees** — `steward workspace start <slug>` creates a branch `<slug>` off `origin/main` (override with `--from BRANCH`) in a tool-owned scratch worktree and records it in steward's bookkeeping; `steward workspace ls` / `status` / `clean` manage only worktrees the tool created.

```bash
pixi run -e pyforge-guild marshal factory dispatch <slug> <story-key>
pixi run -e pyforge-guild steward workspace start <slug>
```

> [!CAUTION]
> **Never run `scripts/bmad-switch` from a parallel agent session.** The switch is per-working-tree global state (a marker file plus two gitignored symlinks) that concurrent agents will silently re-point under each other. Address projects by physical path (`_bmad-output/projects/<slug>/planning-artifacts/…`) or pass `BMAD_ACTIVE_PROJECT=<slug>` per invocation, which outranks the marker in `_bmad/scripts/resolve_config.py` and mutates nothing shared. The one exception is inside a bmad-loop run worktree, which has its own copy of that state.

Before any broad `git add` or push in a shared checkout, check whether another session is already working there: [Detecting concurrent agent activity](detect-concurrent-agent-activity.md).

## Cleaning Up Worktrees

When a task is merged and the branch is deleted, sweep the stale worktrees to prevent disk exhaustion and stale reference errors.

```bash
python scripts/worktree_sweep.py            # dry run: one verdict per registered worktree
python scripts/worktree_sweep.py --execute  # apply the safe verdicts
```

The sweep is dry-run by default. It classifies every registered worktree (`KEEP`, `PRUNE`, `DELETE`, `PRESERVE-THEN-DELETE`, `DELETE-WORKTREE-KEEP-BRANCH`, `INSPECT`) and with `--execute` removes only the provably safe ones — clean trees whose HEAD is an ancestor of `main`, or ledger-`done` stories whose branch is on `origin` — preserving a `format-patch` of anything unmerged first. It never deletes branches (unless `--delete-merged-local-branches` is given), never touches `loop/<station>` heads or `attempt-preserve/*`, and never removes the primary checkout or a loop home. The marshal-native equivalent for per-story branches is `marshal retire` (dry-run by default, `--execute` to delete). Scratch worktrees made by steward are archived, not deleted, with `steward workspace clean`.
