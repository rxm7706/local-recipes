---
title: One workspace opens every repo a story touches
type: dream
owner: steward
status: specified   # 2026-08-22 — spec-multi-repo-workspaces, decomposed into the station backlog same day
---

# One workspace opens every repo a story touches

## The Dream

Fleet work routinely spans local-recipes + conda-forge-tracker + feedstock
clones, but workspace tooling is single-repo: steward Epic 13
(spec-scratch-worktree-lifecycle, stories 13.1/13.2 backlog) manages
worktrees of THIS repo only. The dream: `steward workspace start <feature>`
cuts one worktree per registered repo on a shared feature branch, generates
a `.code-workspace`, answers dirty/unpushed status across the set in one
command, and refuses destructive removal while any member is dirty — the
repo set modeled declaratively (the org's `pyforge.toml [projects.<slug>]`
shape).

## Grounding

Imported from the sibling PyForge instantiation's ONLY substantive
capability gap vs this fleet: OpenTeams mgmt-wf's
`developer-workspace-management` dream (2026-08-22 analysis; unlicensed —
pattern adopted, prose not copied). Local kinship is live: Epic 13 is
backlog, so the spec pass DECIDES extend-Epic-13 vs new chain rather than
building two worktree systems.

## Constraints / Non-goals

Single-repo verbs stay 13.1/13.2's contract; this layers coordination above
them. Not a monorepo migration; not bmad-switch scope (kin:
`bmad-switch-scope-enforcement`).
