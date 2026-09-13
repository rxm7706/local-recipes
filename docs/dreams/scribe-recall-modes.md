---
title: Ask for planning, memory, or code without inventing --kind bags
type: dream
owner: scribe
status: specified
---

# Ask for planning, memory, or code without inventing --kind bags

## The Dream

`--kind` is enough for CAP-4 (default omits `code:`). Agents and the
portal still invent argv when they want “just the planning tree” or
“just team memory.” Three named modes — `planning`, `memory`, `code` —
are the PyForge wiring shape.

Internal ranking stays `lexical` / `--semantic`. Those are not these
modes.

## What it looks like when real

- `scribe recall "…" --mode planning` only scores `doc` and `memlog`.
- `--mode memory` only scores `memory`.
- `--mode code` only scores `code`.
- No `--mode` and no `--kind` is still the CAP-4 default bag.
- `--mode` and `--kind` together exit 2.
- Unknown `--mode` exits 2.

## Constraints / Non-goals

- Do not change portal argv in this story (CAP-12 already locks no
  `--kind`).
- Do not replace Marshal `codegraph.db` (CAP-14).
- Do not make semantic ranking the default.

## Kinships

[[pyforge-scribe]] · [[scribe-knowledge-layers]] ·
[[scribe-portal-recall-defaults]]

## Realization log

- **2026-09-13** — Hoisted parked CAP-11. Spec
  `spec-scribe-recall-modes`; Epic 16 Story 16.1.
