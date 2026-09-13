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

## Ledger — 2026-09-13 standard rebuild (Story 20.4)

Rebuilt repo-side to `infographic-standard.md` (spec-deck-family-currency CAP-3) from
`facts.yaml` re-derived at tree `b5fe5e46fc`. Every count, version, status and date the
poster prints is a `data-fact` mark resolving to a ledger row; `deck-facts pyforge-doctor
--check` → `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced, 0 unshown; facts 85/85`.

| Artifact | Measured | Design etag | Notes |
|---|---|---|---|
| `PyForge Doctor Infographic standalone.html` | 135,606 B · 24 sections (23 numbered + creed) · 6 acts · 4 SVG · 9 tables · facts 85/85 | `pushed 2026-09-13 via DesignSync `finalize_plan` → `write_files` (localPath) · Design etag `1789296846077989` · 135,606 B on both sides · read back 2026-09-13 via `render_preview` → curl → harness strip: **byte-identical** to git` (operator pushes via DesignSync after review) | rendered 2026-09-13, page 20012 px; head + Infographic Deck: standalone ahead (lockstep slice pending) |

Floors (standard): acts exactly six ✓ · sections ≥ 18 ✓ · inline SVG ≥ 3 ✓ · bytes ≥ 90,000 ✓ ·
tables ≥ 3 ✓ · cast cards full for all eight stations ✓ · facts all resolved ✓ · headless
full-page PNG at 1240 px reviewed by eye (`.herald/deck-qa/pyforge-doctor/standalone.png`,
gitignored) ✓ · offline apart from the Google Fonts `<link>` ✓. No section of the standard's
set was dropped; the Warden "sub-agent team" slot is filled by Doctor's source registry (§06).
