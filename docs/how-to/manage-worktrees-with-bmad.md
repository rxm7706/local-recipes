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
python scripts/worktree_sweep.py --remote   # dry run: KEEP / DELETE / INSPECT per origin branch
python scripts/worktree_sweep.py --remote --execute  # delete DELETE branches on origin (manifest first)
python scripts/worktree_sweep.py --retire attempt-preserve/name  # explicit protected-branch retirement (names only)
```

The sweep is dry-run by default. It classifies every registered worktree (`KEEP`, `STALE-LOCK`, `PRUNE`, `DELETE`, `PRESERVE-THEN-DELETE`, `DELETE-WORKTREE-KEEP-BRANCH`, `INSPECT`) and scans unregistered directories under `.claude/worktrees/`, `.cursor/worktrees/`, and `~/.cursor/worktrees/` as `ORPHAN-DIR` (never `~/.bmad-loops/`). With `--execute` it removes only the provably safe ones — clean trees whose HEAD is an ancestor of `main`, merged `STALE-LOCK` agent worktrees whose pid is gone, empty orphan directories, or ledger-`done` stories whose branch is on `origin`. When `pyforge.marshal.preserve_refs` is **off**, unmerged or dirty done stories still get a `format-patch` under `--preserve-dir` first; when the flag is **on**, the sweeper writes an annotated `refs/tags/preserve/…/sweep-<sha8>` tag (including untracked files in the snapshot) before `git worktree remove`, tries to push it through the content gate, and reports unpushed tags as preserve debt rather than refusing removal. With the flag on it also classifies local engine scratch (`refs/heads/attempt-preserve/*`, `refs/attempt-preserve-dirty/*`): unpromoted scratch stays `KEEP`, promoted scratch (a preserve tag names it and contains its tip) is retired on `--execute`. Local branch deletion with `--delete-merged-local-branches` writes an `archive/heads` twin first when the tip would orphan commits. It never deletes `refs/tags/**`, never touches protected branch prefixes while the flag is off (`loop/`, `attempt-preserve/`, `recover/`, `rescue/` — see `docs/governance/guild-roster.json` `protected_refs`), and never removes the primary checkout or a loop home.

**Remote branches (`--remote`).** The same tool classifies every `origin` head: `KEEP` (for example `main`, a protected prefix, an open PR head, a branch checked out in any worktree, or a live dispatch run), `DELETE` (tip is an ancestor of `origin/main`, or the PR merged, or the PR closed with a ledger-`done` story), or `INSPECT` (everything else). Dry run is the default; `--remote --execute` writes a JSON manifest under `--preserve-dir` before the first delete, then removes only `DELETE` branches. A delete that would orphan commits first writes and pushes an annotated `refs/tags/archive/heads/<branch>` twin through `pyforge.core.preserve_refs` (content gate); ancestor tips skip the twin. The effective protected list is the script code floor (`refs/heads/main`, `refs/heads/loop/`, all `refs/tags/`) unioned with `guild-roster.json` `protected_refs` (the roster can only add). Tags are never delete candidates. Branches that GitHub rulesets forbid deleting (today `loop/**` and `attempt-preserve/**`) are refused with a finding that names the ruleset.

**Explicit retirement (`--retire <branch>…`).** Retires only the branch names given on the command line (never globs or patterns), with the same manifest-before-delete and archive-twin rules. Ruleset-protected names are refused with a finding; use this for operator-approved retirement of other protected prefixes (for example legacy `recover/` branches) after review.

Per-story loop-home branch retirement remains `marshal retire` (dry-run by default, `--execute` to delete). The sweeper is the permanent home for worktree and remote branch hygiene (2026-10-03 ruling). Scratch worktrees made by steward are archived by default with `steward workspace clean`; use `steward workspace clean --delete` to drop gone or proven-landed workspaces without an archive.
