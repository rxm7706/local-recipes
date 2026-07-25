---
title: Marshal — autonomy a human can trust
type: dream
owner: marshal
status: realized
---

# Marshal — graduated autonomy on the factory floor

## The Dream

The Commander's dream: **unattended development loops a human can actually
trust.** Not autonomy as a leap of faith — autonomy as a *gradient*: attended
stories first, then unattended loops wrapped in verify gates and quality gates,
with a hard rule that anything the agent cannot safely decide **escalates to a
human** instead of being guessed. Spec in, validated code out, every run
visible. Anti-vibe, by construction.

## What is real

- **bmad-loop v0.8.1 + bmad-dev-auto**: the deterministic dev-loop orchestrator
  (tmux-driven Claude Code sessions, graduated gates, CRITICAL escalation via
  `bmad-loop-resolve`, deferred-work ledger + sweep). It has shipped real
  systems: [[pyforge-atlas]] end-to-end (32/32) and [[pyforge-warden]] to 23/31.
- **The bmad-suite**: BMAD 6.10 (BMM 34+ workflows) + BMB/TEA/BMGD/CIS, web
  bundles (Gemini Gems / Custom GPTs for flat-rate planning), community plugins
  (skill-forge), and the multi-project machinery (`scripts/bmad-switch`,
  per-project config/artifact isolation).
- **Visibility**: sprint-status feeds → the GitHub Pages program console
  (`docs/dashboard/`), kept honest (2026-07-23 correction: dashboards must be
  regenerated from ledgers, never hand-trusted).
- Live governance evidence: per-story `mode: ATTENDED/…` in story_meta; model-tier
  policy (sonnet default, opus for hard stories); this maps directly onto the
  L1–L5 taxonomy in [[agentic-sdlc-autonomy]].

## The execution doctrine (affirmed 2026-07-23)

> **Execution has one owner (Marshal). Skills — existing, community, and forged —
> are the unit of execution; the deterministic harness is the unit of governance;
> station verdicts stay independent. That triad is the whole agentic SDLC, at
> every autonomy level.**

- **One owner:** all execution — any story, any autonomy level up to unattended —
  runs on Marshal's line. Other personas own their *stations' verdicts*, never
  the loop: the hand that builds must not be the gate that judges it.
- **Skills are the unit of execution:** BMM's 34+ workflows, community plugins,
  and newly forged skills (BMB, the `skf-*` forge, the Rule-2 retro loop that
  continuously re-forges domain skills). Everything agentic ships as a skill.
- **The harness is the unit of governance — and is deliberately NOT a skill:**
  bmad-loop itself, sandbox/permission gates, CI verify gates, and no-LLM
  deterministic tools sit outside the skill layer, because the thing that
  governs the agent cannot be a thing the agent authors.
- **Two persona layers:** the PyForge Guild are the factory's *stations*; the
  BMAD team (Mary · John · Winston · Sally · Amelia · Paige) are Marshal's
  *sub-agents on the floor* — the inner workforce his line mobilizes.

## The frontier

- **W4**: BMad Method UI dashboards (`bmad-ui` env, consume-not-submit mirrors).
- Formal L-level labeling of story modes; fleet-level resource budgets.
- The `marshal` CLI as a named product (today the capability runs as bmad-loop).
- **Many lines, one floor — concurrent loop isolation.** Today only one loop can
  run per checkout: the active-project symlinks + marker are per-working-tree
  global state, and two loops would also thrash the working tree's HEAD. The
  design that removes the ceiling: one **git worktree per loop** (own HEAD; own
  gitignored symlinks/marker via `bmad-switch` run inside it), a **shared
  Tier-3 store** (a worktree's `implementation-artifacts` symlinks back to the
  main checkout's — no migration, same repo-relative path for every consumer),
  `BMAD_ACTIVE_PROJECT` exported per-loop as belt-and-suspenders, and
  rebase-before-merge at `main`. Root-cause fix (the hard-coded
  `planning_artifacts` key composing with project config) belongs upstream in
  bmad-method. First live proof: the [[regenerable-factory]] backfill loop and
  the [[pyforge-warden]] 6.3 resume running concurrently.

## Realization log

- **2026-07 (bmad-loop-adoption spec)** — 6.6.0→6.10.0 upgrade, loop adoption
  W1–W3 done (validate 9/9, sprint feed 20/20).
- **2026-07-17/18** — atlas proven: a full system shipped unattended-with-gates.
- **2026-07-23** — Dream retro-seeded; chapter deck seeded; origin plan
  `docs/bmad-setup-plan.md` (also the seed of [[pyforge-genesis]]).
- **2026-07-23 (later)** — concurrent-loop isolation SHIPPED as
  [[regenerable-factory]] Wave 0: worktree-aware `bmad-switch` (Tier-3
  backlink) + `scripts/bmad-loop-worktree` (provision / --verify / --remove);
  live proof `--verify pyforge-warden deckcraft` → ISOLATION OK. Spec:
  `spec-multi-loop-isolation` (local-recipes planning-artifacts).
- **2026-07-24** — spec BACKFILLED (user-directed, closing the last realized-Dream
  gap): `spec-pyforge-marshal` kernel (local-recipes planning-artifacts) binds
  `.bmad-loop/**` into governance, adopting the multi-loop-isolation kernel +
  the bmad-loop-adoption spec; grounded live by the warden 6.3/6.5 wave.
