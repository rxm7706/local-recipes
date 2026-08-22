---
spec: multi-repo-workspaces
status: ready
owner-dream: docs/dreams/multi-repo-workspaces.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/multi-repo-workspaces.md
open_questions:
  - "Where the repo-set registry lives (steward config vs a tracked manifest) — decide at 13.3."
---

# SPEC — One workspace opens every repo a story touches

## Why
Fleet work spans local-recipes + conda-forge-tracker + feedstock clones;
workspace tooling is single-repo (Epic 13's 13.1/13.2, backlog). Decision
(memlog): EXTEND Epic 13 — this is the layer above those verbs, not a
second system.

## Capabilities
- **CAP-1 — repo sets + coordinated start.** Declarative `[projects.<slug>]`
  repo sets; `steward workspace start <feature>` cuts one worktree per
  registered repo on branch `f-<feature>` and generates a
  `.code-workspace`. *Success:* one command opens the set; members missing
  locally are named, not guessed.
- **CAP-2 — set-level status + safe teardown.** Dirty/unpushed across the
  set in one command; removal refuses while any member is dirty.
  *Success:* the refusal names the dirty member; --merged-only honors 13.1's
  archive-not-delete discipline per member.

## Constraints
13.1/13.2's single-repo contract is the substrate (deps); the own-worktrees-
only HARD rule extends set-wide (loop homes stay invisible); sibling-org
pattern only, no prose/code import.

## Non-goals
Monorepo migration; bmad-switch scope (kin: bmad-switch-scope-enforcement);
cross-repo atomic commits.

## Success signal
A feature spanning three repos opens, reports, and tears down as one
workspace, with every single-repo guarantee intact per member.
