---
spec: modernist-identity
status: shipped
owner-dream: docs/dreams/modernist-identity.md
program: regenerable-factory (Wave 3)
surface:
  - presentations/**
  - scripts/deck_export.py   # the export-set contract's engine
companions:
  - ../../../../../../docs/specs/presentation-deck.md   # adopted: deck workflow (legacy Tier-1, in force)
open_questions: []
---

# SPEC — one visual language for everything pyforge

## Why

Every pyforge artifact a human sees — decks, infographics, exports — speaks
one visual language, so the family reads as one product. Owner: Herald.

## Capabilities

- **CAP-1 — the Modernist design system.** Intent: all Design work binds the
  Modernist DS (Design project `fbc1d6c8-b35f-4df6-9044-a64d2675427b`):
  palette `#f3f2f2` ground / `#201e1d` ink / `#ec3013` accent / `#c22a10`
  accent-deep / `#d3d0cf` line; Archivo + Archivo Expanded. Success: a new
  deck seeded through the bridge inherits the DS without manual styling.
- **CAP-2 — one engine, many decks.** Intent: the deck engine (fit-to-
  viewport, keyboard nav, hash routing, overview grid, presenter view) is
  byte-identical across every deck under `presentations/`. Success: engine
  files diff empty across all decks (10 at time of writing).
- **CAP-3 — the `.dc.html` contract.** Intent: Design-authored prototypes
  are mechanical-extraction-ready: 1920×1080 `deck-stage` sections carrying
  `data-label`, `data-speaker-notes`, `background:#hex`. Success: the
  extractor produces N labeled slides with correct backgrounds and notes.

## Constraints

- Speaker notes must stay bracket-free — the extractor's tag regex stops at
  the first `>`, and an angle bracket inside `data-speaker-notes` silently
  truncates the tag (observed: phantom `#0B1626` background).
- Standard export set per deck: prototype + extracted slides + built bundle
  + standalone HTML + Marp + PPTX (`deck-export` task).

## Non-goals

- Per-deck bespoke styling; editable-PPTX engine internals (that is
  [[deckcraft]]'s Dream).

## Success signal

Engine byte-identity check passes across the family; a bridge-seeded deck
renders in the DS with zero manual font/color fixes; every deck ships the
standard export set.
