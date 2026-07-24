# PyForge-Atlas deck (`pyforge.atlas`)

A self-contained React + Vite slide deck for **PyForge-Atlas** — the conda-forge
intelligence layer being migrated from a hand-rolled ~10,000-LOC orchestrator to
declarative **Kedro + Dagster + DuckDB** dataflow, with a Boring Semantic Layer,
a Vizro / Vizro-AI read surface, and MCP / A2A agent interfaces. Built with the
reusable **Design-to-Deck** workflow (`docs/specs/presentation-deck.md`); the
deck **engine** (`src/deck/*`) and glue are copied verbatim from
`presentations/pyforge-warden/`, so only the **prototype** and the **generated**
`src/slides/fragments/` + `manifest.json` are PyForge-Atlas-specific.

The slide content lives in the Claude Design prototype at
`project/PyForge Atlas.dc.html`; the fragments and manifest are generated from
it by `npm run extract` and are already committed here (21 slides, 5 acts).

## Quick start

```
npm install
npm approve-scripts esbuild && npm rebuild esbuild   # npm 11+ blocks esbuild's install script
npm run extract    # prototype -> src/slides/fragments/*.html + manifest.json
npm run dev        # review at localhost:5173
npm run build      # static, offline-safe dist/
```

`extract` is plain Node (no esbuild) and runs without the approve-scripts step.
`dev`/`build` need it once per clone; commit the `allowScripts` entry + lockfile.

## Bringing in / updating the deck

1. **Author the deck in Claude Design** at **1920×1080**, following the
   *prototype contract* in `docs/specs/presentation-deck.md`: each slide is one
   `<section>` carrying `data-label="…"`, `data-speaker-notes="…"`, and
   `style="background:#HEX; …"` (first `#hex` = slide background); inline styles;
   footers `PYFORGE-ATLAS · <TAG>` left, `NN / TT` right. Each slide's inner is a
   full-frame root `<div>` (the extractor keeps only the section inner, rendered
   into a padding-less `1920×1080` frame).
2. **Export the handoff `.dc.html`** and drop it in **`project/`**, named
   **`PyForge Atlas.dc.html`** (or rename `SRC` at the top of
   `scripts/extract-slides.mjs` to match your filename — spaces are fine).
3. **Extract → build:** `npm run extract` (→ 21 fragments + manifest),
   then `npm run dev` to review or `npm run build` for `dist/`.
4. **(Optional) exports:** keep a Marp `.marp.md` mirror in `src/marp/` and a
   dated PowerPoint `src/pptx/pyforge-atlas-YYYY-MM-DD.pptx`.

## Keymap

| Key | Action |
|---|---|
| `→` · `Space` · `PgDn` | Next slide |
| `←` · `PgUp` | Previous |
| `Home` · `End` | First / last |
| `O` | Overview grid |
| `S` | Presenter view (notes + timer) |
| `F` | Fullscreen |
| `?` | Keyboard cheat-sheet |
| `Esc` | Back to the deck |

The current slide mirrors to the URL hash (`#/12`) — every slide is
deep-linkable and reload-stable.

## How it's structured

- **`src/deck/*`, `src/slides/index.js`, `vite.config.js`, `src/main.jsx`,
  `src/App.jsx`, `src/index.css`, `.gitignore`** — the topic-agnostic engine +
  glue, copied **verbatim** from `pyforge-warden`. Keep byte-identical across
  decks; any engine fix lands in every copy in the same change.
- **`index.html`** — per-deck title/description + the Archivo Google-Fonts link.
- **`scripts/extract-slides.mjs`** — topic-agnostic extractor; only its `SRC`
  (prototype filename) and `BANNER_MAP` are per-deck (`BANNER_MAP = {}` here —
  the prototype references no remote images, so `dist/` is fully offline bar
  Google Fonts).
- **`project/`** — the design handoff (`PyForge Atlas.dc.html` + its
  `deck-stage.js` / `support.js` design-time runtime).
- **`src/slides/fragments/` + `manifest.json`** — **generated** by `extract`;
  never hand-edit (they're overwritten). Content lives in the prototype.

## Act structure (21 slides)

Cover · **Act I** From monolith to DAG (problem · before/after · seven pipelines)
· **Act II** Node-shaped & agent-maintainable (add phase 24 · what it buys ·
verify-first gate) · **Act III** An agent workforce builds it (who runs it ·
graduated autonomy · eight waves · which surface) · **Act IV** New signals
(Basilisk / velocity / readiness · open questions) · **Act V** The read surface
inverts (five surfaces · the pyforge family) · closing statement.

Design brand **Atlas** on the slides; distribution slug `pyforge-atlas` in paths.
Palette is Modernist — light `#f3f2f2`, dark `#201e1d`, red `#ec3013` / `#c22a10`
— matching the `pyforge-warden` deck so the two sit next to each other.

## Design project (the bridge's far end)

Claude Design project **"PyForge Atlas deck"**
(`2acb0575-9997-442b-bb0e-6207d78f6648`) — created + seeded 2026-07-24 (the
deck predates the pilot, so it had no Design project until now). Bound to the
Modernist design system.

### Artifact map + sync ledger (2026-07-24, disk → Design seed)

- `PyForge Atlas.dc.html` (75448, `1784892835897059`) — **byte-identical to
  disk** ✓ (uploaded via DesignSync `localPath`, no context relay)
- `support.js` (66404, `1784890273511358`) — server-written current runtime,
  matches disk byte count
- `deck-stage.js` (133230, `1784890278864518`) — server-side copy from the
  genesis project (byte count matches disk)
- `PyForge Atlas - Executive Summary.dc.html` (7656) +
  `src/marp/pyforge-atlas-{deck,executive-summary,infographic}-2026-07-24.md`
  — batch etag `1784893549439075`

Disk-side only (stay git-side): `src/pptx/*.pptx`, the infographic standalone,
the built React deck. Convention: Design project name ↔ this folder.
