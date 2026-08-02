---
title: One front door — Marshal drives everything BMAD installs
type: dream
owner: marshal
status: archived
archived-reason: absorbed
---

> **Superseded 2026-08-02 (dream consolidation).** Fully decomposed into `spec-pyforge-marshal`
> and the real PRD as FR-65 (`marshal check` — the detector registry through a single command,
> context resolved once per invocation) — see
> [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md). This Dream's other candidate verbs
> (`run`/`status`/`land`) were found convergent with already-specified FRs (FR-9/10/11 `factory
> spin`, FR-59/60 `land`) during the 2026-08-01 decomposition and correctly did not get new FR
> numbers. See `spec-one-front-door` for the retirement record.

# One front door — Marshal drives everything BMAD installs

> **Draft for refinement.** Seeded 2026-07-31 on an operator call; the inventory
> below is derived from the tree, but the *boundaries* — what Marshal drives, what
> it merely routes to, and what it should never touch — are open. Edit freely.

## The Dream

The Charter says **execution has one owner: Marshal**. Today that is true of
accountability and false of interface. What is actually installed is a toolbox of
**11 packages, 51 BMAD skills, 16 Skill Forge skills, 10 detectors, an engine, a
dashboard and a multi-project switch** — and the way you use it is to remember
which one you need, in what order, with which project active.

The Dream is that **one front door drives all of it**. Not a new tool: a
*conductor* for the tools already here, holding the context they each need and
that a human currently holds in their head.

> A toolbox is not a factory. The difference is that somebody knows the order.

## What Marshal would drive — the inventory

Derived from the tree 2026-07-31. **This is the list to argue with.**

| # | Installed surface | What it is | Marshal's role |
|---|---|---|---|
| 1 | **`bmad-loop` 0.9.0** | The engine — run/resume/resolve/sweep/status/attach/stop/clean | **wrap** (never absorb) |
| 2 | **`bmad-method` 6.10.0** | 51 skills: planning · dev · review · sprint · personas · research · docs | **route + context** |
| 3 | **BMB** `bmad-builder` 2.1.0 | Author custom agents & workflows | route |
| 4 | **TEA** `…test-architecture-enterprise` 1.19.1 | Risk-based test strategy | route |
| 5 | **CIS** `…creative-intelligence-suite` 0.2.1 | Brainstorming, design thinking | route |
| 6 | `bmad-manticore` · `bmad-labs-skills` · `bmad-utility-skills` · `bmad-method-wds-expansion` · `bmad-module-template` | Installed, largely unexercised here | **triage — keep or drop?** |
| 7 | **Skill Forge** — 16 `skf-*` skills | Skill authoring, campaigns, audits | route |
| 8 | **`bmad-dashboard` 1.2.2.dev0** + `docs/dashboard/` | The Guildhall board | own (it reports Marshal's runs) |
| 9 | **Multi-project wiring** — `bmad-switch`, marker, two symlinks, six-layer config | Which project is active | **own — it is already Marshal's** |
| 10 | **Loop homes** — `bmad-loop-worktree`, `marshal init/homes` | Isolated worktrees per station | **own — shipped** |
| 11 | **10 detectors** + the derived registry | drift · chain · surface · story-status · stall · layout · unpushed · … | own (invoke; Doctor judges Marshal's row) |
| 12 | **Tier layout** — `docs/dreams/`, `_bmad-output/projects/<station>/` | Dream → Spec → chain → stories | own |
| 13 | **Repo gates** — linter, `maintenance` label, `environment.yaml` sync, PR lifecycle | What landing requires | own ([[pr-lifecycle]]) |
| 14 | **`conda-forge-expert` 8.81.0** | The packaging craft (Rule 1: any BMAD agent doing conda work must wield it) | route — **Mason's craft, not Marshal's** |

## Why now

This session is the argument. Driving *one* fleet run end to end meant hand-invoking:
`bmad-loop run` · `bmad-loop status` · `tmux capture-pane` · seven detectors ·
`dashboard-gen` · `dashboard-watch` · `spec-surface-check --write-baseline` ·
`git push` across nine homes · `gh pr create/edit/merge` five times.

Every one is documented. None is composed. The operator asked "is marshal's work
saved?" and the honest answer required four separate commands — because no single
thing knows what a run *is*.

And the failure modes were all seams: `dashboard-watch` was never started because
nobody thought of it; the push window reopened because nothing owned it; #170
merged broken because the landing path asked nothing. **A front door is where
seams go to be owned.**

## The frontier — and the open questions

- **`marshal <verb>` as the composed surface.** Candidate verbs, to argue with:
  `run` (drive a story/epic — wraps the engine) · `status` (one answer across
  fleet, board, detectors, unpushed work) · `check` (the detector registry) ·
  `land` ([[pr-lifecycle]]) · `switch`/`homes` (shipped) · `doctor` (delegate).
- **Route, do not re-implement.** The moment Marshal *contains* a skill instead of
  invoking it, `wrap, never absorb` has been broken one level up. Unresolved:
  where exactly is that line for the 51 skills?
- **Context is the product.** The value is not shorter commands, it is that the
  active project, loop home, policy layer and story key are supplied *once*.
- **Triage row 6.** Five installed packages this repo barely exercises. Keep,
  wrap, or remove? An unexercised dependency is surface area with no owner.
- **Row 14 is a boundary test.** CFE is Mason's craft. Marshal routing to it is
  fine; Marshal *knowing conda* is not — §4, *each works one craft, not all*.

## What this is not

[[genesis-installer]] **installs** this surface — greenfield `init`, brownfield
`adopt`, the write guard, managed regions. It is `specified` with a full chain.
This Dream is the **runtime** half: once installed, who drives it. Install-time
and run-time are different jobs, and merging them would give one Dream two.

Nor is it a replacement for any tool listed above. Every row keeps its owner and
its interface; the front door composes them.

## Kinships

[[genesis-installer]] (installs what this drives — the two halves of the same
promise) · [[pyforge-marshal]] (the station; this is its CLI cadence made real) ·
[[pr-lifecycle]] (the last mile, one verb behind this door) · [[durable-runs]]
(a seam a front door would own) · [[agent-portability]] (the door must not assume
one coding CLI) · [[pyforge-charter]] (§ Execution Doctrine — *execution has one
owner*).

## Realization log

- **2026-07-31** — Dream seeded (operator call: "Marshal should install and be an
  orchestrator and wrapper around all that's installed around BMAD"). The
  *install* half was found already owned by [[genesis-installer]] (`specified`,
  full chain), so this Dream is scoped to the **runtime** half only, and the
  boundary is stated above rather than left to be discovered. Inventory derived
  from the tree at seeding: 11 conda packages, 51 `bmad-*` skills, 16 `skf-*`,
  10 detectors, 9 projects. Left deliberately open for operator refinement: the
  verb list, the route-versus-contain line, and the row-6 triage.
