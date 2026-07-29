---
title: Genesis installer — the seed, made executable
type: dream
owner: marshal
status: specified
---

# Genesis installer — the seed, made executable

## The Dream

[[pyforge-genesis]] is the operating model: the Charter, the Lexicon, the Guild, the
Dream→Code chain. This Dream is the **machine that installs it** — the difference between
a model that exists in one repository and a model that can be adopted by any repository.

```bash
genesis init    # greenfield — a new repo born Dream-first
genesis adopt   # brownfield — layer the model onto a repo without disturbing what runs
```

What it stands up: the pixi environment and Python toolchain, `bmad-method`, `bmad-loop`
and `bmad-dev-auto`, the multi-project wiring (`scripts/bmad-switch`, per-project config and
artifact isolation, concurrent loop homes), `skill-forge`, and the BMM / BMB / TEA core
modules — plus the tier layout (`docs/dreams/`, `_bmad-output/projects/<station>/`), the
`AGENTS.md` family, and the deck family.

## Why this is the Marshal's

Splitting this out of [[pyforge-genesis]] (2026-07-28, Charter §5 amendment) resolved a
Dream that was doing two jobs at once. Genesis-the-Dream is **constitutive** — it records
the Charter, the Lexicon, and the Guild's membership, and is owned by `guild` because it
precedes the stations. The installer is **buildable work**, and buildable work with no
accountable Smith is the exact condition the station model exists to make impossible.

It is the Marshal's by the Charter's own text, not by assignment: Marshal's toolkit already
lists every component this installs (bmad-method, bmad-loop, BMM/BMB/TEA, skill-forge,
web bundles), Marshal already owns *Monorepo & Multi-Project Operation* (`bmad-switch`,
per-project isolation, loop homes), and Marshal's CLI cadence already opens with
`marshal init — initialize a new BMAD-compliant project blueprint`. The installer is that
verb, made real.

## What is real

- **The Spec** — `spec-genesis-installer` (9 capabilities), with its extraction manifest:
  what is **copied** (conventions, skills, workflows) vs **referenced** (bmad-method
  releases) vs **generated** (per-repo Dreams).
- **The proof** — this repository was the first brownfield adoption, installed by hand from
  `archive/docs/bmad-setup-plan.md`. The installer is that procedure, generalized.
- **The chain** — PRD, architecture and epics exist (Foundation & the Write Guard · the
  Managed-Region Engine · Detect & Plan), inherited from the pre-split `pyforge-genesis`
  project.

## The frontier

- **The write guard and managed regions** are the hard part: `adopt` must layer the model
  onto a live repo without clobbering what already runs. Every write is either into a
  managed region it owns, or refused.
- **Idempotent re-adoption** — running `adopt` twice must be a no-op, and running it after
  a model upgrade must migrate rather than overwrite.

## Realization log

- **2026-07-28** — split from [[pyforge-genesis]] per the Charter §5 amendment
  ("owning is becoming — at the planning tier"). Genesis keeps the constitutive records;
  the installer becomes this Dream, owned by the Marshal. The chain (Spec, PRD,
  architecture, epics) moves to `pyforge-marshal` — physically blocked until Marshal's
  planning tree is sharded, because both trees are currently flat and their `prd.md` /
  `architecture.md` / `epics.md` would collide.
