# PyForge-Warden deck (`pyforge.warden`)

A self-contained React + Vite slide deck for **PyForge-Warden** — the multi-axis
Python dependency compliance gate. Built with the reusable **Design-to-Deck**
workflow (`docs/specs/presentation-deck.md`); the deck **engine** (`src/deck/*`)
and glue are copied verbatim from `presentations/agentic-sdlc/`, so only the
**prototype** and the **generated** `src/slides/fragments/` + `manifest.json`
are PyForge-Warden-specific.

> **This is a scaffold.** The slide content is not here yet — it lives in a
> Claude Design prototype you drop in (below), then extract.

## Bringing in the Claude Design session work

1. **Author the deck in Claude Design** at **1920×1080**, following the
   *prototype contract* in `docs/specs/presentation-deck.md`
   ("The prototype contract"): each slide is one `<section>` carrying
   `data-label="…"`, `data-speaker-notes="…"`, and `style="background:#HEX; …"`
   (first `#hex` = slide background); inline styles; footers `PYFORGE-WARDEN · <TAG>`
   left, `NN / TT` right; `<image-slot placeholder="Drop image">` for screenshot
   drop targets. (The paste-in prompt is recorded with the effort.)
2. **Export the handoff `.dc.html`** and drop it in **`project/`**, named
   **`PyForge-Warden.dc.html`** (or rename `SRC` at the top of
   `scripts/extract-slides.mjs` to match your filename).
3. **Remote images:** if the prototype references any remote image, add an entry
   to `BANNER_MAP` in `scripts/extract-slides.mjs` and download the image into
   `public/assets/banners/` (relative paths, offline-safe).
4. **(Optional) restructure:** if the raw prototype needs editorial surgery
   (insert act dividers, reorder, renumber footers), author a per-deck
   `scripts/restructure-deck.mjs` (see the agentic-sdlc one as a template — it
   is **not** reusable verbatim) and run it once before extract.
5. **Build the deck:**
   ```
   npm install
   npm run extract    # prototype -> src/slides/fragments/*.html + manifest.json
   npm run dev        # review at localhost:5173
   npm run build      # static, offline-safe dist/
   ```
6. **Exports:** keep a Marp `.marp.md` in `project/` (mirror to `src/marp/`) and
   a dated PowerPoint `src/pptx/pyforge-warden-YYYY-MM-DD.pptx`.

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
  glue, copied verbatim from `agentic-sdlc`. Don't hand-edit for content.
- **`scripts/extract-slides.mjs`** — topic-agnostic extractor; only its `SRC`
  (prototype filename) and `BANNER_MAP` are per-deck (already stubbed).
- **`project/`** — the design handoff (drop `PyForge-Warden.dc.html` here).
- **`src/slides/fragments/` + `manifest.json`** — **generated** by `extract`;
  never hand-edit (they're overwritten). Content lives in the prototype.
- **`public/assets/banners/`** — remote images localized for offline/export.

Reskin the palette in `src/index.css` (`--navy`/`--paper`/`--gold`/`--blue`/`--sky`)
if PyForge-Warden gets its own colors.
