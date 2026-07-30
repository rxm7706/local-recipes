---
title: Genesis — the seed of the operating model
type: dream
owner: guild
status: specified
---

# Genesis — the master idea, and the seed that plants it

> **Constitutive (`owner: guild`, Charter §5).** This Dream and the Charter are the two
> that precede the stations; their chains live in the `pyforge-genesis` project, which
> records the Charter, the Lexicon, and the Guild's membership.
>
> **The installer is not held here** *(split 2026-07-28)*. `genesis init` / `genesis adopt`
> — the machine that installs this model into any repo — is buildable work owned by the
> **Marshal**: **[[genesis-installer]]**. This Dream is what gets installed; that Dream is
> what installs it. The § Frontier note below is superseded by the split.

## The Dream

Genesis is three things in one. **The master idea**: the umbrella narrative that
describes the personas, the setup, and the vision of a monorepo that builds
software libraries, skills, agents, and crews using BMAD-method. **The alignment
instrument**: one deck that onboards anyone into the whole model in ten minutes.
And **the seed**: the bootstrapper that installs the operating model anywhere —

- **Greenfield**: `genesis init` — a new repository born Dream-first:
  `docs/dreams/`, the tier layout, agent conventions (AGENTS.md family), BMAD
  multi-project wiring, and the deck family, from day zero.
- **Brownfield**: `genesis adopt` — layer the model onto an existing repo
  without disturbing what already runs. **This repo was the first brownfield
  adoption.**

## What is real

- The **master vision deck** `presentations/pyforge-genesis/` (13 slides:
  Dream → Deck → Spec → Code, the crew, the Master Pipeline, proof, "Genesis is
  also the seed"), seeded into Claude Design via the bridge.
- The **origin document**: `archive/docs/bmad-setup-plan.md` — *"greenfield + brownfield,
  multi-project, unattended"* — the plan that set this repo up; Genesis is that
  plan, generalized beyond one repo.
- The operating model itself, proven in production here: Tier 0 Dreams,
  BMAD-produced specs, graduated autonomy ([[pyforge-marshal]]), the bridge
  ([[design-code-bridge]]).

## The frontier

- The installer (`genesis init` / `genesis adopt`) as a buildable tool — awaits
  its own `bmad-spec` run when the model stabilizes.
- Extraction question: what is copied (conventions, skills, workflows) vs.
  referenced (bmad-method releases) vs. generated (per-repo Dreams).

## Realization log

- **~2026-07 (setup plan)** — the model installed here, by hand, from
  `archive/docs/bmad-setup-plan.md`.
- **2026-07-23** — the Dream-first governance landed repo-wide; the master deck
  seeded; named `pyforge-genesis` (the origin-story deck of the family).
- **2026-07-23 (gist audit)** — grounding: `docs/intake/gists/how-we-operate/` ("documentation as programmable infrastructure" — the operating philosophy in embryo).
- **2026-07-23 (evening)** — master deck refreshed to the **eight-persona** crew: mottos grid 4×2 (+Scribe, +Steward), a Throughout-row in the Master Pipeline, "One Dream, nine decks"; re-seeded to Design via the bridge.
