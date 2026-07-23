---
title: Local AI — the factory's own compute
type: dream
status: seeded
---

# Local AI — models that run where the code lives

## The Dream

The factory owns its inference: a **dual-GPU local AI workstation** (and the
software posture to use it) so that planning, embedding, vision, and eventually
dev-loop inference can run on-premises — flat-cost, private, air-gap-compatible.
The hardware dream is concrete (16-core X3D, dual RTX 5080-ready, 1600 W); the
software dream connects it to everything already specced for local execution.

## What it looks like when real

- The build assembled (`local-ai-2026-dual-gpu/` gist: full parts list, dual-GPU
  PCIe 5 x8/x8 layout, expansion-ready).
- Local backends serving the stack: vLLM (the [[sentinel]] ADR-005b default),
  per-agent local model tiers (ADR-038), mlx/deckcraft local image generation,
  embedding/RAG for [[team-memory]] and [[pyforge-scribe]]'s graph.
- Flat-rate/local planning per [[agent-portability]]; fully offline operation
  per [[enterprise-airgap]].

## Realization log

- **2026-06-21** — build list authored (gist).
- **2026-07-23** — Dream seeded from the gist audit; snapshot at
  `docs/specs/gists/local-ai-2026-dual-gpu/`.
