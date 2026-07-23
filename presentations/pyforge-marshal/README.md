# PyForge-Marshal deck (`pyforge.marshal`)

**Status: SCAFFOLD — prototype pending.** Engine + glue are in place (copied
**verbatim** from `presentations/pyforge-atlas/`, the Archivo persona system);
the Claude Design prototype has not been authored yet, so `src/slides/` holds an
empty `manifest.json` and no fragments.

A self-contained React + Vite slide deck for **PyForge-Marshal** — the Commander — autonomous build-factory supervisor & BMAD-method orchestrator of the pyforge
**"Dream to Code"** Ecosystem Crew (founding Dream:
`docs/dreams/ecosystem-crew.md`). Motto: *"Enforce the spec. Guard the boundaries. Run the line."*

Built with the reusable **Design-to-Deck** workflow
(`docs/specs/presentation-deck.md` — read it first; it defines the prototype
contract, the pipeline, and the § Standard export set this deck must ship).

## Wiring the deck (when the prototype lands)

1. **Author the deck in Claude Design** at **1920×1080** following the prototype
   contract (each slide one `<section>` with `data-label`, `data-speaker-notes`,
   `style="background:#HEX; …"`). Use the family design system: Archivo /
   Archivo Expanded; light `#f3f2f2`, dark `#201e1d`, red `#ec3013` / `#c22a10`.
2. **Drop the handoff export** in `project/` as **`PyForge Marshal.dc.html`** (or update
   `SRC` in `scripts/extract-slides.mjs`; spaces in the name are fine).
3. `npm run extract` → fragments + manifest; `npm run dev` to review;
   `npm run build` for the offline `dist/`.
4. **Exports:** author the three Marp sources in `src/marp/`
   (`pyforge-marshal-deck-<date>.md`, `-executive-summary-<date>.md`, `-infographic-<date>.md`),
   then `pixi run -e local-recipes deck-export pyforge-marshal` regenerates the derived
   standalone HTML + PPTX (§ Standard export set).

## Quick start

```
npm install
npm approve-scripts esbuild && npm rebuild esbuild   # npm 11+ blocks esbuild's install script
npm run extract && npm run dev
```

## Keymap

`→`/`Space`/`PgDn` next · `←`/`PgUp` prev · `Home`/`End` first/last · `O` overview ·
`S` presenter (notes + timer) · `F` fullscreen · `?` help · `Esc` back. Slide index
mirrors to the URL hash (`#/12`).

Display brand **Marshal** on the slides; distribution slug `pyforge-marshal` in paths.
Engine files must stay **byte-identical** across every deck — apply any engine fix
to all decks in the same change (`diff -q` to prove it).

## Design project (the bridge's far end)

Prototype lives in Claude Design project **"PyForge Marshal deck"** (`ad84d4f6-c292-42c8-98bf-ede78a567773`):
https://claude.ai/design/p/ad84d4f6-c292-42c8-98bf-ede78a567773?file=PyForge+Marshal.dc.html
Pull it into this deck with the MCP bridge ("pull marshal") — see
`docs/specs/presentation-deck.md` § *The MCP bridge*.
