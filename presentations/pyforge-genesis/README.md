# PyForge Genesis deck (`pyforge.genesis`)

**Status: STARTER — awaiting the Design pass.** The **master vision deck** of the
pyforge **"Dream to Code"** factory — the deck for the founding Dream itself
(`docs/dreams/pyforge-charter.md`): the Genesis, the six-persona Ecosystem Crew,
the Master Pipeline, and the proof it already runs. Each persona deck
(`pyforge-atlas` … `pyforge-doctor`) is one *chapter* of this Dream; Genesis is
the parent narrative — **and the seed**: it lays out the big picture well enough
to initiate a new repo with the operating model, or to adopt the model in a
brownfield repo (this repo was the first brownfield adoption).

Engine + glue copied **verbatim** from `presentations/pyforge-atlas/` (Archivo /
Modernist system). Built with the Design-to-Deck workflow
(`docs/specs/presentation-deck.md` — prototype contract, pipeline, § Standard
export set).

## Quick start

```
npm install
npm approve-scripts esbuild && npm rebuild esbuild   # npm 11+ blocks esbuild's install script
npm run extract && npm run dev
```

Keymap: `→`/`Space` next · `←` prev · `O` overview · `S` presenter · `F` fullscreen ·
`?` help · URL hash (`#/n`) deep-links.

Display brand **pyforge · Dream to Code** on the slides; slug `pyforge-genesis`
in paths. Engine files stay **byte-identical** across every deck.

## Design project (the bridge's far end)

Prototype lives in Claude Design project **"PyForge Genesis deck"** (`6af4c28d-d510-4e9b-b788-6c0e5d651183`):
https://claude.ai/design/p/6af4c28d-d510-4e9b-b788-6c0e5d651183?file=PyForge+Genesis.dc.html
Pull it into this deck with the MCP bridge ("pull genesis") — see
`docs/specs/presentation-deck.md` § *The MCP bridge*.

## Artifact family (2026-07-24 sweep)

Full warden-style set on disk: derived Marp deck + authored Executive Summary
(Marp + `project/PyForge Genesis - Executive Summary.dc.html`) + authored
Infographic (Marp) + `deck-export` outputs (standalone HTML + deck/infographic
PPTX), all dated 2026-07-24. Design-project upload of the light artifacts
(3 Marp + exec-summary dc.html) queued in the family-wide upload pass.

**Infographic hand-expanded in Design + fully round-tripped 2026-07-24.** The
one-pager `PyForge Genesis - Infographic.dc.html` was grown in the Design project
(17,574 → **48,040** bytes; +3 sections: "The autonomy gradient — how far the
leash goes" (L1–L5 ladder), "The SDLC, staffed — phase × persona × skills", and
"The Master Pipeline relay") and pulled to disk **byte-exact** (etag
`1784926929273012`, via render-preview → strip-harness). The whole infographic
family was then refreshed to match and re-synced both ways:
- `Infographic standalone.html` — mechanically re-derived from the edited dc.html
  (x-dc wrapper dropped, helmet hoisted to `<head>`); pushed back to Design.
- `src/marp/…-infographic-2026-07-24.md` — 3 condensed slides added (the ladder,
  the phase×persona table, the relay); pushed back to Design.
- `- Infographic Deck.dc.html` — 3 deck-stage slides added (badges 04–06), Proof
  and seed renumbered to 07/08; pushed back to Design.
- `deck-export` re-run → refreshed `…-infographic-standalone-*.html` +
  `…_infographic_deck-*.pptx` + `…-deck-*.pptx`.

NOT touched (separate branches, not affected by an infographic edit): the main
deck (`PyForge Genesis.dc.html` / `…-deck-*.md`) and the Executive Summary.
