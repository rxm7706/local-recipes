---
title: Marshal — autonomy a human can trust
type: dream
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

## The frontier

- **W4**: BMad Method UI dashboards (`bmad-ui` env, consume-not-submit mirrors).
- Formal L-level labeling of story modes; fleet-level resource budgets.
- The `marshal` CLI as a named product (today the capability runs as bmad-loop).

## Realization log

- **2026-07 (bmad-loop-adoption spec)** — 6.6.0→6.10.0 upgrade, loop adoption
  W1–W3 done (validate 9/9, sprint feed 20/20).
- **2026-07-17/18** — atlas proven: a full system shipped unattended-with-gates.
- **2026-07-23** — Dream retro-seeded; chapter deck seeded; origin plan
  `docs/bmad-setup-plan.md` (also the seed of [[pyforge-genesis]]).
