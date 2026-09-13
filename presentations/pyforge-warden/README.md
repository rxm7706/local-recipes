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

## Ledger — 2026-09-13 standard rebuild (Story 20.10)

Rebuilt repo-side to `infographic-standard.md` (spec-deck-family-currency CAP-3) from
`facts.yaml` re-derived at tree `fbefe6eea6`. Every count, version, status and date the
poster prints is a `data-fact` mark resolving to a ledger row; `deck-facts pyforge-warden
--check` → `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced, 1 unshown; facts 91/91` (the one
`unshown` row is `poster_last_commit_date`, deliberately not printed — dates come only from
the `dream_log_*` and `tree_commit_date` rows).

| Artifact | Measured | Design etag | Notes |
|---|---|---|---|
| `Warden Infographic standalone.html` | 295,079 B · 33 sections (32 numbered + creed) · 6 acts · 26 SVG · 11 tables · facts 91/91 | `PENDING-PUSH` (operator pushes via DesignSync after review) | rendered 2026-09-13, page 34715 px; head + Infographic Deck: standalone ahead (lockstep slice pending) |

Floors (standard): acts exactly six ✓ · sections ≥ 18 ✓ · inline SVG ≥ 3 ✓ · bytes ≥ 90,000 ✓ ·
tables ≥ 3 ✓ · cast cards full for all eight stations with ledger chips ✓ · facts all resolved ✓ ·
headless full-page PNG at 1240 px reviewed by eye in 2500 px tiles
(`.herald/deck-qa/pyforge-warden/`, gitignored) ✓ · offline apart from the Google Fonts `<link>` ✓ ·
no `<script>`, no `<x-dc>`, no `support.js`, no raster image ✓. No section of the standard's set
was dropped; the "sub-agent team" slot is filled by Warden's engines and feeds (§07).

**This file remains the family's density and visual-form reference.** The 411,764 B measured on
2026-09-13 was a Claude Design *bundle*: 192,472 B of page content JSON-encoded inside a
`__bundler/template` script tag plus ~205 KB of base64 assets (three Archivo woff2 faces and three
Design runtime scripts) and an `<x-dc>` wrapper — none of which the standard permits. The rebuild
is plain standalone HTML, so the honest before/after is **192,472 B → 295,079 B of page content**,
18 → 32 numbered sections, every div-built diagram kept (the six-axis grid, the five-step
pipeline, the three path columns, the lattice ladder, the three rings, the roadmap and leader
cards, the 70-row integration matrix), the 14 icon glyphs kept with their `viewBox` restored
(Design had mangled them to `sc-camel-view-box`, so they never scaled outside Design), Design's
`sc-raw-table` pseudo-elements converted to real `<table>` markup, and four genuine 1128-wide
SVG diagrams added (the spine topology, the seven-rungs-to-four-exits ladder, the autonomy
gradient, the relay).

Left out for lack of a fact row (never guessed): the two-ecosystem population figures
(`~850K packages`, `~30K feedstocks`, the `20% / 80%` footprint split), the `20k+` repo-fleet
scale target, the waiver default expiry (`14 days`), the old `5 epics · 20 stories` scope cell,
`Python 3.12+` and every other two-part or third-party version (CycloneDX spec, report schema,
deptry / osv-scanner ranges), story counts such as `31/31` / `43/43`, the corpus size
(`~1,950`), the test count (`--with-tests` not run), and the retired duplicate Dream's date.
Exit codes appear only as separate code literals or in their own table cells, never
slash-adjacent.
