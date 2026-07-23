---
title: Presenton, conda-native — AI decks inside the regulated enterprise
type: dream
status: seeded
---

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

## What is real

- The BMAD project `presenton-pixi-image` (registered, active). Planning not yet
  run under the Dream-first flow.

## Realization log

- **2026-07** — project registered in PROJECTS.md.
- **2026-07-23** — Dream retro-seeded; awaits `bmad-spec`.
