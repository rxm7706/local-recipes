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

## Design project (the bridge's far end)

Prototype lives in Claude Design project **"PyForge Warden deck"**
(`100ca8cc-8daa-409a-8564-1f8d79c579d2`) — renamed 2026-07-24 from
"Python deptry OSV scanner" (it was the original warden deck workspace all
along, mislabeled). Pull with the MCP bridge ("pull warden").

### Artifact map + sync ledger (2026-07-24)

Design-side (etags at last sync):
- `Warden Deck.dc.html` (87101, `1784052451438301`) — **byte-identical to disk** ✓
- `Warden - Executive Summary.dc.html` (7695, `1784053769227170`) — pulled to
  `project/` **byte-exact** 2026-07-24 (supersedes the earlier 7683-byte
  hand-relay pull and its 12B drift)
- `Warden - Infographic.dc.html` (166081, `1784080169043534`) — pulled to
  `project/` **byte-exact** 2026-07-24 ✓
- `Warden - Infographic Deck.dc.html` (88461, `1784080724075247`) — pulled to
  `project/` **byte-exact** 2026-07-24 ✓
- `Warden Infographic standalone.html` (411764) — **user-designated BEST version
  (2026-07-24)**: the golden exemplar for all family infographics. Pulled to
  `project/` **byte-exact** 2026-07-24 ✓. Copied server-side (byte-exact) into
  ALL other deck Design projects (genesis / herald / scribe / steward / doctor /
  mason / marshal / atlas) as `reference/Warden Infographic standalone.html` —
  the shape reference each project's Design chat reads when generating its own
  infographic. Disk's `src/marp/` standalone is a different, marp-regenerated
  render — NOT this artifact.
- engines: `deck-stage.js` 111060 / `support.js` 64222 (older pins than the current
  family 133230/66404 — the dc.html files were authored against these)
- Marp: original `warden-*.md` trio + the refined disk trio uploaded whole as
  `src/marp/pyforge-warden-*-2026-07-15.md` ✓ (batch etag `1784893941350201`,
  2026-07-24, via DesignSync `localPath` — byte-exact, zero context relay).
  A stray root-level `pyforge-warden-executive-summary-2026-07-15.md`
  (`1784887337596364`) remains from the earlier hand-relay upload; superseded
  by the `src/marp/` copy, left in place (delete from the Design UI if unwanted).

Disk-side only (stay git-side; too heavy for the MCP channel):
- `src/pptx/*.pptx` (636KB + 719KB editable exports)
- the built React deck (`src/`, `dist/`), extracted slides, manifest

Convention: Design project name ↔ this folder (`presentations/pyforge-warden`);
Design keeps design sources, disk keeps the full artifact set incl. binaries.

Transfer mechanics (2026-07-24): disk→Design uploads use the `DesignSync` tool's
`write_files` with `localPath` — the file is read/encoded/uploaded server-side,
byte-exact, never relayed through the agent context. Design→disk pulls
(**proven byte-exact 2026-07-24** against the known-identical `Warden
Deck.dc.html`): `render_preview` → `curl` the serve URL to disk → strip the
contiguous `data-omelette-injected` `<style>/<script>` block after `<head>`
(fixed-size harness; splice with a single newline). Both directions are now
mechanized; the herald CLI formalizes them but no longer gates them.
