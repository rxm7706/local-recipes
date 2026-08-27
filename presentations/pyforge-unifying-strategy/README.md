# PyForge Unifying Strategy — deck family

Herald-station presentation family for the **pyforge-unifying-strategy** chain
(*PyForge Unifying Strategy — The Canopy & 8-Station Hub-and-Spoke Enterprise
Architecture*). Steward's chain; display brand **The Canopy** on the slides,
slug `pyforge-unifying-strategy` in paths, per the display-brand-vs-slug rule
in `docs/specs/presentation-deck.md`.

**Content grounding** (all facts derived, none recalled):

- `docs/dreams/pyforge-unifying-strategy.md` — the Dream + decision trail
  (Grounding, the 2026-08-24 rulings, the Realization log).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/`
  — SPEC.md (CAP-1..19 with live proofs), `stack.md`, `convergence.md`,
  `console-parity-inventory.md`, `resilience-invariants.md`,
  `architecture-diagrams.md`; plus the brief and PRD bundles dated 2026-08-24.

## The artifact family

```
project/
  Unifying Strategy Deck.dc.html                       28-slide narrative deck prototype (six acts)
  PyForge Unifying Strategy - Executive Summary.dc.html  one-page 1920×1080 exec summary
  PyForge Unifying Strategy - Infographic.dc.html        ★ the trio head — 19-section one-pager, 3 inline-SVG diagrams
  PyForge Unifying Strategy - Infographic Deck.dc.html   the same story re-laid as 27 slides
  PyForge Unifying Strategy Infographic standalone.html  same body as ★, no x-dc wrapper, styles in <head>
src/marp/
  pyforge-unifying-strategy-deck-2026-08-26.md
  pyforge-unifying-strategy-executive-summary-2026-08-26.md
  pyforge-unifying-strategy-infographic-2026-08-26.md
  pyforge-unifying-strategy-infographic-standalone-2026-08-26.html   (generated — marp)
src/pptx/
  pyforge-unifying-strategy-deck-2026-08-26.pptx                     (generated — marp --pptx)
  pyforge-unifying-strategy_infographic_deck-2026-08-26.pptx         (generated — marp --pptx)
```

Regenerate the derived exports (never hand-edit them):

```bash
pixi run -e local-recipes deck-export pyforge-unifying-strategy
```

Visual system: **Modernist** (Archivo / Archivo Expanded; light `#f3f2f2`,
ink `#201e1d`, red `#ec3013`), matching the other pyforge persona decks. The
form/density exemplar is `presentations/pyforge-warden/project/"Warden
Infographic standalone.html"`; the six-act arc follows the canonical deck
framework. Design-system tokens are inlined in each `.dc.html` helmet so every
file renders from disk (Google Fonts online, system fallback offline).

**Deliberately not included:** the React/Vite interactive deck engine
(`src/deck/`, `scripts/extract-slides.mjs`, `dist/`). The family filename
contract does not require it; the prototype honors the `<section
data-label/data-speaker-notes>` extraction contract, so wiring the engine
later is a mechanical copy from `presentations/pyforge-warden/` plus
`npm run extract`.
