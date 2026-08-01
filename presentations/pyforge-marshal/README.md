# PyForge-Marshal deck (`pyforge.marshal`)

**Status: FULL FAMILY — the ecosystem chapter deck.** 26-slide prototype
(six-act arc, 2026-07-31 generation) extracted and built; the complete
five-artifact Design family is current (deck · infographic · Infographic Deck ·
standalone · exec summary). Since the genesis fold, this family carries the
whole big picture: the Charter, the Guild, the Dream-to-Code operating model.
Content standard: full-depth warden-pattern sections with acts — see the
per-deck ledger below. Narration extracts + the master ecosystem script live in
`src/marp/` (inputs for `bmad-manticore` video production).

A self-contained React + Vite slide deck for **PyForge-Marshal** — the Commander — autonomous build-factory supervisor & BMAD-method orchestrator of the PyForge
**"Dream to Code"** PyForge Guild (founding Dream:
`docs/dreams/pyforge-charter.md`). Motto: *"Enforce the spec. Guard the boundaries. Run the line."*

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

## Ledger — 2026-07-31 six-act rebuild (Design ↔ repo sync)

| Artifact | Slides/size | Design etag |
|---|---|---|
| `PyForge Marshal.dc.html` | 26 slides · 100,631 B | `1785555947450949` |
| `PyForge Marshal - Infographic.dc.html` | 19 sections + 6 acts · 91,060 B | `1785551674739328` |
| `PyForge Marshal Infographic standalone.html` | body-identical mirror | `1785551674739328` |
| `PyForge Marshal - Infographic Deck.dc.html` | 20 slides · 90,658 B | `1785556512103907` |
| `PyForge Marshal - Executive Summary.dc.html` | 1080p one-shot, stats refreshed | `1785556555212786` |

Authored repo-side this generation (inverted from the usual Design-first flow);
pushed byte-for-byte via the DesignSync localPath pipeline. On the next
Design-side edit session, finish with a byte-exact pull per
`docs/specs/presentation-deck.md` § the MCP bridge.
