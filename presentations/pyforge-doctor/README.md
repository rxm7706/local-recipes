# PyForge-Doctor deck (`pyforge.doctor`)

**Status: SCAFFOLD — prototype pending.** Engine + glue are in place (copied
**verbatim** from `presentations/pyforge-atlas/`, the Archivo persona system);
the Claude Design prototype has not been authored yet, so `src/slides/` holds an
empty `manifest.json` and no fragments.

A self-contained React + Vite slide deck for **PyForge-Doctor** — the Physician — ecosystem health & diagnostics officer of the PyForge
**"Dream to Code"** PyForge Guild (founding Dream:
`docs/dreams/pyforge-charter.md`). Motto: *"Check the vitals. Diagnose the fault. Keep the ecosystem alive."*

Built with the reusable **Design-to-Deck** workflow
(`docs/specs/presentation-deck.md` — read it first; it defines the prototype
contract, the pipeline, and the § Standard export set this deck must ship).

## Wiring the deck (when the prototype lands)

1. **Author the deck in Claude Design** at **1920×1080** following the prototype
   contract (each slide one `<section>` with `data-label`, `data-speaker-notes`,
   `style="background:#HEX; …"`). Use the family design system: Archivo /
   Archivo Expanded; light `#f3f2f2`, dark `#201e1d`, red `#ec3013` / `#c22a10`.
2. **Drop the handoff export** in `project/` as **`PyForge Doctor.dc.html`** (or update
   `SRC` in `scripts/extract-slides.mjs`; spaces in the name are fine).
3. `npm run extract` → fragments + manifest; `npm run dev` to review;
   `npm run build` for the offline `dist/`.
4. **Exports:** author the three Marp sources in `src/marp/`
   (`pyforge-doctor-deck-<date>.md`, `-executive-summary-<date>.md`, `-infographic-<date>.md`),
   then `pixi run -e local-recipes deck-export pyforge-doctor` regenerates the derived
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

Display brand **Doctor** on the slides; distribution slug `pyforge-doctor` in paths.
Engine files must stay **byte-identical** across every deck — apply any engine fix
to all decks in the same change (`diff -q` to prove it).

## Design project (the bridge's far end)

Prototype lives in Claude Design project **"PyForge Doctor deck"** (`46dbbdea-6f8d-45c6-9309-15d1f297beeb`):
https://claude.ai/design/p/46dbbdea-6f8d-45c6-9309-15d1f297beeb?file=PyForge+Doctor.dc.html
Pull it into this deck with the MCP bridge ("pull doctor") — see
`docs/specs/presentation-deck.md` § *The MCP bridge*.
