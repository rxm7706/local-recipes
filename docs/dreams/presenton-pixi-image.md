---
title: Presenton, conda-native — AI decks inside the regulated enterprise
type: dream
owner: mason
status: archived
archived-reason: blocked
blocked-on: Phase-0 decision gate (Epic 1)
---

> **Archived, blocked — not superseded, not absorbed.** The full BMAD planning
> chain (research → brief → PRD → architecture → 7 epics / 30 stories) landed
> 2026-07-25 and has not moved since: no story has entered implementation, and
> the Phase-0 exit criteria this Dream's own frontmatter names
> (`blocked-on: Phase-0 decision gate`) remain unresolved a week later — most
> load-bearingly, whether Microsoft's disconnected on-prem stack (GA
> 2026-02-24) already ships a Copilot-for-PowerPoint-equivalent, which bears
> directly on whether this Dream's core differentiator still holds. This
> record is genuinely unrelated subject matter to [[pyforge-mason]] — an
> air-gapped repackaging of a third-party AI deck tool, not part of the
> `mason` CLI — so it is archived on its own, not folded into that Dream's
> narrative. See `spec-presenton-pixi-image`'s retirement record for the full
> account of what was contracted, why work stopped, and what carries forward
> if the Phase-0 gate is ever cleared.

# Presenton for the air-gapped enterprise

## The Dream

Bring the Presenton AI deck-generation app to places SaaS cannot go: an
**air-gapped, conda-forge-native repackaging** deployable on OpenShift Container
Platform in regulated-enterprise environments. Every dependency resolved from
governed channels, every image reproducible, no call home — AI deck generation
as an internal platform service.

## What it looks like when real

- Presenton repackaged with conda-forge primitives (pixi-locked image,
  OpenShift-ready), passing [[pyforge-warden]]-grade dependency gates.
- Distribution through the [[enterprise-airgap]] machinery (Artifactory
  routing, offline bundles).
- Division of labor with [[deckcraft]]: presenton = the repackaged *app*;
  deckcraft = the from-primitives *pipeline*. Complementary, not competing.
- Stations: [[packaging-factory]] (Mason) repackages; **[[pyforge-steward]]
  deploys and operates** the OpenShift service.

## What is real

- The BMAD project `presenton-pixi-image` (registered, active). Planning not yet
  run under the Dream-first flow.

## Realization log

- **2026-07** — project registered in PROJECTS.md.
- **2026-07-23** — Dream retro-seeded; awaits `bmad-spec`.
- **2026-08-02** — **ARCHIVED (blocked)** during dream consolidation: the full
  planning chain landed 2026-07-25 (7 epics / 30 stories) and has not moved
  since — no story has entered implementation, and the Phase-0 exit criteria
  remain unresolved. See `spec-presenton-pixi-image`'s retirement record for
  the full account.
