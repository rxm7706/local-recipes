# PyForge Genesis deck (`pyforge.genesis`)

**Status: STARTER — awaiting the Design pass.** The **master vision deck** of the
pyforge **"Dream to Code"** factory — the deck for the founding Dream itself
(`docs/dreams/ecosystem-crew.md`): the Genesis, the six-persona Ecosystem Crew,
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

**Infographic edited in Design + pulled 2026-07-24** — `PyForge Genesis -
Infographic.dc.html` was hand-expanded in the Design project (17,574 → 40,257
bytes; +2 sections: "The autonomy gradient" and "The SDLC, staffed — phase ×
persona × skills") and pulled to disk **byte-exact** (etag `1784926528376406`,
via render-preview → strip-harness). `PyForge Genesis Infographic
standalone.html` was **mechanically re-derived from the edited dc.html** (same
body, x-dc wrapper dropped, helmet hoisted to `<head>`) so the pair stays in
step. NOT auto-synced: the `- Infographic Deck.dc.html` (slides) — a different
layout that needs the 2 new sections re-laid as slides — and the Marp/pptx
exports (they derive from the Marp `.md`, not the dc.html).
