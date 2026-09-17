---title: One workspace opens every repo a story touches
type: dream
owner: steward
status: archived   # 2026-08-22 — spec-multi-repo-workspaces, decomposed into the station backlog same day
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-steward]]** on 2026-09-17 (one-chain-per-station steward fold; folded from `multi-repo-workspaces`).


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

## Realization log

- **2026-08-22** — Seeded from the seven-repo external analysis (`f0c695758c`);
  `spec-multi-repo-workspaces` derived under pyforge-steward and decomposed into the station backlog
  the same day (`a20192dd84`). Spec status `ready`.
- **2026-09-09 (fleet readiness pass)** — Log resumed; it had stopped at 2026-08-22 while the epic finished (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, Class B row stB / § 2.3 **C7**). CAP-1/CAP-2 are built and `done` (Stories 13.3, 13.4): `start_repo_set` / `status_repo_set` / `clean_repo_set` and `.code-workspace` generation at `workspace.py:277`, `:394`, `:413`, `:239`, registry path `.steward/repo-sets.yaml` at `:38`. **Never adopted** — no `.steward/repo-sets.yaml` exists; `git ls-files .steward/` returns only `keys-inventory.yaml` and the two `.example.yaml` files. **Decision: park with a named trigger — "when a second repo joins the estate", i.e. `python-foundry`, Story 44.3.** Adopting now would mean writing a repo-set naming a repo that does not exist. Status held at `specified`.
